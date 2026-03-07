# iHhashi AI Moderator - Implementation Plan

> AI-Powered Dispute Resolution for South African E-Commerce

---

## Executive Summary

Build an AI moderator that resolves refund disputes in minutes instead of days, while maintaining full legal compliance with South African Consumer Protection Act (CPA) and Electronic Communications and Transactions Act (ECTA).

**Target Metrics:**
- Resolution time: <5 minutes for AI-resolved cases (vs industry 7-14 days)
- Accuracy: >90% (measured by human review agreement)
- Customer satisfaction: >4.0/5.0
- Human escalation rate: <15%

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACES                          │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   Mobile App    │   Merchant      │   Moderator                 │
│   (Customer)    │   Dashboard     │   Dashboard                 │
└────────┬────────┴────────┬────────┴──────────────┬──────────────┘
         │                 │                       │
         ▼                 ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API GATEWAY (FastAPI)                       │
│  - Authentication/Authorization                                  │
│  - Rate Limiting                                                 │
│  - Request Validation                                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Refund Service  │ │ Evidence Svc    │ │ Mediation Svc   │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AI MODERATOR ENGINE                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Case      │  │   Legal     │  │   Decision              │  │
│  │   Analyzer  │──▶│   Engine    │──▶│   Generator            │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│         │                │                      │               │
│         ▼                ▼                      ▼               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              EVIDENCE ANALYZER                           │    │
│  │  - Image recognition (spoiled food, damage)             │    │
│  │  - Text analysis (chat logs, descriptions)              │    │
│  │  - Pattern matching (fraud detection)                   │    │
│  └─────────────────────────────────────────────────────────┘    │
└────────────────────────────┬────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│    MongoDB      │ │  Vector Store   │ │   Redis         │
│  (Case Data)    │ │  (Embeddings)   │ │  (Cache/Queue)  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## Phase 1: Core AI Moderator (Week 1-2)

### 1.1 Case Analyzer Module

**Purpose:** Analyze refund requests and extract structured information.

```python
# backend/app/services/ai_moderator/case_analyzer.py

from pydantic import BaseModel
from typing import Optional, List
import openai
from datetime import datetime

class CaseAnalysis(BaseModel):
    """Structured analysis of a refund case"""
    
    # Case categorization
    primary_issue: str  # defective, damaged, wrong_item, late, etc.
    severity: str  # low, medium, high, critical
    
    # Party analysis
    customer_fault_probability: float
    merchant_fault_probability: float
    rider_fault_probability: float
    
    # Evidence assessment
    evidence_quality: float  # 0-1
    evidence_gaps: List[str]
    recommended_additional_evidence: List[str]
    
    # Context
    similar_cases: List[str]  # Case IDs
    precedent_analysis: str
    
    # Flags
    fraud_indicators: List[str]
    requires_human_review: bool
    human_review_reasons: List[str]


async def analyze_case(
    order: dict,
    refund_request: dict,
    evidence: List[dict],
    customer_history: dict,
    merchant_history: dict
) -> CaseAnalysis:
    """
    Analyze a refund case using AI.
    
    Steps:
    1. Extract key information from order and refund request
    2. Analyze uploaded evidence (images, text)
    3. Check customer and merchant history
    4. Search for similar cases
    5. Generate structured analysis
    """
    
    # Build context for AI
    context = f"""
    ORDER DETAILS:
    - Order ID: {order['id']}
    - Items: {order['items']}
    - Total: R{order['total']}
    - Delivered: {order.get('delivered_at')}
    - Days since delivery: {(datetime.utcnow() - order.get('delivered_at', datetime.utcnow())).days}
    
    REFUND REQUEST:
    - Reason: {refund_request['reason_category']}
    - Description: {refund_request['reason_description']}
    - Amount requested: R{refund_request['amount']}
    
    EVIDENCE:
    {[e['description'] for e in evidence]}
    
    CUSTOMER HISTORY:
    - Total orders: {customer_history['total_orders']}
    - Previous refunds: {customer_history['refund_requests']}
    - Approval rate: {customer_history['refund_approval_rate']}
    
    MERCHANT HISTORY:
    - Complaint rate: {merchant_history['complaint_rate']}
    - Average rating: {merchant_history['average_rating']}
    """
    
    # Call AI for analysis
    response = await openai.ChatCompletion.acreate(
        model="gpt-4-turbo-preview",  # Or your preferred model
        messages=[
            {
                "role": "system",
                "content": """You are a refund case analyzer for iHhashi, a South African 
                delivery platform. Analyze cases objectively based on South African 
                Consumer Protection Act (CPA) and Electronic Communications and 
                Transactions Act (ECTA). Return structured JSON analysis."""
            },
            {
                "role": "user",
                "content": f"Analyze this refund case:\n\n{context}"
            }
        ],
        response_format={"type": "json_object"},
        temperature=0.1  # Low temperature for consistency
    )
    
    return CaseAnalysis.parse_raw(response.choices[0].message.content)
```

