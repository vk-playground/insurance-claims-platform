-- Migration: Add Vector Embeddings Support to Claims Table
-- Date: 2026-05-03
-- Description: Adds pgvector-compatible VECTOR column for semantic search

-- ============================================================================
-- STEP 1: Add vector column to claims table
-- ============================================================================
-- CockroachDB supports VECTOR type for pgvector compatibility
-- Using 384 dimensions for sentence-transformers/all-MiniLM-L6-v2 model

ALTER TABLE claims ADD COLUMN IF NOT EXISTS description_embedding VECTOR(384);

-- ============================================================================
-- STEP 2: Create vector index for similarity search
-- ============================================================================
-- Using HNSW (Hierarchical Navigable Small World) index for fast approximate nearest neighbor search
-- This enables efficient semantic similarity queries

CREATE INDEX IF NOT EXISTS idx_claims_description_embedding 
ON claims USING HNSW (description_embedding vector_cosine_ops);

-- ============================================================================
-- STEP 3: Add metadata columns for embedding tracking
-- ============================================================================

ALTER TABLE claims ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(100) DEFAULT 'all-MiniLM-L6-v2';
ALTER TABLE claims ADD COLUMN IF NOT EXISTS embedding_generated_at TIMESTAMP;

-- ============================================================================
-- STEP 4: Create helper function for similarity search
-- ============================================================================

-- Function to find similar claims based on description embedding
-- Returns claims ordered by cosine similarity (most similar first)
CREATE OR REPLACE FUNCTION find_similar_claims(
    query_embedding VECTOR(384),
    similarity_threshold FLOAT DEFAULT 0.7,
    max_results INT DEFAULT 10
)
RETURNS TABLE (
    claim_id UUID,
    claim_number VARCHAR(50),
    description TEXT,
    similarity_score FLOAT,
    claim_amount DECIMAL(15, 2),
    risk_score DECIMAL(5, 2),
    status VARCHAR(50),
    created_at TIMESTAMP
)
LANGUAGE SQL
AS $$
    SELECT 
        c.claim_id,
        c.claim_number,
        c.description,
        1 - (c.description_embedding <=> query_embedding) AS similarity_score,
        c.claim_amount,
        c.risk_score,
        c.status,
        c.created_at
    FROM claims c
    WHERE c.description_embedding IS NOT NULL
        AND 1 - (c.description_embedding <=> query_embedding) >= similarity_threshold
    ORDER BY c.description_embedding <=> query_embedding
    LIMIT max_results;
$$;

-- ============================================================================
-- STEP 5: Add comments for documentation
-- ============================================================================

COMMENT ON COLUMN claims.description_embedding IS 'Vector embedding of claim description for semantic similarity search (384 dimensions)';
COMMENT ON COLUMN claims.embedding_model IS 'Name of the sentence-transformer model used to generate the embedding';
COMMENT ON COLUMN claims.embedding_generated_at IS 'Timestamp when the embedding was generated';

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify vector column was added
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'claims' 
AND column_name IN ('description_embedding', 'embedding_model', 'embedding_generated_at');

-- Verify index was created
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'claims' 
AND indexname = 'idx_claims_description_embedding';

-- Made with Bob