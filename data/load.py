"""Executa fitxers .cypher contra Neo4j (Aura o local), en l'ordre indicat.

Ús (des de l'arrel del repositori):
    python data/load.py data/00_constraints.cypher data/01_dades_fixes.cypher
    python data/load.py --dry-run data/01_dades_fixes.cypher
    python data/load.py --param email=paula@example.com data/consultes_comprovacio.cypher

Llegeix NEO4J_URI, NEO4J_USER i NEO4J_PASSWORD (i opcionalment NEO4J_DATABASE)
del fitxer .env de l'arrel del repositori.

Les sentències se separen per ";". Els ";" dins de cadenes de text i els
comentaris (// i /* */) s'ignoren. Les línies d'ordres del Neo4j Browser
(":param", ":use", ...) se salten.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j.exceptions import AuthError, Neo4jError, ServiceUnavailable, SessionExpired

ROOT = Path(__file__).resolve().parent.parent
MAX_ROWS = 50


def make_driver(uri: str, user: str, password: str):
    """Crea el driver. Per a URIs xifrades (neo4j+s://) es fan servir els
    certificats arrel de certifi en comptes dels del sistema: a Windows, Python
    no sempre troba l'arrel que fa servir Aura (SSL.com) i la connexió falla
    amb 'self-signed certificate in certificate chain'."""
    scheme, sep, rest = uri.partition("://")
    if scheme.endswith("+s"):
        try:
            import certifi
            from neo4j import TrustCustomCAs
        except ImportError:
            pass
        else:
            return GraphDatabase.driver(
                f"{scheme[:-2]}{sep}{rest}",
                auth=(user, password),
                encrypted=True,
                trusted_certificates=TrustCustomCAs(certifi.where()),
            )
    return GraphDatabase.driver(uri, auth=(user, password))


def split_statements(text: str) -> list[str]:
    """Separa un script Cypher per ';' respectant cadenes i comentaris."""
    statements: list[str] = []
    buf: list[str] = []
    quote = None
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if quote:
            buf.append(c)
            if c == "\\" and i + 1 < n:
                buf.append(text[i + 1])
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in ("'", '"', "`"):
            quote = c
            buf.append(c)
            i += 1
            continue
        if text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j == -1 else j
            continue
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j == -1 else j + 2
            continue
        if c == ";":
            statements.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(c)
        i += 1
    statements.append("".join(buf))
    return [s.strip() for s in statements if s.strip()]


def parse_params(items: list[str]) -> dict:
    params = {}
    for item in items:
        if "=" not in item:
            sys.exit(f"Paràmetre invàlid '{item}': el format és clau=valor")
        key, raw = item.split("=", 1)
        try:
            params[key] = json.loads(raw)  # números, booleans, llistes...
        except json.JSONDecodeError:
            params[key] = raw  # text
    return params


def preview(statement: str, max_lines: int = 3) -> str:
    lines = [line for line in statement.splitlines() if line.strip()]
    text = "\n      ".join(lines[:max_lines])
    return text + (" ..." if len(lines) > max_lines else "")


def print_records(records, keys) -> None:
    if not records:
        return
    print("      " + " | ".join(keys))
    for record in records[:MAX_ROWS]:
        print("      " + " | ".join(str(record[k]) for k in keys))
    if len(records) > MAX_ROWS:
        print(f"      ... ({len(records) - MAX_ROWS} files més)")


def print_counters(summary) -> None:
    counters = summary.counters
    changes = {
        name: getattr(counters, name)
        for name in (
            "nodes_created", "nodes_deleted",
            "relationships_created", "relationships_deleted",
            "properties_set", "labels_added",
            "constraints_added", "constraints_removed",
            "indexes_added", "indexes_removed",
        )
        if getattr(counters, name)
    }
    if changes:
        print("      canvis: " + ", ".join(f"{k}={v}" for k, v in changes.items()))
    elif summary.query_type in ("w", "rw", "s"):
        print("      canvis: cap (ja existia)")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Carrega fitxers .cypher a Neo4j")
    parser.add_argument("files", nargs="+", type=Path, help="fitxers .cypher, en ordre")
    parser.add_argument("--param", action="append", default=[], metavar="CLAU=VALOR",
                        help="paràmetre per a les consultes (es pot repetir)")
    parser.add_argument("--dry-run", action="store_true",
                        help="només mostra les sentències, sense connectar")
    parser.add_argument("--continue-on-error", action="store_true",
                        help="no s'atura al primer error")
    args = parser.parse_args()

    params = parse_params(args.param)

    scripts = []
    for path in args.files:
        if not path.is_file():
            print(f"ERROR: no existeix el fitxer {path}")
            return 1
        statements = split_statements(path.read_text(encoding="utf-8-sig"))
        scripts.append((path, statements))

    driver = None
    database = None
    if not args.dry_run:
        load_dotenv(ROOT / ".env")
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USER")
        password = os.getenv("NEO4J_PASSWORD")
        database = os.getenv("NEO4J_DATABASE") or None
        if not (uri and user and password):
            print(f"ERROR: falten NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD a {ROOT / '.env'}")
            return 1
        print(f"Connectant a {uri} com a '{user}'...")
        driver = make_driver(uri, user, password)
        try:
            driver.verify_connectivity()
        except (ServiceUnavailable, SessionExpired, AuthError) as exc:
            print(f"ERROR de connexió: {exc}")
            driver.close()
            return 2
        print("Connectat.\n")

    errors = 0
    try:
        for path, statements in scripts:
            print(f"=== {path} ({len(statements)} sentències)")
            for k, statement in enumerate(statements, 1):
                if statement.startswith(":"):
                    print(f"  [{k}] (ordre del Browser, se salta) {statement.splitlines()[0]}")
                    continue
                print(f"  [{k}] {preview(statement)}")
                if args.dry_run:
                    continue
                start = time.perf_counter()
                try:
                    records, summary, keys = driver.execute_query(
                        statement, params, database_=database
                    )
                except Neo4jError as exc:
                    errors += 1
                    print(f"      ERROR {exc.code}: {exc.message}")
                    if not args.continue_on_error:
                        print("\nAturat al primer error (usa --continue-on-error per seguir).")
                        return 1
                    continue
                elapsed = (time.perf_counter() - start) * 1000
                print(f"      OK ({elapsed:.0f} ms)")
                print_counters(summary)
                print_records(records, keys)
            print()
    finally:
        if driver:
            driver.close()

    if errors:
        print(f"Acabat amb {errors} error(s).")
        return 1
    print("Fet." if not args.dry_run else "Dry-run acabat (no s'ha executat res).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