---

### 1.2 Legal Engine Module

**Purpose:** Determine legal eligibility and applicable consumer protection laws.

```python
# backend/app/services/ai_moderator/legal_engine.py

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List

class LegalBasis(Enum):
    """South African consumer protection legal bases"""
    CPA_SECTION_20 = "CPA_SECTION_20"  # Right to return goods
    CPA_SECTION_56 = "CPA_SECTION_56"  # Implied warranty (6 months)
    CPA_SECTION_61 = "CPA_SECTION_61"  # Damages from defective goods
    ECTA_SECTION_44 = "ECTA_SECTION_44"  # 7-day cooling off
    ECTA_SECTION_42 = "ECTA_SECTION_42"  # 30-day delivery failure
    COMPANY_POLICY = "COMPANY_POLICY"


class LegalEligibility(BaseModel):
    """Legal eligibility assessment"""
    
    eligible: bool
    primary_basis: Optional[LegalBasis]
    secondary_bases: List[LegalBasis] = []
    
    # Time-based checks
    within_cooling_off: bool  # ECTA 7-day
    within_warranty: bool  # CPA 6-month
    within_claim_window: bool  # CPA 10-day notification
    
    # Details
    days_since_delivery: int
    days_since_order: int
    delivery_failure: bool
    
    # Explanations
    explanation: str
    consumer_rights: List[str]
    merchant_obligations: List[str]


async def assess_legal_eligibility(
    order: dict,
    refund_request: dict
) -> LegalEligibility:
    """
    Assess legal eligibility for refund under South African law.
    
    Key Laws:
    - CPA Section 56: 6-month implied warranty for defective goods
    - CPA Section 20: Right to return goods not examined
    - ECTA Section 44: 7-day cooling-off for online purchases
    - ECTA Section 42: 30-day delivery guarantee
    """
    
    now = datetime.utcnow()
    ordered_at = order.get('ordered_at', now)
    delivered_at = order.get('delivered_at')
    
    # Calculate time deltas
    days_since_order = (now - ordered_at).days if ordered_at else 0
    days_since_delivery = (now - delivered_at).days if delivered_at else 0
    
    # Determine eligibility
    bases = []
    
    # ECTA Section 44: 7-day cooling off for online purchases
    within_cooling_off = days_since_delivery <= 7 if delivered_at else days_since_order <= 7
    if within_cooling_off:
        bases.append(LegalBasis.ECTA_SECTION_44)
    
    # CPA Section 56: 6-month warranty for defective goods
    within_warranty = days_since_delivery <= 180 if delivered_at else False
    if within_warranty and refund_request['reason_category'] in [
        'DEFECTIVE_PRODUCT', 'QUALITY_ISSUE', 'FOOD_SAFETY'
    ]:
        bases.append(LegalBasis.CPA_SECTION_56)
    
    # ECTA Section 42: 30-day delivery failure
    delivery_failure = (
        not delivered_at and 
        days_since_order > 30
    )
    if delivery_failure:
        bases.append(LegalBasis.ECTA_SECTION_42)
    
    # CPA Section 20: Goods not examined before purchase
    if refund_request['reason_category'] == 'NOT_AS_DESCRIBED':
        bases.append(LegalBasis.CPA_SECTION_20)
    
    # Determine primary basis
    primary = bases[0] if bases else None
    
    # Generate explanation
    explanation = generate_legal_explanation(
        primary_basis=primary,
        within_cooling_off=within_cooling_off,
        within_warranty=within_warranty,
        reason=refund_request['reason_category']
    )
    
    return LegalEligibility(
        eligible=len(bases) > 0,
        primary_basis=primary,
        secondary_bases=bases[1:],
        within_cooling_off=within_cooling_off,
        within_warranty=within_warranty,
        within_claim_window=days_since_delivery <= 10,
        days_since_delivery=days_since_delivery,
        days_since_order=days_since_order,
        delivery_failure=delivery_failure,
        explanation=explanation,
        consumer_rights=get_consumer_rights(primary),
        merchant_obligations=get_merchant_obligations(primary)
    )


def generate_legal_explanation(
    primary_basis: Optional[LegalBasis],
    within_cooling_off: bool,
    within_warranty: bool,
    reason: str
) -> str:
    """Generate human-readable legal explanation."""
    
    if primary_basis == LegalBasis.ECTA_SECTION_44:
        return (
            "Under Section 44 of the Electronic Communications and Transactions Act, "
            "you have a 7-day cooling-off period for online purchases. You are entitled "
            "to cancel this transaction and receive a full refund."
        )
    
    if primary_basis == LegalBasis.CPA_SECTION_56:
        return (
            "Under Section 56 of the Consumer Protection Act, all goods come with an "
            "implied warranty of quality. The goods must be suitable for their purpose, "
            "of good quality, and free of defects. As the product is defective, you are "
            "entitled to a refund, repair, or replacement at your choice."
        )
    
    if primary_basis == LegalBasis.ECTA_SECTION_42:
        return (
            "Under Section 42 of the Electronic Communications and Transactions Act, "
            "if goods are not delivered within 30 days, you may cancel the transaction "
            "and receive a full refund."
        )
    
    return "This claim will be reviewed based on company policy and fairness."
```

