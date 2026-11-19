import uuid

from fastapi import APIRouter, HTTPException

from backend.db import run_query

from ..schemas import LoginIn, RegisterIn
from .persons import set_activities_for

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201)
def register(body: RegisterIn):
    """Crea el perfil (pas 1 del registre). Després el frontend crida
    PUT /persons/{id}/availability amb els horaris (pas 2)."""
    if run_query("MATCH (p:Person {email:$email}) RETURN p.id AS id", email=body.email.strip().lower()):
        raise HTTPException(409, "Ja existeix un compte amb aquest correu")
    rows = run_query(
        """MERGE (z:Zone {name: $zone})
           CREATE (p:Person {id: $id, name: $name, age: $age, email: $email})-[:LIVES_IN]->(z)
           RETURN p.id AS id, p.name AS name, p.age AS age, p.email AS email, z.name AS zone""",
        id=str(uuid.uuid4()), name=body.name, age=body.age, email=body.email.strip().lower(), zone=body.zone,
    )
    if not rows:
        raise HTTPException(500, "La zona indicada no existeix")

    person = rows[0]
    if body.activities:
        set_activities_for(person["id"], body.activities)
    person["activities"] = body.activities
    return person


"TO DO: afegir autenticació real amb JWT i contrasenya. Per ara només es comprova que el correu existeix."
@router.post("/login")
def login(body: LoginIn):
    """Login simulat: només comprova que el correu existeix i retorna l'id."""
    rows = run_query(
        """MATCH (p:Person {email:$email})
           OPTIONAL MATCH (p)-[:LIVES_IN]->(z:Zone)
           RETURN p.id AS id, p.name AS name, p.age AS age, p.email AS email, z.name AS zone""",
        email=body.email.strip().lower(),
    )
    if not rows:
        raise HTTPException(404, "No hi ha cap compte amb aquest correu")
    return rows[0]
