# iHhashi Refund & Dispute System - Database Schema

> South African Consumer Protection Act (CPA 68 of 2008) & ECTA Compliant

---

## Overview

This schema supports an AI-moderated refund and dispute resolution system that:
- Resolves disputes quickly (target: <24 hours for AI-mediated cases)
- Maintains solid evidence for all decisions
- Complies with SA consumer protection laws
- Provides transparent audit trails

---

## Core Collections

### 1. `refunds`

Primary collection for all refund requests and processing.

```python
class Refund(BaseModel):
    """Refund request and processing record"""
    
    # Identification
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str  # Reference to original order
    user_id: str  # Customer requesting refund
    merchant_id: str  # Merchant who fulfilled order
    
    # Refund Details
    refund_type: RefundType  # FULL, PARTIAL
    status: RefundStatus  # PENDING, AI_PROCESSING, ESCALATED, APPROVED, REJECTED, COMPLETED
    amount: float  # Amount to refund in ZAR
    currency: str = "ZAR"
    
    # Reason & Evidence
    reason_category: RefundReasonCategory
    reason_description: str
    evidence: List[EvidenceItem]  # Photos, videos, messages
    
    # CPA/ECTA Compliance
    legal_basis: LegalBasis  # Which law applies
    within_cooling_off_period: bool  # ECTA 7-day rule
    warranty_claim: bool  # CPA Section 56 (6 months)
    days_since_delivery: int  # For eligibility calculation
    
    # AI Moderation
    ai_decision: Optional[AIDecision]
    ai_confidence_score: Optional[float]  # 0-1
    ai_reasoning: Optional[str]
    requires_human_review: bool = False
    
    # Processing
    approved_by: Optional[str]  # User ID of approver (AI or human)
    approved_at: Optional[datetime]
    rejected_reason: Optional[str]
    rejection_details: Optional[str]
    
    # Payout
    payout_method: Optional[PayoutMethod]
    payout_reference: Optional[str]
    payout_completed_at: Optional[datetime]
    
    # Audit Trail
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime]
    
    # Communication
    messages: List[RefundMessage] = []
    
    class Settings:
        collection = "refunds"


class RefundType(str, Enum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"


class RefundStatus(str, Enum):
    PENDING = "PENDING"
    AI_PROCESSING = "AI_PROCESSING"
    AWAITING_MERCHANT_RESPONSE = "AWAITING_MERCHANT_RESPONSE"
    AWAITING_CUSTOMER_RESPONSE = "AWAITING_CUSTOMER_RESPONSE"
    ESCALATED = "ESCALATED"  # Human review required
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class RefundReasonCategory(str, Enum):
    """Categories aligned with CPA grounds for refund"""
    DEFECTIVE_PRODUCT = "DEFECTIVE_PRODUCT"  # CPA Section 56
    NOT_AS_DESCRIBED = "NOT_AS_DESCRIBED"  # Misleading description
    WRONG_ITEM_DELIVERED = "WRONG_ITEM_DELIVERED"
    MISSING_ITEMS = "MISSING_ITEMS"
    DAMAGED_IN_TRANSIT = "DAMAGED_IN_TRANSIT"
    LATE_DELIVERY = "LATE_DELIVERY"  # ECTA 30-day rule
    QUALITY_ISSUE = "QUALITY_ISSUE"
    FOOD_SAFETY = "FOOD_SAFETY"  # Public health concern
    COOLING_OFF = "COOLING_OFF"  # ECTA 7-day cancellation
    UNSATISFIED = "UNSATISFIED"  # Subjective (may be partial refund)
    COURIER_ISSUE = "COURIER_ISSUE"  # Delivery problems
    OTHER = "OTHER"


class LegalBasis(str, Enum):
    """South African legal grounds for refund"""
    CPA_SECTION_20 = "CPA_SECTION_20"  # Right to return goods
    CPA_SECTION_56 = "CPA_SECTION_56"  # Implied warranty (6 months)
    CPA_SECTION_61 = "CPA_SECTION_61"  # Damages from defective goods
    ECTA_SECTION_44 = "ECTA_SECTION_44"  # 7-day cooling off
    ECTA_SECTION_42 = "ECTA_SECTION_42"  # 30-day delivery failure
    COMPANY_POLICY = "COMPANY_POLICY"  # Voluntary goodwill refund
    DISPUTED = "DISPUTED"  # Requires investigation


class PayoutMethod(str, Enum):
    ORIGINAL_PAYMENT = "ORIGINAL_PAYMENT"  # Refund to card/wallet
    WALLET_CREDIT = "WALLET_CREDIT"  # iHhashi wallet
    BANK_TRANSFER = "BANK_TRANSFER"  # EFT to customer
```

