// =====================================================================
// AFINIT - Exemple inicial: Paula (usuària de la demo) i Joana
// ---------------------------------------------------------------------
// Requereix 00_constraints.cypher i 01_dades_fixes.cypher.
//
// Aquest script NOMÉS OMPLE EL QUE FALTA i no modifica res que ja existeixi:
//  - Les persones es busquen per email (únic). Si no existeixen, es creen
//    amb un id UUID, igual que fa el backend.
//  - Zona, interessos i disponibilitat només s'afegeixen si la persona
//    encara no en té cap.
//  - La quedada només es crea si no n'hi ha cap amb el mateix títol.
// Així es pot executar contra Aura sense tocar la Paula que ja hi ha,
// i serveix per reconstruir la demo en una base de dades buida.
// =====================================================================

// ---------------------------------------------------------------------
// Persones
// ---------------------------------------------------------------------
MERGE (paula:Person {email: 'paula@example.com'})
ON CREATE SET paula.id = randomUUID(),
              paula.name = 'Paula',
              paula.age = 22,
              paula.createdAt = datetime();

MERGE (joana:Person {email: 'joana@example.com'})
ON CREATE SET joana.id = randomUUID(),
              joana.name = 'Joana',
              joana.age = 21,
              joana.createdAt = datetime();

// ---------------------------------------------------------------------
// Zona on viuen (només si encara no en tenen)
// ---------------------------------------------------------------------
UNWIND [['paula@example.com', 'Girona'],
        ['joana@example.com', 'Salt']] AS row
MATCH (p:Person {email: row[0]})
WHERE NOT EXISTS { (p)-[:LIVES_IN]->(:Zone) }
MATCH (z:Zone {name: row[1]})
MERGE (p)-[:LIVES_IN]->(z);

// ---------------------------------------------------------------------
// Interessos (només si encara no en tenen)
// ---------------------------------------------------------------------
UNWIND [['paula@example.com', 'Córrer'],
        ['joana@example.com', 'Córrer']] AS row
MATCH (p:Person {email: row[0]})
WHERE NOT EXISTS { (p)-[:LIKES]->(:Activity) }
MATCH (a:Activity {name: row[1]})
MERGE (p)-[:LIKES]->(a);

// ---------------------------------------------------------------------
// Disponibilitat (només si encara no en tenen)
// Guardem les franges en què POT quedar (AVAILABLE_AT): totes les 98
// menys les que la persona ha marcat com a NO disponibles.
//   Paula NO pot: Dl-Dv de 8 a 9h i de 13 a 14h, i Dv de 19 a 20h
//                 (11 franges) -> 87 AVAILABLE_AT.
//   Joana NO pot: Dl-Dv de 8 a 9h, Dj de 19 a 20h i Dv de 19 a 21h
//                 (8 franges) -> 90 AVAILABLE_AT.
// ---------------------------------------------------------------------
UNWIND [
  {email: 'paula@example.com',
   unavailable: ['Dl-8', 'Dm-8', 'Dc-8', 'Dj-8', 'Dv-8',
                 'Dl-13', 'Dm-13', 'Dc-13', 'Dj-13', 'Dv-13', 'Dv-19']},
  {email: 'joana@example.com',
   unavailable: ['Dl-8', 'Dm-8', 'Dc-8', 'Dj-8', 'Dv-8',
                 'Dj-19', 'Dv-19', 'Dv-20']}
] AS row
MATCH (p:Person {email: row.email})
WHERE NOT EXISTS { (p)-[:AVAILABLE_AT]->(:Slot) }
MATCH (s:Slot)
WHERE NOT s.id IN row.unavailable
MERGE (p)-[:AVAILABLE_AT]->(s);

// ---------------------------------------------------------------------
// Una quedada organitzada per la Paula
// (dijous 12/11/2026 de 19 a 20h, Girona). Només si no existeix.
// ---------------------------------------------------------------------
MATCH (paula:Person {email: 'paula@example.com'})
WHERE NOT EXISTS { (:Event {title: 'Quedada per córrer'}) }
MATCH (correr:Activity {name: 'Córrer'})
MATCH (girona:Zone {name: 'Girona'})
MATCH (dj19:Slot {id: 'Dj-19'})
CREATE (e:Event {id: randomUUID(),
                 title: 'Quedada per córrer',
                 description: 'Volta tranquil·la de 5 km per la Devesa.',
                 date: date('2026-11-12'),
                 startTime: '19:00',
                 endTime: '20:00',
                 place: 'Parc de la Devesa',
                 capacity: 10,
                 createdAt: datetime()})
CREATE (paula)-[:ORGANIZES]->(e),
       (paula)-[:ATTENDS]->(e),
       (e)-[:OF_TYPE]->(correr),
       (e)-[:IN]->(girona),
       (e)-[:AT]->(dj19);
