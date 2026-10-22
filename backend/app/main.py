from fastapi import FastAPI
from app.db import run_query

app = FastAPI(title="Xarxa d'interessos")

@app.get("/persons")
def list_persons():
    return run_query(
        "MATCH (p:Person) RETURN p.name AS name, p.age AS age ORDER BY name"
    )

@app.get("/persons/{name}/recommendations")
def recommendations(name: str):
    return run_query("""
        MATCH (p:Person {name: $name})-[:LIKES]->(a:Activity)<-[:LIKES]-(o:Person),
              (p)-[:AVAILABLE_AT]->(s:Slot)<-[:AVAILABLE_AT]-(o),
              (p)-[:LIVES_IN]->(:Zone)-[:NEAR*0..1]-(:Zone)<-[:LIVES_IN]-(o)
        WHERE o <> p AND abs(p.age - o.age) <= 5
        RETURN o.name AS persona,
               collect(DISTINCT a.name) AS activitats,
               count(DISTINCT s) AS franges_compartides
        ORDER BY franges_compartides DESC
    """, name=name)