"""Demo script showing how to use vector embeddings for semantic claim search."""
import sys
from database import DatabaseManager
from embeddings import EmbeddingGenerator, ClaimEmbeddingManager
from config import settings
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


def demo_embedding_generation():
    """Demonstrate generating embeddings for claim descriptions."""
    print("\n" + "="*80)
    print("DEMO 1: Generating Embeddings")
    print("="*80 + "\n")
    
    # Initialize embedding generator
    generator = EmbeddingGenerator()
    
    # Example claim descriptions
    claims = [
        "Minor collision at intersection, rear-end accident with no injuries",
        "Water damage from burst pipe in basement, extensive flooding",
        "Vehicle collision on highway during heavy rain, multiple cars involved",
        "Fire damage to kitchen from cooking accident, smoke throughout house",
        "Slip and fall accident in grocery store, injured back"
    ]
    
    print("Generating embeddings for sample claims:\n")
    for i, claim_desc in enumerate(claims, 1):
        embedding = generator.generate_embedding(claim_desc)
        print(f"{i}. {claim_desc[:60]}...")
        print(f"   Embedding dimensions: {len(embedding)}")
        print(f"   First 5 values: {embedding[:5]}\n")


def demo_similarity_computation():
    """Demonstrate computing similarity between claims."""
    print("\n" + "="*80)
    print("DEMO 2: Computing Similarity Between Claims")
    print("="*80 + "\n")
    
    generator = EmbeddingGenerator()
    
    # Similar claims
    claim1 = "Car accident on highway with multiple vehicles"
    claim2 = "Vehicle collision on freeway involving several cars"
    
    # Different claims
    claim3 = "Water damage from burst pipe in basement"
    
    emb1 = generator.generate_embedding(claim1)
    emb2 = generator.generate_embedding(claim2)
    emb3 = generator.generate_embedding(claim3)
    
    similarity_12 = generator.compute_similarity(emb1, emb2)
    similarity_13 = generator.compute_similarity(emb1, emb3)
    
    print(f"Claim 1: {claim1}")
    print(f"Claim 2: {claim2}")
    print(f"Similarity: {similarity_12:.4f} (should be HIGH - similar claims)\n")
    
    print(f"Claim 1: {claim1}")
    print(f"Claim 3: {claim3}")
    print(f"Similarity: {similarity_13:.4f} (should be LOW - different claims)\n")


def demo_database_integration():
    """Demonstrate storing and searching embeddings in CockroachDB."""
    print("\n" + "="*80)
    print("DEMO 3: Database Integration - Storing and Searching Embeddings")
    print("="*80 + "\n")
    
    # Initialize database and embedding manager
    db = DatabaseManager()
    db.connect()
    
    manager = ClaimEmbeddingManager(db)
    
    print("Step 1: Generating embeddings for existing claims in database...\n")
    
    # Generate embeddings for existing claims
    stats = manager.batch_generate_embeddings_for_existing_claims(batch_size=10)
    print(f"✓ Processed: {stats['processed']} claims")
    print(f"✓ Updated: {stats['updated']} claims")
    print(f"✓ Skipped: {stats['skipped']} claims\n")
    
    print("Step 2: Searching for similar claims...\n")
    
    # Search for similar claims
    query = "Car accident on highway"
    print(f"Query: '{query}'\n")
    
    similar_claims = manager.find_similar_claims(
        query_text=query,
        similarity_threshold=0.5,
        max_results=5
    )
    
    if similar_claims:
        print(f"Found {len(similar_claims)} similar claims:\n")
        for i, claim in enumerate(similar_claims, 1):
            print(f"{i}. Claim: {claim['claim_number']}")
            print(f"   Similarity: {claim['similarity_score']:.4f}")
            print(f"   Description: {claim['description'][:80]}...")
            print(f"   Amount: ${claim['claim_amount']:,.2f}")
            print(f"   Risk Score: {claim['risk_score']}")
            print(f"   Status: {claim['status']}\n")
    else:
        print("No similar claims found. Try generating embeddings first.\n")
    
    db.close()


def demo_use_cases():
    """Show practical use cases for vector embeddings."""
    print("\n" + "="*80)
    print("PRACTICAL USE CASES FOR VECTOR EMBEDDINGS")
    print("="*80 + "\n")
    
    use_cases = [
        {
            "title": "1. Fraud Detection",
            "description": "Find claims with similar descriptions to known fraudulent claims",
            "example": "Query: 'staged accident with fake injuries' → Find similar suspicious claims"
        },
        {
            "title": "2. Duplicate Detection",
            "description": "Identify potential duplicate claims from the same incident",
            "example": "Query: 'rear-end collision at Main St intersection' → Find duplicates"
        },
        {
            "title": "3. Historical Analysis",
            "description": "Find similar past claims to estimate settlement amounts",
            "example": "Query: 'water damage from burst pipe' → Find similar resolved claims"
        },
        {
            "title": "4. Auto-Assignment",
            "description": "Route claims to adjusters based on their expertise",
            "example": "Query: 'complex fire damage claim' → Find adjuster who handled similar cases"
        },
        {
            "title": "5. Risk Assessment",
            "description": "Compare new claims to high-risk historical claims",
            "example": "Query: new claim description → Find similar high-risk claims"
        }
    ]
    
    for use_case in use_cases:
        print(f"{use_case['title']}")
        print(f"   {use_case['description']}")
        print(f"   Example: {use_case['example']}\n")


def main():
    """Run all demos."""
    print("\n" + "="*80)
    print("VECTOR EMBEDDINGS DEMO FOR INSURANCE CLAIMS")
    print("="*80)
    
    try:
        # Demo 1: Basic embedding generation
        demo_embedding_generation()
        
        # Demo 2: Similarity computation
        demo_similarity_computation()
        
        # Demo 3: Database integration
        demo_database_integration()
        
        # Show use cases
        demo_use_cases()
        
        print("\n" + "="*80)
        print("DEMO COMPLETE!")
        print("="*80 + "\n")
        
    except Exception as e:
        logger.error("demo_failed", error=str(e))
        print(f"\n✗ Demo failed: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

# Made with Bob
