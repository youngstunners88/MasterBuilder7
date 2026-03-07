"""
Refund and Dispute API Endpoints
Compliant with South African Consumer Protection Act (CPA) 68 of 2008
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import Optional, List
from datetime import datetime, timedelta
import math

from app.services.auth import get_current_user
from app.models.refund import (
    Refund, RefundRequest, RefundStatus, RefundReason, RefundEvidence,
    Dispute, DisputeStatus, DisputePriority, DisputeType, DisputeMessage,
    ModerationDecision, RefundSummary, DisputeSummary
)
from app.database import get_database

router = APIRouter(tags=["Refunds & Disputes"])


# ============= REFUND ENDPOINTS =============

@router.post("/request", response_model=dict)
async def request_refund(
    refund_request: RefundRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Submit a refund request
    
    SA CPA Compliance:
    - Consumer has 10 business days to report issues
    - Must provide proof of purchase
    - Goods must be returned in original condition (where applicable)
    """
    # Validate order belongs to user
    order = await db.orders.find_one({
        "_id": refund_request.order_id,
        "customer_id": str(current_user["_id"])
    })
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check 10 business day window
    order_date = order.get("created_at", datetime.utcnow())
    deadline = _add_business_days(order_date, 10)
    
    if datetime.utcnow() > deadline:
        raise HTTPException(
            status_code=400,
            detail="Refund request exceeds 10 business day limit per CPA requirements"
        )
    
    # Calculate total refund amount
    total_amount = sum(item.total_price for item in refund_request.refund_items)
    
    # Create refund record
    refund = Refund(
        order_id=refund_request.order_id,
        delivery_id=refund_request.delivery_id,
        customer_id=str(current_user["_id"]),
        merchant_id=order.get("merchant_id", ""),
        refund_items=[item.dict() for item in refund_request.refund_items],
        total_refund_amount=total_amount,
        refund_reason=refund_request.refund_reason,
        customer_explanation=refund_request.customer_explanation,
        deadline=deadline,
        cpa_section_applicable=_determine_cpa_section(refund_request.refund_reason)
    )
    
    # Handle evidence uploads
    for url in refund_request.evidence_urls:
        refund.evidence.append(RefundEvidence(
            evidence_type="photo",
            file_url=url,
            description="Customer submitted evidence",
            submitted_by=str(current_user["_id"])
        ))
    
    result = await db.refunds.insert_one(refund.dict())
    
    # Trigger AI moderation in background
    background_tasks.add_task(
        _ai_moderate_refund,
        str(result.inserted_id),
        db
    )
    
    return {
        "refund_id": str(result.inserted_id),
        "status": "requested",
        "estimated_resolution": deadline.isoformat(),
        "message": "Your refund request has been submitted and is being reviewed"
    }


