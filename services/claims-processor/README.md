# Claims Processor Service

A Python service that processes insurance claims using Confluent Kafka and CockroachDB with AI-powered logic gates for automated decision-making.

## Features

- **Kafka Integration**: Consumes from `claims.ingest` topic on Confluent Cloud
- **Policy Verification**: Validates policies against CockroachDB
- **AI Logic Gate**:
  - Auto-approves claims < $2,000 with Risk < 20
  - Escalates claims with Risk > 80
  - Routes other claims for manual review
- **Event Publishing**: Publishes decisions to appropriate topics (approved, escalated, processed)
- **Dead Letter Queue**: Handles failed messages gracefully

## Architecture

```
┌─────────────────┐
│ Confluent Cloud │
│  claims.ingest  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Claims Processor       │
│  ┌──────────────────┐   │
│  │ 1. Verify Policy │   │
│  │    (CockroachDB) │   │
│  └────────┬─────────┘   │
│           │             │
│  ┌────────▼─────────┐   │
│  │ 2. AI Logic Gate │   │
│  │  • Auto-approve  │   │
│  │  • Escalate      │   │
│  │  • Review        │   │
│  └────────┬─────────┘   │
│           │             │
│  ┌────────▼─────────┐   │
│  │ 3. Save to DB    │   │
│  └────────┬─────────┘   │
│           │             │
│  ┌────────▼─────────┐   │
│  │ 4. Publish Event │   │
│  └──────────────────┘   │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│   Output Topics         │
│  • claims.approved      │
│  • claims.escalated     │
│  • claims.processed     │
│  • claims.dlq           │
└─────────────────────────┘
```

## Prerequisites

- Python 3.9+
- Confluent Cloud account with Kafka cluster
- CockroachDB instance
- API credentials for Confluent Cloud

## Installation

1. **Clone the repository**:
   ```bash
   cd insurance-claims-platform/services/claims-processor
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   ```

5. **Edit `.env` file** with your credentials:
   ```bash
   # Confluent Cloud Kafka
   KAFKA_BOOTSTRAP_SERVERS=pkc-4rn2p.canadacentral.azure.confluent.cloud:9092
   KAFKA_SASL_USERNAME=your_api_key
   KAFKA_SASL_PASSWORD=your_api_secret
   
   # CockroachDB
   DB_HOST=your_cockroachdb_host
   DB_PORT=26257
   DB_NAME=insurance_claims
   DB_USER=your_db_user
   DB_PASSWORD=your_db_password
   ```

## Setup

### 1. Create Kafka Topics

Run the setup script to create all required topics in Confluent Cloud:

```bash
python setup_topics.py
```

This creates:
- `claims.ingest` - Input topic for new claims
- `claims.processed` - Claims requiring manual review
- `claims.approved` - Auto-approved claims
- `claims.escalated` - High-risk escalated claims
- `claims.dlq` - Dead letter queue for failed messages

### 2. Initialize Database

Ensure your CockroachDB has the schema loaded:

```bash
cockroach sql --url "postgresql://user:password@host:26257/insurance_claims?sslmode=require" \
  < ../../database/schema.sql
```

## Usage

### Start the Service

```bash
python main.py
```

The service will:
1. Connect to CockroachDB
2. Subscribe to `claims.ingest` topic
3. Start processing claims in real-time

### Test with Sample Data

Produce test claims to verify the service:

```bash
python test_producer.py
```

This produces 5 test claims covering different scenarios:
1. **Auto-Approve**: $1,500, Risk 15 → `AUTO_APPROVED`
2. **Under Review**: $5,000, Risk 45 → `UNDER_REVIEW`
3. **Escalate**: $3,000, Risk 85 → `ESCALATED`
4. **Edge Case**: $1,999.99, Risk 19 → `AUTO_APPROVED`
5. **High Risk + Amount**: $15,000, Risk 90 → `ESCALATED`

## AI Logic Gate Rules

The service applies the following decision logic:

