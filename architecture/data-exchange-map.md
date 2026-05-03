# Data Exchange Map: Mobile App → Confluent → CockroachDB

## Overview
This document details the complete data flow from claim submission through event streaming to persistent storage, including message formats, transformations, and data contracts.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MOBILE APP (PRODUCER)                               │
│                                                                              │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐             │
│  │   Claim      │      │   Photo      │      │  Validation  │             │
│  │   Form UI    │─────▶│   Capture    │─────▶│   Layer      │             │
│  └──────────────┘      └──────────────┘      └──────┬───────┘             │
│                                                       │                      │
│                                                       ▼                      │
│                                              ┌────────────────┐             │
│                                              │  Claims API    │             │
│                                              │  Client SDK    │             │
│                                              └────────┬───────┘             │
└───────────────────────────────────────────────────────┼──────────────────────┘
                                                        │
                                                        │ HTTPS/TLS 1.3
                                                        │ JSON Payload
                                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        API GATEWAY / LOAD BALANCER                           │
│                                                                              │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐             │
│  │     Auth     │      │     Rate     │      │   Request    │             │
│  │  Validation  │─────▶│   Limiting   │─────▶│   Routing    │             │
│  └──────────────┘      └──────────────┘      └──────┬───────┘             │
└───────────────────────────────────────────────────────┼──────────────────────┘
                                                        │
                                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CLAIMS INGESTION SERVICE                                │
│                                                                              │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐             │
│  │   Schema     │      │   Enrich     │      │   Kafka      │             │
│  │  Validation  │─────▶│   Metadata   │─────▶│   Producer   │             │
│  └──────────────┘      └──────────────┘      └──────┬───────┘             │
└───────────────────────────────────────────────────────┼──────────────────────┘
                                                        │
                                                        │ Avro/Protobuf
                                                        │ Serialization
                                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CONFLUENT KAFKA (STREAM)                             │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────┐        │
│  │                    TOPIC: claims.submitted                      │        │
│  │  Partitions: 12 | Replication: 3 | Retention: 30 days         │        │
│  └────────────────────────────┬───────────────────────────────────┘        │
│                                │                                             │
│                                ├──────────────┐                             │
│                                │              │                             │
│                                ▼              ▼                             │
│  ┌──────────────────────────────┐  ┌──────────────────────────┐           │
│  │  TOPIC: claims.high-value    │  │ TOPIC: claims.standard   │           │
│  │  (Amount > $5,000)           │  │ (Amount ≤ $5,000)        │           │
│  │  Partitions: 6               │  │ Partitions: 12           │           │
│  └──────────────┬───────────────┘  └────────────┬─────────────┘           │
│                 │                                │                          │
└─────────────────┼────────────────────────────────┼──────────────────────────┘
                  │                                │
                  │                                │
                  ▼                                ▼
┌─────────────────────────────────┐  ┌─────────────────────────────────┐
│   CLAIMS ADJUSTER AGENT         │  │   CLAIMS ADJUSTER AGENT         │
│   (High-Value Consumer)         │  │   (Standard Consumer)           │
│                                 │  │                                 │
│  ┌──────────────┐              │  │  ┌──────────────┐              │
│  │   Fraud      │              │  │  │  Automated   │              │
│  │   Detection  │              │  │  │   Approval   │              │
│  └──────┬───────┘              │  │  └──────┬───────┘              │
│         │                       │  │         │                       │
│         ▼                       │  │         ▼                       │
│  ┌──────────────┐              │  │  ┌──────────────┐              │
│  │   Human      │              │  │  │   Auto       │              │
│  │  Escalation  │              │  │  │  Settlement  │              │
│  └──────┬───────┘              │  │  └──────┬───────┘              │
└─────────┼────────────────────────┘  └─────────┼────────────────────────┘
          │                                      │
          │                                      │
          └──────────────┬───────────────────────┘
                         │
                         │ JDBC/SQL
                         │ Transactional Writes
                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        COCKROACHDB (VAULT)                                   │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────┐        │
