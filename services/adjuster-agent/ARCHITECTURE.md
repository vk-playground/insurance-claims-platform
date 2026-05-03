# Adjuster Agent Architecture

Detailed technical architecture for the Chainlit-based Adjuster Agent interface.

## System Overview

The Adjuster Agent is an AI-powered conversational interface that enables insurance claim adjusters to query claims data, perform semantic similarity searches, and detect fraud patterns through natural language interactions.

## Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface Layer                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              Chainlit Web Interface                    │  │
│  │  - WebSocket connection                                │  │
│  │  - Real-time chat                                      │  │
│  │  - Markdown rendering                                  │  │
│  │  - Session management                                  │  │
│  └────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ HTTP/WebSocket
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                   Application Layer                          │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                  AdjusterAgent                         │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │  Intent Detection Engine                         │  │  │
│  │  │  - Regex pattern matching                        │  │  │
│  │  │  - Claim number extraction                       │  │  │
│  │  │  - Query classification                          │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │  Query Router                                    │  │  │
│  │  │  - Route to appropriate handler                  │  │  │
│  │  │  - Context management                            │  │  │
│  │  │  - Response formatting                           │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │  Conversation History                            │  │  │
│  │  │  - Session-based storage                         │  │  │
│  │  │  - Context preservation                          │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
┌───────────────▼──────────┐  ┌────────▼──────────────────────┐
│   Data Access Layer      │  │   AI/ML Layer                 │
│  ┌────────────────────┐  │  │  ┌─────────────────────────┐  │
│  │ DatabaseClient     │  │  │  │  EmbeddingsClient       │  │
│  │                    │  │  │  │                         │  │
│  │ - Connection pool  │  │  │  │ - SentenceTransformer   │  │
│  │ - Query execution  │  │  │  │ - Vector generation     │  │
│  │ - Result mapping   │  │  │  │ - Similarity search     │  │
│  │ - Error handling   │  │  │  │ - Fraud detection       │  │
│  └────────────────────┘  │  │  └─────────────────────────┘  │
└───────────────┬──────────┘  └────────┬──────────────────────┘
                │                      │
                └──────────┬───────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    Data Storage Layer                        │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              CockroachDB + pgvector                    │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │  Claims Table                                    │  │  │
│  │  │  - Structured claim data                         │  │  │
│  │  │  - Vector embeddings (384 dimensions)            │  │  │
│  │  │  - HNSW index for fast similarity search         │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. User Query Flow

```
User Input
    │
    ├─> Chainlit Interface
    │       │
    │       ├─> WebSocket Message
    │       │
    │       └─> AdjusterAgent.process_query()
    │               │
    │               ├─> Intent Detection
    │               │       │
    │               │       ├─> Regex Pattern Matching
    │               │       ├─> Claim Number Extraction
    │               │       └─> Query Classification
    │               │
    │               ├─> Query Routing
    │               │       │
    │               │       ├─> get_claim_details
    │               │       ├─> find_policyholder
    │               │       ├─> find_similar_claims
    │               │       ├─> fraud_detection
    │               │       ├─> claim_statistics
    │               │       └─> high_risk_claims
    │               │
    │               └─> Response Formatting
    │                       │
    │                       └─> Markdown Response
    │
    └─> Display to User
```

### 2. Database Query Flow

```
Query Request
    │
    ├─> DatabaseClient
    │       │
    │       ├─> Connection Pool
    │       │       │
    │       │       └─> psycopg2 Connection
    │       │
    │       ├─> SQL Query Execution
    │       │       │
    │       │       ├─> Parameterized Query
    │       │       ├─> RealDictCursor
    │       │       └─> Result Fetching
    │       │
    │       └─> Result Mapping
    │               │
    │               └─> Python Dictionary
    │
    └─> Return to Agent
```

### 3. Semantic Search Flow

```
Search Query
    │
    ├─> EmbeddingsClient
    │       │
    │       ├─> Text Preprocessing
    │       │
    │       ├─> SentenceTransformer
    │       │       │
    │       │       ├─> Tokenization
    │       │       ├─> Model Inference
    │       │       └─> 384-dim Vector
    │       │
    │       ├─> Vector Search Query
    │       │       │
    │       │       ├─> pgvector Cosine Distance
    │       │       ├─> HNSW Index Lookup
    │       │       └─> Similarity Threshold Filter
    │       │
    │       └─> Ranked Results
    │               │
    │               └─> Similarity Scores
    │
    └─> Return to Agent
```

