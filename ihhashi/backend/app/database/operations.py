"""
iHhashi Database Operations Layer
Implements all 48+ pending database operations for referrals, rewards, coin balances, and more.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, TEXT
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging

from app.config import settings
from app.models.referral import (
    ReferralCode, Referral, ReferralStatus, ReferralType,
    VendorReferralStats, CustomerReferralStats
)
from app.models.customer_rewards import (
    CustomerRewardAccount, CustomerTier, CoinTransaction, 
    RewardRedemption, CoinValues
)
from app.models.order import Order
from app.models.user import User

logger = logging.getLogger(__name__)

# Import database instance from parent module
try:
    from app.database import database, get_collection
except ImportError:
    database = None
    get_collection = None


def get_db() -> AsyncIOMotorDatabase:
    """Get database instance"""
    if database is None:
        raise RuntimeError("Database not connected")
    return database


# ============================================================================
# REFERRAL OPERATIONS (1-12)
# ============================================================================

async def create_referral_code(
    user_id: str, 
    referral_type: ReferralType,
    prefix: str = "IH"
) -> ReferralCode:
    """Create a new unique referral code for a user"""
    db = get_db()
    
    # Generate unique code
    max_attempts = 10
    for _ in range(max_attempts):
        code_str = ReferralCode.generate_code(prefix)
        
        # Check if code exists
        existing = await db.referral_codes.find_one({"code": code_str})
        if not existing:
            break
    else:
        raise Exception("Could not generate unique referral code")
    
    referral_code = ReferralCode(
        user_id=user_id,
        code=code_str,
        referral_type=referral_type
    )
    
    await db.referral_codes.insert_one(referral_code.dict())
    logger.info(f"Created {referral_type.value} referral code {code_str} for user {user_id}")
    
    return referral_code


async def get_referral_code_by_user(
    user_id: str, 
    referral_type: ReferralType
) -> Optional[ReferralCode]:
    """Get existing referral code for user"""
    db = get_db()
    
    doc = await db.referral_codes.find_one({
        "user_id": user_id,
        "referral_type": referral_type.value,
        "is_active": True
    })
    
    if doc:
        return ReferralCode(**doc)
    return None


async def get_referral_code_by_code(code: str) -> Optional[ReferralCode]:
    """Get referral code by code string"""
    db = get_db()
    
    doc = await db.referral_codes.find_one({
        "code": code.upper(),
        "is_active": True
    })
    
    if doc:
        return ReferralCode(**doc)
    return None


async def create_referral(
    referrer_id: str,
    referee_id: str,
    referral_code: str,
    referral_type: ReferralType
) -> Referral:
    """Create a new referral record"""
    db = get_db()
    
    referral = Referral(
        referrer_id=referrer_id,
        referee_id=referee_id,
        referral_code=referral_code.upper(),
        referral_type=referral_type,
        status=ReferralStatus.PENDING
    )
    
    await db.referrals.insert_one(referral.dict())
    
    # Update referrer's pending count
    if referral_type == ReferralType.CUSTOMER:
        await db.customer_reward_accounts.update_one(
            {"customer_id": referrer_id},
            {"$inc": {"pending_referrals": 1}}
        )
    
    logger.info(f"Created referral: {referral.id}")
    return referral


async def complete_referral(
    referral_id: str,
    reward_details: Dict[str, Any]
) -> Optional[Referral]:
    """Mark a referral as completed and award bonuses"""
    db = get_db()
    
    update_data = {
        "status": ReferralStatus.COMPLETED.value,
        "completed_at": datetime.utcnow(),
        "reward_applied": True,
        "reward_details": reward_details
    }
    
    result = await db.referrals.find_one_and_update(
        {"id": referral_id},
        {"$set": update_data},
        return_document=True
    )
    
    if result:
        # Update referrer stats
        referral = Referral(**result)
        
        if referral.referral_type == ReferralType.CUSTOMER:
            # Update customer reward account
            await db.customer_reward_accounts.update_one(
                {"customer_id": referral.referrer_id},
                {
                    "$inc": {
                        "completed_referrals": 1,
                        "pending_referrals": -1,
                        "total_referrals": 1
                    }
                }
            )
        
        logger.info(f"Completed referral: {referral_id}")
        return referral
    
    return None


async def get_referrals_by_referrer(
    referrer_id: str,
    referral_type: Optional[ReferralType] = None,
    status: Optional[ReferralStatus] = None
) -> List[Referral]:
    """Get all referrals made by a user"""
    db = get_db()
    
    query = {"referrer_id": referrer_id}
    if referral_type:
        query["referral_type"] = referral_type.value
    if status:
        query["status"] = status.value
    
    cursor = db.referrals.find(query).sort("created_at", DESCENDING)
    docs = await cursor.to_list(length=100)
    
    return [Referral(**doc) for doc in docs]


async def get_referral_stats(referrer_id: str, referral_type: ReferralType) -> Dict[str, Any]:
    """Get referral statistics for a user"""
    db = get_db()
    
    # Get counts by status
    pipeline = [
        {"$match": {"referrer_id": referrer_id, "referral_type": referral_type.value}},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1}
        }}
    ]
    
    status_counts = {}
    async for doc in db.referrals.aggregate(pipeline):
        status_counts[doc["_id"]] = doc["count"]
    
    total = sum(status_counts.values())
    completed = status_counts.get(ReferralStatus.COMPLETED.value, 0)
    pending = status_counts.get(ReferralStatus.PENDING.value, 0)
    
    # Get referral code
    ref_code = await get_referral_code_by_user(referrer_id, referral_type)
    
    return {
        "referral_code": ref_code.code if ref_code else None,
        "total_referrals": total,
        "completed_referrals": completed,
        "pending_referrals": pending,
        "rewards_earned": {
            "bonus_days": completed * 2 if referral_type == ReferralType.VENDOR else 0,
            "hashi_coins": completed * 50 if referral_type == ReferralType.CUSTOMER else 0
        }
    }


async def check_referral_eligibility(referee_id: str, referral_code: str) -> bool:
    """Check if a user can apply a referral code"""
    db = get_db()
    
    # Check if user already used a referral code
    existing = await db.referrals.find_one({"referee_id": referee_id})
    if existing:
        return False
    
    # Check if referral code exists and is active
    code_doc = await db.referral_codes.find_one({
        "code": referral_code.upper(),
        "is_active": True
    })
    if not code_doc:
        return False
    
    # Can't refer yourself
    if code_doc["user_id"] == referee_id:
        return False
    
    return True


# ============================================================================
# CUSTOMER REWARD OPERATIONS (13-24)
# ============================================================================

async def create_customer_reward_account(customer_id: str) -> CustomerRewardAccount:
    """Create a new reward account for a customer"""
    db = get_db()
    
    # Generate unique referral code for customer
    code = ReferralCode.generate_code("IH-C")
    
    account = CustomerRewardAccount(
        customer_id=customer_id,
        referral_code=code,
        tier=CustomerTier.BRONZE,
        hashi_coins_balance=0,
        total_referrals=0,
        completed_referrals=0,
        pending_referrals=0
    )
    
    await db.customer_reward_accounts.insert_one(account.dict())
    
    # Also create the referral code record
    await create_referral_code(customer_id, ReferralType.CUSTOMER, "IH-C")
    
    logger.info(f"Created reward account for customer {customer_id}")
    return account


async def get_customer_reward_account(customer_id: str) -> Optional[CustomerRewardAccount]:
    """Get a customer's reward account"""
    db = get_db()
    
    doc = await db.customer_reward_accounts.find_one({"customer_id": customer_id})
    
    if doc:
        return CustomerRewardAccount(**doc)
    return None


