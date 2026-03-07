from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field


class TransportMode(str, Enum):
    """Multi-modal transport for South Africa - inclusive of all delivery methods"""
    CAR = "car"
    MOTORCYCLE = "motorcycle"
    SCOOTER = "scooter"
    BICYCLE = "bicycle"
    ON_FOOT = "on_foot"
    WHEELCHAIR = "wheelchair"  # Inclusive - wheelchair users welcome
    RUNNING = "running"  # For fitness enthusiasts
    ROLLERBLADE = "rollerblade"  # Alternative eco transport


class DeliveryTier(str, Enum):
    """Delivery tiers based on transport mode"""
    EXPRESS = "express"  # Motorcycle/Scooter - fastest
    STANDARD = "standard"  # Car - reliable
    BUDGET = "budget"  # Bicycle/On-foot - eco-friendly, affordable
    ECO = "eco"  # Bicycle only


class DeliveryPricing(BaseModel):
    """Delivery pricing set by serviceman - competitive pricing"""
    base_fee: float  # Starting fee in ZAR
    per_km_rate: float  # Rate per kilometre
    per_minute_rate: float = 0.0  # Rate per minute (optional)
    minimum_fee: float = 15.0  # Minimum delivery fee
    maximum_distance_km: float = 15.0  # Max delivery radius
    surge_multiplier: float = 1.0  # During peak times
    
    # Transport mode affects default rates
    transport_mode: TransportMode = TransportMode.ON_FOOT


class DeliveryOffer(BaseModel):
    """A delivery serviceman's offer for an order"""
    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    serviceman_id: str
    order_id: str
    
    # Pricing (set by serviceman)
    delivery_fee: float
    estimated_time_minutes: int
    
    # Transport details
    transport_mode: TransportMode
    can_handle_size: str = "medium"  # small, medium, large
    can_handle_weight_kg: float = 10.0
    
    # Current location
    pickup_distance_km: float
    total_distance_km: float
    
    # Serviceman rating
    serviceman_rating: float
    total_deliveries: int
    has_blue_horse: bool = False
    
    # Timestamp
    offered_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime  # Offer expires
    
    # Status
    is_accepted: bool = False


class DeliveryServiceMan(BaseModel):
    """Delivery serviceman profile"""
    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    user_id: str
    
    # Profile
    full_name: str
    phone: str
    profile_photo: Optional[str] = None
    
    # Transport
    transport_mode: TransportMode = TransportMode.ON_FOOT
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_year: Optional[int] = None
    vehicle_color: Optional[str] = None
    number_plate: Optional[str] = None
    
    # Status
    is_online: bool = False
    is_available: bool = True
    current_location: Optional[dict] = None  # {lat, lng}
    
    # Pricing (serviceman sets their own rates)
    pricing: DeliveryPricing
    
    # Stats
    rating: float = 5.0
    total_deliveries: int = 0
    total_earnings: float = 0.0
    completed_today: int = 0
    
    # Verification
    is_verified: bool = False
    blue_horse_verified: bool = False
    
    # Banking
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Tip(BaseModel):
    """Tip for delivery serviceman - platform takes NO fee"""
    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    order_id: str
    customer_id: str
    serviceman_id: str
    
    amount: float  # In ZAR
    message: Optional[str] = None
    
    # 100% goes to serviceman
    platform_fee: float = 0.0  # Always 0 - platform takes no cut of tips
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Aliases for backwards compatibility with models/__init__.py
Delivery = DeliveryServiceMan


class DeliveryCreate(BaseModel):
    """Schema for creating a delivery serviceman profile"""
    full_name: str
    phone: str
    transport_mode: TransportMode = TransportMode.ON_FOOT
    base_fee: float = 20.0
    per_km_rate: float = 5.0
    minimum_fee: float = 15.0