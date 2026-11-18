import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

# .env a l'arrel del repositori (un nivell per sobre de backend/)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Accepta NEO4J_USER (el nom original) i NEO4J_USERNAME (el que fa servir el pla de treball / Aura)
_user = (os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME") or "neo4j").strip()
_password = os.getenv("NEO4J_PASSWORD", "").strip()
_uri = os.getenv("NEO4J_URI", "").strip()


def _make_driver():
    """Per a URIs xifrades (neo4j+s://) es fan servir els certificats arrel de
    certifi: a Windows, Python no sempre troba l'arrel que fa servir Aura i la
    connexió falla amb 'self-signed certificate in certificate chain'."""
    scheme, sep, rest = _uri.partition("://")
    if scheme.endswith("+s"):
        try:
            import certifi
            from neo4j import TrustCustomCAs
        except ImportError:
            pass
        else:
            return GraphDatabase.driver(
                f"{scheme[:-2]}{sep}{rest}",
                auth=(_user, _password),
                encrypted=True,
                trusted_certificates=TrustCustomCAs(certifi.where()),
            )
    return GraphDatabase.driver(_uri, auth=(_user, _password))


driver = _make_driver()


def run_query(query, **params):
    records, _, _ = driver.execute_query(query, params)
    return [record.data() for record in records]