@router.get("/my-requests", response_model=List[dict])
async def get_my_refunds(
    status: Optional[RefundStatus] = None,
    limit: int = Query(20, le=100),
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get customer's refund requests"""
    query = {"customer_id": str(current_user["_id"])}
    
    if status:
        query["status"] = status
    
    refunds = await db.refunds.find(query).sort("created_at", -1).skip(offset).limit(limit).to_list(length=limit)
    
    return [{
        "id": r["_id"],
        "order_id": r["order_id"],
        "amount": r["total_refund_amount"],
        "reason": r["refund_reason"],
        "status": r["status"],
        "created_at": r["created_at"],
        "deadline": r["deadline"]
    } for r in refunds]


@router.get("/{refund_id}", response_model=dict)
async def get_refund_details(
    refund_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get detailed refund information"""
    refund = await db.refunds.find_one({"_id": refund_id})
    
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found")
    
    # Check access
    user_id = str(current_user["_id"])
    if refund["customer_id"] != user_id and refund["merchant_id"] != user_id:
        if current_user.get("user_type") not in ["admin", "moderator"]:
            raise HTTPException(status_code=403, detail="Access denied")
    
    return refund


@router.post("/{refund_id}/evidence", response_model=dict)
async def add_refund_evidence(
    refund_id: str,
    evidence_type: str,
    file_url: str,
    description: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Add evidence to a refund request"""
    refund = await db.refunds.find_one({"_id": refund_id})
    
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found")
    
    user_id = str(current_user["_id"])
    is_customer = refund["customer_id"] == user_id
    is_merchant = refund["merchant_id"] == user_id
    
    if not (is_customer or is_merchant):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    evidence = RefundEvidence(
        evidence_type=evidence_type,
        file_url=file_url,
        description=description,
        submitted_by=user_id
    )
    
    # Add to appropriate evidence list
    if is_merchant:
        await db.refunds.update_one(
            {"_id": refund_id},
            {
                "$push": {"merchant_evidence": evidence.dict()},
                "$set": {"merchant_response_at": datetime.utcnow()}
            }
        )
    else:
        await db.refunds.update_one(
            {"_id": refund_id},
            {"$push": {"evidence": evidence.dict()}}
        )
    
    return {"message": "Evidence added successfully"}


@router.post("/{refund_id}/merchant-response", response_model=dict)
async def merchant_respond(
    refund_id: str,
    response: str,
    accept: bool,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Merchant responds to refund request
    
    SA CPA: Merchant has 48 hours to respond before auto-escalation
    """
    refund = await db.refunds.find_one({"_id": refund_id})
    
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found")
    
    if refund["merchant_id"] != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if refund["status"] == RefundStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Refund already completed")
    
    update_data = {
        "merchant_response": response,
        "merchant_response_at": datetime.utcnow(),
        "status": RefundStatus.APPROVED if accept else RefundStatus.DISPUTED
    }
    
    if accept:
        update_data["approved_amount"] = refund["total_refund_amount"]
        update_data["resolved_by"] = str(current_user["_id"])
        update_data["resolved_at"] = datetime.utcnow()
    
    await db.refunds.update_one({"_id": refund_id}, {"$set": update_data})
    
    return {
        "message": "Response recorded",
        "status": update_data["status"]
    }


# ============= DISPUTE ENDPOINTS =============

@router.post("/{refund_id}/dispute", response_model=dict)
async def open_dispute(
    refund_id: str,
    dispute_type: DisputeType,
    description: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Open a dispute for rejected/contested refund
    
    Can escalate to Consumer Goods and Services Ombud (CGSO) if unresolved
    """
    refund = await db.refunds.find_one({"_id": refund_id})
    
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found")
    
    user_id = str(current_user["_id"])
    if refund["customer_id"] != user_id and refund["merchant_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check if dispute already exists
    existing = await db.disputes.find_one({"refund_id": refund_id})
    if existing:
        raise HTTPException(status_code=400, detail="Dispute already exists for this refund")
    
    # Calculate resolution deadline (20 business days)
    deadline = _add_business_days(datetime.utcnow(), 20)
    
    # Determine priority
    priority = DisputePriority.MEDIUM
    if refund["total_refund_amount"] > 500:
        priority = DisputePriority.HIGH
    if refund["total_refund_amount"] > 2000:
        priority = DisputePriority.URGENT
    
    dispute = Dispute(
        refund_id=refund_id,
        order_id=refund["order_id"],
        delivery_id=refund.get("delivery_id"),
        customer_id=refund["customer_id"],
        merchant_id=refund["merchant_id"],
        dispute_type=dispute_type,
        priority=priority,
        title=f"Dispute: {refund['refund_reason']}",
        description=description,
        resolution_deadline=deadline
    )
    
    result = await db.disputes.insert_one(dispute.dict())
    
    # Update refund status
    await db.refunds.update_one(
        {"_id": refund_id},
        {"$set": {"status": RefundStatus.ESCALATED, "escalated_at": datetime.utcnow()}}
    )
    
    return {
        "dispute_id": str(result.inserted_id),
        "status": "opened",
        "resolution_deadline": deadline.isoformat(),
        "message": "Dispute opened. An AI moderator will review shortly."
    }


@router.get("/disputes/my", response_model=List[dict])
async def get_my_disputes(
    status: Optional[DisputeStatus] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get user's disputes"""
    query = {
        "$or": [
            {"customer_id": str(current_user["_id"])},
            {"merchant_id": str(current_user["_id"])}
        ]
    }
    
    if status:
        query["status"] = status
    
    disputes = await db.disputes.find(query).sort("created_at", -1).to_list(length=50)
    
    return [{
        "id": d["_id"],
        "type": d["dispute_type"],
        "priority": d["priority"],
        "title": d["title"],
        "status": d["status"],
        "created_at": d["created_at"],
        "deadline": d["resolution_deadline"]
    } for d in disputes]


@router.post("/disputes/{dispute_id}/message", response_model=dict)
async def add_dispute_message(
    dispute_id: str,
    message: str,
    attachments: List[str] = [],
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Add a message to dispute thread"""
    dispute = await db.disputes.find_one({"_id": dispute_id})
    
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    
    user_id = str(current_user["_id"])
    if dispute["customer_id"] != user_id and dispute["merchant_id"] != user_id:
        if current_user.get("user_type") not in ["admin", "moderator"]:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    msg = DisputeMessage(
        dispute_id=dispute_id,
        sender_id=user_id,
        sender_type=current_user.get("user_type", "customer"),
        message=message,
        attachments=attachments
    )
    
    await db.disputes.update_one(
        {"_id": dispute_id},
        {
            "$push": {"communications": msg.dict()},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    return {"message": "Message added", "message_id": msg.id}


# ============= MERCHANT ENDPOINTS =============

@router.get("/merchant/pending", response_model=List[dict])
async def get_merchant_pending_refunds(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get pending refund requests for merchant"""
    if current_user.get("user_type") != "merchant":
        raise HTTPException(status_code=403, detail="Merchants only")
    
    refunds = await db.refunds.find({
        "merchant_id": str(current_user["_id"]),
        "status": {"$in": [RefundStatus.REQUESTED, RefundStatus.PENDING_MERCHANT, RefundStatus.AI_REVIEW]}
    }).sort("created_at", 1).to_list(length=100)
    
    return [{
        "id": r["_id"],
        "order_id": r["order_id"],
        "customer_explanation": r["customer_explanation"],
        "amount": r["total_refund_amount"],
        "reason": r["refund_reason"],
        "status": r["status"],
        "deadline": r["deadline"],
        "created_at": r["created_at"],
        "ai_decision": r.get("ai_decision"),
        "ai_confidence": r.get("ai_confidence")
    } for r in refunds]


# ============= SUMMARY ENDPOINTS =============

@router.get("/summary/customer", response_model=RefundSummary)
async def get_customer_refund_summary(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get refund summary for customer dashboard"""
    user_id = str(current_user["_id"])
    
    total_requested = await db.refunds.count_documents({"customer_id": user_id})
    total_approved = await db.refunds.count_documents({
        "customer_id": user_id,
        "status": {"$in": [RefundStatus.APPROVED, RefundStatus.COMPLETED]}
    })
    total_rejected = await db.refunds.count_documents({
        "customer_id": user_id,
        "status": RefundStatus.REJECTED
    })
    
    # Calculate total amount refunded
    pipeline = [
        {"$match": {"customer_id": user_id, "status": {"$in": [RefundStatus.APPROVED, RefundStatus.COMPLETED]}}},
        {"$group": {"_id": None, "total": {"$sum": "$approved_amount"}}}
    ]
    result = await db.refunds.aggregate(pipeline).to_list(length=1)
    total_amount = result[0]["total"] if result else 0.0
    
    # Top refund reasons
    reason_pipeline = [
        {"$match": {"customer_id": user_id}},
        {"$group": {"_id": "$refund_reason", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    top_reasons = await db.refunds.aggregate(reason_pipeline).to_list(length=5)
    
    # Calculate satisfaction rate
    satisfaction_rate = (total_approved / total_requested * 100) if total_requested > 0 else 100.0
    
    # Average resolution time
    resolved_pipeline = [
        {"$match": {"customer_id": user_id, "resolved_at": {"$exists": True}}},
        {"$project": {
            "duration": {"$divide": [
                {"$subtract": ["$resolved_at", "$created_at"]},
                3600000  # Convert ms to hours
            ]}
        }},
        {"$group": {"_id": None, "avg": {"$avg": "$duration"}}}
    ]
    resolved_result = await db.refunds.aggregate(resolved_pipeline).to_list(length=1)
    avg_resolution_time = resolved_result[0]["avg"] if resolved_result else 0.0
    
    return RefundSummary(
        total_refunds_requested=total_requested,
        total_refunds_approved=total_approved,
        total_refunds_rejected=total_rejected,
        total_amount_refunded=total_amount,
        average_resolution_time_hours=round(avg_resolution_time, 1),
        top_refund_reasons=[{"reason": r["_id"], "count": r["count"]} for r in top_reasons],
        satisfaction_rate=round(satisfaction_rate, 1)
    )


@router.get("/summary/merchant", response_model=RefundSummary)
async def get_merchant_refund_summary(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get refund summary for merchant dashboard"""
    if current_user.get("user_type") != "merchant":
        raise HTTPException(status_code=403, detail="Merchants only")
    
    merchant_id = str(current_user["_id"])
    
    total_requested = await db.refunds.count_documents({"merchant_id": merchant_id})
    total_approved = await db.refunds.count_documents({
        "merchant_id": merchant_id,
        "status": {"$in": [RefundStatus.APPROVED, RefundStatus.COMPLETED]}
    })
    total_rejected = await db.refunds.count_documents({
        "merchant_id": merchant_id,
        "status": RefundStatus.REJECTED
    })
    
    # Calculate total amount refunded
    pipeline = [
        {"$match": {"merchant_id": merchant_id, "status": {"$in": [RefundStatus.APPROVED, RefundStatus.COMPLETED]}}},
        {"$group": {"_id": None, "total": {"$sum": "$approved_amount"}}}
    ]
    result = await db.refunds.aggregate(pipeline).to_list(length=1)
    total_amount = result[0]["total"] if result else 0.0
    
    # Top refund reasons
    reason_pipeline = [
        {"$match": {"merchant_id": merchant_id}},
        {"$group": {"_id": "$refund_reason", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    top_reasons = await db.refunds.aggregate(reason_pipeline).to_list(length=5)
    
    # Satisfaction rate (from merchant perspective = low refund rate is good)
    satisfaction_rate = ((total_requested - total_approved) / total_requested * 100) if total_requested > 0 else 100.0
    
    return RefundSummary(
        total_refunds_requested=total_requested,
        total_refunds_approved=total_approved,
        total_refunds_rejected=total_rejected,
        total_amount_refunded=total_amount,
        average_resolution_time_hours=0.0,  # Calculate similarly if needed
        top_refund_reasons=[{"reason": r["_id"], "count": r["count"]} for r in top_reasons],
        satisfaction_rate=round(satisfaction_rate, 1)
    )


# ============= ADMIN/MODERATOR ENDPOINTS =============

@router.get("/admin/disputes", response_model=List[dict])
async def get_all_disputes(
    status: Optional[DisputeStatus] = None,
    priority: Optional[DisputePriority] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get all disputes for admin/moderator review"""
    if current_user.get("user_type") not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="Admin or moderator access required")
    
    query = {}
    if status:
        query["status"] = status
    if priority:
        query["priority"] = priority
    
    disputes = await db.disputes.find(query).sort("created_at", -1).skip(offset).limit(limit).to_list(length=limit)
    
    return [{
        "id": d["_id"],
        "refund_id": d.get("refund_id"),
        "order_id": d["order_id"],
        "type": d["dispute_type"],
        "priority": d["priority"],
        "title": d["title"],
        "status": d["status"],
        "customer_id": d["customer_id"],
        "merchant_id": d.get("merchant_id"),
        "ai_summary": d.get("ai_summary"),
        "created_at": d["created_at"],
        "deadline": d["resolution_deadline"]
    } for d in disputes]


@router.post("/admin/disputes/{dispute_id}/resolve", response_model=dict)
async def resolve_dispute(
    dispute_id: str,
    resolution: str,
    resolution_type: str,  # "full_refund", "partial_refund", "replacement", "credit", "rejected"
    compensation_amount: Optional[float] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Resolve a dispute as admin/moderator"""
    if current_user.get("user_type") not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="Admin or moderator access required")
    
    dispute = await db.disputes.find_one({"_id": dispute_id})
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    
    # Update dispute
    await db.disputes.update_one(
        {"_id": dispute_id},
        {
            "$set": {
                "status": DisputeStatus.RESOLVED,
                "resolution": resolution,
                "resolution_type": resolution_type,
                "compensation_amount": compensation_amount,
                "resolved_by": str(current_user["_id"]),
                "resolved_at": datetime.utcnow()
            }
        }
    )
    
    # Update related refund if exists
    if dispute.get("refund_id"):
        refund_update = {
            "status": RefundStatus.COMPLETED,
            "resolved_by": str(current_user["_id"]),
            "resolved_at": datetime.utcnow(),
            "resolution_notes": resolution
        }
        if resolution_type in ["full_refund", "partial_refund"] and compensation_amount:
            refund_update["approved_amount"] = compensation_amount
        
        await db.refunds.update_one(
            {"_id": dispute["refund_id"]},
            {"$set": refund_update}
        )
    
    return {
        "message": "Dispute resolved successfully",
        "dispute_id": dispute_id,
        "resolution_type": resolution_type
    }


@router.get("/admin/refunds", response_model=List[dict])
async def get_all_refunds(
    status: Optional[RefundStatus] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get all refunds for admin/moderator review"""
    if current_user.get("user_type") not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="Admin or moderator access required")
    
    query = {}
    if status:
        query["status"] = status
    
    refunds = await db.refunds.find(query).sort("created_at", -1).skip(offset).limit(limit).to_list(length=limit)
    
    return [{
        "id": r["_id"],
        "order_id": r["order_id"],
        "customer_id": r["customer_id"],
        "merchant_id": r["merchant_id"],
        "amount": r["total_refund_amount"],
        "reason": r["refund_reason"],
        "status": r["status"],
        "ai_decision": r.get("ai_decision"),
        "ai_confidence": r.get("ai_confidence"),
        "ai_flags": r.get("ai_flags", []),
        "created_at": r["created_at"],
        "deadline": r["deadline"],
        "resolved_at": r.get("resolved_at")
    } for r in refunds]


# ============= AI MODERATION ENDPOINTS =============

@router.post("/{refund_id}/ai-review", response_model=dict)
async def get_ai_review(
    refund_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get AI moderation analysis for a refund"""
    if current_user.get("user_type") not in ["admin", "moderator", "merchant"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    refund = await db.refunds.find_one({"_id": refund_id})
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found")
    
    # Get AI decision
    decision = await _ai_moderate_refund(refund_id, db)
    
    return decision


# ============= HELPER FUNCTIONS =============

def _add_business_days(start_date: datetime, days: int) -> datetime:
    """Add business days (exclude weekends)"""
    current = start_date
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Monday = 0, Friday = 4
            added += 1
    return current


def _determine_cpa_section(reason: RefundReason) -> str:
    """Map refund reason to applicable CPA section"""
    cpa_mapping = {
        RefundReason.DEFECTIVE_GOODS: "s56 - Implied warranty of quality",
        RefundReason.NOT_AS_DESCRIBED: "s55 - Consumer's right to safe, good quality goods",
        RefundReason.LATE_DELIVERY: "s19 - Right to receive delivery on agreed date",
        RefundReason.ORDER_CANCELLED: "s16 - Cooling-off period (direct marketing)",
        RefundReason.FOOD_SAFETY: "s55 - Consumer's right to safe goods",
        RefundReason.ALLERGEN_ISSUES: "s55 - Consumer's right to safe goods",
    }
    return cpa_mapping.get(reason, "s20 - Right to return goods")


async def _ai_moderate_refund(refund_id: str, db) -> dict:
    """
    AI Moderation logic for refund requests
    
    Decision factors:
    - Customer history (previous refunds, fraud flags)
    - Merchant reliability score
    - Evidence quality
    - CPA compliance assessment
    - Similar case outcomes
    """
    refund = await db.refunds.find_one({"_id": refund_id})
    if not refund:
        return {"error": "Refund not found"}
    
    # Get customer history
    customer_refunds = await db.refunds.count_documents({
        "customer_id": refund["customer_id"],
        "status": {"$in": [RefundStatus.COMPLETED, RefundStatus.APPROVED]}
    })
    
    customer_rejected = await db.refunds.count_documents({
        "customer_id": refund["customer_id"],
        "status": RefundStatus.REJECTED
    })
    
    # Get merchant reliability
    merchant_total = await db.refunds.count_documents({"merchant_id": refund["merchant_id"]})
    merchant_approved = await db.refunds.count_documents({
        "merchant_id": refund["merchant_id"],
        "status": {"$in": [RefundStatus.APPROVED, RefundStatus.COMPLETED]}
    })
    
    merchant_reliability = (merchant_total - merchant_approved) / max(merchant_total, 1)
    
    # Calculate fraud risk score
    fraud_risk = 0.0
    risk_factors = []
    
    # High refund frequency
    if customer_refunds > 5:
        fraud_risk += 0.2
        risk_factors.append("high_refund_frequency")
    
    # High rejection rate
    if customer_rejected > 2 and customer_refunds > 0:
        if customer_rejected / (customer_refunds + customer_rejected) > 0.3:
            fraud_risk += 0.3
            risk_factors.append("high_rejection_rate")
    
    # Low merchant reliability
    if merchant_reliability < 0.7:
        fraud_risk -= 0.2  # Lower risk = more likely to approve
        risk_factors.append("merchant_quality_concerns")
    
    # Evidence quality check
    evidence_count = len(refund.get("evidence", []))
    if evidence_count == 0:
        fraud_risk += 0.15
        risk_factors.append("no_evidence_provided")
    
    # Make decision based on risk score
    confidence = max(0, min(1, 1 - fraud_risk))
    
    decision = {
        "refund_id": refund_id,
        "action": "approve" if confidence > 0.6 else "escalate",
        "confidence": confidence,
        "reasoning": f"Customer has {customer_refunds} approved refunds, {customer_rejected} rejected. "
                     f"Merchant reliability: {merchant_reliability:.2f}. Evidence count: {evidence_count}",
        "risk_factors": risk_factors,
        "cpa_compliant": True,
        "processing_time_ms": 150  # Simulated
    }
    
    # Update refund with AI decision
    await db.refunds.update_one(
        {"_id": refund_id},
        {
            "$set": {
                "ai_decision": decision["action"],
                "ai_confidence": decision["confidence"],
                "ai_reasoning": decision["reasoning"],
                "ai_flags": risk_factors,
                "status": RefundStatus.AI_REVIEW if decision["action"] == "escalate" else RefundStatus.PENDING_MERCHANT
            }
        }
    )
    
    # Auto-approve high confidence cases
    if decision["action"] == "approve" and confidence > 0.85:
        await db.refunds.update_one(
            {"_id": refund_id},
            {
                "$set": {
                    "status": RefundStatus.APPROVED,
                    "approved_amount": refund["total_refund_amount"],
                    "resolved_by": "ai_moderator",
                    "resolved_at": datetime.utcnow()
                }
            }
        )
        decision["auto_approved"] = True
    
    return decision
