# file: /positive-proxy/ledger/api/services/notification.py
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

# This module acts as the "Civic Engagement Sentinel." Its most important job
#  is enforcing the democratic fallback safety net: if a citizen has assigned a proxy,
#  but that proxy votes in a way the citizen might not agree with, the system must
#  immediately flag an alert. This gives the voter an explicit window to step in and
#  execute a direct-vote override before the legislative floor closes.

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import UUID
from typing import List

async def check_proxy_action_alerts(db: AsyncSession, user_id: UUID) -> list[dict]:
    """
    Evaluates cast ballots to see if a user's chosen proxy has voted on an active bill.
    Generates actionable alert notifications so citizens can review their proxy's choice 
    and exercise their sovereign right to a direct-vote override if necessary.
    """
    # This query finds all active bills where the user hasn't voted directly,
    # but their downstream proxy chain HAS cast a ballot.
    query = text("""
        WITH RECURSIVE proxy_chain AS (
            SELECT CAST(:voter_id AS UUID) AS current_voter, 0 AS depth, ARRAY[CAST(:voter_id AS UUID)] AS path, TRUE AS transferable

            UNION ALL

            SELECT p.proxy_to_id, pc.depth + 1, pc.path || p.proxy_to_id, p.is_transferable
            FROM proxy_chain pc
            JOIN positive_proxy.proxies p ON pc.current_voter = p.grantor_id
            WHERE p.revoked_at IS NULL 
              AND pc.transferable = TRUE
              AND NOT (p.proxy_to_id = ANY(pc.path))
        )
        SELECT 
            prop.proposal_id,
            prop.title,
            b.vote_choice,
            u.username AS proxy_voter_name,
            pc.depth
        FROM positive_proxy.proposals prop
        CROSS JOIN proxy_chain pc
        JOIN positive_proxy.ballots b ON b.voter_id = pc.current_voter AND b.proposal_id = prop.proposal_id
        JOIN positive_proxy.users u ON u.user_id = pc.current_voter
        WHERE prop.status = 'bill'
          -- Exclude if the user themselves already cast a direct ballot overriding the proxy
          AND NOT EXISTS (
              SELECT 1 FROM positive_proxy.ballots 
              WHERE voter_id = CAST(:voter_id AS UUID) AND proposal_id = prop.proposal_id
          )
        ORDER BY prop.proposal_id, pc.depth ASC;
    """)

    result = await db.execute(query, {"voter_id": user_id})
    rows = result.fetchall()
    
    alerts = []
    seen_proposals = set()
    
    for row in rows:
        proposal_id, title, vote_choice, proxy_name, depth = row
        
        # Since the query is ordered by depth, the first row per proposal id 
        # is the closest active proxy whose vote actually dictates the current fallback state.
        if proposal_id in seen_proposals:
            continue
            
        seen_proposals.add(proposal_id)
        
        alerts.append({
            "proposal_id": proposal_id,
            "title": title,
            "type": "proxy_activity",
            "message": f"Your delegate '{proxy_name}' (at depth {depth}) has cast a '{vote_choice}' on this bill.",
            "action_required": "Review choice. You may submit a direct ballot to completely override this action."
        })
        
    return alerts

### EOF: /positive-proxy/ledger/api/services/notification.py ###