# Insurance Claims Intelligence Platform - Complete Architecture

## Executive Summary

The Insurance Claims Intelligence Platform is an AI-powered, event-driven system that combines real-time stream processing, distributed SQL, vector embeddings, and large language models to provide intelligent claims processing and conversational analytics. This document explains the complete architecture and the strategic reasons behind each technology choice.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    User Interface Layer                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Chainlit Chat Interface (Conversational AI)              │  │
│  │  - Natural language queries                               │  │
│  │  - Real-time notifications (Chainlit's built-in WS)       │  │
│  │  - Context-aware conversations                            │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  AI/ML Intelligence Layer                        │
│  ┌────────────────────┐  ┌──────────────────────────────────┐  │
│  │ IBM Watsonx.ai LLM │  │ Sentence Transformers            │  │
│  │ (Llama 3.3 70B)    │  │ (all-MiniLM-L6-v2)              │  │
│  │                    │  │                                  │  │
│  │ • Conversational   │  │ • Text → 384-dim vectors        │  │
│  │ • Context-aware    │  │ • Semantic similarity           │  │
│  │ • Intent detection │  │ • Fraud pattern matching        │  │
│  └────────────────────┘  └──────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Application Layer                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Claims Processor Service (Python)                        │  │
│  │  - Kafka consumer (claims.ingest)                         │  │
│  │  - Policy verification                                    │  │
│  │  - AI logic gate (auto-approval/escalation)              │  │
│  │  - Embedding generation                                   │  │
│  │  - Event production (approved/escalated/under_review)    │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Adjuster Agent Service (Python + Chainlit)              │  │
│  │  - LLM-powered conversational interface                  │  │
│  │  - Database query orchestration                          │  │
│  │  - Vector similarity search                              │  │
│  │  - Background Kafka monitoring (threading)               │  │
│  │  - Hybrid approach (LLM + pattern fallback)              │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Data Layer                                    │
│  ┌────────────────────┐  ┌──────────────────────────────────┐  │
│  │ Confluent Cloud    │  │ CockroachDB Cloud + pgvector     │  │
│  │ (Kafka)            │  │                                  │  │
│  │                    │  │ • Distributed SQL                │  │
│  │ • Event streaming  │  │ • ACID transactions              │  │
│  │ • Real-time data   │  │ • Vector embeddings (384-dim)    │  │
│  │ • Decoupling       │  │ • HNSW index for similarity      │  │
│  │ • Scalability      │  │ • Global distribution            │  │
│  │ • SASL_SSL auth    │  │ • SSL/TLS (sslmode=verify-full)  │  │
│  └────────────────────┘  └──────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Why This Architecture? Strategic Technology Choices

### 1. Confluent Cloud Kafka - Event Streaming Backbone

**Why Kafka?**
- **Real-time Processing**: Claims need immediate processing, not batch jobs
- **Event-Driven Architecture**: Decouples services for independent scaling
- **Durability**: Events are persisted, enabling replay and audit trails
- **Scalability**: Handles millions of claims without bottlenecks
- **Integration**: Standard protocol for microservices communication

**Why Confluent Cloud?**
- **Managed Service**: No infrastructure management overhead
- **Enterprise Features**: Schema registry, connectors, monitoring
- **Global Availability**: Multi-region deployment for disaster recovery
- **Security**: Built-in SASL_SSL, encryption at rest/transit
- **Cost-Effective**: Pay-per-use vs. self-hosting Kafka clusters

**Our Implementation**:
```python
# Kafka configuration with SASL_SSL authentication
consumer_config = {
    'bootstrap.servers': 'pkc-4rn2p.canadacentral.azure.confluent.cloud:9092',
    'security.protocol': 'SASL_SSL',  # TLS encryption
    'sasl.mechanism': 'PLAIN',
    'sasl.username': '<API_KEY>',
    'sasl.password': '<API_SECRET>',
    'group.id': 'claims-processor'
}

# Topics designed for claim lifecycle
claims.ingest        → New claims enter the system
claims.approved      → Auto-approved claims (< $2K, Risk < 20)
claims.escalated     → High-risk claims (Risk > 80)
claims.under_review  → Manual review required
```

**Background Monitoring** (Threading, NOT WebSocket):
```python
# kafka_monitor.py - Background thread monitoring
class KafkaClaimMonitor:
    def start_monitoring(self):
        # Runs in separate daemon thread
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
    
    def _monitor_loop(self):
        while self.running:
            msg = self.consumer.poll(timeout=1.0)
            # Process messages in background
```

### 2. CockroachDB Cloud - Distributed SQL Database

**Why CockroachDB?**
- **Distributed by Design**: No single point of failure
- **ACID Transactions**: Critical for financial data integrity
- **PostgreSQL Compatible**: Standard SQL, easy migration
- **Horizontal Scalability**: Add nodes without downtime
- **Multi-Region**: Data locality for compliance (GDPR, etc.)
- **Automatic Replication**: Built-in fault tolerance

**Why NOT Traditional Databases?**
- **MySQL/PostgreSQL**: Single-node bottleneck, complex replication
- **MongoDB**: No ACID transactions, eventual consistency issues
- **DynamoDB**: Vendor lock-in, limited query capabilities

**Our Implementation**:
```python
# database_client.py - SSL/TLS connection (NOT custom WebSocket)
conn_params = {
    'host': 'claims-demo-15395.jxf.gcp-us-east1.cockroachlabs.cloud',
    'port': 26257,
    'database': 'defaultdb',
    'user': '<username>',
    'password': '<password>',
    'sslmode': 'verify-full',  # SSL/TLS encryption
    'options': '--cluster=claims-demo-15395'  # CockroachDB Serverless
}

conn = psycopg2.connect(**conn_params)
```

**Schema Design**:
```sql
CREATE TABLE claims (
    claim_id UUID PRIMARY KEY,
    claim_number VARCHAR(50) UNIQUE,
    policy_number VARCHAR(50),
    claimant_name VARCHAR(255),
    claim_amount DECIMAL(12,2),
    risk_score INTEGER,
    status VARCHAR(50),
    description TEXT,
    description_embedding VECTOR(384),  -- pgvector!
    created_at TIMESTAMP,
    INDEX idx_risk_score (risk_score),
    INDEX idx_status (status),
    INDEX idx_policy (policy_number)
);
```

### 3. pgvector - Semantic Search with Vector Embeddings

**Why Vector Embeddings?**
- **Semantic Understanding**: "car accident" matches "vehicle collision"
- **Fraud Detection**: Find similar suspicious claim patterns
- **Beyond Keywords**: Traditional search misses semantic relationships
- **ML-Powered**: Leverages transformer models for understanding

**Why pgvector?**
- **Native PostgreSQL**: No separate vector database needed
- **ACID Compliance**: Vectors + transactional data together
- **Cost-Effective**: One database instead of two
- **Mature Ecosystem**: PostgreSQL tools, backups, monitoring

**Why NOT Alternatives?**
- **Pinecone/Weaviate**: Separate service, additional cost, complexity
- **Elasticsearch**: Not designed for vector similarity
- **Redis**: In-memory only, no ACID guarantees

**Our Vector Implementation**:
```python
# embeddings_client.py - Generate and search embeddings
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')
embedding = model.encode(claim_description)  # 384 dimensions

# Semantic similarity search with cosine distance
query = """
    SELECT claim_number, description, 
           1 - (description_embedding <=> %s) as similarity
    FROM claims
    WHERE 1 - (description_embedding <=> %s) > 0.7
    ORDER BY description_embedding <=> %s
    LIMIT 10
"""
```

**HNSW Index for Performance**:
```sql
CREATE INDEX ON claims 
USING hnsw (description_embedding vector_cosine_ops);
-- 10-50ms search time vs. 1000ms+ without index
```

### 4. IBM Watsonx.ai LLM - Conversational Intelligence

**Why LLM Integration?**
- **Natural Language**: Users ask questions naturally, not SQL queries
- **Context Awareness**: Understands follow-up questions
- **Explanations**: Provides reasoning, not just data
- **Intent Detection**: Automatically routes to correct handlers
- **Adaptive**: Learns from conversation patterns

**Why Watsonx.ai?**
- **Enterprise-Grade**: IBM's production-ready LLM platform
- **Data Privacy**: On-premises deployment option
- **Compliance**: Meets regulatory requirements
- **Integration**: Native IBM Cloud integration
- **Support**: Enterprise SLA and support

**Why NOT Alternatives?**
- **OpenAI GPT**: Data privacy concerns, API dependency
- **Local LLMs (Ollama)**: Resource-intensive, lower quality
- **Pattern Matching**: Rigid, no context, poor UX

**Our LLM Architecture**:
```python
# watsonx_client.py - LLM integration
from ibm_watsonx_ai.foundation_models import Model

class WatsonxClient:
    def __init__(self):
        self.model = Model(
            model_id="meta-llama/llama-3-3-70b-instruct",
            credentials={"apikey": "<API_KEY>", "url": "<URL>"},
            project_id="<PROJECT_ID>"
        )
    
    def generate_response(self, prompt, conversation_history):
        # Generate conversational response with context
        return self.model.generate_text(prompt)
```

**Hybrid Approach** (LLM + Pattern Fallback):
```python
# app.py - Graceful degradation
class AdjusterAgent:
    def __init__(self):
        try:
            self.watsonx_client = get_watsonx_client()
            self.use_llm = True  # Primary mode
        except Exception:
            self.watsonx_client = None
            self.use_llm = False  # Fallback to patterns
    
    async def process_query(self, user_message):
        if self.use_llm:
            # LLM-powered conversational AI
            return await self._process_with_llm(user_message)
        else:
            # Pattern-based fallback
            return await self._process_with_patterns(user_message)
```

**Conversational Memory** (6 messages):
```python
# Maintains context across conversation
self.conversation_history = [
    {"role": "user", "content": "Show me claim #123"},
    {"role": "assistant", "content": "[claim details]"},
    {"role": "user", "content": "What about the policyholder?"},
    # LLM understands "the policyholder" refers to claim #123
]
```

### 5. Chainlit - Web-Based Chat Interface

**Why Chainlit?**
- **Built-in WebSocket**: Handles real-time communication internally
- **Python-Native**: Seamless integration with our Python services
- **Async Support**: Non-blocking I/O for better performance
- **Session Management**: Built-in user session handling
- **Markdown Support**: Rich formatting for responses

**What Chainlit Provides (We Don't Implement)**:
- ✅ WebSocket server (Chainlit handles this internally)
- ✅ Session management (automatic)
- ✅ Message routing (built-in)
- ✅ UI rendering (provided by framework)

**What We Implement**:
```python
# app.py - Our application logic only
@cl.on_chat_start
async def start():
    # Initialize agent for this session
    agent = AdjusterAgent()
    cl.user_session.set("agent", agent)

@cl.on_message
async def main(message: cl.Message):
    # Process user message
    agent = cl.user_session.get("agent")
    response = await agent.process_query(message.content)
    await cl.Message(content=response).send()  # Chainlit handles WS
```

## Complete Data Flow

### Scenario 1: New Claim Submission → Auto-Approval

```
1. User submits claim → Kafka (claims.ingest)
   ├─ Event: {claim_id, amount: $1500, description: "minor fender bender"}
   
2. Claims Processor consumes event
   ├─ Verify policy in CockroachDB (SSL/TLS connection)
   ├─ Generate embedding for description
   ├─ Calculate risk score: 15
   ├─ AI Logic Gate: amount < $2000 AND risk < 20
   └─ Decision: AUTO_APPROVED
   
3. Produce to Kafka (claims.approved) with SASL_SSL
   ├─ Update CockroachDB: status = 'APPROVED'
   └─ Store embedding in pgvector
   
4. Adjuster Agent monitors Kafka (background thread)
   ├─ Receives approval notification
   └─ Sends alert via Chainlit (Chainlit's WebSocket, not ours)
```

### Scenario 2: Adjuster Searches for Similar Claims

```
1. Adjuster asks: "Find fraud patterns like staged accidents"
   
2. LLM processes query (Watsonx.ai)
   ├─ Extract intent: fraud_detection
   ├─ Extract entities: "staged accidents"
   └─ Route to fraud detection handler
   
3. Generate embedding
   ├─ Text: "staged accidents"
   └─ Vector: [0.23, -0.45, 0.67, ...] (384 dims)
   
4. Vector similarity search (pgvector + HNSW)
   ├─ Query: SELECT * WHERE similarity > 0.65 AND risk_score > 70
   ├─ HNSW index: ~20ms search time
   └─ Results: 5 similar high-risk claims
   
5. LLM generates response
   ├─ Context: Database results + conversation history
   ├─ Generate: Explanation of fraud patterns
   └─ Format: Markdown with insights
   
6. Display to adjuster (Chainlit renders via WebSocket)
   └─ "⚠️ Found 5 similar high-risk claims..."
```

### Scenario 3: Conversational Follow-up

```
1. User: "Show me claim #123"
   └─ LLM: [Displays claim details]

2. User: "What about the policyholder?"
   ├─ LLM understands context (claim #123)
   ├─ Queries database for policyholder
   └─ Response: "The policyholder is John Doe..."

3. User: "Find similar claims"
   ├─ LLM knows to search similar to claim #123
   ├─ Uses claim #123's embedding
   └─ Returns: "Found 3 similar claims..."

4. User: "Why are these risky?"
   ├─ LLM analyzes risk scores and patterns
   └─ Explains: "These claims are flagged because..."
```

## Security Implementation

### Data in Transit (What We Actually Implement)

**Kafka - SASL_SSL Configuration**:
```python
# kafka_monitor.py
consumer_config = {
    'security.protocol': 'SASL_SSL',  # TLS 1.2+ encryption
    'sasl.mechanism': 'PLAIN',
    'sasl.username': '<API_KEY>',
    'sasl.password': '<API_SECRET>'
}
```

**CockroachDB - SSL/TLS Configuration**:
```python
# database_client.py
conn_params = {
    'sslmode': 'verify-full',  # Verify server certificate
    'host': 'claims-demo-15395.jxf.gcp-us-east1.cockroachlabs.cloud',
    'port': 26257
}
```

**Watsonx.ai - HTTPS**:
```python
# watsonx_client.py
credentials = {
    "url": "https://ca-tor.ml.cloud.ibm.com",  # HTTPS only
    "apikey": "<API_KEY>"
}
```

**Chainlit - Built-in WebSocket Security**:
- Chainlit framework handles WebSocket security internally
- We don't implement custom WebSocket code
- Session-based authentication (can be extended)

### Data at Rest
- **CockroachDB**: Encryption at rest (AES-256) - managed by CockroachDB Cloud
- **Kafka**: Encrypted storage - managed by Confluent Cloud
- **Embeddings**: Encrypted with claim data in CockroachDB

### Access Control
- **Kafka**: Topic-level ACLs (configured in Confluent Cloud)
- **CockroachDB**: Role-based access control (RBAC)
- **Watsonx.ai**: Project-level isolation
- **Chainlit**: Session isolation (built-in)

## What We DON'T Implement (Managed by Services)

### ❌ Custom WebSocket Server
- **Chainlit provides this**: Built-in WebSocket handling
- **We use**: `@cl.on_message` decorators, Chainlit handles WS protocol

### ❌ Custom SSL/TLS Implementation
- **We configure**: Connection parameters (`sslmode`, `security.protocol`)
- **Services handle**: Certificate validation, encryption, handshakes

### ❌ Custom Authentication Server
- **We use**: API keys, credentials in environment variables
- **Services handle**: OAuth, token validation, session management

### ❌ Load Balancing
- **Confluent Cloud**: Handles Kafka broker load balancing
- **CockroachDB Cloud**: Handles SQL query routing
- **Chainlit**: Can be deployed behind NGINX/ALB

## Performance Characteristics

### End-to-End Latency

| Operation | Latency | Implementation |
|-----------|---------|----------------|
| Kafka produce | 5-10ms | SASL_SSL overhead |
| Kafka consume | 10-50ms | Poll interval (1s) |
| Database query | 10-100ms | SSL connection + index lookup |
| Vector search | 20-50ms | HNSW traversal |
| Embedding generation | 50-100ms | Model inference (CPU) |
| LLM response | 2-5s | Model size (70B params) |
| **Total (with LLM)** | **2-6s** | LLM generation dominates |
| **Total (pattern)** | **100-300ms** | Database + vector only |

### Scalability

**Horizontal Scaling**:
- **Kafka**: Add partitions (10K+ msgs/sec per partition)
- **CockroachDB**: Add nodes (linear scaling)
- **Claims Processor**: Add consumer instances (consumer group)
- **Adjuster Agent**: Add Chainlit instances (stateless)

**Vertical Scaling**:
- **LLM**: Larger models (70B → 405B) for better quality
- **Vector Search**: More dimensions (384 → 768) for accuracy
- **Database**: More RAM for caching

## Technology Stack Details

### Backend Services
```python
# Claims Processor
confluent-kafka==2.3.0      # Kafka client with SASL_SSL
psycopg2-binary==2.9.9      # PostgreSQL/CockroachDB driver
sentence-transformers==2.2.2 # Embedding generation
structlog==23.1.0           # Structured logging

# Adjuster Agent
chainlit==1.0.0             # Chat interface (includes WebSocket)
ibm-watsonx-ai>=0.2.0       # LLM integration
pgvector==0.2.4             # Vector operations
asyncio                     # Async processing (built-in)
```

### Infrastructure
```yaml
Confluent Cloud:
  Bootstrap: pkc-4rn2p.canadacentral.azure.confluent.cloud:9092
  Auth: SASL_SSL (PLAIN mechanism)
  Topics: 4 (ingest, approved, escalated, under_review)
  Encryption: TLS 1.2+
  
CockroachDB Cloud:
  Host: claims-demo-15395.jxf.gcp-us-east1.cockroachlabs.cloud
  Port: 26257
  SSL: verify-full (TLS 1.2+)
  Extensions: pgvector
  Cluster: Serverless (--cluster option)
  
IBM Watsonx.ai:
  URL: https://ca-tor.ml.cloud.ibm.com
  Model: meta-llama/llama-3-3-70b-instruct
  Project: 0ad45a34-630f-4b64-9a97-6970bfacfb89
  Auth: API key
```

## Deployment Architecture

### Development
```bash
# Local services
- Chainlit: localhost:8000 (Chainlit's built-in server)
- Claims Processor: Background service (threading)
- Kafka: Confluent Cloud (SASL_SSL)
- CockroachDB: Cloud (SSL/TLS)
- Watsonx.ai: Cloud (HTTPS)
```

### Production
```yaml
Kubernetes Deployment:
  - Claims Processor: 3 replicas (consumer group)
  - Adjuster Agent: 5 replicas (load balanced)
  - Ingress: NGINX with TLS termination
  - Monitoring: Prometheus + Grafana
  - Logging: ELK stack
  - Secrets: Kubernetes secrets / Vault
```

## Monitoring and Observability

### Logging (structlog)
```json
{
  "timestamp": "2026-05-03T07:30:00Z",
  "level": "INFO",
  "service": "claims-processor",
  "event": "claim_processed",
  "claim_id": "CLM-2026-000123",
  "decision": "AUTO_APPROVED",
  "risk_score": 15,
  "processing_time_ms": 45
}
```

### Metrics (Future)
- Kafka consumer lag
- Database query latency (p50, p95, p99)
- Vector search performance
- LLM response time
- Error rates by service

## Cost Analysis

### Monthly Costs (Estimated)

| Service | Cost | Justification |
|---------|------|---------------|
| Confluent Cloud | $200 | Event streaming, 4 topics, SASL_SSL |
| CockroachDB Cloud | $300 | Distributed SQL + vectors + SSL |
| IBM Watsonx.ai | $500 | LLM API calls (70B model) |
| Compute (K8s) | $400 | 8 replicas, load balancing |
| **Total** | **$1,400/mo** | **Enterprise-grade platform** |

**Cost Optimization**:
- Use smaller LLM model (mistral-small: $200/mo)
- Cache frequent queries (Redis: +$50/mo, -$200 LLM)
- Pattern fallback reduces LLM calls by 30%

## Why This Stack Beats Alternatives

### Alternative 1: Monolithic + MySQL + Keyword Search
❌ **Problems**:
- Single point of failure
- No real-time processing
- Poor semantic search
- No conversational AI
- Difficult to scale

### Alternative 2: Microservices + MongoDB + Elasticsearch
❌ **Problems**:
- No ACID transactions (data inconsistency)
- Elasticsearch not designed for vectors
- Complex operational overhead
- Higher costs (3 databases)

### Alternative 3: Serverless + DynamoDB + OpenAI
❌ **Problems**:
- Vendor lock-in (AWS + OpenAI)
- Data privacy concerns (OpenAI)
- Cold start latency
- Limited query capabilities (DynamoDB)
- Higher API costs

### Our Stack ✅
- **Event-driven**: Real-time, scalable, decoupled
- **Distributed SQL**: ACID + scalability + vectors
- **Semantic search**: Built-in, cost-effective
- **Conversational AI**: Enterprise-grade, private
- **Hybrid approach**: Graceful degradation
- **Cloud-native**: Managed services, global scale
- **Security**: SASL_SSL, SSL/TLS, HTTPS (configured, not custom)
- **Simple**: No custom WebSocket, no custom SSL implementation

## Conclusion

This architecture represents a modern, AI-powered insurance claims platform that combines:

1. **Real-time Processing** (Kafka with SASL_SSL) - Immediate claim handling
2. **Distributed SQL** (CockroachDB with SSL/TLS) - Scalable, ACID-compliant storage
3. **Semantic Search** (pgvector) - Intelligent fraud detection
4. **Conversational AI** (Watsonx.ai) - Natural language interface
5. **Simple Integration** (Chainlit) - Built-in WebSocket, no custom implementation

Each technology was chosen for specific reasons:
- **Confluent Cloud**: Best-in-class event streaming with managed SASL_SSL
- **CockroachDB**: PostgreSQL-compatible distributed SQL with SSL/TLS
- **pgvector**: Cost-effective vector search within SQL database
- **Watsonx.ai**: Enterprise LLM with data privacy
- **Chainlit**: Python-native chat framework with built-in WebSocket

**What We Implement**:
- ✅ Business logic (claims processing, AI logic gate)
- ✅ Database queries (SQL with SSL connection params)
- ✅ Kafka integration (consumer/producer with SASL_SSL config)
- ✅ LLM integration (API calls to Watsonx.ai)
- ✅ Vector embeddings (generation and similarity search)
- ✅ Background monitoring (threading, not WebSocket)

**What Services Provide** (We Configure, Not Implement):
- ✅ WebSocket server (Chainlit framework)
- ✅ SSL/TLS encryption (Kafka, CockroachDB, Watsonx.ai)
- ✅ Authentication (API keys, SASL, certificates)
- ✅ Load balancing (Confluent, CockroachDB)
- ✅ Session management (Chainlit)

The result is a platform that is:
- ✅ **Scalable**: Handles millions of claims
- ✅ **Intelligent**: AI-powered decision making
- ✅ **Real-time**: Immediate processing and notifications
- ✅ **Conversational**: Natural language interface
- ✅ **Reliable**: Distributed, fault-tolerant architecture
- ✅ **Secure**: Managed encryption and authentication
- ✅ **Simple**: Leverages managed services, minimal custom code
- ✅ **Cost-effective**: Managed services, pay-per-use

---

**Built with ❤️ using Confluent Cloud, CockroachDB, pgvector, IBM Watsonx.ai, and Chainlit**