# Confluent Cloud Setup Guide

Complete guide to setting up Kafka topics, API keys, and clients in Confluent Cloud for the Claims Processor service.

## Prerequisites

- Confluent Cloud account (sign up at https://confluent.cloud)
- Active Kafka cluster in Confluent Cloud
- Billing enabled (or free trial credits)

## Step 1: Create Kafka Cluster (If Not Already Created)

1. **Log in to Confluent Cloud**: https://confluent.cloud
2. **Create Environment** (if needed):
   - Click "Environments" → "Add cloud environment"
   - Name: `insurance-claims-demo`
   - Click "Create"

3. **Create Cluster**:
   - Click "Add cluster"
   - Select cluster type:
     - **Basic** (recommended for demo): $0.50/hour
     - **Standard**: For production
     - **Dedicated**: For enterprise
   - Choose cloud provider: **Azure** (Canada Central)
   - Cluster name: `claims-processor-cluster`
   - Click "Launch cluster"

## Step 2: Create API Keys

API keys are required for your service to authenticate with Confluent Cloud.

### Create Cluster API Key

1. Navigate to your cluster
2. Click **"API keys"** in left menu
3. Click **"Add key"**
4. Select scope: **"Global access"** (for demo) or **"Granular access"** (for production)
5. Description: `claims-processor-service`
6. Click **"Download and continue"**

**⚠️ IMPORTANT**: Save these credentials immediately - you won't see them again!

```
API Key: XXXXXXXXXXXXXXXX
API Secret: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

Add these to your `.env` file:
```bash
KAFKA_SASL_USERNAME=your_api_key_here
KAFKA_SASL_PASSWORD=your_api_secret_here
```

## Step 3: Get Bootstrap Server URL

1. In your cluster, click **"Cluster settings"**
2. Find **"Bootstrap server"** under "Endpoints"
3. Copy the URL (format: `pkc-xxxxx.region.provider.confluent.cloud:9092`)

Add to your `.env` file:
```bash
KAFKA_BOOTSTRAP_SERVERS=pkc-4rn2p.canadacentral.azure.confluent.cloud:9092
```

## Step 4: Create Topics

You have **two options** to create topics:

### Option A: Automated (Recommended) - Using Python Script

```bash
# Ensure .env is configured with API credentials
python setup_topics.py
```

This creates all 5 required topics:
- `claims.ingest` (3 partitions, 30-day retention)
- `claims.processed` (3 partitions, 90-day retention)
- `claims.approved` (3 partitions, 365-day retention)
- `claims.escalated` (2 partitions, 365-day retention)
- `claims.dlq` (2 partitions, 90-day retention)

### Option B: Manual - Using Confluent Cloud Console

1. Navigate to your cluster
2. Click **"Topics"** in left menu
3. Click **"Add topic"**

**For each topic, create with these settings:**

#### Topic 1: claims.ingest
```
Name: claims.ingest
Partitions: 3
Retention time: 30 days (2592000000 ms)
Cleanup policy: delete
Compression: snappy
Min in-sync replicas: 2
```

#### Topic 2: claims.processed
```
Name: claims.processed
Partitions: 3
Retention time: 90 days (7776000000 ms)
Cleanup policy: delete
Compression: lz4
Min in-sync replicas: 2
```

#### Topic 3: claims.approved
```
Name: claims.approved
Partitions: 3
Retention time: 365 days (31536000000 ms)
Cleanup policy: delete
Compression: lz4
Min in-sync replicas: 2
```

#### Topic 4: claims.escalated
```
Name: claims.escalated
Partitions: 2
Retention time: 365 days (31536000000 ms)
Cleanup policy: delete
Compression: lz4
Min in-sync replicas: 2
```

#### Topic 5: claims.dlq
```
Name: claims.dlq
Partitions: 2
Retention time: 90 days (7776000000 ms)
Cleanup policy: delete
Compression: snappy
Min in-sync replicas: 2
```

## Step 5: Create Consumer Group (Automatic)

Consumer groups are created automatically when your service starts. No manual setup needed!

The service uses consumer group: `claims-processor-group`

You can monitor it in Confluent Cloud:
1. Go to **"Consumers"** in left menu
2. You'll see `claims-processor-group` appear when service starts

## Step 6: Configure Network Access (If Required)

For production environments:

1. Go to **"Cluster settings"** → **"Networking"**
2. Add your IP address or CIDR range to allowlist
3. For demo/development, you can use **"Public internet"** access

## Step 7: Verify Setup

### Check Topics
```bash
# List all topics
confluent kafka topic list --cluster <cluster-id>

# Or use the Python script
python -c "
from confluent_kafka.admin import AdminClient
from config import settings

admin = AdminClient(settings.kafka_config)
topics = admin.list_topics(timeout=10)
print('Topics:', list(topics.topics.keys()))
"
```

### Test Connection
```bash
# Send a test message
python test_producer.py
```

You should see:
```
✓ Message delivered to claims.ingest [partition 0] at offset 0
```

## Step 8: Monitor in Confluent Cloud

### View Messages
1. Go to **"Topics"** → Select a topic
2. Click **"Messages"** tab
3. You can view messages in real-time

### Monitor Metrics
1. Go to **"Cluster overview"**
2. View:
   - Throughput (MB/s)
   - Request rate
   - Consumer lag
   - Partition distribution

### Check Consumer Groups
1. Go to **"Consumers"**
2. Select `claims-processor-group`
3. View:
   - Lag per partition
   - Current offset
   - Committed offset

## Complete .env Configuration

After completing all steps, your `.env` should look like:

```bash
# Confluent Cloud Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=pkc-4rn2p.canadacentral.azure.confluent.cloud:9092
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_MECHANISM=PLAIN
KAFKA_SASL_USERNAME=YOUR_API_KEY_HERE
KAFKA_SASL_PASSWORD=YOUR_API_SECRET_HERE
KAFKA_GROUP_ID=claims-processor-group
KAFKA_AUTO_OFFSET_RESET=earliest

# Kafka Topics
KAFKA_TOPIC_INGEST=claims.ingest
KAFKA_TOPIC_PROCESSED=claims.processed
KAFKA_TOPIC_APPROVED=claims.approved
KAFKA_TOPIC_ESCALATED=claims.escalated
KAFKA_TOPIC_DLQ=claims.dlq

# CockroachDB Configuration
DB_HOST=your-cockroachdb-host
DB_PORT=26257
DB_NAME=insurance_claims
DB_USER=your_username
DB_PASSWORD=your_password
DB_SSLMODE=require

# Service Configuration
LOG_LEVEL=INFO
SERVICE_NAME=claims-processor
METRICS_PORT=9090

# AI Logic Gate Thresholds
AUTO_APPROVE_AMOUNT_THRESHOLD=2000
AUTO_APPROVE_RISK_THRESHOLD=20
ESCALATION_RISK_THRESHOLD=80
```

## Troubleshooting

### "Authentication failed"
- Verify API key and secret are correct
- Check key has proper permissions
- Ensure key is for the correct cluster

### "Topic not found"
- Run `python setup_topics.py` to create topics
- Or create manually in Confluent Cloud console
- Verify topic names match exactly in `.env`

### "Connection timeout"
- Check bootstrap server URL is correct
- Verify network access (firewall/allowlist)
- Ensure cluster is running

### "Insufficient permissions"
- API key needs read/write permissions
- Create new key with "Global access" for demo

## Cost Optimization Tips

For demo/development:
- Use **Basic cluster** ($0.50/hour)
- Set shorter retention periods (7-30 days)
- Use fewer partitions (1-3 per topic)
- Delete cluster when not in use

For production:
- Use **Standard** or **Dedicated** cluster
- Enable auto-scaling
- Set appropriate retention based on compliance
- Monitor usage in billing dashboard

## Next Steps

Once setup is complete:

1. ✅ Verify `.env` has all credentials
2. ✅ Run `python setup_topics.py` (if using automated setup)
3. ✅ Run `python test_producer.py` to send test messages
4. ✅ Run `python main.py` to start the processor
5. ✅ Monitor in Confluent Cloud console

## Additional Resources

- **Confluent Cloud Docs**: https://docs.confluent.io/cloud/current/
- **Kafka Python Client**: https://docs.confluent.io/kafka-clients/python/current/
- **API Keys Guide**: https://docs.confluent.io/cloud/current/access-management/authenticate/api-keys/
- **Topic Configuration**: https://docs.confluent.io/cloud/current/clusters/broker-config.html

## Support

If you encounter issues:
1. Check Confluent Cloud status page
2. Review service logs for detailed errors
3. Contact Confluent support (if on paid plan)
4. Check community forums: https://forum.confluent.io/