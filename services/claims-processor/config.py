"""Configuration management for the claims processor service."""
import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Kafka Configuration
    kafka_bootstrap_servers: str = Field(
        default="pkc-4rn2p.canadacentral.azure.confluent.cloud:9092",
        alias="KAFKA_BOOTSTRAP_SERVERS"
    )
    kafka_security_protocol: str = Field(default="SASL_SSL", alias="KAFKA_SECURITY_PROTOCOL")
    kafka_sasl_mechanism: str = Field(default="PLAIN", alias="KAFKA_SASL_MECHANISM")
    kafka_sasl_username: str = Field(default="", alias="KAFKA_SASL_USERNAME")
    kafka_sasl_password: str = Field(default="", alias="KAFKA_SASL_PASSWORD")
    kafka_group_id: str = Field(default="claims-processor-group", alias="KAFKA_GROUP_ID")
    kafka_auto_offset_reset: str = Field(default="earliest", alias="KAFKA_AUTO_OFFSET_RESET")
    
    # Kafka Topics
    kafka_topic_ingest: str = Field(default="claims.ingest", alias="KAFKA_TOPIC_INGEST")
    kafka_topic_processed: str = Field(default="claims.processed", alias="KAFKA_TOPIC_PROCESSED")
    kafka_topic_approved: str = Field(default="claims.approved", alias="KAFKA_TOPIC_APPROVED")
    kafka_topic_escalated: str = Field(default="claims.escalated", alias="KAFKA_TOPIC_ESCALATED")
    kafka_topic_dlq: str = Field(default="claims.dlq", alias="KAFKA_TOPIC_DLQ")
    
    # CockroachDB Configuration
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=26257, alias="DB_PORT")
    db_name: str = Field(default="insurance_claims", alias="DB_NAME")
    db_user: str = Field(default="root", alias="DB_USER")
    db_password: str = Field(default="", alias="DB_PASSWORD")
    db_sslmode: str = Field(default="require", alias="DB_SSLMODE")
    
    # Service Configuration
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    service_name: str = Field(default="claims-processor", alias="SERVICE_NAME")
    metrics_port: int = Field(default=9090, alias="METRICS_PORT")
    
    # AI Logic Gate Thresholds
    auto_approve_amount_threshold: float = Field(default=2000.0, alias="AUTO_APPROVE_AMOUNT_THRESHOLD")
    auto_approve_risk_threshold: int = Field(default=20, alias="AUTO_APPROVE_RISK_THRESHOLD")
    escalation_risk_threshold: int = Field(default=80, alias="ESCALATION_RISK_THRESHOLD")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def db_connection_string(self) -> str:
        """Generate database connection string."""
        password_part = f":{self.db_password}" if self.db_password else ""
        return (
            f"postgresql://{self.db_user}{password_part}@{self.db_host}:{self.db_port}/"
            f"{self.db_name}?sslmode={self.db_sslmode}"
        )
    
    @property
    def kafka_config(self) -> dict:
        """Generate Kafka consumer/producer configuration."""
        config = {
            'bootstrap.servers': self.kafka_bootstrap_servers,
            'security.protocol': self.kafka_security_protocol,
            'sasl.mechanism': self.kafka_sasl_mechanism,
            'sasl.username': self.kafka_sasl_username,
            'sasl.password': self.kafka_sasl_password,
        }
        return config
    
    @property
    def kafka_consumer_config(self) -> dict:
        """Generate Kafka consumer-specific configuration."""
        config = self.kafka_config.copy()
        config.update({
            'group.id': self.kafka_group_id,
            'auto.offset.reset': self.kafka_auto_offset_reset,
            'enable.auto.commit': False,  # Manual commit for reliability
        })
        return config


# Global settings instance
settings = Settings()

# Made with Bob
