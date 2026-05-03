# Quick Start Guide - Claims Processor Service

Get the claims processor running in 5 minutes!

## Prerequisites Checklist

- [ ] Python 3.9+ installed
- [ ] Confluent Cloud account with Kafka cluster
- [ ] Confluent Cloud API Key & Secret
- [ ] CockroachDB instance (or local setup)
- [ ] Database schema loaded

## Step-by-Step Setup

### 1. Navigate to Service Directory

```bash
cd insurance-claims-platform/services/claims-processor
```

### 2. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your credentials
nano .env  # or use your preferred editor
```

**Required Configuration:**

```bash
# Confluent Cloud Kafka
KAFKA_BOOTSTRAP_SERVERS=pkc-4rn2p.canadacentral.azure.confluent.cloud:9092
KAFKA_SASL_USERNAME=YOUR_API_KEY_HERE
KAFKA_SASL_PASSWORD=YOUR_API_SECRET_HERE

# CockroachDB
DB_HOST=your-cockroachdb-host
DB_PORT=26257
DB_NAME=insurance_claims
DB_USER=your_username
DB_PASSWORD=your_password
```

### 3. Run the Service

**Option A: Using the Quick Start Script (Recommended)**

```bash
./run.sh
```

Then select option 4 to:
1. Create Kafka topics
2. Send test claims
3. Start the processor

**Option B: Manual Setup**

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create Kafka topics
python setup_topics.py

# Send test claims
python test_producer.py

# Start the service
python main.py
```

## Verify It's Working

You should see logs like:

```json
{"event": "service_started", "service": "claims-processor", "timestamp": "2026-05-03T01:00:00Z"}
{"event": "database_connected", "host": "localhost", "database": "insurance_claims"}
{"event": "kafka_consumer_initialized", "topic": "claims.ingest"}
{"event": "message_received", "claim_number": "CLM-2026-000001"}
{"event": "policy_verified", "policy_number": "POL-2026-00001"}
{"event": "ai_decision_auto_approved", "amount": 1500.0, "risk": 15}
{"event": "claim_processed", "decision": "AUTO_APPROVED", "next_topic": "claims.approved"}
```

## Test Scenarios

The test producer creates 5 claims:

| Claim | Amount | Risk | Expected Decision |
|-------|--------|------|-------------------|
| CLM-2026-000001 | $1,500 | 15 | AUTO_APPROVED |
| CLM-2026-000002 | $5,000 | 45 | UNDER_REVIEW |
| CLM-2026-000003 | $3,000 | 85 | ESCALATED |
| CLM-2026-000004 | $1,999.99 | 19 | AUTO_APPROVED |
| CLM-2026-000005 | $15,000 | 90 | ESCALATED |

## AI Logic Gate Rules

```
IF claim_amount < $2,000 AND risk_score < 20:
    → AUTO_APPROVED (published to claims.approved)

ELSE IF risk_score > 80:
    → ESCALATED (published to claims.escalated)

ELSE:
    → UNDER_REVIEW (published to claims.processed)
```

## Monitoring

### Check Kafka Topics in Confluent Cloud

1. Go to Confluent Cloud Console
2. Navigate to your cluster
3. Click "Topics"
4. You should see:
   - `claims.ingest` (input)
   - `claims.approved` (auto-approved claims)
   - `claims.escalated` (high-risk claims)
   - `claims.processed` (manual review needed)
   - `claims.dlq` (failed messages)

### Check Database

```sql
-- Connect to CockroachDB
cockroach sql --url "postgresql://user:password@host:26257/insurance_claims?sslmode=require"

-- View processed claims
SELECT 
    claim_number,
    policy_number,
    claim_amount,
    risk_score,
    status,
    created_at
FROM claims
ORDER BY created_at DESC
LIMIT 10;

-- Count by status
SELECT status, COUNT(*) 
FROM claims 
GROUP BY status;
```

## Troubleshooting

### "Connection refused" Error

**Problem**: Can't connect to Kafka
**Solution**: 
- Verify `KAFKA_BOOTSTRAP_SERVERS` in `.env`
- Check API credentials are correct
- Ensure your IP is whitelisted in Confluent Cloud

### "Database connection failed"

**Problem**: Can't connect to CockroachDB
**Solution**:
- Verify database credentials in `.env`
- Check database is running
- Ensure schema is loaded: `cockroach sql < ../../database/schema.sql`

### "No messages received"

**Problem**: Service starts but no messages processed
**Solution**:
- Run `python test_producer.py` to send test messages
- Check topic name matches in `.env`
- Verify consumer group ID is unique

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'confluent_kafka'`
**Solution**:
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

## Next Steps

1. **Customize Thresholds**: Edit `.env` to adjust auto-approval and escalation thresholds
2. **Add Monitoring**: Integrate with Prometheus/Grafana
3. **Scale Up**: Run multiple instances with same consumer group
4. **Production Deploy**: Use Docker/Kubernetes for deployment

## Support

- **Documentation**: See [README.md](README.md) for detailed information
- **Issues**: Contact claims-platform@insurance.com
- **Logs**: Check service logs for detailed error messages

## Architecture Diagram

```
┌──────────────────┐
│ Confluent Cloud  │
│  claims.ingest   │
└────────┬─────────┘
         │
         ▼
┌─────────────────────────────┐
│   Claims Processor Service  │
│                             │
│  1. Listen to Kafka         │
│  2. Verify Policy (DB)      │
│  3. Apply AI Logic:         │
│     • < $2K & Risk < 20     │
│       → AUTO_APPROVED       │
│     • Risk > 80             │
│       → ESCALATED           │
│     • Otherwise             │
│       → UNDER_REVIEW        │
│  4. Save to CockroachDB     │
│  5. Publish to next topic   │
└─────────────────────────────┘
         │
         ▼
┌──────────────────┐
│  Output Topics   │
│  • approved      │
│  • escalated     │
│  • processed     │
└──────────────────┘
```

---

**Ready to go?** Run `./run.sh` and select option 4! 🚀