│  │                      DATABASE: claims_db                        │        │
│  │                                                                  │        │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │        │
│  │  │   claims     │  │  claim_      │  │   claim_     │         │        │
│  │  │   (master)   │  │  events      │  │  documents   │         │        │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │        │
│  │         │                  │                  │                  │        │
│  │         └──────────────────┴──────────────────┘                  │        │
│  │                            │                                     │        │
│  │  ┌──────────────┐  ┌──────▼───────┐  ┌──────────────┐         │        │
│  │  │  adjusters   │  │   audit_     │  │  escalations │         │        │
│  │  │              │  │   trail      │  │              │         │        │
│  │  └──────────────┘  └──────────────┘  └──────────────┘         │        │
│  │                                                                  │        │
│  │  Multi-Region: us-east-1, us-west-2, eu-west-1                │        │
│  │  Replication: 3x per region                                    │        │
│  └────────────────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Stages

### Stage 1: Mobile App → API Gateway

**Protocol**: HTTPS/TLS 1.3  
**Format**: JSON  
**Authentication**: OAuth 2.0 + JWT

#### Request Payload Example
```json
{
  "claim": {
    "policyNumber": "POL-2026-123456",
    "claimType": "AUTO_ACCIDENT",
    "incidentDate": "2026-05-01T14:30:00Z",
    "location": {
      "latitude": 40.7128,
      "longitude": -74.0060,
      "address": "123 Main St, New York, NY 10001"
    },
    "description": "Rear-end collision at intersection",
    "estimatedAmount": 7500.00,
    "currency": "USD"
  },
  "claimant": {
    "userId": "USR-789012",
    "name": "John Doe",
    "phone": "+1-555-0123",
    "email": "john.doe@example.com"
  },
  "attachments": [
    {
      "type": "PHOTO",
      "filename": "damage_front.jpg",
      "size": 2048576,
      "mimeType": "image/jpeg",
      "s3Key": "claims/2026/05/01/abc123.jpg"
    },
    {
      "type": "POLICE_REPORT",
      "filename": "police_report.pdf",
      "size": 512000,
      "mimeType": "application/pdf",
      "s3Key": "claims/2026/05/01/def456.pdf"
    }
  ],
  "metadata": {
    "appVersion": "2.5.1",
    "deviceId": "DEVICE-XYZ789",
    "platform": "iOS",
    "submittedAt": "2026-05-01T14:35:22Z"
  }
}
```

#### Response
```json
{
  "claimId": "CLM-2026050114352201",
  "status": "SUBMITTED",
  "message": "Claim submitted successfully",
  "estimatedProcessingTime": "2-4 hours",
  "trackingUrl": "https://claims.insurance.com/track/CLM-2026050114352201"
}
```

---

### Stage 2: API Gateway → Kafka Producer

**Transformation**: JSON → Avro/Protobuf  
**Enrichment**: Add system metadata, generate IDs, validate schema

