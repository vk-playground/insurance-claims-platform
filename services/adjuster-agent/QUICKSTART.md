# Adjuster Agent - Quick Start Guide

Get your AI-powered claims adjuster chat interface running in 5 minutes!

## Prerequisites

✅ CockroachDB running on `localhost:26257`  
✅ Claims data in the `insurance_claims` database  
✅ Vector embeddings migration completed  
✅ Python 3.8+ installed

## Quick Setup

### 1. Navigate to the Directory

```bash
cd insurance-claims-platform/services/adjuster-agent
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment (Optional)

The `.env` file is already configured for local development. Edit if needed:

```bash
nano .env
```

### 4. Start the Interface

**Option A: Using the startup script (recommended)**
```bash
./start.sh
```

**Option B: Direct launch**
```bash
chainlit run app.py -w
```

### 5. Access the Interface

Open your browser to: **http://localhost:8000**

## First Queries to Try

Once the interface loads, try these queries:

### 1️⃣ Get Claim Details
```
Who is the policyholder for claim #1?
```

### 2️⃣ Find Similar Claims
```
Find claims similar to: car accident with rear-end collision
```

### 3️⃣ Detect Fraud Patterns
```
Find fraud patterns similar to: staged accident with fake injuries
```

### 4️⃣ View Statistics
```
Show me claim statistics
```

### 5️⃣ Monitor High-Risk Claims
```
Show me high-risk claims
```

## Troubleshooting

### ❌ "Database connection failed"

**Check if CockroachDB is running:**
```bash
cockroach sql --insecure --host=localhost:26257
```

**Verify database exists:**
```sql
SHOW DATABASES;
USE insurance_claims;
SHOW TABLES;
```

### ❌ "No similar claims found"

**Generate embeddings first:**
```bash
cd ../claims-processor
python3 demo_embeddings.py
# Select option 5: Batch generate embeddings
```

### ❌ "Import chainlit could not be resolved"

**Install Chainlit:**
```bash
pip install chainlit
```

### ❌ "Model loading failed"

**Install sentence-transformers:**
```bash
pip install sentence-transformers torch
```

## Architecture Overview

```
┌──────────────────────────────────────┐
│     Browser (localhost:8000)         │
│  ┌────────────────────────────────┐  │
│  │   Chainlit Chat Interface      │  │
│  └────────────────────────────────┘  │
└──────────────┬───────────────────────┘
               │
               │ WebSocket
               │
┌──────────────▼───────────────────────┐
│      Adjuster Agent (app.py)         │
│  ┌────────────────────────────────┐  │
│  │  Intent Detection & Routing    │  │
│  └────────────────────────────────┘  │
└──────────────┬───────────────────────┘
               │
        ┌──────┴──────┐
        │             │
┌───────▼──────┐  ┌──▼────────────┐
│ Database     │  │  Embeddings   │
│ Client       │  │  Client       │
│              │  │               │
│ - Queries    │  │ - Similarity  │
│ - Stats      │  │ - Fraud Det.  │
└───────┬──────┘  └──┬────────────┘
        │            │
        └─────┬──────┘
              │
    ┌─────────▼──────────┐
    │   CockroachDB      │
    │   + pgvector       │
    │                    │
    │ - Claims Table     │
    │ - Vector Index     │
    └────────────────────┘
```

## Key Features

### 🎯 Natural Language Understanding
The agent understands various ways to ask questions:
- "Who is the policyholder for claim #123?"
- "Show me claim CLM-2026-000001"
- "Get details for claim 456"

### 🔍 Semantic Search
Uses AI embeddings to find similar claims based on meaning, not just keywords:
- "Find claims like: water damage from burst pipe"
- "Search for similar: slip and fall accident"

### ⚠️ Fraud Detection
Identifies suspicious patterns by comparing to known high-risk claims:
- "Find fraud patterns similar to: staged accident"
- "Check for suspicious claims like this description"

### 📊 Real-Time Analytics
Live statistics from your CockroachDB:
- Total claims and amounts
- Status distribution
- Risk level analysis

## Example Session

```
You: Who is the policyholder for claim #1?

Agent: 👤 Policyholder for Claim CLM-2026-000001:
- Name: John Doe
- Email: john@example.com
- Phone: (555) 123-4567
- Policy Number: POL-2026-001

---

You: Find fraud patterns similar to: rear-end collision with whiplash

Agent: ⚠️ Fraud Alert: Found 3 Similar High-Risk Claims

1. Claim CLM-2026-000005 (Similarity: 85.2%)
- Risk Score: 87/100 ⚠️
- Amount: $8,500.00
- Status: ESCALATED
- Description: Rear-end collision with claimed whiplash...

💡 Recommendation: Review these claims for potential fraud indicators.
```

## Performance Tips

### 🚀 Speed Optimization

1. **Pre-generate embeddings** for all claims:
   ```bash
   cd ../claims-processor
   python3 demo_embeddings.py  # Option 5
   ```

2. **Use specific claim numbers** when possible:
   ```
   "Show claim #123" (fast)
   vs
   "Find all claims by John" (slower)
   ```

3. **Adjust similarity threshold** for faster searches:
   - Edit `.env`: `SIMILARITY_THRESHOLD=0.75` (higher = faster, fewer results)

## Advanced Usage

### Custom Similarity Threshold

Edit `.env`:
```bash
SIMILARITY_THRESHOLD=0.65  # Lower = more results, less strict
```

### Change Port

Edit `.env`:
```bash
CHAINLIT_PORT=8080
```

Then access at: `http://localhost:8080`

### Enable Debug Logging

Edit `.env`:
```bash
LOG_LEVEL=DEBUG
```

## Next Steps

1. ✅ **Test the interface** with sample queries
2. ✅ **Generate embeddings** for all claims
3. ✅ **Explore fraud detection** capabilities
4. ✅ **Review statistics** and insights
5. ✅ **Integrate** with your workflow

## Support

- 📖 Full documentation: `README.md`
- 🔧 Configuration: `.env`
- 📊 Database schema: `../../database/schema.sql`
- 🧪 Test embeddings: `../claims-processor/demo_embeddings.py`

## What's Next?

Try these advanced queries:
- "Find all claims by policyholder John Doe"
- "Show me claims with risk score above 80"
- "Compare claim #1 to claim #5"
- "What's the average claim amount for auto claims?"

Happy adjusting! 🎉