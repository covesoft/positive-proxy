-- file: /positive-proxy/ledger/scripts/init_db.sql
-- Positive Proxy Database Initialization Script (2026 Production Specification)
-- Enforces: UUIDv7 Temporal Sorting, UTC Timezone Safety, and Asymmetric Privacy.

CREATE SCHEMA IF NOT EXISTS positive_proxy;

-- =========================================================================
-- SYSTEM UTILITIES: NATIVE UUIDv7 GENERATOR
-- =========================================================================
-- Allows PostgreSQL to generate time-ordered UUIDv7 keys matching Python.
CREATE OR REPLACE FUNCTION positive_proxy.generate_uuidv7()
RETURNS UUID AS $$
DECLARE
    v_time timestamp with time zone := clock_timestamp();
    v_secs bigint;
    v_msec bigint;
    v_time_hex varchar;
    v_rand_hex varchar;
    v_uuid_str varchar;
BEGIN
    v_secs := extract(epoch from v_time);
    v_msec := (extract(milliseconds from v_time)::bigint % 1000);
    v_time_hex := lpad(to_hex((v_secs * 1000) + v_msec), 12, '0');
    v_rand_hex := encode(gen_random_bytes(10), 'hex');
    
    -- Format into structural UUID formatting layout with variant 4 bits
    v_uuid_str := substr(v_time_hex, 1, 8) || '-' ||
                  substr(v_time_hex, 9, 4) || '-' ||
                  '7' || substr(v_rand_hex, 1, 3) || '-' ||
                  to_hex((decode(substr(v_rand_hex, 4, 1), 'hex')::int & 3) | 8) || substr(v_rand_hex, 5, 3) || '-' ||
                  substr(v_rand_hex, 8, 12);
                  
    RETURN v_uuid_str::uuid;
END;
$$ LANGUAGE plpgsql VOLATILE;

-- =========================================================================
-- CORE CORE TABLES
-- =========================================================================

