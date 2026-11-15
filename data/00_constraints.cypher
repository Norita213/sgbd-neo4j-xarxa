// =====================================================================
// AFINIT - 00. Restriccions d'unicitat (Neo4j 5)
// ---------------------------------------------------------------------
// S'han d'executar ABANS de carregar dades: cada restricció crea també
// un índex, i així els MERGE posteriors són ràpids i no generen duplicats.
// Idempotent: IF NOT EXISTS fa que es pugui tornar a executar sense error.
// =====================================================================

CREATE CONSTRAINT person_id_unique IF NOT EXISTS
FOR (p:Person) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT person_email_unique IF NOT EXISTS
FOR (p:Person) REQUIRE p.email IS UNIQUE;

CREATE CONSTRAINT event_id_unique IF NOT EXISTS
FOR (e:Event) REQUIRE e.id IS UNIQUE;

CREATE CONSTRAINT community_id_unique IF NOT EXISTS
FOR (c:Community) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT activity_name_unique IF NOT EXISTS
FOR (a:Activity) REQUIRE a.name IS UNIQUE;

CREATE CONSTRAINT zone_name_unique IF NOT EXISTS
FOR (z:Zone) REQUIRE z.name IS UNIQUE;

CREATE CONSTRAINT slot_id_unique IF NOT EXISTS
FOR (s:Slot) REQUIRE s.id IS UNIQUE;
