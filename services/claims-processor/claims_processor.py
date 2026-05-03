"""Main claims processor with AI logic gate."""
import json
from typing import Dict, Any, Optional
from datetime import datetime
import structlog
from config import settings
from database import DatabaseManager

logger = structlog.get_logger()


class ClaimsProcessor:
    """Processes insurance claims with AI logic gate for auto-approval and escalation."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.auto_approve_amount = settings.auto_approve_amount_threshold
        self.auto_approve_risk = settings.auto_approve_risk_threshold
        self.escalation_risk = settings.escalation_risk_threshold
    
    def process_claim(self, claim_message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a claim with AI logic gate.
        
        Logic:
        1. Verify policy in CockroachDB
        2. Apply AI logic gate:
           - If claim < $2,000 AND Risk < 20: AUTO_APPROVED
           - If Risk > 80: ESCALATED
           - Otherwise: UNDER_REVIEW
        
        Args:
            claim_message: Claim data from Kafka message
            
        Returns:
            Processing result with decision and next topic
        """
        claim_number = claim_message.get('claimId', claim_message.get('claim_number'))
        policy_number = claim_message.get('policyNumber', claim_message.get('policy_number'))
        claim_amount = float(claim_message.get('estimatedAmount', {}).get('amount', 0) 
                           if isinstance(claim_message.get('estimatedAmount'), dict)
                           else claim_message.get('claim_amount', 0))
        risk_score = int(claim_message.get('riskScore', claim_message.get('risk_score', 50)))
        
        logger.info(
            "processing_claim",
            claim_number=claim_number,
            policy_number=policy_number,
            amount=claim_amount,
            risk_score=risk_score
        )
        
        # Step 1: Verify policy in CockroachDB
        policy = self.db.verify_policy(policy_number)
        if not policy:
            logger.error("policy_verification_failed", policy_number=policy_number)
            return {
                'decision': 'REJECTED',
                'reason': 'Policy verification failed',
                'next_topic': settings.kafka_topic_dlq,
                'claim_number': claim_number
            }
        
        logger.info("policy_verified", policy_number=policy_number, policy_data=policy)
        
        # Step 2: Apply AI Logic Gate
        decision = self._apply_ai_logic_gate(claim_amount, risk_score)
        
        # Step 3: Prepare claim data for database
        claim_data = self._prepare_claim_data(claim_message, decision)
        
        # Step 4: Insert claim into database
        claim_id = self.db.insert_claim(claim_data)
        if not claim_id:
            logger.error("claim_insertion_failed", claim_number=claim_number)
            return {
                'decision': 'ERROR',
                'reason': 'Database insertion failed',
                'next_topic': settings.kafka_topic_dlq,
                'claim_number': claim_number
            }
        
        # Step 5: Determine next topic based on decision
        next_topic = self._get_next_topic(decision['status'])
        
        result = {
            'claim_id': claim_id,
            'claim_number': claim_number,
            'policy_number': policy_number,
            'decision': decision['status'],
            'reason': decision['reason'],
            'next_topic': next_topic,
            'claim_amount': claim_amount,
            'risk_score': risk_score,
            'processed_at': datetime.utcnow().isoformat()
        }
        
        logger.info(
            "claim_processed",
            claim_id=claim_id,
            claim_number=claim_number,
            decision=decision['status'],
            next_topic=next_topic
        )
        
        return result
    
    def _apply_ai_logic_gate(self, claim_amount: float, risk_score: int) -> Dict[str, str]:
        """
        Apply AI logic gate to determine claim status.
        
        Rules:
        1. If claim < $2,000 AND Risk < 20: AUTO_APPROVED
        2. If Risk > 80: ESCALATED
        3. Otherwise: UNDER_REVIEW
        
        Args:
            claim_amount: Claim amount in dollars
            risk_score: Risk score (0-100)
            
        Returns:
            Dictionary with status and reason
        """
        # Rule 1: Auto-approve low-value, low-risk claims
        if claim_amount < self.auto_approve_amount and risk_score < self.auto_approve_risk:
            logger.info(
                "ai_decision_auto_approved",
                amount=claim_amount,
                risk=risk_score,
                threshold_amount=self.auto_approve_amount,
                threshold_risk=self.auto_approve_risk
            )
            return {
                'status': 'APPROVED',  # Changed from AUTO_APPROVED to match DB constraint
                'reason': f'Auto-approved: Amount ${claim_amount:.2f} < ${self.auto_approve_amount} and Risk {risk_score} < {self.auto_approve_risk}'
            }
        
        # Rule 2: Escalate high-risk claims
        if risk_score > self.escalation_risk:
            logger.warning(
                "ai_decision_escalated",
                amount=claim_amount,
                risk=risk_score,
                threshold_risk=self.escalation_risk
            )
            return {
                'status': 'ESCALATED',
                'reason': f'Escalated: High risk score {risk_score} > {self.escalation_risk}'
            }
        
        # Rule 3: Manual review for everything else
        logger.info(
            "ai_decision_under_review",
            amount=claim_amount,
            risk=risk_score
        )
        return {
            'status': 'UNDER_REVIEW',
            'reason': f'Manual review required: Amount ${claim_amount:.2f} or Risk {risk_score} outside auto-approval thresholds'
        }
    
    def _prepare_claim_data(self, claim_message: Dict[str, Any], decision: Dict[str, str]) -> Dict[str, Any]:
        """
        Prepare claim data for database insertion.
        
        Args:
            claim_message: Original claim message
            decision: AI decision result
            
        Returns:
            Formatted claim data for database
        """
        # Extract claimant information
        claimant = claim_message.get('claimant', {})
        
        # Convert incident_date from milliseconds timestamp to datetime
        incident_date_ms = claim_message.get('incidentDate', claim_message.get('incident_date'))
        if isinstance(incident_date_ms, (int, float)):
            incident_date = datetime.fromtimestamp(incident_date_ms / 1000)
        else:
            incident_date = datetime.utcnow()
        
        return {
            'claim_number': claim_message.get('claimId', claim_message.get('claim_number', 'UNKNOWN')),
            'policy_number': claim_message.get('policyNumber', claim_message.get('policy_number', 'UNKNOWN')),
            'claimant_name': claimant.get('name', claim_message.get('claimant_name', 'Unknown')),
            'claimant_email': claimant.get('email', claim_message.get('claimant_email')),
            'claimant_phone': claimant.get('phone', claim_message.get('claimant_phone')),
            'incident_date': incident_date,
            'claim_type': self._normalize_claim_type(claim_message.get('claimType', claim_message.get('claim_type', 'other'))),
            'claim_amount': float(
                claim_message.get('estimatedAmount', {}).get('amount', 0)
                if isinstance(claim_message.get('estimatedAmount'), dict)
                else claim_message.get('claim_amount', 0)
            ),
            'risk_score': int(claim_message.get('riskScore', claim_message.get('risk_score', 50))),
            'status': decision['status'],
            'description': claim_message.get('description', ''),
            'created_by': 'claims-processor-service'
        }
    
    def _normalize_claim_type(self, claim_type: str) -> str:
        """
        Normalize claim type to match database constraints.
        
        Args:
            claim_type: Raw claim type from message
            
        Returns:
            Normalized claim type (auto, property, health, life, liability, other)
        """
        claim_type_lower = claim_type.lower()
        
        # Map various claim type formats to database-valid values
        if 'auto' in claim_type_lower or 'vehicle' in claim_type_lower or 'car' in claim_type_lower:
            return 'auto'
        elif 'property' in claim_type_lower or 'home' in claim_type_lower or 'house' in claim_type_lower:
            return 'property'
        elif 'health' in claim_type_lower or 'medical' in claim_type_lower:
            return 'health'
        elif 'life' in claim_type_lower:
            return 'life'
        elif 'liability' in claim_type_lower:
            return 'liability'
        else:
            return 'other'
    
    def _get_next_topic(self, status: str) -> str:
        """
        Determine the next Kafka topic based on claim status.
        
        Args:
            status: Claim status
            
        Returns:
            Next Kafka topic name
        """
        topic_mapping = {
            'APPROVED': settings.kafka_topic_approved,
            'ESCALATED': settings.kafka_topic_escalated,
            'UNDER_REVIEW': settings.kafka_topic_processed,
            'REJECTED': settings.kafka_topic_dlq
        }
        
        return topic_mapping.get(status, settings.kafka_topic_processed)

# Made with Bob
