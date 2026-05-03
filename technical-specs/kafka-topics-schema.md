# Kafka Topics & Schema Specifications

## Overview
This document defines all Kafka topics, their configurations, message schemas, and data contracts for the insurance claims platform.

---

## Topic Inventory

### Production Topics

| Topic Name | Purpose | Partitions | Replication | Retention | Consumers |
|------------|---------|------------|-------------|-----------|-----------|
| `claims.submitted` | All incoming claims | 12 | 3 | 30 days | Stream processor |
| `claims.high-value` | Claims > $5,000 | 6 | 3 | 90 days | High-value agent |
| `claims.standard` | Claims ≤ $5,000 | 12 | 3 | 30 days | Standard agent |
| `claims.processed` | Processed claims | 8 | 3 | 90 days | Analytics, Reporting |
| `claims.approved` | Approved claims | 8 | 3 | 365 days | Payment service |
| `claims.rejected` | Rejected claims | 4 | 3 | 365 days | Notification service |
| `claims.escalated` | Escalated claims | 4 | 3 | 365 days | Human review system |
| `claims.events` | All claim events (audit) | 12 | 3 | 365 days | Audit service |
| `claims.dlq` | Dead letter queue | 4 | 3 | 90 days | Error handler |

### Configuration Details

```yaml
topics:
  claims.submitted:
    partitions: 12
    replication_factor: 3
    config:
      compression.type: snappy
      retention.ms: 2592000000  # 30 days
      min.insync.replicas: 2
      cleanup.policy: delete
      segment.ms: 86400000  # 1 day
      
  claims.high-value:
    partitions: 6
    replication_factor: 3
    config:
      compression.type: lz4
      retention.ms: 7776000000  # 90 days
      min.insync.replicas: 2
      cleanup.policy: delete
      
  claims.events:
    partitions: 12
    replication_factor: 3
    config:
      compression.type: lz4
      retention.ms: 31536000000  # 365 days
      min.insync.replicas: 2
      cleanup.policy: delete
      segment.ms: 86400000
```

---

## Message Schemas

### 1. ClaimSubmitted Event

**Topic**: `claims.submitted`  
**Format**: Avro  
**Version**: 1.0

