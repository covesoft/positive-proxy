### file: /positive-proxy/ledger/api/routers/proposals.py
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

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from uuid import UUID
from typing import List
from datetime import datetime, timezone

from ledger.api.database import get_db # database session dependency
from ledger.api.models.models import Proposal, Ballot, BillSection
from ledger.api.schemas.schemas import ProposalCreate, ProposalResponse, VoteCast, VoteResponse



router = APIRouter(prefix="/proposals", tags=["proposals"])


@router.post("/", response_model=ProposalResponse, status_code=status.HTTP_201_CREATED)
async def create_proposal(proposal_data: ProposalCreate, db: AsyncSession = Depends(get_db)):
    """
    Draft a completely new policy proposal or bill from scratch.
    """
    new_proposal = Proposal(
        title=proposal_data.title,
        author_id=proposal_data.author_id,
        status="draft"
    )
    db.add(new_proposal)
    await db.commit()
    await db.refresh(new_proposal)
    return new_proposal


@router.get("/{proposal_id}/trace/{user_id}")
async def trace_vote(proposal_id: UUID, user_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Executes the secure downward vote-tracing function to follow a user's 
    delegation path for a specific proposal.
    """
    query = text("""
        SELECT step, proxy_holder_name, final_vote 
        FROM positive_proxy.track_my_vote(:user_id, :proposal_id);
    """)
    
    result = await db.execute(query, {"user_id": user_id, "proposal_id": proposal_id})
    rows = result.fetchall()
    
    if not rows:
        return {"message": "No proxy chain or votes found for this user on this proposal."}
    
    # Format the recursive database output into clean JSON
    chain = []
    for row in rows:
        chain.append({
            "step": row[0],
            "proxy_holder": row[1],
            "vote_cast": row[2] if row[2] else "No ballot cast yet (delegated)"
        })
        
    return {"proposal_id": proposal_id, "origin_voter_id": user_id, "chain": chain}



@router.post("/{parent_id}/fork", response_model=ProposalResponse, status_code=status.HTTP_201_CREATED)
async def fork_proposal(parent_id: UUID, author_id: UUID, fork_title: str, db: AsyncSession = Depends(get_db)):
    """
    Supports git-like branching. Fork an existing proposal/bill to modify its trajectory
    or offer a competing version while maintaining historical lineage.
    """
    parent = await db.get(Proposal, parent_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Parent proposal not found")
        
    forked_proposal = Proposal(
        parent_id=parent_id,
        author_id=author_id,
        title=fork_title,
        status="draft"
    )
    db.add(forked_proposal)
    await db.commit()
    await db.refresh(forked_proposal)
    return forked_proposal



@router.post("/vote", response_model=VoteResponse, status_code=status.HTTP_201_CREATED)
async def cast_ballot(vote_data: VoteCast, voter_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Cast a direct vote ('yea', 'nay', 'abstain') on a specific proposal.
    Triggers unique constraint check if the voter already cast a ballot here.
    """
    # 1. Check if user already voted directly
    existing_ballot = await db.execute(
        select(Ballot).where(Ballot.proposal_id == vote_data.proposal_id, Ballot.voter_id == voter_id)
    )
    if existing_ballot.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Voter has already cast a direct ballot on this proposal")

    # 2. Add the ballot record
    new_ballot = Ballot(
        proposal_id=vote_data.proposal_id,
        voter_id=voter_id,
        vote_choice=vote_data.vote_choice
    )
    db.add(new_ballot)
    await db.commit()
    await db.refresh(new_ballot)
    return new_ballot



from sqlalchemy import text
from ledger.api.services.governance import get_voter_turnout

@router.get("/{proposal_id}/turnout")
async def read_proposal_turnout(proposal_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Get total active electorate count, total cast ballots, and raw turnout percentage.
    """
    return await get_voter_turnout(db, proposal_id)


@router.get("/{proposal_id}/proxy-volume/{user_id}")
async def read_proxy_volume(proposal_id: UUID, user_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Returns the total numeric volume of ballots a representative controls for a bill.
    Strictly anonymous: yields only a number, hiding upstream voter identities.
    """
    query = text("""
        SELECT ballot_volume 
        FROM positive_proxy.get_proxy_volume(:user_id, :proposal_id);
    """)
    result = await db.execute(query, {"user_id": user_id, "proposal_id": proposal_id})
    row = result.fetchone()
    
    return {
        "proposal_id": proposal_id,
        "representative_id": user_id,
        "ballot_volume": row[0] if row else 1  # Minimum 1 (includes their own vote)
    }

### EOF: /positive-proxy/ledger/api/routers/proposals.py ###