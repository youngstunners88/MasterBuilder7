"""
Rider API routes - Full implementation with MongoDB
SECURITY: Rate limiting on all endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import Optional
from datetime import datetime, timedelta
from bson import ObjectId

from app.services.auth import get_current_user
from app.models import (
    Driver, DriverCreate, DriverStatus, DriverStatusUpdate, 
    DriverLocationUpdate, User, UserRole
)
from app.database import get_collection
from app.middleware.rate_limit import limiter

router = APIRouter(prefix="/riders", tags=["riders"])


@router.get("/profile")
@limiter.limit("60/minute")
async def get_rider_profile(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get rider profile"""
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(status_code=403, detail="Not a driver")
    
    drivers_col = get_collection("drivers")
    
    driver = await drivers_col.find_one({"user_id": current_user.id})
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    
    driver["id"] = str(driver.get("_id", driver.get("id")))
    return {"rider": driver}


@router.post("/profile")
@limiter.limit("10/minute")
async def create_rider_profile(
    request: Request,
    driver_data: DriverCreate,
    current_user: User = Depends(get_current_user)
):
    """Create rider profile (first-time driver registration)"""
    drivers_col = get_collection("drivers")
    
    # Check if profile exists
    existing = await drivers_col.find_one({"user_id": current_user.id})
    if existing:
        raise HTTPException(status_code=400, detail="Driver profile already exists")
    
    # Create driver profile
    driver_doc = {
        "user_id": current_user.id,
        "full_name": driver_data.full_name,
        "phone": driver_data.phone,
        "vehicle": driver_data.vehicle.dict(),
        "status": DriverStatus.OFFLINE.value,
        "current_location": None,
        "rating": 5.0,
        "total_trips": 0,
        "total_earnings": 0.0,
        "is_verified": False,
        "documents_verified": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await drivers_col.insert_one(driver_doc)
    driver_doc["id"] = str(result.inserted_id)
    
    return {
        "message": "Driver profile created",
        "rider_id": driver_doc["id"],
        "next_steps": "Upload verification documents to start accepting orders"
    }


@router.put("/profile")
@limiter.limit("20/minute")
async def update_rider_profile(
    request: Request,
    full_name: Optional[str] = None,
    bank_name: Optional[str] = None,
    account_number: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Update rider profile"""
    drivers_col = get_collection("drivers")
    
    update_fields = {"updated_at": datetime.utcnow()}
    
    if full_name:
        update_fields["full_name"] = full_name
    if bank_name:
        update_fields["bank_name"] = bank_name
    if account_number:
        update_fields["account_number"] = account_number
    
    result = await drivers_col.update_one(
        {"user_id": current_user.id},
        {"$set": update_fields}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    
    return {"message": "Profile updated"}


@router.put("/status")
@limiter.limit("30/minute")
async def update_rider_status(
    request: Request,
    status_update: DriverStatusUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update rider status and location"""
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(status_code=403, detail="Not a driver")
    
    drivers_col = get_collection("drivers")
    
    update_doc = {
        "status": status_update.status.value,
        "updated_at": datetime.utcnow()
    }
    
    # Update location if provided
    if status_update.latitude and status_update.longitude:
        update_doc["current_location"] = {
            "latitude": status_update.latitude,
            "longitude": status_update.longitude,
            "last_updated": datetime.utcnow()
        }
    
    result = await drivers_col.update_one(
        {"user_id": current_user.id},
        {"$set": update_doc}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    
    return {
        "message": "Status updated",
        "status": status_update.status.value,
        "is_available": status_update.status == DriverStatus.AVAILABLE
    }


@router.put("/location")
@limiter.limit("120/minute")  # High frequency - rider updates location often
async def update_rider_location(
    request: Request,
    location: DriverLocationUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update rider location (called frequently while online)"""
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(status_code=403, detail="Not a driver")
    
    drivers_col = get_collection("drivers")
    
    location_doc = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "heading": location.heading,
        "speed": location.speed,
        "last_updated": datetime.utcnow()
    }
    
    result = await drivers_col.update_one(
        {"user_id": current_user.id},
        {
            "$set": {
                "current_location": location_doc,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    
    return {"message": "Location updated"}


@router.get("/orders/available")
@limiter.limit("30/minute")
async def get_available_orders(
    request: Request,
    lat: Optional[float] = Query(None),
    lng: Optional[float] = Query(None),
    radius_km: float = Query(5.0),
    current_user: User = Depends(get_current_user)
):
    """Fetch orders ready for pickup near rider"""
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(status_code=403, detail="Not a driver")
    
    drivers_col = get_collection("drivers")
    orders_col = get_collection("orders")
    
    # Get rider's current location
    driver = await drivers_col.find_one({"user_id": current_user.id})
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    
    # Use provided location or stored location
    if lat and lng:
        rider_lat, rider_lng = lat, lng
    elif driver.get("current_location"):
        rider_lat = driver["current_location"].get("latitude")
        rider_lng = driver["current_location"].get("longitude")
    else:
        raise HTTPException(
            status_code=400,
            detail="No location available. Please update your location first."
        )
    
    # Find orders ready for pickup
    # Status should be READY and no rider assigned yet
    query = {
        "status": "ready",
        "rider_id": {"$exists": False}
    }
    
    cursor = orders_col.find(query).sort("created_at", 1)
    orders = await cursor.to_list(length=20)
    
    # Calculate distance to each order and filter by radius
    import math
    
    def calculate_distance(lat1, lon1, lat2, lon2):
        R = 6371  # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    
    available_orders = []
    for order in orders:
        delivery_info = order.get("delivery_info", {})
        order_lat = delivery_info.get("latitude")
        order_lng = delivery_info.get("longitude")
        
        if order_lat and order_lng:
            distance = calculate_distance(rider_lat, rider_lng, order_lat, order_lng)
            if distance <= radius_km:
                order["distance_km"] = round(distance, 2)
                order["id"] = str(order["_id"])
                available_orders.append(order)
    
    # Sort by distance
    available_orders.sort(key=lambda x: x.get("distance_km", 999))
    
    return {
        "orders": available_orders[:10],  # Max 10 orders
        "total": len(available_orders),
        "rider_location": {
            "latitude": rider_lat,
            "longitude": rider_lng
        }
    }


@router.post("/orders/{order_id}/accept")
@limiter.limit("20/minute")
async def accept_order(
    request: Request,
    order_id: str,
    current_user: User = Depends(get_current_user)
):
    """Accept a delivery order"""
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(status_code=403, detail="Not a driver")
    
    drivers_col = get_collection("drivers")
    orders_col = get_collection("orders")
    
    # Verify driver is available
    driver = await drivers_col.find_one({"user_id": current_user.id})
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    
    if driver.get("status") != DriverStatus.AVAILABLE.value:
        raise HTTPException(
            status_code=400,
            detail="Driver not available. Update status to available first."
        )
    
    # Find order
    try:
        order = await orders_col.find_one({"_id": ObjectId(order_id)})
    except Exception:
        order = await orders_col.find_one({"id": order_id})
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check order is ready and not assigned
    if order["status"] != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"Order status is {order['status']}, not ready for pickup"
        )
    
    if order.get("rider_id"):
        raise HTTPException(
            status_code=409,
            detail="Order already accepted by another rider"
        )
    
    # Atomically assign rider (prevent race conditions)
    result = await orders_col.update_one(
        {
            "_id": order["_id"],
            "rider_id": {"$exists": False}
        },
        {
            "$set": {
                "rider_id": current_user.id,
                "status": "picked_up",
                "updated_at": datetime.utcnow()
            },
            "$push": {
                "status_history": {
                    "status": "picked_up",
                    "timestamp": datetime.utcnow().isoformat(),
                    "by": current_user.id,
                    "notes": f"Accepted by {driver.get('full_name', 'Driver')}"
                }
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=409,
            detail="Order was just accepted by another rider"
        )
    
    # Update driver status to busy
    await drivers_col.update_one(
        {"user_id": current_user.id},
        {
            "$set": {
                "status": DriverStatus.BUSY.value,
                "updated_at": datetime.utcnow()
            },
            "$inc": {"total_trips": 1}
        }
    )
    
    return {
        "message": "Order accepted",
        "order_id": order_id,
        "pickup_location": order.get("store_address"),
        "delivery_location": order.get("delivery_info"),
        "estimated_earnings": order.get("delivery_fee", 0) * 0.8  # 80% to driver
    }


@router.get("/earnings")
@limiter.limit("30/minute")
async def get_earnings(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Calculate rider earnings"""
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(status_code=403, detail="Not a driver")
    
    drivers_col = get_collection("drivers")
    orders_col = get_collection("orders")
    
    driver = await drivers_col.find_one({"user_id": current_user.id})
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Calculate earnings from delivered orders
    async def calculate_earnings(start_date):
        pipeline = [
            {
                "$match": {
                    "rider_id": current_user.id,
                    "status": "delivered",
                    "delivered_at": {"$gte": start_date}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": "$delivery_fee"},
                    "count": {"$sum": 1}
                }
            }
        ]
        
        cursor = orders_col.aggregate(pipeline)
        result = await cursor.to_list(length=1)
        
        if result:
            # Driver gets 80% of delivery fee
            return {
                "amount": round(result[0]["total"] * 0.8, 2),
                "deliveries": result[0]["count"]
            }
        return {"amount": 0.0, "deliveries": 0}
    
    today = await calculate_earnings(today_start)
    this_week = await calculate_earnings(week_start)
    this_month = await calculate_earnings(month_start)
    
    return {
        "today": today["amount"],
        "today_deliveries": today["deliveries"],
        "this_week": this_week["amount"],
        "this_week_deliveries": this_week["deliveries"],
        "this_month": this_month["amount"],
        "this_month_deliveries": this_month["deliveries"],
        "total": driver.get("total_earnings", 0.0),
        "total_trips": driver.get("total_trips", 0),
        "rating": driver.get("rating", 5.0),
        "payout_bank": {
            "bank_name": driver.get("bank_name"),
            "account_number": driver.get("account_number", "")[-4:] if driver.get("account_number") else None
        }
    }


@router.get("/history")
@limiter.limit("30/minute")
async def get_trip_history(
    request: Request,
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user)
):
    """Get rider's trip history"""
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(status_code=403, detail="Not a driver")
    
    orders_col = get_collection("orders")
    
    query = {
        "rider_id": current_user.id,
        "status": {"$in": ["delivered", "cancelled"]}
    }
    
    total = await orders_col.count_documents(query)
    
    cursor = orders_col.find(query).sort("delivered_at", -1).skip(offset).limit(limit)
    orders = await cursor.to_list(length=limit)
    
    for order in orders:
        order["id"] = str(order["_id"])
    
    return {
        "trips": orders,
        "total": total
    }
