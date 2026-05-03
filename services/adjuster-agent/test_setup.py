#!/usr/bin/env python3
"""Test script to verify Adjuster Agent setup."""
import sys

def test_imports():
    """Test all required imports."""
    print("🔍 Testing imports...")
    
    try:
        import chainlit
        print("  ✅ chainlit")
    except ImportError as e:
        print(f"  ❌ chainlit: {e}")
        return False
    
    try:
        import psycopg2
        print("  ✅ psycopg2")
    except ImportError as e:
        print(f"  ❌ psycopg2: {e}")
        return False
    
    try:
        from confluent_kafka import Consumer
        print("  ✅ confluent-kafka")
    except ImportError as e:
        print(f"  ❌ confluent-kafka: {e}")
        return False
    
    try:
        from sentence_transformers import SentenceTransformer
        print("  ✅ sentence-transformers")
    except ImportError as e:
        print(f"  ❌ sentence-transformers: {e}")
        return False
    
    try:
        import structlog
        print("  ✅ structlog")
    except ImportError as e:
        print(f"  ❌ structlog: {e}")
        return False
    
    return True

def test_config():
    """Test configuration."""
    print("\n🔍 Testing configuration...")
    
    try:
        from config import Config
        config = Config()
        print(f"  ✅ Database: {config.DB_HOST}:{config.DB_PORT}")
        print(f"  ✅ Kafka: {config.KAFKA_BOOTSTRAP_SERVERS}")
        print(f"  ✅ Kafka Monitoring: {config.KAFKA_ENABLE_MONITORING}")
        print(f"  ✅ Chainlit Port: {config.CHAINLIT_PORT}")
        return True
    except Exception as e:
        print(f"  ❌ Configuration error: {e}")
        return False

def test_database():
    """Test database connection."""
    print("\n🔍 Testing database connection...")
    
    try:
        from database_client import DatabaseClient
        client = DatabaseClient()
        print("  ✅ Database connection successful")
        client.close()
        return True
    except Exception as e:
        print(f"  ❌ Database connection failed: {e}")
        return False

def test_embeddings():
    """Test embeddings model."""
    print("\n🔍 Testing embeddings model...")
    
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        embedding = model.encode("test")
        print(f"  ✅ Embeddings model loaded (dimension: {len(embedding)})")
        return True
    except Exception as e:
        print(f"  ❌ Embeddings model failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("🧪 Adjuster Agent Setup Test")
    print("=" * 60)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Configuration", test_config()))
    results.append(("Database", test_database()))
    results.append(("Embeddings", test_embeddings()))
    
    print("\n" + "=" * 60)
    print("📊 Test Results")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:20s} {status}")
    
    all_passed = all(result[1] for result in results)
    
    print("=" * 60)
    if all_passed:
        print("🎉 All tests passed! Ready to start Chainlit.")
        print("\nRun: chainlit run app.py -w")
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
