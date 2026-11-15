import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

# Accepta NEO4J_USER (el nom original) i NEO4J_USERNAME (el que fa servir el pla de treball / Aura)
_user = (os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME") or "neo4j").strip()

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI", "").strip(),
    auth=(_user, os.getenv("NEO4J_PASSWORD", "").strip()),
)

def run_query(query, **params):
    records, _, _ = driver.execute_query(query, params)
    return [record.data() for record in records]
