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

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import UUID
from app.database import get_db # Your database session dependency

router = APIRouter(prefix="/proposals", tags=["proposals"])

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
### EOF: /positive-proxy/ledger/api/routers/proposals.py ###