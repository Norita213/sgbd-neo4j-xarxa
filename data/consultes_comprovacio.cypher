// =====================================================================
// AFINIT - Consultes de comprovació de la càrrega (només lectura)
// ---------------------------------------------------------------------
// Des del Neo4j Browser / Aura Query: executar abans
//   :param personId => 'p-paula'
// Des de load.py:
//   python data/load.py --param personId=p-paula data/consultes_comprovacio.cypher
// =====================================================================

:param personId => 'p-paula';

// ---------------------------------------------------------------------
// 1. Recompte de nodes per etiqueta
//    Esperat (dades fixes + exemple): Activity 10, Zone 10, Slot 98,
//    Person 2, Event 1.
// ---------------------------------------------------------------------
MATCH (n)
UNWIND labels(n) AS label
RETURN label, count(*) AS total
ORDER BY label;

// ---------------------------------------------------------------------
// 2. Recompte de relacions per tipus
//    Esperat: NEAR 16, UNAVAILABLE_AT 19, LIKES 2, LIVES_IN 2,
//    CREATED 1, ATTENDS 1, OF_TYPE 1, IN 1, AT 1.
// ---------------------------------------------------------------------
MATCH ()-[r]->()
RETURN type(r) AS relacio, count(*) AS total
ORDER BY relacio;

// ---------------------------------------------------------------------
// 3. Restriccions creades (esperat: 7 de tipus UNIQUENESS)
// ---------------------------------------------------------------------
SHOW CONSTRAINTS YIELD name, type, labelsOrTypes, properties
RETURN name, type, labelsOrTypes, properties
ORDER BY name;

// ---------------------------------------------------------------------
// 4. Persones afins a la Paula
//    Afí = comparteix alguna activitat, viu a la mateixa zona o a una de
//    veïna, i té una edat semblant (±5 anys). S'ordena per activitats
//    en comú i per franges en què TOTS DOS estan disponibles
//    (franges on cap dels dos té UNAVAILABLE_AT).
//    Esperat: Joana, [Córrer], Salt, 85 franges comunes.
// ---------------------------------------------------------------------
MATCH (p:Person {id: $personId})-[:LIKES]->(a:Activity)<-[:LIKES]-(o:Person)
WHERE o <> p AND abs(p.age - o.age) <= 5
MATCH (p)-[:LIVES_IN]->(zp:Zone), (o)-[:LIVES_IN]->(zo:Zone)
WHERE zp = zo OR EXISTS { (zp)-[:NEAR]-(zo) }
WITH p, o, zo, collect(DISTINCT a.name) AS activitats
RETURN o.name AS persona,
       activitats,
       zo.name AS zona,
       COUNT {
         MATCH (s:Slot)
         WHERE NOT EXISTS { (p)-[:UNAVAILABLE_AT]->(s) }
           AND NOT EXISTS { (o)-[:UNAVAILABLE_AT]->(s) }
       } AS frangesComunes
ORDER BY size(activitats) DESC, frangesComunes DESC, persona;
