### file: /positive-proxy/back_ledger/api/models/models.py
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



from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

# 1. USERS TABLE
class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "positive_proxy"}

    user_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

# 3. PROPOSALS TABLE (with Self-Referential Hierarchy for Forking)
class Proposal(Base):
    __tablename__ = "proposals"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'bill', 'law', 'archived')", name="check_status"),
        {"schema": "positive_proxy"}
    )

    proposal_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    parent_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("positive_proxy.proposals.proposal_id"), nullable=True)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("positive_proxy.users.user_id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    declared_bill_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    children: Mapped[List["Proposal"]] = relationship("Proposal", back_populates="parent")
    parent: Mapped[Optional["Proposal"]] = relationship("Proposal", back_populates="children", remote_side=[proposal_id])

# 6. BALLOTS TABLE (Ensures one vote per person per bill)
class Ballot(Base):
    __tablename__ = "ballots"
    __table_args__ = (
        UniqueConstraint("proposal_id", "voter_id", name="unique_voter_per_proposal"),
        CheckConstraint("vote_choice IN ('yea', 'nay', 'abstain')", name="check_vote_choice"),
        {"schema": "positive_proxy"}
    )

    ballot_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    proposal_id: Mapped[UUID] = mapped_column(ForeignKey("positive_proxy.proposals.proposal_id"))
    voter_id: Mapped[UUID] = mapped_column(ForeignKey("positive_proxy.users.user_id"))
    vote_choice: Mapped[str] = mapped_column(String(10))
    cast_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

### EOF: /positive-proxy/back_ledger/api/models/models.py ###