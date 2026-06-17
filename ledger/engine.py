### file: /positive-proxy/ledger/engine.py
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

### MODULE REDACTED 2026-06-17

#Python Engine (SQLAlchemy Core / Psycopg3)
#This Python module handles database operations,
#  counts real-time active electorate weights,
#  and enforces a dynamic Oligarchy Cap (e.g., 5% municipal limit).

import hashlib
from psycopg import connect
from psycopg.rows import dict_row

# Database connection details string (adjust to match your shared Postgres instance)
DB_CONN = "dbname=your_existing_db user=postgres password=secret host=localhost"

def get_db_connection():
    return connect(DB_CONN, row_factory=dict_row)

def compute_section_hash(content: str) -> str:
    """Generates a git-like hash for line-item tracking."""
    return hashlib.sha256(content.strip().encode('utf-8')).hexdigest()

def create_proposal_fork(parent_proposal_id: str, author_id: str, title: str) -> str:
    """Forks an existing proposal, copying over all current active sections to start a new branch."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 1. Insert new proposal pointing to parent
            cur.execute(
                """INSERT INTO positive_proxy.proposals (parent_id, author_id, title, status)
                   VALUES (%s, %s, %s, 'draft') RETURNING proposal_id;""",
                (parent_proposal_id, author_id, title)
            )
            new_proposal_id = cur.fetchone()['proposal_id']
            
            # 2. Copy line items from parent
            cur.execute(
                """INSERT INTO positive_proxy.bill_sections (proposal_id, section_number, content, version_hash, updated_by, parent_section_id)
                   SELECT %s, section_number, content, version_hash, %s, section_id
                   FROM positive_proxy.bill_sections WHERE proposal_id = %s;""",
                (new_proposal_id, author_id, parent_proposal_id)
            )
            conn.commit()
            return new_proposal_id

def check_oligarchy_cap(proxy_holder_id: str, max_percentage: float = 0.05) -> bool:
    """
    Computes a voter's dynamic proxy weight. 
    Returns True if they are safely under the cap, False if they breach oligarchy limits.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Total active citizens
            cur.execute("SELECT COUNT(*) FROM positive_proxy.users WHERE is_active = TRUE;")
            total_electorate = cur.fetchone()['count']
            
            # Calculate dynamic weight using recursive tracking
            cur.execute(
                """WITH RECURSIVE total_influence AS (
                       SELECT grantor_id FROM positive_proxy.proxies 
                       WHERE proxy_to_id = %s AND revoked_at IS NULL
                       
                       UNION
                       
                       SELECT p.grantor_id FROM positive_proxy.proxies p
                       JOIN total_influence ti ON p.proxy_to_id = ti.grantor_id
                       WHERE p.revoked_at IS NULL AND p.is_transferable = TRUE
                   )
                   SELECT COUNT(*) + 1 AS proxy_weight FROM total_influence;""", # +1 includes themselves
                (proxy_holder_id,)
            )
            weight = cur.fetchone()['proxy_weight']
            
            cap_limit = total_electorate * max_percentage
            return weight <= cap_limit

def declare_bill(proposal_id: str) -> None:
    """Transitions a living document draft into a frozen Bill ready for formal voting."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE positive_proxy.proposals 
                   SET status = 'bill', declared_bill_at = NOW() 
                   WHERE proposal_id = %s AND status = 'draft';""",
                (proposal_id,)
            )
            conn.commit()

def calculate_bill_tally(proposal_id: str):
    """
    Runs the recursive engine across the active electorate to discover the outcome of a bill.
    Honors the transparent stack (direct votes overriding proxies).
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Fetch all active users
            cur.execute("SELECT user_id FROM positive_proxy.users WHERE is_active = TRUE;")
            voters = cur.fetchall()
            
            results = {"yea": 0, "nay": 0, "abstain": 0, "uncast": 0}
            
            for voter in voters:
                # Walk down the stack for every single user to see where their ballot landed
                cur.execute(
                    """WITH RECURSIVE proxy_chain AS (
                           SELECT %s AS current_voter, 0 AS depth, ARRAY[%s::uuid] AS path, TRUE AS transferable
                           
                           UNION ALL
                           
                           SELECT p.proxy_to_id, pc.depth + 1, pc.path || p.proxy_to_id, p.is_transferable
                           FROM proxy_chain pc
                           JOIN positive_proxy.proxies p ON pc.current_voter = p.grantor_id
                           WHERE p.revoked_at IS NULL 
                             AND pc.transferable = TRUE
                             AND (p.proposal_id = %s OR p.proposal_id IS NULL)
                             AND NOT (p.proxy_to_id = ANY(pc.path))
                       )
                       SELECT b.vote_choice FROM proxy_chain pc
                       JOIN positive_proxy.ballots b ON b.voter_id = pc.current_voter
                       WHERE b.proposal_id = %s
                       ORDER BY pc.depth ASC
                       LIMIT 1;""",
                    (voter['user_id'], voter['user_id'], proposal_id, proposal_id)
                )
                vote = cur.fetchone()
                if vote:
                    results[vote['vote_choice']] += 1
                else:
                    results["uncast"] += 1
            
            return results

### EOF: /positive-proxy/ledger/engine.py ###