## Intent Detection System

### Pattern Matching Rules

```python
Intent Detection Logic:
├─> Claim Details
│   └─> Patterns: r'claim\s*#?\s*\d+|clm-\d+-\d+'
│
├─> Policyholder Query
│   └─> Keywords: 'policyholder', 'policy holder'
│   └─> + Claim number present
│
├─> Similarity Search
│   └─> Keywords: 'similar', 'like', 'resembles', 'comparable'
│
├─> Fraud Detection
│   └─> Keywords: 'fraud', 'suspicious', 'fraudulent'
│
├─> Statistics
│   └─> Keywords: 'statistics', 'stats', 'average', 'total', 'count'
│
└─> High Risk
    └─> Keywords: 'high risk', 'escalated'
```

### Claim Number Extraction

```python
Extraction Patterns:
1. "claim #123"        → CLM-2026-000123
2. "CLM-2026-000001"   → CLM-2026-000001
3. "#456"              → CLM-2026-000456
```

## Database Schema Integration

### Claims Table Structure

```sql
CREATE TABLE claims (
    claim_id UUID PRIMARY KEY,
    claim_number VARCHAR(50) UNIQUE,
    policy_number VARCHAR(50),
    claimant_name VARCHAR(255),
    claimant_email VARCHAR(255),
    claimant_phone VARCHAR(20),
    claim_type VARCHAR(50),
    claim_amount DECIMAL(12,2),
    incident_date DATE,
    claim_date TIMESTAMP,
    description TEXT,
    status VARCHAR(50),
    status_reason TEXT,
    risk_score INTEGER,
    
    -- Vector embeddings
    description_embedding VECTOR(384),
    embedding_model VARCHAR(100),
    embedding_generated_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- HNSW Index for fast similarity search
CREATE INDEX idx_claims_embedding 
ON claims 
USING hnsw (description_embedding vector_cosine_ops);
```

### Query Patterns

#### 1. Claim Lookup
```sql
SELECT * FROM claims WHERE claim_number = $1;
```

#### 2. Similarity Search
```sql
SELECT 
    *,
    1 - (description_embedding <=> $1::vector) as similarity_score
FROM claims
WHERE description_embedding IS NOT NULL
    AND 1 - (description_embedding <=> $1::vector) >= $2
ORDER BY description_embedding <=> $1::vector
LIMIT $3;
```

#### 3. Statistics Aggregation
```sql
SELECT 
    COUNT(*) as total_claims,
    SUM(claim_amount) as total_amount,
    AVG(claim_amount) as average_amount,
    AVG(risk_score) as average_risk_score,
    COUNT(CASE WHEN status = 'AUTO_APPROVED' THEN 1 END) as approved_count
FROM claims;
```

## AI/ML Components

### Sentence Transformer Model

**Model**: `all-MiniLM-L6-v2`
- **Architecture**: Transformer-based
- **Dimensions**: 384
- **Training**: Sentence similarity tasks
- **Performance**: ~120ms per encoding
- **Memory**: ~90MB model size

### Vector Similarity

**Distance Metric**: Cosine Distance
```
distance = 1 - cosine_similarity
similarity_score = 1 - distance
```

**Threshold Tuning**:
- 0.9-1.0: Nearly identical
- 0.8-0.9: Very similar
- 0.7-0.8: Similar (default)
- 0.6-0.7: Somewhat similar
- <0.6: Different

### HNSW Index

**Algorithm**: Hierarchical Navigable Small World
- **Type**: Approximate Nearest Neighbor (ANN)
- **Trade-off**: Speed vs Accuracy
- **Performance**: O(log n) search time
- **Build Time**: O(n log n)

## Session Management

### Chainlit Session Lifecycle

