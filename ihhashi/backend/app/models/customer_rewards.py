from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field


class CustomerTier(str, Enum):
    """Customer reward tiers based on referral count"""
    BRONZE = "bronze"      # 1-5 referrals
    SILVER = "silver"      # 6-15 referrals
    GOLD = "gold"          # 16-50 referrals
    PLATINUM = "platinum"  # 51+ referrals


class CoinTransaction(BaseModel):
    """A iHhashi Coin transaction"""
    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    customer_id: str
    amount: int  # Positive for earning, negative for spending
    transaction_type: str  # "referral_reward", "welcome_bonus", "redemption", "purchase_bonus"
    description: str
    related_referral_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    balance_after: int = 0


class CustomerRewardAccount(BaseModel):
    """Customer's reward account with iHhashi Coins and tier status"""
    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    customer_id: str
    referral_code: str  # Their unique referral code
    
    # Tier system
    tier: CustomerTier = CustomerTier.BRONZE
    
    # iHhashi Coins (virtual currency)
    hashi_coins_balance: int = 0
    total_coins_earned: int = 0
    total_coins_spent: int = 0
    
    # Referral tracking
    total_referrals: int = 0
    completed_referrals: int = 0
    pending_referrals: int = 0
    
    # Reward credits
    free_delivery_credits: int = 0  # Number of free deliveries available
    discount_credits: float = 0.0   # ZAR value of discount coupons
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_referral_at: Optional[datetime] = None
    
    def update_tier(self) -> bool:
        """Update tier based on referral count. Returns True if tier changed."""
        old_tier = self.tier
        
        if self.completed_referrals >= 51:
            self.tier = CustomerTier.PLATINUM
        elif self.completed_referrals >= 16:
            self.tier = CustomerTier.GOLD
        elif self.completed_referrals >= 6:
            self.tier = CustomerTier.SILVER
        elif self.completed_referrals >= 1:
            self.tier = CustomerTier.BRONZE
        
        return self.tier != old_tier
    
    def add_coins(self, amount: int, description: str, transaction_type: str = "referral_reward") -> CoinTransaction:
        """Add iHhashi Coins to account"""
        self.hashi_coins_balance += amount
        self.total_coins_earned += amount
        self.updated_at = datetime.utcnow()
        
        return CoinTransaction(
            customer_id=self.customer_id,
            amount=amount,
            transaction_type=transaction_type,
            description=description,
            balance_after=self.hashi_coins_balance
        )
    
    def spend_coins(self, amount: int, description: str, transaction_type: str = "redemption") -> Optional[CoinTransaction]:
        """Spend iHhashi Coins. Returns None if insufficient balance."""
        if self.hashi_coins_balance < amount:
            return None
        
        self.hashi_coins_balance -= amount
        self.total_coins_spent += amount
        self.updated_at = datetime.utcnow()
        
        return CoinTransaction(
            customer_id=self.customer_id,
            amount=-amount,
            transaction_type=transaction_type,
            description=description,
            balance_after=self.hashi_coins_balance
        )
    
    @staticmethod
    def get_tier_benefits(tier: CustomerTier) -> dict:
        """Get benefits for a specific tier"""
        benefits = {
            CustomerTier.BRONZE: {
                "name": "Bronze",
                "discount_percent": 5,
                "free_deliveries_per_month": 0,
                "support_level": "Standard",
                "exclusive_offers": False,
                "early_access": False,
                "icon": "🥉",
                "color": "#CD7F32"
            },
            CustomerTier.SILVER: {
                "name": "Silver",
                "discount_percent": 10,
                "free_deliveries_per_month": 1,
                "support_level": "Priority",
                "exclusive_offers": True,
                "early_access": False,
                "icon": "🥈",
                "color": "#C0C0C0"
            },
            CustomerTier.GOLD: {
                "name": "Gold",
                "discount_percent": 15,
                "free_deliveries_per_month": 2,
                "support_level": "VIP",
                "exclusive_offers": True,
                "early_access": True,
                "icon": "🥇",
                "color": "#FFD700"
            },
            CustomerTier.PLATINUM: {
                "name": "Platinum",
                "discount_percent": 20,
                "free_deliveries_per_month": -1,  # Unlimited
                "support_level": "Dedicated Manager",
                "exclusive_offers": True,
                "early_access": True,
                "icon": "💎",
                "color": "#E5E4E2"
            }
        }
        return benefits.get(tier, benefits[CustomerTier.BRONZE])


class RewardRedemption(BaseModel):
    """A reward redemption record"""
    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    customer_id: str
    redemption_type: str  # "free_delivery", "discount_15", "discount_30", "special_offer"
    coins_spent: int
    value_zar: float  # The value of the reward in ZAR
    status: str = "active"  # "active", "used", "expired"
    expires_at: Optional[datetime] = None
    used_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Coin values and redemption rates
class CoinValues:
    """Constants for coin values and redemption"""
    COIN_VALUE_ZAR = 0.10  # 1 coin = 10 cents
    
    # Earning coins
    REFERRAL_BONUS_REFERRER = 50  # Coins for referring someone
    REFERRAL_BONUS_REFEREE = 25   # Coins for new user using referral
    FIRST_ORDER_BONUS = 20        # Coins for first order
    
    # Redemption options
    FREE_DELIVERY_COST = 100      # 100 coins = free delivery (~R10 value)
    DISCOUNT_15_COST = 150        # 150 coins = R15 discount
    DISCOUNT_30_COST = 300        # 300 coins = R30 discount
    
    # Tier thresholds
    BRONZE_MIN = 1
    SILVER_MIN = 6
    GOLD_MIN = 16
    PLATINUM_MIN = 51
