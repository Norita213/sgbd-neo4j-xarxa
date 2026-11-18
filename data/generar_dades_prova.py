"""Generador de dades de prova per a la demo d'AFINIT.

Ús (des de l'arrel del repositori, amb el venv activat):
    python data/generar_dades_prova.py --dry-run   # només mostra què crearia
    python data/generar_dades_prova.py             # ho escriu a Neo4j (Aura)

Crea persones, disponibilitat, connexions, comunitats i quedades (passades i futures)
coherents amb el model (docs/model.md). Requereix 00_constraints i 01_dades_fixes.

- Idempotent: llavor aleatòria fixa, dates fixes i ids UUID deterministes
  (uuid5 a partir del correu o del títol + data). Executar-lo dues vegades no
  duplica res: tot és MERGE.
- No modifica cap persona que ja existeixi (Paula, etc.): només crea persones
  noves (@example.com) i relacions entre elles. Les quedades noves sí que es poden
  apuntar a comunitats que ja existeixen (MEMBER_OF de persones noves).
"""

import argparse
import random
import sys
import uuid
from datetime import date, timedelta

sys.path.insert(0, __import__("os").path.dirname(__file__))
from load import ROOT, make_driver  # noqa: E402  (mateix directori)

SEED = 2026
NS = uuid.UUID("6f1c2a52-6d0e-4f7e-9a7b-2b8d6a1f0a11")  # espai de noms dels uuid5
BASE_MONDAY = date(2026, 11, 16)   # setmana de referència (fixa, perquè sigui idempotent)
WEEKS = range(-2, 4)                # 2 setmanes passades + la de referència + 3 futures
DAYS = ["Dl", "Dm", "Dc", "Dj", "Dv", "Ds", "Dg"]
HOURS = range(8, 22)

ZONES = ["Girona", "Salt", "Sarrià de Ter", "Sant Gregori", "Quart", "Vilablareix",
         "Fornells de la Selva", "Bescanó", "Sant Julià de Ramis", "Celrà"]
ZONE_WEIGHTS = [10, 5, 2, 2, 1, 2, 1, 1, 1, 1]
NEAR = [("Girona", z) for z in ["Salt", "Sarrià de Ter", "Sant Gregori", "Quart", "Vilablareix",
                                 "Fornells de la Selva", "Sant Julià de Ramis", "Celrà"]] + [
    ("Salt", "Bescanó"), ("Salt", "Vilablareix"), ("Salt", "Sant Gregori"),
    ("Sarrià de Ter", "Sant Julià de Ramis"), ("Sarrià de Ter", "Celrà"),
    ("Quart", "Fornells de la Selva"), ("Vilablareix", "Fornells de la Selva"),
    ("Sant Gregori", "Bescanó")]
ACTIVITIES = ["Córrer", "Escalada", "Jocs de taula", "Ciclisme", "Pàdel",
              "Senderisme", "Ioga", "Fotografia", "Natació", "Futbol"]

# Noms nous (no coincideixen amb les persones que ja hi ha: Paula, Joana, Clara, Laia, Marc, Miquel, Pol)
# Usuaris de l'equip: perfils fixos, connectats entre ells (nom, zona, activitats, edat)
TEAM = [
    ("Nour", "Girona", ["Córrer", "Escalada", "Fotografia"], 21),
    ("Lara", "Salt", ["Jocs de taula", "Ioga", "Córrer"], 21),
    ("Sara", "Girona", ["Pàdel", "Senderisme", "Córrer"], 21),
    ("Gemma", "Sarrià de Ter", ["Ciclisme", "Natació", "Jocs de taula"], 21),
]

NAMES = ["Aina", "Biel", "Carla", "David", "Elena", "Ferran", "Hugo", "Irene", "Jordi",
         "Júlia", "Lluc", "Marta", "Nil", "Núria", "Oriol", "Queralt", "Roger", "Toni",
         "Úrsula", "Víctor", "Xènia", "Arnau", "Berta", "Cesc", "Dolors", "Eric", "Fiona", "Guillem",
         "Helena", "Ignasi", "Jana", "Kevin", "Lídia", "Mireia", "Nadia", "Pau", "Rita", "Sergi"]

# Horaris tipus: franges en què NO poden (la resta són AVAILABLE_AT)
PROFILES = {
    "estudiant": lambda d, h: d < 5 and 8 <= h < 14,
    "feina": lambda d, h: d < 5 and 8 <= h < 17,
    "matins": lambda d, h: 8 <= h < 12,
    "flexible": lambda d, h: False,
}