```json
{
  "type": "record",
  "name": "ClaimSubmitted",
  "namespace": "com.insurance.claims.events.v1",
  "doc": "Event published when a new claim is submitted",
  "fields": [
    {
      "name": "claimId",
      "type": "string",
      "doc": "Unique claim identifier (format: CLM-YYYYMMDDHHMMSSNN)"
    },
    {
      "name": "eventId",
      "type": "string",
      "doc": "Unique event identifier (UUID v4)"
    },
    {
      "name": "eventTimestamp",
      "type": "long",
      "logicalType": "timestamp-millis",
      "doc": "Event creation timestamp in milliseconds since epoch"
    },
    {
      "name": "eventVersion",
      "type": "string",
      "default": "1.0",
      "doc": "Schema version"
    },
    {
      "name": "policyNumber",
      "type": "string",
      "doc": "Insurance policy number"
    },
    {
      "name": "claimType",
      "type": {
        "type": "enum",
        "name": "ClaimType",
        "symbols": [
          "AUTO_ACCIDENT",
          "PROPERTY_DAMAGE",
          "HEALTH",
          "LIFE",
          "THEFT",
          "NATURAL_DISASTER",
          "LIABILITY",
          "OTHER"
        ]
      },
      "doc": "Type of insurance claim"
    },
    {
      "name": "incidentDate",
      "type": "long",
      "logicalType": "timestamp-millis",
      "doc": "Date and time when the incident occurred"
    },
    {
      "name": "location",
      "type": {
        "type": "record",
        "name": "Location",
        "fields": [
          {
            "name": "latitude",
            "type": "double",
            "doc": "Latitude coordinate"
          },
          {
            "name": "longitude",
            "type": "double",
            "doc": "Longitude coordinate"
          },
          {
            "name": "address",
            "type": "string",
            "doc": "Full address of incident location"
          },
          {
            "name": "city",
            "type": ["null", "string"],
            "default": null
          },
          {
            "name": "state",
            "type": ["null", "string"],
            "default": null
          },
          {
            "name": "zipCode",
            "type": ["null", "string"],
            "default": null
          },
          {
            "name": "country",
            "type": "string",
            "default": "USA"
          }
        ]
      },
      "doc": "Location where the incident occurred"
    },
    {
      "name": "description",
      "type": "string",
      "doc": "Detailed description of the incident"
    },
    {
      "name": "estimatedAmount",
      "type": {
        "type": "record",
        "name": "Money",
        "fields": [
          {
            "name": "amount",
            "type": "double",
            "doc": "Monetary amount"
          },
          {
            "name": "currency",
            "type": "string",
            "default": "USD",
            "doc": "ISO 4217 currency code"
          }
        ]
      },
      "doc": "Estimated claim amount"
    },
    {
      "name": "claimant",
      "type": {
        "type": "record",
        "name": "Claimant",
        "fields": [
          {
            "name": "userId",
            "type": "string",
            "doc": "Unique user identifier"
          },
          {
            "name": "name",
            "type": "string",
            "doc": "Full name of claimant"
          },
          {
            "name": "phone",
            "type": "string",
            "doc": "Contact phone number"
          },
          {
            "name": "email",
            "type": "string",
            "doc": "Contact email address"
          },
          {
            "name": "dateOfBirth",
            "type": ["null", "long"],
            "logicalType": "timestamp-millis",
            "default": null
          }
        ]
      },
      "doc": "Information about the person filing the claim"
    },
    {
      "name": "attachments",
      "type": {
        "type": "array",
        "items": {
          "type": "record",
          "name": "Attachment",
          "fields": [
            {
              "name": "attachmentId",
              "type": "string",
              "doc": "Unique attachment identifier"
            },
            {
              "name": "type",
              "type": {
                "type": "enum",
                "name": "AttachmentType",
                "symbols": [
                  "PHOTO",
                  "VIDEO",
                  "POLICE_REPORT",
                  "MEDICAL_REPORT",
                  "REPAIR_ESTIMATE",
                  "INVOICE",
                  "OTHER_DOCUMENT"
                ]
              }
            },
            {
              "name": "filename",
              "type": "string"
            },
            {
              "name": "size",
              "type": "long",
              "doc": "File size in bytes"
            },
            {
              "name": "mimeType",
              "type": "string"
            },
            {
              "name": "s3Key",
              "type": "string",
              "doc": "S3 object key for the file"
            },
            {
              "name": "uploadedAt",
              "type": "long",
              "logicalType": "timestamp-millis"
            }
          ]
        }
      },
      "doc": "List of supporting documents"
    },
    {
      "name": "metadata",
      "type": {
        "type": "record",
        "name": "SubmissionMetadata",
        "fields": [
          {
            "name": "appVersion",
            "type": "string",
            "doc": "Mobile app version"
          },
          {
            "name": "deviceId",
            "type": "string",
            "doc": "Device identifier"
          },
          {
            "name": "platform",
            "type": {
              "type": "enum",
              "name": "Platform",
              "symbols": ["iOS", "Android", "Web"]
            }
          },
          {
            "name": "submittedAt",
            "type": "long",
            "logicalType": "timestamp-millis"
          },
          {
            "name": "ipAddress",
            "type": ["null", "string"],
            "default": null
          },
          {
            "name": "userAgent",
            "type": ["null", "string"],
            "default": null
          },
          {
            "name": "sessionId",
            "type": ["null", "string"],
            "default": null
          }
        ]
      },
      "doc": "Submission metadata"
    }
  ]
}
```

---

### 2. ClaimProcessed Event

**Topic**: `claims.processed`  
**Format**: Avro  
**Version**: 1.0

