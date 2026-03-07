
from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field
from bson import ObjectId


# ============================================================================
# ENUMS
# ============================================================================

class RoadType(str, Enum):
    HIGHWAY = "highway"
    MAIN = "main"
    RESIDENTIAL = "residential"
    INFORMAL = "informal"
    DIRT = "dirt"


class InsightType(str, Enum):
    SHORTCUT = "shortcut"
    AVOID = "avoid"
    SLOW_ZONE = "slow_zone"
    GOOD_ALTERNATIVE = "good_alternative"
    ROAD_WORK = "road_work"
    UNSAFE = "unsafe"


class Weather(str, Enum):
    CLEAR = "clear"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"


class FeedbackType(str, Enum):
    SMOOTH = "smooth"
    OK = "ok"
    DELAYED = "delayed"


class DelayReason(str, Enum):
    ROAD_WORK = "road_work"
    HEAVY_TRAFFIC = "heavy_traffic"
    WEATHER = "weather"
    UNSAFE_AREA = "unsafe_area"
    BETTER_ROUTE_AVAILABLE = "better_route_available"
    CUSTOMER_ISSUE = "customer_issue"
    OTHER = "other"


# ============================================================================
# TIME FACTORS - Learned multipliers for time adjustments
# ============================================================================

class TimeFactors(BaseModel):
    """Time-based adjustment factors learned from actual data"""
    peak_hour_factor: float = 1.0  # e.g., 1.5x slower at 5pm
    weekend_factor: float = 1.0   # e.g., 0.8x faster on weekends
    rainy_factor: float = 1.0      # e.g., 1.3x slower in rain
    
    class Config:
        json_schema_extra = {
            "example": {
                "peak_hour_factor": 1.5,
                "weekend_factor": 0.8,
                "rainy_factor": 1.3
            }
        }


# ============================================================================
# ROUTE SEGMENT - Core unit of route knowledge
# ============================================================================

class RouteSegment(BaseModel):
    """
    A segment of a route with learned timing and conditions.
    
    Segments are created automatically from actual delivery data
    and improved by driver insights.
    """
    id: str = Field(default_factory=lambda: str(ObjectId()))
    
    # Geometry
    start_point: dict        # {lat, lng}
    end_point: dict          # {lat, lng}
    polyline: Optional[str] = None  # Encoded Google polyline
    distance_m: float
    
    # Learned data
    avg_time_seconds: float
    difficulty_rating: int = 3  # 1-5
    road_type: RoadType = RoadType.MAIN
    
    # Time factors
    time_factors: TimeFactors = Field(default_factory=TimeFactors)
    
    # Local knowledge
    common_shortcuts: List[dict] = []      # Known shortcut segments
    avoid_times: List[dict] = []            # Times to avoid this segment
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    confidence: int = 0  # Number of data points supporting this segment
    driver_count: int = 0  # Number of unique drivers who've contributed
    
    class Config:
        json_schema_extra = {
            "example": {
                "start_point": {"lat": -26.2041, "lng": 28.0473},
                "end_point": {"lat": -26.1951, "lng": 28.0553},
                "distance_m": 1500,
                "avg_time_seconds": 180,
                "difficulty_rating": 2,
                "road_type": "main",
                "time_factors": {
                    "peak_hour_factor": 1.5,
                    "weekend_factor": 0.8,
                    "rainy_factor": 1.3
                }
            }
        }


class RouteSegmentCreate(BaseModel):
    """Create a new route segment"""
    start_point: dict
    end_point: dict
    polyline: Optional[str] = None
    distance_m: float
    avg_time_seconds: float
    road_type: RoadType = RoadType.MAIN


# ============================================================================
# DRIVER INSIGHT - Qualitative feedback from drivers
# ============================================================================

class DriverInsight(BaseModel):
    """
    A driver's insight about a route or location.
    
    These are qualitative observations that help other drivers:
    - Shortcuts through parking lots
    - Areas to avoid at certain times
    - Road work alerts
    - Safety concerns
    """
    id: str = Field(default_factory=lambda: str(ObjectId()))
    driver_id: str
    
    # Location
    segment_id: Optional[str] = None  # If tied to a specific segment
    location: dict  # {lat, lng}
    
    # Insight
    type: InsightType
    description: str
    saves_minutes: Optional[int] = None  # For shortcuts
    
    # When applicable
    time_relevant: bool = False
    applicable_hours: Optional[dict] = None  # {start: 7, end: 9}
    days_of_week: Optional[List[int]] = None  # 0=Mon, 6=Sun
    
    # Community validation
    upvotes: int = 0
    downvotes: int = 0
    verified: bool = False
    verified_by: Optional[str] = None  # Admin who verified
    
    # Expiry for temporary issues
    expires_at: Optional[datetime] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "driver_id": "driver-123",
                "location": {"lat": -26.2041, "lng": 28.0473},
                "type": "shortcut",
                "description": "Cut through the shopping centre parking lot",
                "saves_minutes": 5,
                "time_relevant": True,
                "applicable_hours": {"start": 7, "end": 9}
            }
        }


