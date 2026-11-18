// =====================================================================
// AFINIT - 01. Dades fixes (activitats, zones, veïnatge i franges)
// ---------------------------------------------------------------------
// Requereix haver executat abans 00_constraints.cypher.
// Idempotent: tot amb MERGE, es pot executar tantes vegades com calgui.
// =====================================================================

// ---------------------------------------------------------------------
// 1. Activitats (10)
// ---------------------------------------------------------------------
UNWIND ['Córrer', 'Escalada', 'Jocs de taula', 'Ciclisme', 'Pàdel',
        'Senderisme', 'Ioga', 'Fotografia', 'Natació', 'Futbol'] AS name
MERGE (:Activity {name: name});

// ---------------------------------------------------------------------
// 2. Zones (10)
// ---------------------------------------------------------------------
UNWIND ['Girona', 'Salt', 'Sarrià de Ter', 'Sant Gregori', 'Quart',
        'Vilablareix', 'Fornells de la Selva', 'Bescanó',
        'Sant Julià de Ramis', 'Celrà'] AS name
MERGE (:Zone {name: name});

// ---------------------------------------------------------------------
// 3. Veïnatge entre zones (NEAR) - PROPOSTA PENDENT DE REVISIÓ
// ---------------------------------------------------------------------
// Criteri: dues zones són NEAR si són municipis que limiten entre si.
// La relació es guarda en un sol sentit i es consulta sense direcció.
// El MERGE és sense direcció: si la relació ja existeix en qualsevol
// sentit no se'n crea cap altra (evita duplicats A->B i B->A).
UNWIND [
  // Girona limita amb tots els municipis de la llista excepte Bescanó
  ['Girona', 'Salt'],
  ['Girona', 'Sarrià de Ter'],
  ['Girona', 'Sant Gregori'],
  ['Girona', 'Quart'],
  ['Girona', 'Vilablareix'],
  ['Girona', 'Fornells de la Selva'],
  ['Girona', 'Sant Julià de Ramis'],
  ['Girona', 'Celrà'],
  // Salt
  ['Salt', 'Bescanó'],
  ['Salt', 'Vilablareix'],
  ['Salt', 'Sant Gregori'],
  // Sarrià de Ter
  ['Sarrià de Ter', 'Sant Julià de Ramis'],
  ['Sarrià de Ter', 'Celrà'],
  // Extres proposats (també limiten), a validar per l'equip
  ['Quart', 'Fornells de la Selva'],
  ['Vilablareix', 'Fornells de la Selva'],
  ['Sant Gregori', 'Bescanó']
] AS pair
MATCH (a:Zone {name: pair[0]})
MATCH (b:Zone {name: pair[1]})
MERGE (a)-[:NEAR]-(b);

// ---------------------------------------------------------------------
// 4. Franges horàries (Slot): 7 dies x 14 hores (8..21) = 98 nodes
// ---------------------------------------------------------------------
// id = "<dia>-<hora>", p. ex. "Dl-8", "Dg-21". hour = hora d'inici.
// El MERGE es fa per (day, hour) i després s'hi posa l'id: així s'aprofiten
// les franges que ja existien sense id (creades pel backend o per l'exemple
// antic) en lloc de duplicar-les, i les relacions que ja hi apunten es mantenen.
UNWIND ['Dl', 'Dm', 'Dc', 'Dj', 'Dv', 'Ds', 'Dg'] AS day
UNWIND range(8, 21) AS hour
MERGE (s:Slot {day: day, hour: hour})
SET s.id = day + '-' + toString(hour);
