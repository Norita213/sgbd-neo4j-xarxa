# Xarxa d'interessos amb Neo4j

Projecte de l'assignatura de Sistemes de Gestió de Bases de Dades (UdG).
Aplicació per connectar persones amb interessos, horaris i zona en comú,
i organitzar quedades i comunitats.

## Com arrencar-ho

La base de dades és una única instància de **Neo4j AuraDB** al núvol, compartida per tot l'equip
(no fem servir Neo4j en local). Model de dades: [`docs/model.md`](docs/model.md).

1. Copiar `.env.example` a `.env` a l'arrel del repositori (no es puja a Git) i posar-hi les credencials d'Aura:
   ```
   NEO4J_URI=neo4j+s://XXXXXXXX.databases.neo4j.io
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=...
   ```
2. Crear l'entorn de Python a l'arrel (PowerShell):
   - `py -m venv .venv`
   - `.\.venv\Scripts\Activate.ps1`
   - `pip install -r backend\requirements.txt`
3. Carregar l'estructura i les dades fixes a Aura (només cal fer-ho una vegada per a tot l'equip;
   els scripts són idempotents):
   - `python data\load.py data\00_constraints.cypher data\01_dades_fixes.cypher data\exemple_inicial.cypher`
   - Comprovar-ho: `python data\load.py --param personId=p-paula data\consultes_comprovacio.cypher`
4. Arrencar el backend des de la carpeta `backend`: `uvicorn app.main:app --reload`
5. Documentació de l'API a http://localhost:8000/docs

## Equip

- Nom 1
- Nom 2
- Nom 3
- Nour Boudad
