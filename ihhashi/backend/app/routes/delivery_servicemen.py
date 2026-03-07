from fastapi import APIRouter, Depends, HTTPException, Form
from typing import Optional, List, Any
from datetime import datetime, timedelta
from app.services.auth import get_current_user
from app.models.verification import (
    DeliveryServicemanVerification, VerificationStatus, DocumentType, 
    VehicleMode, VerificationDocument
)
from app.models.delivery import DeliveryServiceMan, DeliveryPricing, TransportMode
from app.models.account import AccountStatus, AccountRecord
from app.config import settings
from pydantic import BaseModel

router = APIRouter()


class DeliveryServicemanApplication(BaseModel):
    """Application to become a delivery serviceman"""
    full_name: str
    phone: str
    transport_mode: TransportMode
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_year: Optional[int] = None
    vehicle_color: Optional[str] = None
    number_plate: Optional[str] = None
    # Self-set pricing
    base_fee: float = 20.0  # R20 base
    per_km_rate: float = 5.0  # R5 per km
    minimum_fee: float = 15.0
    maximum_distance_km: float = 15.0


class PricingUpdate(BaseModel):
    """Update delivery pricing"""
    base_fee: float
    per_km_rate: float
    per_minute_rate: float = 0.0
    minimum_fee: float = 15.0
    maximum_distance_km: float = 15.0
    surge_multiplier: float = 1.0


@router.post("/apply")
async def apply_as_serviceman(
    application: DeliveryServicemanApplication,
    current_user = Depends(get_current_user)
) -> dict[str, Any]:
    """Apply to become a delivery serviceman - starts 45-day free trial"""
    trial_ends = datetime.utcnow() + timedelta(days=settings.free_trial_days)
    
    # Create pricing model
    pricing = DeliveryPricing(
        base_fee=application.base_fee,
        per_km_rate=application.per_km_rate,
        minimum_fee=application.minimum_fee,
        maximum_distance_km=application.maximum_distance_km,
        transport_mode=VehicleMode(application.transport_mode.value)
    )
    
    # Create serviceman profile
    serviceman = DeliveryServiceMan(
        user_id=current_user.id,
        full_name=application.full_name,
        phone=application.phone,
        transport_mode=VehicleMode(application.transport_mode.value),
        vehicle_make=application.vehicle_make,
        vehicle_model=application.vehicle_model,
        vehicle_year=application.vehicle_year,
        vehicle_color=application.vehicle_color,
        number_plate=application.number_plate,
        pricing=pricing
    )
    
    return {
        "message": "Delivery serviceman application submitted",
        "trial_ends": trial_ends.isoformat(),
        "trial_days_remaining": settings.free_trial_days,
        "transport_mode": application.transport_mode.value,
        "pricing": {
            "base_fee": application.base_fee,
            "per_km_rate": application.per_km_rate,
            "minimum_fee": application.minimum_fee,
            "note": "You set your own rates - compete on speed and quality!"
        },
        "verification_steps": [
            "Upload South African ID",
            "Upload profile photo",
            "Upload driver's license (for motor vehicles)",
            "Upload vehicle registration and number plate photo",
            "Complete Blue Horse verification for higher ranking"
        ]
    }


@router.post("/pricing")
async def update_pricing(
    pricing: PricingUpdate,
    current_user = Depends(get_current_user)
) -> dict[str, Any]:
    """Update your delivery pricing - you set your own rates!"""
    return {
        "message": "Pricing updated successfully",
        "pricing": {
            "base_fee": pricing.base_fee,
            "per_km_rate": pricing.per_km_rate,
            "per_minute_rate": pricing.per_minute_rate,
            "minimum_fee": pricing.minimum_fee,
            "maximum_distance_km": pricing.maximum_distance_km,
            "surge_multiplier": pricing.surge_multiplier
        },
        "note": "Your rates affect your ranking - competitive pricing helps you get more orders!"
    }


@router.get("/verification-status")
async def get_verification_status(current_user = Depends(get_current_user)) -> dict[str, Any]:
    """Get current verification status for Blue Horse badge"""
    return {
        "serviceman_id": current_user.id,
        "status": VerificationStatus.UNVERIFIED.value,
        "blue_horse": {
            "is_verified": False,
            "verification_level": 0,
            "has_blue_horse": False
        },
        "documents": {
            "id_document": False,
            "profile_photo": False,
            "drivers_license": False,
            "vehicle_registration": False,
            "number_plate_photo": False
        },
        "verification_percentage": 0,
        "transport_mode": "on_foot",
        "ranking_boost": 0
    }


@router.get("/account-status")
async def get_account_status(current_user = Depends(get_current_user)) -> dict[str, Any]:
    """Get account status including trial and warnings"""
    return {
        "user_id": current_user.id,
        "status": AccountStatus.FREE_TRIAL.value,
        "trial_active": True,
        "trial_days_remaining": 45,
        "warnings_count": 0,
        "is_suspended": False,
        "is_terminated": False,
        "earnings": {
            "total": 0,
            "this_week": 0,
            "pending_payout": 0
        }
    }


@router.get("/earnings")
async def get_earnings(current_user = Depends(get_current_user)) -> dict[str, Any]:
    """Get earnings summary - tips have 0% platform fee"""
    return {
        "total_earnings": 0,
        "tips_received": 0,
        "platform_fee_on_tips": 0,  # Always 0!
        "delivery_fees": 0,
        "this_week": 0,
        "pending_payout": 0,
        "payout_history": []
    }


@router.post("/online")
async def go_online(current_user = Depends(get_current_user)) -> dict[str, Any]:
    """Go online to accept delivery requests"""
    return {
        "message": "You are now online",
        "status": "available"
    }


@router.post("/offline")
async def go_offline(current_user = Depends(get_current_user)) -> dict[str, Any]:
    """Go offline - stop receiving delivery requests"""
    return {
        "message": "You are now offline",
        "status": "offline"
    }
