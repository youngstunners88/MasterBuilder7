# iHhashi Refund System - API Endpoints Specification

> South African Consumer Protection Act (CPA) & ECTA Compliant

---

## Base URL

```
Production: https://api.ihhashi.co.za/v1
Staging: https://staging-api.ihhashi.co.za/v1
```

---

## Authentication

All endpoints require Bearer token authentication:

```
Authorization: Bearer <jwt_token>
```

Role-based access control:
- `CUSTOMER` - Can create/view own refunds
- `MERCHANT` - Can respond to refunds on their orders
- `RIDER` - View delivery-related disputes
- `MODERATOR` - Full access to all refunds/disputes
- `ADMIN` - Full system access

---

## Endpoints Overview

| Category | Endpoints |
|----------|-----------|
| Refunds | Create, List, Get, Update, Cancel |
| Evidence | Upload, List, Verify |
| AI Moderation | Trigger, Get Decision, Appeal |
| Disputes | Escalate, List, Assign, Resolve |
| Mediation | Start Session, Send Message, Get History |
| Analytics | Dashboard, Reports, Metrics |

---

## Refunds API

### POST `/refunds`

Create a new refund request.

**Request Body:**
```json
{
  "order_id": "ord_abc123",
  "refund_type": "FULL",
  "reason_category": "DEFECTIVE_PRODUCT",
  "reason_description": "The milk was spoiled and curdled when delivered",
  "amount": 89.99,
  "evidence": [
    {
      "type": "PHOTO",
      "description": "Photo showing curdled milk in container"
    }
  ],
  "preferred_resolution": "REFUND"
}
```

**Response (201 Created):**
```json
{
  "id": "ref_xyz789",
  "order_id": "ord_abc123",
  "status": "AI_PROCESSING",
  "amount": 89.99,
  "legal_basis": "CPA_SECTION_56",
  "within_cooling_off_period": true,
  "days_since_delivery": 1,
  "estimated_resolution_time": "2026-02-28T18:00:00Z",
  "message": "Your refund request is being processed by our AI moderator. You'll receive an update within 5 minutes.",
  "_links": {
    "self": "/v1/refunds/ref_xyz789",
    "upload_evidence": "/v1/refunds/ref_xyz789/evidence",
    "order": "/v1/orders/ord_abc123"
  }
}
```

**Business Logic:**
1. Validate order exists and belongs to user
2. Check refund eligibility (time limits, previous refunds)
3. Determine applicable legal basis (CPA/ECTA)
4. Calculate days since delivery
5. Queue for AI processing
6. Send notification to merchant

**Error Codes:**
- `400` - Invalid request (missing fields, invalid reason)
- `404` - Order not found
- `409` - Refund already exists for this order
- `422` - Outside refund window (with explanation)

---

### GET `/refunds`