```json
{
  "type": "record",
  "name": "ClaimProcessed",
  "namespace": "com.insurance.claims.events.v1",
  "doc": "Event published when a claim has been processed by the agent",
  "fields": [
    {
      "name": "claimId",
      "type": "string"
    },
    {
      "name": "eventId",
      "type": "string"
    },
    {
      "name": "eventTimestamp",
      "type": "long",
      "logicalType": "timestamp-millis"
    },
    {
      "name": "processedBy",
      "type": "string",
      "doc": "Agent ID that processed the claim"
    },
    {
      "name": "processingDuration",
      "type": "long",
      "doc": "Processing time in milliseconds"
    },
    {
      "name": "fraudScore",
      "type": "double",
      "doc": "Fraud detection score (0.0 - 1.0)"
    },
    {
      "name": "fraudRiskLevel",
      "type": {
        "type": "enum",
        "name": "RiskLevel",
        "symbols": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
      }
    },
    {
      "name": "riskScore",
      "type": "int",
      "doc": "Overall risk score (0-100)"
    },
    {
      "name": "decision",
      "type": {
        "type": "record",
        "name": "Decision",
        "fields": [
          {
            "name": "action",
            "type": {
              "type": "enum",
              "name": "DecisionAction",
              "symbols": ["APPROVE", "REJECT", "ESCALATE", "REQUEST_INFO"]
            }
          },
          {
            "name": "reason",
            "type": "string"
          },
          {
            "name": "confidence",
            "type": "double",
            "doc": "Decision confidence (0.0 - 1.0)"
          },
          {
            "name": "escalatedTo",
            "type": ["null", "string"],
            "default": null,
            "doc": "Role or person escalated to"
          },
          {
            "name": "priority",
            "type": ["null", {
              "type": "enum",
              "name": "Priority",
              "symbols": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            }],
            "default": null
          }
        ]
      }
    },
    {
      "name": "validationResults",
      "type": {
        "type": "record",
        "name": "ValidationResults",
        "fields": [
          {
            "name": "policyValid",
            "type": "boolean"
          },
          {
            "name": "coverageAdequate",
            "type": "boolean"
          },
          {
            "name": "documentsComplete",
            "type": "boolean"
          },
          {
            "name": "errors",
            "type": {
              "type": "array",
              "items": "string"
            },
            "default": []
          }
        ]
      }
    }
  ]
}
```

---

### 3. ClaimApproved Event

**Topic**: `claims.approved`  
**Format**: Avro  
**Version**: 1.0

```json
{
  "type": "record",
  "name": "ClaimApproved",
  "namespace": "com.insurance.claims.events.v1",
  "doc": "Event published when a claim is approved",
  "fields": [
    {
      "name": "claimId",
      "type": "string"
    },
    {
      "name": "eventId",
      "type": "string"
    },
    {
      "name": "eventTimestamp",
      "type": "long",
      "logicalType": "timestamp-millis"
    },
    {
      "name": "approvedBy",
      "type": "string",
      "doc": "User ID or agent ID that approved"
    },
    {
      "name": "approverRole",
      "type": "string",
      "doc": "Role of approver"
    },
    {
      "name": "approvedAmount",
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
      "name": "deductible",
      "type": "double",
      "default": 0.0
    },
    {
      "name": "payableAmount",
      "type": "double",
      "doc": "Amount to be paid (approved - deductible)"
    },
    {
      "name": "approvalNotes",
      "type": ["null", "string"],
      "default": null
    },
    {
      "name": "paymentMethod",
      "type": {
        "type": "enum",
        "name": "PaymentMethod",
        "symbols": ["DIRECT_DEPOSIT", "CHECK", "WIRE_TRANSFER"]
      },
      "default": "DIRECT_DEPOSIT"
    }
  ]
}
```

---

### 4. ClaimEscalated Event

**Topic**: `claims.escalated`  
**Format**: Avro  
**Version**: 1.0