#### Kafka Message Schema (Avro)
```json
{
  "type": "record",
  "name": "ClaimSubmitted",
  "namespace": "com.insurance.claims.events",
  "fields": [
    {
      "name": "claimId",
      "type": "string",
      "doc": "Unique claim identifier"
    },
    {
      "name": "eventId",
      "type": "string",
      "doc": "Unique event identifier (UUID)"
    },
    {
      "name": "eventTimestamp",
      "type": "long",
      "logicalType": "timestamp-millis"
    },
    {
      "name": "eventVersion",
      "type": "string",
      "default": "1.0"
    },
    {
      "name": "policyNumber",
      "type": "string"
    },
    {
      "name": "claimType",
      "type": {
        "type": "enum",
        "name": "ClaimType",
        "symbols": ["AUTO_ACCIDENT", "PROPERTY_DAMAGE", "HEALTH", "LIFE", "OTHER"]
      }
    },
    {
      "name": "incidentDate",
      "type": "long",
      "logicalType": "timestamp-millis"
    },
    {
      "name": "location",
      "type": {
        "type": "record",
        "name": "Location",
        "fields": [
          {"name": "latitude", "type": "double"},
          {"name": "longitude", "type": "double"},
          {"name": "address", "type": "string"}
        ]
      }
    },
    {
      "name": "description",
      "type": "string"
    },
    {
      "name": "estimatedAmount",
      "type": {
        "type": "record",
        "name": "Money",
        "fields": [
          {"name": "amount", "type": "double"},
          {"name": "currency", "type": "string", "default": "USD"}
        ]
      }
    },
    {
      "name": "claimant",
      "type": {
        "type": "record",
        "name": "Claimant",
        "fields": [
          {"name": "userId", "type": "string"},
          {"name": "name", "type": "string"},
          {"name": "phone", "type": "string"},
          {"name": "email", "type": "string"}
        ]
      }
    },
    {
      "name": "attachments",
      "type": {
        "type": "array",
        "items": {
          "type": "record",
          "name": "Attachment",
          "fields": [
            {"name": "type", "type": "string"},
            {"name": "filename", "type": "string"},
            {"name": "size", "type": "long"},
            {"name": "mimeType", "type": "string"},
            {"name": "s3Key", "type": "string"}
          ]
        }
      }
    },
    {
      "name": "metadata",
      "type": {
        "type": "record",
        "name": "Metadata",
        "fields": [
          {"name": "appVersion", "type": "string"},
          {"name": "deviceId", "type": "string"},
          {"name": "platform", "type": "string"},
          {"name": "submittedAt", "type": "long", "logicalType": "timestamp-millis"},
          {"name": "ipAddress", "type": ["null", "string"], "default": null},
          {"name": "userAgent", "type": ["null", "string"], "default": null}
        ]
      }
    }
  ]
}
```

---

### Stage 3: Kafka Topics & Stream Processing

#### Topic Configuration

| Topic Name | Partitions | Replication | Retention | Compression | Use Case |
|------------|------------|-------------|-----------|-------------|----------|
| `claims.submitted` | 12 | 3 | 30 days | snappy | All incoming claims |
| `claims.high-value` | 6 | 3 | 90 days | lz4 | Claims > $5,000 |
| `claims.standard` | 12 | 3 | 30 days | snappy | Claims ≤ $5,000 |
| `claims.approved` | 8 | 3 | 365 days | lz4 | Approved claims |
| `claims.rejected` | 4 | 3 | 365 days | lz4 | Rejected claims |
| `claims.escalated` | 4 | 3 | 365 days | lz4 | Escalated to human |
| `claims.events` | 12 | 3 | 365 days | lz4 | All claim events (audit) |

#### Stream Processing Logic (Kafka Streams)

```java
// Pseudo-code for stream routing
StreamsBuilder builder = new StreamsBuilder();

KStream<String, ClaimSubmitted> submittedClaims = 
    builder.stream("claims.submitted");

// Branch based on claim amount
KStream<String, ClaimSubmitted>[] branches = submittedClaims.branch(
    (key, claim) -> claim.getEstimatedAmount().getAmount() > 5000.0,  // High-value
    (key, claim) -> true  // Standard
);

// Route to appropriate topics
branches[0].to("claims.high-value");
branches[1].to("claims.standard");

// Enrich with policy data
KStream<String, EnrichedClaim> enrichedClaims = submittedClaims
    .leftJoin(
        policyTable,
        (claim, policy) -> enrichClaim(claim, policy),
        Joined.with(Serdes.String(), claimSerde, policySerde)
    );

// Write all events to audit trail
submittedClaims
    .mapValues(claim -> toAuditEvent(claim))
    .to("claims.events");
```

---

### Stage 4: Kafka → Claims Adjuster Agent

**Consumer Groups**:
- `claims-adjuster-high-value-group` (3 instances)
- `claims-adjuster-standard-group` (6 instances)

**Processing Pattern**: At-least-once delivery with idempotency

#### Consumer Configuration
```properties
group.id=claims-adjuster-high-value-group
enable.auto.commit=false
auto.offset.reset=earliest
max.poll.records=100
max.poll.interval.ms=300000
session.timeout.ms=30000
isolation.level=read_committed
```

