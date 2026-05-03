# Vector Embeddings for Semantic Claim Search

This document explains how to use vector embeddings for semantic similarity search on insurance claims.

## Overview

Vector embeddings enable semantic search on claim descriptions, allowing you to:
- Find similar claims based on meaning, not just keywords
- Detect potential duplicate claims
- Identify fraud patterns
- Route claims to appropriate adjusters
- Estimate settlements based on historical data

## Architecture

### Components

1. **Embedding Generator** (`embeddings.py`)
   - Uses `sentence-transformers` library
   - Model: `all-MiniLM-L6-v2` (384 dimensions)
   - Converts text to vector representations

2. **Database Schema** (CockroachDB with pgvector)
   - `description_embedding` VECTOR(384) column
   - HNSW index for fast similarity search
   - Metadata columns for tracking

3. **Claim Embedding Manager** (`embeddings.py`)
   - Generates and stores embeddings
   - Performs similarity searches
   - Batch processing for existing claims

## Installation

### 1. Install Dependencies

```bash
cd insurance-claims-platform/services/claims-processor
pip install -r requirements.txt
```

This installs:
- `sentence-transformers==2.2.2` - For generating embeddings
- `numpy==1.24.3` - For vector operations
- `torch==2.1.0` - Required by sentence-transformers

### 2. Run Database Migration

```bash
python3 run_migration.py
```

This adds:
- `description_embedding` VECTOR(384) column
- `embedding_model` VARCHAR(100) column
- `embedding_generated_at` TIMESTAMP column
- HNSW index for fast similarity search

## Usage

### Basic Example

```python
from database import DatabaseManager
from embeddings import EmbeddingGenerator, ClaimEmbeddingManager

# Initialize
db = DatabaseManager()
db.connect()
manager = ClaimEmbeddingManager(db)

# Generate and store embedding for a claim
manager.generate_and_store_embedding(
    claim_number="CLM-2026-001",
    description="Minor collision at intersection, rear-end accident"
)

# Search for similar claims
similar_claims = manager.find_similar_claims(
    query_text="Car accident on highway",
    similarity_threshold=0.7,
    max_results=5
)

for claim in similar_claims:
    print(f"{claim['claim_number']}: {claim['similarity_score']:.2f}")
```

### Generating Embeddings

#### For a Single Claim

```python
from embeddings import EmbeddingGenerator

generator = EmbeddingGenerator()
embedding = generator.generate_embedding("Water damage from burst pipe")
print(f"Embedding dimensions: {len(embedding)}")  # 384
```

#### For Multiple Claims (Batch)

```python
texts = [
    "Car accident on highway",
    "Water damage in basement",
    "Fire damage to kitchen"
]
embeddings = generator.generate_batch_embeddings(texts)
print(f"Generated {len(embeddings)} embeddings")
```

#### For Existing Claims in Database

```python
# Process up to 100 claims without embeddings
stats = manager.batch_generate_embeddings_for_existing_claims(batch_size=100)
print(f"Processed: {stats['processed']}")
print(f"Updated: {stats['updated']}")
```

### Similarity Search

#### Basic Search

```python
similar = manager.find_similar_claims(
    query_text="Vehicle collision on freeway",
    similarity_threshold=0.7,  # 0-1 scale (1 = identical)
    max_results=10
)
```

#### Advanced Search with Filters

```python
# Search in database directly
with db.conn.cursor() as cursor:
    cursor.execute("""
        SELECT 
            claim_number,
            description,
            1 - (description_embedding <=> %s::VECTOR(384)) AS similarity
        FROM claims
        WHERE description_embedding IS NOT NULL
            AND status = 'UNDER_REVIEW'
            AND claim_amount > 5000
            AND 1 - (description_embedding <=> %s::VECTOR(384)) > 0.7
        ORDER BY description_embedding <=> %s::VECTOR(384)
        LIMIT 10
    """, (embedding_str, embedding_str, embedding_str))
```

### Computing Similarity

```python
# Compare two claim descriptions
emb1 = generator.generate_embedding("Car accident on highway")
emb2 = generator.generate_embedding("Vehicle collision on freeway")

similarity = generator.compute_similarity(emb1, emb2)
print(f"Similarity: {similarity:.4f}")  # ~0.85 (high similarity)
```

## Use Cases

### 1. Fraud Detection

Find claims similar to known fraudulent claims:

```python
# Get embedding from known fraud case
fraud_claim = "Staged accident with fake injuries at intersection"
similar = manager.find_similar_claims(fraud_claim, similarity_threshold=0.75)

# Review similar claims for potential fraud
for claim in similar:
    if claim['risk_score'] > 60:
        print(f"⚠️ Potential fraud: {claim['claim_number']}")
```

