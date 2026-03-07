"""
Vendor API routes - Full implementation with MongoDB
Blue Horse verification system, account management, and vendor profile operations
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from typing import Optional, List
from datetime import datetime, timedelta
from bson import ObjectId

from app.services.auth import get_current_user
from app.database import get_collection
from app.utils.validation import safe_object_id
from app.models.verification import (
    VendorVerification, VerificationStatus, DocumentType, VerificationDocument
)
from app.models.account import AccountRecord, AccountStatus
from app.models.referral import (
    ReferralCode, Referral, ReferralStatus, ReferralType,
    VendorReferralStats
)
from app.models import User, UserRole
from app.config import settings
from pydantic import BaseModel
import logging

router = APIRouter(prefix="/vendors", tags=["vendors"])
logger = logging.getLogger(__name__)


class VendorApplication(BaseModel):
    """Initial vendor application"""
    business_name: str
    business_address: str
    business_city: str
    business_province: str
    business_lat: Optional[float] = None
    business_lng: Optional[float] = None
    phone: str
    email: str
    description: str
    category: str
    referral_code: Optional[str] = None  # Referral code from another vendor


class DocumentUpload(BaseModel):
    """Document upload result"""
    document_type: DocumentType
    file_url: str


@router.post("/apply")
async def apply_as_vendor(
    application: VendorApplication,
    current_user: User = Depends(get_current_user)
):
    """Apply to become a vendor - starts 45-day free trial"""
    accounts_col = get_collection("accounts")
    verifications_col = get_collection("verifications")
    referral_codes_col = get_collection("referral_codes")
    referrals_col = get_collection("referrals")
    
    # Check if user already has a vendor account
    existing_account = await accounts_col.find_one({"user_id": current_user.id})
    if existing_account and existing_account.get("status") != AccountStatus.TERMINATED.value:
        raise HTTPException(
            status_code=400,
            detail="User already has a vendor account"
        )
    
    # Create account record with free trial
    trial_ends = datetime.utcnow() + timedelta(days=settings.free_trial_days)
    
    account_doc = {
        "user_id": current_user.id,
        "status": AccountStatus.FREE_TRIAL.value,
        "trial_started_at": datetime.utcnow(),
        "trial_ends_at": trial_ends,
        "warnings": [],
        "warning_count": 0,
        "total_orders": 0,
        "completed_orders": 0,
        "cancelled_orders": 0,
        "total_spent": 0.0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    # Generate referral code for this new vendor
    referral_code_str = ReferralCode.generate_code("IH-V")
    referral_code_doc = {
        "user_id": current_user.id,
        "code": referral_code_str,
        "referral_type": ReferralType.VENDOR.value,
        "is_active": True,
        "created_at": datetime.utcnow()
    }
    
    account_doc["referral_code"] = referral_code_str
    
    # If a referral code was provided, process it
    referral_bonus = None
    if application.referral_code:
        # Find the referrer
        referrer_code = await referral_codes_col.find_one({
            "code": application.referral_code,
            "referral_type": ReferralType.VENDOR.value,
            "is_active": True
        })
        
        if referrer_code:
            referrer_id = referrer_code["user_id"]
            
            # Don't allow self-referral
            if referrer_id == current_user.id:
                referral_bonus = {
                    "code_used": application.referral_code,
                    "error": "Cannot use your own referral code"
                }
            else:
                # Add referral record
                referral_doc = {
                    "referrer_id": referrer_id,
                    "referee_id": current_user.id,
                    "referral_code": application.referral_code,
                    "referral_type": ReferralType.VENDOR.value,
                    "status": ReferralStatus.COMPLETED.value,
                    "created_at": datetime.utcnow(),
                    "completed_at": datetime.utcnow(),
                    "reward_applied": True,
                    "reward_details": {"bonus_days": 2}
                }
                await referrals_col.insert_one(referral_doc)
                
                # Update referrer's account with bonus days
                referrer_account = await accounts_col.find_one({"user_id": referrer_id})
                if referrer_account:
                    current_bonus = referrer_account.get("bonus_days_from_referrals", 0)
                    max_bonus = referrer_account.get("max_bonus_days", 90)
                    new_bonus = min(current_bonus + 2, max_bonus)
                    
                    await accounts_col.update_one(
                        {"user_id": referrer_id},
                        {
                            "$set": {
                                "bonus_days_from_referrals": new_bonus,
                                "updated_at": datetime.utcnow()
                            }
                        }
                    )
                
                # Mark this user as referred
                account_doc["referred_by"] = application.referral_code
                
                referral_bonus = {
                    "code_used": application.referral_code,
                    "bonus_for_referrer": "2 days added to their trial",
                    "your_welcome": "Thanks for using a referral link!"
                }
        else:
            referral_bonus = {
                "code_used": application.referral_code,
                "error": "Invalid or expired referral code"
            }
    
    # Insert account
    await accounts_col.insert_one(account_doc)
    
    # Insert referral code
    await referral_codes_col.insert_one(referral_code_doc)
    
    # Create vendor verification record
    verification_doc = {
        "vendor_id": current_user.id,
        "business_name": application.business_name,
        "business_address": application.business_address,
        "business_city": application.business_city,
        "business_province": application.business_province,
        "business_coordinates": {
            "lat": application.business_lat,
            "lng": application.business_lng
        } if application.business_lat else None,
        "phone": application.phone,
        "email": application.email,
        "description": application.description,
        "category": application.category,
        "status": VerificationStatus.UNVERIFIED.value,
        "blue_horse": {
            "is_verified": False,
            "verification_level": 0,
            "documents": [],
            "identity_verified": False,
            "business_verified": False,
            "location_verified": False
        },
        "documents": {
            "id_document": None,
            "company_registration": None,
            "business_license": None,
            "proof_of_address": None
        },
        "ranking_score": 0.0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    await verifications_col.insert_one(verification_doc)
    
    # Update user role to merchant
    users_col = get_collection("users")
    await users_col.update_one(
        {"_id": ObjectId(current_user.id) if ObjectId.is_valid(current_user.id) else current_user.id},
        {"$set": {"role": UserRole.MERCHANT.value, "updated_at": datetime.utcnow()}}
    )
    
    return {
        "message": "Vendor application submitted successfully!",
        "trial_ends": trial_ends.isoformat(),
        "trial_days_remaining": settings.free_trial_days,
        "verification_status": "unverified",
        "your_referral_code": referral_code_str,
        "referral_bonus": referral_bonus,
        "next_steps": [
            "Upload ID document",
            "Upload company registration (if applicable)",
            "Upload proof of business address",
            "Complete Blue Horse verification for higher ranking",
            f"Share your referral code {referral_code_str} with other vendors to earn 2 FREE DAYS per signup!"
        ]
    }


@router.post("/documents")
async def upload_verification_document(
    document_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Upload a verification document for Blue Horse status"""
    verifications_col = get_collection("verifications")
    
    # Check if vendor verification exists
    verification = await verifications_col.find_one({"vendor_id": current_user.id})
    if not verification:
        raise HTTPException(status_code=404, detail="Vendor verification record not found")
    
    # TODO: Implement actual file upload to S3/Supabase storage
    # For now, create a placeholder URL
    file_url = f"https://storage.ihhashi.co.za/documents/{current_user.id}/{document_type.value}_{datetime.utcnow().timestamp()}.pdf"
    
    # Create document record
    document = {
        "document_type": document_type.value,
        "file_url": file_url,
        "uploaded_at": datetime.utcnow().isoformat(),
        "verified_at": None,
        "verified_by": None,
        "rejection_reason": None
    }
    
    # Update verification record with document
    document_field_map = {
        DocumentType.ID_DOCUMENT: "documents.id_document",
        DocumentType.COMPANY_REGISTRATION: "documents.company_registration",
        DocumentType.BUSINESS_LICENSE: "documents.business_license",
        DocumentType.PROOF_OF_ADDRESS: "documents.proof_of_address"
    }
    
    field = document_field_map.get(document_type)
    if field:
        await verifications_col.update_one(
            {"vendor_id": current_user.id},
            {
                "$set": {
                    field: document,
                    "updated_at": datetime.utcnow()
                }
            }
        )
    
    # Add to blue_horse documents array
    await verifications_col.update_one(
        {"vendor_id": current_user.id},
        {
            "$push": {"blue_horse.documents": document},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    return {
        "message": "Document uploaded successfully",
        "document_type": document_type.value,
        "file_url": file_url,
        "status": "pending_review"
    }


@router.get("/verification-status")
async def get_verification_status(current_user: User = Depends(get_current_user)):
    """Get current verification status and Blue Horse progress"""
    verifications_col = get_collection("verifications")
    
    verification = await verifications_col.find_one({"vendor_id": current_user.id})
    if not verification:
        raise HTTPException(status_code=404, detail="Vendor verification record not found")
    
    # Calculate verification percentage
    docs = verification.get("documents", {})
    required_docs = ["id_document", "company_registration", "business_license", "proof_of_address"]
    completed = sum(1 for d in required_docs if docs.get(d) is not None)
    verification_percentage = (completed / len(required_docs)) * 100
    
    blue_horse = verification.get("blue_horse", {})
    
    return {
        "vendor_id": current_user.id,
        "status": verification.get("status", VerificationStatus.UNVERIFIED.value),
        "blue_horse": {
            "is_verified": blue_horse.get("is_verified", False),
            "verification_level": blue_horse.get("verification_level", 0),
            "has_blue_horse": blue_horse.get("verification_level", 0) >= 2
        },
        "documents": {
            "id_document": docs.get("id_document") is not None,
            "company_registration": docs.get("company_registration") is not None,
            "business_license": docs.get("business_license") is not None,
            "proof_of_address": docs.get("proof_of_address") is not None
        },
        "verification_percentage": verification_percentage,
        "ranking_boost": verification.get("ranking_score", 0),
        "next_steps": _get_next_steps(verification_percentage, docs)
    }


def _get_next_steps(percentage: float, docs: dict) -> List[str]:
    """Get next steps based on current verification status"""
    steps = []
    if not docs.get("id_document"):
        steps.append("Upload South African ID document")
    if not docs.get("company_registration"):
        steps.append("Upload company registration (CIPC)")
    if not docs.get("proof_of_address"):
        steps.append("Upload proof of business address")
    if not docs.get("business_license"):
        steps.append("Upload business license (if required)")
    if percentage == 100:
        steps.append("Submit for verification review")
    return steps


@router.get("/account-status")
async def get_account_status(current_user: User = Depends(get_current_user)):
    """Get account status including trial and warnings"""
    accounts_col = get_collection("accounts")
    referral_codes_col = get_collection("referral_codes")
    
    account = await accounts_col.find_one({"user_id": current_user.id})
    if not account:
        raise HTTPException(status_code=404, detail="Account record not found")
    
    # Get referral code
    referral_code_doc = await referral_codes_col.find_one({
        "user_id": current_user.id,
        "referral_type": ReferralType.VENDOR.value
    })
    
    # Calculate trial days remaining
    trial_ends = account.get("trial_ends_at")
    bonus_days = account.get("bonus_days_from_referrals", 0)
    
    if trial_ends:
        effective_end = trial_ends + timedelta(days=bonus_days)
        days_remaining = max(0, (effective_end - datetime.utcnow()).days)
        is_trial_active = datetime.utcnow() < effective_end
    else:
        days_remaining = 45 + bonus_days
        is_trial_active = account.get("status") == AccountStatus.FREE_TRIAL.value
    
    return {
        "user_id": current_user.id,
        "status": account.get("status", AccountStatus.FREE_TRIAL.value),
        "trial_active": is_trial_active,
        "trial_days_remaining": days_remaining,
        "trial_ends_at": trial_ends.isoformat() if trial_ends else None,
        "bonus_days_from_referrals": bonus_days,
        "referral_code": referral_code_doc["code"] if referral_code_doc else None,
        "warnings_count": account.get("warning_count", 0),
        "max_warnings": account.get("max_warnings", 3),
        "is_suspended": account.get("status") == AccountStatus.SUSPENDED.value,
        "is_terminated": account.get("status") == AccountStatus.TERMINATED.value,
        "suspension_reason": account.get("suspension_reason"),
        "suspended_at": account.get("suspended_at").isoformat() if account.get("suspended_at") else None
    }


@router.post("/submit-verification")
async def submit_for_verification(current_user: User = Depends(get_current_user)):
    """Submit all documents for Blue Horse verification review"""
    verifications_col = get_collection("verifications")
    
    verification = await verifications_col.find_one({"vendor_id": current_user.id})
    if not verification:
        raise HTTPException(status_code=404, detail="Vendor verification record not found")
    
    # Check if already submitted or verified
    current_status = verification.get("status")
    if current_status == VerificationStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="Verification already submitted and pending review")
    if current_status == VerificationStatus.VERIFIED.value:
        raise HTTPException(status_code=400, detail="Already verified")
    
    # Check required documents
    docs = verification.get("documents", {})
    if not docs.get("id_document"):
        raise HTTPException(status_code=400, detail="ID document is required")
    
    # Update status to pending
    await verifications_col.update_one(
        {"vendor_id": current_user.id},
        {
            "$set": {
                "status": VerificationStatus.PENDING.value,
                "blue_horse.submitted_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return {
        "message": "Verification submitted for review",
        "estimated_review_time": "2-3 business days",
        "status": VerificationStatus.PENDING.value
    }


@router.get("/my/stats")
async def get_vendor_stats(current_user: User = Depends(get_current_user)):
    """Get vendor statistics and analytics"""
    if current_user.role != UserRole.MERCHANT:
        raise HTTPException(status_code=403, detail="Not a merchant")
    
    stores_col = get_collection("stores")
    orders_col = get_collection("orders")
    products_col = get_collection("products")
    reviews_col = get_collection("reviews")
    
    # Get merchant's store
    store = await stores_col.find_one({"owner_id": current_user.id})
    if not store:
        raise HTTPException(status_code=404, detail="No store found")
    
    store_id = str(store["_id"])
    
    # Order stats
    total_orders = await orders_col.count_documents({"store_id": store_id})
    pending_orders = await orders_col.count_documents({
        "store_id": store_id,
        "status": {"$in": ["pending", "confirmed", "preparing", "ready"]}
    })
    completed_orders = await orders_col.count_documents({
        "store_id": store_id,
        "status": "delivered"
    })
    cancelled_orders = await orders_col.count_documents({
        "store_id": store_id,
        "status": "cancelled"
    })
    
    # Revenue calculation
    pipeline = [
        {
            "$match": {
                "store_id": store_id,
                "status": "delivered"
            }
        },
        {
            "$group": {
                "_id": None,
                "total_revenue": {"$sum": "$subtotal"},
                "total_delivery_fees": {"$sum": "$delivery_fee"},
                "order_count": {"$sum": 1}
            }
        }
    ]
    
    cursor = orders_col.aggregate(pipeline)
    revenue_result = await cursor.to_list(length=1)
    
    total_revenue = revenue_result[0]["total_revenue"] if revenue_result else 0
    order_count = revenue_result[0]["order_count"] if revenue_result else 0
    
    # Product count
    total_products = await products_col.count_documents({"store_id": store_id})
    available_products = await products_col.count_documents({
        "store_id": store_id,
        "is_available": True
    })
    
    # Reviews stats
    total_reviews = await reviews_col.count_documents({"store_id": store_id})
    
    pipeline_reviews = [
        {"$match": {"store_id": store_id}},
        {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}}}
    ]
    cursor = reviews_col.aggregate(pipeline_reviews)
    avg_result = await cursor.to_list(length=1)
    average_rating = avg_result[0]["avg_rating"] if avg_result else 0
    
    # Recent orders (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_orders = await orders_col.count_documents({
        "store_id": store_id,
        "created_at": {"$gte": week_ago}
    })
    
    return {
        "store": {
            "id": store_id,
            "name": store["name"],
            "status": store.get("status"),
            "is_open": store.get("is_open", True),
            "rating": store.get("rating", 5.0)
        },
        "orders": {
            "total": total_orders,
            "pending": pending_orders,
            "completed": completed_orders,
            "cancelled": cancelled_orders,
            "recent_7_days": recent_orders,
            "completion_rate": round(completed_orders / total_orders * 100, 2) if total_orders > 0 else 0
        },
        "revenue": {
            "total": round(total_revenue, 2),
            "platform_fees": round(total_revenue * 0.15, 2),  # 15% platform fee
            "net": round(total_revenue * 0.85, 2),
            "average_order_value": round(total_revenue / order_count, 2) if order_count > 0 else 0
        },
        "products": {
            "total": total_products,
            "available": available_products,
            "out_of_stock": total_products - available_products
        },
        "reviews": {
            "total": total_reviews,
            "average_rating": round(average_rating, 2) if average_rating else 0
        }
    }


