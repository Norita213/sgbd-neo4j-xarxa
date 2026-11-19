import uuid

from fastapi import APIRouter, HTTPException

from backend.db import run_query

from ..queries import EVENT_TAIL
from ..schemas import CommunityIn

router = APIRouter(prefix="/communities", tags=["communities"])


@router.get("")
def search_communities(q: str | None = None, person_id: str | None = None):
    """Pantalla 'Comunitats' / 'Descobreix'. `q` cerca per nom, activitat o zona."""
    return run_query(
        """MATCH (c:Community)-[:ABOUT]->(a:Activity)
           OPTIONAL MATCH (c)-[:IN]->(z:Zone)
           WITH c, a, z
           WHERE $q IS NULL
              OR toLower(c.name) CONTAINS toLower($q)
              OR toLower(a.name) CONTAINS toLower($q)
              OR toLower(coalesce(z.name, '')) CONTAINS toLower($q)
           OPTIONAL MATCH (c)<-[:MEMBER_OF]-(m:Person)
           WITH c, a, z, count(m) AS members, collect(m.id) AS member_ids
           RETURN c.id AS id, c.name AS name, a.name AS activity, z.name AS zone, members,
                  coalesce($viewer IN member_ids, false) AS is_member
           ORDER BY members DESC, name""",
        q=q, viewer=person_id,
    )


@router.post("", status_code=201)
def create_community(body: CommunityIn):
    name = body.name.strip()
    "Comprova que no hi hagi cap comunitat amb el mateix nom (sense tenir en compte majúscules/minúscules)."
    if run_query("MATCH (c:Community) WHERE toLower(c.name) = toLower($name) RETURN c.id AS id", name=name):
        raise HTTPException(409, "Ja existeix una comunitat amb aquest nom")
    
    rows = run_query(
        """MATCH (a:Activity {name:$activity}), (creator:Person {id:$creator})
           MERGE (z:Zone {name:$zone})
           CREATE (c:Community {id:$id, name:$name})
           CREATE (c)-[:ABOUT]->(a), (c)-[:IN]->(z), (creator)-[:MEMBER_OF]->(c)
           RETURN c.id AS id, c.name AS name""",
        activity=body.activity, creator=body.creator_id, zone=body.zone,
        id=str(uuid.uuid4()), name=body.name,
    )
    if not rows:
        raise HTTPException(404, "Activitat o creador no trobats")
    return rows[0]


@router.get("/{community_id}")
def community_detail(community_id: str, person_id: str | None = None):
    rows = run_query(
        """MATCH (c:Community {id:$id})-[:ABOUT]->(a:Activity)
           OPTIONAL MATCH (c)-[:IN]->(z:Zone)
           OPTIONAL MATCH (c)<-[:MEMBER_OF]-(m:Person)
           RETURN c.id AS id, c.name AS name, a.name AS activity, z.name AS zone,
                  count(m) AS members, coalesce($viewer IN collect(m.id), false) AS is_member""",
        id=community_id, viewer=person_id,
    )
    if not rows:
        raise HTTPException(404, "Comunitat no trobada")
    return rows[0]


@router.get("/{community_id}/members")
def community_members(community_id: str):
    return run_query(
        """MATCH (p:Person)-[:MEMBER_OF]->(:Community {id:$id})
           OPTIONAL MATCH (p)-[:LIVES_IN]->(z:Zone)
           RETURN p.id AS id, p.name AS name, p.age AS age, z.name AS zone
           ORDER BY name""",
        id=community_id,
    )


@router.get("/{community_id}/events")
def community_events(community_id: str, person_id: str | None = None):
    """Pestanya 'Quedades' del detall de comunitat."""
    return run_query(
        """MATCH (:Community {id:$cid})-[:HOSTS]->(e:Event)
           WHERE e.date IS NULL OR date(e.date) >= date()\n"""
        + EVENT_TAIL,
        cid=community_id, viewer=person_id,
    )


@router.post("/{community_id}/members/{person_id}", status_code=201)
def join_community(community_id: str, person_id: str):
    """Botó 'Unir-se'."""
    rows = run_query(
        """MATCH (p:Person {id:$pid}), (c:Community {id:$cid})
           MERGE (p)-[:MEMBER_OF]->(c)
           RETURN c.id AS id""",
        pid=person_id, cid=community_id,
    )
    if not rows:
        raise HTTPException(404, "Persona o comunitat no trobades")
    return {"member": True}


@router.delete("/{community_id}/members/{person_id}")
def leave_community(community_id: str, person_id: str):
    run_query(
        "MATCH (:Person {id:$pid})-[r:MEMBER_OF]->(:Community {id:$cid}) DELETE r",
        pid=person_id, cid=community_id,
    )
    return {"member": False}