### 2. Duplicate Detection

Identify potential duplicate claims:

```python
new_claim_desc = "Rear-end collision at Main St and 5th Ave"
duplicates = manager.find_similar_claims(new_claim_desc, similarity_threshold=0.85)

if duplicates:
    print(f"⚠️ Found {len(duplicates)} potential duplicates")
```

### 3. Historical Analysis

Find similar resolved claims for settlement estimation:

```python
# Search for similar claims
similar = manager.find_similar_claims(
    "Water damage from burst pipe in basement",
    similarity_threshold=0.7
)

# Calculate average settlement
resolved = [c for c in similar if c['status'] == 'PAID']
avg_amount = sum(c['claim_amount'] for c in resolved) / len(resolved)
print(f"Average settlement: ${avg_amount:,.2f}")
```

### 4. Auto-Assignment to Adjusters

Route claims based on adjuster expertise:

```python
# Find similar claims handled by specific adjuster
with db.conn.cursor() as cursor:
    cursor.execute("""
        SELECT 
            assigned_adjuster_id,
            COUNT(*) as claim_count,
            AVG(1 - (description_embedding <=> %s::VECTOR(384))) as avg_similarity
        FROM claims
        WHERE description_embedding IS NOT NULL
            AND assigned_adjuster_id IS NOT NULL
            AND status IN ('PAID', 'CLOSED')
        GROUP BY assigned_adjuster_id
        HAVING AVG(1 - (description_embedding <=> %s::VECTOR(384))) > 0.7
        ORDER BY avg_similarity DESC
        LIMIT 1
    """, (embedding_str, embedding_str))
```

## Performance

### Model Specifications

- **Model**: `all-MiniLM-L6-v2`
- **Dimensions**: 384
- **Size**: ~80MB
- **Speed**: ~1000 sentences/second on CPU
- **Quality**: Good balance of speed and accuracy

### Index Performance

- **Index Type**: HNSW (Hierarchical Navigable Small World)
- **Distance Metric**: Cosine similarity
- **Search Speed**: Sub-millisecond for millions of vectors
- **Accuracy**: ~95% recall at 10

### Optimization Tips

1. **Batch Processing**: Use `generate_batch_embeddings()` for multiple claims
2. **Caching**: Store embeddings in database, regenerate only when description changes
3. **Async Processing**: Generate embeddings asynchronously after claim creation
4. **Index Tuning**: Adjust HNSW parameters for your workload

## Demo Script

Run the demo to see embeddings in action:

```bash
python3 demo_embeddings.py
```

This demonstrates:
1. Generating embeddings for sample claims
2. Computing similarity between claims
3. Storing and searching embeddings in database
4. Practical use cases

## API Reference

### EmbeddingGenerator

```python
class EmbeddingGenerator:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2')
    def generate_embedding(self, text: str) -> List[float]
    def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]
    def compute_similarity(self, emb1: List[float], emb2: List[float]) -> float
```

### ClaimEmbeddingManager

```python
class ClaimEmbeddingManager:
    def __init__(self, db_manager, embedding_generator: Optional[EmbeddingGenerator] = None)
    def generate_and_store_embedding(self, claim_number: str, description: str) -> bool
    def find_similar_claims(self, query_text: str, similarity_threshold: float = 0.7, max_results: int = 10) -> List[Dict]
    def batch_generate_embeddings_for_existing_claims(self, batch_size: int = 100) -> Dict[str, int]
```

## Troubleshooting

### Issue: "Model not found"

```bash
# Download model manually
python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

### Issue: "Vector dimension mismatch"

Ensure you're using the correct model (384 dimensions):
```python
generator = EmbeddingGenerator('all-MiniLM-L6-v2')
print(generator.model.get_sentence_embedding_dimension())  # Should be 384
```

### Issue: "Slow similarity search"

Check if HNSW index exists:
```sql
SELECT indexname FROM pg_indexes 
WHERE tablename = 'claims' 
AND indexname = 'idx_claims_description_embedding';
```

## Best Practices

1. **Generate embeddings asynchronously** after claim creation
2. **Set appropriate similarity thresholds** (0.7-0.8 for most use cases)
3. **Combine with traditional filters** (status, amount, date) for better results
4. **Monitor embedding generation time** and optimize batch sizes
5. **Regenerate embeddings** when claim descriptions are significantly updated
6. **Use batch processing** for historical data migration

## Resources

- [Sentence Transformers Documentation](https://www.sbert.net/)
- [CockroachDB Vector Documentation](https://www.cockroachlabs.com/docs/stable/vector.html)
- [HNSW Algorithm Paper](https://arxiv.org/abs/1603.09320)

## Made with Bob