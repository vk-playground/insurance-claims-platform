"""Test script to produce sample claims to Kafka."""
import json
from datetime import datetime, timedelta
from confluent_kafka import Producer
from config import settings
import uuid


def create_sample_claim(claim_number: int, amount: float, risk_score: int):
    """Create a sample claim message."""
    return {
        "claimId": f"CLM-2026-{claim_number:06d}",
        "eventId": str(uuid.uuid4()),
        "eventTimestamp": int(datetime.utcnow().timestamp() * 1000),
        "policyNumber": f"POL-2026-{(claim_number % 1000):05d}",
        "claimType": "AUTO_ACCIDENT",
        "incidentDate": int((datetime.utcnow() - timedelta(days=2)).timestamp() * 1000),
        "description": f"Test claim {claim_number} for demo purposes",
        "estimatedAmount": {
            "amount": amount,
            "currency": "USD"
        },
        "riskScore": risk_score,
        "claimant": {
            "userId": f"USER-{claim_number:06d}",
            "name": f"Test User {claim_number}",
            "phone": "+1-555-0100",
            "email": f"user{claim_number}@example.com"
        },
        "location": {
            "latitude": 43.6532,
            "longitude": -79.3832,
            "address": "123 Test Street, Toronto, ON",
            "city": "Toronto",
            "state": "ON",
            "zipCode": "M5H 2N2",
            "country": "Canada"
        }
    }


def delivery_callback(err, msg):
    """Callback for message delivery."""
    if err:
        print(f"✗ Message delivery failed: {err}")
    else:
        print(f"✓ Message delivered to {msg.topic()} [partition {msg.partition()}] at offset {msg.offset()}")


def produce_test_claims():
    """Produce test claims to Kafka."""
    
    # Create producer
    producer = Producer(settings.kafka_config)
    
    print("\n=== Producing Test Claims ===\n")
    print(f"Topic: {settings.kafka_topic_ingest}")
    print(f"Bootstrap Server: {settings.kafka_bootstrap_servers}\n")
    
    # Test scenarios
    test_cases = [
        # Scenario 1: Auto-approve (amount < $2000, risk < 20)
        {
            "name": "Auto-Approve: Low amount, low risk",
            "amount": 1500.00,
            "risk": 15
        },
        # Scenario 2: Under review (amount >= $2000 or risk >= 20)
        {
            "name": "Under Review: Medium amount, medium risk",
            "amount": 5000.00,
            "risk": 45
        },
        # Scenario 3: Escalate (risk > 80)
        {
            "name": "Escalate: High risk",
            "amount": 3000.00,
            "risk": 85
        },
        # Scenario 4: Auto-approve edge case
        {
            "name": "Auto-Approve: Just under threshold",
            "amount": 1999.99,
            "risk": 19
        },
        # Scenario 5: Escalate with high amount
        {
            "name": "Escalate: High risk and high amount",
            "amount": 15000.00,
            "risk": 90
        },
    ]
    
    for idx, test_case in enumerate(test_cases, start=1):
        claim = create_sample_claim(idx, test_case["amount"], test_case["risk"])
        
        print(f"\n{idx}. {test_case['name']}")
        print(f"   Claim ID: {claim['claimId']}")
        print(f"   Amount: ${test_case['amount']:.2f}")
        print(f"   Risk Score: {test_case['risk']}")
        print(f"   Expected: ", end="")
        
        if test_case["amount"] < 2000 and test_case["risk"] < 20:
            print("AUTO_APPROVED")
        elif test_case["risk"] > 80:
            print("ESCALATED")
        else:
            print("UNDER_REVIEW")
        
        # Produce message
        producer.produce(
            topic=settings.kafka_topic_ingest,
            key=claim['claimId'].encode('utf-8'),
            value=json.dumps(claim).encode('utf-8'),
            callback=delivery_callback
        )
        
        # Trigger delivery reports
        producer.poll(0)
    
    # Wait for all messages to be delivered
    print("\n\nWaiting for messages to be delivered...")
    producer.flush()
    
    print("\n✓ All test claims produced successfully!")
    print("\nYou can now run the claims processor service to consume and process these messages.")


if __name__ == "__main__":
    try:
        produce_test_claims()
    except Exception as e:
        print(f"\n✗ Error producing test claims: {e}")
        exit(1)

# Made with Bob
