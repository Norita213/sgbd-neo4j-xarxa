// =====================================================================
// AFINIT - Consultes de comprovació de la càrrega (només lectura)
// ---------------------------------------------------------------------
// Des del Neo4j Browser / Aura Query: executar abans
//   :param email => 'paula@example.com'
// Des de load.py:
//   python data\load.py --param email=paula@example.com data\consultes_comprovacio.cypher
// =====================================================================

:param email => 'paula@example.com';

// ---------------------------------------------------------------------
// 1. Recompte de nodes per etiqueta
//    Dades fixes: Activity 10, Zone 10, Slot 98.
// ---------------------------------------------------------------------
MATCH (n)
UNWIND labels(n) AS label
RETURN label, count(*) AS total
ORDER BY label;

// ---------------------------------------------------------------------
// 2. Recompte de relacions per tipus (dades fixes: NEAR 16)
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
// 4. Valors fora del catàleg o incomplets (esperat: cap fila)
// ---------------------------------------------------------------------
MATCH (s:Slot) WHERE s.id IS NULL
RETURN 'Slot sense id' AS problema, count(*) AS total
UNION ALL
MATCH (z:Zone)
WHERE NOT z.name IN ['Girona', 'Salt', 'Sarrià de Ter', 'Sant Gregori', 'Quart',
                     'Vilablareix', 'Fornells de la Selva', 'Bescanó',
                     'Sant Julià de Ramis', 'Celrà']
RETURN 'Zona fora del catàleg: ' + z.name AS problema, 1 AS total
UNION ALL
MATCH (a:Activity)
WHERE NOT a.name IN ['Córrer', 'Escalada', 'Jocs de taula', 'Ciclisme', 'Pàdel',
                     'Senderisme', 'Ioga', 'Fotografia', 'Natació', 'Futbol']
RETURN 'Activitat fora del catàleg: ' + a.name AS problema, 1 AS total;

// ---------------------------------------------------------------------
// 5. Persones afins a la Paula
//    Afí = comparteix alguna activitat, viu a la mateixa zona o a una de
//    veïna, té una edat semblant (±5 anys) i té alguna franja lliure en
//    comú. La franja comuna és un camí del graf:
//      (Paula)-[:AVAILABLE_AT]->(Slot)<-[:AVAILABLE_AT]-(altra persona)
//    Amb l'exemple inicial en una base de dades buida:
//    Joana, [Córrer], Salt, 85 franges comunes.
// ---------------------------------------------------------------------
MATCH (p:Person {email: $email})-[:LIKES]->(a:Activity)<-[:LIKES]-(o:Person)
WHERE o <> p AND abs(p.age - o.age) <= 5
MATCH (p)-[:LIVES_IN]->(zp:Zone), (o)-[:LIVES_IN]->(zo:Zone)
WHERE zp = zo OR EXISTS { (zp)-[:NEAR]-(zo) }
WITH p, o, zo, collect(DISTINCT a.name) AS activitats
MATCH (p)-[:AVAILABLE_AT]->(s:Slot)<-[:AVAILABLE_AT]-(o)
RETURN o.name AS persona,
       activitats,
       zo.name AS zona,
       count(s) AS frangesComunes
ORDER BY size(activitats) DESC, frangesComunes DESC, persona;
