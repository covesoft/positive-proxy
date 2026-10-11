# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Joel Spector
# file: /positive-proxy/ledger/api/schemas/schemas.py

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


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
    proposal_id: UUID | None = None  # None sets it as a global proxy
    is_transferable: bool = True

class ProxyResponse(BaseModel):
    proxy_id: UUID
    grantor_id: UUID
    proxy_to_id: UUID
    proposal_id: UUID | None
    is_transferable: bool
    created_at: datetime
    revoked_at: datetime | None

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




# --- ISSUE SCHEMAS ---
class IssueCreate(BaseModel):
    title: str = Field(..., max_length=1024, description="Clear, concise headline of the civic issue.")
    description: str = Field(..., description="Detailed context and background of the problem.")

class IssueResponse(BaseModel):
    issue_id: UUID
    creator_id: UUID
    title: str
    description: str
    created_at: datetime

    class Config:
        from_attributes = True



# --- PROPOSAL SCHEMAS ---
class ProposalCreate(BaseModel):
    title: str = Field(..., max_length=1024, description="The name of the working draft or proposed bill.")
    issue_ids: list[UUID] = Field(default=[], description="Links this proposal to one or many tracked issues.")
    parent_id: UUID | None = Field(default=None, description="Populated only if this proposal is a fork of another bill.")

class ProposalResponse(BaseModel):
    proposal_id: UUID
    parent_id: UUID | None
    author_id: UUID
    title: str
    status: str
    declared_bill_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True



# --- BILL SECTION SCHEMAS ---
class BillSectionCreate(BaseModel):
    section_number: int
    content: str
    updated_by: UUID
    parent_section_id: UUID | None = None

class BillSectionResponse(BaseModel):
    section_id: UUID
    proposal_id: UUID
    section_number: int
    content: str
    version_hash: str
    updated_by: UUID
    parent_section_id: UUID | None
    created_at: datetime

    class Config:
        from_attributes = True




class SectionEdit(BaseModel):
    section_number: int
    content: str

class BallotCast(BaseModel):
    vote_choice: str  # 'yea', 'nay', or 'abstain'

### EOF: /positive-proxy/ledger/api/schemas/schemas.py ###