from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    PENDING = "pending"  # Just placed, waiting for store confirmation
    CONFIRMED = "confirmed"  # Store accepted
    PREPARING = "preparing"  # Being packed
    READY = "ready"  # Ready for pickup by rider
    PICKED_UP = "picked_up"  # Rider has it
    IN_TRANSIT = "in_transit"  # On the way
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class OrderItem(BaseModel):
    """Single item in an order"""
    product_id: str
    product_name: str  # Snapshot at time of order
    quantity: int
    unit_price: float
    total_price: float


class DeliveryInfo(BaseModel):
    """Delivery details for an order"""
    address_label: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    area: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    delivery_instructions: Optional[str] = None
    recipient_phone: str


class Order(BaseModel):
    """Order placed by a buyer"""
    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    
    # Parties
    buyer_id: str
    store_id: str
    rider_id: Optional[str] = None
    
    # Items
    items: List[OrderItem]
    
    # Pricing
    subtotal: float
    delivery_fee: float
    total: float
    currency: str = "ZAR"
    
    # Status
    status: OrderStatus = OrderStatus.PENDING
    status_history: List[dict] = []  # Track status changes
    
    # Delivery
    delivery_info: DeliveryInfo
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    confirmed_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    estimated_delivery: Optional[datetime] = None
    
    # Payment
    payment_method: str = "cash"  # or "card", "wallet"
    payment_status: str = "pending"  # pending, paid, failed, refunded
    
    # Notes
    buyer_notes: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "buyer_id": "buyer-123",
                "store_id": "store-456",
                "items": [{
                    "product_id": "prod-789",
                    "product_name": "Bic Ballpoint Pens (Pack of 10)",
                    "quantity": 2,
                    "unit_price": 35.00,
                    "total_price": 70.00
                }],
                "subtotal": 70.00,
                "delivery_fee": 25.00,
                "total": 95.00,
                "delivery_info": {
                    "address_label": "Work",
                    "address_line1": "45 Office Park",
                    "city": "Johannesburg",
                    "area": "Sandton",
                    "recipient_phone": "+27821234567"
                }
            }
        }


class OrderCreate(BaseModel):
    store_id: str
    items: List[dict]  # [{product_id, quantity}]
    delivery_address_id: str
    payment_method: str = "cash"
    buyer_notes: Optional[str] = None


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    notes: Optional[str] = None