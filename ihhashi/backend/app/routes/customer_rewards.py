from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import datetime, timedelta
from app.services.auth import get_current_user
from app.models.customer_rewards import (
    CustomerRewardAccount, CustomerTier, CoinValues, RewardRedemption
)
from app.models.referral import ReferralCode, Referral, ReferralType, ReferralStatus
from app.database import (
    get_or_create_customer_reward_account, get_customer_reward_account,
    get_customer_tier_info, get_customer_referral_history, get_coin_transactions,
    redeem_coins_for_reward, spend_coins, add_coins_to_customer,
    create_referral_code, get_referral_code_by_user, get_referral_code_by_code,
    create_referral, check_referral_eligibility, get_db
)
from pymongo import DESCENDING
from pydantic import BaseModel
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class ReferralLinkResponse(BaseModel):
    """Response for customer referral link"""
    referral_code: str
    share_link: str
    message: str
    coins_for_referrer: int
    coins_for_friend: int


class RewardsDashboardResponse(BaseModel):
    """Full rewards dashboard for customer"""
    tier: str
    tier_name: str
    tier_icon: str
    tier_color: str
    hashi_coins_balance: int
    total_referrals: int
    referral_code: str
    free_delivery_credits: int
    discount_credits: float
    tier_progress: dict
    next_tier: Optional[str]
    referrals_to_next_tier: int
    tier_benefits: dict
    referral_history: list
    coin_history: list


class RedeemResponse(BaseModel):
    """Response for coin redemption"""
    success: bool
    message: str
    coins_spent: int
    new_balance: int
    reward_type: str
    reward_value: float
    expires_at: Optional[str]


@router.get("/referral-link", response_model=ReferralLinkResponse)
async def get_referral_link(current_user = Depends(get_current_user)):
    """Get your unique referral link to share with friends"""
    
    # Get or create referral code
    existing = await get_referral_code_by_user(current_user.id, ReferralType.CUSTOMER)
    if existing:
        code = existing.code
    else:
        new_code = await create_referral_code(current_user.id, ReferralType.CUSTOMER, "IH-C")
        code = new_code.code
    
    return ReferralLinkResponse(
        referral_code=code,
        share_link=f"https://ihhashi.co.za/signup?ref={code}",
        message="Share this link with friends! You BOTH get Hashi Coins when they sign up!",
        coins_for_referrer=CoinValues.REFERRAL_BONUS_REFERRER,
        coins_for_friend=CoinValues.REFERRAL_BONUS_REFEREE
    )


@router.get("/dashboard", response_model=RewardsDashboardResponse)
async def get_rewards_dashboard(current_user = Depends(get_current_user)):
    """Get your full rewards dashboard with tier, coins, and benefits"""
    
    # Get or create account
    account = await get_or_create_customer_reward_account(current_user.id)
    
    # Get tier info
    tier_info = await get_customer_tier_info(current_user.id)
    
    # Get referral history
    referral_history = await get_customer_referral_history(current_user.id, 10)
    
    # Get coin transactions
    coin_transactions = await get_coin_transactions(current_user.id, 10)
    coin_history = [
        {
            "id": tx.id,
            "amount": tx.amount,
            "type": tx.transaction_type,
            "description": tx.description,
            "date": tx.created_at.isoformat() if tx.created_at else None,
            "balance_after": tx.balance_after
        }
        for tx in coin_transactions
    ]
    
    # Calculate next tier
    completed = account.completed_referrals
    next_tier = tier_info.get("next_tier")
    referrals_to_next = tier_info.get("referrals_to_next_tier", 0)
    
    return RewardsDashboardResponse(
        tier=account.tier.value,
        tier_name=tier_info["tier_name"],
        tier_icon=tier_info["tier_icon"],
        tier_color=tier_info["tier_color"],
        hashi_coins_balance=account.hashi_coins_balance,
        total_referrals=account.total_referrals,
        referral_code=account.referral_code,
        free_delivery_credits=account.free_delivery_credits,
        discount_credits=account.discount_credits,
        tier_progress=tier_info.get("tier_progress", {}),
        next_tier=next_tier,
        referrals_to_next_tier=referrals_to_next,
        tier_benefits=tier_info.get("benefits", {}),
        referral_history=referral_history,
        coin_history=coin_history
    )


@router.get("/tiers")
async def get_tier_info():
    """Get information about all reward tiers and their benefits"""
    tiers = []
    for tier in CustomerTier:
        benefits = CustomerRewardAccount.get_tier_benefits(tier)
        thresholds = {
            CustomerTier.BRONZE: {"min": 1, "max": 5},
            CustomerTier.SILVER: {"min": 6, "max": 15},
            CustomerTier.GOLD: {"min": 16, "max": 50},
            CustomerTier.PLATINUM: {"min": 51, "max": "∞"}
        }
        tiers.append({
            "tier": tier.value,
            **benefits,
            "referral_range": thresholds[tier]
        })
    
    return {
        "tiers": tiers,
        "how_to_level_up": "Refer friends to iHhashi! Each successful referral moves you closer to the next tier.",
        "referral_reward": f"{CoinValues.REFERRAL_BONUS_REFERRER} Hashi Coins for you, {CoinValues.REFERRAL_BONUS_REFEREE} for your friend!"
    }


