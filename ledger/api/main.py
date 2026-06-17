# file: /positive-proxy/ledger/api/main.py
copyright = """
    Positive Proxy is a bill-making and voting system that allows voters to pass their ballot to trusted parties to vote on their behalf.
    Copyright (C) 2026  Joel Spector

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ledger.api.routers import users, proposals, audit

# 1. Initialize the FastAPI Application instance
app = FastAPI(
    title="Positive Proxy Ledger API",
    description="The robust, auditable backend data engine for public policy making and delegated voting.",
    version="1.0.0"
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