List refunds with filtering.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status (comma-separated) |
| `user_id` | string | Filter by customer (moderator only) |
| `merchant_id` | string | Filter by merchant |
| `reason_category` | string | Filter by reason |
| `from_date` | ISO date | Created after date |
| `to_date` | ISO date | Created before date |
| `page` | int | Page number (default: 1) |
| `limit` | int | Items per page (default: 20, max: 100) |

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": "ref_xyz789",
      "order_id": "ord_abc123",
      "status": "APPROVED",
      "reason_category": "DEFECTIVE_PRODUCT",
      "amount": 89.99,
      "created_at": "2026-02-27T10:30:00Z",
      "resolved_at": "2026-02-27T10:35:00Z",
      "resolution_time_minutes": 5
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 45,
    "pages": 3
  },
  "summary": {
    "total_amount_pending": 450.00,
    "total_amount_approved": 1250.50,
    "average_resolution_time_hours": 2.3
  }
}
```

---

### GET `/refunds/{refund_id}`

Get detailed refund information.

**Response (200 OK):**
```json
{
  "id": "ref_xyz789",
  "order_id": "ord_abc123",
  "user_id": "usr_customer1",
  "merchant_id": "merch_shop1",
  "refund_type": "FULL",
  "status": "APPROVED",
  "amount": 89.99,
  "currency": "ZAR",
  
  "reason_category": "DEFECTIVE_PRODUCT",
  "reason_description": "The milk was spoiled and curdled when delivered",
  
  "legal_basis": "CPA_SECTION_56",
  "legal_basis_explanation": "Under Section 56 of the Consumer Protection Act, goods must be of good quality. The spoiled milk violates the implied warranty.",
  "within_cooling_off_period": true,
  "warranty_claim": true,
  "days_since_delivery": 1,
  
  "ai_decision": {
    "action": "APPROVE_FULL",
    "confidence_score": 0.95,
    "reasoning": "Clear evidence of spoiled dairy product. CPA Section 56 applies. Customer entitled to full refund.",
    "processing_time_ms": 234
  },
  
  "evidence": [
    {
      "id": "ev_123",
      "type": "PHOTO",
      "description": "Photo showing curdled milk",
      "uploaded_at": "2026-02-27T10:30:00Z",
      "ai_verified": true,
      "ai_analysis": "Image shows dairy product with visible curdling consistent with spoilage"
    }
  ],
  
  "timeline": [
    {
      "action": "CREATED",
      "timestamp": "2026-02-27T10:30:00Z",
      "actor": "CUSTOMER"
    },
    {
      "action": "AI_PROCESSED",
      "timestamp": "2026-02-27T10:30:15Z",
      "actor": "AI"
    },
    {
      "action": "APPROVED",
      "timestamp": "2026-02-27T10:35:00Z",
      "actor": "AI"
    },
    {
      "action": "PAYOUT_INITIATED",
      "timestamp": "2026-02-27T10:36:00Z",
      "actor": "SYSTEM"
    }
  ],
  
  "payout": {
    "method": "ORIGINAL_PAYMENT",
    "status": "PROCESSING",
    "reference": "PAY-abc123",
    "estimated_completion": "2026-02-28T10:00:00Z"
  },
  
  "created_at": "2026-02-27T10:30:00Z",
  "updated_at": "2026-02-27T10:36:00Z",
  "resolved_at": "2026-02-27T10:35:00Z",
  
  "_links": {
    "self": "/v1/refunds/ref_xyz789",
    "order": "/v1/orders/ord_abc123",
    "evidence": "/v1/refunds/ref_xyz789/evidence",
    "appeal": "/v1/refunds/ref_xyz789/appeal"
  }
}
```

---

### PATCH `/refunds/{refund_id}`

Update refund request (limited fields).

**Request Body:**
```json
{
  "reason_description": "Additional info: The milk had an expiry date of 2026-02-20 but was delivered on 2026-02-27",
  "additional_evidence_ids": ["ev_456"]
}
```

**Response (200 OK):**
```json
{
  "id": "ref_xyz789",
  "status": "AI_PROCESSING",
  "message": "Refund updated and queued for re-evaluation"
}
```

---

### POST `/refunds/{refund_id}/cancel`

Cancel a pending refund request.

**Request Body:**
```json
{
  "reason": "Found the item, was in wrong place"
}
```

**Response (200 OK):**
```json
{
  "id": "ref_xyz789",
  "status": "CANCELLED",
  "cancelled_at": "2026-02-27T11:00:00Z"
}
```

---

### POST `/refunds/{refund_id}/appeal`

Appeal an AI decision.

**Request Body:**
```json
{
  "appeal_reason": "The photo doesn't clearly show the issue. I have additional evidence.",
  "additional_evidence_ids": ["ev_new123"]
}
```

**Response (201 Created):**
```json
{
  "id": "ref_xyz789",
  "status": "ESCALATED",
  "appeal": {
    "id": "app_123",
    "created_at": "2026-02-27T12:00:00Z",
    "status": "PENDING_REVIEW",
    "estimated_response": "2026-02-28T12:00:00Z"
  },
  "message": "Your appeal has been submitted. A human moderator will review within 24 hours."
}
```

---

## Evidence API

### POST `/refunds/{refund_id}/evidence`

Upload evidence for a refund.

**Request (multipart/form-data):**
```
file: [binary]
type: "PHOTO"
description: "Photo of damaged packaging"
```

**Response (201 Created):**
```json
{
  "id": "ev_123",
  "refund_id": "ref_xyz789",
  "type": "PHOTO",
  "description": "Photo of damaged packaging",
  "file_url": "https://storage.ihhashi.co.za/evidence/ev_123.jpg",
  "uploaded_at": "2026-02-27T10:30:00Z",
  "ai_verified": false,
  "message": "Evidence uploaded. AI verification in progress."
}
```

---

### GET `/refunds/{refund_id}/evidence`

List all evidence for a refund.

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": "ev_123",
      "type": "PHOTO",
      "description": "Photo of damaged packaging",
      "file_url": "https://storage.ihhashi.co.za/evidence/ev_123.jpg",
      "uploaded_at": "2026-02-27T10:30:00Z",
      "ai_verified": true,
      "ai_analysis": "Packaging shows visible damage consistent with impact during delivery",
      "uploaded_by": "usr_customer1"
    }
  ],
  "total": 1
}
```