---

### 2. `disputes`

For escalated cases requiring more investigation or merchant-customer mediation.

```python
class Dispute(BaseModel):
    """Complex dispute requiring investigation"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    refund_id: str  # Parent refund request
    
    # Parties
    customer_id: str
    merchant_id: str
    rider_id: Optional[str]  # If delivery issue
    
    # Dispute Details
    status: DisputeStatus
    priority: DisputePriority  # Based on amount, evidence, customer history
    category: DisputeCategory
    
    # Investigation
    assigned_to: Optional[str]  # Human moderator ID
    investigation_notes: List[InvestigationNote] = []
    
    # Timeline
    created_at: datetime = Field(default_factory=datetime.utcnow)
    escalation_reason: str
    target_resolution_hours: int  # SLA target
    resolved_at: Optional[datetime]
    
    # Resolution
    resolution: Optional[DisputeResolution]
    resolution_summary: Optional[str]
    
    # Evidence Trail
    evidence_log: List[EvidenceLogEntry] = []
    
    class Settings:
        collection = "disputes"


class DisputeStatus(str, Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    AWAITING_INFO = "AWAITING_INFO"
    MEDIATION = "MEDIATION"  # AI or human mediation
    DECISION_PENDING = "DECISION_PENDING"
    RESOLVED = "RESOLVED"
    ESCALATED_EXTERNAL = "ESCALATED_EXTERNAL"  # CGSO, NCC


class DisputePriority(str, Enum):
    LOW = "LOW"  # Under R100, straightforward
    MEDIUM = "MEDIUM"  # R100-R500
    HIGH = "HIGH"  # R500-R2000
    CRITICAL = "CRITICAL"  # Over R2000 or safety issue
    URGENT = "URGENT"  # Food safety, health hazard


class DisputeCategory(str, Enum):
    QUALITY_DISPUTE = "QUALITY_DISPUTE"
    DELIVERY_DISPUTE = "DELIVERY_DISPUTE"
    BILLING_DISPUTE = "BILLING_DISPUTE"
    SERVICE_DISPUTE = "SERVICE_DISPUTE"
    FRAUD_SUSPECTED = "FRAUD_SUSPECTED"
    SAFETY_CONCERN = "SAFETY_CONCERN"
```

---

### 3. `ai_moderation_decisions`

Complete audit trail of AI moderator decisions for compliance and improvement.

```python
class AIModerationDecision(BaseModel):
    """Record of AI moderator analysis and decision"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    refund_id: str
    dispute_id: Optional[str]
    
    # Input Data (what AI analyzed)
    input_data: ModerationInput
    
    # AI Analysis
    analysis: AIAnalysis
    
    # Decision
    decision: AIDecisionOutput
    
    # Confidence & Flags
    confidence_score: float  # 0-1
    requires_human_review: bool
    review_reasons: List[str] = []
    
    # Outcome Tracking
    human_overridden: bool = False
    override_reason: Optional[str]
    outcome_correct: Optional[bool]  # Set after human review
    
    # Model Info
    model_version: str
    processing_time_ms: int
    
    # Timestamp
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        collection = "ai_moderation_decisions"


class ModerationInput(BaseModel):
    """Data fed to AI for decision"""
    order_details: dict
    refund_request: dict
    evidence_descriptions: List[str]
    customer_history: CustomerHistorySummary
    merchant_history: MerchantHistorySummary
    time_factors: dict  # Days since order, delivery, etc.


class AIAnalysis(BaseModel):
    """AI's analysis of the case"""
    legal_compliance_check: dict  # CPA/ECTA eligibility
    evidence_strength: float  # 0-1
    evidence_gaps: List[str]  # What evidence is missing
    similar_cases: List[str]  # IDs of similar resolved cases
    precedent_analysis: str  # Text explanation
    merchant_fault_probability: float  # 0-1
    customer_fault_probability: float  # 0-1
    third_party_fault_probability: float  # 0-1 (e.g., rider)


class AIDecisionOutput(BaseModel):
    """AI's recommended decision"""
    recommended_action: RecommendedAction
    recommended_amount: Optional[float]  # For partial refunds
    reasoning: str  # Explainable AI - why this decision
    legal_basis: LegalBasis
    required_actions: List[str]  # Steps to complete
    customer_message_template: str  # Pre-written message
    merchant_message_template: str


class RecommendedAction(str, Enum):
    APPROVE_FULL = "APPROVE_FULL"
    APPROVE_PARTIAL = "APPROVE_PARTIAL"
    REJECT = "REJECT"
    REQUEST_MORE_INFO = "REQUEST_MORE_INFO"
    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"
    MEDIATE_CHAT = "MEDIATE_CHAT"


class CustomerHistorySummary(BaseModel):
    total_orders: int
    refund_requests: int
    refund_approval_rate: float
    average_rating_given: float
    account_age_days: int
    fraud_flags: int


class MerchantHistorySummary(BaseModel):
    total_orders: int
    complaint_rate: float
    average_rating: float
    refund_rate: float
    response_time_hours: float
    quality_issues_count: int
```