COMMUNITIES = [
    ("Ciclistes del Gironès", "Ciclisme", "Girona", "Sortides de carretera i BTT cada cap de setmana."),
    ("Ioga a Salt", "Ioga", "Salt", "Sessions de ioga a l'aire lliure per a tots els nivells."),
    ("Pàdel Sant Gregori", "Pàdel", "Sant Gregori", "Busquem parella i rivals per jugar entre setmana."),
    ("Caminants de les Gavarres", "Senderisme", "Quart", "Rutes de muntanya pel Gironès."),
    ("Foto Girona", "Fotografia", "Girona", "Passejades fotogràfiques i quedades per compartir fotos."),
]
EXISTING_COMMUNITIES = ["Runners Girona", "Escalada Gironès", "Jocs de taula Girona"]

# (títol, activitat, lloc, zona, dia de la setmana 0=Dl, hora, durada, places, descripció)
TEMPLATES = [
    ("Rodatge suau pel Ter", "Córrer", "Pont de la Barca", "Girona", 0, 19, 1, 12, "Uns 6 km a ritme tranquil vora el Ter."),
    ("Sèries a la Devesa", "Córrer", "Parc de la Devesa", "Girona", 2, 19, 1, 10, "Escalfament i sèries curtes. Porta aigua!"),
    ("Sortida llarga per les Gavarres", "Córrer", "Font de la Pólvora", "Girona", 5, 9, 2, 15, "Uns 15 km de pista amb desnivell suau."),
    ("Bloc al rocòdrom", "Escalada", "Rocòdrom de Salt", "Salt", 1, 19, 2, 8, "Sessió de bloc. Hi ha peus de gat de lloguer."),
    ("Nit de jocs de taula", "Jocs de taula", "Cafè del Barri Vell", "Girona", 3, 20, 2, 10, "Portem Catan, Dixit i Carcassonne."),
    ("Volta per la Via Verda", "Ciclisme", "Inici de la Via Verda", "Salt", 5, 9, 3, 12, "Uns 40 km pla fins a Anglès i tornada."),
    ("Partit de pàdel 2x2", "Pàdel", "Pistes municipals", "Sant Gregori", 1, 19, 1, 4, "Nivell mitjà. Pista reservada."),
    ("Ruta a Sant Miquel", "Senderisme", "Aparcament de Quart", "Quart", 6, 9, 3, 15, "Ruta circular d'uns 12 km fins a Sant Miquel de les Gavarres."),
    ("Ioga al parc", "Ioga", "Parc de la Massana", "Salt", 5, 10, 1, 15, "Porta estoreta i roba còmoda."),
    ("Passejada fotogràfica pel Barri Vell", "Fotografia", "Plaça de la Catedral", "Girona", 5, 17, 2, 10, "Llum de tarda pels carrerons. Qualsevol càmera serveix."),
    ("Natació a Palau", "Natació", "Piscina de Palau", "Girona", 2, 20, 1, 8, "Entrenament lliure, cada qui al seu ritme."),
    ("Futbol 7 a Fontajau", "Futbol", "Camp de Fontajau", "Girona", 3, 20, 1, 14, "Partit amistós. Falten jugadors!"),
    ("Pedalada a Sarrià", "Ciclisme", "Plaça de l'Ajuntament", "Sarrià de Ter", 6, 10, 2, 10, "Volta tranquil·la pels voltants."),
    ("Escalada a la Pedra del Diable", "Escalada", "La Pedra del Diable", "Girona", 6, 10, 3, 6, "Via fàcil. Cal portar material propi."),
    ("Jocs de taula a Celrà", "Jocs de taula", "Biblioteca de Celrà", "Celrà", 4, 18, 2, 8, "Tarda de jocs cooperatius."),
]


def uid(*parts) -> str:
    return str(uuid.uuid5(NS, "|".join(map(str, parts))))


