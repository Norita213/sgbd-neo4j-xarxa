from fastapi import APIRouter, Query

from db import run_query

from ..queries import EVENT_FIELDS, EVENT_TAIL
from ..schemas import DAYS
from .persons import require_person

router = APIRouter(prefix="/persons", tags=["recommendations"])

# La consulta del pla de treball: mateixa activitat + mateixa zona o zona NEAR
# + almenys una franja (Slot) compartida + diferència d'edat limitada.
PEOPLE_QUERY = """
MATCH (p:Person {id:$id})-[:LIKES]->(a:Activity)<-[:LIKES]-(o:Person)
WHERE o <> p
  AND (p.age IS NULL OR o.age IS NULL OR abs(p.age - o.age) <= $max_age_diff)
  AND ($include_connected OR NOT (p)-[:CONNECTED_WITH]-(o))
  AND ($activity IS NULL
       OR (EXISTS { (p)-[:LIKES]->(:Activity {name: $activity}) }
           AND EXISTS { (o)-[:LIKES]->(:Activity {name: $activity}) }))
MATCH (p)-[:LIVES_IN]->(zp:Zone)-[:NEAR*0..1]-(zo:Zone)<-[:LIVES_IN]-(o)
MATCH (p)-[:AVAILABLE_AT]->(s:Slot)<-[:AVAILABLE_AT]-(o)
WITH p, o, zo, zp, collect(DISTINCT a.name) AS activities, collect(DISTINCT s) AS slots
RETURN o.id AS id, o.name AS name, o.age AS age, zo.name AS zone,
       zo <> zp AS nearby_zone, EXISTS { (p)-[:CONNECTED_WITH]-(o) } AS connected, activities,
       [x IN slots | x {.day, .hour}] AS shared_slots,
       size(slots) AS shared_hours
ORDER BY size(activities) DESC, shared_hours DESC, nearby_zone, name, id
"""

FOR_YOU_QUERY = """
MATCH (p:Person {id:$viewer})-[:LIKES]->(:Activity)<-[:OF_TYPE]-(e:Event)
MATCH (p)-[:LIVES_IN]->(:Zone)-[:NEAR*0..1]-(:Zone)<-[:IN]-(e)
WHERE NOT (p)-[:ATTENDS]->(e)
  AND (e.date IS NULL OR date(e.date) >= date())
WITH DISTINCT p, e, date(e.date).dayOfWeek - 1 AS weekday,
     split(toString(e.startTime), ':') AS startTime,
     split(toString(e.endTime), ':') AS endTime
WITH p, e, weekday, toIntegerOrNull(startTime[0]) AS startHour,
     toIntegerOrNull(endTime[0]) AS endHour, toIntegerOrNull(endTime[1]) AS endMinute
// Les 20:30 ocupen part de la franja de les 20. Les 20:00 no.
WITH p, e, weekday, startHour,
     endHour + CASE WHEN endHour < startHour THEN 24 ELSE 0 END
             + CASE WHEN endMinute > 0 THEN 1 ELSE 0 END AS endExclusive,
     endMinute
WHERE CASE
  WHEN weekday IS NULL OR startHour IS NULL OR endExclusive IS NULL OR endMinute IS NULL THEN
    EXISTS { (e)-[:AT]->(:Slot) }
    AND NOT EXISTS { MATCH (e)-[:AT]->(s:Slot) WHERE NOT (p)-[:AVAILABLE_AT]->(s) }
  ELSE
    endExclusive > startHour AND NOT EXISTS {
      UNWIND range(startHour, endExclusive - 1) AS hour
      WITH hour, $days[(weekday + CASE WHEN hour >= 24 THEN 1 ELSE 0 END) % 7] AS day
      WHERE NOT EXISTS { (p)-[:AVAILABLE_AT]->(:Slot {day: day, hour: hour % 24}) }
    }
END
""" + EVENT_FIELDS + """
ORDER BY CASE WHEN EXISTS { (:Person {id:$viewer})-[:LIVES_IN]->(z) } THEN 0 ELSE 1 END,
         e.date, e.startTime, id
"""


@router.get("/{person_id}/recommendations")
def recommended_people(
    person_id: str,
    activity: str | None = None,
    max_age_diff: int = Query(5, ge=0, description="Diferència màxima d'edat"),
    include_connected: bool = False,
):
    """Pantalla 'Persones afins'. `activity` és el filtre dels xips (Córrer, Escalada...)."""
    require_person(person_id)
    return run_query(
        PEOPLE_QUERY, id=person_id, activity=activity,
        max_age_diff=max_age_diff, include_connected=include_connected,
    )


@router.get("/{person_id}/events/for-you")
def events_for_you(person_id: str):
    """Quedades 'Per a tu': activitat que t'agrada, a la teva zona o propera, i
    TOTES les hores de la quedada dins de la teva disponibilitat."""
    require_person(person_id)
    return run_query(FOR_YOU_QUERY, viewer=person_id, days=DAYS)


@router.get("/{person_id}/events/nearby")
def events_nearby(person_id: str):
    """Quedades 'Totes a prop': totes les de la teva zona."""
    require_person(person_id)
    return run_query(
        """MATCH (:Person {id:$viewer})-[:LIVES_IN]->(:Zone)<-[:IN]-(e:Event)
           WHERE e.date IS NULL OR date(e.date) >= date()\n"""
        + EVENT_TAIL,
        viewer=person_id,
    )


@router.get("/{person_id}/events/attending")
def events_attending(
    person_id: str,
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$", description="p.ex. 2026-10 (calendari)"),
    upcoming: bool = False,
):
    """Quedades on ja t'has apuntat ('Hi estàs apuntada' i calendari)."""
    require_person(person_id)
    return run_query(
        """MATCH (:Person {id:$viewer})-[:ATTENDS]->(e:Event)
           WHERE ($month IS NULL OR toString(e.date) STARTS WITH $month)
             AND (NOT $upcoming OR e.date IS NULL OR date(e.date) >= date())"""
        + EVENT_TAIL,
        viewer=person_id, month=month, upcoming=upcoming,
    )