```json
{
  "type": "record",
  "name": "ClaimEscalated",
  "namespace": "com.insurance.claims.events.v1",
  "doc": "Event published when a claim is escalated for human review",
  "fields": [
    {
      "name": "claimId",
      "type": "string"
    },
    {
      "name": "eventId",
      "type": "string"
    },
    {
      "name": "eventTimestamp",
      "type": "long",
      "logicalType": "timestamp-millis"
    },
    {
      "name": "escalationId",
      "type": "string",
      "doc": "Unique escalation identifier"
    },
    {
      "name": "escalatedFrom",
      "type": "string",
      "doc": "Agent or user who escalated"
    },
    {
      "name": "escalatedTo",
      "type": "string",
      "doc": "Role or user to handle escalation"
    },
    {
      "name": "reason",
      "type": "string",
      "doc": "Reason for escalation"
    },
    {
      "name": "priority",
      "type": {
        "type": "enum",
        "name": "Priority",
        "symbols": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
      }
    },
    {
      "name": "slaDeadline",
      "type": "long",
      "logicalType": "timestamp-millis",
      "doc": "SLA deadline for resolution"
    },
    {
      "name": "context",
      "type": {
        "type": "record",
        "name": "EscalationContext",
        "fields": [
          {
            "name": "fraudScore",
            "type": "double"
          },
          {
            "name": "riskScore",
            "type": "int"
          },
          {
            "name": "claimAmount",
            "type": "double"
          },
          {
            "name": "riskFactors",
            "type": {
              "type": "array",
              "items": "string"
            }
          }
        ]
      }
    }
  ]
}
```

---

## Message Keys

### Partitioning Strategy

All topics use the `claimId` as the message key to ensure:
- All events for a claim go to the same partition
- Ordered processing of events per claim
- Efficient consumer group coordination

```javascript
// Producer key configuration
const messageKey = claim.claimId;

await producer.send({
  topic: 'claims.submitted',
  messages: [{
    key: messageKey,
    value: JSON.stringify(claimEvent)
  }]
});
```

---

## Schema Evolution

### Compatibility Rules

- **Forward Compatibility**: New consumers can read old data
- **Backward Compatibility**: Old consumers can read new data
- **Full Compatibility**: Both forward and backward compatible

### Version Management

```yaml
schema_registry:
  url: https://schema-registry.insurance.com
  compatibility: FULL
  
schemas:
  - subject: claims.submitted-value
    version: 1
    compatibility: FULL
    
  - subject: claims.processed-value
    version: 1
    compatibility: FULL
```

### Evolution Guidelines

1. **Adding Fields**: Always provide default values
2. **Removing Fields**: Deprecate first, remove after 6 months
3. **Changing Types**: Create new field, deprecate old
4. **Renaming Fields**: Create new field with alias

---

## Producer Configuration

### Best Practices

```properties
# Reliability
acks=all
retries=2147483647
max.in.flight.requests.per.connection=5
enable.idempotence=true

# Performance
compression.type=snappy
batch.size=16384
linger.ms=10
buffer.memory=33554432

# Timeouts
request.timeout.ms=30000
delivery.timeout.ms=120000
```

### Example Producer

```javascript
const { Kafka } = require('kafkajs');

const kafka = new Kafka({
  clientId: 'claims-producer',
  brokers: ['kafka-1:9092', 'kafka-2:9092', 'kafka-3:9092'],
  ssl: true,
  sasl: {
    mechanism: 'scram-sha-512',
    username: process.env.KAFKA_USERNAME,
    password: process.env.KAFKA_PASSWORD
  }
});

const producer = kafka.producer({
  idempotent: true,
  maxInFlightRequests: 5,
  transactionalId: 'claims-producer-1'
});

await producer.connect();

// Send with transaction
const transaction = await producer.transaction();
try {
  await transaction.send({
    topic: 'claims.submitted',
    messages: [{
      key: claim.claimId,
      value: avroSerializer.serialize(claim),
      headers: {
        'correlation-id': correlationId,
        'trace-id': traceId
      }
    }]
  });
  
  await transaction.commit();
} catch (error) {
  await transaction.abort();
  throw error;
}
```

