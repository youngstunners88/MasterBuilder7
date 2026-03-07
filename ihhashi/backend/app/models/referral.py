from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field
import secrets
import string


class ReferralStatus(str, Enum):
    """Status of a referral"""
    PENDING = "pending"  # Referred user signed up but hasn't completed action
    COMPLETED = "completed"  # Referral bonus awarded
    EXPIRED = "expired"  # Referral code expired or invalid


class ReferralType(str, Enum):
    """Type of referral program"""
    VENDOR = "vendor"  # Vendor referring other vendors
    CUSTOMER = "customer"  # Customer referring other customers


class ReferralCode(BaseModel):
    """Unique referral code for a user"""
    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    user_id: str
    code: str
    referral_type: ReferralType
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    expires_at: Optional[datetime] = None  # None means no expiry
    
    @staticmethod
    def generate_code(prefix: str = "IH") -> str:
        """Generate a unique referral code like IH-ABC123"""
        chars = string.ascii_uppercase + string.digits
        random_part = ''.join(secrets.choice(chars) for _ in range(6))
        return f"{prefix}-{random_part}"


class Referral(BaseModel):
    """A referral record - when someone uses a referral code"""
    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    referrer_id: str  # User who shared the code
    referee_id: str  # User who signed up with the code
    referral_code: str  # The code used
    referral_type: ReferralType
    status: ReferralStatus = ReferralStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Reward details
    reward_applied: bool = False
    reward_details: Optional[dict] = None  # e.g., {"bonus_days": 2, "coins": 50}


class VendorReferralStats(BaseModel):
    """Vendor referral statistics"""
    vendor_id: str
    referral_code: str
    total_referrals: int = 0
    completed_referrals: int = 0
    pending_referrals: int = 0
    bonus_days_earned: int = 0
    bonus_days_used: int = 0
    current_trial_extension: int = 0  # Days added to trial


class CustomerReferralStats(BaseModel):
    """Customer referral statistics and rewards"""
    customer_id: str
    referral_code: str
    total_referrals: int = 0
    completed_referrals: int = 0
    pending_referrals: int = 0
    
    # iHhashi Coins (virtual currency)
    hashi_coins_balance: int = 0
    hashi_coins_earned: int = 0
    hashi_coins_spent: int = 0
    
    # Tier system
    class Tier(str, Enum):
        BRONZE = "bronze"      # 1-5 referrals
        SILVER = "silver"      # 6-15 referrals
        GOLD = "gold"          # 16-50 referrals
        PLATINUM = "platinum"  # 51+ referrals
    
    tier: str = "bronze"
    
    # Rewards earned
    free_delivery_credits: int = 0
    discount_credits: float = 0.0  # In ZAR


class ReferralReward(BaseModel):
    """Reward configuration for referrals"""
    referral_type: ReferralType
    
    # Vendor rewards
    vendor_bonus_days_per_referral: int = 2
    vendor_max_bonus_days: int = 90  # Max 90 extra days (3 months)
    
    # Customer rewards (both parties get rewards)
    customer_referrer_coins: int = 50  # iHhashi Coins for referrer
    customer_referee_coins: int = 25   # iHhashi Coins for new user
    
    # Tier thresholds
    tier_bronze_min: int = 1
    tier_silver_min: int = 6
    tier_gold_min: int = 16
    tier_platinum_min: int = 51
    
    # Coin redemption rates
    coin_value_zar: float = 0.10  # 1 coin = 10 cents
    coins_for_free_delivery: int = 100  # 100 coins = free delivery
    coins_for_discount_10: int = 150    # 150 coins = R15 discount
    coins_for_discount_25: int = 300    # 300 coins = R30 discount
