# Troubleshooting Guide - Adjuster Agent

## Common Issues and Solutions

### 1. Protobuf Compatibility Error

**Error Message**:
```
AttributeError: 'MessageFactory' object has no attribute 'GetPrototype'
AttributeError: 'google.protobuf.pyext._message.FieldDescriptor' object has no attribute 'is_repeated'
```

**Cause**: Incompatible protobuf version with TensorFlow/Transformers on Python 3.12+

**Solution**:
```bash
cd insurance-claims-platform/services/adjuster-agent
./fix_dependencies.sh
```

This script will:
1. Uninstall conflicting packages
2. Install compatible protobuf version (3.20.x)
3. Install PyTorch CPU version
4. Install compatible transformers and sentence-transformers
5. Verify all imports work correctly

**Manual Fix** (if script fails):
```bash
# Uninstall conflicting packages
pip uninstall -y protobuf tensorflow transformers sentence-transformers torch

# Install in correct order
pip install "protobuf>=3.20.0,<4.0.0"
pip install "torch>=2.0.0,<2.3.0" --index-url https://download.pytorch.org/whl/cpu
pip install "transformers>=4.30.0,<4.40.0"
pip install "sentence-transformers>=2.2.0,<3.0.0"
pip install -r requirements.txt
```

### 2. Kafka Connection Failed

**Error Message**:
```
KafkaError: Failed to connect to broker
```

**Possible Causes**:
- Incorrect bootstrap servers
- Invalid SASL credentials
- Network connectivity issues

**Solution**:
1. Verify `.env` configuration:
```bash
cat .env | grep KAFKA
```

2. Check credentials match Confluent Cloud:
   - `KAFKA_BOOTSTRAP_SERVERS` should be your Confluent Cloud endpoint
   - `KAFKA_SASL_USERNAME` is your API Key
   - `KAFKA_SASL_PASSWORD` is your API Secret

3. Test connectivity:
```bash
python3 -c "
from confluent_kafka import Consumer
from config import Config
config = Config()
consumer_config = {
    'bootstrap.servers': config.KAFKA_BOOTSTRAP_SERVERS,
    'security.protocol': config.KAFKA_SECURITY_PROTOCOL,
    'sasl.mechanism': config.KAFKA_SASL_MECHANISM,
    'sasl.username': config.KAFKA_SASL_USERNAME,
    'sasl.password': config.KAFKA_SASL_PASSWORD,
    'group.id': 'test-consumer'
}
consumer = Consumer(consumer_config)
print('✅ Kafka connection successful!')
consumer.close()
"
```

### 3. Database Connection Failed

**Error Message**:
```
psycopg2.OperationalError: could not connect to server
```

**Possible Causes**:
- Incorrect database credentials
- SSL/TLS configuration issues
- Network connectivity problems

**Solution**:
1. Verify `.env` configuration:
```bash
cat .env | grep DB_
```

2. Test database connection:
```bash
python3 -c "
import psycopg2
from config import Config
config = Config()
conn = psycopg2.connect(
    host=config.DB_HOST,
    port=config.DB_PORT,
    database=config.DB_NAME,
    user=config.DB_USER,
    password=config.DB_PASSWORD,
    sslmode=config.DB_SSLMODE
)
print('✅ Database connection successful!')
conn.close()
"
```

3. For CockroachDB Cloud, ensure:
   - `DB_SSLMODE=verify-full`
   - Correct host format: `cluster-name.region.cockroachlabs.cloud`
   - Port is typically `26257`

### 4. Vector Search Not Working

**Error Message**:
```
psycopg2.errors.UndefinedFunction: operator does not exist: vector <=>
```

**Cause**: pgvector extension not installed or enabled

**Solution**:
1. Check if pgvector is installed:
```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

2. If not installed, run migration:
```bash
cd insurance-claims-platform/services/claims-processor
python3 run_migration.py
```

3. Verify embeddings exist:
```sql
SELECT COUNT(*) FROM claims WHERE description_embedding IS NOT NULL;
```

### 5. Chainlit Won't Start

**Error Message**:
```
Error: Port 8000 is already in use
```

**Solution**:
1. Kill existing process:
```bash
lsof -ti:8000 | xargs kill -9
```

2. Or use different port:
```bash
chainlit run app.py -w --port 8001
```

**Error Message**:
```
FileNotFoundError: .chainlit/config.toml not found
```

**Solution**:
```bash
mkdir -p .chainlit
cat > .chainlit/config.toml << 'EOF'
[project]
enable_telemetry = false