```python
if claim_amount < $2,000 AND risk_score < 20:
    status = "AUTO_APPROVED"
    topic = "claims.approved"

elif risk_score > 80:
    status = "ESCALATED"
    topic = "claims.escalated"

else:
    status = "UNDER_REVIEW"
    topic = "claims.processed"
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `KAFKA_BOOTSTRAP_SERVERS` | Confluent Cloud bootstrap server | Required |
| `KAFKA_SASL_USERNAME` | Confluent Cloud API key | Required |
| `KAFKA_SASL_PASSWORD` | Confluent Cloud API secret | Required |
| `DB_HOST` | CockroachDB host | `localhost` |
| `DB_PORT` | CockroachDB port | `26257` |
| `DB_NAME` | Database name | `insurance_claims` |
| `AUTO_APPROVE_AMOUNT_THRESHOLD` | Max amount for auto-approval | `2000` |
| `AUTO_APPROVE_RISK_THRESHOLD` | Max risk for auto-approval | `20` |
| `ESCALATION_RISK_THRESHOLD` | Min risk for escalation | `80` |

### Adjusting Thresholds

Modify thresholds in `.env`:

```bash
# More conservative (fewer auto-approvals)
AUTO_APPROVE_AMOUNT_THRESHOLD=1000
AUTO_APPROVE_RISK_THRESHOLD=10

# More aggressive escalation
ESCALATION_RISK_THRESHOLD=70
```

## Monitoring

The service uses structured logging (JSON format) for easy monitoring:

```json
{
  "event": "claim_processed",
  "claim_id": "abc-123",
  "claim_number": "CLM-2026-000001",
  "decision": "AUTO_APPROVED",
  "next_topic": "claims.approved",
  "timestamp": "2026-05-03T01:00:00Z"
}
```

### Key Log Events

- `service_started` - Service initialization
- `message_received` - New claim received
- `policy_verified` - Policy validation complete
- `ai_decision_*` - AI logic gate decision
- `claim_processed` - Claim processing complete
- `message_delivered` - Event published to Kafka

## Error Handling

### Dead Letter Queue

Failed messages are sent to `claims.dlq` with error details:

```json
{
  "original_topic": "claims.ingest",
  "original_offset": 12345,
  "error_reason": "Policy verification failed",
  "failed_at": "2026-05-03T01:00:00Z"
}
```

### Retry Logic

- Kafka consumer uses manual commit for at-least-once delivery
- Database operations use transactions with rollback
- Producer delivery callbacks track message delivery status

## Development

### Project Structure

```
claims-processor/
├── main.py              # Service entry point
├── config.py            # Configuration management
├── database.py          # CockroachDB operations
├── claims_processor.py  # Core processing logic
├── setup_topics.py      # Kafka topic creation
├── test_producer.py     # Test data generator
├── requirements.txt     # Python dependencies
├── .env.example         # Environment template
└── README.md           # This file
```

### Running Tests

```bash
# Install dev dependencies
pip install pytest pytest-cov

# Run tests (when available)
pytest tests/
```

## Troubleshooting

### Connection Issues

**Kafka Connection Failed**:
```bash
# Verify credentials
echo $KAFKA_SASL_USERNAME
echo $KAFKA_SASL_PASSWORD

# Test connectivity
telnet pkc-4rn2p.canadacentral.azure.confluent.cloud 9092
```

**Database Connection Failed**:
```bash
# Test CockroachDB connection
cockroach sql --url "postgresql://user:password@host:26257/insurance_claims?sslmode=require"
```

### Message Processing Issues

**Messages not being consumed**:
- Check consumer group ID is unique
- Verify topic exists: `python setup_topics.py`
- Check offset reset policy in `.env`

**Claims not being saved**:
- Verify database schema is loaded
- Check database connection string
- Review logs for SQL errors

## Production Considerations

1. **Scaling**: Run multiple instances with same `KAFKA_GROUP_ID`
2. **Monitoring**: Integrate with Prometheus/Grafana
3. **Alerting**: Set up alerts for DLQ messages
4. **Security**: Use secrets management (AWS Secrets Manager, HashiCorp Vault)
5. **High Availability**: Deploy across multiple availability zones

## License

Copyright © 2026 Insurance Claims Platform

## Support

For issues or questions, contact: claims-platform@insurance.com