from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import Optional
from datetime import datetime, timedelta
from app.services.auth import get_current_user
from app.models.referral import (
    ReferralCode, Referral, ReferralStatus, ReferralType,
    VendorReferralStats, CustomerReferralStats, ReferralReward
)
from app.models.account import AccountRecord, AccountStatus
from app.config import settings
from app.database import (
    create_referral_code, get_referral_code_by_user, get_referral_code_by_code,
    create_referral, complete_referral, get_referral_stats, check_referral_eligibility,
    extend_vendor_trial, get_vendor_referral_stats, get_top_referrers,
    get_all_referral_stats, process_pending_referrals, add_coins_to_customer,
    get_or_create_customer_reward_account, get_customer_tier_info,
    get_customer_reward_account, redeem_coins_for_reward,
    get_customer_referral_history
)
from pydantic import BaseModel
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class ReferralCodeResponse(BaseModel):
    """Response for referral code generation"""
    code: str
    referral_type: str
    share_link: str
    message: str


class ApplyReferralRequest(BaseModel):
    """Request to apply a referral code during signup"""
    referral_code: str
    referral_type: ReferralType


class ReferralStatsResponse(BaseModel):
    """Referral statistics response"""
    referral_code: str
    total_referrals: int
    completed_referrals: int
    pending_referrals: int
    rewards_earned: dict


class CustomerRewardsResponse(BaseModel):
    """Customer rewards and tier status"""
    referral_code: str
    tier: str
    hashi_coins_balance: int
    total_referrals: int
    free_delivery_credits: int
    discount_credits: float
    tier_progress: dict
    tier_benefits: dict


@router.post("/generate/{referral_type}", response_model=ReferralCodeResponse)
async def generate_referral_code(
    referral_type: ReferralType,
    current_user = Depends(get_current_user)
):
    """Generate a unique referral code for the current user"""
    
    # Check if user already has a code for this type
    existing = await get_referral_code_by_user(current_user.id, referral_type)
    if existing:
        code = existing.code
    else:
        # Create new code
        prefix = "IH-V" if referral_type == ReferralType.VENDOR else "IH-C"
        new_code = await create_referral_code(current_user.id, referral_type, prefix)
        code = new_code.code
    
    # Generate share link
    base_url = "https://ihhashi.co.za"
    if referral_type == ReferralType.VENDOR:
        share_link = f"{base_url}/vendor/signup?ref={code}"
        message = "Share this link with vendors. You get 2 FREE DAYS for each vendor who signs up!"
    else:
        share_link = f"{base_url}/signup?ref={code}"
        message = "Share this link with friends. You BOTH earn Hashi Coins!"
    
    return ReferralCodeResponse(
        code=code,
        referral_type=referral_type.value,
        share_link=share_link,
        message=message
    )


@router.post("/apply", status_code=200)
async def apply_referral_code(
    request: ApplyReferralRequest,
    current_user = Depends(get_current_user)
):
    """Apply a referral code during signup - awards bonuses to both parties"""
    
    # Check eligibility
    eligible = await check_referral_eligibility(current_user.id, request.referral_code)
    if not eligible:
        raise HTTPException(
            status_code=400, 
            detail="Invalid referral code or you have already used a referral code"
        )
    
    # Validate code format
    code = request.referral_code.upper()
    expected_prefix = "IH-V" if request.referral_type == ReferralType.VENDOR else "IH-C"
    if not code.startswith(expected_prefix):
        raise HTTPException(
            status_code=400, 
            detail=f"This code is for {'vendors' if request.referral_type == ReferralType.CUSTOMER else 'customers'}"
        )
    
    # Get the referral code record
    code_record = await get_referral_code_by_code(code)
    if not code_record:
        raise HTTPException(status_code=404, detail="Referral code not found")
    
    # Create referral record
    referral = await create_referral(
        referrer_id=code_record.user_id,
        referee_id=current_user.id,
        referral_code=code,
        referral_type=request.referral_type
    )
    
    rewards = ReferralReward(referral_type=request.referral_type)
    
    if request.referral_type == ReferralType.VENDOR:
        # For vendor referrals, extend trial immediately
        await extend_vendor_trial(code_record.user_id, rewards.vendor_bonus_days_per_referral)
        
        # Complete the referral
        await complete_referral(referral.id, {
            "bonus_days": rewards.vendor_bonus_days_per_referral
        })
        
        return {
            "message": "Referral code applied successfully!",
            "referrer_reward": f"{rewards.vendor_bonus_days_per_referral} days added to free trial",
            "your_welcome_bonus": "Welcome to iHhashi! Your referrer helped you get started.",
            "referral_code": code
        }
    else:
        # For customer referrals, coins are awarded when referee completes first order
        # But give welcome bonus immediately
        await add_coins_to_customer(
            current_user.id,
            rewards.customer_referee_coins,
            "Welcome bonus for using referral code",
            "welcome_bonus"
        )
        
        return {
            "message": "Referral code applied successfully!",
            "referrer_reward": f"{rewards.customer_referrer_coins} Hashi Coins (after your first order)",
            "your_welcome_bonus": f"{rewards.customer_referee_coins} Hashi Coins added to your account!",
            "referral_code": code,
            "hashi_coins": rewards.customer_referee_coins
        }


