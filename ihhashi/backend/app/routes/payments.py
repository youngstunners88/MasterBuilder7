"""
Payment API routes for Paystack integration - Full implementation
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid
import hashlib
import hmac
import json
from pymongo.errors import DuplicateKeyError
import logging
from datetime import timezone

from app.services.auth import get_current_user
from app.services.paystack import PaystackService, SA_BANK_CODES
from app.config import settings
from app.database import get_collection
from app.models import User, UserRole
from app.utils.validation import safe_object_id

router = APIRouter(prefix="/payments", tags=["payments"])

logger = logging.getLogger(__name__)


# ============ MODELS ============

class PaymentInitialize(BaseModel):
    """Payment initialization request"""
    email: EmailStr
    amount: float = Field(..., gt=0, description="Amount in ZAR")
    order_id: Optional[str] = None
    callback_url: Optional[str] = None


class PaymentVerify(BaseModel):
    """Payment verification request"""
    reference: str


class PayoutRequest(BaseModel):
    """Payout to driver/merchant bank account"""
    account_number: str
    bank_code: str
    account_name: str
    amount: float = Field(..., gt=0, description="Amount in ZAR")
    reason: str = "iHhashi payout"


class PaymentResponse(BaseModel):
    """Standard payment response"""
    status: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class CardDetails(BaseModel):
    """Card tokenization request"""
    card_number: str
    expiry_month: str
    expiry_year: str
    cvv: str


class RefundRequest(BaseModel):
    """Refund request"""
    reference: str
    amount: Optional[float] = None  # Full refund if not specified
    reason: str = "Customer request"


# ============ PAYMENT INITIALIZATION ============

@router.post("/initialize", response_model=PaymentResponse)
async def initialize_payment(
    payment: PaymentInitialize,
    current_user: User = Depends(get_current_user)
):
    """
    Initialize a payment transaction
    
    Returns a payment URL to redirect the user
    """
    paystack = PaystackService()
    
    # Validate order exists if order_id provided
    if payment.order_id:
        orders_col = get_collection("orders")
        from bson import ObjectId
        
        order = await orders_col.find_one({"_id": ObjectId(payment.order_id)})
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Verify amount matches order total
        if abs(order["total"] - payment.amount) > 0.01:
            raise HTTPException(
                status_code=400,
                detail=f"Amount mismatch. Order total: {order['total']}"
            )
        
        # Check order not already paid
        if order.get("payment_status") == "paid":
            raise HTTPException(status_code=400, detail="Order already paid")
    
    # Generate unique reference
    reference = f"ihhashi-{uuid.uuid4().hex[:12]}"
    
    # Whitelist allowed callback domains to prevent open redirect attacks
    ALLOWED_CALLBACK_DOMAINS = [
        "ihhashi.app", "www.ihhashi.app", "localhost", "127.0.0.1"
    ]
    requested_cb = payment.callback_url
    if requested_cb:
        from urllib.parse import urlparse
        parsed = urlparse(requested_cb)
        if parsed.hostname not in ALLOWED_CALLBACK_DOMAINS:
            raise HTTPException(status_code=400, detail="Invalid callback URL domain")
        callback_url = requested_cb
    else:
        callback_url = settings.payment_callback_url
    
    # Store payment attempt
    payments_col = get_collection("payments")
    payment_doc = {
        "reference": reference,
        "user_id": current_user.id,
        "email": payment.email,
        "amount": payment.amount,
        "order_id": payment.order_id,
        "status": "initialized",
        "created_at": datetime.now(timezone.utc)
    }
    await payments_col.insert_one(payment_doc)
    
    try:
        result = await paystack.initialize_payment(
            email=payment.email,
            amount=payment.amount,
            reference=reference,
            callback_url=callback_url,
            metadata={
                "order_id": payment.order_id,
                "user_id": current_user.id,
                "user_email": payment.email
            }
        )
        
        if result.get("status"):
            # Update payment record
            await payments_col.update_one(
                {"reference": reference},
                {"$set": {
                    "access_code": result["data"]["access_code"],
                    "status": "pending"
                }}
            )
            
            return PaymentResponse(
                status=True,
                message="Payment initialized",
                data={
                    "authorization_url": result["data"]["authorization_url"],
                    "reference": result["data"]["reference"],
                    "access_code": result["data"]["access_code"]
                }
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get("message", "Payment initialization failed")
            )
            
    except Exception as e:
        await payments_col.update_one(
            {"reference": reference},
            {"$set": {
                "status": "failed",
                "error": str(e)
            }}
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verify/{reference}", response_model=PaymentResponse)
async def verify_payment(
    reference: str,
    current_user: User = Depends(get_current_user)
):
    """
    Verify a payment transaction
    
    Call this after payment redirect to confirm status
    """
    paystack = PaystackService()
    payments_col = get_collection("payments")
    orders_col = get_collection("orders")
    
    # Check our records first
    payment_record = await payments_col.find_one({"reference": reference})
    
    try:
        result = await paystack.verify_payment(reference)
        
        if result.get("status"):
            data = result["data"]
            
            # Update payment record
            await payments_col.update_one(
                {"reference": reference},
                {"$set": {
                    "status": data["status"],
                    "paid_at": data.get("paid_at"),
                    "channel": data.get("channel"),
                    "verification_data": data
                }}
            )
            
            # If successful, update order
            if data["status"] == "success" and payment_record:
                if payment_record.get("order_id"):
                    await orders_col.update_one(
                        {"_id": payment_record["order_id"]},
                        {"$set": {
                            "payment_status": "paid",
                            "payment_reference": reference,
                            "paid_at": datetime.now(timezone.utc)
                        }}
                    )
            
            return PaymentResponse(
                status=True,
                message="Payment verified",
                data={
                    "reference": data["reference"],
                    "amount": data["amount"] / 100,  # Convert from cents
                    "status": data["status"],
                    "paid_at": data.get("paid_at"),
                    "channel": data.get("channel"),
                    "customer_email": data["customer"]["email"]
                }
            )
        else:
            raise HTTPException(status_code=400, detail="Payment verification failed")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ PAYOUTS ============

@router.post("/payout", response_model=PaymentResponse)
async def create_payout(
    payout: PayoutRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Create a payout to a bank account (for driver/merchant earnings)
    
    Note: This creates a transfer recipient and initiates transfer
    """
    if current_user.role not in [UserRole.DRIVER, UserRole.MERCHANT, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized for payouts")
    
    paystack = PaystackService()
    payments_col = get_collection("payments")
    
    # Verify user has sufficient balance
    # TODO: Implement wallet/balance check
    
    # Create payout record
    payout_reference = f"payout-{uuid.uuid4().hex[:12]}"
    payout_doc = {
        "reference": payout_reference,
        "user_id": current_user.id,
        "type": "payout",
        "amount": payout.amount,
        "account_number": payout.account_number,
        "bank_code": payout.bank_code,
        "account_name": payout.account_name,
        "status": "initialized",
        "created_at": datetime.now(timezone.utc)
    }
    await payments_col.insert_one(payout_doc)
    
    try:
        # Create recipient
        recipient_result = await paystack.create_transfer_recipient(
            account_number=payout.account_number,
            bank_code=payout.bank_code,
            name=payout.account_name
        )
        
        if not recipient_result.get("status"):
            raise HTTPException(
                status_code=400,
                detail="Failed to verify bank account"
            )
        
        recipient_code = recipient_result["data"]["recipient_code"]
        
        # Initiate transfer
        transfer_result = await paystack.initiate_transfer(
            amount=payout.amount,
            recipient_code=recipient_code,
            reason=payout.reason
        )
        
        if transfer_result.get("status"):
            await payments_col.update_one(
                {"reference": payout_reference},
                {"$set": {
                    "status": "processing",
                    "transfer_code": transfer_result["data"]["transfer_code"],
                    "recipient_code": recipient_code
                }}
            )
            
            return PaymentResponse(
                status=True,
                message="Payout initiated",
                data={
                    "transfer_code": transfer_result["data"]["transfer_code"],
                    "amount": payout.amount,
                    "recipient": payout.account_name,
                    "reference": payout_reference
                }
            )
        else:
            raise HTTPException(status_code=400, detail="Payout failed")
            
    except HTTPException:
        raise
    except Exception as e:
        await payments_col.update_one(
            {"reference": payout_reference},
            {"$set": {
                "status": "failed",
                "error": str(e)
            }}
        )
        raise HTTPException(status_code=500, detail=str(e))


# ============ REFUNDS ============

@router.post("/refund", response_model=PaymentResponse)
async def create_refund(
    refund: RefundRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Create a refund for a payment
    
    Only admins or the original payer can request refunds
    """
    paystack = PaystackService()
    payments_col = get_collection("payments")
    
    # Get payment record
    payment = await payments_col.find_one({"reference": refund.reference})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Verify authorization
    if current_user.role != UserRole.ADMIN and payment["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to refund this payment")
    
    # Check payment was successful
    if payment.get("status") != "success":
        raise HTTPException(status_code=400, detail="Payment was not successful")
    
    try:
        result = await paystack.refund_payment(
            reference=refund.reference,
            amount=refund.amount
        )
        
        if result.get("status"):
            await payments_col.update_one(
                {"reference": refund.reference},
                {"$set": {
                    "refund_status": "processing",
                    "refund_amount": refund.amount or payment["amount"],
                    "refund_reason": refund.reason,
                    "refunded_at": datetime.now(timezone.utc)
                }}
            )
            
            return PaymentResponse(
                status=True,
                message="Refund initiated",
                data={
                    "refund_id": result["data"]["id"],
                    "amount": refund.amount or payment["amount"],
                    "status": "processing"
                }
            )
        else:
            raise HTTPException(status_code=400, detail="Refund failed")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ BANKS & ACCOUNTS ============

@router.get("/banks", response_model=PaymentResponse)
async def list_banks():
    """Get list of supported South African banks"""
    return PaymentResponse(
        status=True,
        message="Banks retrieved",
        data=[
            {"name": name, "code": code}
            for name, code in SA_BANK_CODES.items()
        ]
    )


@router.post("/verify-account")
async def verify_bank_account(
    account_number: str,
    bank_code: str,
    current_user: User = Depends(get_current_user)
):
    """Verify bank account details"""
    paystack = PaystackService()
    
    try:
        result = await paystack.verify_account_number(
            account_number=account_number,
            bank_code=bank_code
        )
        
        if result.get("status"):
            return {
                "valid": True,
                "account_name": result["data"]["account_name"],
                "account_number": result["data"]["account_number"]
            }
        else:
            return {
                "valid": False,
                "message": "Could not verify account"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ WEBHOOK ============

@router.post("/webhook")
async def paystack_webhook(request: Request):
    """
    Handle Paystack webhooks with idempotency protection
    
    Events: charge.success, transfer.success, transfer.failed, refund.processed
    """
    # Get raw body for signature verification
    body = await request.body()
    payload = json.loads(body)
    
    # Verify webhook signature
    signature = request.headers.get("x-paystack-signature")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")
    
    # Compute expected signature
    secret = settings.paystack_secret_key
    expected_signature = hmac.new(
        secret.encode(),
        body,
        hashlib.sha512
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    event = payload.get("event")
    data = payload.get("data", {})
    event_id = payload.get("id") or data.get("id")  # Paystack event ID
    
    payments_col = get_collection("payments")
    orders_col = get_collection("orders")
    webhooks_col = get_collection("payment_webhooks")
    
    # IDEMPOTENCY: Check if webhook already processed
    try:
        await webhooks_col.insert_one({
            "event_id": event_id,
            "event": event,
            "data": data,
            "received_at": datetime.now(timezone.utc),
            "processed": False
        })
    except DuplicateKeyError:
        # Webhook already processed - return success without re-processing
        return {"status": "ignored", "reason": "duplicate_event"}
    
    if event == "charge.success":
        reference = data.get("reference")
        
        # VERIFY with Paystack before marking success (prevents fraud)
        try:
            paystack = PaystackService()
            verification = await paystack.verify_payment(reference)
            if verification.get("data", {}).get("status") != "success":
                await webhooks_col.update_one(
                    {"event_id": event_id},
                    {"$set": {"processed": True, "verification_failed": True}}
                )
                return {"status": "verification_failed"}
        except Exception as e:
            # Log but continue - webhook signature was valid
            logger.error(f"Payment verification failed for {reference}: {e}")
        
        # Update payment record
        await payments_col.update_one(
            {"reference": reference, "status": {"$ne": "success"}},  # Idempotent update
            {"$set": {
                "status": "success",
                "paid_at": data.get("paid_at"),
                "channel": data.get("channel"),
                "verification_data": data
            }}
        )
        
        # Update order if exists
        payment = await payments_col.find_one({"reference": reference})
        if payment and payment.get("order_id"):
            from bson import ObjectId
            await orders_col.update_one(
                {"_id": ObjectId(payment["order_id"])},
                {"$set": {
                    "payment_status": "paid",
                    "paid_at": datetime.now(timezone.utc)
                }}
            )
            
            # TODO: Send push notification to merchant
            # TODO: Trigger order confirmation flow
        
    elif event == "transfer.success":
        transfer_code = data.get("transfer_code")
        
        await payments_col.update_one(
            {"transfer_code": transfer_code},
            {"$set": {
                "status": "success",
                "completed_at": datetime.now(timezone.utc)
            }}
        )
        
        # TODO: Notify driver/merchant of successful payout
        
    elif event == "transfer.failed":
        transfer_code = data.get("transfer_code")
        
        await payments_col.update_one(
            {"transfer_code": transfer_code},
            {"$set": {
                "status": "failed",
                "failed_at": datetime.now(timezone.utc),
                "failure_reason": data.get("reason")
            }}
        )
        
        # TODO: Notify user of failed payout
        
    elif event == "refund.processed":
        reference = data.get("transaction_reference")
        
        await payments_col.update_one(
            {"reference": reference},
            {"$set": {
                "refund_status": "completed",
                "refunded_at": datetime.now(timezone.utc)
            }}
        )
        
        # Update order
        payment = await payments_col.find_one({"reference": reference})
        if payment and payment.get("order_id"):
            from bson import ObjectId
            await orders_col.update_one(
                {"_id": ObjectId(payment["order_id"])},
                {"$set": {
                    "payment_status": "refunded",
                    "status": "cancelled"
                }}
            )
    
    # Mark webhook as processed
    await webhooks_col.update_one(
        {"data.reference": data.get("reference")},
        {"$set": {"processed": True}}
    )
    
    return {"status": "received"}


# ============ PAYMENT HISTORY ============

@router.get("/history")
async def get_payment_history(
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user)
):
    """Get user's payment history"""
    payments_col = get_collection("payments")
    
    query = {"user_id": current_user.id}
    
    total = await payments_col.count_documents(query)
    
    cursor = payments_col.find(query).sort("created_at", -1).skip(offset).limit(limit)
    payments = await cursor.to_list(length=limit)
    
    for payment in payments:
        payment["id"] = str(payment["_id"])
    
    return {
        "payments": payments,
        "total": total
    }