@router.get("/my/referrals")
async def get_vendor_referrals(current_user: User = Depends(get_current_user)):
    """Get vendor referral statistics"""
    if current_user.role != UserRole.MERCHANT:
        raise HTTPException(status_code=403, detail="Not a merchant")
    
    referral_codes_col = get_collection("referral_codes")
    referrals_col = get_collection("referrals")
    accounts_col = get_collection("accounts")
    
    # Get referral code
    referral_code_doc = await referral_codes_col.find_one({
        "user_id": current_user.id,
        "referral_type": ReferralType.VENDOR.value
    })
    
    if not referral_code_doc:
        raise HTTPException(status_code=404, detail="Referral code not found")
    
    code = referral_code_doc["code"]
    
    # Get all referrals
    cursor = referrals_col.find({
        "referrer_id": current_user.id,
        "referral_type": ReferralType.VENDOR.value
    })
    referrals = await cursor.to_list(length=100)
    
    total_referrals = len(referrals)
    completed = sum(1 for r in referrals if r.get("status") == ReferralStatus.COMPLETED.value)
    pending = sum(1 for r in referrals if r.get("status") == ReferralStatus.PENDING.value)
    
    # Get account for bonus days
    account = await accounts_col.find_one({"user_id": current_user.id})
    bonus_days = account.get("bonus_days_from_referrals", 0) if account else 0
    
    return {
        "referral_code": code,
        "stats": {
            "total_referrals": total_referrals,
            "completed": completed,
            "pending": pending
        },
        "rewards": {
            "bonus_days_earned": bonus_days,
            "bonus_per_referral": 2,
            "max_bonus_days": 90
        },
        "share_link": f"https://ihhashi.app/vendor/apply?ref={code}",
        "referrals": [
            {
                "referee_id": r.get("referee_id"),
                "status": r.get("status"),
                "created_at": r.get("created_at").isoformat() if r.get("created_at") else None,
                "completed_at": r.get("completed_at").isoformat() if r.get("completed_at") else None
            }
            for r in referrals
        ]
    }


