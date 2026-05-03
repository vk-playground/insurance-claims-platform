"""Kafka monitor for real-time claim updates in Adjuster Agent."""
from confluent_kafka import Consumer, KafkaError
import json
import structlog
from typing import Callable, Optional
from config import Config
import threading

logger = structlog.get_logger()


class KafkaClaimMonitor:
    """Monitor Kafka topics for real-time claim updates."""
    
    def __init__(self, callback: Optional[Callable] = None):
        """
        Initialize Kafka monitor.
        
        Args:
            callback: Function to call when new claim is received
        """
        self.config = Config()
        self.callback = callback
        self.consumer = None
        self.running = False
        self.thread = None
        
    def _create_consumer(self):
        """Create Kafka consumer."""
        consumer_config = {
            'bootstrap.servers': self.config.KAFKA_BOOTSTRAP_SERVERS,
            'group.id': 'adjuster-agent-monitor',
            'auto.offset.reset': 'latest',  # Only new messages
            'enable.auto.commit': True,
            'session.timeout.ms': 6000,
        }
        
        # Add authentication if using Confluent Cloud
        if self.config.KAFKA_SECURITY_PROTOCOL != 'PLAINTEXT':
            consumer_config.update({
                'security.protocol': self.config.KAFKA_SECURITY_PROTOCOL,
                'sasl.mechanism': self.config.KAFKA_SASL_MECHANISM,
                'sasl.username': self.config.KAFKA_SASL_USERNAME,
                'sasl.password': self.config.KAFKA_SASL_PASSWORD
            })
            logger.info("kafka_auth_configured",
                       security_protocol=self.config.KAFKA_SECURITY_PROTOCOL,
                       sasl_mechanism=self.config.KAFKA_SASL_MECHANISM)
        
        self.consumer = Consumer(consumer_config)
        logger.info("kafka_consumer_created", group_id="adjuster-agent-monitor")
    
    def start_monitoring(self, topics: list = None):
        """
        Start monitoring Kafka topics in background thread.
        
        Args:
            topics: List of topics to monitor (default: all claim topics)
        """
        if topics is None:
            topics = [
                self.config.KAFKA_TOPIC_INGEST,
                self.config.KAFKA_TOPIC_APPROVED,
                self.config.KAFKA_TOPIC_ESCALATED,
                self.config.KAFKA_TOPIC_UNDER_REVIEW
            ]
        
        self._create_consumer()
        self.consumer.subscribe(topics)
        self.running = True
        
        # Start monitoring in background thread
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        
        logger.info("kafka_monitoring_started", topics=topics)
    
    def _monitor_loop(self):
        """Main monitoring loop (runs in background thread)."""
        while self.running:
            try:
                msg = self.consumer.poll(timeout=1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error("kafka_error", error=msg.error())
                        continue
                
                # Parse message
                claim_data = json.loads(msg.value().decode('utf-8'))
                topic = msg.topic()
                
                logger.info(
                    "claim_received",
                    topic=topic,
                    claim_number=claim_data.get('claim_number'),
                    status=claim_data.get('status')
                )
                
                # Call callback if provided
                if self.callback:
                    self.callback(topic, claim_data)
                    
            except json.JSONDecodeError as e:
                logger.error("json_decode_error", error=str(e))
            except Exception as e:
                logger.error("monitoring_error", error=str(e))
    
    def stop_monitoring(self):
        """Stop monitoring Kafka topics."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        if self.consumer:
            self.consumer.close()
        logger.info("kafka_monitoring_stopped")
    
    def get_recent_claims(self, topic: str, count: int = 10) -> list:
        """
        Get recent claims from a specific topic.
        
        Args:
            topic: Kafka topic name
            count: Number of recent claims to retrieve
            
        Returns:
            List of recent claims
        """
        claims = []
        
        # Create temporary consumer
        temp_config = {
            'bootstrap.servers': self.config.KAFKA_BOOTSTRAP_SERVERS,
            'group.id': f'adjuster-agent-fetch-{topic}',
            'auto.offset.reset': 'latest',
            'enable.auto.commit': False,
        }
        
        # Add authentication if using Confluent Cloud
        if self.config.KAFKA_SECURITY_PROTOCOL != 'PLAINTEXT':
            temp_config.update({
                'security.protocol': self.config.KAFKA_SECURITY_PROTOCOL,
                'sasl.mechanism': self.config.KAFKA_SASL_MECHANISM,
                'sasl.username': self.config.KAFKA_SASL_USERNAME,
                'sasl.password': self.config.KAFKA_SASL_PASSWORD
            })
        
        temp_consumer = Consumer(temp_config)
        
        try:
            temp_consumer.subscribe([topic])
            
            # Fetch messages
            for _ in range(count * 2):  # Fetch more to ensure we get enough
                msg = temp_consumer.poll(timeout=1.0)
                
                if msg is None:
                    break
                
                if msg.error():
                    continue
                
                try:
                    claim_data = json.loads(msg.value().decode('utf-8'))
                    claims.append(claim_data)
                    
                    if len(claims) >= count:
                        break
                except json.JSONDecodeError:
                    continue
                    
        finally:
            temp_consumer.close()
        
        return claims[:count]


class ClaimNotifier:
    """Notify users about real-time claim updates."""
    
    def __init__(self):
        """Initialize notifier."""
        self.subscribers = {}  # session_id -> callback
        
    def subscribe(self, session_id: str, callback: Callable):
        """
        Subscribe to claim notifications.
        
        Args:
            session_id: User session ID
            callback: Function to call with notifications
        """
        self.subscribers[session_id] = callback
        logger.info("user_subscribed", session_id=session_id)
    
    def unsubscribe(self, session_id: str):
        """
        Unsubscribe from notifications.
        
        Args:
            session_id: User session ID
        """
        if session_id in self.subscribers:
            del self.subscribers[session_id]
            logger.info("user_unsubscribed", session_id=session_id)
    
    def notify(self, topic: str, claim_data: dict):
        """
        Notify all subscribers about new claim.
        
        Args:
            topic: Kafka topic
            claim_data: Claim information
        """
        notification = self._format_notification(topic, claim_data)
        
        for session_id, callback in self.subscribers.items():
            try:
                callback(notification)
            except Exception as e:
                logger.error(
                    "notification_failed",
                    session_id=session_id,
                    error=str(e)
                )
    
    def _format_notification(self, topic: str, claim_data: dict) -> str:
        """Format notification message."""
        claim_number = claim_data.get('claim_number', 'Unknown')
        status = claim_data.get('status', 'Unknown')
        amount = claim_data.get('claim_amount', 0)
        risk_score = claim_data.get('risk_score', 0)
        
        # Format based on topic
        if topic == 'claims.approved':
            icon = "✅"
            message = f"**Claim Approved**: {claim_number}"
        elif topic == 'claims.escalated':
            icon = "⚠️"
            message = f"**Claim Escalated**: {claim_number}"
        elif topic == 'claims.under_review':
            icon = "🔍"
            message = f"**Claim Under Review**: {claim_number}"
        else:
            icon = "📋"
            message = f"**New Claim**: {claim_number}"
        
        return f"""
{icon} {message}
- Amount: ${amount:,.2f}
- Risk Score: {risk_score}/100
- Status: {status}
"""


# Global notifier instance
claim_notifier = ClaimNotifier()

# Made with Bob