-- 1. USERS TABLE
CREATE TABLE positive_proxy.users (
    user_id UUID PRIMARY KEY DEFAULT positive_proxy.generate_uuidv7(),
    username VARCHAR(100) NOT NULL UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Historic log for citizen relocation/status changes
CREATE TABLE positive_proxy.user_status_log (
    log_id UUID PRIMARY KEY DEFAULT positive_proxy.generate_uuidv7(),
    user_id UUID REFERENCES positive_proxy.users(user_id) ON DELETE CASCADE,
    status_changed_to BOOLEAN NOT NULL,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. ISSUES DATABASE
CREATE TABLE positive_proxy.issues (
    issue_id UUID PRIMARY KEY DEFAULT positive_proxy.generate_uuidv7(),
    creator_id UUID REFERENCES positive_proxy.users(user_id) ON DELETE SET NULL,
    title VARCHAR(1024) NOT NULL, -- Expanded length matching Python configuration specs
    description TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. PROPOSALS TABLE
CREATE TABLE positive_proxy.proposals (
    proposal_id UUID PRIMARY KEY DEFAULT positive_proxy.generate_uuidv7(),
    parent_id UUID REFERENCES positive_proxy.proposals(proposal_id) ON DELETE SET NULL NULL,
    author_id UUID REFERENCES positive_proxy.users(user_id) ON DELETE SET NULL,
    title VARCHAR(1024) NOT NULL, -- Expanded length matching Python configuration specs
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'bill', 'law', 'archived')),
    declared_bill_at TIMESTAMP WITH TIME ZONE NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Many-to-Many junction table for Issues and Proposals
CREATE TABLE positive_proxy.proposal_issues (
    proposal_id UUID REFERENCES positive_proxy.proposals(proposal_id) ON DELETE CASCADE,
    issue_id UUID REFERENCES positive_proxy.issues(issue_id) ON DELETE CASCADE,
    PRIMARY KEY (proposal_id, issue_id)
);

-- 4. LINE-ITEM BILL SECTIONS (Git-like evolution)
CREATE TABLE positive_proxy.bill_sections (
    section_id UUID PRIMARY KEY DEFAULT positive_proxy.generate_uuidv7(),
    proposal_id UUID REFERENCES positive_proxy.proposals(proposal_id) ON DELETE CASCADE,
    section_number INT NOT NULL,
    content TEXT NOT NULL,
    version_hash VARCHAR(64) NOT NULL, -- SHA-256 hash of content
    updated_by UUID REFERENCES positive_proxy.users(user_id) ON DELETE SET NULL,
    parent_section_id UUID NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. PROXIES TABLE (Handles Global or Per-Bill delegation)
CREATE TABLE positive_proxy.proxies (
    proxy_id UUID PRIMARY KEY DEFAULT positive_proxy.generate_uuidv7(),
    grantor_id UUID REFERENCES positive_proxy.users(user_id) ON DELETE CASCADE,
    proxy_to_id UUID REFERENCES positive_proxy.users(user_id) ON DELETE CASCADE,
    proposal_id UUID REFERENCES positive_proxy.proposals(proposal_id) ON DELETE CASCADE NULL,
    is_transferable BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP WITH TIME ZONE NULL
);

-- 6. BALLOTS TABLE (The direct actions)
CREATE TABLE positive_proxy.ballots (
    ballot_id UUID PRIMARY KEY DEFAULT positive_proxy.generate_uuidv7(),
    proposal_id UUID REFERENCES positive_proxy.proposals(proposal_id) ON DELETE CASCADE,
    voter_id UUID REFERENCES positive_proxy.users(user_id) ON DELETE CASCADE,
    vote_choice VARCHAR(10) CHECK (vote_choice IN ('yea', 'nay', 'abstain')),
    cast_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_voter_per_proposal UNIQUE (proposal_id, voter_id)
);

-- =========================================================================
-- OPTIMIZED INDEX ARCHITECTURE
-- =========================================================================
-- Partial index guarantees lightning fast recursive lookups for active delegations
CREATE INDEX idx_active_proxies ON positive_proxy.proxies (grantor_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_ballots_lookup ON positive_proxy.ballots (proposal_id, voter_id);
CREATE INDEX idx_bill_sections_order ON positive_proxy.bill_sections (proposal_id, section_number);

-- =========================================================================
-- SECURE DOWNWARD VOTE TRACING FUNCTION
-- =========================================================================
CREATE OR REPLACE FUNCTION positive_proxy.track_my_vote(voter_uuid UUID, target_proposal_id UUID)
RETURNS TABLE (step INT, proxy_holder_name VARCHAR, final_vote VARCHAR) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE downstream_chain AS (
        -- Base Case: Find who I explicitly proxied this bill to, or fallback to global
        SELECT 
            p.proxy_to_id,
            1 AS depth,
            p.is_transferable
        FROM positive_proxy.proxies p
        WHERE p.grantor_id = voter_uuid 
          AND p.revoked_at IS NULL
          AND (p.proposal_id = target_proposal_id OR p.proposal_id IS NULL)
        ORDER BY p.proposal_id DESC NULLS LAST
        LIMIT 1

        UNION ALL

        -- Recursive Step: Trace exclusively forward/downward
        SELECT 
            p.proxy_to_id,
            dc.depth + 1,
            p.is_transferable
        FROM downstream_chain dc
        JOIN positive_proxy.proxies p ON dc.proxy_to_id = p.grantor_id
        WHERE dc.is_transferable = TRUE -- Enforce transferability limits strictly
          AND p.revoked_at IS NULL
          AND (p.proposal_id = target_proposal_id OR p.proposal_id IS NULL)
    )
    SELECT 
        dc.depth,
        u.username,
        b.vote_choice::varchar
    FROM downstream_chain dc
    JOIN positive_proxy.users u ON u.user_id = dc.proxy_to_id
    LEFT JOIN positive_proxy.ballots b ON b.voter_id = dc.proxy_to_id AND b.proposal_id = target_proposal_id
    ORDER BY dc.depth ASC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;