# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Joel Spector
# file: /positive-proxy/ledger/api/routers/audit.py

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ledger.api.database import get_db
from ledger.api.services.audit import (
    generate_state_snapshot_hash,
    verify_proposal_integrity,
)

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