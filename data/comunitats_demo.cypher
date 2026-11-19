// Dades fictícies per provar la pantalla de comunitats en una base de desenvolupament.
// Entra amb el correu comunitats.demo@example.test i uneix-te a una comunitat.

MERGE (correr:Activity {name: 'Córrer'})
MERGE (caminar:Activity {name: 'Caminar'})
MERGE (girona:Zone {name: 'Girona'})
MERGE (salt:Zone {name: 'Salt'})

MERGE (paula:Person {id: 'demo-comunitats-paula'})
ON CREATE SET paula.name = 'Paula (demo)', paula.email = 'comunitats.demo@example.test', paula.age = 22
MERGE (paula)-[:LIVES_IN]->(salt)
MERGE (laia:Person {id: 'demo-comunitats-laia'})
ON CREATE SET laia.name = 'Laia (demo)', laia.email = 'laia.comunitats@example.test', laia.age = 23
MERGE (laia)-[:LIVES_IN]->(girona)

MERGE (grupCorrer:Community {id: 'demo-comunitats-correr'})
ON CREATE SET grupCorrer.name = 'Córrer a Girona'
MERGE (grupCorrer)-[:ABOUT]->(correr)
MERGE (grupCorrer)-[:IN]->(girona)
MERGE (laia)-[:MEMBER_OF]->(grupCorrer)

MERGE (grupCaminar:Community {id: 'demo-comunitats-caminades'})
ON CREATE SET grupCaminar.name = 'Caminades a Salt'
MERGE (grupCaminar)-[:ABOUT]->(caminar)
MERGE (grupCaminar)-[:IN]->(salt);
