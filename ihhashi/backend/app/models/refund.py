"""
Refund, Dispute, and AI Moderation Models
Compliant with South African Consumer Protection Act (CPA) 68 of 2008
and Electronic Communications and Transactions Act (ECTA) 25 of 2002
"""

from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum
from pydantic import BaseModel, Field
from decimal import Decimal


# ============= REFUND MODELS =============

class RefundReason(str, Enum):
    """Valid refund reasons under SA Consumer Protection Act"""
    DEFECTIVE_GOODS = "defective_goods"  # Goods not of good quality (CPA s56)
    NOT_AS_DESCRIBED = "not_as_described"  # Goods don't match description
    WRONG_ITEM = "wrong_item"  # Incorrect item delivered
    MISSING_ITEMS = "missing_items"  # Items missing from order
    DAMAGED_IN_TRANSIT = "damaged_in_transit"  # Damaged during delivery
    LATE_DELIVERY = "late_delivery"  # Not delivered within agreed time (ECTA s42)
    ORDER_CANCELLED = "order_cancelled"  # Customer cancelled within cooling-off period
    FOOD_SAFETY = "food_safety"  # Food safety concerns
    ALLERGEN_ISSUES = "allergen_issues"  # Allergen not disclosed
    COUNTERFEIT = "counterfeit"  # Counterfeit goods detected
    PRICE_ERROR = "price_error"  # Pricing error by merchant
    OTHER = "other"


class RefundStatus(str, Enum):
    REQUESTED = "requested"  # Customer submitted refund request
    AI_REVIEW = "ai_review"  # AI moderator reviewing
    PENDING_MERCHANT = "pending_merchant"  # Awaiting merchant response
    PENDING_EVIDENCE = "pending_evidence"  # Need more evidence
    APPROVED = "approved"  # Refund approved
    PARTIALLY_APPROVED = "partially_approved"  # Partial refund approved
    REJECTED = "rejected"  # Refund rejected
    ESCALATED = "escalated"  # Escalated to human moderator
    COMPLETED = "completed"  # Refund processed
    DISPUTED = "disputed"  # Merchant disputed the refund


class RefundMethod(str, Enum):
    ORIGINAL_PAYMENT = "original_payment"  # Refund to original payment method
    WALLET_CREDIT = "wallet_credit"  # Credit to iHhashi wallet
    BANK_TRANSFER = "bank_transfer"  # Direct bank transfer (ZAR)


class RefundEvidence(BaseModel):
    """Evidence submitted for refund claim"""
    evidence_id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    evidence_type: str  # "photo", "video", "receipt", "chat_log", "system_log"
    file_url: Optional[str] = None
    description: str
    submitted_by: str  # user_id
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    verified: bool = False
    ai_confidence: Optional[float] = None  # AI confidence score (0-1)


class RefundItem(BaseModel):
    """Individual item in a refund request"""
    order_item_id: str
    product_name: str
    quantity: int
    unit_price: float
    total_price: float
    refund_reason: RefundReason
    notes: Optional[str] = None


class Refund(BaseModel):
    """Refund request model"""
    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    
    # References
    order_id: str
    delivery_id: Optional[str] = None
    customer_id: str
    merchant_id: str
    
    # Refund details
    refund_items: List[RefundItem]
    total_refund_amount: float
    refund_reason: RefundReason
    customer_explanation: str
    
    # Status
    status: RefundStatus = RefundStatus.REQUESTED
    
    # Evidence
    evidence: List[RefundEvidence] = []
    
    # AI Moderation
    ai_decision: Optional[str] = None  # "approve", "reject", "escalate"
    ai_confidence: Optional[float] = None
    ai_reasoning: Optional[str] = None
    ai_flags: List[str] = []  # Risk flags detected by AI
    
    # Resolution
    approved_amount: Optional[float] = None
    refund_method: RefundMethod = RefundMethod.ORIGINAL_PAYMENT
    resolution_notes: Optional[str] = None
    resolved_by: Optional[str] = None  # user_id or "ai_moderator"
    resolved_at: Optional[datetime] = None
    
    # Timeline (SA CPA compliance: 10 business days for resolution)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    deadline: datetime  # 10 business days from creation
    
    # Merchant response
    merchant_response: Optional[str] = None
    merchant_response_at: Optional[datetime] = None
    merchant_evidence: List[RefundEvidence] = []
    
    # Escalation
    escalation_reason: Optional[str] = None
    escalated_to: Optional[str] = None  # human moderator id
    escalated_at: Optional[datetime] = None
    
    # CPA Compliance tracking
    cpa_section_applicable: Optional[str] = None  # e.g., "s56", "s20"
    consumer_rights_exercised: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "order_id": "order-123",
                "customer_id": "customer-456",
                "merchant_id": "merchant-789",
                "total_refund_amount": 250.00,
                "refund_reason": "defective_goods",
                "customer_explanation": "Food was cold and spoiled on arrival"
            }
        }


class RefundRequest(BaseModel):
    """Request to create a refund"""
    order_id: str
    delivery_id: Optional[str] = None
    refund_items: List[RefundItem]
    refund_reason: RefundReason
    customer_explanation: str
    evidence_urls: List[str] = []


