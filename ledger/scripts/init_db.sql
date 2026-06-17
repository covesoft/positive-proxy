CREATE SCHEMA IF NOT EXISTS positive_proxy;

-- 1. USERS TABLE
CREATE TABLE positive_proxy.users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) NOT NULL UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Historic log for citizen relocation/status changes
CREATE TABLE positive_proxy.user_status_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES positive_proxy.users(user_id),
    status_changed_to BOOLEAN NOT NULL,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. ISSUES DATABASE
CREATE TABLE positive_proxy.issues (
    issue_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    creator_id UUID REFERENCES positive_proxy.users(user_id),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. PROPOSALS TABLE
CREATE TABLE positive_proxy.proposals (
    proposal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id UUID REFERENCES positive_proxy.proposals(proposal_id) NULL, -- Supports branching/forking
    author_id UUID REFERENCES positive_proxy.users(user_id),
    title VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'bill', 'law', 'archived')),
    declared_bill_at TIMESTAMP WITH TIME ZONE NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Many-to-Many junction table for Issues and Proposals
CREATE TABLE positive_proxy.proposal_issues (
    proposal_id UUID REFERENCES positive_proxy.proposals(proposal_id) ON DELETE CASCADE,
    issue_id UUID REFERENCES positive_proxy.issues(issue_id) ON DELETE CASCADE,
    PRIMARY KEY (proposal_id, issue_id)
);

-- 4. LINE-ITEM BILL SECTIONS (Git-like evolution)
CREATE TABLE positive_proxy.bill_sections (
    section_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id UUID REFERENCES positive_proxy.proposals(proposal_id) ON DELETE CASCADE,
    section_number INT NOT NULL,                  -- Keeps lines/paragraphs in order
    content TEXT NOT NULL,
    version_hash VARCHAR(64) NOT NULL,           -- SHA-256 hash of content
    updated_by UUID REFERENCES positive_proxy.users(user_id),
    parent_section_id UUID NULL,                  -- Traces exact origin line if forked
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. PROXIES TABLE (Handles Global or Per-Bill delegation)
CREATE TABLE positive_proxy.proxies (
    proxy_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    grantor_id UUID REFERENCES positive_proxy.users(user_id),
    proxy_to_id UUID REFERENCES positive_proxy.users(user_id),
    proposal_id UUID REFERENCES positive_proxy.proposals(proposal_id) NULL, -- NULL means Global Fallback
    is_transferable BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    revoked_at TIMESTAMP WITH TIME ZONE NULL
);

-- 6. BALLOTS TABLE (The direct actions)
CREATE TABLE positive_proxy.ballots (
    ballot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id UUID REFERENCES positive_proxy.proposals(proposal_id),
    voter_id UUID REFERENCES positive_proxy.users(user_id),
    vote_choice VARCHAR(10) CHECK (vote_choice IN ('yea', 'nay', 'abstain')),
    cast_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_voter_per_proposal UNIQUE (proposal_id, voter_id)
);

--- PERFORMANCE INDEXES ---
CREATE INDEX idx_active_proxies ON positive_proxy.proxies (grantor_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_ballots_lookup ON positive_proxy.ballots (proposal_id, voter_id);
CREATE INDEX idx_bill_sections_order ON positive_proxy.bill_sections (proposal_id, section_number);

CREATE OR REPLACE FUNCTION positive_proxy.track_my_vote(voter_uuid UUID, target_proposal_id UUID)
RETURNS TABLE (step INT, proxy_holder_name VARCHAR, final_vote VARCHAR) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE downstream_chain AS (
        -- Base Case: Find who I explicitly proxied this bill to, or my global proxy
        SELECT 
            p.proxy_to_id,
            1 AS depth,
            p.is_transferable
        FROM positive_proxy.proxies p
        WHERE p.grantor_id = voter_uuid 
          AND p.revoked_at IS NULL
          AND (p.proposal_id = target_proposal_id OR p.proposal_id IS NULL)
        ORDER BY p.proposal_id DESC NULLS LAST -- Prioritize bill-specific proxy over global
        LIMIT 1

        UNION ALL

        -- Recursive Step: Trace downstream
        SELECT 
            p.proxy_to_id,
            dc.depth + 1,
            p.is_transferable
        FROM downstream_chain dc
        JOIN positive_proxy.proxies p ON dc.proxy_to_id = p.grantor_id
        WHERE dc.is_transferable = TRUE -- Break chain if previous proxy marked non-transferable
          AND p.revoked_at IS NULL
          AND (p.proposal_id = target_proposal_id OR p.proposal_id IS NULL)
    )
    SELECT 
        dc.depth,
        u.username,
        b.vote_choice
    FROM downstream_chain dc
    JOIN positive_proxy.users u ON u.user_id = dc.proxy_to_id
    LEFT JOIN positive_proxy.ballots b ON b.voter_id = dc.proxy_to_id AND b.proposal_id = target_proposal_id
    ORDER BY dc.depth ASC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;