---

### 1.3 Evidence Analyzer Module

**Purpose:** Analyze uploaded evidence (images, text) to verify claims.

```python
# backend/app/services/ai_moderator/evidence_analyzer.py

import base64
from typing import List, Optional
from pydantic import BaseModel

class EvidenceAnalysis(BaseModel):
    """Analysis of evidence item"""
    evidence_id: str
    evidence_type: str
    
    # Verification
    authentic: bool
    authenticity_score: float  # 0-1
    tampering_detected: bool
    
    # Content analysis
    detected_issues: List[str]  # e.g., ["visible spoilage", "damaged packaging"]
    confidence: float
    
    # Correlation with claim
    supports_claim: bool
    contradicts_claim: bool
    relevance_score: float  # 0-1
    
    # Details
    description: str
    ai_notes: str


async def analyze_image_evidence(
    evidence_id: str,
    image_url: str,
    claim_description: str,
    expected_issues: List[str]  # What to look for based on claim
) -> EvidenceAnalysis:
    """
    Analyze image evidence using computer vision.
    
    Capabilities:
    - Detect spoilage in food items
    - Identify damaged packaging
    - Recognize wrong items
    - Check expiry dates
    - Assess product condition
    """
    
    # Download and encode image
    image_data = await download_image(image_url)
    image_base64 = base64.b64encode(image_data).decode()
    
    # Use vision model
    response = await openai.ChatCompletion.acreate(
        model="gpt-4-vision-preview",
        messages=[
            {
                "role": "system",
                "content": """You are an evidence analyzer for refund claims. 
                Analyze images objectively to verify or refute customer claims.
                Look for: product quality issues, damage, spoilage, wrong items, 
                expiry dates, and any discrepancies with the claim."""
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""Analyze this image as evidence for a refund claim.
                        
                        Claim: {claim_description}
                        
                        Look for these specific issues: {expected_issues}
                        
                        Return JSON with:
                        - detected_issues: list of issues found
                        - confidence: 0-1 confidence in findings
                        - supports_claim: does evidence support the claim
                        - description: detailed description of what you see
                        - notes: any additional observations"""
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ],
        max_tokens=500,
        temperature=0.1
    )
    
    result = parse_vision_response(response)
    
    return EvidenceAnalysis(
        evidence_id=evidence_id,
        evidence_type="IMAGE",
        authentic=True,  # Could add tampering detection
        authenticity_score=0.9,
        tampering_detected=False,
        detected_issues=result['detected_issues'],
        confidence=result['confidence'],
        supports_claim=result['supports_claim'],
        contradicts_claim=False,
        relevance_score=0.85,
        description=result['description'],
        ai_notes=result['notes']
    )


async def analyze_text_evidence(
    evidence_id: str,
    text_content: str,
    claim_description: str
) -> EvidenceAnalysis:
    """
    Analyze text evidence (chat logs, receipts, etc.).
    """
    
    response = await openai.ChatCompletion.acreate(
        model="gpt-4-turbo-preview",
        messages=[
            {
                "role": "system",
                "content": "Analyze text evidence for refund claims."
            },
            {
                "role": "user",
                "content": f"""Analyze this text as evidence for a refund claim.
                
                Claim: {claim_description}
                
                Text Evidence:
                {text_content}
                
                Does this support the claim? What relevant information does it contain?"""
            }
        ]
    )
    
    # Parse response and return analysis
    ...
```

