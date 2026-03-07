"""
Route Memory API - Driver Knowledge Capture for iHhashi

Phase 1: Foundation
- Submit actual time records
- Submit driver insights
- Submit route feedback
- Query route intelligence
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
from typing import Optional, List
from bson import ObjectId
import math

from app.database import get_collection
from app.models.route_memory import (
    RoadType, InsightType, Weather, FeedbackType, DelayReason,
    TimeFactors, RouteSegment, RouteSegmentCreate,
    DriverInsight, DriverInsightCreate, DriverInsightVote,
    ActualTimeRecord, ActualTimeCreate,
    RouteFeedback, RouteFeedbackCreate,
    RouteIntelligence
)

router = APIRouter(prefix="/route-memory", tags=["route-memory"])


# ============================================================================
# COLLECTION HELPERS
# ============================================================================

def segments_collection():
    return get_collection("route_segments")

def insights_collection():
    return get_collection("driver_insights")

def time_records_collection():
    return get_collection("actual_time_records")

def feedback_collection():
    return get_collection("route_feedback")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two points in meters"""
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


def find_nearby_segments(lat: float, lng: float, radius_m: float = 500) -> List[dict]:
    """Find segments within radius of a point"""
    collection = segments_collection()
    
    # Use geospatial query if index exists, otherwise filter in code
    try:
        cursor = collection.find({
            "start_point": {
                "$near": {
                    "$geometry": {"type": "Point", "coordinates": [lng, lat]},
                    "$maxDistance": radius_m
                }
            }
        }).limit(10)
        return list(cursor)
    except Exception:
        # Fallback to simple query if geospatial index doesn't exist
        all_segments = list(collection.find().limit(100))
        nearby = []
        for seg in all_segments:
            start = seg.get("start_point", {})
            seg_lat = start.get("lat", 0)
            seg_lng = start.get("lng", 0)
            if haversine_distance(lat, lng, seg_lat, seg_lng) <= radius_m:
                nearby.append(seg)
        return nearby


def calculate_time_factors(records: List[dict]) -> dict:
    """Calculate time adjustment factors from actual time records"""
    if not records:
        return {"peak_hour_factor": 1.0, "weekend_factor": 1.0, "rainy_factor": 1.0}
    
    # Group by time periods
    peak_records = [r for r in records if 7 <= r.get("time_of_day", 12) <= 9 or 
                    16 <= r.get("time_of_day", 12) <= 18]
    off_peak = [r for r in records if r not in peak_records]
    weekend = [r for r in records if r.get("day_of_week", 0) in [5, 6]]
    weekday = [r for r in records if r not in weekend]
    rainy = [r for r in records if r.get("weather") == "rain"]
    clear = [r for r in records if r.get("weather") == "clear"]
    
    # Calculate factors
    def avg_factor(group1, group2):
        if not group1 or not group2:
            return 1.0
        avg1 = sum(r.get("actual_time_seconds", 0) for r in group1) / len(group1)
        avg2 = sum(r.get("actual_time_seconds", 0) for r in group2) / len(group2)
        if avg2 == 0:
            return 1.0
        return round(avg1 / avg2, 2)
    
    return {
        "peak_hour_factor": avg_factor(peak_records, off_peak) if peak_records else 1.0,
        "weekend_factor": avg_factor(weekend, weekday) if weekend else 1.0,
        "rainy_factor": avg_factor(rainy, clear) if rainy else 1.0
    }


# ============================================================================
# ACTUAL TIME RECORDS - Phase 1 Core
# ============================================================================

@router.post("/actual-time", response_model=dict)
async def submit_actual_time(data: ActualTimeCreate):
    """
    Submit actual time taken for a route/segment.
    
    This is the core learning data that improves ETA predictions.
    Called by driver app after each delivery.
    """
    collection = time_records_collection()
    
    # Auto-calculate time context
    now = datetime.utcnow()
    record = {
        "driver_id": data.driver_id,
        "route_id": data.route_id,
        "segment_id": data.segment_id,
        "expected_time_seconds": data.expected_time_seconds,
        "actual_time_seconds": data.actual_time_seconds,
        "time_of_day": now.hour,
        "day_of_week": now.weekday(),
        "weather": data.delivery_successful,  # Will be replaced by weather API
        "delivery_successful": data.delivery_successful,
        "delay_reason": data.delay_reason,
        "start_location": data.start_location,
        "end_location": data.end_location,
        "created_at": now
    }
    
    result = await collection.insert_one(record)
    
    return {
        "success": True,
        "record_id": str(result.inserted_id),
        "message": "Time record submitted successfully"
    }