#### Message Processing Flow
1. **Consume**: Read message from Kafka topic
2. **Deserialize**: Convert Avro → Java object
3. **Validate**: Check business rules and data integrity
4. **Process**: Execute agent logic (triage, fraud detection, etc.)
5. **Persist**: Write to CockroachDB
6. **Commit**: Acknowledge Kafka offset
7. **Publish**: Emit downstream events if needed

---

### Stage 5: Agent → CockroachDB

**Protocol**: PostgreSQL wire protocol (JDBC)  
**Connection Pool**: HikariCP (min: 10, max: 50 per instance)  
**Transaction Isolation**: SERIALIZABLE

#### Database Schema

```sql
-- Claims master table
CREATE TABLE claims (
    claim_id VARCHAR(50) PRIMARY KEY,
    policy_number VARCHAR(50) NOT NULL,
    claim_type VARCHAR(50) NOT NULL,
    incident_date TIMESTAMPTZ NOT NULL,
    location_lat DECIMAL(10, 8),
    location_lng DECIMAL(11, 8),
    location_address TEXT,
    description TEXT,
    estimated_amount DECIMAL(15, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(50) NOT NULL,
    assigned_adjuster_id VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_policy_number (policy_number),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at DESC),
    INDEX idx_amount (estimated_amount)
);

-- Claimant information
CREATE TABLE claimants (
    claimant_id VARCHAR(50) PRIMARY KEY,
    claim_id VARCHAR(50) NOT NULL REFERENCES claims(claim_id),
    user_id VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_claim_id (claim_id),
    INDEX idx_user_id (user_id)
);

-- Claim events (event sourcing)
CREATE TABLE claim_events (
    event_id VARCHAR(50) PRIMARY KEY,
    claim_id VARCHAR(50) NOT NULL REFERENCES claims(claim_id),
    event_type VARCHAR(50) NOT NULL,
    event_timestamp TIMESTAMPTZ NOT NULL,
    event_data JSONB NOT NULL,
    actor_id VARCHAR(50),
    actor_type VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_claim_id (claim_id),
    INDEX idx_event_type (event_type),
    INDEX idx_event_timestamp (event_timestamp DESC)
);

-- Attachments/documents
CREATE TABLE claim_documents (
    document_id VARCHAR(50) PRIMARY KEY,
    claim_id VARCHAR(50) NOT NULL REFERENCES claims(claim_id),
    document_type VARCHAR(50) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100),
    s3_key VARCHAR(500) NOT NULL,
    uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_claim_id (claim_id)
);

-- Escalations
CREATE TABLE escalations (
    escalation_id VARCHAR(50) PRIMARY KEY,
    claim_id VARCHAR(50) NOT NULL REFERENCES claims(claim_id),
    reason VARCHAR(255) NOT NULL,
    escalated_from VARCHAR(50),
    escalated_to VARCHAR(50),
    priority VARCHAR(20) DEFAULT 'MEDIUM',
    status VARCHAR(50) DEFAULT 'PENDING',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    INDEX idx_claim_id (claim_id),
    INDEX idx_status (status),
    INDEX idx_priority (priority)
);

-- Audit trail
CREATE TABLE audit_trail (
    audit_id VARCHAR(50) PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    actor_id VARCHAR(50),
    actor_type VARCHAR(50),
    changes JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT,
    INDEX idx_entity (entity_type, entity_id),
    INDEX idx_timestamp (timestamp DESC)
);
```

#### Write Pattern Example

```java
// Transactional write with event sourcing
@Transactional
public void processClaim(ClaimSubmitted event) {
    // 1. Insert claim record
    Claim claim = new Claim();
    claim.setClaimId(event.getClaimId());
    claim.setPolicyNumber(event.getPolicyNumber());
    claim.setEstimatedAmount(event.getEstimatedAmount().getAmount());
    claim.setStatus("SUBMITTED");
    claimRepository.save(claim);
    
    // 2. Insert claimant
    Claimant claimant = new Claimant();
    claimant.setClaimId(event.getClaimId());
    claimant.setUserId(event.getClaimant().getUserId());
    claimant.setName(event.getClaimant().getName());
    claimantRepository.save(claimant);
    
    // 3. Insert event record
    ClaimEvent claimEvent = new ClaimEvent();
    claimEvent.setEventId(event.getEventId());
    claimEvent.setClaimId(event.getClaimId());
    claimEvent.setEventType("CLAIM_SUBMITTED");
    claimEvent.setEventData(toJson(event));
    claimEventRepository.save(claimEvent);
    
    // 4. Insert documents
    for (Attachment attachment : event.getAttachments()) {
        ClaimDocument doc = new ClaimDocument();
        doc.setClaimId(event.getClaimId());
        doc.setDocumentType(attachment.getType());
        doc.setS3Key(attachment.getS3Key());
        documentRepository.save(doc);
    }
    
    // 5. Audit trail
    auditService.log("CLAIM", event.getClaimId(), "CREATED", event.getClaimant().getUserId());
}
```

