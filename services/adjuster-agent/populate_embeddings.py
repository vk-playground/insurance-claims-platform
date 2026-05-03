#!/usr/bin/env python3
"""
Populate Vector Embeddings for Existing Claims

This script generates embeddings for all claims that don't have them yet.
Run this after the migration to populate embeddings for existing data.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from sentence_transformers import SentenceTransformer
import structlog
from config import Config
from tqdm import tqdm

logger = structlog.get_logger()


def get_connection(config):
    """Get database connection with cluster identifier for CockroachDB Serverless."""
    # Extract cluster identifier
    cluster_id = None
    if 'cockroachlabs.cloud' in config.DB_HOST:
        cluster_id = config.DB_HOST.split('.')[0]
    
    conn_params = {
        'host': config.DB_HOST,
        'port': config.DB_PORT,
        'database': config.DB_NAME,
        'user': config.DB_USER,
        'password': config.DB_PASSWORD,
        'sslmode': config.DB_SSLMODE,
        'connect_timeout': 10
    }
    
    if cluster_id:
        conn_params['options'] = f'--cluster={cluster_id}'
    
    return psycopg2.connect(**conn_params)


def main():
    """Main function to populate embeddings."""
    print("🚀 Starting embedding population...")
    print("")
    
    # Load configuration
    config = Config()
    
    # Connect to database
    print("📊 Connecting to database...")
    try:
        conn = get_connection(config)
        print(f"✅ Connected to {config.DB_HOST}")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return 1
    
    # Load embedding model
    print("")
    print("🤖 Loading embedding model (all-MiniLM-L6-v2)...")
    print("   (This may take a minute on first run)")
    try:
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Model loaded successfully")
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        return 1
    
    # Get claims without embeddings
    print("")
    print("🔍 Finding claims without embeddings...")
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT claim_id, claim_number, description
                FROM claims
                WHERE description IS NOT NULL 
                  AND description != ''
                  AND description_embedding IS NULL
                ORDER BY created_at DESC
            """)
            claims = cursor.fetchall()
            
            if not claims:
                print("✅ All claims already have embeddings!")
                return 0
            
            print(f"📝 Found {len(claims)} claims needing embeddings")
    except Exception as e:
        print(f"❌ Query failed: {e}")
        return 1
    
    # Generate and store embeddings
    print("")
    print("⚙️  Generating embeddings...")
    success_count = 0
    error_count = 0
    
    for claim in tqdm(claims, desc="Processing claims"):
        try:
            # Generate embedding
            embedding = model.encode(claim['description'])
            embedding_list = embedding.tolist()
            embedding_str = '[' + ','.join(map(str, embedding_list)) + ']'
            
            # Update database
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE claims
                    SET description_embedding = %s::vector,
                        embedding_model = 'all-MiniLM-L6-v2',
                        embedding_generated_at = NOW()
                    WHERE claim_id = %s
                """, (embedding_str, claim['claim_id']))
                conn.commit()
            
            success_count += 1
            
        except Exception as e:
            error_count += 1
            logger.error(
                "embedding_generation_failed",
                claim_number=claim['claim_number'],
                error=str(e)
            )
    
    # Summary
    print("")
    print("=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"✅ Successfully generated: {success_count} embeddings")
    if error_count > 0:
        print(f"❌ Failed: {error_count} embeddings")
    print("")
    
    # Verify embeddings
    print("🔍 Verifying embeddings...")
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_claims,
                    COUNT(description_embedding) as claims_with_embeddings,
                    COUNT(*) - COUNT(description_embedding) as claims_without_embeddings
                FROM claims
                WHERE description IS NOT NULL AND description != ''
            """)
            stats = cursor.fetchone()
            
            print(f"   Total claims with descriptions: {stats[0]}")
            print(f"   Claims with embeddings: {stats[1]}")
            print(f"   Claims without embeddings: {stats[2]}")
            
            if stats[2] == 0:
                print("")
                print("🎉 All claims now have embeddings!")
            else:
                print("")
                print(f"⚠️  {stats[2]} claims still need embeddings")
    except Exception as e:
        print(f"❌ Verification failed: {e}")
    
    # Close connection
    conn.close()
    print("")
    print("✅ Done!")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

# Made with Bob