@router.get("/actual-time/stats/{driver_id}")
async def get_driver_time_stats(driver_id: str, days: int = Query(default=30, ge=1, le=90)):
    """Get time statistics for a driver"""
    collection = time_records_collection()
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    pipeline = [
        {"$match": {"driver_id": driver_id, "created_at": {"$gte": cutoff}}},
        {"$group": {
            "_id": None,
            "total_records": {"$sum": 1},
            "avg_expected": {"$avg": "$expected_time_seconds"},
            "avg_actual": {"$avg": "$actual_time_seconds"},
            "total_deliveries": {"$sum": {"$cond": ["$delivery_successful", 1, 0]}}
        }}
    ]
    
    result = await collection.aggregate(pipeline).to_list(length=1)
    
    if not result:
        return {
            "driver_id": driver_id,
            "total_records": 0,
            "accuracy_score": None,
            "days_analyzed": days
        }
    
    stats = result[0]
    avg_expected = stats.get("avg_expected", 0)
    avg_actual = stats.get("avg_actual", 0)
    
    # Calculate accuracy (how close actual is to expected)
    if avg_expected > 0:
        accuracy = 1 - abs(avg_actual - avg_expected) / avg_expected
        accuracy = max(0, min(1, accuracy))
    else:
        accuracy = None
    
    return {
        "driver_id": driver_id,
        "total_records": stats["total_records"],
        "total_deliveries": stats["total_deliveries"],
        "avg_expected_seconds": round(avg_expected, 1),
        "avg_actual_seconds": round(avg_actual, 1),
        "accuracy_score": round(accuracy, 2) if accuracy else None,
        "days_analyzed": days
    }


# ============================================================================
# DRIVER INSIGHTS - Phase 1 Core
# ============================================================================