def build():
    rng = random.Random(SEED)
    near = {z: {z} for z in ZONES}
    for a, b in NEAR:
        near[a].add(b)
        near[b].add(a)

    # ---------- Persones ----------
    persons = []
    for name, zone, activities, age in TEAM:
        email = f"{name.lower()}@example.com"
        blocked = {(d, h) for d in range(7) for h in HOURS if PROFILES["estudiant"](d, h)}
        persons.append({
            "id": uid("person", email), "name": name, "email": email, "age": age,
            "zone": zone, "activities": activities,
            "available": [f"{DAYS[d]}-{h}" for d in range(7) for h in HOURS if (d, h) not in blocked],
        })
    team_ids = [p["id"] for p in persons]
    for name in NAMES:
        email = f"{name.lower().replace('ú', 'u').replace('í', 'i').replace('è', 'e')}@example.com"
        profile = rng.choice(list(PROFILES))
        blocked = {(d, h) for d in range(7) for h in HOURS if PROFILES[profile](d, h)}
        blocked |= {(rng.randrange(7), rng.choice(list(HOURS))) for _ in range(rng.randint(0, 4))}
        persons.append({
            "id": uid("person", email), "name": name, "email": email,
            "age": rng.randint(18, 40),
            "zone": rng.choices(ZONES, ZONE_WEIGHTS)[0],
            "activities": rng.sample(ACTIVITIES, rng.randint(1, 3)),
            "available": [f"{DAYS[d]}-{h}" for d in range(7) for h in HOURS if (d, h) not in blocked],
        })

    # ---------- Connexions (entre persones noves amb alguna activitat en comú) ----------
    connections = {tuple(sorted((a, b))) for i, a in enumerate(team_ids) for b in team_ids[i + 1:]}
    for _ in range(60):
        a, b = rng.sample(persons, 2)
        if set(a["activities"]) & set(b["activities"]):
            connections.add(tuple(sorted((a["id"], b["id"]))))
    connections = [{"a": a, "b": b, "since": str(BASE_MONDAY - timedelta(days=rng.randint(5, 90)))}
                   for a, b in sorted(connections)]

    # ---------- Comunitats ----------
    communities = [{"id": uid("community", n), "name": n, "activity": a, "zone": z, "description": d}
                   for n, a, z, d in COMMUNITIES]
    members = []
    for c in communities:
        for p in persons:
            if c["activity"] in p["activities"] and c["zone"] in near[p["zone"]] and rng.random() < 0.7:
                members.append({"pid": p["id"], "cid": c["id"], "since": str(BASE_MONDAY - timedelta(days=rng.randint(1, 60)))})
    by_activity_existing = {"Runners Girona": "Córrer", "Escalada Gironès": "Escalada", "Jocs de taula Girona": "Jocs de taula"}
    existing_members = [{"pid": p["id"], "name": name, "since": str(BASE_MONDAY - timedelta(days=rng.randint(1, 60)))}
                        for name in EXISTING_COMMUNITIES for p in persons
                        if by_activity_existing[name] in p["activities"] and rng.random() < 0.5]

    # ---------- Quedades ----------
    community_of = {c["activity"]: c for c in communities}
    member_set = {(m["pid"], m["cid"]) for m in members}
    events = []
    for week in WEEKS:
        for (title, act, place, zone, wd, hour, dur, cap, desc) in TEMPLATES:
            if rng.random() > 0.5:
                continue
            day = BASE_MONDAY + timedelta(weeks=week, days=wd)
            slots = [f"{DAYS[wd]}-{h}" for h in range(hour, hour + dur)]
            candidates = [p for p in persons
                          if act in p["activities"] and zone in near[p["zone"]]
                          and all(s in p["available"] for s in slots)]
            if not candidates:
                continue
            rng.shuffle(candidates)
            organizer, others = candidates[0], candidates[1:]
            attendees = [p["id"] for p in others[: rng.randint(0, min(len(others), cap - 1))]]
            community = community_of.get(act)
            hosts = community["id"] if community and (organizer["id"], community["id"]) in member_set and rng.random() < 0.6 else None
            events.append({
                "id": uid("event", title, day), "title": title, "description": desc,
                "date": str(day), "startTime": f"{hour:02d}:00", "endTime": f"{hour + dur:02d}:00",
                "place": place, "capacity": cap, "activity": act, "zone": zone, "slots": slots,
                "organizer": organizer["id"], "attendees": attendees, "community": hosts,
            })

    return persons, connections, communities, members, existing_members, events


