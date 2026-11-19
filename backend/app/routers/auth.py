import hashlib
import hmac
import secrets
import uuid

from fastapi import APIRouter, HTTPException

from db import run_query

from ..schemas import LoginIn, RegisterIn
from .persons import set_activities_for

router = APIRouter(prefix="/auth", tags=["auth"])


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"pbkdf2_sha256$100000${salt}${dk.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        return False
    try:
        algo, iters, salt, dk_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iters))
        return hmac.compare_digest(dk.hex(), dk_hex)
    except ValueError:
        return False


def normalize_username(raw: str) -> str:
    username = raw.strip().lower()
    if not username or " " in username:
        raise HTTPException(422, "El nom d'usuari no pot estar buit ni tenir espais")
    return username


@router.post("/register", status_code=201)
def register(body: RegisterIn):
    """Crea el perfil (pas 1 del registre). Després el frontend crida
    PUT /persons/{id}/availability amb els horaris (pas 2)."""
    name = body.name.strip()
    surname = body.surname.strip()
    if not name or not surname:
        raise HTTPException(422, "Cal indicar el nom i els cognoms")

    username = normalize_username(body.username)
    if run_query("MATCH (p:Person {username:$username}) RETURN p.id AS id", username=username):
        raise HTTPException(409, "Aquest nom d'usuari ja està en ús")

    email = body.email.strip().lower() if body.email and body.email.strip() else None
    if email and run_query("MATCH (p:Person {email:$email}) RETURN p.id AS id", email=email):
        raise HTTPException(409, "Ja existeix un compte amb aquest correu")

    rows = run_query(
        """MATCH (z:Zone {name: $zone})
           CREATE (p:Person {
               id: $id,
               name: $name,
               surname: $surname,
               username: $username,
               passwordHash: $password_hash,
               age: $age,
               email: $email,
               createdAt: datetime()
           })-[:LIVES_IN]->(z)
           RETURN p.id AS id, p.name AS name, p.surname AS surname,
                  p.username AS username, p.age AS age, z.name AS zone""",
        id=str(uuid.uuid4()),
        name=name,
        surname=surname,
        username=username,
        password_hash=hash_password(body.password),
        age=body.age,
        email=email,
        zone=body.zone,
    )
    if not rows:
        raise HTTPException(422, f"La zona '{body.zone}' no existeix")

    person = rows[0]
    if body.activities:
        set_activities_for(person["id"], body.activities)
    person["activities"] = body.activities
    return person


@router.post("/login")
def login(body: LoginIn):
    """Comprova que el nom d'usuari o correu i la contrasenya coincideixin."""
    identifier = body.identifier.strip().lower()
    rows = run_query(
        """MATCH (p:Person)
           WHERE p.username = $identifier OR p.email = $identifier
           OPTIONAL MATCH (p)-[:LIVES_IN]->(z:Zone)
           RETURN p.id AS id, p.name AS name, p.surname AS surname,
                  p.username AS username, p.email AS email, p.age AS age, z.name AS zone,
                  p.passwordHash AS password_hash""",
        identifier=identifier,
    )
    if not rows or not verify_password(body.password, rows[0].pop("password_hash", None)):
        raise HTTPException(401, "Usuari, correu o contrasenya incorrectes")

    return rows[0]