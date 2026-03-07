"""
Quantum Extraction Models for iHhashi
Auto-populate merchant profiles from minimal input
"""
from datetime import datetime, timezone
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field


class ExtractionSource(str, Enum):
    WEBSITE_URL = "website_url"
    STORE_NAME_LOCATION = "store_name_location"
    GOOGLE_MAPS_URL = "google_maps_url"
    TRIPADVISOR_URL = "tripadvisor_url"
    FACEBOOK_PAGE = "facebook_page"
    INSTAGRAM_PAGE = "instagram_page"
    WHATSAPP_CATALOG = "whatsapp_catalog"


class ExtractionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some data extracted, but incomplete


class ExtractedHours(BaseModel):
    """Operating hours for each day"""
    monday: Optional[str] = None
    tuesday: Optional[str] = None
    wednesday: Optional[str] = None
    thursday: Optional[str] = None
    friday: Optional[str] = None
    saturday: Optional[str] = None
    sunday: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "monday": self.monday,
            "tuesday": self.tuesday,
            "wednesday": self.wednesday,
            "thursday": self.thursday,
            "friday": self.friday,
            "saturday": self.saturday,
            "sunday": self.sunday
        }


class ExtractedSocialMedia(BaseModel):
    """Social media links"""
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    twitter: Optional[str] = None
    whatsapp: Optional[str] = None
    tiktok: Optional[str] = None
    youtube: Optional[str] = None


class ExtractedProduct(BaseModel):
    """A product extracted from external source"""
    name: str
    price: Optional[float] = None
    original_price: Optional[float] = None
    currency: str = "ZAR"
    description: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    dietary_tags: List[str] = []  # vegan, vegetarian, halaal, etc.
    availability: bool = True
    
    class Config:
        extra = "allow"  # Allow additional fields


class ExtractedMenuCategory(BaseModel):
    """A menu category with items"""
    name: str
    items: List[ExtractedProduct] = []


class QuantumMerchantProfile(BaseModel):
    """
    Full merchant profile extracted from external sources
    This is the "quantum" result - populated from minimal input
    """
    # Source info
    extraction_id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    source_type: ExtractionSource
    source_url: Optional[str] = None
    source_query: Optional[str] = None  # For name+location searches
    
    # Extraction metadata
    status: ExtractionStatus = ExtractionStatus.PENDING
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    extraction_method: Optional[str] = None  # firecrawl, scrapfly, google_places, etc.
    confidence_score: float = 0.0  # 0.0 to 1.0 - how confident in the extraction
    
    # Business info
    business_name: Optional[str] = None
    trading_name: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    
    # Contact
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    
    # Address
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "South Africa"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    # Hours
    operating_hours: Optional[ExtractedHours] = None
    
    # Social
    social_media: ExtractedSocialMedia = ExtractedSocialMedia()
    
    # Products/Menu
    categories: List[ExtractedMenuCategory] = []
    total_products: int = 0
    
    # Business type detection
    business_type: Optional[str] = None  # restaurant, grocery, bakery, etc.
    cuisine_type: Optional[str] = None  # for restaurants
    
    # Delivery info
    estimated_delivery_radius_km: float = 5.0
    
    # Errors/warnings
    extraction_notes: List[str] = []
    missing_fields: List[str] = []
    
    # Raw data (for debugging)
    raw_data: Optional[dict] = None


class QuantumDiscoveryRequest(BaseModel):
    """Input for quantum discovery"""
    input: str  # URL or store name + location
    force_refresh: bool = False  # Re-extract even if cached


class QuantumOnboardRequest(BaseModel):
    """Request to onboard a merchant with extracted data"""
    extraction_id: str
    edits: Optional[dict] = None  # Merchant edits to extracted data
    merchant_user_id: str  # The user ID of the merchant


class QuantumRefreshRequest(BaseModel):
    """Request to refresh extracted data"""
    merchant_id: str
    refresh_products: bool = True
    refresh_contact: bool = False
    refresh_hours: bool = False
