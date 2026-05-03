"""Embeddings client for semantic similarity search."""
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any
import structlog
from sentence_transformers import SentenceTransformer
from config import Config

logger = structlog.get_logger()


class EmbeddingsClient:
    """Client for semantic similarity search using embeddings."""
    
    def __init__(self):
        """Initialize embeddings client."""
        self.config = Config()
        self.conn = None
        self.model = None
        self._connect()
        self._load_model()
    
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
            logger.info("embeddings_database_connected")
        except Exception as e:
            logger.error("embeddings_database_connection_failed", error=str(e))
            raise
    
    def _load_model(self):
        """Load sentence transformer model."""
        try:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("embeddings_model_loaded", model="all-MiniLM-L6-v2")
        except Exception as e:
            logger.error("embeddings_model_load_failed", error=str(e))
            raise
    
    def _ensure_connection(self):
        """Ensure database connection is active."""
        if self.conn is None or self.conn.closed:
            self._connect()
    
    async def find_similar_claims(
        self,
        query_text: str,
        similarity_threshold: float = 0.7,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find claims similar to the query text using semantic search.
        
        Args:
            query_text: Text to search for similar claims
            similarity_threshold: Minimum similarity score (0-1)
            max_results: Maximum number of results
            
        Returns:
            List of similar claims with similarity scores
        """
        self._ensure_connection()
        
        # Generate embedding for query
        query_embedding = self.model.encode(query_text).tolist()
        
        # Search for similar claims using cosine similarity
        query = """
            SELECT 
                claim_id,
                claim_number,
                policy_number,
                claimant_name,
                claim_type,
                claim_amount,
                description,
                status,
                risk_score,
                created_at,
                1 - (description_embedding <=> %s::vector) as similarity_score
            FROM claims
            WHERE description_embedding IS NOT NULL
                AND 1 - (description_embedding <=> %s::vector) >= %s
            ORDER BY description_embedding <=> %s::vector
            LIMIT %s
        """
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Convert embedding to string format for pgvector
                embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
                
                cursor.execute(
                    query,
                    (embedding_str, embedding_str, similarity_threshold, embedding_str, max_results)
                )
                results = cursor.fetchall()
                
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error("find_similar_claims_failed", error=str(e))
            raise
    
    async def find_fraud_patterns(
        self,
        query_text: str,
        min_risk_score: int = 70,
        similarity_threshold: float = 0.65,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find high-risk claims similar to the query text.
        
        Args:
            query_text: Text to search for fraud patterns
            min_risk_score: Minimum risk score to consider
            similarity_threshold: Minimum similarity score
            max_results: Maximum number of results
            
        Returns:
            List of high-risk similar claims
        """
        self._ensure_connection()
        
        # Generate embedding for query
        query_embedding = self.model.encode(query_text).tolist()
        
        query = """
            SELECT 
                claim_id,
                claim_number,
                policy_number,
                claimant_name,
                claim_type,
                claim_amount,
                description,
                status,
                risk_score,
                created_at,
                1 - (description_embedding <=> %s::vector) as similarity_score
            FROM claims
            WHERE description_embedding IS NOT NULL
                AND risk_score >= %s
                AND 1 - (description_embedding <=> %s::vector) >= %s
            ORDER BY risk_score DESC, description_embedding <=> %s::vector
            LIMIT %s
        """
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
                
                cursor.execute(
                    query,
                    (embedding_str, min_risk_score, embedding_str, similarity_threshold, embedding_str, max_results)
                )
                results = cursor.fetchall()
                
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error("find_fraud_patterns_failed", error=str(e))
            raise
    
    def close(self):
        """Close database connection."""
        if self.conn and not self.conn.closed:
            self.conn.close()
            logger.info("embeddings_connection_closed")

# Made with Bob
