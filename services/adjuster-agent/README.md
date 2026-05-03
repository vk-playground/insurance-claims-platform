# Claims Intelligence Assistant - Chainlit Chat Interface

AI-powered chat interface for insurance claim adjusters to query claims data, find similar claims, and detect fraud patterns using semantic search.

## Features

### 🔍 Query Capabilities

1. **Claim Details Lookup**
   - Get complete claim information by claim number
   - View policyholder details, amounts, risk scores, and status

2. **Policyholder Information**
   - Quick lookup of policyholder details for any claim
   - Contact information and policy numbers

3. **Semantic Similarity Search**
   - Find claims similar to a given description
   - Uses AI embeddings for intelligent matching
   - Powered by sentence-transformers

4. **Fraud Pattern Detection**
   - Identify suspicious claims based on description
   - Compare against known high-risk claims
   - Similarity scoring with risk analysis

5. **Statistics & Reports**
   - Overall claim statistics
   - Status distribution
   - Risk level analysis

6. **High-Risk Monitoring**
   - List claims with risk scores > 70
   - Escalated claims tracking

## Architecture

```
┌─────────────────┐
│  Chainlit UI    │  ← User Interface
└────────┬────────┘
         │
┌────────▼────────┐
│  AdjusterAgent  │  ← Main Agent Logic
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼──┐  ┌──▼────────┐
│ DB   │  │ Embeddings│
│Client│  │  Client   │
└───┬──┘  └──┬────────┘
    │        │
    └────┬───┘
         │
    ┌────▼────────┐
    │ CockroachDB │  ← Live Data
    │  + pgvector │
    └─────────────┘
```

## Installation

### 1. Install Dependencies

```bash
cd insurance-claims-platform/services/adjuster-agent
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your database credentials
```

### 3. Ensure Database Setup

Make sure the vector embeddings migration has been run:

```bash
cd ../claims-processor
python3 run_migration.py
```

### 4. Generate Embeddings (if not already done)

```bash
cd ../claims-processor
python3 demo_embeddings.py
# Select option 5 to batch generate embeddings
```

## Usage

### Start the Chainlit Interface

```bash
cd insurance-claims-platform/services/adjuster-agent
chainlit run app.py -w
```

The interface will be available at: `http://localhost:8000`

### Example Queries

#### 1. Get Claim Details
```
Who is the policyholder for claim #1?
Show me details for CLM-2026-000001
Get claim information for #123
```

#### 2. Find Similar Claims
```
Find claims similar to claim #1
Find similar claims: car accident on highway with rear-end collision
Search for claims like: water damage from burst pipe
```

#### 3. Fraud Detection
```
Find fraud patterns similar to: staged accident with fake injuries
Check for suspicious claims like: slip and fall at grocery store
Detect fraud patterns: whiplash injury from minor fender bender
```

#### 4. Statistics
```
Show me claim statistics
What's the average claim amount?
Give me a summary of all claims
```

#### 5. High-Risk Claims
```
Show me high-risk claims
List escalated claims
What claims need immediate attention?
```

## Components

### `app.py`
Main Chainlit application with:
- Chat interface handlers
- Intent detection
- Query routing
- Response formatting

### `database_client.py`
Database operations:
- Claim lookups
- Statistics queries
- High-risk claim filtering
- Policyholder searches

### `embeddings_client.py`
Semantic search operations:
- Vector similarity search
- Fraud pattern detection
- Embedding generation
- Cosine similarity scoring

### `config.py`
Configuration management:
- Database credentials
- Chainlit settings
- Embedding model configuration
- Logging setup

## Query Intent Detection

The agent automatically detects user intent:

| Intent | Triggers | Example |
|--------|----------|---------|
| `get_claim_details` | claim #, CLM- | "Show claim #123" |
| `find_policyholder` | policyholder, policy holder | "Who owns claim #1?" |
| `find_similar_claims` | similar, like, resembles | "Find similar claims" |
| `fraud_detection` | fraud, suspicious | "Check for fraud" |
| `claim_statistics` | statistics, stats, average | "Show stats" |
| `high_risk_claims` | high risk, escalated | "List high-risk" |

## Response Formats

### Claim Details Response
```
📋 Claim Details: CLM-2026-000001

Policyholder Information:
- Name: John Doe
- Email: john@example.com
- Policy Number: POL-2026-001

Claim Information:
- Type: Auto
- Amount: $5,000.00
- Status: UNDER_REVIEW
- Risk Score: 45/100
```

### Similar Claims Response
```
🔍 Found 3 Similar Claims:

1. Claim CLM-2026-000002 (Similarity: 87.5%)
- Amount: $4,500.00
- Risk Score: 42/100
- Description: Rear-end collision...
```

### Fraud Alert Response
```
⚠️ Fraud Alert: Found 2 Similar High-Risk Claims

1. Claim CLM-2026-000005 (Similarity: 82.3%)
- Risk Score: 85/100 ⚠️
- Amount: $8,000.00
- Status: ESCALATED

💡 Recommendation: Review these claims for potential fraud indicators.
```

## Technical Details

### Embedding Model
- **Model**: `all-MiniLM-L6-v2`
- **Dimensions**: 384
- **Provider**: sentence-transformers
- **Index**: HNSW (Hierarchical Navigable Small World)

### Similarity Thresholds
- **Default**: 0.7 (70% similarity)
- **Fraud Detection**: 0.65 (65% similarity)
- **Adjustable** via environment variables

### Database Queries
- Uses pgvector for similarity search
- Cosine distance operator: `<=>`
- Indexed for fast retrieval

## Troubleshooting

### Issue: "No similar claims found"
**Solution**: Ensure embeddings are generated:
```bash
cd ../claims-processor
python3 demo_embeddings.py
# Select option 5
```

### Issue: "Database connection failed"
**Solution**: Check `.env` configuration and ensure CockroachDB is running

### Issue: "Model loading failed"
**Solution**: Install sentence-transformers:
```bash
pip install sentence-transformers torch
```

### Issue: "Import chainlit could not be resolved"
**Solution**: Install Chainlit:
```bash
pip install chainlit
```

## Performance

- **Query Response Time**: < 500ms for claim lookups
- **Similarity Search**: < 1s for 10 results
- **Embedding Generation**: ~100ms per claim
- **Concurrent Users**: Supports multiple simultaneous sessions

## Security

- Database credentials via environment variables
- No hardcoded secrets
- SSL/TLS support for database connections
- Session isolation per user

## Future Enhancements

- [ ] Multi-language support
- [ ] Voice input/output
- [ ] Advanced analytics dashboard
- [ ] Real-time claim monitoring
- [ ] Integration with external fraud databases
- [ ] Automated report generation
- [ ] Mobile app support

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review logs in the terminal
3. Verify database connectivity
4. Ensure all dependencies are installed

## License

Part of the Insurance Claims Platform