---

## Data Consistency & Reliability

### Exactly-Once Semantics
- **Kafka Transactions**: Enable idempotent producer and transactional writes
- **Database Idempotency**: Use unique constraint on `event_id` to prevent duplicates
- **Offset Management**: Commit Kafka offsets only after successful DB write

### Error Handling
```java
try {
    // Process message
    processClaim(claimEvent);
    
    // Commit offset
    consumer.commitSync();
    
} catch (RecoverableException e) {
    // Retry with exponential backoff
    retryWithBackoff(claimEvent, e);
    
} catch (NonRecoverableException e) {
    // Send to dead letter queue
    sendToDeadLetterQueue(claimEvent, e);
    
    // Commit offset to move forward
    consumer.commitSync();
}
```

### Dead Letter Queue
- **Topic**: `claims.dlq`
- **Retention**: 90 days
- **Monitoring**: Alert on DLQ message count > 10

---

## Performance Characteristics

### Throughput
- **Mobile App → Kafka**: 10,000 claims/minute
- **Kafka → Agent**: 15,000 messages/second (across all consumers)
- **Agent → CockroachDB**: 5,000 writes/second

### Latency (p95)
- **End-to-End (Submit → DB)**: < 2 seconds
- **Mobile App → Kafka**: < 200ms
- **Kafka → Agent Processing**: < 500ms
- **Agent → CockroachDB Write**: < 300ms

### Data Volume
- **Average Message Size**: 5 KB
- **Daily Volume**: ~14.4 million claims
- **Monthly Storage Growth**: ~2.2 TB (compressed)

---

## Monitoring & Observability

### Key Metrics
1. **Producer Metrics**
   - Message send rate
   - Send latency (p50, p95, p99)
   - Error rate

2. **Kafka Metrics**
   - Consumer lag per partition
   - Messages in/out per second
   - Replication lag

3. **Consumer Metrics**
   - Processing time per message
   - Commit rate
   - Rebalance frequency

4. **Database Metrics**
   - Write throughput
   - Query latency
   - Connection pool utilization
   - Replication lag

### Alerting Thresholds
- Consumer lag > 10,000 messages
- Processing latency p95 > 5 seconds
- Error rate > 1%
- Database connection pool > 80% utilized

---

## Security Considerations

### Data in Transit
- TLS 1.3 for all connections
- mTLS between services
- Kafka SASL/SCRAM authentication

### Data at Rest
- Kafka: Encryption at rest enabled
- CockroachDB: Transparent data encryption (TDE)
- S3: Server-side encryption (SSE-KMS)

### Access Control
- Kafka ACLs per topic and consumer group
- CockroachDB role-based access control
- API Gateway OAuth 2.0 + JWT

### Compliance
- PII data encrypted in database
- Audit trail for all data access
- Data retention policies enforced
- GDPR right-to-erasure support

---

## Disaster Recovery

### Backup Strategy
- **Kafka**: Multi-region replication
- **CockroachDB**: Automated backups every 6 hours, retained for 30 days
- **S3 Documents**: Cross-region replication

### Recovery Objectives
- **RPO (Recovery Point Objective)**: < 5 minutes
- **RTO (Recovery Time Objective)**: < 30 minutes

### Failover Procedures
1. Kafka: Automatic leader election
2. CockroachDB: Automatic failover to replica
3. Application: Health checks trigger pod restart
