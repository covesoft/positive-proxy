### file: /positive-proxy/back_ledger/api/schemas/schemas.py
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



from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, List

# --- USER SCHEMAS ---
class UserBase(BaseModel):
    username: str = Field(..., max_length=100)

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    user_id: UUID
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# --- PROXY SCHEMAS ---
class ProxyCreate(BaseModel):
    proxy_to_id: UUID
    proposal_id: Optional[UUID] = None  # None sets it as a global proxy
    is_transferable: bool = True

class ProxyResponse(BaseModel):
    proxy_id: UUID
    grantor_id: UUID
    proxy_to_id: UUID
    proposal_id: Optional[UUID]
    is_transferable: bool
    created_at: datetime
    revoked_at: Optional[datetime]

    class Config:
        from_attributes = True

# --- BALLOT/VOTE SCHEMAS ---
class VoteCast(BaseModel):
    proposal_id: UUID
    vote_choice: str = Field(..., description="Must be 'yea', 'nay', or 'abstain'")

class VoteResponse(BaseModel):
    ballot_id: UUID
    proposal_id: UUID
    voter_id: UUID
    vote_choice: str
    cast_at: datetime

    class Config:
        from_attributes = True

### EOF: /positive-proxy/ledger/api/schemas/schemas.py ###