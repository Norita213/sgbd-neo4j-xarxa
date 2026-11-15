"""Fragments de Cypher reutilitzats per les llistes de quedades.

Els prefixos defineixen `e` (les quedades candidates) i aquest tros final les
converteix en la 'targeta' que mostra l'app. Necessita el paràmetre $viewer
(id de qui mira, o None) per calcular `attending`.
"""

EVENT_TAIL = """
WITH DISTINCT e
MATCH (e)-[:OF_TYPE]->(a:Activity)
MATCH (e)-[:IN]->(z:Zone)
OPTIONAL MATCH (c:Community)-[:HOSTS]->(e)
OPTIONAL MATCH (e)<-[:ATTENDS]-(att:Person)
WITH e, a, z, c, count(DISTINCT att) AS participants, collect(DISTINCT att.id) AS attendee_ids
RETURN e.id AS id, e.title AS title, toString(e.date) AS date,
       e.startTime AS start_time, e.endTime AS end_time, e.place AS place,
       e.description AS description, e.capacity AS capacity,
       a.name AS activity, z.name AS zone, c.name AS community, c.id AS community_id,
       participants, coalesce($viewer IN attendee_ids, false) AS attending
ORDER BY e.date, e.startTime
"""
