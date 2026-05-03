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
-- WEBHOOK_SUBSCRIPTIONS TABLE
-- ============================================================================
-- Manages webhook subscriptions for partner integrations

CREATE TABLE IF NOT EXISTS webhook_subscriptions (
    -- Primary Key
    subscription_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Partner Information
    partner_id UUID NOT NULL,
    partner_name VARCHAR(255) NOT NULL,
    partner_api_key_hash VARCHAR(255), -- Hashed API key for verification
    
    -- Webhook Configuration
    webhook_url VARCHAR(2048) NOT NULL,
    webhook_secret VARCHAR(255) NOT NULL, -- Used for HMAC signature
    
    -- Event Subscription
    event_types JSONB NOT NULL, -- Array of subscribed event types
    event_filters JSONB, -- Optional filters (e.g., claim_type, risk_level)
    
    -- Delivery Settings
    delivery_method VARCHAR(20) DEFAULT 'POST' CHECK (delivery_method IN ('POST', 'PUT')),
    content_type VARCHAR(50) DEFAULT 'application/json',
    timeout_seconds INT DEFAULT 30 CHECK (timeout_seconds > 0 AND timeout_seconds <= 300),
    retry_policy JSONB, -- Retry configuration (max_retries, backoff_strategy)
    
    -- Status and Health
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    verification_token VARCHAR(255),
    verified_at TIMESTAMP,
    
    -- Rate Limiting
    rate_limit_per_minute INT DEFAULT 60,
    rate_limit_per_hour INT DEFAULT 1000,
    
    -- Monitoring
    last_triggered_at TIMESTAMP,
    last_success_at TIMESTAMP,
    last_failure_at TIMESTAMP,
    total_deliveries INT DEFAULT 0,
    successful_deliveries INT DEFAULT 0,
    failed_deliveries INT DEFAULT 0,
    consecutive_failures INT DEFAULT 0,
    
    -- Health Status
    health_status VARCHAR(20) DEFAULT 'HEALTHY' CHECK (
        health_status IN ('HEALTHY', 'DEGRADED', 'FAILING', 'SUSPENDED')
    ),
    health_check_at TIMESTAMP,
    
    -- Metadata
    description TEXT,
    tags JSONB, -- Array of tags for categorization
    custom_headers JSONB, -- Custom HTTP headers to include
    
    -- Audit Fields
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    created_by VARCHAR(255),
    updated_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_by VARCHAR(255),
    expires_at TIMESTAMP, -- Optional expiration date
    
    -- Constraints
    CONSTRAINT valid_url CHECK (webhook_url ~ '^https?://'),
    CONSTRAINT valid_rate_limits CHECK (
        rate_limit_per_minute > 0 AND 
        rate_limit_per_hour > 0 AND
        rate_limit_per_hour >= rate_limit_per_minute
    ),
    CONSTRAINT valid_delivery_counts CHECK (
        total_deliveries >= 0 AND
        successful_deliveries >= 0 AND
        failed_deliveries >= 0 AND
        consecutive_failures >= 0 AND
        total_deliveries = successful_deliveries + failed_deliveries
    )
);

-- Indexes for webhook_subscriptions table
CREATE INDEX idx_webhook_partner_id ON webhook_subscriptions(partner_id);
CREATE INDEX idx_webhook_is_active ON webhook_subscriptions(is_active) WHERE is_active = true;
CREATE INDEX idx_webhook_health_status ON webhook_subscriptions(health_status);
CREATE INDEX idx_webhook_created_at ON webhook_subscriptions(created_at DESC);
CREATE INDEX idx_webhook_expires_at ON webhook_subscriptions(expires_at) WHERE expires_at IS NOT NULL;

-- Inverted indexes for JSONB columns
CREATE INVERTED INDEX idx_webhook_event_types ON webhook_subscriptions(event_types);
CREATE INVERTED INDEX idx_webhook_event_filters ON webhook_subscriptions(event_filters);
CREATE INVERTED INDEX idx_webhook_tags ON webhook_subscriptions(tags);

-- ============================================================================
-- WEBHOOK_DELIVERY_LOG TABLE
-- ============================================================================
-- Tracks webhook delivery attempts for debugging and monitoring