---

### 1.4 Decision Generator Module

**Purpose:** Generate final decision with reasoning.

```python
# backend/app/services/ai_moderator/decision_generator.py

from typing import Optional
from enum import Enum
from pydantic import BaseModel

class DecisionAction(str, Enum):
    APPROVE_FULL = "APPROVE_FULL"
    APPROVE_PARTIAL = "APPROVE_PARTIAL"
    REJECT = "REJECT"
    REQUEST_MORE_INFO = "REQUEST_MORE_INFO"
    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"


class RefundDecision(BaseModel):
    """AI-generated refund decision"""
    
    action: DecisionAction
    amount: Optional[float]
    confidence: float  # 0-1
    
    # Reasoning
    primary_reason: str
    legal_basis: str
    evidence_summary: str
    
    # Communication
    customer_message: str
    merchant_message: str
    
    # Actions
    required_actions: List[str]
    
    # Flags
    requires_human_review: bool
    review_reasons: List[str]


async def generate_decision(
    case_analysis: CaseAnalysis,
    legal_eligibility: LegalEligibility,
    evidence_analyses: List[EvidenceAnalysis]
) -> RefundDecision:
    """
    Generate final decision based on all analyses.
    
    Decision Logic:
    1. Check legal eligibility first
    2. Evaluate evidence quality and support
    3. Consider customer/merchant history
    4. Apply confidence thresholds
    5. Determine if human review needed
    """
    
    # High confidence auto-approve conditions
    if legal_eligibility.within_cooling_off:
        return RefundDecision(
            action=DecisionAction.APPROVE_FULL,
            amount=case_analysis.order_total,
            confidence=0.95,
            primary_reason="Within ECTA 7-day cooling-off period",
            legal_basis="ECTA Section 44",
            evidence_summary="Not required for cooling-off refund",
            customer_message=generate_cooling_off_message(),
            merchant_message=generate_merchant_notification(),
            required_actions=["Process refund within 24 hours"],
            requires_human_review=False,
            review_reasons=[]
        )
    
    # Check evidence support
    evidence_support = sum(1 for e in evidence_analyses if e.supports_claim)
    evidence_count = len(evidence_analyses)
    
    # Defective product with good evidence
    if (
        legal_eligibility.within_warranty and
        evidence_support / max(evidence_count, 1) >= 0.5
    ):
        confidence = 0.7 + (evidence_support / evidence_count * 0.2)
        
        return RefundDecision(
            action=DecisionAction.APPROVE_FULL,
            amount=case_analysis.order_total,
            confidence=confidence,
            primary_reason="Defective product within CPA warranty period with supporting evidence",
            legal_basis="CPA Section 56",
            evidence_summary=f"{evidence_support}/{evidence_count} evidence items support claim",
            customer_message=generate_approval_message(),
            merchant_message=generate_merchant_notification(),
            required_actions=["Process refund", "Update inventory if return required"],
            requires_human_review=confidence < 0.8,
            review_reasons=["Confidence below auto-approve threshold"] if confidence < 0.8 else []
        )
    
    # Request more evidence if weak
    if evidence_count < 2 or evidence_support == 0:
        return RefundDecision(
            action=DecisionAction.REQUEST_MORE_INFO,
            amount=None,
            confidence=0.5,
            primary_reason="Insufficient evidence to determine claim validity",
            legal_basis="Pending investigation",
            evidence_summary="Need additional evidence to proceed",
            customer_message=generate_evidence_request_message(case_analysis.recommended_additional_evidence),
            merchant_message="Awaiting customer evidence",
            required_actions=["Request photos/videos from customer"],
            requires_human_review=False,
            review_reasons=[]
        )
    
    # Default: escalate to human
    return RefundDecision(
        action=DecisionAction.ESCALATE_TO_HUMAN,
        amount=None,
        confidence=0.4,
        primary_reason="Case complexity requires human review",
        legal_basis="Pending human review",
        evidence_summary="Mixed or inconclusive evidence",
        customer_message="Your case is being reviewed by our team. We'll update you within 24 hours.",
        merchant_message="Dispute escalated to human moderation.",
        required_actions=["Assign to human moderator"],
        requires_human_review=True,
        review_reasons=["Complex case", "Conflicting evidence", "Low confidence"]
    )
```