---

### POST `/evidence/{evidence_id}/verify`

Verify evidence (moderator only).

**Request Body:**
```json
{
  "verified": true,
  "notes": "Clear evidence of damage as described"
}
```

---

## AI Moderation API

### POST `/refunds/{refund_id}/process`

Trigger AI moderation processing.

**Response (200 OK):**
```json
{
  "refund_id": "ref_xyz789",
  "ai_decision": {
    "action": "APPROVE_FULL",
    "confidence_score": 0.92,
    "reasoning": "Under CPA Section 56, goods must be of good quality. Evidence shows clear defect within warranty period. Customer entitled to full refund.",
    "legal_basis": "CPA_SECTION_56",
    "required_actions": [
      "Process refund within 24 hours",
      "Notify merchant of decision",
      "Update inventory if item returned"
    ],
    "merchant_fault_probability": 0.88,
    "similar_cases": ["ref_abc", "ref_def"]
  },
  "requires_human_review": false,
  "processing_time_ms": 312
}
```

---

### GET `/refunds/{refund_id}/ai-decision`

Get detailed AI decision breakdown.

**Response (200 OK):**
```json
{
  "refund_id": "ref_xyz789",
  "decision_id": "ai_dec_456",
  
  "input_summary": {
    "order_value": 89.99,
    "days_since_delivery": 1,
    "evidence_count": 2,
    "customer_history": {
      "total_orders": 15,
      "previous_refunds": 1,
      "approval_rate": 1.0
    },
    "merchant_history": {
      "complaint_rate": 0.02,
      "average_rating": 4.3
    }
  },
  
  "analysis": {
    "legal_compliance": {
      "cpa_section_56": {
        "applies": true,
        "reason": "Defective product within 6-month warranty"
      },
      "ecta_cooling_off": {
        "applies": true,
        "reason": "Within 7-day online purchase cooling-off"
      }
    },
    "evidence_strength": 0.85,
    "evidence_gaps": ["No temperature log available for cold chain item"],
    "similar_cases": [
      {
        "case_id": "ref_similar1",
        "similarity": 0.92,
        "outcome": "APPROVED"
      }
    ]
  },
  
  "decision": {
    "action": "APPROVE_FULL",
    "amount": 89.99,
    "confidence": 0.92
  },
  
  "model_info": {
    "version": "ihhashi-moderator-v2.3",
    "trained_on": "2026-02-01",
    "accuracy_metrics": {
      "precision": 0.94,
      "recall": 0.91
    }
  }
}
```

---

## Disputes API

### POST `/refunds/{refund_id}/escalate`

Escalate to dispute (by customer, merchant, or AI).

**Request Body:**
```json
{
  "escalation_reason": "Customer disagrees with AI decision",
  "additional_context": "Customer claims AI misinterpreted evidence",
  "requested_outcome": "Full refund instead of partial"
}
```

**Response (201 Created):**
```json
{
  "id": "disp_123",
  "refund_id": "ref_xyz789",
  "status": "OPEN",
  "priority": "MEDIUM",
  "assigned_to": null,
  "target_resolution_hours": 48,
  "message": "Your dispute has been escalated. A moderator will be assigned within 2 hours.",
  "_links": {
    "self": "/v1/disputes/disp_123",
    "mediation": "/v1/disputes/disp_123/mediation"
  }
}
```

---

### GET `/disputes`

