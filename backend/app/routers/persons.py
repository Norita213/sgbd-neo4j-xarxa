from fastapi import APIRouter, HTTPException

from backend.db import run_query

from ..schemas import DAYS, AvailabilityIn, PersonUpdate

router = APIRouter(prefix="/persons", tags=["persons"])


def require_person(person_id: str) -> None:
    if not run_query("MATCH (p:Person {id:$id}) RETURN p.id AS id", id=person_id):
        raise HTTPException(404, "Persona no trobada")


def set_activities_for(person_id: str, names: list[str]) -> int:
    """Substitueix els LIKES de la persona. Les activitats han d'existir."""
    rows = run_query(
        """MATCH (p:Person {id:$id})
           OPTIONAL MATCH (p)-[r:LIKES]->()
           DELETE r
           WITH DISTINCT p
           UNWIND $names AS n
           MATCH (a:Activity {name: n})
           MERGE (p)-[:LIKES]->(a)
           RETURN count(a) AS linked""",
        id=person_id, names=names,
    )
    return rows[0]["linked"] if rows else 0


@router.get("")
def list_persons():
    return run_query(
        """MATCH (p:Person)
           OPTIONAL MATCH (p)-[:LIVES_IN]->(z:Zone)
           RETURN p.id AS id, p.name AS name, p.age AS age, p.email AS email, z.name AS zone
           ORDER BY name"""
    )


@router.get("/{person_id}")
def get_profile(person_id: str):
    """Pantalla 'El meu perfil': dades, activitats, comunitats i comptadors."""
    rows = run_query(
        """MATCH (p:Person {id:$id})
           OPTIONAL MATCH (p)-[:LIVES_IN]->(z:Zone)
           OPTIONAL MATCH (p)-[:LIKES]->(a:Activity)
           WITH p, z, collect(DISTINCT a.name) AS activities
           OPTIONAL MATCH (p)-[:CONNECTED_WITH]-(c:Person)
           WITH p, z, activities, count(DISTINCT c) AS connections
           OPTIONAL MATCH (p)-[:ATTENDS]->(e:Event)
           WITH p, z, activities, connections, count(DISTINCT e) AS events
           OPTIONAL MATCH (p)-[:MEMBER_OF]->(cm:Community)
           RETURN p.id AS id, p.name AS name, p.age AS age, p.email AS email, z.name AS zone,
                  activities, connections, events,
                  collect(DISTINCT cm.name) AS communities""",
        id=person_id,
    )
    if not rows:
        raise HTTPException(404, "Persona no trobada")
    profile = rows[0]
    profile["communities_count"] = len(profile["communities"])
    raw_slots = run_query(
        """MATCH (:Person {id:$id})-[:AVAILABLE_AT]->(s:Slot)
           RETURN s.day AS day, s.hour AS hour""",
        id = person_id,
    )
    profile["available_slots"] = sorted(
        raw_slots,
        key = lambda x: (DAYS.index(x["day"]) if x["day"] in DAYS else 99, x["hour"]),
    )
    return profile


@router.put("/{person_id}")
def update_profile(person_id: str, body: PersonUpdate):
    """'Editar perfil': nom, edat, zona i activitats (tot opcional)."""
    require_person(person_id)

    if body.email is not None:
        clash = run_query(
            "MATCH (p:Person {email:$email}) WHERE p.id <> $id RETURN p.id AS id",
            email = body.email, id = person_id,
        )
        if clash:
            raise HTTPException(409, "Ja existeix un compte amb aquest correu")

    if body.zone is not None:
        if not run_query(
            "MATCH (z:Zone {name:$zone}) RETURN z.name AS name", zone = body.zone):
                raise HTTPException(400, "La zona indicada no existeix")
        run_query(
            """MATCH (p:person {id:$id}), (z:Zone {name:$name})
                OPTIONAL MATCH (p)-[r:LIVES_IN]->()
                DELETE r
                MERGE (p)-[:LIVES_IN]->(z)""",
            id = person_id, name = body.zone,
        )   

    run_query(
        """MATCH (p:Person {id:$id})
           SET p.name  = coalesce($name, p.name),
               p.age   = coalesce($age, p.age),
               p.email = coalesce($email, p.email)""",
        id=person_id, name=body.name, age=body.age, email=body.email,
    )

    if body.activities is not None:
        set_activities_for(person_id, body.activities)
    return get_profile(person_id)


