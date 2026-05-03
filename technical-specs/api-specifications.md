# API Specifications

## Architecture Overview

The Insurance Claims Platform uses an **event-driven architecture** with Kafka for asynchronous message processing, rather than traditional REST/GraphQL APIs.

## Event-Driven Architecture

```
┌─────────────────┐
│ Confluent Cloud │
│  Kafka Cluster  │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼──┐  ┌──▼────────┐
│Ingest│  │ Processor │
│Topic │  │  Service  │
└──────┘  └──┬────────┘
             │
    ┌────────┴────────┐
    │                 │
┌───▼────┐  ┌────────▼──┐
│Approved│  │ Escalated │
│ Topic  │  │   Topic   │
└────────┘  └───────────┘
```

## Kafka Topics

### Input Topics

#### `claims.ingest`
**Purpose**: Entry point for new insurance claims

**Message Schema**:
```json
{
  "claimId": "CLM-2026-000001",
  "eventId": "550e8400-e29b-41d4-a716-446655440000",
  "eventTimestamp": 1714694400000,
  "policyNumber": "POL-2026-00001",
  "claimType": "AUTO_ACCIDENT",
  "incidentDate": 1714608000000,
  "description": "Rear-end collision at intersection during rush hour",
  "estimatedAmount": {
    "amount": 4500.00,
    "currency": "USD"
  },
  "riskScore": 45,
  "claimant": {
    "userId": "USER-000001",
    "name": "John Doe",
    "phone": "+1-555-0100",
    "email": "john@example.com"
  },
  "location": {
    "latitude": 43.6532,
    "longitude": -79.3832,
    "address": "123 Main St, Toronto, ON",
    "city": "Toronto",
    "state": "ON",
    "zipCode": "M5H 2N2",
    "country": "Canada"
  }
}
```

**Field Descriptions**:
- `claimId`: Unique claim identifier (format: CLM-YYYY-NNNNNN)
- `eventId`: UUID for event tracking
- `eventTimestamp`: Unix timestamp in milliseconds
- `policyNumber`: Associated policy number
- `claimType`: Type of claim (AUTO_ACCIDENT, PROPERTY_DAMAGE, etc.)
- `incidentDate`: Unix timestamp in milliseconds when incident occurred
- `description`: Detailed description of the incident
- `estimatedAmount`: Nested object with amount and currency
- `riskScore`: Risk assessment score (0-100)
- `claimant`: Nested object with claimant details
- `location`: Nested object with incident location details

**Producers**: External claim submission systems, mobile apps, web portals

**Consumers**: Claims Processor Service

### Output Topics

#### `claims.approved`
**Purpose**: Auto-approved claims (amount < $2,000 AND risk < 20)

**Message Schema**:
```json
{
  "claimId": "CLM-2026-000001",
  "claimNumber": "CLM-2026-000001",
  "policyNumber": "POL-2026-00001",
  "decision": "APPROVED",
  "reason": "Auto-approved: Amount $1500.00 < $2000.00 and Risk 15 < 20",
  "claimAmount": 1500.00,
  "riskScore": 15,
  "processedAt": "2026-05-02T16:57:45.123Z",
  "processedBy": "claims-processor"
}
```

**Field Descriptions**:
- `decision`: Always "APPROVED" for this topic (not "AUTO_APPROVED")
- `reason`: Detailed explanation of the auto-approval decision
- `processedBy`: Service name that processed the claim

**Producers**: Claims Processor Service

**Consumers**: Payment processing systems, notification services

#### `claims.processed`
**Purpose**: Claims requiring manual adjuster review

**Message Schema**:
```json
{
  "claimId": "CLM-2026-000002",
  "claimNumber": "CLM-2026-000002",
  "policyNumber": "POL-2026-00002",
  "decision": "UNDER_REVIEW",
  "reason": "Manual review required: Amount $5000.00 or Risk 45 outside auto-approval thresholds",
  "claimAmount": 5000.00,
  "riskScore": 45,
  "processedAt": "2026-05-02T17:15:30.456Z",
  "processedBy": "claims-processor"
}
```

**Field Descriptions**:
- `decision`: Always "UNDER_REVIEW" for this topic
- `reason`: Explanation of why manual review is required

**Producers**: Claims Processor Service

**Consumers**: Adjuster assignment systems, workflow management

#### `claims.escalated`
**Purpose**: High-risk claims requiring immediate attention (risk > 80)

**Message Schema**:
```json
{
  "claimId": "CLM-2026-000003",
  "claimNumber": "CLM-2026-000003",
  "policyNumber": "POL-2026-00003",
  "decision": "ESCALATED",
  "reason": "Escalated: High risk score 85 > 80",
  "claimAmount": 8000.00,
  "riskScore": 85,
  "processedAt": "2026-05-02T17:20:15.789Z",
  "processedBy": "claims-processor"
}
```

**Field Descriptions**:
- `decision`: Always "ESCALATED" for this topic
- `reason`: Specific reason for escalation with threshold comparison

