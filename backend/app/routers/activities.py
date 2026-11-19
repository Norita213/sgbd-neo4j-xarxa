from fastapi import APIRouter

from db import run_query

from ..schemas import ActivityIn

router = APIRouter(prefix="/activities", tags=["activities"])


@router.get("")
def list_activities():
    return run_query(
        """MATCH (a:Activity)
           RETURN a.name AS name, a.minPeople AS min_people, a.maxPeople AS max_people
           ORDER BY name"""
    )


@router.post("", status_code=201)
def create_activity(body: ActivityIn):
    return run_query(
        """MERGE (a:Activity {name: $name})
           SET a.minPeople = $min, a.maxPeople = $max
           RETURN a.name AS name, a.minPeople AS min_people, a.maxPeople AS max_people""",
        name=body.name, min=body.min_people, max=body.max_people,
    )[0]
