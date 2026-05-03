# Adjuster Agent - Deployment Guide

Complete deployment guide for the Chainlit Adjuster Agent interface.

## Prerequisites

### System Requirements

- **OS**: macOS, Linux, or Windows with WSL
- **Python**: 3.8 or higher
- **Memory**: Minimum 2GB RAM (4GB recommended)
- **Storage**: 500MB for dependencies and models
- **Network**: Access to CockroachDB instance

### Required Services

- ✅ **CockroachDB**: Running and accessible
- ✅ **Database**: `insurance_claims` database created
- ✅ **Tables**: Claims table with vector embeddings column
- ✅ **Data**: Sample claims data loaded

## Installation Steps

### 1. Clone/Navigate to Directory

```bash
cd insurance-claims-platform/services/adjuster-agent
```

### 2. Create Virtual Environment (Recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Expected installation time**: 2-5 minutes

### 4. Configure Environment

```bash
cp .env.example .env
nano .env  # or use your preferred editor
```

**Required configuration**:
```bash
DB_HOST=localhost          # Your CockroachDB host
DB_PORT=26257             # Your CockroachDB port
DB_NAME=insurance_claims  # Database name
DB_USER=root              # Database user
DB_PASSWORD=              # Database password (if any)
DB_SSLMODE=disable        # SSL mode (disable for local)
```

### 5. Verify Database Connection

```bash
python3 -c "
from database_client import DatabaseClient
client = DatabaseClient()
print('✅ Database connection successful!')
client.close()
"
```

### 6. Generate Embeddings (If Not Done)

```bash
cd ../claims-processor
python3 demo_embeddings.py
# Select option 5: Batch generate embeddings for existing claims
cd ../adjuster-agent
```

### 7. Start the Application

**Option A: Using startup script**
```bash
./start.sh
```

**Option B: Direct launch**
```bash
chainlit run app.py -w
```

**Option C: Production mode (no auto-reload)**
```bash
chainlit run app.py
```

### 8. Access the Interface

Open your browser to: **http://localhost:8000**

## Deployment Scenarios

### Local Development

```bash
# Start with auto-reload for development
chainlit run app.py -w --port 8000
```

**Features**:
- Auto-reload on file changes
- Debug logging enabled
- Local database connection

### Production Deployment

#### Option 1: Direct Process

```bash
# Run in production mode
chainlit run app.py --host 0.0.0.0 --port 8000
```

#### Option 2: Using systemd (Linux)

Create `/etc/systemd/system/adjuster-agent.service`:

```ini
[Unit]
Description=Adjuster Agent Chainlit Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/insurance-claims-platform/services/adjuster-agent
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/chainlit run app.py --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable adjuster-agent
sudo systemctl start adjuster-agent
sudo systemctl status adjuster-agent
```

#### Option 3: Using Docker

Create `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t adjuster-agent .
docker run -d -p 8000:8000 --env-file .env adjuster-agent
```

#### Option 4: Using Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  adjuster-agent:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DB_HOST=${DB_HOST}
      - DB_PORT=${DB_PORT}
      - DB_NAME=${DB_NAME}
      - DB_USER=${DB_USER}
      - DB_PASSWORD=${DB_PASSWORD}
    restart: unless-stopped
    depends_on:
      - cockroachdb
  
  cockroachdb:
    image: cockroachdb/cockroach:latest
    command: start-single-node --insecure
    ports:
      - "26257:26257"
      - "8080:8080"
    volumes:
      - cockroach-data:/cockroach/cockroach-data

volumes:
  cockroach-data:
```

Start services:
```bash
docker-compose up -d
```

### Cloud Deployment

#### AWS EC2

1. **Launch EC2 instance** (t3.medium or larger)
2. **Install dependencies**:
   ```bash
   sudo apt update
   sudo apt install python3-pip python3-venv
   ```
3. **Clone repository and setup**
4. **Configure security group**: Allow inbound on port 8000
5. **Use systemd** for process management

#### Google Cloud Run

1. **Create Dockerfile** (see above)
2. **Build and push**:
   ```bash
   gcloud builds submit --tag gcr.io/PROJECT_ID/adjuster-agent
   ```
3. **Deploy**:
   ```bash
   gcloud run deploy adjuster-agent \
     --image gcr.io/PROJECT_ID/adjuster-agent \
     --platform managed \
     --port 8000 \
     --set-env-vars DB_HOST=...,DB_PORT=...
   ```

#### Azure Container Instances

```bash
az container create \
  --resource-group myResourceGroup \
  --name adjuster-agent \
  --image adjuster-agent:latest \
  --ports 8000 \
  --environment-variables \
    DB_HOST=... \
    DB_PORT=... \
    DB_NAME=...
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | localhost | Database host |
| `DB_PORT` | 26257 | Database port |
| `DB_NAME` | insurance_claims | Database name |
| `DB_USER` | root | Database user |
| `DB_PASSWORD` | (empty) | Database password |
| `DB_SSLMODE` | disable | SSL mode |
| `CHAINLIT_HOST` | 0.0.0.0 | Chainlit host |
| `CHAINLIT_PORT` | 8000 | Chainlit port |
| `EMBEDDING_MODEL` | all-MiniLM-L6-v2 | Embedding model |
| `SIMILARITY_THRESHOLD` | 0.7 | Similarity threshold |
| `LOG_LEVEL` | INFO | Logging level |

