"""Configuration for Adjuster Agent."""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration class for Adjuster Agent."""
    
    # Database configuration
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', '26257'))
    DB_NAME = os.getenv('DB_NAME', 'defaultdb')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_SSLMODE = os.getenv('DB_SSLMODE', 'verify-full')
    
    # Kafka configuration
    KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    KAFKA_SECURITY_PROTOCOL = os.getenv('KAFKA_SECURITY_PROTOCOL', 'PLAINTEXT')
    KAFKA_SASL_MECHANISM = os.getenv('KAFKA_SASL_MECHANISM', 'PLAIN')
    KAFKA_SASL_USERNAME = os.getenv('KAFKA_SASL_USERNAME', '')
    KAFKA_SASL_PASSWORD = os.getenv('KAFKA_SASL_PASSWORD', '')
    KAFKA_ENABLE_MONITORING = os.getenv('KAFKA_ENABLE_MONITORING', 'false').lower() == 'true'
    
    # Kafka Topics
    KAFKA_TOPIC_INGEST = os.getenv('KAFKA_TOPIC_INGEST', 'claims.ingest')
    KAFKA_TOPIC_APPROVED = os.getenv('KAFKA_TOPIC_APPROVED', 'claims.approved')
    KAFKA_TOPIC_ESCALATED = os.getenv('KAFKA_TOPIC_ESCALATED', 'claims.escalated')
    KAFKA_TOPIC_UNDER_REVIEW = os.getenv('KAFKA_TOPIC_UNDER_REVIEW', 'claims.under_review')
    
    # Chainlit configuration
    CHAINLIT_HOST = os.getenv('CHAINLIT_HOST', '0.0.0.0')
    CHAINLIT_PORT = int(os.getenv('CHAINLIT_PORT', '8000'))
    
    # Embeddings configuration
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
    SIMILARITY_THRESHOLD = float(os.getenv('SIMILARITY_THRESHOLD', '0.7'))
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Made with Bob
