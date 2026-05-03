"""Vector embeddings module for semantic similarity search on claims."""
import numpy as np
from typing import List, Optional, Dict, Any
from sentence_transformers import SentenceTransformer
import structlog
from datetime import datetime

logger = structlog.get_logger()


class EmbeddingGenerator:
    """Generates vector embeddings for claim descriptions using sentence-transformers."""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize the embedding generator.
        
        Args:
            model_name: Name of the sentence-transformer model to use.
                       Default is 'all-MiniLM-L6-v2' (384 dimensions, fast and efficient)
        
        Available models:
            - all-MiniLM-L6-v2: 384 dimensions, 80MB, fast (recommended)
            - all-mpnet-base-v2: 768 dimensions, 420MB, more accurate
            - paraphrase-MiniLM-L6-v2: 384 dimensions, good for paraphrasing
        """
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the sentence-transformer model."""
        try:
            logger.info("loading_embedding_model", model=self.model_name)
            self.model = SentenceTransformer(self.model_name)
            logger.info(
                "embedding_model_loaded",
                model=self.model_name,
                dimensions=self.model.get_sentence_embedding_dimension()
            )
        except Exception as e:
            logger.error("embedding_model_load_failed", error=str(e), model=self.model_name)
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate a vector embedding for the given text.
        
        Args:
            text: The text to embed (e.g., claim description)
            
        Returns:
            List of floats representing the embedding vector
            
        Example:
            >>> generator = EmbeddingGenerator()
            >>> embedding = generator.generate_embedding("Car accident on highway")
            >>> len(embedding)
            384
        """
        if not text or not text.strip():
            logger.warning("empty_text_for_embedding")
            return [0.0] * self.model.get_sentence_embedding_dimension()
        
        try:
            # Generate embedding
            embedding = self.model.encode(text, convert_to_numpy=True)
            
            # Convert to list for JSON serialization
            embedding_list = embedding.tolist()
            
            logger.debug(
                "embedding_generated",
                text_length=len(text),
                embedding_dimensions=len(embedding_list)
            )
            
            return embedding_list
            
        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e), text_preview=text[:100])
            raise
    
    def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch (more efficient).
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
            
        Example:
            >>> generator = EmbeddingGenerator()
            >>> texts = ["Car accident", "Water damage", "Medical claim"]
            >>> embeddings = generator.generate_batch_embeddings(texts)
            >>> len(embeddings)
            3
        """
        if not texts:
            return []
        
        try:
            # Filter out empty texts
            valid_texts = [t if t and t.strip() else " " for t in texts]
            
            # Generate embeddings in batch
            embeddings = self.model.encode(valid_texts, convert_to_numpy=True, show_progress_bar=False)
            
            # Convert to list of lists
            embeddings_list = [emb.tolist() for emb in embeddings]
            
            logger.info(
                "batch_embeddings_generated",
                count=len(embeddings_list),
                dimensions=len(embeddings_list[0]) if embeddings_list else 0
            )
            
            return embeddings_list
            
        except Exception as e:
            logger.error("batch_embedding_generation_failed", error=str(e), count=len(texts))
            raise
    
    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score between 0 and 1 (1 = identical, 0 = completely different)
            
        Example:
            >>> generator = EmbeddingGenerator()
            >>> emb1 = generator.generate_embedding("Car accident on highway")
            >>> emb2 = generator.generate_embedding("Vehicle collision on freeway")
            >>> similarity = generator.compute_similarity(emb1, emb2)
            >>> similarity > 0.7  # Should be high similarity
            True
        """
        try:
            # Convert to numpy arrays
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Compute cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            
            # Ensure result is between 0 and 1
            similarity = max(0.0, min(1.0, float(similarity)))
            
            return similarity
            
        except Exception as e:
            logger.error("similarity_computation_failed", error=str(e))
            return 0.0


class ClaimEmbeddingManager:
    """Manages embedding generation and storage for claims in CockroachDB."""
    
    def __init__(self, db_manager, embedding_generator: Optional[EmbeddingGenerator] = None):
        """
        Initialize the claim embedding manager.
        
        Args:
            db_manager: Database manager instance for CockroachDB operations
            embedding_generator: Optional custom embedding generator (uses default if None)
        """
        self.db = db_manager
        self.generator = embedding_generator or EmbeddingGenerator()
    
    def generate_and_store_embedding(self, claim_number: str, description: str) -> bool:
        """
        Generate embedding for a claim description and store it in the database.
        
        Args:
            claim_number: The claim number to update
            description: The claim description text
            
        Returns:
            True if successful, False otherwise
            
        Example:
            >>> manager = ClaimEmbeddingManager(db_manager)
            >>> success = manager.generate_and_store_embedding(
            ...     "CLM-2026-001",
            ...     "Minor collision at intersection, rear-end accident"
            ... )
        """
        try:
            # Generate embedding
            embedding = self.generator.generate_embedding(description)
            
            # Convert to pgvector format (array string)
            embedding_str = '[' + ','.join(map(str, embedding)) + ']'
            
            # Update database
            with self.db.conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE claims 
                    SET 
                        description_embedding = %s::VECTOR(384),
                        embedding_model = %s,
                        embedding_generated_at = NOW(),
                        updated_at = NOW()
                    WHERE claim_number = %s
                    """,
                    (embedding_str, self.generator.model_name, claim_number)
                )
                self.db.conn.commit()
            
            logger.info(
                "embedding_stored",
                claim_number=claim_number,
                model=self.generator.model_name,
                dimensions=len(embedding)
            )
            
            return True
            
        except Exception as e:
            self.db.conn.rollback()
            logger.error(
                "embedding_storage_failed",
                error=str(e),
                claim_number=claim_number
            )
            return False
    
    def find_similar_claims(
        self,
        query_text: str,
        similarity_threshold: float = 0.7,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find claims with similar descriptions using semantic search.
        
        Args:
            query_text: The text to search for (e.g., "car accident on highway")
            similarity_threshold: Minimum similarity score (0-1) to include results
            max_results: Maximum number of results to return
            
        Returns:
            List of similar claims with similarity scores
            
        Example:
            >>> manager = ClaimEmbeddingManager(db_manager)
            >>> similar = manager.find_similar_claims(
            ...     "Vehicle collision on freeway",
            ...     similarity_threshold=0.7,
            ...     max_results=5
            ... )
            >>> for claim in similar:
            ...     print(f"{claim['claim_number']}: {claim['similarity_score']:.2f}")
        """
        try:
            # Generate embedding for query
            query_embedding = self.generator.generate_embedding(query_text)
            query_embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
            
            # Search for similar claims
            with self.db.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM find_similar_claims(
                        %s::VECTOR(384),
                        %s,
                        %s
                    )
                    """,
                    (query_embedding_str, similarity_threshold, max_results)
                )
                results = cursor.fetchall()
            
            # Convert to list of dicts
            similar_claims = []
            for row in results:
                similar_claims.append({
                    'claim_id': str(row['claim_id']),
                    'claim_number': row['claim_number'],
                    'description': row['description'],
                    'similarity_score': float(row['similarity_score']),
                    'claim_amount': float(row['claim_amount']),
                    'risk_score': float(row['risk_score']),
                    'status': row['status'],
                    'created_at': row['created_at'].isoformat()
                })
            
            logger.info(
                "similar_claims_found",
                query_preview=query_text[:50],
                results_count=len(similar_claims),
                threshold=similarity_threshold
            )
            
            return similar_claims
            
        except Exception as e:
            logger.error(
                "similar_claims_search_failed",
                error=str(e),
                query_preview=query_text[:50]
            )
            return []
    
    def batch_generate_embeddings_for_existing_claims(self, batch_size: int = 100) -> Dict[str, int]:
        """
        Generate embeddings for all existing claims that don't have embeddings yet.
        Now let me create the Python module for generating embeddings:

<write_to_file>
<path>insurance-claims-platform/services/claims-processor/embeddings.py</path>
<content>
"""Vector embeddings module for semantic similarity search on claims."""
import numpy as np
from typing import List, Optional, Dict, Any
from sentence_transformers import SentenceTransformer
import structlog
from datetime import datetime

logger = structlog.get_logger()


class EmbeddingGenerator:
    """Generates vector embeddings for claim descriptions using sentence-transformers."""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize the embedding generator.
        
        Args:
            model_name: Name of the sentence-transformer model to use.
                       Default is 'all-MiniLM-L6-v2' (384 dimensions, fast and efficient)
        
        Available models:
            - all-MiniLM-L6-v2: 384 dimensions, 80MB, fast (recommended)
            - all-mpnet-base-v2: 768 dimensions, 420MB, more accurate
            - paraphrase-MiniLM-L6-v2: 384 dimensions, good for paraphrasing
        """
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the sentence-transformer model."""
        try:
            logger.info("loading_embedding_model", model=self.model_name)
            self.model = SentenceTransformer(self.model_name)
            logger.info(
                "embedding_model_loaded",
                model=self.model_name,
                dimensions=self.model.get_sentence_embedding_dimension()
            )
        except Exception as e:
            logger.error("embedding_model_load_failed", error=str(e), model=self.model_name)
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate a vector embedding for the given text.
        
        Args:
            text: The text to embed (e.g., claim description)
            
        Returns:
            List of floats representing the embedding vector
            
        Example:
            >>> generator = EmbeddingGenerator()
            >>> embedding = generator.generate_embedding("Car accident on highway")
            >>> len(embedding)
            384
        """
        if not text or not text.strip():
            logger.warning("empty_text_for_embedding")
            return [0.0] * self.model.get_sentence_embedding_dimension()
        
        try:
            # Generate embedding
            embedding = self.model.encode(text, convert_to_numpy=True)
            
            # Convert to list for JSON serialization
            embedding_list = embedding.tolist()
            
            logger.debug(
                "embedding_generated",
                text_length=len(text),
                embedding_dimensions=len(embedding_list)
            )
            
            return embedding_list
            
        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e), text_preview=text[:100])
            raise
    
    def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch (more efficient).
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
            
        Example:
            >>> generator = EmbeddingGenerator()
            >>> texts = ["Car accident", "Water damage", "Medical claim"]
            >>> embeddings = generator.generate_batch_embeddings(texts)
            >>> len(embeddings)
            3
        """
        if not texts:
            return []
        
        try:
            # Filter out empty texts
            valid_texts = [t if t and t.strip() else " " for t in texts]
            
            # Generate embeddings in batch
            embeddings = self.model.encode(valid_texts, convert_to_numpy=True, show_progress_bar=False)
            
            # Convert to list of lists
            embeddings_list = [emb.tolist() for emb in embeddings]
            
            logger.info(
                "batch_embeddings_generated",
                count=len(embeddings_list),
                dimensions=len(embeddings_list[0]) if embeddings_list else 0
            )
            
            return embeddings_list
            
        except Exception as e:
            logger.error("batch_embedding_generation_failed", error=str(e), count=len(texts))
            raise
    
    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score between 0 and 1 (1 = identical, 0 = completely different)
            
        Example:
            >>> generator = EmbeddingGenerator()
            >>> emb1 = generator.generate_embedding("Car accident on highway")
            >>> emb2 = generator.generate_embedding("Vehicle collision on freeway")
            >>> similarity = generator.compute_similarity(emb1, emb2)
            >>> similarity > 0.7  # Should be high similarity
            True
        """
        try:
            # Convert to numpy arrays
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Compute cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            
            # Ensure result is between 0 and 1
            similarity = max(0.0, min(1.0, float(similarity)))
            
            return similarity
            
        except Exception as e:
            logger.error("similarity_computation_failed", error=str(e))
            return 0.0


