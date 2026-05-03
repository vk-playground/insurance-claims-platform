"""Main entry point for the claims processor service."""
import json
import signal
import sys
from typing import Optional
from confluent_kafka import Consumer, Producer, KafkaError, KafkaException
import structlog
from config import settings
from database import DatabaseManager
from claims_processor import ClaimsProcessor

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


class ClaimsProcessorService:
    """Main service class for processing insurance claims."""
    
    def __init__(self):
        self.running = False
        self.consumer: Optional[Consumer] = None
        self.producer: Optional[Producer] = None
        self.db_manager: Optional[DatabaseManager] = None
        self.processor: Optional[ClaimsProcessor] = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info("shutdown_signal_received", signal=signum)
        self.running = False
    
    def initialize(self):
        """Initialize all service components."""
        logger.info("initializing_service", service=settings.service_name)
        
        # Initialize database
        try:
            self.db_manager = DatabaseManager()
            self.db_manager.connect()
            logger.info("database_initialized")
        except Exception as e:
            logger.error("database_initialization_failed", error=str(e))
            raise
        
        # Initialize claims processor
        self.processor = ClaimsProcessor(self.db_manager)
        logger.info("claims_processor_initialized")
        
        # Initialize Kafka consumer
        try:
            self.consumer = Consumer(settings.kafka_consumer_config)
            self.consumer.subscribe([settings.kafka_topic_ingest])
            logger.info(
                "kafka_consumer_initialized",
                topic=settings.kafka_topic_ingest,
                group_id=settings.kafka_group_id
            )
        except Exception as e:
            logger.error("kafka_consumer_initialization_failed", error=str(e))
            raise
        
        # Initialize Kafka producer
        try:
            self.producer = Producer(settings.kafka_config)
            logger.info("kafka_producer_initialized")
        except Exception as e:
            logger.error("kafka_producer_initialization_failed", error=str(e))
            raise
        
        logger.info("service_initialization_complete")
    
    def run(self):
        """Main service loop."""
        self.running = True
        logger.info(
            "service_started",
            service=settings.service_name,
            listening_topic=settings.kafka_topic_ingest
        )
        
        try:
            while self.running:
                # Poll for messages
                msg = self.consumer.poll(timeout=1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # End of partition, not an error
                        continue
                    else:
                        logger.error("kafka_error", error=msg.error())
                        continue
                
                # Process message
                self._process_message(msg)
                
        except KafkaException as e:
            logger.error("kafka_exception", error=str(e))
        except Exception as e:
            logger.error("unexpected_error", error=str(e))
        finally:
            self.shutdown()
    
    def _process_message(self, msg):
        """
        Process a single Kafka message.
        
        Args:
            msg: Kafka message
        """
        try:
            # Decode message
            claim_data = json.loads(msg.value().decode('utf-8'))
            claim_number = claim_data.get('claimId', claim_data.get('claim_number', 'UNKNOWN'))
            
            logger.info(
                "message_received",
                claim_number=claim_number,
                topic=msg.topic(),
                partition=msg.partition(),
                offset=msg.offset()
            )
            
            # Process claim
            result = self.processor.process_claim(claim_data)
            
            # Publish result to next topic
            self._publish_result(result)
            
            # Commit offset after successful processing
            self.consumer.commit(asynchronous=False)
            
            logger.info(
                "message_processed_successfully",
                claim_number=claim_number,
                decision=result['decision'],
                next_topic=result['next_topic']
            )
            
        except json.JSONDecodeError as e:
            logger.error("json_decode_error", error=str(e), raw_message=msg.value())
            self._send_to_dlq(msg, f"JSON decode error: {str(e)}")
            self.consumer.commit(asynchronous=False)
            
        except Exception as e:
            logger.error(
                "message_processing_error",
                error=str(e),
                claim_data=claim_data if 'claim_data' in locals() else None
            )
            self._send_to_dlq(msg, f"Processing error: {str(e)}")
            self.consumer.commit(asynchronous=False)
    
    def _publish_result(self, result: dict):
        """
        Publish processing result to the appropriate Kafka topic.
        
        Args:
            result: Processing result dictionary
        """
        try:
            topic = result['next_topic']
            message = {
                'claimId': result['claim_number'],
                'claimNumber': result['claim_number'],
                'policyNumber': result['policy_number'],
                'decision': result['decision'],
                'reason': result['reason'],
                'claimAmount': result['claim_amount'],
                'riskScore': result['risk_score'],
                'processedAt': result['processed_at'],
                'processedBy': settings.service_name
            }
            
            self.producer.produce(
                topic=topic,
                key=result['claim_number'].encode('utf-8'),
                value=json.dumps(message).encode('utf-8'),
                callback=self._delivery_callback
            )
            
            # Trigger delivery reports
            self.producer.poll(0)
            
            logger.info(
                "result_published",
                claim_number=result['claim_number'],
                topic=topic,
                decision=result['decision']
            )
            
        except Exception as e:
            logger.error("result_publication_failed", error=str(e), result=result)
    
    def _send_to_dlq(self, msg, error_reason: str):
        """
        Send failed message to Dead Letter Queue.
        
        Args:
            msg: Original Kafka message
            error_reason: Reason for failure
        """
        try:
            dlq_message = {
                'original_topic': msg.topic(),
                'original_partition': msg.partition(),
                'original_offset': msg.offset(),
                'original_value': msg.value().decode('utf-8', errors='replace'),
                'error_reason': error_reason,
                'failed_at': structlog.processors.TimeStamper(fmt="iso")(None, None, {})['timestamp']
            }
            
            self.producer.produce(
                topic=settings.kafka_topic_dlq,
                value=json.dumps(dlq_message).encode('utf-8'),
                callback=self._delivery_callback
            )
            
            self.producer.poll(0)
            
            logger.warning(
                "message_sent_to_dlq",
                topic=settings.kafka_topic_dlq,
                error=error_reason
            )
            
        except Exception as e:
            logger.error("dlq_send_failed", error=str(e))
    
    def _delivery_callback(self, err, msg):
        """
        Kafka producer delivery callback.
        
        Args:
            err: Error if delivery failed
            msg: Delivered message
        """
        if err:
            logger.error(
                "message_delivery_failed",
                error=str(err),
                topic=msg.topic()
            )
        else:
            logger.debug(
                "message_delivered",
                topic=msg.topic(),
                partition=msg.partition(),
                offset=msg.offset()
            )
    
    def shutdown(self):
        """Shutdown service gracefully."""
        logger.info("shutting_down_service")
        
        if self.consumer:
            self.consumer.close()
            logger.info("kafka_consumer_closed")
        
        if self.producer:
            self.producer.flush()
            logger.info("kafka_producer_flushed")
        
        if self.db_manager:
            self.db_manager.close()
            logger.info("database_connection_closed")
        
        logger.info("service_shutdown_complete")


def main():
    """Main entry point."""
    logger.info(
        "starting_claims_processor_service",
        service=settings.service_name,
        log_level=settings.log_level
    )
    
    service = ClaimsProcessorService()
    
    try:
        service.initialize()
        service.run()
    except Exception as e:
        logger.error("service_failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()

# Made with Bob
