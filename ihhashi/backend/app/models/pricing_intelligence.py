"""
Pricing Intelligence Models for iHhashi

Tracks pricing performance, conversion rates, and revenue metrics.
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field
from bson import ObjectId


class PricingTier(str, Enum):
    ECONOMY = "economy"
    STANDARD = "standard"
    PREMIUM = "premium"


class OfferType(str, Enum):
    FREE_DELIVERY = "free_delivery"
    PERCENTAGE_OFF = "percentage_off"
    FIXED_DISCOUNT = "fixed_discount"
    BOGO = "buy_one_get_one"


class PricingGap(BaseModel):
    """Detected pricing gap or anomaly"""
    id: str = Field(default_factory=lambda: str(ObjectId()))
    merchant_id: str
    product_id: Optional[str] = None
    
    # Gap details
    our_price: float
    competitor_price: float
    gap_percentage: float
    gap_direction: str  # "higher" or "lower"
    
    # Impact
    estimated_lost_orders: int = 0
    estimated_lost_revenue: float = 0.0
    
    # Metadata
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolution_action: Optional[str] = None


class ConversionByTier(BaseModel):
    """Conversion metrics by customer tier"""
    tier: PricingTier
    period_start: datetime
    period_end: datetime
    
    # Metrics
    total_orders: int = 0
    completed_orders: int = 0
    cancelled_orders: int = 0
    conversion_rate: float = 0.0
    
    # Revenue
    total_revenue: float = 0.0
    avg_order_value: float = 0.0
    
    # Behaviour
    avg_delivery_time_minutes: float = 0.0
    repeat_order_rate: float = 0.0


class ChurnByOffer(BaseModel):
    """Customer churn analysis by offer type"""
    offer_type: OfferType
    period_start: datetime
    period_end: datetime
    
    # Acquisition
    customers_acquired: int = 0
    acquisition_cost: float = 0.0
    
    # Retention
    customers_retained_7d: int = 0
    customers_retained_30d: int = 0
    customers_retained_90d: int = 0
    
    # Churn
    churn_rate_7d: float = 0.0
    churn_rate_30d: float = 0.0
    churn_rate_90d: float = 0.0
    
    # LTV
    avg_lifetime_value: float = 0.0
    roi: float = 0.0


class DailyRevenueForecast(BaseModel):
    """Daily revenue actual vs forecast"""
    date: datetime
    forecast_amount: float
    actual_amount: float
    variance: float
    variance_percentage: float
    
    # Breakdown
    delivery_fees: float = 0.0
    merchant_commissions: float = 0.0
    tips: float = 0.0
    hashi_coins_redeemed: float = 0.0
    
    # Context
    order_count: int = 0
    avg_order_value: float = 0.0
    active_merchants: int = 0
    active_drivers: int = 0


class PricingIntelligenceReport(BaseModel):
    """Complete pricing intelligence report"""
    report_date: datetime = Field(default_factory=datetime.utcnow)
    period_start: datetime
    period_end: datetime
    
    # Key metrics
    total_revenue: float
    revenue_vs_forecast: float
    avg_conversion_rate: float
    avg_churn_rate: float
    
    # Gaps detected
    pricing_gaps: List[PricingGap] = []
    
    # Conversion by tier
    conversion_tiers: List[ConversionByTier] = []
    
    # Churn by offer
    offer_churn: List[ChurnByOffer] = []
    
    # Daily breakdown
    daily_revenue: List[DailyRevenueForecast] = []
    
    # Alerts
    alerts: List[dict] = []
    
    # Recommendations
    recommendations: List[str] = []


# Create schemas
class PricingGapCreate(BaseModel):
    merchant_id: str
    product_id: Optional[str] = None
    our_price: float
    competitor_price: float
    gap_direction: str


class ForecastInput(BaseModel):
    date: datetime
    forecast_amount: float
