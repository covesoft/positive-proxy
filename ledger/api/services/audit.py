# file: /positive-proxy/ledger/api/services/audit.py
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

import hashlib
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from uuid import UUID

from ledger.api.models.models import BillSection, Proposal

async def generate_state_snapshot_hash(db: AsyncSession) -> dict:
    """
    Computes a single, deterministic cryptographic master hash capturing the 
    exact architectural state of all laws and active bills on the ledger.
    Provides external watchdogs a mathematical proof that past records haven't changed.
    """
    # 1. Gather all line-item hashes ordered chronologically by creation and position
    query = (
        select(BillSection.version_hash)
        .order_by(BillSection.created_at.asc(), BillSection.section_id.asc())
    )
    result = await db.execute(query)
    section_hashes = result.scalars().all()
    
    if not section_hashes:
        # Return an initial genesis seed hash if the database is brand new
        genesis_hash = hashlib.sha256(b"positive_proxy_genesis_block_2026").hexdigest()
        return {
            "snapshot_timestamp": datetime.now(timezone.utc),
            "total_sections_verified": 0,
            "master_state_hash": genesis_hash
        }
        
    # 2. Hash the concatenated stream of all individual version strings
    hasher = hashlib.sha256()
    for v_hash in section_hashes:
        hasher.update(v_hash.encode('utf-8'))
        
    master_hash = hasher.hexdigest()
    
    return {
        "snapshot_timestamp": datetime.now(timezone.utc),
        "total_sections_verified": len(section_hashes),
        "master_state_hash": master_hash
    }


async def verify_proposal_integrity(db: AsyncSession, proposal_id: UUID) -> dict:
    """
    Audits a single policy proposal or bill from root to leaf. Recalculates the 
    SHA-256 components of every paragraph text block to detect silent tampering.
    """
    # Fetch all sections associated with this specific proposal
    query = (
        select(BillSection)
        .where(BillSection.proposal_id == proposal_id)
        .order_by(BillSection.section_number.asc())
    )
    result = await db.execute(query)
    sections = result.scalars().all()
    
    if not sections:
        return {"proposal_id": proposal_id, "integrity_status": "empty_or_not_found", "corrupted_sections": []}
        
    corrupted_sections = []
    
    # Verify that the text matches the stored checksum hash exactly
    for sec in sections:
        calculated_hash = hashlib.sha256(sec.content.strip().encode('utf-8')).hexdigest()
        
        if calculated_hash != sec.version_hash:
            corrupted_sections.append({
                "section_id": sec.section_id,
                "section_number": sec.section_number,
                "expected_hash": sec.version_hash,
                "calculated_actual_hash": calculated_hash
            })
            
    is_valid = len(corrupted_sections) == 0
    
    return {
        "proposal_id": proposal_id,
        "integrity_status": "verified_authentic" if is_valid else "compromised",
        "total_sections_checked": len(sections),
        "corrupted_sections": corrupted_sections
    }

### EOF: /positive-proxy/ledger/api/services/audit.py ###