class DriverInsightCreate(BaseModel):
    """Submit a new driver insight"""
    driver_id: str
    segment_id: Optional[str] = None
    location: dict
    type: InsightType
    description: str
    saves_minutes: Optional[int] = None
    time_relevant: bool = False
    applicable_hours: Optional[dict] = None
    days_of_week: Optional[List[int]] = None
    expires_at: Optional[datetime] = None


class DriverInsightVote(BaseModel):
    """Vote on an insight"""
    driver_id: str
    insight_id: str
    vote: str  # "up" or "down"


# ============================================================================
# ACTUAL TIME RECORD - Real delivery timing data
# ============================================================================

class ActualTimeRecord(BaseModel):
    """
    A record of actual time taken vs predicted.
    
    This is the core learning data that improves ETA predictions.
    """
    id: str = Field(default_factory=lambda: str(ObjectId()))
    driver_id: str
    route_id: Optional[str] = None  # If tied to a specific route
    segment_id: Optional[str] = None  # If tied to a specific segment
    
    # What happened
    expected_time_seconds: int  # What routing predicted
    actual_time_seconds: int    # What it really took
    
    # Context
    time_of_day: int            # Hour 0-23
    day_of_week: int            # 0-6, 0=Monday
    weather: Weather = Weather.CLEAR
    
    # Outcome
    delivery_successful: bool = True
    delay_reason: Optional[str] = None
    
    # Location context
    start_location: dict  # {lat, lng}
    end_location: dict    # {lat, lng}
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "driver_id": "driver-123",
                "expected_time_seconds": 900,
                "actual_time_seconds": 1120,
                "time_of_day": 17,
                "day_of_week": 4,
                "weather": "clear",
                "delivery_successful": True,
                "delay_reason": "peak_hour_traffic"
            }
        }


class ActualTimeCreate(BaseModel):
    """Submit actual time for a route/segment"""
    driver_id: str
    route_id: Optional[str] = None
    segment_id: Optional[str] = None
    expected_time_seconds: int
    actual_time_seconds: int
    start_location: dict
    end_location: dict
    delivery_successful: bool = True
    delay_reason: Optional[str] = None


# ============================================================================
# ROUTE FEEDBACK - Quick feedback after delivery
# ============================================================================

class RouteFeedback(BaseModel):
    """
    Quick feedback submitted by driver after a delivery.
    
    Simple one-tap feedback with optional details.
    """
    id: str = Field(default_factory=lambda: str(ObjectId()))
    driver_id: str
    route_id: str
    
    # Quick feedback
    feedback_type: FeedbackType
    delay_reasons: List[DelayReason] = []
    
    # Optional details
    notes: Optional[str] = None
    better_route_polyline: Optional[str] = None  # If driver found better route
    
    # Location context
    pickup_location: dict
    delivery_location: dict
    
    # Time data
    actual_duration_seconds: int
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "driver_id": "driver-123",
                "route_id": "route-456",
                "feedback_type": "delayed",
                "delay_reasons": ["heavy_traffic", "road_work"],
                "notes": "Construction on Main Street",
                "pickup_location": {"lat": -26.2041, "lng": 28.0473},
                "delivery_location": {"lat": -26.1951, "lng": 28.0553},
                "actual_duration_seconds": 1200
            }
        }


class RouteFeedbackCreate(BaseModel):
    """Submit route feedback after delivery"""
    driver_id: str
    route_id: str
    feedback_type: FeedbackType
    delay_reasons: List[DelayReason] = []
    notes: Optional[str] = None
    better_route_polyline: Optional[str] = None
    pickup_location: dict
    delivery_location: dict
    actual_duration_seconds: int


# ============================================================================
# ROUTE INTELLIGENCE - Aggregated response for routing
# ============================================================================

class RouteIntelligence(BaseModel):
    """
    Aggregated route intelligence for a requested route.
    
    Combines segments, insights, and time predictions.
    """
    segments: List[dict]
    insights: List[dict]
    estimated_time_seconds: int
    estimated_time_with_factors: int  # Adjusted for current time/weather
    distance_m: float
    confidence: float  # 0-1, how confident in the estimate
    
    # Alternative suggestions
    alternative_routes: List[dict] = []
    
    # Active alerts
    active_alerts: List[dict] = []
    
    class Config:
        json_schema_extra = {
            "example": {
                "segments": [],
                "insights": [
                    {
                        "type": "road_work",
                        "description": "Construction on Main Street until March",
                        "location": {"lat": -26.2041, "lng": 28.0473}
                    }
                ],
                "estimated_time_seconds": 900,
                "estimated_time_with_factors": 1120,
                "distance_m": 2500,
                "confidence": 0.85,
                "active_alerts": [
                    {
                        "type": "road_work",
                        "message": "Road work on Main Street - expect 5 min delay",
                        "location": {"lat": -26.2041, "lng": 28.0473}
                    }
                ]
            }
        }
