"""Run database migration to add vector embeddings support."""
import psycopg2
import sys

# Connection string
conn_str = 'postgresql://vicky:cffak3fHvm4SajXa1o6p4g@claims-demo-15395.jxf.gcp-us-east1.cockroachlabs.cloud:26257/defaultdb?sslmode=verify-full'

def run_migration():
    """Execute migration to add vector columns."""
    try:
        # Connect to database
        conn = psycopg2.connect(conn_str)
        cursor = conn.cursor()
        print('✓ Connected to CockroachDB\n')
        
        # Step 1: Add vector column
        print('Step 1: Adding vector column...')
        try:
            cursor.execute("""
                ALTER TABLE claims ADD COLUMN IF NOT EXISTS description_embedding VECTOR(384)
            """)
            conn.commit()
            print('✓ Vector column added\n')
        except Exception as e:
            if 'already exists' in str(e).lower():
                print('⚠ Vector column already exists\n')
                conn.rollback()
            else:
                raise
        
        # Step 2: Add metadata columns
        print('Step 2: Adding metadata columns...')
        try:
            cursor.execute("""
                ALTER TABLE claims ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(100) DEFAULT 'all-MiniLM-L6-v2'
            """)
            cursor.execute("""
                ALTER TABLE claims ADD COLUMN IF NOT EXISTS embedding_generated_at TIMESTAMP
            """)
            conn.commit()
            print('✓ Metadata columns added\n')
        except Exception as e:
            if 'already exists' in str(e).lower():
                print('⚠ Metadata columns already exist\n')
                conn.rollback()
            else:
                raise
        
        # Step 3: Create vector index
        print('Step 3: Creating vector index...')
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_claims_description_embedding 
                ON claims USING HNSW (description_embedding vector_cosine_ops)
            """)
            conn.commit()
            print('✓ Vector index created\n')
        except Exception as e:
            if 'already exists' in str(e).lower():
                print('⚠ Vector index already exists\n')
                conn.rollback()
            else:
                raise
        
        # Verify columns
        print('Verification:')
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'claims' 
            AND column_name IN ('description_embedding', 'embedding_model', 'embedding_generated_at')
            ORDER BY column_name
        """)
        columns = cursor.fetchall()
        print(f'✓ Found {len(columns)} vector-related columns:')
        for col in columns:
            print(f'  - {col[0]}: {col[1]}')
        
        cursor.close()
        conn.close()
        
        print('\n✓ Migration completed successfully!')
        return True
        
    except Exception as e:
        print(f'\n✗ Migration failed: {e}')
        return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)

# Made with Bob
