from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field, EmailStr


class BuyerStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class DeliveryAddress(BaseModel):
    """Buyer's delivery address"""
    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    label: str  # "Home", "Work", etc.
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    area: Optional[str] = None  # Neighbourhood/local area
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_default: bool = False
    delivery_instructions: Optional[str] = None


class Buyer(BaseModel):
    """Core buyer model - everyday people ordering essentials"""
    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    phone_number: str = Field(..., unique=True, index=True)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    
    # Authentication
    otp_secret: Optional[str] = None
    otp_expires: Optional[datetime] = None
    is_verified: bool = False
    
    # Profile
    addresses: List[DeliveryAddress] = []
    default_address_id: Optional[str] = None
    
    # Status
    status: BuyerStatus = BuyerStatus.ACTIVE
    
    # Analytics (for understanding buyer behaviour)
    total_orders: int = 0
    total_spent: float = 0.0
    last_order_at: Optional[datetime] = None
    
    # Preferences
    preferred_categories: List[str] = []  # e.g., "utensils", "stationery"
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "phone_number": "+27821234567",
                "full_name": "Thandi Nkosi",
                "addresses": [{
                    "label": "Home",
                    "address_line1": "123 Main Street",
                    "city": "Johannesburg",
                    "area": "Hillbrow",
                    "is_default": True
                }],
                "preferred_categories": ["utensils", "stationery"]
            }
        }


class BuyerCreate(BaseModel):
    phone_number: str
    full_name: Optional[str] = None


class BuyerUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class OTPRequest(BaseModel):
    phone_number: str


class OTPVerify(BaseModel):
    phone_number: str
    otp_code: str