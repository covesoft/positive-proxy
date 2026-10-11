# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Joel Spector

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from ledger.api.database import initialize_db_schema
from ledger.api.routers import users, proposals, audit

@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs EXACTLY once when Render wakes the app up
    await initialize_db_schema()
    yield
    # Cleanup logic on shutdown goes here if necessary

# 1. Initialize the FastAPI Application instance
app = FastAPI(
    title="Positive Proxy Ledger API",
    description="The robust, auditable backend data engine for public policy making and delegated voting.",
    version="1.0.1",
    lifespan=lifespan
)

# 2. Add Security & Middleware (Essential for connecting to your future Webapp frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production to point to your specific frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Mount the Core Architecture Pipelines
app.include_router(users.router)
app.include_router(proposals.router)
app.include_router(audit.router)

# 4. Root Health Check Endpoint
@app.get("/", tags=["system"])
async def root_health_check():
    return {
        "status": "healthy",
        "service": "Positive Proxy Ledger Backend",
        "architecture": "Asynchronous Core Engine",
        "license": "AGPLv3"
    }

### EOF: /positive-proxy/ledger/api/main.py ###