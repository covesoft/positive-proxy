# file: /positive-proxy/ledger/api/routers/proposals.py
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
from datetime import datetime, timezone

from ledger.api.database import get_db
from ledger.api.models.models import Issue, Proposal, ProposalIssue, BillSection, Ballot
from ledger.api.schemas.schemas import IssueCreate, SectionEdit, BallotCast, ProposalCreate, ProposalResponse
from ledger.api.services.governance import compute_section_hash, get_voter_turnout

router = APIRouter(prefix="/proposals", tags=["proposals"])

# =========================================================================
# 1. STATIC PATHS (Placed at top to prevent router path-trapping)
# =========================================================================

@router.post("/issues", status_code=status.HTTP_201_CREATED)
async def create_issue(issue_data: IssueCreate, creator_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Allows a user to anchor a public problem/issue into the database.
    """
    new_issue = Issue(
        creator_id=creator_id,
        title=issue_data.title,
        description=issue_data.description
    )
    db.add(new_issue)
    await db.commit()
    await db.refresh(new_issue)
    return new_issue


@router.post("/", response_model=ProposalResponse, status_code=status.HTTP_201_CREATED)
async def create_proposal(
    proposal_data: ProposalCreate, 
    author_id: UUID, 
    db: AsyncSession = Depends(get_db)
):
    """
    Drafts a completely new policy proposal or bill from scratch and 
    automatically binds it to one or many structural civic issues.
    """
    new_proposal = Proposal(
        parent_id=proposal_data.parent_id,
        author_id=author_id,
        title=proposal_data.title,
        status="draft"
    )
    db.add(new_proposal)
    await db.flush() 

    if proposal_data.issue_ids:
        for issue_id in proposal_data.issue_ids:
            junction = ProposalIssue(proposal_id=new_proposal.proposal_id, issue_id=issue_id)
            db.add(junction)
        
    await db.commit()
    await db.refresh(new_proposal)
    return new_proposal

# =========================================================================
# 2. DYNAMIC IDENTIFIER PATHS
# =========================================================================

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


@router.post("/{proposal_id}/sections", status_code=status.HTTP_201_CREATED)
async def add_or_edit_section(proposal_id: UUID, section_data: SectionEdit, user_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Appends or updates a deterministic text block within a working draft bill.
    """
    proposal = await db.get(Proposal, proposal_id)
    if not proposal or proposal.status != "draft":
        raise HTTPException(status_code=400, detail="Cannot alter text unless the proposal is an active draft")

    v_hash = compute_section_hash(section_data.content)
    
    new_section = BillSection(
        proposal_id=proposal_id,
        section_number=section_data.section_number,
        content=section_data.content,
        version_hash=v_hash,
        updated_by=user_id
    )
    db.add(new_section)
    await db.commit()
    return {"status": "section_committed", "version_hash": v_hash}


@router.post("/{proposal_id}/vote", status_code=status.HTTP_201_CREATED)
async def cast_direct_ballot(proposal_id: UUID, voter_id: UUID, ballot_data: BallotCast, db: AsyncSession = Depends(get_db)):
    """
    Cast an explicit direct vote. Overrides active proxy chain paths automatically.
    """
    proposal = await db.get(Proposal, proposal_id)
    if not proposal or proposal.status != "bill":
        raise HTTPException(status_code=400, detail="Voting is only permitted on formal, frozen bills")

    # Clear any past ballot cast by this user on this proposal to allow updating intent securely
    existing_ballot = await db.execute(
        select(Ballot).where(Ballot.proposal_id == proposal_id, Ballot.voter_id == voter_id)
    )
    old_vote = existing_ballot.scalar_one_or_none()
    if old_vote:
        await db.delete(old_vote)

    new_ballot = Ballot(
        proposal_id=proposal_id,
        voter_id=voter_id,
        vote_choice=ballot_data.vote_choice
    )
    db.add(new_ballot)
    await db.commit()
    return {"status": "ballot_logged_successfully", "choice": ballot_data.vote_choice}


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
    
    chain = []
    for row in rows:
        chain.append({
            "step": row[0],
            "proxy_holder": row[1],
            "vote_cast": row[2] if row[2] else "No ballot cast yet (delegated)"
        })
        
    return {"proposal_id": proposal_id, "origin_voter_id": user_id, "chain": chain}


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
        "ballot_volume": row[0] if row else 1
    }

@router.get("/", status_code=status.HTTP_200_OK)
async def list_proposals(db: AsyncSession = Depends(get_db)):
    """
    Retrieves all active community proposals and bills from the ledger.
    """
    result = await db.execute(select(Proposal))
    proposals = result.scalars().all()
    return {"proposals": proposals}

### EOF: /positive-proxy/ledger/api/routers/proposals.py ###