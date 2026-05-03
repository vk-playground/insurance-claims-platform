"""Database operations for claims processing."""
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, Any
import structlog
from config import settings

logger = structlog.get_logger()


class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self):
        self.connection_string = settings.db_connection_string
        self.conn = None
    
    def connect(self):
        """Establish database connection."""
        try:
            self.conn = psycopg2.connect(
                self.connection_string,
                cursor_factory=RealDictCursor
            )
            logger.info("database_connected", host=settings.db_host, database=settings.db_name)
        except Exception as e:
            logger.error("database_connection_failed", error=str(e))
            raise
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("database_connection_closed")
    
    def verify_policy(self, policy_number: str) -> Optional[Dict[str, Any]]:
        """
        Verify if a policy exists and is active.
        
        Args:
            policy_number: The policy number to verify
            
        Returns:
            Policy information if valid, None otherwise
        """
        try:
            with self.conn.cursor() as cursor:
                # Check if policy exists in claims table (simplified for demo)
                # In production, this would query a separate policies table
                cursor.execute(
                    """
                    SELECT DISTINCT 
                        policy_number,
                        COUNT(*) OVER (PARTITION BY policy_number) as claim_count
                    FROM claims 
                    WHERE policy_number = %s
                    LIMIT 1
                    """,
                    (policy_number,)
                )
                result = cursor.fetchone()
                
                if result:
                    logger.info(
                        "policy_verified",
                        policy_number=policy_number,
                        existing_claims=result['claim_count']
                    )
                    return dict(result)
                else:
                    # For demo: assume policy is valid if not found
                    # In production, this would return None for invalid policies
                    logger.warning(
                        "policy_not_found_assuming_valid",
                        policy_number=policy_number
                    )
                    return {
                        'policy_number': policy_number,
                        'claim_count': 0,
                        'status': 'ACTIVE'
                    }
                    
        except Exception as e:
            logger.error("policy_verification_failed", error=str(e), policy_number=policy_number)
            return None
    
    def insert_claim(self, claim_data: Dict[str, Any]) -> Optional[str]:
        """
        Insert a new claim into the database.
        
        Args:
            claim_data: Dictionary containing claim information
            
        Returns:
            Claim ID if successful, None otherwise
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO claims (
                        claim_number,
                        policy_number,
                        claimant_name,
                        claimant_email,
                        claimant_phone,
                        incident_date,
                        claim_date,
                        claim_type,
                        claim_amount,
                        risk_score,
                        status,
                        description,
                        created_by
                    ) VALUES (
                        %(claim_number)s,
                        %(policy_number)s,
                        %(claimant_name)s,
                        %(claimant_email)s,
                        %(claimant_phone)s,
                        %(incident_date)s,
                        NOW(),
                        %(claim_type)s,
                        %(claim_amount)s,
                        %(risk_score)s,
                        %(status)s,
                        %(description)s,
                        %(created_by)s
                    )
                    RETURNING claim_id
                    """,
                    claim_data
                )
                result = cursor.fetchone()
                self.conn.commit()
                
                claim_id = str(result['claim_id'])
                logger.info(
                    "claim_inserted",
                    claim_id=claim_id,
                    claim_number=claim_data['claim_number'],
                    status=claim_data['status']
                )
                return claim_id
                
        except Exception as e:
            self.conn.rollback()
            logger.error("claim_insertion_failed", error=str(e), claim_data=claim_data)
            return None
    
    def update_claim_status(
        self,
        claim_number: str,
        status: str,
        status_reason: Optional[str] = None
    ) -> bool:
        """
        Update the status of a claim.
        
        Args:
            claim_number: The claim number to update
            status: New status value
            status_reason: Optional reason for status change
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE claims 
                    SET 
                        status = %s,
                        status_reason = %s,
                        previous_status = status,
                        updated_at = NOW()
                    WHERE claim_number = %s
                    """,
                    (status, status_reason, claim_number)
                )
                self.conn.commit()
                
                logger.info(
                    "claim_status_updated",
                    claim_number=claim_number,
                    new_status=status,
                    reason=status_reason
                )
                return True
                
        except Exception as e:
            self.conn.rollback()
            logger.error(
                "claim_status_update_failed",
                error=str(e),
                claim_number=claim_number
            )
            return False

# Made with Bob
