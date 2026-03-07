from datetime import datetime, timezone
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, EmailStr, field_validator


class UserRole(str, Enum):
    CUSTOMER = "customer"
    MERCHANT = "merchant"
    RIDER = "rider"
    ADMIN = "admin"
    # Aliases for backwards compatibility with older route code
    BUYER = "customer"
    DRIVER = "rider"


class UserLocation(BaseModel):
    """User's location data"""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    area: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    updated_at: Optional[datetime] = None


class User(BaseModel):
    """Core user model"""
    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    email: Optional[EmailStr] = None
    phone: str = Field(..., unique=True, index=True)
    full_name: Optional[str] = None
    hashed_password: Optional[str] = None
    
    # Role and status
    role: UserRole = UserRole.CUSTOMER
    is_active: bool = True
    is_verified: bool = False
    
    # Location
    location: Optional[UserLocation] = None
    
    # Profile
    profile_photo: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True


class UserCreate(BaseModel):
    """Schema for creating a new user"""
    email: Optional[EmailStr] = None
    phone: str
    full_name: Optional[str] = None
    password: str
    role: UserRole = UserRole.CUSTOMER

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v

    @field_validator("phone")
    @classmethod
    def phone_format(cls, v):
        # Normalize SA phone numbers
        digits = v.replace(" ", "").replace("-", "")
        if not (digits.startswith("+27") or digits.startswith("0")):
            raise ValueError("Phone number must be a valid South African number")
        return digits


class UserLogin(BaseModel):
    """Schema for user login"""
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: str


class UserUpdate(BaseModel):
    """Schema for updating user info"""
    full_name: Optional[str] = None
    profile_photo: Optional[str] = None
    location: Optional[UserLocation] = None