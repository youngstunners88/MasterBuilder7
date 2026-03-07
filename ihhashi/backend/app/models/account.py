from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field


class WarningType(str, Enum):
    """Types of warnings for policy violations"""
    ORDER_FRAUD = "order_fraud"
    LATE_DELIVERY = "late_delivery"
    ORDER_CANCELLATION = "order_cancellation"
    CUSTOMER_COMPLAINT = "customer_complaint"
    INAPPROPRIATE_BEHAVIOUR = "inappropriate_behaviour"
    FAKE_LISTING = "fake_listing"
    PRICE_MANIPULATION = "price_manipulation"
    DELIVERY_DAMAGE = "delivery_damage"
    NO_SHOW = "no_show"
    HARASSMENT = "harassment"


class SuspensionReason(str, Enum):
    """Reasons for account suspension"""
    EXCESSIVE_WARNINGS = "excessive_warnings"
    SUSPECTED_FRAUD = "suspected_fraud"
    PAYMENT_ISSUES = "payment_issues"
    POLICY_VIOLATION = "policy_violation"
    INVESTIGATION = "investigation"


class TerminationReason(str, Enum):
    """Reasons for permanent account termination"""
    CRIMINAL_ACTIVITY = "criminal_activity"
    FRAUD = "fraud"
    THEFT = "theft"
    VIOLENCE = "violence"
    REPEATED_VIOLATIONS = "repeated_violations"
    ILLEGAL_SUBSTANCES = "illegal_substances"
    MONEY_LAUNDERING = "money_laundering"
    IDENTITY_FRAUD = "identity_fraud"


class UserWarning(BaseModel):
    """A warning issued to a user"""
    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    warning_type: WarningType
    description: str
    order_id: Optional[str] = None
    reported_by: Optional[str] = None  # User ID who reported
    issued_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None


class AccountStatus(str, Enum):
    ACTIVE = "active"
    FREE_TRIAL = "free_trial"  # 45-day free trial
    WARNING = "warning"  # Has active warnings
    SUSPENDED = "suspended"  # Temporarily suspended
    TERMINATED = "terminated"  # Permanent ban


class AccountRecord(BaseModel):
    """User account status and history"""
    user_id: str
    status: AccountStatus = AccountStatus.FREE_TRIAL
    
    # Free trial tracking
    trial_started_at: datetime = Field(default_factory=datetime.utcnow)
    trial_ends_at: Optional[datetime] = None  # 45 days from trial_started_at
    
    # Referral system - Bonus days from vendor referrals
    referral_code: Optional[str] = None  # User's own referral code
    referred_by: Optional[str] = None  # Referral code used during signup
    bonus_days_from_referrals: int = 0  # Extra days earned from referrals
    max_bonus_days: int = 90  # Maximum bonus days allowed (3 months)
    
    # Warning system
    warnings: List[UserWarning] = []
    warning_count: int = 0
    max_warnings: int = 3  # Auto-suspend after 3 warnings
    
    # Suspension tracking
    suspended_at: Optional[datetime] = None
    suspension_reason: Optional[SuspensionReason] = None
    suspension_ends_at: Optional[datetime] = None
    
    # Termination
    terminated_at: Optional[datetime] = None
    termination_reason: Optional[TerminationReason] = None
    
    # Stats
    total_orders: int = 0
    completed_orders: int = 0
    cancelled_orders: int = 0
    total_spent: float = 0.0
    
    @property
    def is_trial_active(self) -> bool:
        if self.status != AccountStatus.FREE_TRIAL:
            return False
        if self.trial_ends_at is None:
            return True
        # Include bonus days in trial end calculation
        effective_end = self._get_effective_trial_end()
        return datetime.utcnow() < effective_end
    
    def _get_effective_trial_end(self) -> datetime:
        """Calculate trial end including bonus days from referrals"""
        if self.trial_ends_at is None:
            return datetime.utcnow()
        bonus_seconds = self.bonus_days_from_referrals * 24 * 60 * 60
        return self.trial_ends_at + timedelta(seconds=bonus_seconds)
    
    @property
    def trial_days_remaining(self) -> int:
        if not self.is_trial_active:
            return 0
        if self.trial_ends_at is None:
            return 45 + self.bonus_days_from_referrals
        effective_end = self._get_effective_trial_end()
        delta = effective_end - datetime.utcnow()
        return max(0, delta.days)
    
    def add_referral_bonus(self, days: int = 2) -> dict:
        """Add bonus days from a referral. Returns result dict."""
        if self.bonus_days_from_referrals >= self.max_bonus_days:
            return {
                "success": False,
                "message": "Maximum bonus days already reached",
                "current_bonus": self.bonus_days_from_referrals,
                "max_bonus": self.max_bonus_days
            }
        
        new_bonus = min(days, self.max_bonus_days - self.bonus_days_from_referrals)
        self.bonus_days_from_referrals += new_bonus
        
        return {
            "success": True,
            "message": f"Added {new_bonus} bonus days to your trial!",
            "bonus_added": new_bonus,
            "total_bonus_days": self.bonus_days_from_referrals,
            "trial_days_remaining": self.trial_days_remaining
        }
    
    def issue_warning(self, warning: UserWarning) -> bool:
        """Issue a warning and check if suspension needed"""
        self.warnings.append(warning)
        self.warning_count = len([w for w in self.warnings if not w.acknowledged])
        
        if self.warning_count >= self.max_warnings:
            self.status = AccountStatus.SUSPENDED
            self.suspended_at = datetime.utcnow()
            self.suspension_reason = SuspensionReason.EXCESSIVE_WARNINGS
            return True  # Suspended
        return False
    
    def terminate(self, reason: TerminationReason):
        """Permanently terminate account"""
        self.status = AccountStatus.TERMINATED
        self.terminated_at = datetime.utcnow()
        self.termination_reason = reason


# Import timedelta for the new methods
from datetime import timedelta