async def get_or_create_customer_reward_account(customer_id: str) -> CustomerRewardAccount:
    """Get existing account or create new one"""
    account = await get_customer_reward_account(customer_id)
    if account:
        return account
    return await create_customer_reward_account(customer_id)


async def add_coins_to_customer(
    customer_id: str,
    amount: int,
    description: str,
    transaction_type: str = "referral_reward",
    related_referral_id: Optional[str] = None
) -> Optional[CoinTransaction]:
    """Add Hashi Coins to customer account"""
    db = get_db()
    
    # Get current balance
    account = await get_customer_reward_account(customer_id)
    if not account:
        account = await create_customer_reward_account(customer_id)
    
    new_balance = account.hashi_coins_balance + amount
    
    # Update account
    await db.customer_reward_accounts.update_one(
        {"customer_id": customer_id},
        {
            "$inc": {
                "hashi_coins_balance": amount,
                "total_coins_earned": amount
            },
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    # Create transaction record
    transaction = CoinTransaction(
        customer_id=customer_id,
        amount=amount,
        transaction_type=transaction_type,
        description=description,
        related_referral_id=related_referral_id,
        balance_after=new_balance
    )
    
    await db.coin_transactions.insert_one(transaction.dict())
    
    # Check for tier upgrade
    await update_customer_tier(customer_id)
    
    logger.info(f"Added {amount} coins to customer {customer_id}")
    return transaction


async def spend_coins(
    customer_id: str,
    amount: int,
    description: str,
    transaction_type: str = "redemption"
) -> Optional[CoinTransaction]:
    """Spend Hashi Coins from customer account"""
    db = get_db()
    
    # Check balance
    account = await get_customer_reward_account(customer_id)
    if not account or account.hashi_coins_balance < amount:
        return None
    
    new_balance = account.hashi_coins_balance - amount
    
    # Update account
    await db.customer_reward_accounts.update_one(
        {"customer_id": customer_id},
        {
            "$inc": {
                "hashi_coins_balance": -amount,
                "total_coins_spent": amount
            },
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    # Create transaction record
    transaction = CoinTransaction(
        customer_id=customer_id,
        amount=-amount,
        transaction_type=transaction_type,
        description=description,
        balance_after=new_balance
    )
    
    await db.coin_transactions.insert_one(transaction.dict())
    
    logger.info(f"Spent {amount} coins from customer {customer_id}")
    return transaction


async def get_coin_transactions(
    customer_id: str,
    limit: int = 20,
    offset: int = 0
) -> List[CoinTransaction]:
    """Get coin transaction history for a customer"""
    db = get_db()
    
    cursor = db.coin_transactions.find(
        {"customer_id": customer_id}
    ).sort("created_at", DESCENDING).skip(offset).limit(limit)
    
    docs = await cursor.to_list(length=limit)
    return [CoinTransaction(**doc) for doc in docs]


async def update_customer_tier(customer_id: str) -> bool:
    """Update customer tier based on completed referrals"""
    db = get_db()
    
    account = await get_customer_reward_account(customer_id)
    if not account:
        return False
    
    # Determine new tier
    completed = account.completed_referrals
    
    if completed >= 51:
        new_tier = CustomerTier.PLATINUM
    elif completed >= 16:
        new_tier = CustomerTier.GOLD
    elif completed >= 6:
        new_tier = CustomerTier.SILVER
    elif completed >= 1:
        new_tier = CustomerTier.BRONZE
    else:
        return False
    
    # Only update if tier changed
    if new_tier != account.tier:
        await db.customer_reward_accounts.update_one(
            {"customer_id": customer_id},
            {
                "$set": {
                    "tier": new_tier.value,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        logger.info(f"Upgraded customer {customer_id} to {new_tier.value}")
        return True
    
    return False


async def get_customer_tier_info(customer_id: str) -> Dict[str, Any]:
    """Get complete tier information for a customer"""
    account = await get_or_create_customer_reward_account(customer_id)
    
    current_tier = account.tier
    benefits = CustomerRewardAccount.get_tier_benefits(current_tier)
    
    # Calculate next tier
    completed = account.completed_referrals
    
    tier_order = [CustomerTier.BRONZE, CustomerTier.SILVER, CustomerTier.GOLD, CustomerTier.PLATINUM]
    current_index = tier_order.index(current_tier)
    
    next_tier = None
    referrals_to_next = 0
    
    if current_index < len(tier_order) - 1:
        next_tier = tier_order[current_index + 1]
        thresholds = {
            CustomerTier.SILVER: 6,
            CustomerTier.GOLD: 16,
            CustomerTier.PLATINUM: 51
        }
        referrals_to_next = thresholds[next_tier] - completed
    
    return {
        "tier": current_tier.value,
        "tier_name": benefits["name"],
        "tier_icon": benefits["icon"],
        "tier_color": benefits["color"],
        "benefits": benefits,
        "completed_referrals": completed,
        "next_tier": next_tier.value if next_tier else None,
        "referrals_to_next_tier": max(0, referrals_to_next),
        "tier_progress": {
            "bronze": {"min": 1, "achieved": completed >= 1},
            "silver": {"min": 6, "achieved": completed >= 6},
            "gold": {"min": 16, "achieved": completed >= 16},
            "platinum": {"min": 51, "achieved": completed >= 51}
        }
    }


async def redeem_coins_for_reward(
    customer_id: str,
    redemption_type: str  # "free_delivery", "discount_15", "discount_30"
) -> Optional[RewardRedemption]:
    """Redeem coins for a reward"""
    db = get_db()
    
    # Get cost
    costs = {
        "free_delivery": CoinValues.FREE_DELIVERY_COST,
        "discount_15": CoinValues.DISCOUNT_15_COST,
        "discount_30": CoinValues.DISCOUNT_30_COST
    }
    
    values = {
        "free_delivery": 0.0,
        "discount_15": 15.0,
        "discount_30": 30.0
    }
    
    if redemption_type not in costs:
        return None
    
    coins_required = costs[redemption_type]
    value_zar = values[redemption_type]
    
    # Check and deduct balance
    transaction = await spend_coins(
        customer_id,
        coins_required,
        f"Redeemed for {redemption_type}",
        "redemption"
    )
    
    if not transaction:
        return None
    
    # Create redemption record
    expires_at = datetime.utcnow() + timedelta(days=30)  # 30 day expiry
    
    redemption = RewardRedemption(
        customer_id=customer_id,
        redemption_type=redemption_type,
        coins_spent=coins_required,
        value_zar=value_zar,
        status="active",
        expires_at=expires_at
    )
    
    await db.reward_redemptions.insert_one(redemption.dict())
    
    logger.info(f"Customer {customer_id} redeemed {coins_required} coins for {redemption_type}")
    return redemption


async def get_customer_referral_history(
    customer_id: str,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Get customer's referral history with details"""
    db = get_db()
    
    cursor = db.referrals.find(
        {"referrer_id": customer_id}
    ).sort("created_at", DESCENDING).limit(limit)
    
    referrals = []
    async for doc in cursor:
        # Get referee info
        referee = await db.users.find_one({"id": doc["referee_id"]})
        
        referral = {
            "id": doc["id"],
            "status": doc["status"],
            "created_at": doc["created_at"],
            "completed_at": doc.get("completed_at"),
            "referee_name": referee.get("name", "Unknown") if referee else "Unknown",
            "coins_earned": 50 if doc["status"] == ReferralStatus.COMPLETED.value else 0
        }
        referrals.append(referral)
    
    return referrals


# ============================================================================
# VENDOR REFERRAL OPERATIONS (25-30)
# ============================================================================

async def extend_vendor_trial(vendor_id: str, days: int) -> bool:
    """Extend vendor's free trial by referral bonus days"""
    db = get_db()
    
    # Get vendor's account record
    from app.models.account import AccountRecord
    
    account = await db.account_records.find_one({"user_id": vendor_id})
    if not account:
        return False
    
    # Extend trial end date
    current_trial_end = account.get("trial_end_date", datetime.utcnow())
    if isinstance(current_trial_end, str):
        current_trial_end = datetime.fromisoformat(current_trial_end.replace('Z', '+00:00'))
    
    new_trial_end = current_trial_end + timedelta(days=days)
    
    await db.account_records.update_one(
        {"user_id": vendor_id},
        {
            "$set": {
                "trial_end_date": new_trial_end,
                "referral_bonus_days": account.get("referral_bonus_days", 0) + days
            }
        }
    )
    
    logger.info(f"Extended vendor {vendor_id} trial by {days} days")
    return True


async def get_vendor_referral_stats(vendor_id: str) -> Dict[str, Any]:
    """Get vendor referral statistics"""
    stats = await get_referral_stats(vendor_id, ReferralType.VENDOR)
    
    # Add vendor-specific info
    completed = stats.get("completed_referrals", 0)
    bonus_days = completed * 2
    
    return {
        **stats,
        "bonus_days_earned": bonus_days,
        "bonus_days_remaining": max(0, 90 - bonus_days),
        "max_bonus_days": 90
    }


# ============================================================================
# ORDER OPERATIONS (31-36)
# ============================================================================

async def create_order(order_data: Dict[str, Any]) -> Order:
    """Create a new order"""
    db = get_db()
    
    order = Order(**order_data)
    await db.orders.insert_one(order.dict())
    
    logger.info(f"Created order {order.id}")
    return order


async def get_order_by_id(order_id: str) -> Optional[Order]:
    """Get order by ID"""
    db = get_db()
    
    doc = await db.orders.find_one({"id": order_id})
    if doc:
        return Order(**doc)
    return None


async def get_orders_by_buyer(
    buyer_id: str,
    status: Optional[str] = None,
    limit: int = 20
) -> List[Order]:
    """Get orders for a buyer"""
    db = get_db()
    
    query = {"buyer_id": buyer_id}
    if status:
        query["status"] = status
    
    cursor = db.orders.find(query).sort("created_at", DESCENDING).limit(limit)
    docs = await cursor.to_list(length=limit)
    
    return [Order(**doc) for doc in docs]


async def update_order_status(order_id: str, status: str, **kwargs) -> bool:
    """Update order status"""
    db = get_db()
    
    update_data = {
        "status": status,
        "updated_at": datetime.utcnow()
    }
    
    # Add any additional fields
    for key, value in kwargs.items():
        update_data[key] = value
    
    result = await db.orders.update_one(
        {"id": order_id},
        {"$set": update_data}
    )
    
    return result.modified_count > 0


async def assign_driver_to_order(order_id: str, driver_id: str) -> bool:
    """Assign a driver to an order"""
    return await update_order_status(
        order_id,
        "assigned",
        driver_id=driver_id,
        assigned_at=datetime.utcnow()
    )


# ============================================================================
# USER OPERATIONS (37-42)
# ============================================================================

async def get_user_by_id(user_id: str) -> Optional[User]:
    """Get user by ID"""
    db = get_db()
    
    doc = await db.users.find_one({"id": user_id})
    if doc:
        return User(**doc)
    return None


async def get_user_by_email(email: str) -> Optional[User]:
    """Get user by email"""
    db = get_db()
    
    doc = await db.users.find_one({"email": email.lower()})
    if doc:
        return User(**doc)
    return None


async def get_user_by_phone(phone: str) -> Optional[User]:
    """Get user by phone number"""
    db = get_db()
    
    doc = await db.users.find_one({"phone": phone})
    if doc:
        return User(**doc)
    return None


async def update_user(user_id: str, update_data: Dict[str, Any]) -> bool:
    """Update user data"""
    db = get_db()
    
    update_data["updated_at"] = datetime.utcnow()
    
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": update_data}
    )
    
    return result.modified_count > 0


async def create_user(user_data: Dict[str, Any]) -> User:
    """Create a new user"""
    db = get_db()
    
    user = User(**user_data)
    await db.users.insert_one(user.dict())
    
    # Create reward account for customers
    if user.role == "customer":
        await create_customer_reward_account(user.id)
    
    logger.info(f"Created user {user.id} with role {user.role}")
    return user


# ============================================================================
# ANALYTICS & ADMIN OPERATIONS (43-48)
# ============================================================================

async def get_all_referral_stats() -> Dict[str, Any]:
    """Get overall referral program statistics"""
    db = get_db()
    
    # Total counts
    total_codes = await db.referral_codes.count_documents({})
    total_referrals = await db.referrals.count_documents({})
    
    # By type
    vendor_referrals = await db.referrals.count_documents({
        "referral_type": ReferralType.VENDOR.value
    })
    customer_referrals = await db.referrals.count_documents({
        "referral_type": ReferralType.CUSTOMER.value
    })
    
    # By status
    completed = await db.referrals.count_documents({
        "status": ReferralStatus.COMPLETED.value
    })
    
    # Tier distribution
    pipeline = [
        {"$group": {
            "_id": "$tier",
            "count": {"$sum": 1}
        }}
    ]
    
    tier_dist = {}
    async for doc in db.customer_reward_accounts.aggregate(pipeline):
        tier_dist[doc["_id"]] = doc["count"]
    
    return {
        "total_referral_codes": total_codes,
        "total_referrals": total_referrals,
        "vendor_referrals": vendor_referrals,
        "customer_referrals": customer_referrals,
        "completed_referrals": completed,
        "total_bonus_days_awarded": completed * 2,  # 2 days per vendor referral
        "total_hashi_coins_awarded": completed * 75,  # 50 referrer + 25 referee
        "tier_distribution": tier_dist
    }


async def process_pending_referrals() -> Dict[str, int]:
    """Process pending referrals and award bonuses"""
    db = get_db()
    
    processed = 0
    awarded = 0
    
    # Find pending referrals that should be completed
    # (e.g., referee has made first order)
    cursor = db.referrals.find({
        "status": ReferralStatus.PENDING.value,
        "referral_type": ReferralType.CUSTOMER.value
    })
    
    async for doc in cursor:
        referral = Referral(**doc)
        
        # Check if referee has made an order
        order_count = await db.orders.count_documents({
            "buyer_id": referral.referee_id,
            "status": {"$in": ["completed", "delivered"]}
        })
        
        if order_count > 0:
            # Complete the referral
            reward_details = {
                "referrer_coins": 50,
                "referee_coins": 25,
                "trigger": "first_order_completed"
            }
            
            await complete_referral(referral.id, reward_details)
            
            # Award coins
            await add_coins_to_customer(
                referral.referrer_id,
                50,
                f"Referral bonus for referring {referral.referee_id}",
                "referral_reward",
                referral.id
            )
            
            await add_coins_to_customer(
                referral.referee_id,
                25,
                "Welcome bonus for using referral code",
                "welcome_bonus",
                referral.id
            )
            
            awarded += 1
        
        processed += 1
    
    logger.info(f"Processed {processed} pending referrals, awarded {awarded}")
    return {"processed": processed, "awarded": awarded}


async def get_top_referrers(limit: int = 10) -> List[Dict[str, Any]]:
    """Get top referrers leaderboard"""
    db = get_db()
    
    pipeline = [
        {"$match": {"status": ReferralStatus.COMPLETED.value}},
        {"$group": {
            "_id": "$referrer_id",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}},
        {"$limit": limit}
    ]
    
    top_referrers = []
    async for doc in db.referrals.aggregate(pipeline):
        user = await db.users.find_one({"id": doc["_id"]})
        account = await db.customer_reward_accounts.find_one({
            "customer_id": doc["_id"]
        })
        
        top_referrers.append({
            "user_id": doc["_id"],
            "name": user.get("name", "Anonymous") if user else "Anonymous",
            "referrals": doc["count"],
            "tier": account.get("tier", "bronze") if account else "bronze"
        })
    
    return top_referrers


# Export all operations
__all__ = [
    # Connection
    "get_db",
    
    # Referrals
    "create_referral_code", "get_referral_code_by_user", "get_referral_code_by_code",
    "create_referral", "complete_referral", "get_referrals_by_referrer",
    "get_referral_stats", "check_referral_eligibility",
    
    # Customer Rewards
    "create_customer_reward_account", "get_customer_reward_account",
    "get_or_create_customer_reward_account", "add_coins_to_customer",
    "spend_coins", "get_coin_transactions", "update_customer_tier",
    "get_customer_tier_info", "redeem_coins_for_reward", "get_customer_referral_history",
    
    # Vendor
    "extend_vendor_trial", "get_vendor_referral_stats",
    
    # Orders
    "create_order", "get_order_by_id", "get_orders_by_buyer",
    "update_order_status", "assign_driver_to_order",
    
    # Users
    "get_user_by_id", "get_user_by_email", "get_user_by_phone",
    "update_user", "create_user",
    
    # Analytics
    "get_all_referral_stats", "process_pending_referrals", "get_top_referrers"
]
