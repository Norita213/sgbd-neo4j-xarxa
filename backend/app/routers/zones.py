from fastapi import APIRouter, HTTPException

from db import run_query

from ..schemas import NearIn, ZoneIn

router = APIRouter(prefix="/zones", tags=["zones"])


@router.get("")
def list_zones():
    return run_query(
        """MATCH (z:Zone)
           OPTIONAL MATCH (z)-[:NEAR]-(n:Zone)
           RETURN z.name AS name, collect(DISTINCT n.name) AS near
           ORDER BY name"""
    )


@router.post("", status_code=201)
def create_zone(body: ZoneIn):
    return run_query("MERGE (z:Zone {name:$name}) RETURN z.name AS name", name=body.name.strip())[0]


@router.post("/near")
def link_zones(body: NearIn):
    "No es poden connectar zones amb elles mateixes"
    if body.zone_a.strip() == body.zone_b.strip():
        raise HTTPException(400, "No es pot enllaçar una zona amb ella mateixa")
    rows = run_query(
        """MATCH (a:Zone {name:$a}), (b:Zone {name:$b})
           MERGE (a)-[:NEAR]-(b)
           RETURN a.name AS zone_a, b.name AS zone_b""",
        a=body.zone_a, b=body.zone_b,
    )
    if not rows:
        raise HTTPException(404, "Alguna de les zones no existeix")
    return rows[0]
