# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Joel Spector

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func
from uuid import UUID

from ledger.api.models.models import User

async def calculate_gini_coefficient(db: AsyncSession, proposal_id: UUID = None) -> dict:
    """
    Calculates the concentration of voting power using the Gini Coefficient formula.
    0.0 = Perfect democratic equality (everyone holds equal voting power).
    1.0 = Absolute oligarchy (one person controls the entire electorate).
    """
    # 1. Fetch the active proxy weight or global weight for every active user
    weight_query = text("""
        SELECT u.user_id, (
            SELECT ballot_volume 
            FROM positive_proxy.get_proxy_volume(u.user_id, :proposal_id)
        ) as weight
        FROM positive_proxy.users u
        WHERE u.is_active = TRUE;
    """)
    
    result = await db.execute(weight_query, {"proposal_id": proposal_id})
    weights = [float(row[1]) for row in result.fetchall()]
    
    n = len(weights)
    if n <= 1 or sum(weights) == 0:
        return {"gini_coefficient": 0.0, "status": "nominal"}
        
    # 2. Compute the standard Gini formula math
    weights.sort()
    sum_of_absolute_differences = sum(
        abs(x - y) for i, x in enumerate(weights) for j, y in enumerate(weights)
    )
    sum_of_weights = sum(weights)
    
    gini = sum_of_absolute_differences / (2 * n * sum_of_weights)
    
    # 3. Categorize warning flags
    status = "nominal"
    if gini >= 0.7:
        status = "critical_oligarchy_warning"
    elif gini >= 0.4:
        status = "soft_oligarchy_warning"
        
    return {
        "gini_coefficient": round(gini, 4),
        "total_tracked_electorate": n,
        "status": status
    }


async def detect_proxy_loops(db: AsyncSession) -> list[dict]:
    """
    Scans the live network graph for cyclical proxy assignments (A -> B -> C -> A).
    Loops paralyze automated voting pathways and must be flagged for resolution.
    """
    # Recursive CTE tracking path arrays to find cycles
    loop_query = text("""
        WITH RECURSIVE graph_tracker AS (
            -- Base: Get all active proxy pairings
            SELECT 
                grantor_id, 
                proxy_to_id, 
                ARRAY[grantor_id, proxy_to_id] AS current_path,
                FALSE AS is_cycle
            FROM positive_proxy.proxies
            WHERE revoked_at IS NULL
            
            UNION ALL
            
            -- Step: Append connections and flag if a node repeats
            SELECT 
                p.grantor_id, 
                p.proxy_to_id, 
                gt.current_path || p.proxy_to_id,
                p.proxy_to_id = ANY(gt.current_path)
            FROM graph_tracker gt
            JOIN positive_proxy.proxies p ON gt.proxy_to_id = p.grantor_id
            WHERE p.revoked_at IS NULL AND gt.is_cycle = FALSE
        )
        SELECT DISTINCT current_path 
        FROM graph_tracker 
        WHERE is_cycle = TRUE;
    """)
    
    result = await db.execute(loop_query)
    loops = result.fetchall()
    
    flagged_loops = []
    for loop in loops:
        flagged_loops.append({
            "message": "Circular delegation chain detected",
            "chain_path": loop[0]
        })
        
    return flagged_loops

### EOF: /positive-proxy/ledger/api/services/analytics.py ###