class ClaimEmbeddingManager:
    """Manages embedding generation and storage for claims in CockroachDB."""
    
    def __init__(self, db_manager, embedding_generator: Optional[EmbeddingGenerator] = None):
        """
        Initialize the claim embedding manager.
        
        Args:
            db_manager: Database manager instance for CockroachDB operations
            embedding_generator: Optional custom embedding generator (uses default if None)
        """
        self.db = db_manager
        self.generator = embedding_generator or EmbeddingGenerator()
    
    def generate_and_store_embedding(self, claim_number: str, description: str) -> bool:
        """
        Generate embedding for a claim description and store it in the database.
        
        Args:
            claim_number: The claim number to update
            description: The claim description text
            
        Returns:
            True if successful, False otherwise
            
        Example:
            >>> manager = ClaimEmbeddingManager(db_manager)
            >>> success = manager.generate_and_store_embedding(
            ...     "CLM-2026-001",
            ...     "Minor collision at intersection, rear-end accident"
            ... )
        """
        try:
            # Generate embedding
            embedding = self.generator.generate_embedding(description)
            
            # Convert to pgvector format (array string)
            embedding_str = '[' + ','.join(map(str, embedding)) + ']'
            
            # Update database
            with self.db.conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE claims 
                    SET 
                        description_embedding = %s::VECTOR(384),
                        embedding_model = %s,
                        embedding_generated_at = NOW(),
                        updated_at = NOW()
                    WHERE claim_number = %s
                    """,
                    (embedding_str, self.generator.model_name, claim_number)
                )
                self.db.conn.commit()
            
            logger.info(
                "embedding_stored",
                claim_number=claim_number,
                model=self.generator.model_name,
                dimensions=len(embedding)
            )
            
            return True
            
        except Exception as e:
            self.db.conn.rollback()
            logger.error(
                "embedding_storage_failed",
                error=str(e),
                claim_number=claim_number
            )
            return False
    
    def find_similar_claims(
        self,
        query_text: str,
        similarity_threshold: float = 0.7,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find claims with similar descriptions using semantic search.
        
        Args:
            query_text: The text to search for (e.g., "car accident on highway")
            similarity_threshold: Minimum similarity score (0-1) to include results
            max_results: Maximum number of results to return
            
        Returns:
            List of similar claims with similarity scores
            
        Example:
            >>> manager = ClaimEmbeddingManager(db_manager)
            >>> similar = manager.find_similar_claims(
            ...     "Vehicle collision on freeway",
            ...     similarity_threshold=0.7,
            ...     max_results=5
            ... )
            >>> for claim in similar:
            ...     print(f"{claim['claim_number']}: {claim['similarity_score']:.2f}")
        """
        try:
            # Generate embedding for query
            query_embedding = self.generator.generate_embedding(query_text)
            query_embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
            
            # Search for similar claims
            with self.db.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM find_similar_claims(
                        %s::VECTOR(384),
                        %s,
                        %s
                    )
                    """,
                    (query_embedding_str, similarity_threshold, max_results)
                )
                results = cursor.fetchall()
            
            # Convert to list of dicts
            similar_claims = []
            for row in results:
                similar_claims.append({
                    'claim_id': str(row['claim_id']),
                    'claim_number': row['claim_number'],
                    'description': row['description'],
                    'similarity_score': float(row['similarity_score']),
                    'claim_amount': float(row['claim_amount']),
                    'risk_score': float(row['risk_score']),
                    'status': row['status'],
                    'created_at': row['created_at'].isoformat()
                })
            
            logger.info(
                "similar_claims_found",
                query_preview=query_text[:50],
                results_count=len(similar_claims),
                threshold=similarity_threshold
            )
            
            return similar_claims
            
        except Exception as e:
            logger.error(
                "similar_claims_search_failed",
                error=str(e),
                query_preview=query_text[:50]
            )
            return []
    
    def batch_generate_embeddings_for_existing_claims(self, batch_size: int = 100) -> Dict[str, int]:
        """
        Generate embeddings for all existing claims that don't have embeddings yet.
        
        Args:
            batch_size: Number of claims to process in each batch
            
        Returns:
            Dictionary with processing statistics
            
        Example:
            >>> manager = ClaimEmbeddingManager(db_manager)
            >>> stats = manager.batch_generate_embeddings_for_existing_claims(batch_size=50)
            >>> print(f"Processed {stats['processed']} claims")
        """
        try:
            processed = 0
            updated = 0
            skipped = 0
            
            with self.db.conn.cursor() as cursor:
                # Get claims without embeddings
                cursor.execute(
                    """
                    SELECT claim_number, description
                    FROM claims
                    WHERE description_embedding IS NULL
                    AND description IS NOT NULL
                    AND description != ''
                    LIMIT %s
                    """,
                    (batch_size,)
                )
                claims = cursor.fetchall()
                
                if not claims:
                    logger.info("no_claims_to_process_for_embeddings")
                    return {
                        'processed': 0,
                        'updated': 0,
                        'skipped': 0
                    }
                
                # Process in batches
                for claim in claims:
                    claim_number = claim['claim_number']
                    description = claim['description']
                    
                    processed += 1
                    
                    # Skip if description is empty
                    if not description or not description.strip():
                        skipped += 1
                        continue
                    
                    # Generate and store embedding
                    if self.generate_and_store_embedding(claim_number, description):
                        updated += 1
                    
            logger.info(
                "batch_embedding_processing_complete",
                processed=processed,
                updated=updated,
                skipped=skipped
            )
            
            return {
                'processed': processed,
                'updated': updated,
                'skipped': skipped
            }
            
        except Exception as e:
            logger.error("batch_embedding_processing_failed", error=str(e))
            return {
                'processed': processed,
                'updated': updated,
                'skipped': skipped,
                'error': str(e)
            }

# Made with Bob