---

## Consumer Configuration

### Best Practices

```properties
# Consumer group
group.id=claims-adjuster-group
enable.auto.commit=false
auto.offset.reset=earliest

# Performance
fetch.min.bytes=1
fetch.max.wait.ms=500
max.poll.records=100
max.poll.interval.ms=300000

# Reliability
session.timeout.ms=30000
heartbeat.interval.ms=3000
isolation.level=read_committed
```

### Example Consumer

```javascript
const consumer = kafka.consumer({
  groupId: 'claims-adjuster-group',
  sessionTimeout: 30000,
  heartbeatInterval: 3000
});

await consumer.connect();
await consumer.subscribe({ 
  topics: ['claims.high-value', 'claims.standard'],
  fromBeginning: false
});

await consumer.run({
  autoCommit: false,
  eachMessage: async ({ topic, partition, message }) => {
    const claim = avroDeserializer.deserialize(message.value);
    
    try {
      await processClaim(claim);
      
      // Manual commit after successful processing
      await consumer.commitOffsets([{
        topic,
        partition,
        offset: (parseInt(message.offset) + 1).toString()
      }]);
      
    } catch (error) {
      // Handle error, potentially send to DLQ
      await handleError(claim, error);
    }
  }
});
```

---

## Monitoring & Metrics

### Key Metrics to Track

```yaml
producer_metrics:
  - record-send-rate
  - record-error-rate
  - request-latency-avg
  - request-latency-max
  - buffer-available-bytes
  
consumer_metrics:
  - records-consumed-rate
  - records-lag-max
  - fetch-latency-avg
  - commit-latency-avg
  - assigned-partitions
  
broker_metrics:
  - messages-in-per-sec
  - bytes-in-per-sec
  - bytes-out-per-sec
  - under-replicated-partitions
  - offline-partitions
```

### Alerting Thresholds

```yaml
alerts:
  - name: High Consumer Lag
    condition: records-lag-max > 10000
    severity: HIGH
    
  - name: Producer Error Rate
    condition: record-error-rate > 0.01
    severity: CRITICAL
    
  - name: Under Replicated Partitions
    condition: under-replicated-partitions > 0
    severity: CRITICAL
```

---

## Testing

### Schema Validation Tests

```javascript
describe('ClaimSubmitted Schema', () => {
  it('should validate valid claim', () => {
    const claim = {
      claimId: 'CLM-2026050114352201',
      eventId: uuidv4(),
      eventTimestamp: Date.now(),
      policyNumber: 'POL-2026-123456',
      claimType: 'AUTO_ACCIDENT',
      // ... rest of fields
    };
    
    const result = avroSchema.isValid(claim);
    expect(result).toBe(true);
  });
  
  it('should reject invalid claim type', () => {
    const claim = {
      claimId: 'CLM-2026050114352201',
      claimType: 'INVALID_TYPE',
      // ... rest of fields
    };
    
    expect(() => avroSchema.validate(claim)).toThrow();
  });
});
```

### Integration Tests

```javascript
describe('Kafka Integration', () => {
  it('should produce and consume message', async () => {
    const claim = createTestClaim();
    
    // Produce
    await producer.send({
      topic: 'claims.submitted',
      messages: [{ key: claim.claimId, value: serialize(claim) }]
    });
    
    // Consume
    const consumed = await consumeMessage('claims.submitted');
    expect(consumed.claimId).toBe(claim.claimId);
  });
});
```

---

## Disaster Recovery

### Backup Strategy

- **Topic Replication**: 3x replication across availability zones
- **Mirror Maker**: Cross-region replication for DR
- **Snapshot Backups**: Daily snapshots of topic data

### Recovery Procedures

1. **Partition Loss**: Automatic leader election
2. **Broker Failure**: Automatic failover to replica
3. **Complete Cluster Loss**: Restore from mirror cluster
4. **Data Corruption**: Replay from backup snapshots