---

### 4. `refund_evidence`

Structured evidence storage for audit trail.

```python
class RefundEvidence(BaseModel):
    """Evidence attached to refund/dispute"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    refund_id: str
    
    # Evidence Details
    evidence_type: EvidenceType
    uploaded_by: str  # User ID
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Content
    file_url: Optional[str]  # Image/video URL
    file_type: Optional[str]  # MIME type
    description: str
    
    # AI Analysis
    ai_verified: bool = False
    ai_analysis: Optional[str]  # What AI detected in image
    authenticity_score: Optional[float]  # 0-1
    
    # Verification
    verified_by: Optional[str]  # Human moderator
    verification_notes: Optional[str]
    
    class Settings:
        collection = "refund_evidence"


class EvidenceType(str, Enum):
    PHOTO = "PHOTO"
    VIDEO = "VIDEO"
    RECEIPT = "RECEIPT"
    CHAT_LOG = "CHAT_LOG"
    DELIVERY_PROOF = "DELIVERY_PROOF"
    GPS_LOG = "GPS_LOG"
    TEMPERATURE_LOG = "TEMPERATURE_LOG"  # For cold chain items
    WITNESS_STATEMENT = "WITNESS_STATEMENT"
    OTHER = "OTHER"
```

---

### 5. `refund_policies`

Configurable policies per merchant and system-wide defaults.

```python
class RefundPolicy(BaseModel):
    """Refund policy configuration"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Scope
    scope: PolicyScope  # SYSTEM, MERCHANT, CATEGORY
    merchant_id: Optional[str]  # If merchant-specific
    category: Optional[str]  # Product category override
    
    # Time Limits
    cooling_off_days: int = 7  # ECTA default
    warranty_months: int = 6  # CPA Section 56 default
    claim_window_days: int = 10  # CPA notification period
    
    # Auto-Approve Rules
    auto_approve_under: float = 50.0  # Auto-approve under R50
    auto_approve_categories: List[RefundReasonCategory] = []
    
    # Partial Refund Rules
    partial_refund_rules: List[PartialRefundRule] = []
    
    # Exclusions
    excluded_items: List[str] = []  # Non-refundable items
    exclusion_reasons: List[str] = []  # Perishables, hygiene items
    
    # Service Level
    max_response_hours: int = 24
    max_resolution_hours: int = 72
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    
    class Settings:
        collection = "refund_policies"


class PolicyScope(str, Enum):
    SYSTEM = "SYSTEM"  # Platform-wide default
    MERCHANT = "MERCHANT"  # Merchant-specific
    CATEGORY = "CATEGORY"  # Product category


class PartialRefundRule(BaseModel):
    """Rules for calculating partial refunds"""
    condition: str  # e.g., "late_delivery_over_30_min"
    deduction_percent: float  # e.g., 10.0
    max_deduction: Optional[float]
    description: str
```

---

### 6. `mediation_sessions`

AI-powered chat mediation for disputes.