---

## Phase 2: AI Mediation Chat (Week 3-4)

### 2.1 Mediator Chat Module

```python
# backend/app/services/ai_moderator/chat_mediator.py

from typing import List, Optional
from datetime import datetime
import openai

class MediationContext(BaseModel):
    """Context for mediation session"""
    dispute_id: str
    customer_id: str
    merchant_id: str
    issue_summary: str
    legal_basis: Optional[str]
    previous_messages: List[dict]
    sentiment_history: List[dict]


class MediatorResponse(BaseModel):
    """AI mediator's response"""
    message: str
    action: Optional[str]  # propose_settlement, request_info, etc.
    settlement_proposal: Optional[dict]
    escalation_needed: bool
    escalation_reason: Optional[str]


async def generate_mediator_response(
    context: MediationContext,
    new_message: Optional[str] = None,
    sender_type: str = None  # CUSTOMER, MERCHANT
) -> MediatorResponse:
    """
    Generate AI mediator response in a dispute chat.
    
    Mediator Role:
    - Facilitate fair discussion
    - Explain relevant laws
    - Propose fair settlements
    - Detect escalation needs
    - Maintain professional tone
    """
    
    # Build conversation history
    history = format_conversation_history(context.previous_messages)
    
    # Build system prompt
    system_prompt = f"""You are an AI dispute mediator for iHhashi, a South African 
    delivery platform. Your role is to help customers and merchants resolve refund 
    disputes fairly and efficiently.

    DISPUTE CONTEXT:
    {context.issue_summary}
    
    LEGAL CONTEXT:
    {context.legal_basis or "To be determined"}

    SOUTH AFRICAN LAWS TO REFERENCE:
    - Consumer Protection Act (CPA) Section 56: 6-month implied warranty
    - Electronic Communications and Transactions Act (ECTA) Section 44: 7-day cooling-off
    - CPA Section 20: Right to return goods
    - CPA Section 61: Liability for defective goods

    MEDIATION GUIDELINES:
    1. Be neutral and fair to both parties
    2. Reference relevant laws when applicable
    3. Propose reasonable settlements
    4. De-escalate tension
    5. If parties cannot agree after reasonable attempts, suggest escalation
    6. Never take sides without clear evidence
    7. Keep responses concise (2-3 sentences)
    8. If settlement is reached, confirm details with both parties

    RESPONSE FORMAT:
    - Message: Your response to send
    - Action: Any special action (propose_settlement, request_info, escalate, close)
    - Settlement: If proposing, include amount and reasoning
    - Escalation: Recommend if parties cannot agree after 5+ exchanges
    """
    
    # Generate response
    user_message = f"[{sender_type}]: {new_message}" if new_message else "Start mediation"
    
    response = await openai.ChatCompletion.acreate(
        model="gpt-4-turbo-preview",
        messages=[
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": user_message}
        ],
        temperature=0.3,
        max_tokens=300
    )
    
    # Parse response
    content = response.choices[0].message.content
    
    return MediatorResponse(
        message=content,
        action=detect_action(content),
        settlement_proposal=extract_settlement(content),
        escalation_needed=detect_escalation_need(context.sentiment_history),
        escalation_reason="Parties unable to reach agreement"
    )


# Example conversation flow
"""
[MEDIATOR]: Hello! I'm the iHhashi AI Mediator. I'm here to help resolve this dispute 
about the spoiled milk. Let me review the details...

[CUSTOMER]: Yes, the milk was already spoiled when delivered. I want a full refund.

[MEDIATOR]: I understand your frustration. Under the Consumer Protection Act Section 56, 
you're entitled to a refund for defective goods. The evidence shows clear spoilage. 
I've reviewed QuickMart's response.

[MERCHANT]: The milk was fine when it left our store. It might have spoiled in transit.

[MEDIATOR]: Thank you for that context. The delivery was made within 2 hours, which 
shouldn't cause spoilage in properly stored dairy. However, I note this was on a hot day. 
A fair resolution might be to share the refund: 70% from merchant, 30% from delivery 
handling. Does this work for both parties?

[CUSTOMER]: I'd prefer full refund, but I can accept that.

[MERCHANT]: That's fair. We'll process the 70% portion.

[MEDIATOR]: Great! I'll record this agreement. Customer will receive R63 (70%) from 
QuickMart and R27 (30%) adjustment from iHhashi. Total refund: R90. Is this correct?

[CUSTOMER]: Yes, thank you.

[MEDIATOR]: Settlement confirmed. Refund will be processed within 24 hours. 
Thank you both for working this out fairly. Is there anything else?
"""
```