# ============= DISPUTE MODELS =============

class DisputeStatus(str, Enum):
    OPENED = "opened"
    AI_INVESTIGATION = "ai_investigation"
    PENDING_RESPONSE = "pending_response"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    ESCALATED_EXTERNAL = "escalated_external"  # To Consumer Goods and Services Ombud (CGSO)
    CLOSED = "closed"


class DisputePriority(str, Enum):
    LOW = "low"  # Minor issues, easy resolution
    MEDIUM = "medium"  # Standard disputes
    HIGH = "high"  # Significant value or repeat issues
    URGENT = "urgent"  # Legal implications or media attention


class DisputeType(str, Enum):
    REFUND_DISPUTE = "refund_dispute"
    QUALITY_DISPUTE = "quality_dispute"
    DELIVERY_DISPUTE = "delivery_dispute"
    PAYMENT_DISPUTE = "payment_dispute"
    MERCHANT_CONDUCT = "merchant_conduct"
    RIDER_CONDUCT = "rider_conduct"
    FRAUD_ALLEGATION = "fraud_allegation"


class Dispute(BaseModel):
    """Dispute model for escalated issues"""
    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    
    # References
    refund_id: Optional[str] = None
    order_id: str
    delivery_id: Optional[str] = None
    customer_id: str
    merchant_id: Optional[str] = None
    rider_id: Optional[str] = None
    
    # Dispute details
    dispute_type: DisputeType
    priority: DisputePriority = DisputePriority.MEDIUM
    title: str
    description: str
    
    # Status
    status: DisputeStatus = DisputeStatus.OPENED
    
    # AI Analysis
    ai_summary: Optional[str] = None
    ai_recommendation: Optional[str] = None
    ai_confidence: Optional[float] = None
    similar_cases_found: int = 0
    
    # Timeline
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    resolution_deadline: datetime  # SA CPA: reasonable time (typically 20 business days)
    
    # Resolution
    resolution: Optional[str] = None
    resolution_type: Optional[str] = None  # "full_refund", "partial_refund", "replacement", "credit", "rejected"
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    
    # Parties involved
    assigned_moderator: Optional[str] = None
    
    # Communication log
    communications: List[Dict] = []  # {timestamp, from, to, message}
    
    # External escalation
    external_reference: Optional[str] = None  # CGSO case number, etc.
    external_status: Optional[str] = None
    
    # Compensation tracking
    compensation_amount: Optional[float] = None
    compensation_type: Optional[str] = None


class DisputeMessage(BaseModel):
    """Message in a dispute thread"""
    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    dispute_id: str
    sender_id: str
    sender_type: str  # "customer", "merchant", "rider", "moderator", "ai"
    message: str
    attachments: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_internal: bool = False  # Internal notes not visible to parties


# ============= AI MODERATION MODELS =============

class ModerationAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    ESCALATE = "escalate"
    REQUEST_INFO = "request_info"
    PARTIAL_REFUND = "partial_refund"


class ModerationDecision(BaseModel):
    """AI Moderator decision"""
    decision_id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    
    # Reference
    refund_id: Optional[str] = None
    dispute_id: Optional[str] = None
    
    # Decision
    action: ModerationAction
    confidence: float  # 0-1
    reasoning: str
    
    # Analysis
    evidence_analysis: Dict = {}
    policy_violations: List[str] = []
    risk_factors: List[str] = []
    similar_cases: List[str] = []  # IDs of similar past cases
    
    # CPA Compliance check
    cpa_sections_considered: List[str] = []
    consumer_rights_assessed: List[str] = []
    
    # Timestamp
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: Optional[int] = None
    
    # Human review
    human_override: bool = False
    override_reason: Optional[str] = None
    overridden_by: Optional[str] = None


class ModerationPolicy(BaseModel):
    """Policy rules for AI moderation"""
    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    name: str
    description: str
    policy_type: str  # "refund", "dispute", "quality", "delivery"
    rules: List[Dict]  # List of rule conditions and actions
    priority: int = 1  # Higher priority evaluated first
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # SA-specific compliance
    cpa_reference: Optional[str] = None  # e.g., "Section 56(2)"
    ecta_reference: Optional[str] = None  # e.g., "Section 42"


class ModerationAudit(BaseModel):
    """Audit trail for moderation decisions"""
    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    moderation_decision_id: str
    action_taken: str
    action_by: str  # user_id or "ai_moderator"
    previous_state: Dict
    new_state: Dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = None


# ============= RESPONSE MODELS =============

class RefundSummary(BaseModel):
    """Summary for customer/merchant dashboard"""
    total_refunds_requested: int
    total_refunds_approved: int
    total_refunds_rejected: int
    total_amount_refunded: float
    average_resolution_time_hours: float
    top_refund_reasons: List[Dict]
    satisfaction_rate: float


class DisputeSummary(BaseModel):
    """Summary for dashboard"""
    total_disputes: int
    open_disputes: int
    resolved_disputes: int
    escalated_disputes: int
    average_resolution_time_hours: float
    by_type: Dict[str, int]
    by_priority: Dict[str, int]
