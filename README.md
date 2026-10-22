# Xarxa d'interessos amb Neo4j

Projecte de l'assignatura de Sistemes de Gestió de Bases de Dades (UdG).
Aplicació per connectar persones amb interessos, horaris i zona en comú,
i organitzar quedades i comunitats.

## Com arrencar-ho

1. Copiar `.env.example` a `.env` i posar-hi la contrasenya.
2. Arrencar Neo4j: `docker compose up -d`
3. Obrir http://localhost:7474 i executar `data/exemple_inicial.cypher`.
4. Arrencar el backend des de la carpeta `backend`:
   - `python -m venv venv`
   - `venv\Scripts\activate`
   - `pip install -r requirements.txt`
   - `uvicorn app.main:app --reload`
5. Documentació de l'API a http://localhost:8000/docs

## Equip

- Nom 1
- Nom 2
- Nom 3
- Nom 4