@router.post("/redeem/free-delivery", response_model=RedeemResponse)
async def redeem_free_delivery(current_user = Depends(get_current_user)):
    """Redeem Hashi Coins for a free delivery voucher"""
    
    # Check balance first
    account = await get_customer_reward_account(current_user.id)
    if not account:
        raise HTTPException(status_code=404, detail="Reward account not found")
    
    if account.hashi_coins_balance < CoinValues.FREE_DELIVERY_COST:
        return RedeemResponse(
            success=False,
            message=f"You need {CoinValues.FREE_DELIVERY_COST} Hashi Coins for free delivery",
            coins_spent=0,
            new_balance=account.hashi_coins_balance,
            reward_type="free_delivery",
            reward_value=0.0,
            expires_at=None
        )
    
    # Process redemption
    redemption = await redeem_coins_for_reward(current_user.id, "free_delivery")
    
    if redemption:
        return RedeemResponse(
            success=True,
            message="Free delivery redeemed successfully! Valid for 30 days.",
            coins_spent=CoinValues.FREE_DELIVERY_COST,
            new_balance=account.hashi_coins_balance - CoinValues.FREE_DELIVERY_COST,
            reward_type="free_delivery",
            reward_value=10.0,  # Approximate delivery value
            expires_at=redemption.expires_at.isoformat() if redemption.expires_at else None
        )
    
    raise HTTPException(status_code=400, detail="Failed to process redemption")


@router.post("/redeem/discount/{amount}", response_model=RedeemResponse)
async def redeem_discount(
    amount: int,  # 15 or 30
    current_user = Depends(get_current_user)
):
    """Redeem Hashi Coins for a discount voucher (R15 or R30)"""
    if amount not in [15, 30]:
        raise HTTPException(status_code=400, detail="Discount must be R15 or R30")
    
    redemption_type = f"discount_{amount}"
    coins_required = CoinValues.DISCOUNT_15_COST if amount == 15 else CoinValues.DISCOUNT_30_COST
    
    # Check balance
    account = await get_customer_reward_account(current_user.id)
    if not account:
        raise HTTPException(status_code=404, detail="Reward account not found")
    
    if account.hashi_coins_balance < coins_required:
        return RedeemResponse(
            success=False,
            message=f"You need {coins_required} Hashi Coins for R{amount} discount",
            coins_spent=0,
            new_balance=account.hashi_coins_balance,
            reward_type=redemption_type,
            reward_value=0.0,
            expires_at=None
        )
    
    # Process redemption
    redemption = await redeem_coins_for_reward(current_user.id, redemption_type)
    
    if redemption:
        return RedeemResponse(
            success=True,
            message=f"R{amount} discount redeemed successfully! Valid for 30 days.",
            coins_spent=coins_required,
            new_balance=account.hashi_coins_balance - coins_required,
            reward_type=redemption_type,
            reward_value=float(amount),
            expires_at=redemption.expires_at.isoformat() if redemption.expires_at else None
        )
    
    raise HTTPException(status_code=400, detail="Failed to process redemption")


@router.get("/coin-history")
async def get_coin_history(
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    current_user = Depends(get_current_user)
):
    """Get your Hashi Coin transaction history"""
    
    transactions = await get_coin_transactions(current_user.id, limit, offset)
    account = await get_customer_reward_account(current_user.id)
    
    return {
        "transactions": [
            {
                "id": tx.id,
                "amount": tx.amount,
                "type": tx.transaction_type,
                "description": tx.description,
                "date": tx.created_at.isoformat() if tx.created_at else None,
                "balance_after": tx.balance_after
            }
            for tx in transactions
        ],
        "total_earned": account.total_coins_earned if account else 0,
        "total_spent": account.total_coins_spent if account else 0,
        "current_balance": account.hashi_coins_balance if account else 0,
        "has_more": len(transactions) == limit
    }


@router.get("/referral-history")
async def get_referral_history(
    limit: int = Query(20, le=100),
    current_user = Depends(get_current_user)
):
    """Get your referral history"""
    
    referrals = await get_customer_referral_history(current_user.id, limit)
    account = await get_customer_reward_account(current_user.id)
    
    return {
        "referrals": referrals,
        "total_referrals": account.total_referrals if account else 0,
        "completed_referrals": account.completed_referrals if account else 0,
        "pending_referrals": account.pending_referrals if account else 0,
        "coins_earned_from_referrals": sum(r.get("coins_earned", 0) for r in referrals)
    }


