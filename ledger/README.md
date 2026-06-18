# Positive Proxy — Core Ledger Backend Engine

This is the core storage, computational logic, and API controller layer for Positive Proxy — a bill-making and fluid governance system. The service utilizes an asynchronous processing stack to manage downward-traceable vote audits and upward-anonymous proxy weight accumulation.

## 🛠️ Tech Stack Core
* **Framework:** FastAPI (Asynchronous Python REST API)
* **Database Driver:** PostgreSQL + `asyncpg` (Fully async connection pooling)
* **ORM:** SQLAlchemy 2.0 (Async Extension)
* **Data Validation:** Pydantic v2

---

## 🚀 Local Quickstart & Deployment

### 1. Environment Isolation
Ensure you are running Python 3.10+ within a localized virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Database Provisioning & PL/pgSQL Assembly
Create a local PostgreSQL instance named positive_proxy_db.

Create a .env file in the root of the /ledger directory matching your local database footprints:
```DATABASE_URL=postgresql+asyncpg://<username>:<password>@localhost:5432/positive_proxy_db```

Initialize the schema, triggers, and recursive network graph functions by piping the script from your root directory:
```bash
psql -d positive_proxy_db -f scripts/init_db.sql
```

### 3. Launching the Hot-Reload API Development Server
Run the Uvicorn engine from the root workspace directory:
```bash
uvicorn ledger.api.main:app --reload
```

## 🗺️ Key API Layer Structural Breakdown
`POST /proposals/issues`: Anchors systemic civic problems into the schema timeline.

`POST /proposals/`: Instantiates drafts or branches/forks an existing bill while preserving lineage links.

`POST /users/{user_id}/proxy`: Establishes global fallback paths or bill-isolated proxy mappings.

`POST /proposals/{proposal_id}/vote`: Explicit ballot log. Automatically overrides active proxy network inheritance.

`GET /proposals/{proposal_id}/trace/{user_id}`: Downward trace execution showing exactly how a vote propagated across trusted proxies.

`GET /audit/snapshot`: Computes standard cryptographic master SHA-256 state-hashing proofs for public watchdogs (AGPLv3 compliance verification).

## 🛡️ License

This module is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, version 3.
