from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field


class DriverStatus(str, Enum):
    OFFLINE = "offline"
    AVAILABLE = "available"
    BUSY = "busy"


class VehicleType(str, Enum):
    STANDARD = "standard"
    LUXURY = "luxury"
    DELIVERY = "delivery"


class VehicleInfo(BaseModel):
    """Vehicle details"""
    make: str
    model: str
    year: int
    color: str
    license_plate: str
    vehicle_type: VehicleType = VehicleType.STANDARD


class DriverLocation(BaseModel):
    """Current driver location"""
    latitude: float
    longitude: float
    heading: Optional[float] = None  # Direction in degrees
    speed: Optional[float] = None  # km/h
    last_updated: datetime


class Driver(BaseModel):
    """Driver model for taxi/delivery drivers"""
    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    user_id: str
    
    # Profile
    full_name: str
    phone: str
    profile_photo: Optional[str] = None
    
    # Vehicle
    vehicle: VehicleInfo
    
    # Status
    status: DriverStatus = DriverStatus.OFFLINE
    current_location: Optional[DriverLocation] = None
    
    # Ratings & Stats
    rating: float = 5.0
    total_trips: int = 0
    total_earnings: float = 0.0
    
    # Verification
    is_verified: bool = False
    documents_verified: bool = False
    
    # Banking (for payouts)
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user-123",
                "full_name": "Sipho Mbeki",
                "phone": "+27821234567",
                "vehicle": {
                    "make": "Toyota",
                    "model": "Corolla",
                    "year": 2020,
                    "color": "White",
                    "license_plate": "CA123456",
                    "vehicle_type": "standard"
                },
                "status": "available"
            }
        }


class DriverCreate(BaseModel):
    """Create new driver"""
    full_name: str
    phone: str
    vehicle: VehicleInfo


class DriverLocationUpdate(BaseModel):
    """Update driver location"""
    latitude: float
    longitude: float
    heading: Optional[float] = None
    speed: Optional[float] = None


class DriverStatusUpdate(BaseModel):
    """Update driver status"""
    status: DriverStatus
    latitude: Optional[float] = None
    longitude: Optional[float] = None