---

### 2.2 WebSocket Real-time Chat

```python
# backend/app/routes/websocket.py

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict
import json

class MediationConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str, user_id: str):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append({
            "websocket": websocket,
            "user_id": user_id
        })
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            self.active_connections[session_id] = [
                conn for conn in self.active_connections[session_id]
                if conn["websocket"] != websocket
            ]


manager = MediationConnectionManager()


@app.websocket("/ws/mediation/{session_id}")
async def mediation_websocket(
    websocket: WebSocket,
    session_id: str,
    token: str  # JWT token for auth
):
    """
    WebSocket endpoint for real-time mediation chat.
    
    Message Types:
    - user_message: From customer/merchant
    - mediator_response: From AI mediator
    - system_message: Status updates
    - settlement_proposed: AI proposes settlement
    - settlement_confirmed: Both parties agree
    """
    
    # Authenticate
    user = await verify_token(token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    
    await manager.connect(websocket, session_id, user.id)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "user_message":
                # Save message
                await save_message(session_id, user.id, message["content"])
                
                # Broadcast to other participants
                await broadcast_to_session(
                    session_id,
                    {
                        "type": "user_message",
                        "sender": user.id,
                        "content": message["content"],
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    exclude_user=user.id
                )
                
                # Generate AI mediator response
                context = await get_mediation_context(session_id)
                ai_response = await generate_mediator_response(
                    context=context,
                    new_message=message["content"],
                    sender_type=user.role
                )
                
                # Send AI response
                await broadcast_to_session(
                    session_id,
                    {
                        "type": "mediator_response",
                        "content": ai_response.message,
                        "action": ai_response.action,
                        "settlement_proposal": ai_response.settlement_proposal,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                
                if ai_response.escalation_needed:
                    await escalate_session(session_id)
            
            elif message["type"] == "accept_settlement":
                await process_settlement_agreement(
                    session_id,
                    user.id,
                    message["settlement_id"]
                )
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
```

---

## Phase 3: Integration & Testing (Week 5-6)

### 3.1 End-to-End Flow

```python
# backend/app/services/refund_service.py

async def process_refund_request(
    order_id: str,
    user_id: str,
    reason: str,
    amount: float,
    evidence_files: List[UploadFile]
) -> RefundResult:
    """
    Complete refund processing flow.
    
    Flow:
    1. Validate request
    2. Create refund record
    3. Store evidence
    4. Run AI analysis
    5. Generate decision
    6. Execute or escalate
    7. Notify parties
    """
    
    # 1. Validate
    order = await get_order(order_id)
    if not order or order.user_id != user_id:
        raise InvalidRequestError("Order not found or access denied")
    
    # 2. Create refund record
    refund = await create_refund(
        order_id=order_id,
        user_id=user_id,
        merchant_id=order.merchant_id,
        reason=reason,
        amount=amount
    )
    
    # 3. Store evidence
    evidence_records = []
    for file in evidence_files:
        evidence = await store_evidence(refund.id, file)
        evidence_records.append(evidence)
    
    # 4. AI Analysis
    case_analysis = await analyze_case(
        order=order,
        refund_request=refund,
        evidence=evidence_records,
        customer_history=await get_customer_history(user_id),
        merchant_history=await get_merchant_history(order.merchant_id)
    )
    
    # 5. Legal assessment
    legal_eligibility = await assess_legal_eligibility(order, refund)
    
    # 6. Evidence analysis
    evidence_analyses = []
    for evidence in evidence_records:
        if evidence.type == "PHOTO":
            analysis = await analyze_image_evidence(
                evidence.id,
                evidence.file_url,
                refund.reason_description,
                case_analysis.expected_issues
            )
            evidence_analyses.append(analysis)
    
    # 7. Generate decision
    decision = await generate_decision(
        case_analysis=case_analysis,
        legal_eligibility=legal_eligibility,
        evidence_analyses=evidence_analyses
    )
    
    # 8. Execute decision
    if decision.action == DecisionAction.APPROVE_FULL:
        await execute_refund(refund.id, amount)
        await notify_customer(refund.user_id, decision.customer_message)
        await notify_merchant(refund.merchant_id, decision.merchant_message)
    
    elif decision.action == DecisionAction.ESCALATE_TO_HUMAN:
        await escalate_to_moderator(refund.id, decision.review_reasons)
    
    # 9. Log decision
    await log_ai_decision(refund.id, decision, case_analysis)
    
    return RefundResult(
        refund_id=refund.id,
        status=refund.status,
        decision=decision,
        estimated_resolution=calculate_resolution_time(decision)
    )
```