```python
class MediationSession(BaseModel):
    """AI-mediated dispute resolution session"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    dispute_id: str
    
    # Participants
    customer_id: str
    merchant_id: str
    moderator_type: ModeratorType  # AI, HUMAN
    
    # Session State
    status: MediationStatus
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime]
    
    # Messages
    messages: List[MediationMessage] = []
    
    # Outcome
    resolution_reached: bool = False
    resolution_type: Optional[str]
    resolution_amount: Optional[float]
    
    # AI Moderation
    ai_sentiment_analysis: List[SentimentSnapshot] = []
    escalation_triggered: bool = False
    escalation_reason: Optional[str]
    
    class Settings:
        collection = "mediation_sessions"


class ModeratorType(str, Enum):
    AI = "AI"
    HUMAN = "HUMAN"
    AI_ESCALATED = "AI_ESCALATED"  # Started AI, escalated to human


class MediationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PENDING_RESPONSE = "PENDING_RESPONSE"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"
    TIMEOUT = "TIMEOUT"  # No response within SLA


class MediationMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender_type: str  # CUSTOMER, MERCHANT, MODERATOR, SYSTEM
    sender_id: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ai_flagged: bool = False
    flag_reason: Optional[str]


class SentimentSnapshot(BaseModel):
    timestamp: datetime
    customer_sentiment: float  # -1 to 1
    merchant_sentiment: float  # -1 to 1
    escalation_risk: float  # 0-1
```

---

### 7. `refund_audit_log`

Complete audit trail for compliance and dispute resolution.

```python
class RefundAuditLog(BaseModel):
    """Immutable audit log for all refund actions"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    refund_id: str
    
    # Action Details
    action: RefundAction
    actor_type: ActorType  # SYSTEM, AI, HUMAN
    actor_id: str
    
    # Before/After State
    previous_status: Optional[str]
    new_status: str
    changes: dict  # What changed
    
    # Context
    reason: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    
    # Timestamp
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        collection = "refund_audit_log"


class RefundAction(str, Enum):
    CREATED = "CREATED"
    EVIDENCE_ADDED = "EVIDENCE_ADDED"
    AI_PROCESSED = "AI_PROCESSED"
    STATUS_CHANGED = "STATUS_CHANGED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PAYOUT_INITIATED = "PAYOUT_INITIATED"
    PAYOUT_COMPLETED = "PAYOUT_COMPLETED"
    ESCALATED = "ESCALATED"
    MEDIATION_STARTED = "MEDIATION_STARTED"
    MEDIATION_ENDED = "MEDIATION_ENDED"
    DISPUTED = "DISPUTED"
    CANCELLED = "CANCELLED"
    NOTE_ADDED = "NOTE_ADDED"


class ActorType(str, Enum):
    SYSTEM = "SYSTEM"
    AI = "AI"
    CUSTOMER = "CUSTOMER"
    MERCHANT = "MERCHANT"
    MODERATOR = "MODERATOR"
    ADMIN = "ADMIN"
```

---

## Indexes

```python
# Performance indexes
Refund.indexes = [
    IndexModel([("user_id", 1), ("status", 1)]),
    IndexModel([("merchant_id", 1), ("status", 1)]),
    IndexModel([("status", 1), ("created_at", -1)]),
    IndexModel([("created_at", -1)]),
]

Dispute.indexes = [
    IndexModel([("refund_id", 1)]),
    IndexModel([("status", 1), ("priority", -1)]),
    IndexModel([("assigned_to", 1), ("status", 1)]),
]

AIModerationDecision.indexes = [
    IndexModel([("refund_id", 1)]),
    IndexModel([("created_at", -1)]),
    IndexModel([("requires_human_review", 1), ("created_at", -1)]),
]

MediationSession.indexes = [
    IndexModel([("dispute_id", 1)]),
    IndexModel([("status", 1), ("started_at", -1)]),
]
```

---

## South African Legal Compliance

### CPA Section 56 - Implied Warranty
- All goods have 6-month implied warranty
- Consumer can choose: repair, replacement, or refund
- If repair fails within 3 months, refund/replacement required

### ECTA Section 44 - Cooling Off Period
- 7-day unconditional return for online purchases
- Consumer pays return shipping
- Full refund required

### ECTA Section 42 - Delivery Timeline
- If not delivered within 30 days, consumer can cancel
- Full refund required

### CPA Section 20 - Right to Return
- Right to return goods not examined before purchase
- Must notify within 10 business days
- Refund within 15 business days

### Record Retention
- All records kept for minimum 5 years
- Audit logs immutable
- Evidence preserved for legal proceedings

---

## Implementation Notes

1. **Evidence Collection**: Automatically capture GPS logs, delivery photos, timestamps
2. **AI Decision Thresholds**: 
   - Confidence > 0.85: Auto-decide
   - Confidence 0.6-0.85: Flag for review but proceed
   - Confidence < 0.6: Escalate to human
3. **Time Limits**: 
   - AI must decide within 5 minutes
   - Human response within 24 hours
   - Total resolution within 72 hours (vs industry standard 7-14 days)
4. **Appeals**: Customers can appeal AI decisions within 7 days
