"""
Pricing Intelligence API - Revenue Analytics for iHhashi

Endpoints for:
- Pricing gap detection
- Conversion by tier analysis
- Churn by offer tracking
- Daily revenue vs forecast
- Reporter templates
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
from typing import Optional, List
from bson import ObjectId
import math

from app.database import get_collection
from app.models.pricing_intelligence import (
    PricingTier, OfferType,
    PricingGap, PricingGapCreate,
    ConversionByTier, ChurnByOffer,
    DailyRevenueForecast, PricingIntelligenceReport,
    ForecastInput
)

router = APIRouter(prefix="/pricing-intelligence", tags=["pricing-intelligence"])


# ============================================================================
# COLLECTION HELPERS
# ============================================================================

def pricing_gaps_collection():
    return get_collection("pricing_gaps")

def conversion_metrics_collection():
    return get_collection("conversion_metrics")

def churn_metrics_collection():
    return get_collection("churn_metrics")

def revenue_forecasts_collection():
    return get_collection("revenue_forecasts")

def orders_collection():
    return get_collection("orders")

def users_collection():
    return get_collection("users")


# ============================================================================
# PRICING GAPS - Detection & Tracking
# ============================================================================

@router.post("/gaps", response_model=dict)
async def report_pricing_gap(data: PricingGapCreate):
    """Report a detected pricing gap"""
    collection = pricing_gaps_collection()
    
    gap_percentage = abs(data.our_price - data.competitor_price) / data.competitor_price * 100
    
    gap = {
        "merchant_id": data.merchant_id,
        "product_id": data.product_id,
        "our_price": data.our_price,
        "competitor_price": data.competitor_price,
        "gap_percentage": round(gap_percentage, 2),
        "gap_direction": data.gap_direction,
        "estimated_lost_orders": 0,
        "estimated_lost_revenue": 0.0,
        "detected_at": datetime.utcnow(),
        "resolved_at": None,
        "resolution_action": None
    }
    
    result = await collection.insert_one(gap)
    
    return {
        "success": True,
        "gap_id": str(result.inserted_id),
        "gap_percentage": round(gap_percentage, 2)
    }


@router.get("/gaps")
async def get_pricing_gaps(
    merchant_id: Optional[str] = None,
    min_gap_percentage: float = Query(default=5.0),
    unresolved_only: bool = Query(default=True),
    limit: int = Query(default=50, ge=1, le=200)
):
    """Get detected pricing gaps"""
    collection = pricing_gaps_collection()
    
    query = {"gap_percentage": {"$gte": min_gap_percentage}}
    
    if merchant_id:
        query["merchant_id"] = merchant_id
    
    if unresolved_only:
        query["resolved_at"] = None
    
    cursor = collection.find(query).sort("gap_percentage", -1).limit(limit)
    gaps = await cursor.to_list(length=limit)
    
    for gap in gaps:
        gap["id"] = str(gap["_id"])
        del gap["_id"]
    
    return {
        "gaps": gaps,
        "count": len(gaps)
    }


@router.post("/gaps/{gap_id}/resolve")
async def resolve_pricing_gap(gap_id: str, action: str):
    """Mark a pricing gap as resolved"""
    collection = pricing_gaps_collection()
    
    result = await collection.update_one(
        {"_id": ObjectId(gap_id)},
        {
            "$set": {
                "resolved_at": datetime.utcnow(),
                "resolution_action": action
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Gap not found")
    
    return {"success": True, "message": "Gap resolved"}


# ============================================================================
# CONVERSION BY TIER - Analysis
# ============================================================================

@router.get("/conversion/by-tier")
async def get_conversion_by_tier(
    days: int = Query(default=30, ge=1, le=90)
):
    """Get conversion metrics by customer tier"""
    orders = orders_collection()
    users = users_collection()
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    # Get all customer tiers
    tiers = ["economy", "standard", "premium"]
    results = []
    
    for tier in tiers:
        # Find users in this tier
        tier_users = await users.find({"tier": tier}).to_list(length=10000)
        tier_user_ids = [str(u["_id"]) for u in tier_users]
        
        # Count orders for these users
        total_orders = await orders.count_documents({
            "customer_id": {"$in": tier_user_ids},
            "created_at": {"$gte": cutoff}
        })
        
        completed_orders = await orders.count_documents({
            "customer_id": {"$in": tier_user_ids},
            "status": "delivered",
            "created_at": {"$gte": cutoff}
        })
        
        cancelled_orders = await orders.count_documents({
            "customer_id": {"$in": tier_user_ids},
            "status": "cancelled",
            "created_at": {"$gte": cutoff}
        })
        
        # Revenue
        pipeline = [
            {"$match": {
                "customer_id": {"$in": tier_user_ids},
                "status": "delivered",
                "created_at": {"$gte": cutoff}
            }},
            {"$group": {
                "_id": None,
                "total_revenue": {"$sum": "$total_amount"},
                "avg_order_value": {"$avg": "$total_amount"}
            }}
        ]
        
        revenue_result = await orders.aggregate(pipeline).to_list(length=1)
        revenue_data = revenue_result[0] if revenue_result else {}
        
        conversion_rate = (completed_orders / total_orders * 100) if total_orders > 0 else 0
        
        results.append({
            "tier": tier,
            "period_days": days,
            "total_orders": total_orders,
            "completed_orders": completed_orders,
            "cancelled_orders": cancelled_orders,
            "conversion_rate": round(conversion_rate, 2),
            "total_revenue": round(revenue_data.get("total_revenue", 0), 2),
            "avg_order_value": round(revenue_data.get("avg_order_value", 0), 2)
        })
    
    return {
        "period_days": days,
        "tiers": results
    }


# ============================================================================
# CHURN BY OFFER - Tracking
# ============================================================================

@router.get("/churn/by-offer")
async def get_churn_by_offer(
    days: int = Query(default=90, ge=7, le=365)
):
    """Get customer churn analysis by offer type"""
    orders = orders_collection()
    users = users_collection()
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    offer_types = ["free_delivery", "percentage_off", "fixed_discount", "buy_one_get_one"]
    results = []
    
    for offer in offer_types:
        # Find users who signed up with this offer
        offer_users = await users.find({
            "acquisition_offer": offer,
            "created_at": {"$gte": cutoff}
        }).to_list(length=10000)
        
        customers_acquired = len(offer_users)
        if customers_acquired == 0:
            continue
        
        offer_user_ids = [str(u["_id"]) for u in offer_users]
        signup_dates = {str(u["_id"]): u["created_at"] for u in offer_users}
        
        # Check retention at 7, 30, 90 days
        retained_7d = 0
        retained_30d = 0
        retained_90d = 0
        
        for user_id, signup_date in signup_dates.items():
            # Check for orders after retention periods
            has_order_7d = await orders.find_one({
                "customer_id": user_id,
                "created_at": {"$gte": signup_date + timedelta(days=7)}
            })
            if has_order_7d:
                retained_7d += 1
            
            has_order_30d = await orders.find_one({
                "customer_id": user_id,
                "created_at": {"$gte": signup_date + timedelta(days=30)}
            })
            if has_order_30d:
                retained_30d += 1
            
            has_order_90d = await orders.find_one({
                "customer_id": user_id,
                "created_at": {"$gte": signup_date + timedelta(days=90)}
            })
            if has_order_90d:
                retained_90d += 1
        
        results.append({
            "offer_type": offer,
            "period_days": days,
            "customers_acquired": customers_acquired,
            "retained_7d": retained_7d,
            "retained_30d": retained_30d,
            "retained_90d": retained_90d,
            "churn_rate_7d": round((1 - retained_7d/customers_acquired) * 100, 2) if customers_acquired > 0 else 0,
            "churn_rate_30d": round((1 - retained_30d/customers_acquired) * 100, 2) if customers_acquired > 0 else 0,
            "churn_rate_90d": round((1 - retained_90d/customers_acquired) * 100, 2) if customers_acquired > 0 else 0
        })
    
    return {
        "period_days": days,
        "offers": results
    }


# ============================================================================
# DAILY REVENUE VS FORECAST
# ============================================================================

@router.post("/forecast/daily")
async def record_daily_forecast(data: ForecastInput):
    """Record daily revenue forecast"""
    collection = revenue_forecasts_collection()
    
    forecast = {
        "date": data.date,
        "forecast_amount": data.forecast_amount,
        "actual_amount": 0.0,
        "variance": 0.0,
        "variance_percentage": 0.0,
        "delivery_fees": 0.0,
        "merchant_commissions": 0.0,
        "tips": 0.0,
        "hashi_coins_redeemed": 0.0,
        "order_count": 0,
        "avg_order_value": 0.0,
        "active_merchants": 0,
        "active_drivers": 0,
        "created_at": datetime.utcnow()
    }
    
    result = await collection.insert_one(forecast)
    
    return {
        "success": True,
        "forecast_id": str(result.inserted_id)
    }


@router.get("/revenue/daily")
async def get_daily_revenue(
    days: int = Query(default=14, ge=1, le=90)
):
    """Get daily revenue actual vs forecast"""
    orders = orders_collection()
    forecasts = revenue_forecasts_collection()
    
    results = []
    
    for i in range(days):
        date = datetime.utcnow().date() - timedelta(days=i)
        day_start = datetime.combine(date, datetime.min.time())
        day_end = datetime.combine(date, datetime.max.time())
        
        # Get actual revenue
        pipeline = [
            {"$match": {
                "status": "delivered",
                "created_at": {"$gte": day_start, "$lte": day_end}
            }},
            {"$group": {
                "_id": None,
                "actual_amount": {"$sum": "$total_amount"},
                "delivery_fees": {"$sum": "$delivery_fee"},
                "tips": {"$sum": "$tip"},
                "order_count": {"$sum": 1}
            }}
        ]
        
        actual_result = await orders.aggregate(pipeline).to_list(length=1)
        actual_data = actual_result[0] if actual_result else {}
        
        # Get forecast
        forecast = await forecasts.find_one({"date": date})
        forecast_amount = forecast["forecast_amount"] if forecast else 0
        
        actual_amount = actual_data.get("actual_amount", 0)
        variance = actual_amount - forecast_amount
        variance_pct = (variance / forecast_amount * 100) if forecast_amount > 0 else 0
        
        results.append({
            "date": date.isoformat(),
            "forecast_amount": round(forecast_amount, 2),
            "actual_amount": round(actual_amount, 2),
            "variance": round(variance, 2),
            "variance_percentage": round(variance_pct, 2),
            "delivery_fees": round(actual_data.get("delivery_fees", 0), 2),
            "tips": round(actual_data.get("tips", 0), 2),
            "order_count": actual_data.get("order_count", 0)
        })
    
    return {
        "period_days": days,
        "daily": list(reversed(results))
    }


# ============================================================================
# QUERY PLAN - Pre-built Analytics Queries
# ============================================================================

QUERY_PLANS = {
    "windowed_price_deltas": {
        "description": "Detect price changes over time windows",
        "query": """
            db.pricing_gaps.aggregate([
                { $match: { resolved_at: null } },
                { $group: {
                    _id: "$merchant_id",
                    avg_gap: { $avg: "$gap_percentage" },
                    max_gap: { $max: "$gap_percentage" },
                    count: { $sum: 1 }
                }},
                { $sort: { avg_gap: -1 } }
            ])
        """,
        "alert_threshold": 15.0,
        "schedule": "daily"
    },
    
    "underperforming_tiers": {
        "description": "Find customer tiers with declining conversion",
        "query": """
            db.conversion_metrics.aggregate([
                { $match: { period_start: { $gte: ISODate("...") } } },
                { $group: {
                    _id: "$tier",
                    avg_conversion: { $avg: "$conversion_rate" },
                    trend: { $last: "$conversion_rate" }
                }},
                { $match: { trend: { $lt: "$avg_conversion" } } }
            ])
        """,
        "alert_threshold": -5.0,
        "schedule": "weekly"
    },
    
    "churn_streaks": {
        "description": "Identify offers causing churn streaks",
        "query": """
            db.churn_metrics.aggregate([
                { $match: { churn_rate_30d: { $gt: 50 } } },
                { $sort: { churn_rate_30d: -1 } }
            ])
        """,
        "alert_threshold": 50.0,
        "schedule": "weekly"
    },
    
    "revenue_variance_alerts": {
        "description": "Alert when revenue deviates from forecast",
        "query": """
            db.revenue_forecasts.aggregate([
                { $match: { date: { $gte: ISODate("...") } } },
                { $match: { 
                    $or: [
                        { variance_percentage: { $gt: 20 } },
                        { variance_percentage: { $lt: -20 } }
                    ]
                }}
            ])
        """,
        "alert_threshold": 20.0,
        "schedule": "daily"
    }
}


@router.get("/query-plans")
async def get_query_plans():
    """Get all pre-built query plans"""
    return {
        "plans": QUERY_PLANS,
        "total": len(QUERY_PLANS)
    }


@router.post("/query-plans/{plan_name}/execute")
async def execute_query_plan(plan_name: str):
    """Execute a pre-built query plan"""
    if plan_name not in QUERY_PLANS:
        raise HTTPException(status_code=404, detail="Query plan not found")
    
    plan = QUERY_PLANS[plan_name]
    
    # Execute based on plan type
    if plan_name == "windowed_price_deltas":
        collection = pricing_gaps_collection()
        results = await collection.aggregate([
            {"$match": {"resolved_at": None}},
            {"$group": {
                "_id": "$merchant_id",
                "avg_gap": {"$avg": "$gap_percentage"},
                "max_gap": {"$max": "$gap_percentage"},
                "count": {"$sum": 1}
            }},
            {"$sort": {"avg_gap": -1}}
        ]).to_list(length=50)
        
        # Check threshold
        alerts = [r for r in results if r.get("avg_gap", 0) > plan["alert_threshold"]]
        
        return {
            "plan": plan_name,
            "results": results,
            "alerts": alerts,
            "alert_count": len(alerts)
        }
    
    elif plan_name == "revenue_variance_alerts":
        collection = revenue_forecasts_collection()
        cutoff = datetime.utcnow() - timedelta(days=7)
        
        results = await collection.find({
            "date": {"$gte": cutoff},
            "$or": [
                {"variance_percentage": {"$gt": plan["alert_threshold"]}},
                {"variance_percentage": {"$lt": -plan["alert_threshold"]}}
            ]
        }).to_list(length=50)
        
        return {
            "plan": plan_name,
            "results": results,
            "alerts": results,
            "alert_count": len(results)
        }
    
    else:
        return {
            "plan": plan_name,
            "description": plan["description"],
            "alert_threshold": plan["alert_threshold"],
            "schedule": plan["schedule"],
            "note": "Execute manually in MongoDB shell"
        }


# ============================================================================
# REPORTER TEMPLATE
# ============================================================================

@router.get("/report")
async def generate_intelligence_report(
    days: int = Query(default=7, ge=1, le=30)
):
    """Generate complete pricing intelligence report"""
    period_end = datetime.utcnow()
    period_start = period_end - timedelta(days=days)
    
    # Gather all metrics
    gaps = await get_pricing_gaps(min_gap_percentage=10.0, limit=20)
    conversion = await get_conversion_by_tier(days=days)
    churn = await get_churn_by_offer(days=days)
    revenue = await get_daily_revenue(days=days)
    
    # Calculate summary metrics
    total_revenue = sum(d.get("actual_amount", 0) for d in revenue.get("daily", []))
    total_forecast = sum(d.get("forecast_amount", 0) for d in revenue.get("daily", []))
    revenue_variance = total_revenue - total_forecast
    
    # Generate alerts
    alerts = []
    
    # Pricing gap alerts
    for gap in gaps.get("gaps", [])[:5]:
        if gap.get("gap_percentage", 0) > 20:
            alerts.append({
                "type": "pricing_gap",
                "severity": "high",
                "message": f"Large pricing gap detected: {gap['gap_percentage']}% at {gap['merchant_id']}"
            })
    
    # Conversion alerts
    for tier in conversion.get("tiers", []):
        if tier.get("conversion_rate", 0) < 50:
            alerts.append({
                "type": "low_conversion",
                "severity": "medium",
                "message": f"Low conversion for {tier['tier']} tier: {tier['conversion_rate']}%"
            })
    
    # Churn alerts
    for offer in churn.get("offers", []):
        if offer.get("churn_rate_30d", 0) > 50:
            alerts.append({
                "type": "high_churn",
                "severity": "high",
                "message": f"High churn for {offer['offer_type']} offer: {offer['churn_rate_30d']}%"
            })
    
    # Generate recommendations
    recommendations = []
    
    if revenue_variance < 0:
        recommendations.append(f"Revenue below forecast by R{abs(revenue_variance):.2f}. Review pricing strategy.")
    
    if gaps.get("count", 0) > 10:
        recommendations.append(f"{gaps['count']} pricing gaps detected. Consider price adjustments.")
    
    if any(t.get("conversion_rate", 0) < 60 for t in conversion.get("tiers", [])):
        recommendations.append("Conversion rates below target. Consider targeted promotions.")
    
    return {
        "report_date": datetime.utcnow().isoformat(),
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "period_days": days,
        
        "summary": {
            "total_revenue": round(total_revenue, 2),
            "total_forecast": round(total_forecast, 2),
            "revenue_variance": round(revenue_variance, 2),
            "pricing_gaps_count": gaps.get("count", 0),
            "alerts_count": len(alerts)
        },
        
        "pricing_gaps": gaps.get("gaps", [])[:10],
        "conversion_by_tier": conversion.get("tiers", []),
        "churn_by_offer": churn.get("offers", []),
        "daily_revenue": revenue.get("daily", []),
        
        "alerts": alerts,
        "recommendations": recommendations
    }


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def health_check():
    """Check pricing intelligence system status"""
    gaps_count = await pricing_gaps_collection().count_documents({})
    forecasts_count = await revenue_forecasts_collection().count_documents({})
    
    return {
        "status": "healthy",
        "collections": {
            "pricing_gaps": gaps_count,
            "revenue_forecasts": forecasts_count
        },
        "query_plans_available": len(QUERY_PLANS)
    }