List disputes (moderator view).

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status |
| `priority` | string | Filter by priority |
| `assigned_to` | string | Filter by moderator |
| `unassigned` | boolean | Show only unassigned |
| `page` | int | Page number |
| `limit` | int | Items per page |

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": "disp_123",
      "refund_id": "ref_xyz789",
      "status": "INVESTIGATING",
      "priority": "MEDIUM",
      "amount": 89.99,
      "customer_id": "usr_1",
      "merchant_id": "merch_1",
      "assigned_to": "mod_1",
      "created_at": "2026-02-27T10:00:00Z",
      "sla_remaining_hours": 24
    }
  ],
  "summary": {
    "open": 12,
    "in_progress": 8,
    "resolved_today": 5,
    "average_resolution_hours": 18.5
  }
}
```

---

### PATCH `/disputes/{dispute_id}`

Update dispute (moderator only).

**Request Body:**
```json
{
  "status": "RESOLVED",
  "resolution": {
    "type": "FULL_REFUND",
    "amount": 89.99,
    "reason": "After investigation, evidence supports customer claim. CPA Section 56 applies."
  },
  "resolution_summary": "Evidence clearly showed spoiled milk delivered. Full refund approved."
}
```

---

### POST `/disputes/{dispute_id}/assign`

Assign dispute to moderator.

**Request Body:**
```json
{
  "moderator_id": "mod_123"
}
```

---

## Mediation API

### POST `/disputes/{dispute_id}/mediation`

Start AI mediation session.

**Request Body:**
```json
{
  "moderator_type": "AI",
  "language": "en"
}
```

**Response (201 Created):**
```json
{
  "id": "med_123",
  "dispute_id": "disp_123",
  "status": "ACTIVE",
  "moderator_type": "AI",
  "started_at": "2026-02-27T14:00:00Z",
  "welcome_message": "Hello! I'm the iHhashi AI Mediator. I'm here to help resolve this dispute fairly and quickly. Let's work together to find a solution that works for everyone.",
  "_links": {
    "messages": "/v1/mediation/med_123/messages",
    "websocket": "wss://api.ihhashi.co.za/ws/mediation/med_123"
  }
}
```

---

### GET `/mediation/{session_id}/messages`

Get mediation chat history.

**Query Parameters:**
- `after` - Message ID to get messages after (for pagination)

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": "msg_1",
      "sender_type": "MODERATOR",
      "sender_name": "iHhashi AI Mediator",
      "message": "Hello! I understand there's a dispute about a refund. Let me review the details...",
      "timestamp": "2026-02-27T14:00:00Z"
    },
    {
      "id": "msg_2",
      "sender_type": "CUSTOMER",
      "sender_name": "John D.",
      "message": "Yes, I received spoiled milk and the AI only offered 50% refund",
      "timestamp": "2026-02-27T14:01:00Z"
    },
    {
      "id": "msg_3",
      "sender_type": "MODERATOR",
      "sender_name": "iHhashi AI Mediator",
      "message": "I see. Under the Consumer Protection Act Section 56, you're entitled to a full refund for defective goods. Let me review the evidence again.",
      "timestamp": "2026-02-27T14:01:30Z"
    }
  ],
  "participants": [
    {
      "type": "CUSTOMER",
      "name": "John D.",
      "online": true
    },
    {
      "type": "MERCHANT",
      "name": "QuickMart",
      "online": false
    }
  ]
}
```

---

### POST `/mediation/{session_id}/messages`

Send a message in mediation session.

**Request Body:**
```json
{
  "message": "Here's the additional photo evidence showing the expiry date"
}
```

**Response (201 Created):**
```json
{
  "id": "msg_10",
  "sender_type": "CUSTOMER",
  "message": "Here's the additional photo evidence showing the expiry date",
  "timestamp": "2026-02-27T14:05:00Z"
}
```

---

### POST `/mediation/{session_id}/resolve`

Resolve mediation with agreement.

**Request Body:**
```json
{
  "resolution_type": "FULL_REFUND",
  "amount": 89.99,
  "agreed_by": ["CUSTOMER", "MERCHANT"],
  "notes": "Both parties agreed to full refund after reviewing evidence"
}
```

---

## Analytics API

### GET `/analytics/refunds/dashboard`

Get refund analytics dashboard data.

**Query Parameters:**
- `period` - `day`, `week`, `month`, `year`
- `merchant_id` - Filter by merchant (optional)