---

### 3.2 Testing Strategy

```python
# backend/tests/test_ai_moderator.py

import pytest
from datetime import datetime, timedelta

class TestLegalEligibility:
    """Test legal eligibility assessment"""
    
    @pytest.mark.asyncio
    async def test_cooling_off_period(self):
        """Test ECTA 7-day cooling off"""
        order = {
            "ordered_at": datetime.utcnow() - timedelta(days=3),
            "delivered_at": datetime.utcnow() - timedelta(days=2)
        }
        refund = {"reason_category": "UNSATISFIED"}
        
        eligibility = await assess_legal_eligibility(order, refund)
        
        assert eligibility.eligible == True
        assert eligibility.primary_basis == LegalBasis.ECTA_SECTION_44
        assert eligibility.within_cooling_off == True
    
    @pytest.mark.asyncio
    async def test_warranty_claim(self):
        """Test CPA 6-month warranty"""
        order = {
            "ordered_at": datetime.utcnow() - timedelta(days=30),
            "delivered_at": datetime.utcnow() - timedelta(days=28)
        }
        refund = {"reason_category": "DEFECTIVE_PRODUCT"}
        
        eligibility = await assess_legal_eligibility(order, refund)
        
        assert eligibility.eligible == True
        assert LegalBasis.CPA_SECTION_56 in [eligibility.primary_basis] + eligibility.secondary_bases


class TestEvidenceAnalysis:
    """Test evidence analysis"""
    
    @pytest.mark.asyncio
    async def test_spoiled_food_detection(self):
        """Test AI can detect spoiled food in image"""
        analysis = await analyze_image_evidence(
            evidence_id="test_1",
            image_url="test_spoiled_milk.jpg",
            claim_description="Milk was spoiled when delivered",
            expected_issues=["spoilage", "curdling", "off-color"]
        )
        
        assert "spoilage" in analysis.detected_issues or "curdling" in analysis.detected_issues
        assert analysis.supports_claim == True
    
    @pytest.mark.asyncio
    async def test_authenticity_check(self):
        """Test AI can detect tampered evidence"""
        analysis = await analyze_image_evidence(
            evidence_id="test_2",
            image_url="test_edited_image.jpg",
            claim_description="Item was damaged",
            expected_issues=["damage"]
        )
        
        # Should flag if tampering detected
        if analysis.tampering_detected:
            assert analysis.authenticity_score < 0.5


class TestDecisionGeneration:
    """Test decision generation"""
    
    @pytest.mark.asyncio
    async def test_auto_approve_cooling_off(self):
        """Test auto-approve within cooling-off"""
        case = CaseAnalysis(
            primary_issue="unwanted",
            severity="low",
            customer_fault_probability=0.0,
            merchant_fault_probability=0.0,
            rider_fault_probability=0.0,
            evidence_quality=0.5,
            evidence_gaps=[],
            recommended_additional_evidence=[],
            similar_cases=[],
            precedent_analysis="Standard cooling-off case",
            fraud_indicators=[],
            requires_human_review=False,
            human_review_reasons=[]
        )
        
        legal = LegalEligibility(
            eligible=True,
            primary_basis=LegalBasis.ECTA_SECTION_44,
            within_cooling_off=True,
            within_warranty=True,
            within_claim_window=True,
            days_since_delivery=2,
            days_since_order=3,
            delivery_failure=False
        )
        
        decision = await generate_decision(case, legal, [])
        
        assert decision.action == DecisionAction.APPROVE_FULL
        assert decision.confidence >= 0.9
        assert decision.requires_human_review == False


class TestMediatorChat:
    """Test mediation chat"""
    
    @pytest.mark.asyncio
    async def test_settlement_proposal(self):
        """Test AI can propose fair settlement"""
        context = MediationContext(
            dispute_id="disp_1",
            customer_id="cust_1",
            merchant_id="merch_1",
            issue_summary="Customer claims late delivery caused food to be cold",
            legal_basis="CPA Section 56 - quality",
            previous_messages=[
                {"sender": "CUSTOMER", "content": "Food was cold when delivered"},
                {"sender": "MERCHANT", "content": "We prepared it fresh, delivery took long"}
            ],
            sentiment_history=[]
        )
        
        response = await generate_mediator_response(context)
        
        assert response.message is not None
        assert len(response.message) > 0
        # Should propose some settlement or resolution path
```

