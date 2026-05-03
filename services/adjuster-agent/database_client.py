"""Database client for Adjuster Agent using CockroachDB."""
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, Any, List
import structlog
from config import Config

logger = structlog.get_logger()


class DatabaseClient:
    """Client for interacting with CockroachDB."""
    
    def __init__(self):
        """Initialize database connection."""
        self.config = Config()
        self.conn = None
        self._connect()
    
    def _connect(self):
        """Establish database connection."""
        try:
            # Extract cluster identifier from hostname for CockroachDB Serverless
            # Format: cluster-name-id.region.cockroachlabs.cloud
            cluster_id = None
            if 'cockroachlabs.cloud' in self.config.DB_HOST:
                # Extract cluster identifier (e.g., "claims-demo-15395" from "claims-demo-15395.jxf.gcp-us-east1.cockroachlabs.cloud")
                cluster_id = self.config.DB_HOST.split('.')[0]
            
            # Build connection parameters
            conn_params = {
                'host': self.config.DB_HOST,
                'port': self.config.DB_PORT,
                'database': self.config.DB_NAME,
                'user': self.config.DB_USER,
                'password': self.config.DB_PASSWORD,
                'sslmode': self.config.DB_SSLMODE,
                'connect_timeout': 10
            }
            
            # Add cluster identifier as options parameter for CockroachDB Serverless
            if cluster_id:
                conn_params['options'] = f'--cluster={cluster_id}'
                logger.info("cockroachdb_serverless_connection", cluster_id=cluster_id)
            
            self.conn = psycopg2.connect(**conn_params)
            logger.info("database_connected", host=self.config.DB_HOST)
        except Exception as e:
            logger.error("database_connection_failed", error=str(e))
            raise
    
    def _ensure_connection(self):
        """Ensure database connection is active."""
        if self.conn is None or self.conn.closed:
            self._connect()
    
    async def get_claim_by_number(self, claim_number: str) -> Optional[Dict[str, Any]]:
        """
        Get claim details by claim number.
        
        Args:
            claim_number: Claim number (e.g., CLM-2026-000001)
            
        Returns:
            Claim details or None if not found
        """
        self._ensure_connection()
        
        query = """
            SELECT 
                claim_id,
                claim_number,
                policy_number,
                claimant_name,
                claimant_email,
                claimant_phone,
                claim_type,
                claim_amount,
                incident_date,
                claim_date,
                description,
                status,
                status_reason,
                risk_score,
                CASE 
                    WHEN risk_score < 30 THEN 'LOW'
                    WHEN risk_score < 70 THEN 'MEDIUM'
                    ELSE 'HIGH'
                END as risk_level,
                created_at,
                updated_at
            FROM claims
            WHERE claim_number = %s
        """
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (claim_number,))
                result = cursor.fetchone()
                
                if result:
                    return dict(result)
                return None
                
        except Exception as e:
            logger.error("get_claim_failed", claim_number=claim_number, error=str(e))
            raise
    
    async def get_claim_statistics(self) -> Dict[str, Any]:
        """
        Get overall claim statistics.
        
        Returns:
            Dictionary with statistics
        """
        self._ensure_connection()
        
        query = """
            SELECT 
                COUNT(*) as total_claims,
                COALESCE(SUM(claim_amount), 0) as total_amount,
                COALESCE(AVG(claim_amount), 0) as average_amount,
                COALESCE(AVG(risk_score), 0) as average_risk_score,
                COUNT(CASE WHEN status = 'AUTO_APPROVED' THEN 1 END) as approved_count,
                COALESCE(SUM(CASE WHEN status = 'AUTO_APPROVED' THEN claim_amount ELSE 0 END), 0) as approved_amount,
                COUNT(CASE WHEN status = 'UNDER_REVIEW' THEN 1 END) as under_review_count,
                COUNT(CASE WHEN status = 'ESCALATED' THEN 1 END) as escalated_count,
                COUNT(CASE WHEN status = 'REJECTED' THEN 1 END) as rejected_count,
                COUNT(CASE WHEN risk_score < 30 THEN 1 END) as low_risk_count,
                COUNT(CASE WHEN risk_score >= 30 AND risk_score < 70 THEN 1 END) as medium_risk_count,
                COUNT(CASE WHEN risk_score >= 70 THEN 1 END) as high_risk_count
            FROM claims
        """
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query)
                result = cursor.fetchone()
                return dict(result) if result else {}
                
        except Exception as e:
            logger.error("get_statistics_failed", error=str(e))
            raise
    
    async def get_high_risk_claims(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get high-risk claims (risk score > 70).
        
        Args:
            limit: Maximum number of claims to return
            
        Returns:
            List of high-risk claims
        """
        self._ensure_connection()
        
        query = """
            SELECT 
                claim_id,
                claim_number,
                policy_number,
                claimant_name,
                claim_type,
                claim_amount,
                risk_score,
                status,
                created_at
            FROM claims
            WHERE risk_score > 70
            ORDER BY risk_score DESC, created_at DESC
            LIMIT %s
        """
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (limit,))
                results = cursor.fetchall()
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error("get_high_risk_claims_failed", error=str(e))
            raise
    
    async def search_claims_by_policyholder(self, name: str) -> List[Dict[str, Any]]:
        """
        Search claims by policyholder name.
        
        Args:
            name: Policyholder name (partial match)
            
        Returns:
            List of matching claims
        """
        self._ensure_connection()
        
        query = """
            SELECT 
                claim_id,
                claim_number,
                policy_number,
                claimant_name,
                claim_type,
                claim_amount,
                status,
                risk_score,
                created_at
            FROM claims
            WHERE claimant_name ILIKE %s
            ORDER BY created_at DESC
            LIMIT 20
        """
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (f'%{name}%',))
                results = cursor.fetchall()
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error("search_claims_failed", name=name, error=str(e))
            raise
    
    async def get_claims_by_status(self, status: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get claims by status.
        
        Args:
            status: Claim status
            limit: Maximum number of claims
            
        Returns:
            List of claims
        """
        self._ensure_connection()
        
        query = """
            SELECT 
                claim_id,
                claim_number,
                policy_number,
                claimant_name,
                claim_type,
                claim_amount,
                status,
                risk_score,
                created_at
            FROM claims
            WHERE status = %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (status, limit))
                results = cursor.fetchall()
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error("get_claims_by_status_failed", status=status, error=str(e))
            raise
    
    def close(self):
        """Close database connection."""
        if self.conn and not self.conn.closed:
            self.conn.close()
            logger.info("database_connection_closed")

# Made with Bob