### Chainlit Configuration

Edit `.chainlit` file for UI customization:

```toml
[UI]
name = "Adjuster Agent"
show_readme_as_default = true

[UI.theme.light]
primary = "#F80061"

[features]
prompt_playground = true
```

## Monitoring

### Health Check Endpoint

Create `health.py`:

```python
from database_client import DatabaseClient

def health_check():
    try:
        client = DatabaseClient()
        client.close()
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

### Logging

Logs are written to stdout in JSON format:

```json
{
  "event": "database_connected",
  "timestamp": "2026-05-03T03:00:00Z",
  "host": "localhost"
}
```

View logs:
```bash
# Direct run
tail -f logs/adjuster-agent.log

# Docker
docker logs -f adjuster-agent

# Systemd
journalctl -u adjuster-agent -f
```

### Metrics

Monitor these key metrics:

- **Response Time**: Query processing duration
- **Error Rate**: Failed queries per minute
- **Active Sessions**: Concurrent users
- **Database Connections**: Pool usage
- **Memory Usage**: Application memory
- **CPU Usage**: Processing load

## Security

### Production Checklist

- [ ] Use strong database passwords
- [ ] Enable SSL/TLS for database connections
- [ ] Set `DB_SSLMODE=require` in production
- [ ] Use environment variables (never commit `.env`)
- [ ] Implement rate limiting
- [ ] Enable CORS restrictions
- [ ] Use HTTPS (reverse proxy)
- [ ] Regular security updates
- [ ] Monitor access logs
- [ ] Implement authentication (if needed)

### Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name adjuster-agent.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### SSL/TLS (Let's Encrypt)

```bash
sudo certbot --nginx -d adjuster-agent.example.com
```

## Troubleshooting

### Common Issues

#### 1. Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
chainlit run app.py --port 8001
```

#### 2. Database Connection Failed

```bash
# Test connection
psql "postgresql://root@localhost:26257/insurance_claims?sslmode=disable"

# Check CockroachDB status
cockroach node status --insecure
```

#### 3. Module Not Found

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

#### 4. Embedding Model Download Failed

```bash
# Pre-download model
python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

#### 5. Out of Memory

```bash
# Increase system memory or reduce batch size
# Edit embeddings_client.py: max_results=5 (instead of 10)
```

### Debug Mode

Enable debug logging:

```bash
# In .env
LOG_LEVEL=DEBUG

# Or via command line
LOG_LEVEL=DEBUG chainlit run app.py
```

## Performance Tuning

### Database Optimization

```sql
-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM claims WHERE claim_number = 'CLM-2026-000001';

-- Update statistics
ANALYZE claims;

-- Check index usage
SELECT * FROM pg_stat_user_indexes WHERE relname = 'claims';
```

### Application Optimization

1. **Connection Pooling**: Already implemented in `database_client.py`
2. **Caching**: Consider Redis for frequent queries
3. **Async Operations**: Use `asyncio` for concurrent requests
4. **Batch Processing**: Process multiple queries together

### Resource Limits

```bash
# Limit memory usage (Docker)
docker run -m 2g adjuster-agent

# Limit CPU (Docker)
docker run --cpus=2 adjuster-agent
```

## Backup and Recovery

### Database Backup

```bash
# Backup claims data
cockroach dump insurance_claims claims --insecure > backup.sql

# Restore
cockroach sql --insecure < backup.sql
```

### Application Backup

```bash
# Backup configuration
tar -czf adjuster-agent-backup.tar.gz .env .chainlit

# Restore
tar -xzf adjuster-agent-backup.tar.gz
```

## Scaling

### Horizontal Scaling

```yaml
# docker-compose.yml
services:
  adjuster-agent:
    deploy:
      replicas: 3
    # ... rest of config

  nginx:
    image: nginx:latest
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
```

### Load Balancing

```nginx
upstream adjuster_agents {
    server adjuster-agent-1:8000;
    server adjuster-agent-2:8000;
    server adjuster-agent-3:8000;
}

server {
    location / {
        proxy_pass http://adjuster_agents;
    }
}
```

## Maintenance

### Regular Tasks

- **Daily**: Check logs for errors
- **Weekly**: Review performance metrics
- **Monthly**: Update dependencies
- **Quarterly**: Security audit

### Update Procedure

```bash
# 1. Backup current version
cp -r . ../adjuster-agent-backup

# 2. Pull latest changes
git pull

# 3. Update dependencies
pip install -r requirements.txt --upgrade

# 4. Test
python3 -m pytest tests/

# 5. Restart service
sudo systemctl restart adjuster-agent
```

## Support

For deployment issues:

1. Check logs: `journalctl -u adjuster-agent`
2. Verify configuration: `.env` file
3. Test database: `python3 -c "from database_client import DatabaseClient; DatabaseClient()"`
4. Review documentation: `README.md`, `ARCHITECTURE.md`

## Conclusion

The Adjuster Agent is now deployed and ready for use. Monitor the application regularly and follow best practices for security and performance.