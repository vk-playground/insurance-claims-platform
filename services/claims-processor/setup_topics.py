"""Script to create Kafka topics in Confluent Cloud."""
from confluent_kafka.admin import AdminClient, NewTopic
from config import settings
import structlog

logger = structlog.get_logger()


def create_topics():
    """Create all required Kafka topics."""
    
    # Admin client configuration
    admin_config = {
        'bootstrap.servers': settings.kafka_bootstrap_servers,
        'security.protocol': settings.kafka_security_protocol,
        'sasl.mechanism': settings.kafka_sasl_mechanism,
        'sasl.username': settings.kafka_sasl_username,
        'sasl.password': settings.kafka_sasl_password,
    }
    
    admin_client = AdminClient(admin_config)
    
    # Define topics to create
    topics = [
        NewTopic(
            topic=settings.kafka_topic_ingest,
            num_partitions=3,
            replication_factor=3,
            config={
                'retention.ms': '2592000000',  # 30 days
                'compression.type': 'snappy'
            }
        ),
        NewTopic(
            topic=settings.kafka_topic_processed,
            num_partitions=3,
            replication_factor=3,
            config={
                'retention.ms': '7776000000',  # 90 days
                'compression.type': 'lz4'
            }
        ),
        NewTopic(
            topic=settings.kafka_topic_approved,
            num_partitions=3,
            replication_factor=3,
            config={
                'retention.ms': '31536000000',  # 365 days
                'compression.type': 'lz4'
            }
        ),
        NewTopic(
            topic=settings.kafka_topic_escalated,
            num_partitions=2,
            replication_factor=3,
            config={
                'retention.ms': '31536000000',  # 365 days
                'compression.type': 'lz4'
            }
        ),
        NewTopic(
            topic=settings.kafka_topic_dlq,
            num_partitions=2,
            replication_factor=3,
            config={
                'retention.ms': '7776000000',  # 90 days
                'compression.type': 'snappy'
            }
        ),
    ]
    
    # Create topics
    fs = admin_client.create_topics(topics)
    
    # Wait for operation to complete
    for topic, f in fs.items():
        try:
            f.result()  # The result itself is None
            logger.info("topic_created", topic=topic)
            print(f"✓ Topic '{topic}' created successfully")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("topic_already_exists", topic=topic)
                print(f"ℹ Topic '{topic}' already exists")
            else:
                logger.error("topic_creation_failed", topic=topic, error=str(e))
                print(f"✗ Failed to create topic '{topic}': {e}")


if __name__ == "__main__":
    print("\n=== Confluent Cloud Topic Setup ===\n")
    print(f"Bootstrap Server: {settings.kafka_bootstrap_servers}")
    print(f"Creating topics...\n")
    
    try:
        create_topics()
        print("\n✓ Topic setup complete!")
    except Exception as e:
        print(f"\n✗ Topic setup failed: {e}")
        exit(1)

# Made with Bob