**Producers**: Claims Processor Service

**Consumers**: Fraud investigation systems, senior adjuster queues

#### `claims.dlq` (Dead Letter Queue)
**Purpose**: Failed messages for error handling and replay

**Message Schema**:
```json
{
  "original_topic": "claims.ingest",
  "original_partition": 0,
  "original_offset": 12345,
  "original_value": "{...original message...}",
  "error_reason": "Policy verification failed: Policy not found",
  "failed_at": "2026-05-02T17:25:00.000Z"
}
```

**Producers**: Claims Processor Service

**Consumers**: Error monitoring systems, manual review queues

## Processing Logic

### AI Logic Gate Rules

The Claims Processor applies automated decision logic (from [`claims_processor.py`](../services/claims-processor/claims_processor.py:108)):

```python
# Rule 1: Auto-approve low-value, low-risk claims
if claim_amount < auto_approve_amount_threshold AND risk_score < auto_approve_risk_threshold:
    status = "APPROVED"  # Note: APPROVED, not AUTO_APPROVED
    topic = "claims.approved"
    reason = f"Auto-approved: Amount ${claim_amount:.2f} < ${threshold} and Risk {risk_score} < {threshold}"

# Rule 2: Escalate high-risk claims
elif risk_score > escalation_risk_threshold:
    status = "ESCALATED"
    topic = "claims.escalated"
    reason = f"Escalated: High risk score {risk_score} > {threshold}"

# Rule 3: Manual review for everything else
else:
    status = "UNDER_REVIEW"
    topic = "claims.processed"
    reason = f"Manual review required: Amount ${claim_amount:.2f} or Risk {risk_score} outside auto-approval thresholds"
```

**Important**: The status is `APPROVED` (not `AUTO_APPROVED`) to match the database constraint in [`schema.sql`](../database/schema.sql:69).

### Configuration Thresholds

| Threshold | Default | Environment Variable |
|-----------|---------|---------------------|
| Auto-Approve Amount | $2,000 | `AUTO_APPROVE_AMOUNT_THRESHOLD` |
| Auto-Approve Risk | 20 | `AUTO_APPROVE_RISK_THRESHOLD` |
| Escalation Risk | 80 | `ESCALATION_RISK_THRESHOLD` |

## Adjuster Agent Interface

### Chainlit Chat Interface

The Adjuster Agent provides a conversational interface for claim adjusters using Chainlit with WebSocket communication (internal to Chainlit, not exposed as API).

**Access**: `http://localhost:8000` (when running locally)

**Features**:
- Natural language claim queries
- Semantic similarity search
- Fraud pattern detection
- Real-time database queries

**Example Interactions**:

```
User: "Show me details for claim #1"
Agent: [Retrieves claim from CockroachDB and displays formatted response]

User: "Find claims similar to: car accident with rear-end collision"
Agent: [Uses vector embeddings to find semantically similar claims]

User: "Show me high-risk claims"
Agent: [Queries claims with risk_score > 70]
```

### Database Direct Access

The Adjuster Agent queries CockroachDB directly using:
- **psycopg2** for database connections
- **pgvector** for semantic similarity search
- **sentence-transformers** for embedding generation

## Data Storage

### CockroachDB Schema

```sql
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
    claim_type VARCHAR(50) NOT NULL,
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
    fraud_indicators JSONB,
    
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
    attachments JSONB,
    
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

-- Indexes
CREATE INDEX idx_claims_policy_number ON claims(policy_number);
CREATE INDEX idx_claims_status ON claims(status);
CREATE INDEX idx_claims_risk_score ON claims(risk_score);
CREATE INDEX idx_claims_claim_date ON claims(claim_date DESC);
CREATE INDEX idx_claims_assigned_adjuster ON claims(assigned_adjuster_id) WHERE assigned_adjuster_id IS NOT NULL;
CREATE INDEX idx_claims_claim_type ON claims(claim_type);
CREATE INDEX idx_claims_created_at ON claims(created_at DESC);
CREATE INVERTED INDEX idx_claims_fraud_indicators ON claims(fraud_indicators);

-- Vector embeddings for semantic search (added via migration)
-- description_embedding VECTOR(384)
-- embedding_model VARCHAR(100)
-- embedding_generated_at TIMESTAMP
-- CREATE INDEX idx_claims_embedding ON claims USING hnsw (description_embedding vector_cosine_ops);
```

**Valid Status Values** (from database constraint):
- `SUBMITTED` - Initial state when claim is received
- `UNDER_REVIEW` - Requires manual adjuster review
- `INVESTIGATING` - Under active investigation
- `PENDING_DOCUMENTS` - Waiting for additional documentation
- `APPROVED` - Claim has been approved (includes auto-approved)
- `REJECTED` - Claim has been rejected
- `PAID` - Payment has been processed
- `CLOSED` - Claim is closed
- `ESCALATED` - High-risk claim escalated to senior adjuster
- `SUSPENDED` - Claim processing suspended

