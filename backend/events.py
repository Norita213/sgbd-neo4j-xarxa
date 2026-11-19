import uuid

from fastapi import APIRouter, HTTPException

from backend.db import run_query

from .app.queries import EVENT_TAIL
from .app.schemas import DAYS, EventIn

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", status_code=201)
def create_event(body: EventIn):
    """'Nova quedada'. El dia de la setmana es calcula a partir de la data i es
    creen els Slot (AT) de totes les hores que dura."""
    if body.community_id and not run_query(
        "MATCH (c:Community {id:$id}) RETURN c.id AS id", id=body.community_id
    ):
        raise HTTPException(404, "Comunitat no trobada")

    day = DAYS[body.date.weekday()]
    hour = body.start_time.hour
    end_hour = hour + body.duration_hours
    minutes = f"{body.start_time.minute:02d}"

    rows = run_query(
        """MATCH (p:Person {id:$organizer}), (a:Activity {name:$activity})
           MERGE (z:Zone {name:$zone})
           CREATE (e:Event {id:$id, title:$title, date:date($date),
                            startTime:$start, endTime:$end, place:$place,
                            description:$description, capacity:$capacity})
           CREATE (p)-[:ORGANIZES]->(e), (p)-[:ATTENDS]->(e),
                  (e)-[:OF_TYPE]->(a), (e)-[:IN]->(z)
           WITH e
           OPTIONAL MATCH (c:Community {id:$community_id})
           FOREACH (_ IN CASE WHEN c IS NULL THEN [] ELSE [1] END | CREATE (c)-[:HOSTS]->(e))
           WITH DISTINCT e
           UNWIND range($hour, $end_hour - 1) AS h
           MERGE (s:Slot {day:$day, hour:h})
           MERGE (e)-[:AT]->(s)
           RETURN DISTINCT e.id AS id""",
        organizer=body.organizer_id, activity=body.activity, zone=body.zone,
        id=str(uuid.uuid4()), title=body.title, date=body.date.isoformat(),
        start=f"{hour:02d}:{minutes}", end=f"{end_hour % 24:02d}:{minutes}",
        place=body.place, description=body.description, capacity=body.capacity,
        community_id=body.community_id, hour=hour, end_hour=end_hour, day=day,
    )
    if not rows:
        raise HTTPException(404, "Organitzador o activitat no trobats")
    return rows[0]


@router.get("")
def list_events(
    zone: str | None = None,
    activity: str | None = None,
    community_id: str | None = None,
    person_id: str | None = None,
):
    """Totes les quedades properes, amb filtres. `person_id` serveix per marcar `attending`."""
    return run_query(
        """MATCH (e:Event)-[:OF_TYPE]->(a:Activity), (e)-[:IN]->(z:Zone)
           WHERE ($zone IS NULL OR z.name = $zone)
             AND ($activity IS NULL OR a.name = $activity)
             AND ($community_id IS NULL OR EXISTS { (:Community {id:$community_id})-[:HOSTS]->(e) })
             AND (e.date IS NULL OR date(e.date) >= date())"""
        + EVENT_TAIL,
        zone=zone, activity=activity, community_id=community_id, viewer=person_id,
    )


@router.get("/{event_id}")
def event_detail(event_id: str, person_id: str | None = None):
    """'Detall de quedada': targeta + organitzador + qui hi va (amb les teves connexions marcades)."""
    cards = run_query(
        "MATCH (e:Event {id:$eid})" + EVENT_TAIL.replace("ORDER BY e.date, e.startTime", ""),
        eid=event_id, viewer=person_id,
    )
    if not cards:
        raise HTTPException(404, "Quedada no trobada")
    event = cards[0]
    organizer = run_query(
        "MATCH (o:Person)-[:ORGANIZES]->(:Event {id:$eid}) RETURN o.id AS id, o.name AS name",
        eid=event_id,
    )
    event["organizer"] = organizer[0] if organizer else None
    event["attendees"] = run_query(
        """MATCH (p:Person)-[:ATTENDS]->(:Event {id:$eid})
           RETURN p.id AS id, p.name AS name,
                  ($viewer IS NOT NULL AND EXISTS {
                      MATCH (v:Person {id:$viewer}) WHERE (v)-[:CONNECTED_WITH]-(p)
                  }) AS is_connection
           ORDER BY is_connection DESC, name""",
        eid=event_id, viewer=person_id,
    )
    event["slots"] = run_query(
        "MATCH (:Event {id:$eid})-[:AT]->(s:Slot) RETURN s.day AS day, s.hour AS hour ORDER BY hour",
        eid=event_id,
    )
    return event


@router.post("/{event_id}/attend/{person_id}")
def attend(event_id: str, person_id: str):
    """Botó 'M'hi apunto'. Respecta les places (capacity)."""
    rows = run_query(
        """MATCH (p:Person {id:$pid}), (e:Event {id:$eid})
           OPTIONAL MATCH (e)<-[:ATTENDS]-(x:Person)
           WITH p, e, count(x) AS n
           WHERE EXISTS { (p)-[:ATTENDS]->(e) } OR e.capacity IS NULL OR n < e.capacity
           MERGE (p)-[:ATTENDS]->(e)
           RETURN e.id AS event_id""",
        pid=person_id, eid=event_id,
    )
    if not rows:
        raise HTTPException(409, "La quedada està plena o la persona/quedada no existeix")
    return {"attending": True}


@router.delete("/{event_id}/attend/{person_id}")
def unattend(event_id: str, person_id: str):
    run_query(
        "MATCH (:Person {id:$pid})-[r:ATTENDS]->(:Event {id:$eid}) DELETE r",
        pid=person_id, eid=event_id,
    )
    return {"attending": False}
