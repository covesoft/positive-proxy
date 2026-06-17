# file: /positive-proxy/ledger/api/routers/audit.py
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

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from ledger.api.database import get_db
from ledger.api.services.audit import generate_state_snapshot_hash, verify_proposal_integrity

router = APIRouter(prefix="/audit", tags=["audit"])

@router.get("/snapshot")
async def get_ledger_snapshot(db: AsyncSession = Depends(get_db)):
    """
    Public Verification Endpoint. Generates a master cryptographic block hash 
    of all active legislative lines to prove system-wide ledger immutability.
    """
    return await generate_state_snapshot_hash(db)


@router.get("/proposal/{proposal_id}/verify")
async def verify_proposal(proposal_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Performs an isolated structural deep audit on an individual bill's 
    line items to ensure zero unauthorized record tampering.
    """
    audit_report = await verify_proposal_integrity(db, proposal_id)
    if audit_report["integrity_status"] == "compromised":
        raise HTTPException(status_code=500, detail={
            "error": "Database integrity violation detected!",
            "report": audit_report
        })
    return audit_report

### EOF: /positive-proxy/ledger/api/routers/audit.py ###