**Valid Claim Types** (from database constraint):
- `auto` - Auto/vehicle claims
- `property` - Property damage claims
- `health` - Health/medical claims
- `life` - Life insurance claims
- `liability` - Liability claims
- `other` - Other claim types

## Integration Patterns

### Producer Integration

To submit claims to the platform:

1. **Connect to Confluent Cloud Kafka**:
```python
from confluent_kafka import Producer

config = {
    'bootstrap.servers': 'pkc-4rn2p.canadacentral.azure.confluent.cloud:9092',
    'security.protocol': 'SASL_SSL',
    'sasl.mechanism': 'PLAIN',
    'sasl.username': 'YOUR_API_KEY',
    'sasl.password': 'YOUR_API_SECRET'
}

producer = Producer(config)
```

2. **Produce claim message**:
```python
import json

claim = {
    "claimId": "CLM-2026-000001",
    "policyNumber": "POL-789012",
    "claimant_name": "John Doe",
    "claim_amount": 4500.00,
    "risk_score": 45,
    # ... other fields
}

producer.produce(
    topic='claims.ingest',
    key=claim['claimId'].encode('utf-8'),
    value=json.dumps(claim).encode('utf-8')
)

producer.flush()
```

### Consumer Integration

To consume processed claims:

```python
from confluent_kafka import Consumer

config = {
    'bootstrap.servers': 'pkc-4rn2p.canadacentral.azure.confluent.cloud:9092',
    'security.protocol': 'SASL_SSL',
    'sasl.mechanism': 'PLAIN',
    'sasl.username': 'YOUR_API_KEY',
    'sasl.password': 'YOUR_API_SECRET',
    'group.id': 'your-consumer-group',
    'auto.offset.reset': 'earliest'
}

consumer = Consumer(config)
consumer.subscribe(['claims.approved', 'claims.escalated', 'claims.processed'])

while True:
    msg = consumer.poll(timeout=1.0)
    if msg is None:
        continue
    
    if msg.error():
        print(f"Error: {msg.error()}")
        continue
    
    claim_data = json.loads(msg.value().decode('utf-8'))
    # Process claim data
    print(f"Received: {claim_data['claimNumber']} - {claim_data['decision']}")
```

## Monitoring & Observability

### Structured Logging

All services use structured JSON logging:

```json
{
  "event": "claim_processed",
  "timestamp": "2026-05-02T16:57:45.123Z",
  "claim_number": "CLM-2026-000001",
  "decision": "AUTO_APPROVED",
  "next_topic": "claims.approved",
  "processing_time_ms": 145
}
```

### Key Metrics

- **Throughput**: Claims processed per second
- **Latency**: Time from ingest to decision
- **Error Rate**: Percentage of claims sent to DLQ
- **Decision Distribution**: AUTO_APPROVED vs UNDER_REVIEW vs ESCALATED

### Kafka Monitoring

Monitor via Confluent Cloud Console:
- Topic lag
- Consumer group health
- Message throughput
- Partition distribution

## Security

### Authentication

- **Kafka**: SASL/PLAIN with API keys
- **Database**: SSL/TLS with username/password
- **Chainlit**: Session-based (internal)

### Data Protection

- All Kafka connections use SSL/TLS
- Database connections use SSL mode `verify-full`
- Credentials stored in environment variables
- No hardcoded secrets in code

## Error Handling

### Retry Strategy

1. **Kafka Consumer**: Manual commit for at-least-once delivery
2. **Database Operations**: Transactional with rollback
3. **Failed Messages**: Sent to DLQ with error details

### Dead Letter Queue Processing

Monitor `claims.dlq` for:
- Policy verification failures
- Database connection errors
- Invalid message formats
- Processing timeouts

## Performance Characteristics

### Throughput

- **Claims Processor**: ~1000 claims/second per instance
- **Database Writes**: ~500 writes/second
- **Semantic Search**: ~100 queries/second

### Latency

- **End-to-end Processing**: < 500ms (p95)
- **Database Query**: < 100ms (p95)
- **Vector Search**: < 1s for 10 results

## Future Enhancements

### Planned Features

1. **REST API Layer** (Future)
   - Synchronous claim submission endpoint
   - Status query API
   - Webhook notifications

2. **GraphQL API** (Future)
   - Flexible claim queries
   - Real-time subscriptions
   - Batch operations

3. **WebSocket Notifications** (Future)
   - Real-time claim status updates
   - Push notifications to adjusters
   - Live dashboard updates

## Migration Notes

This document reflects the **current event-driven architecture**. Previous versions of this specification described REST and GraphQL APIs that were never implemented. The platform was designed from the ground up as an event-driven system using Kafka for asynchronous message processing.

## Support

For integration questions or issues:
- Review Kafka topic schemas above
- Check Confluent Cloud console for connectivity
- Verify database schema matches specification
- Contact: claims-platform@insurance.com

---

**Last Updated**: 2026-05-03  
**Version**: 2.0 (Event-Driven Architecture)  
**Previous Version**: 1.0 (Proposed REST/GraphQL - Never Implemented)