[UI]
name = "Insurance Claims Adjuster Agent"
default_collapse_content = true
default_expand_messages = false
hide_cot = false
EOF
```

### 6. Model Download Issues

**Error Message**:
```
OSError: Can't load tokenizer for 'all-MiniLM-L6-v2'
```

**Cause**: Network issues or HuggingFace Hub connectivity

**Solution**:
1. Pre-download model:
```bash
python3 -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
print('✅ Model downloaded successfully!')
"
```

2. If behind proxy, set environment variables:
```bash
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
```

### 7. Memory Issues

**Error Message**:
```
RuntimeError: [enforce fail at alloc_cpu.cpp:114] . DefaultCPUAllocator: not enough memory
```

**Cause**: Insufficient RAM for model loading

**Solution**:
1. Use smaller model:
```bash
# In .env
EMBEDDING_MODEL=all-MiniLM-L6-v2  # 80MB
# Instead of
EMBEDDING_MODEL=all-mpnet-base-v2  # 420MB
```

2. Increase swap space (Linux):
```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 8. Import Errors

**Error Message**:
```
ModuleNotFoundError: No module named 'chainlit'
```

**Solution**:
```bash
pip install -r requirements.txt
```

**Error Message**:
```
ImportError: cannot import name 'Config' from 'config'
```

**Cause**: Running from wrong directory

**Solution**:
```bash
cd insurance-claims-platform/services/adjuster-agent
python3 app.py
```

## Verification Steps

After fixing issues, verify setup:

```bash
# 1. Test imports
python3 test_setup.py

# 2. Check configuration
python3 -c "from config import Config; c = Config(); print(f'DB: {c.DB_HOST}'); print(f'Kafka: {c.KAFKA_BOOTSTRAP_SERVERS}')"

# 3. Start application
./start.sh
```

## Getting Help

If issues persist:

1. **Check logs**:
```bash
tail -f logs/adjuster-agent.log
```

2. **Enable debug logging**:
```bash
# In .env
LOG_LEVEL=DEBUG
```

3. **Collect diagnostic info**:
```bash
python3 -c "
import sys
import platform
print(f'Python: {sys.version}')
print(f'Platform: {platform.platform()}')
import pkg_resources
for pkg in ['chainlit', 'psycopg2-binary', 'confluent-kafka', 'sentence-transformers', 'torch']:
    try:
        version = pkg_resources.get_distribution(pkg).version
        print(f'{pkg}: {version}')
    except:
        print(f'{pkg}: NOT INSTALLED')
"
```

4. **Create GitHub issue** with:
   - Error message
   - Python version
   - Operating system
   - Diagnostic info from above

## Performance Optimization

### Slow Query Response

**Solution**:
1. Add database indexes:
```sql
CREATE INDEX IF NOT EXISTS idx_claims_claim_number ON claims(claim_number);
CREATE INDEX IF NOT EXISTS idx_claims_risk_score ON claims(risk_score);
CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status);
```

2. Enable query caching (future enhancement)

### Slow Vector Search

**Solution**:
1. Verify HNSW index exists:
```sql
SELECT indexname FROM pg_indexes WHERE tablename = 'claims' AND indexname LIKE '%embedding%';
```

2. Rebuild index if needed:
```sql
DROP INDEX IF EXISTS idx_claims_description_embedding;
CREATE INDEX idx_claims_description_embedding ON claims 
USING hnsw (description_embedding vector_cosine_ops);
```

### High Memory Usage

**Solution**:
1. Reduce batch size in embeddings_client.py
2. Use model quantization (future enhancement)
3. Implement connection pooling

## Environment-Specific Issues

### macOS

**Issue**: SSL certificate verification fails

**Solution**:
```bash
/Applications/Python\ 3.12/Install\ Certificates.command
```

### Linux

**Issue**: Permission denied on scripts

**Solution**:
```bash
chmod +x *.sh
```

### Windows

**Issue**: Scripts won't run

**Solution**: Use Git Bash or WSL, or run Python directly:
```bash
python app.py
```

## Contact Support

- GitHub Issues: [Create an issue]
- Email: support@example.com
- Slack: #adjuster-agent