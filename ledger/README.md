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
