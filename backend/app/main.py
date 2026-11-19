import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from neo4j.exceptions import ServiceUnavailable, SessionExpired

from db import driver, run_query  # backend/db.py

from .routers import activities, auth, communities, events, persons, recommendations, zones

logger = logging.getLogger(__name__)
NEO4J_RETRY_DELAYS = (1, 2, 4, 8)


@asynccontextmanager
async def lifespan(app: FastAPI):
    max_attempts = len(NEO4J_RETRY_DELAYS) + 1
    try:
        for attempt in range(1, max_attempts + 1):
            try:
                await run_in_threadpool(driver.verify_connectivity)
            except (ServiceUnavailable, SessionExpired) as error:
                if attempt == max_attempts:
                    logger.error("No s'ha pogut connectar amb Neo4j després de %d intents.", max_attempts)
                    raise
                delay = NEO4J_RETRY_DELAYS[attempt - 1]
                logger.warning(
                    "Connexió amb Neo4j fallida (%d/%d). Nou intent d'aquí a %d s: %s",
                    attempt, max_attempts, delay, error,
                )
                await asyncio.sleep(delay)
            else:
                break
        yield
    finally:
        await run_in_threadpool(driver.close)


app = FastAPI(title="Afinit - xarxa d'interessos", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # frontend en desenvolupament
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(persons.router)
app.include_router(recommendations.router)
app.include_router(events.router)
app.include_router(communities.router)
app.include_router(activities.router)
app.include_router(zones.router)


# Frontend (HTML + JS simple), servit pel mateix servidor: http://localhost:8000/app/
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/app/")


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


@app.get("/health/data", tags=["health"])
def health_data():
    """Diagnòstic: quines dades encara no s'han adaptat amb data/migracio.cypher.
    Tot hauria de ser 0 (excepte comunitats sense zona, que és opcional)."""
    return run_query(
        """RETURN
             count { MATCH (p:Person) WHERE p.id IS NULL }          AS persons_without_id,
             count { MATCH (p:Person) WHERE p.email IS NULL }       AS persons_without_email,
             count { MATCH (e:Event) WHERE e.id IS NULL }           AS events_without_id,
             count { MATCH (c:Community) WHERE c.id IS NULL }       AS communities_without_id,
             count { MATCH (e:Event) WHERE e.date IS :: STRING }    AS events_with_text_date,
             count { MATCH (c:Community) WHERE NOT (c)-[:IN]->() }  AS communities_without_zone"""
    )[0]
