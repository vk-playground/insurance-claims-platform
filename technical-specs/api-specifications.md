# API Specifications

## REST API Endpoints

### Claims API

#### Submit Claim
```http
POST /api/v1/claims
Content-Type: application/json
Authorization: Bearer {token}

{
  "policyNumber": "POL-789012",
  "incident": {
    "type": "AUTO_ACCIDENT",
    "date": "2026-05-01T14:30:00Z",
    "location": {
      "latitude": 43.6532,
      "longitude": -79.3832,
      "address": "123 Main St, Toronto, ON"
    },
    "description": "Rear-end collision at intersection"
  },
  "damages": {
    "estimatedAmount": 4500.00,
    "items": [
      {
        "category": "VEHICLE_REPAIR",
        "description": "Rear bumper replacement",
        "amount": 3000.00
      }
    ]
  },
  "evidence": {
    "photos": ["base64_encoded_image_1", "base64_encoded_image_2"],
    "documents": ["base64_encoded_pdf"]
  }
}

Response: 201 Created
{
  "claimId": "CLM-2026-0502-XXXX",
  "status": "SUBMITTED",
  "submissionDate": "2026-05-02T16:57:17.573Z",
  "estimatedProcessingTime": "24-48 hours",
  "trackingUrl": "https://app.insurance.com/claims/CLM-2026-0502-XXXX"
}
```

#### Get Claim Status
```http
GET /api/v1/claims/{claimId}
Authorization: Bearer {token}

Response: 200 OK
{
  "claimId": "CLM-2026-0502-XXXX",
  "status": "UNDER_REVIEW",
  "currentStage": "ADJUSTER_REVIEW",
  "assignedAdjuster": "John Smith",
  "lastUpdated": "2026-05-02T18:30:00Z",
  "timeline": [
    {
      "stage": "SUBMITTED",
      "timestamp": "2026-05-02T16:57:17Z",
      "actor": "SYSTEM"
    },
    {
      "stage": "VALIDATED",
      "timestamp": "2026-05-02T16:57:45Z",
      "actor": "SYSTEM"
    },
    {
      "stage": "ASSIGNED",
      "timestamp": "2026-05-02T17:15:00Z",
      "actor": "SYSTEM"
    }
  ]
}
```

### Adjuster API

#### Get Assigned Claims
```http
GET /api/v1/adjusters/me/claims?status=ACTIVE&limit=20
Authorization: Bearer {adjuster_token}

Response: 200 OK
{
  "claims": [
    {
      "claimId": "CLM-2026-0502-XXXX",
      "claimant": "John Doe",
      "incidentType": "AUTO_ACCIDENT",
      "estimatedAmount": 4500.00,
      "priority": "MEDIUM",
      "assignedDate": "2026-05-02T17:15:00Z",
      "dueDate": "2026-05-04T17:15:00Z"
    }
  ],
  "total": 15,
  "page": 1,
  "pageSize": 20
}
```

## GraphQL Schema

```graphql
type Query {
  claim(id: ID!): Claim
  claims(filter: ClaimFilter, pagination: Pagination): ClaimConnection
  adjuster(id: ID!): Adjuster
  policy(policyNumber: String!): Policy
}

type Mutation {
  submitClaim(input: ClaimInput!): ClaimSubmissionResult!
  updateClaimStatus(claimId: ID!, status: ClaimStatus!, notes: String): Claim!
  assignClaim(claimId: ID!, adjusterId: ID!): Assignment!
  approveClaim(claimId: ID!, approvedAmount: Float!, notes: String): Claim!
  rejectClaim(claimId: ID!, reason: String!): Claim!
}

type Subscription {
  claimStatusChanged(claimId: ID!): ClaimStatusUpdate!
  newClaimAssigned(adjusterId: ID!): Claim!
}

type Claim {
  id: ID!
  claimId: String!
  claimant: Claimant!
  policy: Policy!
  incident: Incident!
  damages: Damages!
  status: ClaimStatus!
  priority: Priority!
  assignedAdjuster: Adjuster
  timeline: [ClaimEvent!]!
  createdAt: DateTime!
  updatedAt: DateTime!
}

enum ClaimStatus {
  SUBMITTED
  VALIDATED
  UNDER_REVIEW
  INVESTIGATING
  APPROVED
  REJECTED
  PAID
  CLOSED
}
```

## WebSocket Events

### Real-time Status Updates

```javascript
// Client connection
const ws = new WebSocket('wss://api.insurance.com/ws/claims');

ws.onopen = () => {
  // Subscribe to claim updates
  ws.send(JSON.stringify({
    type: 'SUBSCRIBE',
    channel: 'claim_updates',
    claimId: 'CLM-2026-0502-XXXX'
  }));
};

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  // Handle update
  console.log('Claim update:', update);
};

// Server message format
{
  "type": "CLAIM_STATUS_UPDATE",
  "claimId": "CLM-2026-0502-XXXX",
  "status": "APPROVED",
  "approvedAmount": 4500.00,
  "timestamp": "2026-05-03T10:30:00Z",
  "message": "Your claim has been approved"
}