@router.get("/stats", response_model=ReferralStatsResponse)
async def get_referral_stats(
    referral_type: ReferralType = Query(ReferralType.VENDOR),
    current_user = Depends(get_current_user)
):
    """Get referral statistics for the current user"""
    
    stats = await get_referral_stats(current_user.id, referral_type)
    
    return ReferralStatsResponse(
        referral_code=stats.get("referral_code") or f"IH-{referral_type.value[0].upper()}-XXXXXX",
        total_referrals=stats.get("total_referrals", 0),
        completed_referrals=stats.get("completed_referrals", 0),
        pending_referrals=stats.get("pending_referrals", 0),
        rewards_earned=stats.get("rewards_earned", {})
    )


@router.get("/customer/rewards", response_model=CustomerRewardsResponse)
async def get_customer_rewards(current_user = Depends(get_current_user)):
    """Get detailed customer rewards, tier status, and benefits"""
    
    # Get or create reward account
    account = await get_or_create_customer_reward_account(current_user.id)
    tier_info = await get_customer_tier_info(current_user.id)
    
    return CustomerRewardsResponse(
        referral_code=account.referral_code,
        tier=account.tier.value,
        hashi_coins_balance=account.hashi_coins_balance,
        total_referrals=account.total_referrals,
        free_delivery_credits=account.free_delivery_credits,
        discount_credits=account.discount_credits,
        tier_progress=tier_info.get("tier_progress", {}),
        tier_benefits=tier_info.get("benefits", {})
    )


@router.post("/redeem/free-delivery")
async def redeem_free_delivery(current_user = Depends(get_current_user)):
    """Redeem Hashi Coins for a free delivery"""
    rewards = ReferralReward(referral_type=ReferralType.CUSTOMER)
    
    # Check balance
    account = await get_customer_reward_account(current_user.id)
    if not account:
        raise HTTPException(status_code=404, detail="Reward account not found")
    
    if account.hashi_coins_balance < rewards.coins_for_free_delivery:
        return {
            "success": False,
            "message": f"You need {rewards.coins_for_free_delivery} Hashi Coins for free delivery",
            "coins_required": rewards.coins_for_free_delivery,
            "current_balance": account.hashi_coins_balance
        }
    
    # Process redemption
    redemption = await redeem_coins_for_reward(current_user.id, "free_delivery")
    
    if redemption:
        return {
            "success": True,
            "message": "Free delivery redeemed successfully!",
            "coins_spent": rewards.coins_for_free_delivery,
            "new_balance": account.hashi_coins_balance - rewards.coins_for_free_delivery,
            "expires_at": redemption.expires_at.isoformat() if redemption.expires_at else None
        }
    
    raise HTTPException(status_code=400, detail="Failed to redeem coins")


@router.post("/redeem/discount/{amount}")
async def redeem_discount(
    amount: int,  # 15 or 30
    current_user = Depends(get_current_user)
):
    """Redeem Hashi Coins for a discount coupon"""
    
    if amount not in [15, 30]:
        raise HTTPException(status_code=400, detail="Discount amount must be 15 or 30")
    
    rewards = ReferralReward(referral_type=ReferralType.CUSTOMER)
    
    redemption_type = "discount_15" if amount == 15 else "discount_30"
    coins_required = rewards.coins_for_discount_10 if amount == 15 else rewards.coins_for_discount_25
    
    # Check balance
    account = await get_customer_reward_account(current_user.id)
    if not account:
        raise HTTPException(status_code=404, detail="Reward account not found")
    
    if account.hashi_coins_balance < coins_required:
        return {
            "success": False,
            "message": f"You need {coins_required} Hashi Coins for R{amount} discount",
            "coins_required": coins_required,
            "current_balance": account.hashi_coins_balance
        }
    
    # Process redemption
    redemption = await redeem_coins_for_reward(current_user.id, redemption_type)
    
    if redemption:
        return {
            "success": True,
            "message": f"R{amount} discount redeemed successfully!",
            "coins_spent": coins_required,
            "discount_value": amount,
            "new_balance": account.hashi_coins_balance - coins_required,
            "expires_at": redemption.expires_at.isoformat() if redemption.expires_at else None
        }
    
    raise HTTPException(status_code=400, detail="Failed to redeem coins")


@router.get("/my-referrals")
async def get_my_referrals(
    limit: int = Query(20, le=100),
    current_user = Depends(get_current_user)
):
    """Get my referral history"""
    referrals = await get_customer_referral_history(current_user.id, limit)
    account = await get_customer_reward_account(current_user.id)
    
    return {
        "referrals": referrals,
        "total_referrals": account.total_referrals if account else 0,
        "completed_referrals": account.completed_referrals if account else 0,
        "pending_referrals": account.pending_referrals if account else 0,
        "coins_earned_from_referrals": sum(r.get("coins_earned", 0) for r in referrals)
    }


@router.get("/leaderboard")
async def get_referral_leaderboard(limit: int = Query(10, le=50)):
    """Get top referrers leaderboard"""
    top_referrers = await get_top_referrers(limit)
    
    return {
        "leaderboard": top_referrers,
        "updated_at": datetime.utcnow().isoformat()
    }


# === ADMIN ENDPOINTS ===

@router.post("/admin/process-pending")
async def process_pending_referrals(background_tasks: BackgroundTasks):
    """Process pending referrals and award bonuses (called by cron job)"""
    result = await process_pending_referrals()
    
    return {
        "message": "Pending referrals processed",
        "processed_count": result["processed"],
        "awards_given": result["awarded"]
    }


@router.get("/admin/stats")
async def get_admin_referral_stats():
    """Get overall referral program statistics"""
    stats = await get_all_referral_stats()
    
    return stats
