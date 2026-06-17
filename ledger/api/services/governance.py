# file: /positive-proxy/ledger/api/services/governance.py
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
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func, update, insert

from ledger.api.models.models import User, Proposal, BillSection, Proxy, Ballot

def compute_section_hash(content: str) -> str:
    """Generates a git-like hash for line-item tracking."""
    return hashlib.sha256(content.strip().encode('utf-8')).hexdigest()


async def create_proposal_fork(db: AsyncSession, parent_proposal_id: UUID, author_id: UUID, title: str) -> UUID:
    """
    Forks an existing proposal asynchronously, copying over all current 
    active sections to start a new branch.
    """
    # 1. Insert new proposal pointing to parent using model assignment
    new_proposal = Proposal(
        parent_id=parent_proposal_id,
        author_id=author_id,
        title=title,
        status="draft"
    )
    db.add(new_proposal)
    await db.flush()  # Populates new_proposal.proposal_id utilizing UUIDv7 generator
    
    # 2. Asynchronously copy line-item sections from parent
    copy_query = text("""
        INSERT INTO positive_proxy.bill_sections (section_id, proposal_id, section_number, content, version_hash, updated_by, parent_section_id, created_at)
        SELECT gen_random_uuid(), :new_id, section_number, content, version_hash, :author_id, section_id, :now
        FROM positive_proxy.bill_sections 
        WHERE proposal_id = :parent_id;
    """)
    
    await db.execute(copy_query, {
        "new_id": new_proposal.proposal_id,
        "author_id": author_id,
        "parent_id": parent_proposal_id,
        "now": datetime.now(timezone.utc)
    })
    
    await db.commit()
    return new_proposal.proposal_id


async def check_oligarchy_cap(db: AsyncSession, proxy_holder_id: UUID, max_percentage: float = 0.05) -> bool:
    """
    Computes a voter's dynamic proxy weight over asyncpg. 
    Returns True if they are safely under the cap, False if they breach oligarchy limits.
    """
    # Total active citizens
    total_query = select(func.count()).select_from(User).where(User.is_active == True)
    total_result = await db.execute(total_query)
    total_electorate = total_result.scalar_one() or 0
    
    if total_electorate == 0:
        return True

    # Calculate dynamic influence weight using recursive tracking
    influence_query = text("""
        WITH RECURSIVE total_influence AS (
            SELECT grantor_id FROM positive_proxy.proxies 
            WHERE proxy_to_id = :holder_id AND revoked_at IS NULL
            
            UNION
            
            SELECT p.grantor_id FROM positive_proxy.proxies p
            JOIN total_influence ti ON p.proxy_to_id = ti.grantor_id
            WHERE p.revoked_at IS NULL AND p.is_transferable = TRUE
        )
        SELECT COUNT(*) + 1 AS proxy_weight FROM total_influence;
    """)
    
    weight_result = await db.execute(influence_query, {"holder_id": proxy_holder_id})
    weight = weight_result.scalar_one() or 1
    
    cap_limit = total_electorate * max_percentage
    return weight <= cap_limit


async def declare_bill(db: AsyncSession, proposal_id: UUID) -> bool:
    """Transitions a living document draft into a frozen Bill ready for formal voting."""
    query = (
        update(Proposal)
        .where(Proposal.proposal_id == proposal_id, Proposal.status == "draft")
        .values(status="bill", declared_bill_at=datetime.now(timezone.utc))
    )
    result = await db.execute(query)
    await db.commit()
    return result.rowcount > 0


async def calculate_bill_tally(db: AsyncSession, proposal_id: UUID) -> dict:
    """
    Runs the recursive engine across the active electorate to discover the outcome of a bill.
    Honors the transparent stack (direct votes overriding proxies).
    """
    # Fetch all active user IDs
    users_query = select(User.user_id).where(User.is_active == True)
    users_result = await db.execute(users_query)
    voters = users_result.scalars().all()
    
    results = {"yea": 0, "nay": 0, "abstain": 0, "uncast": 0}
    
    # Recursive loop walking the stack for each citizen
    tally_query = text("""
        WITH RECURSIVE proxy_chain AS (
            SELECT :voter_id AS current_voter, 0 AS depth, ARRAY[:voter_id::uuid] AS path, TRUE AS transferable
            
            UNION ALL
            
            SELECT p.proxy_to_id, pc.depth + 1, pc.path || p.proxy_to_id, p.is_transferable
            FROM proxy_chain pc
            JOIN positive_proxy.proxies p ON pc.current_voter = p.grantor_id
            WHERE p.revoked_at IS NULL 
              AND pc.transferable = TRUE
              AND (p.proposal_id = :proposal_id OR p.proposal_id IS NULL)
              AND NOT (p.proxy_to_id = ANY(pc.path))
        )
        SELECT b.vote_choice FROM proxy_chain pc
        JOIN positive_proxy.ballots b ON b.voter_id = pc.current_voter
        WHERE b.proposal_id = :proposal_id
        ORDER BY pc.depth ASC
        LIMIT 1;
    """)
    
    for voter_id in voters:
        vote_result = await db.execute(tally_query, {"voter_id": voter_id, "proposal_id": proposal_id})
        vote = vote_result.scalar_one_or_none()
        
        if vote:
            results[vote] += 1
        else:
            results["uncast"] += 1
            
    return results

### EOF: /positive-proxy/ledger/api/services/governance.py ###