# ============ PUBLIC ENDPOINTS ============

@router.get("/{vendor_id}")
async def get_vendor_profile(vendor_id: str):
    """Get public vendor profile with Blue Horse status"""
    verifications_col = get_collection("verifications")
    stores_col = get_collection("stores")
    reviews_col = get_collection("reviews")
    products_col = get_collection("products")
    
    # Get verification record
    verification = await verifications_col.find_one({"vendor_id": vendor_id})
    if not verification:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Get store info
    store = await stores_col.find_one({"owner_id": vendor_id})
    
    # Get reviews
    cursor = reviews_col.find({"store_id": str(store["_id"]) if store else None}).limit(10)
    reviews = await cursor.to_list(length=10)
    
    # Get product count
    product_count = 0
    if store:
        product_count = await products_col.count_documents({
            "store_id": str(store["_id"]),
            "is_available": True
        })
    
    # Calculate rating
    pipeline = [
        {"$match": {"store_id": str(store["_id"]) if store else None}},
        {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}, "count": {"$sum": 1}}}
    ]
    cursor = reviews_col.aggregate(pipeline)
    rating_result = await cursor.to_list(length=1)
    
    avg_rating = rating_result[0]["avg_rating"] if rating_result else 0
    total_reviews = rating_result[0]["count"] if rating_result else 0
    
    blue_horse = verification.get("blue_horse", {})
    
    return {
        "vendor_id": vendor_id,
        "business_name": verification.get("business_name"),
        "description": verification.get("description"),
        "category": verification.get("category"),
        "business_address": verification.get("business_address"),
        "business_city": verification.get("business_city"),
        "business_province": verification.get("business_province"),
        "rating": round(avg_rating, 2) if avg_rating else 4.5,
        "total_reviews": total_reviews,
        "blue_horse_verified": blue_horse.get("is_verified", False),
        "verification_level": blue_horse.get("verification_level", 0),
        "has_blue_horse": blue_horse.get("verification_level", 0) >= 2,
        "store": {
            "id": str(store["_id"]) if store else None,
            "name": store["name"] if store else None,
            "is_open": store.get("is_open", True) if store else None
        } if store else None,
        "product_count": product_count
    }


