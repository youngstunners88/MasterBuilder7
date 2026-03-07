from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field


class DeliveryStatus(str, Enum):
    PENDING = "pending"  # Order placed, waiting for rider assignment
    RIDER_ASSIGNED = "rider_assigned"  # Rider matched, heading to merchant
    AT_MERCHANT = "at_merchant"  # Rider at pickup location (merchant)
    PICKED_UP = "picked_up"  # Order collected from merchant
    IN_TRANSIT = "in_transit"  # Delivery underway to customer
    ARRIVED = "arrived"  # Rider at delivery location
    DELIVERED = "delivered"  # Order handed to customer
    CANCELLED = "cancelled"  # Delivery cancelled


class DeliveryVehicleType(str, Enum):
    BIKE = "bike"  # Motorcycle/scooter
    CAR = "car"  # Car/bakkie
    BICYCLE = "bicycle"  # Bicycle
    WALKING = "walking"  # On foot


class Location(BaseModel):
    """GPS location"""
    latitude: float
    longitude: float
    address: Optional[str] = None
    landmark: Optional[str] = None  # Useful for SA addresses


class DeliveryFare(BaseModel):
    """Delivery fee breakdown"""
    base_fee: float  # Base delivery charge
    distance_km: float
    distance_cost: float
    time_cost: float = 0.0
    surge_multiplier: float = 1.0  # Peak time pricing
    tip: float = 0.0
    total: float
    currency: str = "ZAR"


class DeliveryProof(BaseModel):
    """Proof of delivery"""
    photo_url: Optional[str] = None  # Photo of delivered items
    signature: Optional[str] = None  # Customer signature (base64)
    recipient_name: Optional[str] = None  # Who received the delivery
    notes: Optional[str] = None


class Delivery(BaseModel):
    """Delivery model for orders"""
    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    
    # Parties
    order_id: str  # Reference to the order
    customer_id: str
    merchant_id: str
    rider_id: Optional[str] = None
    
    # Locations
    pickup_location: Location  # Merchant location
    delivery_location: Location  # Customer delivery address
    
    # Delivery details
    vehicle_type: DeliveryVehicleType = DeliveryVehicleType.BIKE
    status: DeliveryStatus = DeliveryStatus.PENDING
    
    # Items being delivered
    item_count: int = 1
    special_instructions: Optional[str] = None  # "Leave at gate", etc.
    
    # Fare
    fare: Optional[DeliveryFare] = None
    payment_method: str = "card"  # card, cash, eft
    payment_status: str = "pending"
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    rider_assigned_at: Optional[datetime] = None
    pickup_time: Optional[datetime] = None
    delivery_time: Optional[datetime] = None
    
    # Status tracking
    cancel_reason: Optional[str] = None
    cancellation_time: Optional[datetime] = None
    
    # Proof of delivery
    delivery_proof: Optional[DeliveryProof] = None
    
    # Rating
    customer_rating: Optional[int] = None  # 1-5 stars
    rider_rating: Optional[int] = None  # 1-5 stars
    
    class Config:
        json_schema_extra = {
            "example": {
                "order_id": "order-123",
                "customer_id": "customer-456",
                "merchant_id": "merchant-789",
                "pickup_location": {
                    "latitude": -26.2041,
                    "longitude": 28.0473,
                    "address": "Shop 5, Mall of Africa, Johannesburg"
                },
                "delivery_location": {
                    "latitude": -26.1951,
                    "longitude": 28.0339,
                    "address": "123 Soweto Street, Soweto",
                    "landmark": "Near the spaza shop"
                },
                "vehicle_type": "bike",
                "item_count": 3,
                "special_instructions": "Please call when arriving"
            }
        }


class DeliveryRequest(BaseModel):
    """Request to create a delivery"""
    order_id: str
    pickup_latitude: float
    pickup_longitude: float
    pickup_address: Optional[str] = None
    delivery_latitude: float
    delivery_longitude: float
    delivery_address: Optional[str] = None
    delivery_landmark: Optional[str] = None
    vehicle_type: DeliveryVehicleType = DeliveryVehicleType.BIKE
    item_count: int = 1
    special_instructions: Optional[str] = None
    payment_method: str = "card"


class DeliveryLocationUpdate(BaseModel):
    """Rider location update during delivery"""
    latitude: float
    longitude: float


class DeliveryCompleteRequest(BaseModel):
    """Request to mark delivery complete"""
    recipient_name: Optional[str] = None
    notes: Optional[str] = None


# Alias for backwards compatibility
DeliveryCreate = DeliveryRequest

# Trip aliases for backwards compatibility
# Re-define TripStatus directly since we can't extend DeliveryStatus
class TripStatus(str, Enum):
    PENDING = "pending"
    RIDER_ASSIGNED = "rider_assigned"
    AT_MERCHANT = "at_merchant"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    ARRIVED = "arrived"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


Trip = Delivery
TripCreate = DeliveryRequest