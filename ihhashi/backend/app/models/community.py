"""
Community Validation & Reputation Models for iHhashi Route Memory

Phase 3: Community
- Insight validation system
- Driver reputation scoring
- Local knowledge map
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field
from bson import ObjectId


class ValidationStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DISPUTED = "disputed"
    EXPIRED = "expired"
    REMOVED = "removed"


class ReputationLevel(str, Enum):
    NEWCOMER = "newcomer"       # 0-50 points
    SCOUT = "scout"             # 51-150 points
    NAVIGATOR = "navigator"     # 151-300 points
    EXPERT = "expert"           # 301-500 points
    LEGEND = "legend"           # 501+ points


class KnowledgeCategory(str, Enum):
    SHORTCUT = "shortcut"
    TRAFFIC_PATTERN = "traffic_pattern"
    SAFETY = "safety"
    PARKING = "parking"
    ACCESS_POINT = "access_point"
    DELIVERY_TIP = "delivery_tip"
    AVOID_ZONE = "avoid_zone"
    WEATHER_HAZARD = "weather_hazard"


# ============================================================================
# INSIGHT VALIDATION
# ============================================================================

class InsightValidation(BaseModel):
    """
    Validation record for a driver insight.
    
    Community validates insights through:
    - Upvotes/downvotes
    - Confirmation by using the insight
    - Admin verification
    """
    id: str = Field(default_factory=lambda: str(ObjectId()))
    insight_id: str
    
    # Validation state
    status: ValidationStatus = ValidationStatus.PENDING
    
    # Votes
    upvotes: int = 0
    downvotes: int = 0
    vote_ratio: float = 0.0  # upvotes / total votes
    
    # Confirmations (drivers who used and confirmed the insight)
    confirmations: int = 0
    disconfirmations: int = 0
    
    # Time-based validation
    validations_last_7d: int = 0
    validations_last_30d: int = 0
    
    # Quality score (composite)
    quality_score: float = 0.0  # 0-100
    
    # Validators
    validated_by: List[str] = []  # Driver IDs
    admin_verified: bool = False
    admin_verified_by: Optional[str] = None
    admin_verified_at: Optional[datetime] = None
    
    # Expiry
    expires_at: Optional[datetime] = None
    auto_expire: bool = True
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class InsightValidationCreate(BaseModel):
    insight_id: str
    auto_expire: bool = True
    expires_in_days: Optional[int] = None


class ValidationVote(BaseModel):
    """Vote on an insight validation"""
    insight_id: str
    driver_id: str
    vote: str  # "up" or "down"
    confirmed_use: bool = False  # Did driver actually use the insight?


# ============================================================================
# DRIVER REPUTATION
# ============================================================================

class DriverReputation(BaseModel):
    """
    Driver reputation based on community contributions.
    
    Earn points through:
    - Submitting validated insights
    - Confirming other insights
    - Consistent feedback
    - Accuracy of time predictions
    """
    id: str = Field(default_factory=lambda: str(ObjectId()))
    driver_id: str
    
    # Points
    total_points: int = 0
    level: ReputationLevel = ReputationLevel.NEWCOMER
    next_level_points: int = 50  # Points needed for next level
    
    # Contributions
    insights_submitted: int = 0
    insights_validated: int = 0
    insights_rejected: int = 0
    
    # Validations given
    validations_given: int = 0
    validations_accurate: int = 0  # How many matched community consensus
    
    # Feedback quality
    feedback_submitted: int = 0
    feedback_helpful: int = 0
    
    # Time prediction accuracy
    time_records_submitted: int = 0
    prediction_accuracy_avg: float = 0.0
    
    # Specializations
    top_areas: List[dict] = []  # [{area: "Sandton", insight_count: 15}]
    top_categories: List[dict] = []  # [{category: "shortcut", count: 20}]
    
    # Badges
    badges: List[str] = []
    
    # Streaks
    contribution_streak: int = 0  # Days in a row
    longest_streak: int = 0
    last_contribution: Optional[datetime] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ReputationUpdate(BaseModel):
    driver_id: str
    points_change: int
    reason: str
    insight_id: Optional[str] = None


# ============================================================================
# LOCAL KNOWLEDGE MAP
# ============================================================================

class KnowledgePoint(BaseModel):
    """
    A point on the local knowledge map.
    
    Aggregates driver insights into geographic clusters.
    """
    id: str = Field(default_factory=lambda: str(ObjectId()))
    
    # Location
    location: dict  # {lat, lng}
    radius_m: float = 200  # Cluster radius
    area_name: Optional[str] = None  # e.g., "Sandton CBD"
    
    # Knowledge
    category: KnowledgeCategory
    insights: List[str] = []  # Insight IDs
    insight_count: int = 0
    
    # Quality
    avg_quality_score: float = 0.0
    validation_status: ValidationStatus = ValidationStatus.PENDING
    
    # Usage
    times_used: int = 0
    times_helpful: int = 0
    helpfulness_ratio: float = 0.0
    
    # Time relevance
    peak_usage_hours: List[int] = []  # [7, 8, 17, 18]
    peak_usage_days: List[int] = []   # [0, 1, 2] (Mon, Tue, Wed)
    
    # Top contributors
    top_contributors: List[str] = []  # Driver IDs
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class KnowledgeMapTile(BaseModel):
    """
    A tile of the knowledge map for efficient querying.
    
    Uses a grid system for spatial indexing.
    """
    id: str = Field(default_factory=lambda: str(ObjectId()))
    
    # Grid position
    tile_id: str  # e.g., "T26.2S28.0E"
    bounds: dict  # {min_lat, max_lat, min_lng, max_lng}
    
    # Contents
    knowledge_points: List[str] = []  # KnowledgePoint IDs
    point_count: int = 0
    
    # Summary
    categories_present: List[str] = []
    total_insights: int = 0
    avg_quality: float = 0.0
    
    # Metadata
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class KnowledgeQuery(BaseModel):
    """Query for local knowledge"""
    lat: float
    lng: float
    radius_m: float = 1000
    categories: Optional[List[KnowledgeCategory]] = None
    min_quality: float = 0.0


# ============================================================================
# BADGES
# ============================================================================

class Badge(BaseModel):
    """Achievement badge for drivers"""
    id: str
    name: str
    description: str
    icon: str  # Emoji or icon name
    points_required: int = 0
    special_condition: Optional[str] = None


BADGES = [
    Badge(id="first_insight", name="First Light", description="Submitted your first insight", icon="💡", points_required=0),
    Badge(id="shortcut_king", name="Shortcut King", description="10 validated shortcuts", icon="👑", points_required=100, special_condition="10_shortcuts"),
    Badge(id="safety_scout", name="Safety Scout", description="5 validated safety tips", icon="🛡️", points_required=50, special_condition="5_safety"),
    Badge(id="traffic_whisperer", name="Traffic Whisperer", description="15 traffic pattern insights", icon="🚦", points_required=150, special_condition="15_traffic"),
    Badge(id="streak_7", name="Week Warrior", description="7 day contribution streak", icon="🔥", points_required=0, special_condition="streak_7"),
    Badge(id="streak_30", name="Monthly Master", description="30 day contribution streak", icon="⭐", points_required=0, special_condition="streak_30"),
    Badge(id="accuracy_90", name="GPS Mind", description="90%+ prediction accuracy over 100 deliveries", icon="🎯", points_required=0, special_condition="accuracy_90"),
    Badge(id="mentor", name="Mentor", description="50 helpful validations for others", icon="🎓", points_required=0, special_condition="50_validations"),
]


# ============================================================================
# LEVEL THRESHOLDS
# ============================================================================

LEVEL_THRESHOLDS = {
    ReputationLevel.NEWCOMER: {"min": 0, "max": 50, "benefits": ["Basic insights access"]},
    ReputationLevel.SCOUT: {"min": 51, "max": 150, "benefits": ["Priority on new insights", "5% delivery bonus"]},
    ReputationLevel.NAVIGATOR: {"min": 151, "max": 300, "benefits": ["8% delivery bonus", "Exclusive shortcuts", "Early access to features"]},
    ReputationLevel.EXPERT: {"min": 301, "max": 500, "benefits": ["12% delivery bonus", "Verified badge", "Admin chat access"]},
    ReputationLevel.LEGEND: {"min": 501, "max": 999999, "benefits": ["15% delivery bonus", "Legend badge", "Priority support", "Feature input"]},
}