QUERIES = {
    "persones": """
        UNWIND $rows AS r
        MERGE (p:Person {email: r.email})
        ON CREATE SET p.id = r.id, p.name = r.name, p.age = r.age, p.createdAt = datetime()
        WITH p, r WHERE p.id = r.id            // no toquem persones que ja existien
        MATCH (z:Zone {name: r.zone})
        MERGE (p)-[:LIVES_IN]->(z)
        WITH p, r
        UNWIND r.activities AS act
        MATCH (a:Activity {name: act})
        MERGE (p)-[:LIKES]->(a)""",
    "disponibilitat": """
        UNWIND $rows AS r
        MATCH (p:Person {id: r.id})
        UNWIND r.available AS sid
        MATCH (s:Slot {id: sid})
        MERGE (p)-[:AVAILABLE_AT]->(s)""",
    "connexions": """
        UNWIND $rows AS r
        MATCH (a:Person {id: r.a}), (b:Person {id: r.b})
        MERGE (a)-[c:CONNECTED_WITH]-(b)
        ON CREATE SET c.since = date(r.since)""",
    "comunitats": """
        UNWIND $rows AS r
        MERGE (c:Community {id: r.id})
        ON CREATE SET c.name = r.name, c.description = r.description
        WITH c, r
        MATCH (a:Activity {name: r.activity}), (z:Zone {name: r.zone})
        MERGE (c)-[:ABOUT]->(a)
        MERGE (c)-[:IN]->(z)""",
    "membres": """
        UNWIND $rows AS r
        MATCH (p:Person {id: r.pid}), (c:Community {id: r.cid})
        MERGE (p)-[m:MEMBER_OF]->(c)
        ON CREATE SET m.since = date(r.since)""",
    "membres de comunitats existents": """
        UNWIND $rows AS r
        MATCH (p:Person {id: r.pid}), (c:Community {name: r.name})
        MERGE (p)-[m:MEMBER_OF]->(c)
        ON CREATE SET m.since = date(r.since)""",
    "quedades": """
        UNWIND $rows AS r
        MATCH (org:Person {id: r.organizer}), (a:Activity {name: r.activity}), (z:Zone {name: r.zone})
        MERGE (e:Event {id: r.id})
        ON CREATE SET e.title = r.title, e.description = r.description, e.date = date(r.date),
                      e.startTime = r.startTime, e.endTime = r.endTime, e.place = r.place,
                      e.capacity = r.capacity, e.createdAt = datetime()
        MERGE (org)-[:ORGANIZES]->(e)
        MERGE (org)-[:ATTENDS]->(e)
        MERGE (e)-[:OF_TYPE]->(a)
        MERGE (e)-[:IN]->(z)
        WITH e, r
        UNWIND r.slots AS sid
        MATCH (s:Slot {id: sid})
        MERGE (e)-[:AT]->(s)""",
    "assistents": """
        UNWIND $rows AS r
        MATCH (e:Event {id: r.id})
        UNWIND r.attendees AS pid
        MATCH (p:Person {id: pid})
        MERGE (p)-[:ATTENDS]->(e)""",
    "quedades de comunitat": """
        UNWIND [r IN $rows WHERE r.community IS NOT NULL] AS r
        MATCH (c:Community {id: r.community}), (e:Event {id: r.id})
        MERGE (c)-[:HOSTS]->(e)""",
}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Genera dades de prova per a AFINIT")
    parser.add_argument("--dry-run", action="store_true", help="només mostra què crearia")
    args = parser.parse_args()

    persons, connections, communities, members, existing_members, events = build()
    future = [e for e in events if e["date"] >= str(date.today())]
    print(f"Persones noves: {len(persons)}  ({', '.join(p['name'] for p in persons[:8])}, ...)")
    print(f"AVAILABLE_AT: {sum(len(p['available']) for p in persons)}")
    print(f"Connexions: {len(connections)}")
    print(f"Comunitats noves: {len(communities)}  ({', '.join(c['name'] for c in communities)})")
    print(f"Membres: {len(members)} a comunitats noves + {len(existing_members)} a les existents")
    print(f"Quedades: {len(events)} ({len(future)} futures, {len(events) - len(future)} passades), "
          f"{sum(len(e['attendees']) for e in events)} assistents a més dels organitzadors, "
          f"{sum(1 for e in events if e['community'])} dins d'una comunitat")
    for e in sorted(events, key=lambda e: e["date"])[:6]:
        print(f"  - {e['date']} {e['startTime']} {e['title']} ({e['zone']}, {1 + len(e['attendees'])}/{e['capacity']})")
    print("  ...")

    if args.dry_run:
        print("\nDry-run: no s'ha escrit res.")
        return 0

    import os
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    driver = make_driver(os.getenv("NEO4J_URI"), os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
    data = {
        "persones": persons, "disponibilitat": persons, "connexions": connections,
        "comunitats": communities, "membres": members,
        "membres de comunitats existents": existing_members,
        "quedades": events, "assistents": events, "quedades de comunitat": events,
    }
    try:
        driver.verify_connectivity()
        for step, query in QUERIES.items():
            _, summary, _ = driver.execute_query(query, rows=data[step])
            c = summary.counters
            print(f"  {step}: {c.nodes_created} nodes i {c.relationships_created} relacions noves")
    finally:
        driver.close()
    print("Fet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