---

## Phase 4: Monitoring & Improvement (Week 7+)

### 4.1 Metrics Dashboard

```python
# backend/app/routes/analytics.py

@app.get("/analytics/ai-moderator")
async def get_ai_moderator_metrics(
    period: str = "week"
) -> AIModeratorMetrics:
    """
    AI Moderator performance metrics.
    
    Key Metrics:
    - Decision accuracy (human agreement rate)
    - Resolution time distribution
    - Escalation rate
    - Customer satisfaction
    - Fraud detection rate
    """
    
    return AIModeratorMetrics(
        total_decisions=1250,
        auto_approved=980,
        auto_rejected=120,
        escalated=150,
        
        accuracy={
            "overall": 0.94,
            "by_confidence": {
                "high": 0.97,
                "medium": 0.89,
                "low": 0.72
            }
        },
        
        resolution_time={
            "mean_minutes": 4.2,
            "median_minutes": 2.1,
            "p95_minutes": 15.3
        },
        
        customer_satisfaction={
            "overall": 4.2,
            "auto_resolved": 4.4,
            "escalated": 3.8
        },
        
        fraud_detection={
            "flagged": 25,
            "confirmed": 18,
            "prevented_loss_zar": 45000
        }
    )
```

---

## Implementation Checklist

### Week 1-2: Core Engine
- [ ] Set up database collections
- [ ] Implement Case Analyzer module
- [ ] Implement Legal Engine module
- [ ] Implement Evidence Analyzer module
- [ ] Implement Decision Generator module
- [ ] Create API endpoints
- [ ] Write unit tests

### Week 3-4: Mediation Chat
- [ ] Implement Mediator Chat module
- [ ] Set up WebSocket server
- [ ] Build chat UI components
- [ ] Integrate sentiment analysis
- [ ] Test real-time communication

### Week 5-6: Integration
- [ ] Connect to order system
- [ ] Connect to payment system
- [ ] Implement notification system
- [ ] Build customer-facing refund flow
- [ ] Build merchant response dashboard
- [ ] Build moderator dashboard

### Week 7+: Optimization
- [ ] Set up monitoring
- [ ] Create feedback loop
- [ ] Train model on decisions
- [ ] A/B test decision thresholds
- [ ] Improve fraud detection

---

## Cost Estimates

| Component | Monthly Cost |
|-----------|--------------|
| OpenAI GPT-4 API | R5,000 - R15,000 |
| OpenAI Vision API | R2,000 - R5,000 |
| Vector Database (Pinecone) | R1,500 |
| Redis Cache | R500 |
| **Total** | **R9,000 - R22,000** |

Cost optimization strategies:
- Use GPT-3.5 for simple cases
- Cache frequent patterns
- Batch similar cases
- Fine-tune smaller model for common decisions

---

## Legal Compliance Notes

1. **CPA Section 56** - All goods have implied 6-month warranty
2. **ECTA Section 44** - 7-day cooling-off for online purchases
3. **ECTA Section 42** - 30-day delivery guarantee
4. **Record Keeping** - 5-year retention for all decisions
5. **Appeals Process** - 7-day window for customer appeals
6. **Human Review** - Available for all AI decisions on request

---

## Success Metrics

| Metric | Target | Industry Average |
|--------|--------|------------------|
| Resolution Time | <5 min | 7-14 days |
| AI Accuracy | >90% | N/A |
| Customer Satisfaction | >4.0 | 3.5 |
| Human Escalation | <15% | 100% |
| Fraud Detection | >70% | 40-50% |