@router.put("/{person_id}/availability")
def set_availability(person_id: str, body: AvailabilityIn):
    """Substitueix AVAILABLE_AT. Accepta rangs de 'disponible' o, com a la maqueta,
    de 'NO disponible' (aleshores es calcula el complement entre day_start i day_end)."""
    require_person(person_id)
    given = {(s.day, h) for s in body.slots for h in range(s.from_hour, s.to_hour)}
    if body.mode == "available":
        chosen = given
    else:
        grid = {(d, h) for d in DAYS for h in range(body.day_start, body.day_end)}
        chosen = grid - given
    slots = [{"day": d, "hour": h} for d, h in sorted(chosen, key=lambda x: (DAYS.index(x[0]), x[1]))]
    rows = run_query(
        """MATCH (p:Person {id:$id})
           OPTIONAL MATCH (p)-[r:AVAILABLE_AT]->()
           DELETE r
           WITH DISTINCT p
           UNWIND $slots AS sl
           MERGE (s:Slot {day: sl.day, hour: sl.hour})
           MERGE (p)-[:AVAILABLE_AT]->(s)
           RETURN count(DISTINCT s) AS slots""",
        id=person_id, slots=slots,
    )
    return {"hourly_slots": rows[0]["slots"] if rows else 0}


# ---------- Connexions (CONNECTED_WITH, immediates) ----------
@router.get("/{person_id}/connections")
def list_connections(person_id: str):
    require_person(person_id)
    return run_query(
        """MATCH (:Person {id:$id})-[:CONNECTED_WITH]-(c:Person)
           OPTIONAL MATCH (c)-[:LIVES_IN]->(z:Zone)
           RETURN c.id AS id, c.name AS name, c.age AS age, z.name AS zone
           ORDER BY name""",
        id=person_id,
    )


@router.post("/{person_id}/connections/{other_id}", status_code=201)
def connect(person_id: str, other_id: str):
    """Botó 'Connectar'."""
    if person_id == other_id:
        raise HTTPException(400, "No et pots connectar amb tu mateix")
    rows = run_query(
        """MATCH (a:Person {id:$a}), (b:Person {id:$b})
           MERGE (a)-[:CONNECTED_WITH]-(b)
           RETURN b.id AS id, b.name AS name""",
        a=person_id, b=other_id,
    )
    if not rows:
        raise HTTPException(404, "Persona no trobada")
    return rows[0]


@router.delete("/{person_id}/connections/{other_id}")
def disconnect(person_id: str, other_id: str):
    run_query(
        "MATCH (:Person {id:$a})-[r:CONNECTED_WITH]-(:Person {id:$b}) DELETE r",
        a=person_id, b=other_id,
    )
    return {"disconnected": True}


# ---------- Les teves comunitats ----------
@router.get("/{person_id}/communities")
def my_communities(person_id: str):
    require_person(person_id)
    return run_query(
        """MATCH (:Person {id:$id})-[:MEMBER_OF]->(c:Community)-[:ABOUT]->(a:Activity)
           OPTIONAL MATCH (c)-[:IN]->(z:Zone)
           OPTIONAL MATCH (c)<-[:MEMBER_OF]-(m:Person)
           WITH c, a, z, count(DISTINCT m) AS members
           OPTIONAL MATCH (c)-[:HOSTS]->(e:Event) WHERE e.date IS NULL OR date(e.date) >= date()
           RETURN c.id AS id, c.name AS name, a.name AS activity, z.name AS zone,
                  members, count(DISTINCT e) AS upcoming_events
           ORDER BY name""",
        id=person_id,
    )