```
Session Start
    │
    ├─> @cl.on_chat_start
    │       │
    │       ├─> Create AdjusterAgent instance
    │       ├─> Initialize database connections
    │       ├─> Load embedding model
    │       └─> Store in cl.user_session
    │
    ├─> Message Processing
    │       │
    │       ├─> @cl.on_message
    │       ├─> Retrieve agent from session
    │       ├─> Process query
    │       └─> Send response
    │
    └─> Session End
            │
            └─> @cl.on_chat_end
                    │
                    ├─> Close database connections
                    ├─> Cleanup resources
                    └─> Log session end
```

## Error Handling

### Error Hierarchy

```
Exception Handling:
├─> Database Errors
│   ├─> Connection failures
│   ├─> Query timeouts
│   └─> Data integrity errors
│
├─> Embedding Errors
│   ├─> Model loading failures
│   ├─> Encoding errors
│   └─> Vector dimension mismatches
│
├─> Application Errors
│   ├─> Invalid claim numbers
│   ├─> Missing data
│   └─> Session errors
│
└─> User-Friendly Messages
    └─> Formatted error responses
```

## Performance Optimization

### Caching Strategy

```
Cache Layers:
├─> Database Connection Pool
│   └─> Reuse connections across requests
│
├─> Model Loading
│   └─> Load once, reuse for all sessions
│
└─> Query Results (Future)
    └─> Cache frequent queries
```

### Query Optimization

1. **Indexed Lookups**: Use claim_number index
2. **Vector Search**: HNSW index for O(log n) performance
3. **Limit Results**: Default max_results=10
4. **Threshold Filtering**: Pre-filter before sorting

## Security Considerations

### Data Protection

```
Security Measures:
├─> Database
│   ├─> Parameterized queries (SQL injection prevention)
│   ├─> Connection encryption (SSL/TLS)
│   └─> Credential management (.env)
│
├─> Session
│   ├─> Isolated user sessions
│   ├─> No cross-session data leakage
│   └─> Automatic cleanup
│
└─> Input Validation
    ├─> Claim number format validation
    ├─> Query length limits
    └─> Sanitized outputs
```

## Monitoring & Logging

### Structured Logging

```python
Log Events:
├─> database_connected
├─> database_connection_failed
├─> query_processing_failed
├─> embeddings_model_loaded
├─> find_similar_claims_failed
└─> chat_session_ended
```

### Metrics to Track

- Query response times
- Database connection pool usage
- Embedding generation times
- Similarity search performance
- Error rates by type
- User session durations

## Scalability

### Horizontal Scaling

```
Load Balancing:
├─> Multiple Chainlit instances
├─> Shared CockroachDB cluster
├─> Stateless application design
└─> Session affinity (WebSocket)
```

### Vertical Scaling

```
Resource Optimization:
├─> Database
│   ├─> Connection pooling
│   └─> Query optimization
│
├─> Embeddings
│   ├─> Batch processing
│   └─> GPU acceleration (optional)
│
└─> Application
    ├─> Async operations
    └─> Memory management
```

## Future Enhancements

### Planned Features

1. **Multi-modal Search**
   - Image similarity
   - Document analysis

2. **Advanced Analytics**
   - Trend detection
   - Predictive modeling

3. **Integration**
   - External fraud databases
   - Policy management systems

4. **Collaboration**
   - Multi-user sessions
   - Shared annotations

## Technology Stack

```
Frontend:
├─> Chainlit 1.0.0
└─> WebSocket

Backend:
├─> Python 3.8+
├─> psycopg2-binary 2.9.9
└─> structlog 23.1.0

AI/ML:
├─> sentence-transformers 2.2.2
├─> torch 2.1.0
└─> numpy 1.24.3

Database:
├─> CockroachDB
└─> pgvector 0.2.3

Configuration:
└─> python-dotenv 1.0.0
```

## Deployment Architecture

```
Production Deployment:
├─> Application Tier
│   ├─> Multiple Chainlit instances
│   ├─> Load balancer
│   └─> Auto-scaling
│
├─> Database Tier
│   ├─> CockroachDB cluster
│   ├─> Read replicas
│   └─> Backup strategy
│
└─> Monitoring Tier
    ├─> Application logs
    ├─> Performance metrics
    └─> Error tracking
```

## Conclusion

The Adjuster Agent architecture provides a scalable, maintainable, and performant solution for AI-powered claims processing. The modular design allows for easy extension and integration with existing systems while maintaining security and reliability.