@router.get("/my-rewards")
async def get_my_active_rewards(current_user = Depends(get_current_user)):
    """Get your active rewards (free deliveries, discounts)"""
    
    # Query active redemptions
    db_instance = get_db()
    cursor = db_instance.reward_redemptions.find({
        "customer_id": current_user.id,
        "status": "active",
        "expires_at": {"$gt": datetime.utcnow()}
    }).sort("created_at", DESCENDING)
    
    redemptions = await cursor.to_list(length=50)
    
    return {
        "active_rewards": [
            {
                "id": r["id"],
                "type": r["redemption_type"],
                "value": r["value_zar"],
                "coins_spent": r["coins_spent"],
                "expires_at": r["expires_at"].isoformat() if r.get("expires_at") else None,
                "created_at": r["created_at"].isoformat() if r.get("created_at") else None
            }
            for r in redemptions
        ],
        "total_active": len(redemptions)
    }


# === SPECIAL PROMOTIONS ===

@router.get("/promotions")
async def get_active_promotions():
    """Get active special promotions for Hashi Coins"""
    
    # Check if double referral weekend is active
    now = datetime.utcnow()
    weekend_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    weekend_end = weekend_start + timedelta(days=2)
    
    # Determine active promotions based on current date
    is_weekend = now.weekday() >= 5  # Saturday or Sunday
    
    promotions = [
        {
            "id": "first-order-bonus",
            "title": "First Order Bonus",
            "description": f"Get {CoinValues.FIRST_ORDER_BONUS} bonus Hashi Coins on your first order!",
            "bonus_coins": CoinValues.FIRST_ORDER_BONUS,
            "is_active": True,
            "type": "first_order"
        },
        {
            "id": "daily-checkin",
            "title": "Daily Check-in",
            "description": "Open the app daily to earn bonus Hashi Coins!",
            "bonus_coins": 5,
            "is_active": True,
            "type": "daily"
        }
    ]
    
    # Add weekend promotion if applicable
    if is_weekend:
        promotions.insert(0, {
            "id": "double-referral-weekend",
            "title": "Double Referral Weekend!",
            "description": "This weekend only: Get DOUBLE Hashi Coins for every referral!",
            "bonus_multiplier": 2,
            "ends_at": weekend_end.isoformat(),
            "is_active": True,
            "type": "limited_time"
        })
    
    return {"promotions": promotions}


@router.post("/apply-referral")
async def apply_referral_code(
    referral_code: str,
    current_user = Depends(get_current_user)
):
    """Apply a friend's referral code during signup to get bonus coins"""
    
    # Check eligibility
    eligible = await check_referral_eligibility(current_user.id, referral_code)
    if not eligible:
        raise HTTPException(
            status_code=400, 
            detail="Invalid referral code, already used a code, or cannot refer yourself"
        )
    
    code = referral_code.upper()
    if not code.startswith("IH-C"):
        raise HTTPException(status_code=400, detail="Invalid customer referral code")
    
    # Get code record
    code_record = await get_referral_code_by_code(code)
    if not code_record:
        raise HTTPException(status_code=404, detail="Referral code not found")
    
    # Create referral
    referral = await create_referral(
        referrer_id=code_record.user_id,
        referee_id=current_user.id,
        referral_code=code,
        referral_type=ReferralType.CUSTOMER
    )
    
    # Award welcome bonus immediately
    await add_coins_to_customer(
        current_user.id,
        CoinValues.REFERRAL_BONUS_REFEREE,
        "Welcome bonus for using referral code",
        "welcome_bonus",
        referral.id
    )
    
    return {
        "success": True,
        "message": f"Welcome to iHhashi! {CoinValues.REFERRAL_BONUS_REFEREE} Hashi Coins added to your account!",
        "coins_received": CoinValues.REFERRAL_BONUS_REFEREE,
        "referral_code": code
    }


@router.post("/earn/daily-checkin")
async def daily_checkin(current_user = Depends(get_current_user)):
    """Daily check-in to earn bonus coins"""
    
    # Check if already checked in today
    db_instance = get_db()
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    existing = await db_instance.coin_transactions.find_one({
        "customer_id": current_user.id,
        "transaction_type": "daily_checkin",
        "created_at": {"$gte": today_start}
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="Already checked in today")
    
    # Award check-in bonus
    transaction = await add_coins_to_customer(
        current_user.id,
        5,
        "Daily check-in bonus",
        "daily_checkin"
    )
    
    return {
        "success": True,
        "coins_earned": 5,
        "new_balance": transaction.balance_after if transaction else 0,
        "message": "Check-in successful! +5 Hashi Coins",
        "streak": 1  # TODO: Implement streak tracking
    }