@router.post("/insights", response_model=dict)
async def submit_insight(data: DriverInsightCreate):
    """
    Submit a driver insight about a route.
    
    Drivers can report shortcuts, areas to avoid, road work, etc.
    """
    collection = insights_collection()
    
    insight = {
        "driver_id": data.driver_id,
        "segment_id": data.segment_id,
        "location": data.location,
        "type": data.type.value,
        "description": data.description,
        "saves_minutes": data.saves_minutes,
        "time_relevant": data.time_relevant,
        "applicable_hours": data.applicable_hours,
        "days_of_week": data.days_of_week,
        "expires_at": data.expires_at,
        "upvotes": 0,
        "downvotes": 0,
        "verified": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await collection.insert_one(insight)
    
    return {
        "success": True,
        "insight_id": str(result.inserted_id),
        "message": "Insight submitted successfully"
    }


@router.post("/insights/{insight_id}/vote", response_model=dict)
async def vote_insight(insight_id: str, vote: DriverInsightVote):
    """Upvote or downvote an insight"""
    collection = insights_collection()
    
    if vote.vote not in ["up", "down"]:
        raise HTTPException(status_code=400, detail="Vote must be 'up' or 'down'")
    
    field = "upvotes" if vote.vote == "up" else "downvotes"
    
    result = await collection.update_one(
        {"_id": ObjectId(insight_id)},
        {"$inc": {field: 1}, "$set": {"updated_at": datetime.utcnow()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Insight not found")
    
    return {
        "success": True,
        "message": f"Insight {vote.vote}voted successfully"
    }


@router.get("/insights/nearby")
async def get_nearby_insights(
    lat: float = Query(...),
    lng: float = Query(...),
    radius_m: float = Query(default=500),
    insight_type: Optional[InsightType] = None
):
    """Get insights near a location"""
    collection = insights_collection()
    
    query = {}
    
    # Filter by type if specified
    if insight_type:
        query["type"] = insight_type.value
    
    # Filter out expired insights
    query["expires_at"] = {"$or": [{"$exists": False}, {"$gt": datetime.utcnow()}]}
    
    # Get all insights (geospatial query would be better with index)
    cursor = collection.find(query).limit(100)
    all_insights = await cursor.to_list(length=100)
    
    # Filter by distance
    nearby = []
    for insight in all_insights:
        loc = insight.get("location", {})
        insight_lat = loc.get("lat", 0)
        insight_lng = loc.get("lng", 0)
        
        if haversine_distance(lat, lng, insight_lat, insight_lng) <= radius_m:
            # Convert ObjectId to string
            insight["id"] = str(insight["_id"])
            del insight["_id"]
            nearby.append(insight)
    
    return {
        "insights": nearby,
        "count": len(nearby),
        "center": {"lat": lat, "lng": lng},
        "radius_m": radius_m
    }


# ============================================================================
# ROUTE FEEDBACK - Phase 1 Core
# ============================================================================

@router.post("/feedback", response_model=dict)
async def submit_route_feedback(data: RouteFeedbackCreate):
    """
    Submit quick feedback after a delivery.
    
    Simple one-tap feedback: smooth, ok, or delayed
    with optional delay reasons and notes.
    """
    collection = feedback_collection()
    
    feedback = {
        "driver_id": data.driver_id,
        "route_id": data.route_id,
        "feedback_type": data.feedback_type.value,
        "delay_reasons": [r.value for r in data.delay_reasons],
        "notes": data.notes,
        "better_route_polyline": data.better_route_polyline,
        "pickup_location": data.pickup_location,
        "delivery_location": data.delivery_location,
        "actual_duration_seconds": data.actual_duration_seconds,
        "created_at": datetime.utcnow()
    }
    
    result = await collection.insert_one(feedback)
    
    return {
        "success": True,
        "feedback_id": str(result.inserted_id),
        "message": "Feedback submitted successfully"
    }


@router.get("/feedback/{driver_id}")
async def get_driver_feedback(
    driver_id: str,
    limit: int = Query(default=50, ge=1, le=100)
):
    """Get feedback history for a driver"""
    collection = feedback_collection()
    
    cursor = collection.find({"driver_id": driver_id}).sort("created_at", -1).limit(limit)
    feedbacks = await cursor.to_list(length=limit)
    
    # Convert ObjectIds
    for fb in feedbacks:
        fb["id"] = str(fb["_id"])
        del fb["_id"]
    
    return {
        "driver_id": driver_id,
        "feedbacks": feedbacks,
        "count": len(feedbacks)
    }


# ============================================================================
# ROUTE INTELLIGENCE - Phase 2 (Preview)
# ============================================================================

@router.get("/intelligence")
async def get_route_intelligence(
    from_lat: float = Query(...),
    from_lng: float = Query(...),
    to_lat: float = Query(...),
    to_lng: float = Query(...)
):
    """
    Get route intelligence for a planned route.
    
    Phase 1: Returns nearby insights and basic time estimate.
    Phase 2: Will include segment matching and time factors.
    """
    # Get nearby insights at start and end
    start_insights = await get_nearby_insights(from_lat, from_lng, 500)
    end_insights = await get_nearby_insights(to_lat, to_lng, 500)
    
    all_insights = start_insights["insights"] + end_insights["insights"]
    
    # Calculate distance
    distance = haversine_distance(from_lat, from_lng, to_lat, to_lng)
    
    # Basic time estimate (assume 30 km/h average in city)
    base_time_seconds = (distance / 1000) * 120  # 2 minutes per km
    
    # Get current hour for time factor
    current_hour = datetime.utcnow().hour
    is_peak = 7 <= current_hour <= 9 or 16 <= current_hour <= 18
    
    # Apply peak hour factor if applicable
    time_with_factors = base_time_seconds * (1.5 if is_peak else 1.0)
    
    # Active alerts from insights
    active_alerts = []
    for insight in all_insights:
        if insight.get("type") in ["road_work", "avoid", "unsafe"]:
            active_alerts.append({
                "type": insight["type"],
                "message": insight["description"],
                "location": insight["location"]
            })
    
    return RouteIntelligence(
        segments=[],
        insights=all_insights[:10],  # Limit to 10 most relevant
        estimated_time_seconds=int(base_time_seconds),
        estimated_time_with_factors=int(time_with_factors),
        distance_m=int(distance),
        confidence=0.5,  # Low confidence in Phase 1
        active_alerts=active_alerts
    )


# ============================================================================
# SEGMENT MANAGEMENT - Internal
# ============================================================================

@router.post("/segments", response_model=dict)
async def create_segment(data: RouteSegmentCreate):
    """Create or update a route segment (internal use)"""
    collection = segments_collection()
    
    # Check if segment already exists (same start/end points within 50m)
    existing = await collection.find_one({
        "start_point.lat": {"$gte": data.start_point["lat"] - 0.0005, "$lte": data.start_point["lat"] + 0.0005},
        "start_point.lng": {"$gte": data.start_point["lng"] - 0.0005, "$lte": data.start_point["lng"] + 0.0005},
        "end_point.lat": {"$gte": data.end_point["lat"] - 0.0005, "$lte": data.end_point["lat"] + 0.0005},
        "end_point.lng": {"$gte": data.end_point["lng"] - 0.0005, "$lte": data.end_point["lng"] + 0.0005}
    })
    
    if existing:
        # Update existing segment
        result = await collection.update_one(
            {"_id": existing["_id"]},
            {
                "$inc": {"confidence": 1},
                "$set": {
                    "avg_time_seconds": (existing["avg_time_seconds"] + data.avg_time_seconds) / 2,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return {
            "success": True,
            "segment_id": str(existing["_id"]),
            "action": "updated"
        }
    
    # Create new segment
    segment = {
        "start_point": data.start_point,
        "end_point": data.end_point,
        "polyline": data.polyline,
        "distance_m": data.distance_m,
        "avg_time_seconds": data.avg_time_seconds,
        "road_type": data.road_type.value,
        "time_factors": {"peak_hour_factor": 1.0, "weekend_factor": 1.0, "rainy_factor": 1.0},
        "common_shortcuts": [],
        "avoid_times": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "confidence": 1,
        "driver_count": 1
    }
    
    result = await collection.insert_one(segment)
    
    return {
        "success": True,
        "segment_id": str(result.inserted_id),
        "action": "created"
    }


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def health_check():
    """Check route memory system status"""
    segments_count = await segments_collection().count_documents({})
    insights_count = await insights_collection().count_documents({})
    records_count = await time_records_collection().count_documents({})
    feedback_count = await feedback_collection().count_documents({})
    
    return {
        "status": "healthy",
        "collections": {
            "route_segments": segments_count,
            "driver_insights": insights_count,
            "actual_time_records": records_count,
            "route_feedback": feedback_count
        }
    }
