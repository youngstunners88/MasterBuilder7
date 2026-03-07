from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field


class ProductStatus(str, Enum):
    AVAILABLE = "available"
    OUT_OF_STOCK = "out_of_stock"
    DISCONTINUED = "discontinued"
    HIDDEN = "hidden"


class ProductImage(BaseModel):
    """Product image with display order"""
    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    url: str
    alt_text: Optional[str] = None
    is_primary: bool = False
    display_order: int = 0


class ProductPricing(BaseModel):
    """Product pricing with SA-specific fields"""
    price: float  # In ZAR
    original_price: Optional[float] = None  # For discounts
    vat_inclusive: bool = True  # SA VAT at 15%
    vat_amount: Optional[float] = None  # Calculated VAT


class ProductRating(BaseModel):
    """Product rating summary"""
    average_rating: float = 0.0
    total_reviews: int = 0
    rating_distribution: dict = {  # How many reviews per star
        "5": 0, "4": 0, "3": 0, "2": 0, "1": 0
    }


class ProductTemplate(BaseModel):
    """Standard product template for vendors"""
    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    merchant_id: str
    
    # Basic info
    name: str
    description: str
    category: str
    
    # Images (up to 5)
    images: List[ProductImage] = []
    
    # Pricing
    pricing: ProductPricing
    
    # Inventory
    status: ProductStatus = ProductStatus.AVAILABLE
    quantity_available: int = 0
    low_stock_threshold: int = 5
    
    # Ratings and reviews
    rating: ProductRating = ProductRating()
    
    # Tags for search
    tags: List[str] = []
    
    # Preparation time
    preparation_time_minutes: int = 15
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# Alias for backwards compatibility
Product = ProductTemplate


class ProductCreate(BaseModel):
    """Schema for creating a new product"""
    name: str
    description: str
    category: str
    price: float
    merchant_id: str
    quantity_available: int = 0
    images: List[str] = []
    tags: List[str] = []


class Review(BaseModel):
    """Customer review for product/vendor/delivery"""
    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    
    # Review target (one of these must be set)
    product_id: Optional[str] = None
    merchant_id: Optional[str] = None
    delivery_serviceman_id: Optional[str] = None
    
    # Reviewer
    customer_id: str
    order_id: str
    
    # Content
    rating: int  # 1-5
    title: Optional[str] = None
    comment: str
    images: List[str] = []  # Image URLs
    
    # Merchant response
    merchant_response: Optional[str] = None
    merchant_responded_at: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Moderation
    is_visible: bool = True
    flagged: bool = False


class Comment(BaseModel):
    """Comment on reviews or products"""
    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    
    # Comment target
    review_id: Optional[str] = None
    product_id: Optional[str] = None
    
    # Author (any user type can comment)
    author_id: str
    author_type: str  # "customer", "merchant", "delivery_serviceman"
    author_name: str
    
    # Content
    content: str
    
    # Replies
    parent_comment_id: Optional[str] = None
    replies: List[str] = []  # IDs of reply comments
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Moderation
    is_visible: bool = True
