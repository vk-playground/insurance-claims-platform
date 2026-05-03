# CockroachDB Serverless Connection Guide

## Issue

CockroachDB Serverless requires a cluster identifier to route connections properly. Without it, you'll see this error:

```
FATAL: codeParamsRoutingFailed: missing cluster identifier
```

## Solution

The Adjuster Agent automatically extracts the cluster identifier from the hostname and adds it as an options parameter.

### How It Works

For a hostname like:
```
claims-demo-15395.jxf.gcp-us-east1.cockroachlabs.cloud
```

The code extracts `claims-demo-15395` and adds it as:
```python
options='--cluster=claims-demo-15395'
```

### Implementation

Both `database_client.py` and `embeddings_client.py` include this logic:

```python
def _connect(self):
    """Establish database connection."""
    try:
        # Extract cluster identifier from hostname for CockroachDB Serverless
        cluster_id = None
        if 'cockroachlabs.cloud' in self.config.DB_HOST:
            cluster_id = self.config.DB_HOST.split('.')[0]
        
        # Build connection parameters
        conn_params = {
            'host': self.config.DB_HOST,
            'port': self.config.DB_PORT,
            'database': self.config.DB_NAME,
            'user': self.config.DB_USER,
            'password': self.config.DB_PASSWORD,
            'sslmode': self.config.DB_SSLMODE,
            'connect_timeout': 10
        }
        
        # Add cluster identifier for CockroachDB Serverless
        if cluster_id:
            conn_params['options'] = f'--cluster={cluster_id}'
        
        self.conn = psycopg2.connect(**conn_params)
```

## Configuration

Your `.env` file should have:

```bash
DB_HOST=claims-demo-15395.jxf.gcp-us-east1.cockroachlabs.cloud
DB_PORT=26257
DB_NAME=defaultdb
DB_USER=vicky
DB_PASSWORD=your_password_here
DB_SSLMODE=verify-full
```

## Alternative Methods

If the automatic extraction doesn't work, you can manually specify the cluster identifier in three ways:

### Method 1: Options Parameter (Recommended)
```python
conn = psycopg2.connect(
    host='claims-demo-15395.jxf.gcp-us-east1.cockroachlabs.cloud',
    port=26257,
    database='defaultdb',
    user='vicky',
    password='your_password',
    sslmode='verify-full',
    options='--cluster=claims-demo-15395'  # Add this
)
```

### Method 2: Database Parameter
```python
conn = psycopg2.connect(
    host='claims-demo-15395.jxf.gcp-us-east1.cockroachlabs.cloud',
    port=26257,
    database='claims-demo-15395.defaultdb',  # Prefix with cluster ID
    user='vicky',
    password='your_password',
    sslmode='verify-full'
)
```

### Method 3: Connection String
```python
conn_string = "postgresql://vicky:password@claims-demo-15395.jxf.gcp-us-east1.cockroachlabs.cloud:26257/defaultdb?sslmode=verify-full&options=--cluster%3Dclaims-demo-15395"
conn = psycopg2.connect(conn_string)
```

## Testing Connection

Test your connection with:

```bash
python3 -c "
from database_client import DatabaseClient
client = DatabaseClient()
print('✅ Connection successful!')
"
```

Or use the test script:

```bash
python3 test_setup.py
```

## Troubleshooting

### Error: "missing cluster identifier"
- **Cause**: Cluster identifier not properly extracted or specified
- **Solution**: Verify your `DB_HOST` includes the full hostname with cluster ID

### Error: "SSL connection required"
- **Cause**: `DB_SSLMODE` not set to `verify-full`
- **Solution**: Set `DB_SSLMODE=verify-full` in `.env`

### Error: "authentication failed"
- **Cause**: Incorrect username or password
- **Solution**: Verify credentials in CockroachDB Cloud console

### Error: "connection timeout"
- **Cause**: Network connectivity issues or firewall blocking
- **Solution**: Check network connectivity and firewall rules

## CockroachDB Cloud Console

To get your connection details:

1. Go to https://cockroachlabs.cloud/
2. Select your cluster
3. Click "Connect"
4. Choose "Connection string"
5. Copy the hostname, username, and password

## References

- [CockroachDB Serverless Documentation](https://www.cockroachlabs.com/docs/cockroachcloud/connect-to-a-serverless-cluster)
- [psycopg2 Connection Parameters](https://www.psycopg.org/docs/module.html#psycopg2.connect)
- [CockroachDB Connection Strings](https://www.cockroachlabs.com/docs/stable/connection-parameters.html)

## Support

If you continue to have connection issues:

1. Check the logs: `tail -f logs/adjuster-agent.log`
2. Enable debug logging: `LOG_LEVEL=DEBUG` in `.env`
3. Verify credentials in CockroachDB Cloud console
4. Contact support with error messages and connection details