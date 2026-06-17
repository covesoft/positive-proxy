### File: /positive-proxy/ledger/api/routers/users.py
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

# Here is the implementation for routers/users.py to handle citizens,
#  status logging, and setting up proxies.

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from typing import List

# Pydantic schemas and SQLAlchemy models
from ledger.api.models.models import User, Proxy, UserStatusLog
from ledger.api.schemas.schemas import UserCreate, UserResponse, ProxyCreate, ProxyResponse

#import get_db

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Register a new citizen in the Positive Proxy system.
    """
    # Check if username already exists
    existing_user = await db.execute(select(User).where(User.username == user_data.username))
    if existing_user.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    new_user = User(username=user_data.username)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post("/{user_id}/proxy", response_model=ProxyResponse, status_code=status.HTTP_201_CREATED)
async def assign_proxy(user_id: UUID, proxy_data: ProxyCreate, db: AsyncSession = Depends(get_db)):
    """
    Delegate voting power to a trusted party. 
    If proposal_id is omitted, this sets a Global Fallback proxy.
    """
    # 1. Verify grantor exists
    grantor = await db.get(User, user_id)
    if not grantor or not grantor.is_active:
        raise HTTPException(status_code=404, detail="Granting user not found or inactive")
        
    # 2. Verify proxy target exists
    proxy_target = await db.get(User, proxy_data.proxy_to_id)
    if not proxy_target or not proxy_target.is_active:
        raise HTTPException(status_code=404, detail="Proxy target user not found or inactive")
        
    # 3. Prevent self-delegation
    if user_id == proxy_data.proxy_to_id:
        raise HTTPException(status_code=400, detail="You cannot delegate your vote to yourself")

    # 4. Revoke any existing active proxy for this exact scope (Global or Specific Bill)
    existing_proxy_query = select(Proxy).where(
        Proxy.grantor_id == user_id,
        Proxy.proposal_id == proxy_data.proposal_id,
        Proxy.revoked_at == None
    )
    existing_proxy_result = await db.execute(existing_proxy_query)
    active_proxy = existing_proxy_result.scalar_one_or_none()
    
    if active_proxy:
        from datetime import datetime, timezone
        active_proxy.revoked_at = datetime.now(timezone.utc)

    # 5. Create new proxy mapping
    new_proxy = Proxy(
        grantor_id=user_id,
        proxy_to_id=proxy_data.proxy_to_id,
        proposal_id=proxy_data.proposal_id,
        is_transferable=proxy_data.is_transferable
    )
    
    db.add(new_proxy)
    await db.commit()
    await db.refresh(new_proxy)
    return new_proxy


from ledger.api.services.governance import get_pending_action_items

@router.get("/{user_id}/pending-actions", response_model=list[dict])
async def read_pending_actions(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Returns critical or informational items requiring the citizen's attention 
    (e.g., active bills where neither they nor their proxies have voted).
    """
    return await get_pending_action_items(db, user_id)
### EOF: /positive-proxy/ledger/api/routers/users.py ###