**Response (200 OK):**
```json
{
  "period": "month",
  "summary": {
    "total_refunds": 450,
    "total_amount": 45230.50,
    "approval_rate": 0.87,
    "average_resolution_time_hours": 4.2,
    "customer_satisfaction": 4.3
  },
  "by_status": {
    "pending": 12,
    "processing": 5,
    "approved": 380,
    "rejected": 45,
    "escalated": 8
  },
  "by_reason": {
    "DEFECTIVE_PRODUCT": 120,
    "NOT_AS_DESCRIBED": 85,
    "DAMAGED_IN_TRANSIT": 75,
    "LATE_DELIVERY": 60,
    "OTHER": 110
  },
  "ai_performance": {
    "total_decisions": 425,
    "auto_approved": 340,
    "auto_rejected": 32,
    "escalated": 53,
    "accuracy": 0.94,
    "human_override_rate": 0.06
  },
  "trends": {
    "daily_volume": [
      {"date": "2026-02-01", "count": 12, "amount": 1250.00},
      {"date": "2026-02-02", "count": 15, "amount": 1890.50}
    ]
  },
  "top_merchants_by_disputes": [
    {
      "merchant_id": "merch_1",
      "name": "QuickMart",
      "dispute_count": 15,
      "dispute_rate": 0.02
    }
  ]
}
```

---

### GET `/analytics/refunds/cpa-compliance`

Get CPA compliance report.

**Response (200 OK):**
```json
{
  "reporting_period": "2026-02-01 to 2026-02-27",
  "compliance_metrics": {
    "section_56_warranty_claims": {
      "total": 85,
      "resolved_within_sla": 82,
      "compliance_rate": 0.965
    },
    "ecta_cooling_off": {
      "total": 45,
      "all_honored": true,
      "average_resolution_hours": 2.1
    },
    "ecta_30_day_delivery": {
      "total": 12,
      "all_refunded": true
    }
  },
  "audit_trail_complete": true,
  "pending_legal_reviews": 0
}
```

---

## Webhooks

### POST `/webhooks/refund-status`

Webhook for refund status changes.

**Payload:**
```json
{
  "event": "refund.status_changed",
  "timestamp": "2026-02-27T10:35:00Z",
  "data": {
    "refund_id": "ref_xyz789",
    "previous_status": "AI_PROCESSING",
    "new_status": "APPROVED",
    "amount": 89.99,
    "order_id": "ord_abc123",
    "customer_id": "usr_1",
    "merchant_id": "merch_1"
  }
}
```

**Event Types:**
- `refund.created`
- `refund.status_changed`
- `refund.approved`
- `refund.rejected`
- `refund.completed`
- `refund.escalated`
- `mediation.started`
- `mediation.resolved`

---

## Error Responses

Standard error format:

```json
{
  "error": {
    "code": "REFUND_NOT_ELIGIBLE",
    "message": "This order is outside the refund window",
    "details": {
      "order_date": "2026-01-15",
      "current_date": "2026-02-27",
      "days_elapsed": 43,
      "maximum_days": 30
    },
    "legal_reference": "Under ECTA Section 44, cooling-off period is 7 days. CPA Section 56 warranty claims can be made within 6 months for defective goods.",
    "suggested_action": "If you believe the product is defective, you may still file a warranty claim under CPA Section 56."
  }
}
```

---

## Rate Limits

| Endpoint | Rate Limit |
|----------|------------|
| POST `/refunds` | 10 per hour |
| GET `/refunds` | 100 per minute |
| POST `/evidence` | 20 per hour |
| Mediation messages | 60 per minute |

---

## Implementation Priority

### Phase 1 (Immediate)
1. `POST /refunds` - Create refund
2. `GET /refunds/{id}` - Get refund details
3. `POST /refunds/{id}/evidence` - Upload evidence
4. `POST /refunds/{id}/process` - AI moderation

### Phase 2 (Week 2)
1. `GET /refunds` - List with filtering
2. `PATCH /refunds/{id}` - Update
3. `POST /refunds/{id}/appeal` - Appeal
4. `GET /analytics/refunds/dashboard`

### Phase 3 (Week 3-4)
1. Full mediation API
2. Webhooks
3. Advanced analytics
4. CPA compliance reports
