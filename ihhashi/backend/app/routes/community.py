"""
Community Validation API - Phase 3 of Route Memory

Insight validation, driver reputation, and local knowledge map.
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
from typing import Optional, List
from bson import ObjectId
import math

from app.database import get_collection
from app.models.community import (
    ValidationStatus, ReputationLevel, KnowledgeCategory,
    InsightValidation, InsightValidationCreate, ValidationVote,
    DriverReputation, ReputationUpdate,
    KnowledgePoint, KnowledgeQuery,
    Badge, BADGES, LEVEL_THRESHOLDS
)

router = APIRouter(prefix="/community", tags=["community"])


# ============================================================================
# COLLECTION HELPERS
# ============================================================================

def validations_collection():
    return get_collection("insight_validations")

def reputations_collection():
    return get_collection("driver_reputations")

def knowledge_points_collection():
    return get_collection("knowledge_points")

def insights_collection():
    return get_collection("driver_insights")

def time_records_collection():
    return get_collection("actual_time_records")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def calculate_level(points: int) -> ReputationLevel:
    """Calculate reputation level from points"""
    if points >= 501:
        return ReputationLevel.LEGEND
    elif points >= 301:
        return ReputationLevel.EXPERT
    elif points >= 151:
        return ReputationLevel.NAVIGATOR
    elif points >= 51:
        return ReputationLevel.SCOUT
    return ReputationLevel.NEWCOMER


def calculate_next_level_points(points: int) -> int:
    """Calculate points needed for next level"""
    if points >= 501:
        return 0  # Max level
    elif points >= 301:
        return 501 - points
    elif points >= 151:
        return 301 - points
    elif points >= 51:
        return 151 - points
    return 51 - points


def calculate_quality_score(validation: dict) -> float:
    """Calculate composite quality score"""
    votes = validation.get("upvotes", 0) + validation.get("downvotes", 0)
    if votes == 0:
        return 0.0
    
    vote_score = validation.get("vote_ratio", 0) * 40  # Max 40 points
    
    confirmations = validation.get("confirmations", 0)
    disconfirmations = validation.get("disconfirmations", 0)
    total_conf = confirmations + disconfirmations
    
    if total_conf > 0:
        conf_score = (confirmations / total_conf) * 30  # Max 30 points
    else:
        conf_score = 0
    
    recency_score = min(validation.get("validations_last_7d", 0), 30)  # Max 30 points
    
    return min(vote_score + conf_score + recency_score, 100)


# ============================================================================
# INSIGHT VALIDATION
# ============================================================================

@router.post("/validations", response_model=dict)
async def create_validation(data: InsightValidationCreate):
    """Create validation record for an insight"""
    validations = validations_collection()
    insights = insights_collection()
    
    # Check insight exists
    insight = await insights.find_one({"_id": ObjectId(data.insight_id)})
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    
    # Check validation doesn't already exist
    existing = await validations.find_one({"insight_id": data.insight_id})
    if existing:
        return {
            "success": True,
            "validation_id": str(existing["_id"]),
            "action": "exists"
        }
    
    # Create validation
    expires_at = None
    if data.auto_expire and data.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=data.expires_in_days)
    
    validation = {
        "insight_id": data.insight_id,
        "status": ValidationStatus.PENDING.value,
        "upvotes": insight.get("upvotes", 0),
        "downvotes": insight.get("downvotes", 0),
        "vote_ratio": 0.0,
        "confirmations": 0,
        "disconfirmations": 0,
        "validations_last_7d": 0,
        "validations_last_30d": 0,
        "quality_score": 0.0,
        "validated_by": [],
        "admin_verified": False,
        "admin_verified_by": None,
        "admin_verified_at": None,
        "expires_at": expires_at,
        "auto_expire": data.auto_expire,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await validations.insert_one(validation)
    
    return {
        "success": True,
        "validation_id": str(result.inserted_id),
        "action": "created"
    }


@router.post("/validations/vote", response_model=dict)
async def vote_on_validation(vote: ValidationVote):
    """Vote on an insight validation"""
    validations = validations_collection()
    reputations = reputations_collection()
    
    # Get or create validation
    validation = await validations.find_one({"insight_id": vote.insight_id})
    if not validation:
        # Create validation first
        await create_validation(InsightValidationCreate(insight_id=vote.insight_id))
        validation = await validations.find_one({"insight_id": vote.insight_id})
    
    # Check if already voted
    if vote.driver_id in validation.get("validated_by", []):
        raise HTTPException(status_code=400, detail="Already voted on this insight")
    
    # Update vote counts
    vote_field = "upvotes" if vote.vote == "up" else "downvotes"
    conf_field = "confirmations" if vote.vote == "up" else "disconfirmations"
    
    update = {
        "$inc": {
            vote_field: 1,
            conf_field: 1 if vote.confirmed_use else 0,
            "validations_last_7d": 1,
            "validations_last_30d": 1
        },
        "$push": {"validated_by": vote.driver_id},
        "$set": {"updated_at": datetime.utcnow()}
    }
    
    await validations.update_one({"_id": validation["_id"]}, update)
    
    # Recalculate quality score
    updated = await validations.find_one({"_id": validation["_id"]})
    total_votes = updated.get("upvotes", 0) + updated.get("downvotes", 0)
    vote_ratio = updated.get("upvotes", 0) / total_votes if total_votes > 0 else 0
    quality_score = calculate_quality_score(updated)
    
    # Determine new status
    new_status = ValidationStatus.PENDING.value
    if quality_score >= 70 and updated.get("upvotes", 0) >= 5:
        new_status = ValidationStatus.CONFIRMED.value
    elif quality_score < 30 and updated.get("downvotes", 0) >= 3:
        new_status = ValidationStatus.DISPUTED.value
    
    await validations.update_one(
        {"_id": validation["_id"]},
        {"$set": {
            "vote_ratio": vote_ratio,
            "quality_score": quality_score,
            "status": new_status
        }}
    )
    
    # Update voter reputation
    await update_reputation(ReputationUpdate(
        driver_id=vote.driver_id,
        points_change=2,  # Small points for voting
        reason="voted_on_insight",
        insight_id=vote.insight_id
    ))
    
    # Update insight author reputation if confirmed
    if new_status == ValidationStatus.CONFIRMED.value:
        insights = insights_collection()
        insight = await insights.find_one({"_id": ObjectId(vote.insight_id)})
        if insight:
            await update_reputation(ReputationUpdate(
                driver_id=insight.get("driver_id"),
                points_change=10,
                reason="insight_confirmed",
                insight_id=vote.insight_id
            ))
    
    return {
        "success": True,
        "vote": vote.vote,
        "new_status": new_status,
        "quality_score": round(quality_score, 2)
    }


@router.get("/validations/{insight_id}")
async def get_validation_status(insight_id: str):
    """Get validation status for an insight"""
    validations = validations_collection()
    
    validation = await validations.find_one({"insight_id": insight_id})
    if not validation:
        return {
            "insight_id": insight_id,
            "status": "not_validated",
            "quality_score": None
        }
    
    validation["id"] = str(validation["_id"])
    del validation["_id"]
    
    return validation


# ============================================================================
# DRIVER REPUTATION
# ============================================================================

@router.get("/reputation/{driver_id}")
async def get_driver_reputation(driver_id: str):
    """Get driver reputation profile"""
    reputations = reputations_collection()
    
    reputation = await reputations.find_one({"driver_id": driver_id})
    
    if not reputation:
        # Create new reputation profile
        reputation = {
            "driver_id": driver_id,
            "total_points": 0,
            "level": ReputationLevel.NEWCOMER.value,
            "next_level_points": 50,
            "insights_submitted": 0,
            "insights_validated": 0,
            "insights_rejected": 0,
            "validations_given": 0,
            "validations_accurate": 0,
            "feedback_submitted": 0,
            "feedback_helpful": 0,
            "time_records_submitted": 0,
            "prediction_accuracy_avg": 0.0,
            "top_areas": [],
            "top_categories": [],
            "badges": [],
            "contribution_streak": 0,
            "longest_streak": 0,
            "last_contribution": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        await reputations.insert_one(reputation)
    
    reputation["id"] = str(reputation.get("_id", ""))
    if "_id" in reputation:
        del reputation["_id"]
    
    # Get available badges
    reputation["available_badges"] = [
        {"id": b.id, "name": b.name, "description": b.description, "icon": b.icon}
        for b in BADGES if b.id not in reputation.get("badges", [])
    ]
    
    return reputation


@router.post("/reputation/update")
async def update_reputation(data: ReputationUpdate):
    """Update driver reputation"""
    reputations = reputations_collection()
    insights = insights_collection()
    
    # Get or create reputation
    reputation = await reputations.find_one({"driver_id": data.driver_id})
    if not reputation:
        await get_driver_reputation(data.driver_id)
        reputation = await reputations.find_one({"driver_id": data.driver_id})
    
    # Update points
    new_points = reputation.get("total_points", 0) + data.points_change
    new_level = calculate_level(new_points)
    next_level = calculate_next_level_points(new_points)
    
    # Update streak
    last_contribution = reputation.get("last_contribution")
    streak = reputation.get("contribution_streak", 0)
    
    if last_contribution:
        last_date = last_contribution.date() if isinstance(last_contribution, datetime) else last_contribution
        today = datetime.utcnow().date()
        
        if (today - last_date).days == 1:
            streak += 1
        elif (today - last_date).days > 1:
            streak = 1
    else:
        streak = 1
    
    longest_streak = max(streak, reputation.get("longest_streak", 0))
    
    # Update counters based on reason
    updates = {
        "total_points": new_points,
        "level": new_level.value,
        "next_level_points": next_level,
        "contribution_streak": streak,
        "longest_streak": longest_streak,
        "last_contribution": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    if data.reason == "insight_submitted":
        updates["$inc"] = {"insights_submitted": 1}
    elif data.reason == "insight_confirmed":
        updates["$inc"] = {"insights_validated": 1}
    elif data.reason == "insight_rejected":
        updates["$inc"] = {"insights_rejected": 1}
    elif data.reason == "voted_on_insight":
        updates["$inc"] = {"validations_given": 1}
    elif data.reason == "feedback_submitted":
        updates["$inc"] = {"feedback_submitted": 1}
    
    # Check for badges
    new_badges = []
    current_badges = reputation.get("badges", [])
    
    # First insight badge
    if data.reason == "insight_submitted" and "first_insight" not in current_badges:
        new_badges.append("first_insight")
    
    # Streak badges
    if streak >= 7 and "streak_7" not in current_badges:
        new_badges.append("streak_7")
    if streak >= 30 and "streak_30" not in current_badges:
        new_badges.append("streak_30")
    
    if new_badges:
        updates["$push"] = {"badges": {"$each": new_badges}}
    
    # Build update query
    update_query = {"$set": updates}
    if "$inc" in updates:
        update_query["$inc"] = updates.pop("$inc")
    if "$push" in updates:
        update_query["$push"] = updates.pop("$push")
    
    await reputations.update_one(
        {"driver_id": data.driver_id},
        update_query
    )
    
    return {
        "success": True,
        "points_change": data.points_change,
        "new_total": new_points,
        "level": new_level.value,
        "new_badges": new_badges
    }


@router.get("/leaderboard")
async def get_reputation_leaderboard(
    limit: int = Query(default=20, ge=1, le=100)
):
    """Get reputation leaderboard"""
    reputations = reputations_collection()
    
    cursor = reputations.find().sort("total_points", -1).limit(limit)
    leaders = await cursor.to_list(length=limit)
    
    for leader in leaders:
        leader["id"] = str(leader["_id"])
        del leader["_id"]
    
    return {
        "leaders": leaders,
        "count": len(leaders)
    }


# ============================================================================
# LOCAL KNOWLEDGE MAP
# ============================================================================

@router.get("/knowledge/nearby")
async def get_nearby_knowledge(
    lat: float = Query(...),
    lng: float = Query(...),
    radius_m: float = Query(default=1000),
    categories: Optional[str] = None,  # Comma-separated
    min_quality: float = Query(default=0.0)
):
    """Get knowledge points near a location"""
    knowledge_points = knowledge_points_collection()
    
    # Parse categories if provided
    category_filter = None
    if categories:
        category_filter = [c.strip() for c in categories.split(",")]
    
    # Simple distance filter (would use geospatial index in production)
    all_points = await knowledge_points.find({
        "quality_score": {"$gte": min_quality}
    }).to_list(length=500)
    
    # Filter by distance
    def haversine(lat1, lng1, lat2, lng2):
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lng2 - lng1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    nearby = []
    for point in all_points:
        loc = point.get("location", {})
        point_lat = loc.get("lat", 0)
        point_lng = loc.get("lng", 0)
        
        distance = haversine(lat, lng, point_lat, point_lng)
        
        if distance <= radius_m:
            # Filter by category
            if category_filter and point.get("category") not in category_filter:
                continue
            
            point["id"] = str(point["_id"])
            del point["_id"]
            point["distance_m"] = int(distance)
            nearby.append(point)
    
    # Sort by distance
    nearby.sort(key=lambda x: x.get("distance_m", 0))
    
    return {
        "knowledge_points": nearby[:50],  # Limit to 50
        "count": len(nearby[:50]),
        "center": {"lat": lat, "lng": lng},
        "radius_m": radius_m
    }


@router.post("/knowledge/create")
async def create_knowledge_point(
    insight_id: str,
    lat: float,
    lng: float,
    category: KnowledgeCategory
):
    """Create or update knowledge point from validated insight"""
    knowledge_points = knowledge_points_collection()
    insights = insights_collection()
    validations = validations_collection()
    
    # Check insight is validated
    validation = await validations.find_one({
        "insight_id": insight_id,
        "status": ValidationStatus.CONFIRMED.value
    })
    
    if not validation:
        raise HTTPException(status_code=400, detail="Insight not validated")
    
    # Get insight
    insight = await insights.find_one({"_id": ObjectId(insight_id)})
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    
    # Find existing knowledge point nearby
    existing = await knowledge_points.find_one({
        "location.lat": {"$gte": lat - 0.002, "$lte": lat + 0.002},
        "location.lng": {"$gte": lng - 0.002, "$lte": lng + 0.002},
        "category": category.value
    })
    
    if existing:
        # Add insight to existing point
        await knowledge_points.update_one(
            {"_id": existing["_id"]},
            {
                "$push": {"insights": insight_id},
                "$inc": {"insight_count": 1},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        return {
            "success": True,
            "knowledge_point_id": str(existing["_id"]),
            "action": "updated"
        }
    
    # Create new knowledge point
    point = {
        "location": {"lat": lat, "lng": lng},
        "radius_m": 200,
        "area_name": None,
        "category": category.value,
        "insights": [insight_id],
        "insight_count": 1,
        "avg_quality_score": validation.get("quality_score", 0),
        "validation_status": ValidationStatus.CONFIRMED.value,
        "times_used": 0,
        "times_helpful": 0,
        "helpfulness_ratio": 0.0,
        "peak_usage_hours": [],
        "peak_usage_days": [],
        "top_contributors": [insight.get("driver_id")],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await knowledge_points.insert_one(point)
    
    return {
        "success": True,
        "knowledge_point_id": str(result.inserted_id),
        "action": "created"
    }


@router.post("/knowledge/{point_id}/use")
async def record_knowledge_usage(point_id: str, helpful: bool):
    """Record that a knowledge point was used"""
    knowledge_points = knowledge_points_collection()
    
    update = {
        "$inc": {
            "times_used": 1,
            "times_helpful": 1 if helpful else 0
        },
        "$set": {"updated_at": datetime.utcnow()}
    }
    
    await knowledge_points.update_one(
        {"_id": ObjectId(point_id)},
        update
    )
    
    return {"success": True}


# ============================================================================
# BATCH OPERATIONS
# ============================================================================

@router.post("/sync/insights")
async def sync_validated_insights():
    """Sync insights to knowledge map (run periodically)"""
    validations = validations_collection()
    insights = insights_collection()
    knowledge_points = knowledge_points_collection()
    
    # Find newly confirmed insights
    confirmed = await validations.find({
        "status": ValidationStatus.CONFIRMED.value
    }).to_list(length=100)
    
    synced = 0
    for validation in confirmed:
        insight = await insights.find_one({"_id": ObjectId(validation["insight_id"])})
        if insight:
            loc = insight.get("location", {})
            lat = loc.get("lat", 0)
            lng = loc.get("lng", 0)
            
            if lat and lng:
                # Create knowledge point
                await create_knowledge_point(
                    insight_id=validation["insight_id"],
                    lat=lat,
                    lng=lng,
                    category=KnowledgeCategory.SHORTCUT  # Default
                )
                synced += 1
    
    return {
        "success": True,
        "synced": synced,
        "total_confirmed": len(confirmed)
    }


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def health_check():
    """Check community system status"""
    validations_count = await validations_collection().count_documents({})
    reputations_count = await reputations_collection().count_documents({})
    knowledge_count = await knowledge_points_collection().count_documents({})
    
    confirmed_count = await validations_collection().count_documents({
        "status": ValidationStatus.CONFIRMED.value
    })
    
    return {
        "status": "healthy",
        "collections": {
            "insight_validations": validations_count,
            "driver_reputations": reputations_count,
            "knowledge_points": knowledge_count
        },
        "metrics": {
            "confirmed_insights": confirmed_count,
            "validation_rate": round(confirmed_count / validations_count * 100, 2) if validations_count > 0 else 0
        }
    }
