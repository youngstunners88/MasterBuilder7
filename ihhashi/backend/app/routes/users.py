from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional
from datetime import datetime, timezone
from bson import ObjectId

from app.services.auth import get_current_user
from app.models import User, UserRole
from app.database import get_collection
from app.middleware.rate_limit import limiter

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
@limiter.limit("60/minute")
async def get_profile(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get current user profile"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "phone": current_user.phone,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at,
    }


@router.patch("/me")
@limiter.limit("20/minute")
async def update_profile(
    request: Request,
    full_name: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Update user profile"""
    users_col = get_collection("users")
    
    update_fields = {"updated_at": datetime.now(timezone.utc)}
    
    if full_name:
        update_fields["full_name"] = full_name
    if phone:
        update_fields["phone"] = phone
    if email:
        # Check email not taken
        existing = await users_col.find_one({
            "email": email,
            "_id": {"$ne": ObjectId(current_user.id)}
        })
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        update_fields["email"] = email
    
    result = await users_col.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$set": update_fields}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "Profile updated"}


@router.patch("/location")
@limiter.limit("30/minute")
async def update_location(
    request: Request,
    lat: float,
    lng: float,
    address: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Update user's current location"""
    users_col = get_collection("users")
    
    location_doc = {
        "latitude": lat,
        "longitude": lng,
        "address": address,
        "updated_at": datetime.now(timezone.utc)
    }
    
    await users_col.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$set": {"current_location": location_doc, "updated_at": datetime.now(timezone.utc)}}
    )
    
    return {"message": "Location updated", "location": location_doc}


@router.patch("/language")
@limiter.limit("20/minute")
async def update_language(
    request: Request,
    language: str,
    current_user: User = Depends(get_current_user)
):
    """Update user's preferred language"""
    supported = ["en", "zu", "xh", "af", "st", "tn", "so", "nso", "ts", "ve", "nr"]
    if language not in supported:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language. Supported: {supported}"
        )
    
    users_col = get_collection("users")
    
    await users_col.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$set": {"language": language, "updated_at": datetime.now(timezone.utc)}}
    )
    
    return {"message": "Language updated", "language": language}


@router.delete("/me")
@limiter.limit("5/minute")
async def delete_account(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Delete user account (soft delete)"""
    users_col = get_collection("users")
    
    await users_col.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$set": {
            "is_active": False,
            "deleted_at": datetime.now(timezone.utc),
            "email": f"deleted_{current_user.id}@deleted.ihhashi.app",
            "phone": None
        }}
    )
    
    return {"message": "Account deleted successfully"}