CREATE TABLE IF NOT EXISTS webhook_delivery_log (
    -- Primary Key
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- References
    subscription_id UUID NOT NULL REFERENCES webhook_subscriptions(subscription_id) ON DELETE CASCADE,
    claim_id UUID REFERENCES claims(claim_id) ON DELETE SET NULL,
    
    -- Event Information
    event_type VARCHAR(100) NOT NULL,
    event_id UUID NOT NULL,
    event_timestamp TIMESTAMP NOT NULL DEFAULT now(),
    
    -- Delivery Details
    attempt_number INT NOT NULL DEFAULT 1,
    http_status_code INT,
    response_time_ms INT,
    
    -- Request/Response
    request_payload JSONB,
    request_headers JSONB,
    response_body TEXT,
    response_headers JSONB,
    
    -- Status
    delivery_status VARCHAR(20) NOT NULL CHECK (
        delivery_status IN ('PENDING', 'SUCCESS', 'FAILED', 'TIMEOUT', 'RETRYING')
    ),
    error_message TEXT,
    
    -- Timing
    delivered_at TIMESTAMP NOT NULL DEFAULT now(),
    next_retry_at TIMESTAMP,
    
    -- Audit
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

-- Indexes for webhook_delivery_log table
CREATE INDEX idx_webhook_log_subscription ON webhook_delivery_log(subscription_id, delivered_at DESC);
CREATE INDEX idx_webhook_log_claim ON webhook_delivery_log(claim_id) WHERE claim_id IS NOT NULL;
CREATE INDEX idx_webhook_log_event ON webhook_delivery_log(event_type, event_timestamp DESC);
CREATE INDEX idx_webhook_log_status ON webhook_delivery_log(delivery_status);
CREATE INDEX idx_webhook_log_retry ON webhook_delivery_log(next_retry_at) WHERE next_retry_at IS NOT NULL;

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

-- View for active webhook subscriptions with health metrics
CREATE VIEW active_webhook_subscriptions AS
SELECT 
    subscription_id,
    partner_name,
    webhook_url,
    event_types,
    health_status,
    total_deliveries,
    successful_deliveries,
    failed_deliveries,
    CASE 
        WHEN total_deliveries > 0 
        THEN ROUND((successful_deliveries::DECIMAL / total_deliveries) * 100, 2)
        ELSE 0 
    END AS success_rate_percent,
    last_triggered_at,
    created_at
FROM webhook_subscriptions
WHERE is_active = true
ORDER BY partner_name;

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

-- Insert sample webhook subscriptions
INSERT INTO webhook_subscriptions (
    partner_id, partner_name, webhook_url, webhook_secret,
    event_types, is_active, is_verified
) VALUES
    (gen_random_uuid(), 'Partner Insurance Co', 'https://partner1.example.com/webhooks/claims',
     'secret_key_123', '["claim.created", "claim.status_changed", "claim.approved"]'::JSONB,
     true, true),
    (gen_random_uuid(), 'Claims Analytics Platform', 'https://analytics.example.com/api/webhooks',
     'secret_key_456', '["claim.created", "claim.risk_assessed"]'::JSONB,
     true, true);

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE claims IS 'Stores insurance claim records with risk assessment and status tracking';
COMMENT ON COLUMN claims.risk_score IS 'Risk score from 0-100, where higher values indicate higher risk';
COMMENT ON COLUMN claims.status IS 'Current status of the claim in the processing workflow';
COMMENT ON COLUMN claims.fraud_indicators IS 'JSON array of detected fraud indicators';

COMMENT ON TABLE webhook_subscriptions IS 'Manages webhook subscriptions for partner integrations';
COMMENT ON COLUMN webhook_subscriptions.event_types IS 'JSON array of event types the partner subscribes to';
COMMENT ON COLUMN webhook_subscriptions.webhook_secret IS 'Secret used for HMAC signature verification';
COMMENT ON COLUMN webhook_subscriptions.health_status IS 'Current health status based on delivery success rate';

COMMENT ON TABLE webhook_delivery_log IS 'Audit log of all webhook delivery attempts';

-- Made with Bob
