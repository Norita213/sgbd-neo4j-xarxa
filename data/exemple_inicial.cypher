// Activitat i zones
MERGE (correr:Activity {name:'Córrer'})
MERGE (girona:Zone {name:'Girona'})
MERGE (salt:Zone {name:'Salt'})
MERGE (girona)-[:NEAR]-(salt)

// Franges horàries
MERGE (dl:Slot {day:'Dl', hour:19})
MERGE (dm:Slot {day:'Dm', hour:19})
MERGE (dc:Slot {day:'Dc', hour:19})
MERGE (dj:Slot {day:'Dj', hour:19})

// Persones
MERGE (paula:Person {name:'Paula', age:22})
MERGE (joana:Person {name:'Joana', age:21})
MERGE (paula)-[:LIKES]->(correr)
MERGE (joana)-[:LIKES]->(correr)
MERGE (paula)-[:LIVES_IN]->(girona)
MERGE (joana)-[:LIVES_IN]->(salt)
MERGE (paula)-[:AVAILABLE_AT]->(dl)
MERGE (paula)-[:AVAILABLE_AT]->(dm)
MERGE (paula)-[:AVAILABLE_AT]->(dc)
MERGE (paula)-[:AVAILABLE_AT]->(dj)
MERGE (joana)-[:AVAILABLE_AT]->(dl)
MERGE (joana)-[:AVAILABLE_AT]->(dm)
MERGE (joana)-[:AVAILABLE_AT]->(dc)

// Una quedada
MERGE (e:Event {title:'Quedada per córrer'})
MERGE (e)-[:OF_TYPE]->(correr)
MERGE (e)-[:IN]->(girona)
MERGE (e)-[:AT]->(dj)
