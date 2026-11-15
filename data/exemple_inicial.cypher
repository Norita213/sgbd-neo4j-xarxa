// =====================================================================
// AFINIT - Exemple inicial: Paula (usuària de la demo) i Joana
// ---------------------------------------------------------------------
// Requereix 00_constraints.cypher i 01_dades_fixes.cypher (activitats,
// zones i les 98 franges Slot ja creades).
// Idempotent: MERGE per id i ON CREATE SET per a la resta de propietats.
// Disponibilitat: guardem només quan NO poden (UNAVAILABLE_AT).
// =====================================================================

// ---------------------------------------------------------------------
// Persones
// ---------------------------------------------------------------------
MERGE (paula:Person {id: 'p-paula'})
ON CREATE SET paula.name = 'Paula',
              paula.age = 22,
              paula.email = 'paula@afinit.cat',
              paula.createdAt = datetime();

MERGE (joana:Person {id: 'p-joana'})
ON CREATE SET joana.name = 'Joana',
              joana.age = 21,
              joana.email = 'joana@afinit.cat',
              joana.createdAt = datetime();

// ---------------------------------------------------------------------
// Interessos i zona
// ---------------------------------------------------------------------
MATCH (paula:Person {id: 'p-paula'}), (joana:Person {id: 'p-joana'})
MATCH (correr:Activity {name: 'Córrer'})
MATCH (girona:Zone {name: 'Girona'}), (salt:Zone {name: 'Salt'})
MERGE (paula)-[:LIKES]->(correr)
MERGE (joana)-[:LIKES]->(correr)
MERGE (paula)-[:LIVES_IN]->(girona)
MERGE (joana)-[:LIVES_IN]->(salt);

// ---------------------------------------------------------------------
// No disponibilitat de la Paula
//   Dl-Dv de 8 a 9h (hour 8) i de 13 a 14h (hour 13), i Dv de 19 a 20h.
//   Total: 5 x 2 + 1 = 11 franges.
// ---------------------------------------------------------------------
MATCH (paula:Person {id: 'p-paula'})
UNWIND ['Dl-8',  'Dm-8',  'Dc-8',  'Dj-8',  'Dv-8',
        'Dl-13', 'Dm-13', 'Dc-13', 'Dj-13', 'Dv-13',
        'Dv-19'] AS slotId
MATCH (s:Slot {id: slotId})
MERGE (paula)-[:UNAVAILABLE_AT]->(s);

// ---------------------------------------------------------------------
// No disponibilitat de la Joana
//   Dl-Dv de 8 a 9h, Dj de 19 a 20h i Dv de 19 a 21h. Total: 8 franges.
// ---------------------------------------------------------------------
MATCH (joana:Person {id: 'p-joana'})
UNWIND ['Dl-8', 'Dm-8', 'Dc-8', 'Dj-8', 'Dv-8',
        'Dj-19', 'Dv-19', 'Dv-20'] AS slotId
MATCH (s:Slot {id: slotId})
MERGE (joana)-[:UNAVAILABLE_AT]->(s);

// ---------------------------------------------------------------------
// Una quedada creada per la Paula (dijous 12/11/2026 a les 19h, Girona)
// ---------------------------------------------------------------------
MATCH (paula:Person {id: 'p-paula'})
MATCH (correr:Activity {name: 'Córrer'})
MATCH (girona:Zone {name: 'Girona'})
MATCH (dj19:Slot {id: 'Dj-19'})
MERGE (e:Event {id: 'e-quedada-correr'})
ON CREATE SET e.title = 'Quedada per córrer',
              e.description = 'Volta tranquil·la de 5 km per la Devesa.',
              e.date = date('2026-11-12'),
              e.hour = 19,
              e.place = 'Parc de la Devesa',
              e.capacity = 10,
              e.createdAt = datetime()
MERGE (paula)-[:CREATED]->(e)
MERGE (paula)-[:ATTENDS]->(e)
MERGE (e)-[:OF_TYPE]->(correr)
MERGE (e)-[:IN]->(girona)
MERGE (e)-[:AT]->(dj19);
