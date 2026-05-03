-- CockroachDB SQL Schema for Insurance Claims Platform
-- Generated: 2026-05-03
-- Database: Insurance Claims Management System

-- ============================================================================
-- CLAIMS TABLE
-- ============================================================================
-- Stores insurance claim records with risk assessment and status tracking

CREATE TABLE IF NOT EXISTS claims (
    -- Primary Key
    claim_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Claim Identification
    claim_number VARCHAR(50) UNIQUE NOT NULL,
    policy_number VARCHAR(50) NOT NULL,
    
    -- Claimant Information
    claimant_name VARCHAR(255) NOT NULL,
    claimant_email VARCHAR(255),
    claimant_phone VARCHAR(20),
    
    -- Claim Details
    incident_date TIMESTAMP NOT NULL,
    claim_date TIMESTAMP NOT NULL DEFAULT now(),
    claim_type VARCHAR(50) NOT NULL, -- e.g., 'auto', 'property', 'health', 'life'
    claim_amount DECIMAL(15, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Risk Assessment
    risk_score DECIMAL(5, 2) CHECK (risk_score >= 0 AND risk_score <= 100),
    risk_level VARCHAR(20) GENERATED ALWAYS AS (
        CASE 
            WHEN risk_score < 30 THEN 'LOW'
            WHEN risk_score >= 30 AND risk_score < 70 THEN 'MEDIUM'
            WHEN risk_score >= 70 THEN 'HIGH'
            ELSE 'UNKNOWN'
        END
    ) STORED,
    fraud_indicators JSONB, -- Stores array of fraud indicators
    
    -- Status Management
    status VARCHAR(50) NOT NULL DEFAULT 'SUBMITTED',
    status_reason TEXT,
    previous_status VARCHAR(50),
    
    -- Assignment
    assigned_adjuster_id UUID,
    assigned_at TIMESTAMP,
    
    -- Financial
    approved_amount DECIMAL(15, 2),
    paid_amount DECIMAL(15, 2) DEFAULT 0,
    payment_date TIMESTAMP,
    
    -- Documentation
    description TEXT,
    notes TEXT,
    attachments JSONB, -- Stores array of attachment metadata
    
    -- Audit Fields
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    created_by VARCHAR(255),
    updated_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_by VARCHAR(255),
    version INT DEFAULT 1,
    
    -- Constraints
    CONSTRAINT valid_status CHECK (
        status IN (
            'SUBMITTED', 'UNDER_REVIEW', 'INVESTIGATING', 
            'PENDING_DOCUMENTS', 'APPROVED', 'REJECTED', 
            'PAID', 'CLOSED', 'ESCALATED', 'SUSPENDED'
        )
    ),
    CONSTRAINT valid_claim_type CHECK (
        claim_type IN ('auto', 'property', 'health', 'life', 'liability', 'other')
    ),
    CONSTRAINT valid_amounts CHECK (
        claim_amount >= 0 AND 
        (approved_amount IS NULL OR approved_amount >= 0) AND
        paid_amount >= 0
    ),
    CONSTRAINT valid_dates CHECK (
        incident_date <= claim_date AND
        claim_date <= created_at
    )
);

-- Indexes for claims table
CREATE INDEX idx_claims_policy_number ON claims(policy_number);
CREATE INDEX idx_claims_status ON claims(status);
CREATE INDEX idx_claims_risk_score ON claims(risk_score);
CREATE INDEX idx_claims_claim_date ON claims(claim_date DESC);
CREATE INDEX idx_claims_assigned_adjuster ON claims(assigned_adjuster_id) WHERE assigned_adjuster_id IS NOT NULL;
CREATE INDEX idx_claims_claim_type ON claims(claim_type);
CREATE INDEX idx_claims_created_at ON claims(created_at DESC);

-- Inverted index for JSONB columns
CREATE INVERTED INDEX idx_claims_fraud_indicators ON claims(fraud_indicators);
CREATE INVERTED INDEX idx_claims_attachments ON claims(attachments);

-- ============================================================================
-- HELPER VIEWS
-- ============================================================================

-- View for high-risk claims requiring immediate attention
CREATE VIEW high_risk_claims AS
SELECT
    claim_id,
    claim_number,
    policy_number,
    claimant_name,
    claim_amount,
    risk_score,
    risk_level,
    status,
    assigned_adjuster_id,
    created_at
FROM claims
WHERE risk_score >= 70 AND status NOT IN ('CLOSED', 'PAID', 'REJECTED')
ORDER BY risk_score DESC, created_at DESC;

-- ============================================================================
-- SAMPLE DATA (Optional - for testing)
-- ============================================================================

-- Insert sample claims
INSERT INTO claims (
    claim_number, policy_number, claimant_name, claimant_email,
    incident_date, claim_date, claim_type, claim_amount,
    risk_score, status, description
) VALUES
    ('CLM-2026-001', 'POL-AUTO-12345', 'John Doe', 'john.doe@example.com',
     '2026-04-15', '2026-04-16', 'auto', 5000.00,
     25.50, 'UNDER_REVIEW', 'Minor collision at intersection'),
    ('CLM-2026-002', 'POL-PROP-67890', 'Jane Smith', 'jane.smith@example.com',
     '2026-04-20', '2026-04-21', 'property', 25000.00,
     75.80, 'INVESTIGATING', 'Water damage from burst pipe'),
    ('CLM-2026-003', 'POL-HEALTH-11111', 'Bob Johnson', 'bob.j@example.com',
     '2026-04-25', '2026-04-25', 'health', 3500.00,
     15.20, 'APPROVED', 'Emergency room visit');

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE claims IS 'Stores insurance claim records with risk assessment and status tracking';
COMMENT ON COLUMN claims.risk_score IS 'Risk score from 0-100, where higher values indicate higher risk';
COMMENT ON COLUMN claims.status IS 'Current status of the claim in the processing workflow';
COMMENT ON COLUMN claims.fraud_indicators IS 'JSON array of detected fraud indicators';