@router.get("/{vendor_id}/products")
async def get_vendor_products(
    vendor_id: str,
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0)
):
    """Get vendor's product listing"""
    verifications_col = get_collection("verifications")
    stores_col = get_collection("stores")
    products_col = get_collection("products")
    
    # Verify vendor exists
    verification = await verifications_col.find_one({"vendor_id": vendor_id})
    if not verification:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Get store
    store = await stores_col.find_one({"owner_id": vendor_id})
    if not store:
        return {
            "vendor_id": vendor_id,
            "products": [],
            "total": 0
        }
    
    store_id = str(store["_id"])
    
    # Get products
    query = {
        "store_id": store_id,
        "is_available": True
    }
    
    total = await products_col.count_documents(query)
    
    cursor = products_col.find(query).skip(offset).limit(limit)
    products = await cursor.to_list(length=limit)
    
    # Format products
    formatted_products = []
    for product in products:
        formatted_products.append({
            "id": str(product["_id"]),
            "name": product.get("name"),
            "description": product.get("description"),
            "price": product.get("price"),
            "category": product.get("category"),
            "stock_quantity": product.get("stock_quantity"),
            "images": product.get("images", []),
            "is_available": product.get("is_available", True)
        })
    
    return {
        "vendor_id": vendor_id,
        "store_id": store_id,
        "products": formatted_products,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/{vendor_id}/reviews")
async def get_vendor_reviews(
    vendor_id: str,
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0)
):
    """Get vendor reviews and ratings"""
    verifications_col = get_collection("verifications")
    stores_col = get_collection("stores")
    reviews_col = get_collection("reviews")
    
    # Verify vendor exists
    verification = await verifications_col.find_one({"vendor_id": vendor_id})
    if not verification:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Get store
    store = await stores_col.find_one({"owner_id": vendor_id})
    store_id = str(store["_id"]) if store else None
    
    if not store_id:
        return {
            "vendor_id": vendor_id,
            "average_rating": 0,
            "total_reviews": 0,
            "reviews": []
        }
    
    # Get reviews stats
    pipeline = [
        {"$match": {"store_id": store_id}},
        {"$group": {
            "_id": None,
            "avg_rating": {"$avg": "$rating"},
            "total_reviews": {"$sum": 1}
        }}
    ]
    cursor = reviews_col.aggregate(pipeline)
    stats_result = await cursor.to_list(length=1)
    
    avg_rating = stats_result[0]["avg_rating"] if stats_result else 0
    total_reviews = stats_result[0]["total_reviews"] if stats_result else 0
    
    # Get reviews list
    cursor = reviews_col.find({"store_id": store_id}).sort("created_at", -1).skip(offset).limit(limit)
    reviews = await cursor.to_list(length=limit)
    
    formatted_reviews = []
    for review in reviews:
        formatted_reviews.append({
            "id": str(review["_id"]),
            "rating": review.get("rating"),
            "comment": review.get("comment"),
            "author_name": review.get("author_name", "Anonymous"),
            "created_at": review.get("created_at").isoformat() if review.get("created_at") else None
        })
    
    return {
        "vendor_id": vendor_id,
        "average_rating": round(avg_rating, 2) if avg_rating else 0,
        "total_reviews": total_reviews,
        "reviews": formatted_reviews,
        "limit": limit,
        "offset": offset
    }
