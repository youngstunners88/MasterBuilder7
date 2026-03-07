from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Optional
from app.services.auth import get_current_user
from app.services.matching import MatchingService
from app.models.trip import (
    Delivery, DeliveryRequest, DeliveryStatus, DeliveryLocationUpdate, DeliveryCompleteRequest
)
from app.database import get_database
from datetime import datetime

router = APIRouter()


@router.post("/request")
async def request_delivery(
    delivery_request: DeliveryRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Request a new delivery for an order
    """
    if current_user.get("user_type") not in ["customer", "merchant"]:
        raise HTTPException(status_code=403, detail="Only customers or merchants can request deliveries")
    
    matching_service = MatchingService(db)
    
    try:
        delivery_data = {
            "order_id": delivery_request.order_id,
            "pickup_location": {
                "latitude": delivery_request.pickup_latitude,
                "longitude": delivery_request.pickup_longitude,
                "address": delivery_request.pickup_address
            },
            "delivery_location": {
                "latitude": delivery_request.delivery_latitude,
                "longitude": delivery_request.delivery_longitude,
                "address": delivery_request.delivery_address,
                "landmark": delivery_request.delivery_landmark
            },
            "vehicle_type": delivery_request.vehicle_type,
            "item_count": delivery_request.item_count,
            "special_instructions": delivery_request.special_instructions,
            "payment_method": delivery_request.payment_method
        }
        
        result = await matching_service.request_delivery(
            str(current_user["_id"]),
            delivery_data
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/active")
async def get_active_delivery(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Get current active delivery for user
    """
    user_id = str(current_user["_id"])
    active_statuses = ["pending", "rider_assigned", "at_merchant", "picked_up", "in_transit", "arrived"]
    
    # Check as customer
    delivery = await db.deliveries.find_one({
        "customer_id": user_id,
        "status": {"$in": active_statuses}
    })
    
    # Check as rider
    if not delivery:
        delivery = await db.deliveries.find_one({
            "rider_id": user_id,
            "status": {"$in": active_statuses}
        })
    
    # Check as merchant
    if not delivery:
        delivery = await db.deliveries.find_one({
            "merchant_id": user_id,
            "status": {"$in": active_statuses}
        })
    
    if not delivery:
        return {"status": "no_active_delivery"}
    
    return Delivery(**delivery).dict()


@router.post("/{delivery_id}/accept")
async def accept_delivery(
    delivery_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Rider accepts delivery request
    """
    if current_user.get("user_type") != "rider":
        raise HTTPException(status_code=403, detail="Only riders can accept deliveries")
    
    delivery = await db.deliveries.find_one({"_id": delivery_id})
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    
    if delivery["status"] != "pending":
        raise HTTPException(status_code=400, detail="Delivery already assigned")
    
    # Assign rider
    await db.deliveries.update_one(
        {"_id": delivery_id},
        {
            "$set": {
                "rider_id": str(current_user["_id"]),
                "status": "rider_assigned",
                "rider_assigned_at": datetime.utcnow()
            }
        }
    )
    
    # Notify customer and merchant
    await db.notifications.insert_many([
        {
            "user_id": delivery["customer_id"],
            "type": "rider_assigned",
            "delivery_id": delivery_id,
            "message": "A rider has been assigned to your order",
            "created_at": datetime.utcnow()
        },
        {
            "user_id": delivery["merchant_id"],
            "type": "rider_assigned",
            "delivery_id": delivery_id,
            "message": "A rider is on their way to pick up the order",
            "created_at": datetime.utcnow()
        }
    ])
    
    return {"message": "Delivery accepted", "delivery_id": delivery_id}


@router.post("/{delivery_id}/at-merchant")
async def arrived_at_merchant(
    delivery_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Rider has arrived at merchant for pickup
    """
    delivery = await db.deliveries.find_one({"_id": delivery_id})
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    
    if delivery["rider_id"] != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Not your delivery")
    
    await db.deliveries.update_one(
        {"_id": delivery_id},
        {"$set": {"status": "at_merchant"}}
    )
    
    # Notify merchant
    await db.notifications.insert_one({
        "user_id": delivery["merchant_id"],
        "type": "rider_arrived",
        "delivery_id": delivery_id,
        "message": "Rider has arrived for pickup",
        "created_at": datetime.utcnow()
    })
    
    return {"message": "Status updated", "status": "at_merchant"}


@router.post("/{delivery_id}/picked-up")
async def order_picked_up(
    delivery_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Rider has picked up the order from merchant
    """
    delivery = await db.deliveries.find_one({"_id": delivery_id})
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    
    if delivery["rider_id"] != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Not your delivery")
    
    await db.deliveries.update_one(
        {"_id": delivery_id},
        {
            "$set": {
                "status": "picked_up",
                "pickup_time": datetime.utcnow()
            }
        }
    )
    
    # Notify customer
    await db.notifications.insert_one({
        "user_id": delivery["customer_id"],
        "type": "order_picked_up",
        "delivery_id": delivery_id,
        "message": "Your order has been picked up and is on its way",
        "created_at": datetime.utcnow()
    })
    
    return {"message": "Order picked up", "status": "picked_up"}


@router.post("/{delivery_id}/in-transit")
async def start_delivery(
    delivery_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Rider is in transit to delivery location
    """
    delivery = await db.deliveries.find_one({"_id": delivery_id})
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    
    if delivery["rider_id"] != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Not your delivery")
    
    await db.deliveries.update_one(
        {"_id": delivery_id},
        {"$set": {"status": "in_transit"}}
    )
    
    return {"message": "Delivery in transit", "status": "in_transit"}


@router.post("/{delivery_id}/arrived")
async def arrived_at_delivery(
    delivery_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Rider has arrived at delivery location
    """
    delivery = await db.deliveries.find_one({"_id": delivery_id})
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    
    if delivery["rider_id"] != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Not your delivery")
    
    await db.deliveries.update_one(
        {"_id": delivery_id},
        {"$set": {"status": "arrived"}}
    )
    
    # Notify customer
    await db.notifications.insert_one({
        "user_id": delivery["customer_id"],
        "type": "rider_arrived",
        "delivery_id": delivery_id,
        "message": "Your rider has arrived at your location",
        "created_at": datetime.utcnow()
    })
    
    return {"message": "Arrived at delivery location", "status": "arrived"}


@router.post("/{delivery_id}/complete")
async def complete_delivery(
    delivery_id: str,
    complete_request: DeliveryCompleteRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Mark delivery as complete (hand items to customer)
    """
    delivery = await db.deliveries.find_one({"_id": delivery_id})
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    
    if delivery["rider_id"] != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Not your delivery")
    
    update_data = {
        "status": "delivered",
        "delivery_time": datetime.utcnow(),
        "payment_status": "completed"
    }
    
    if complete_request.recipient_name:
        update_data["delivery_proof.recipient_name"] = complete_request.recipient_name
    if complete_request.notes:
        update_data["delivery_proof.notes"] = complete_request.notes
    
    await db.deliveries.update_one(
        {"_id": delivery_id},
        {"$set": update_data}
    )
    
    # Notify customer and merchant
    await db.notifications.insert_many([
        {
            "user_id": delivery["customer_id"],
            "type": "delivery_completed",
            "delivery_id": delivery_id,
            "message": "Your order has been delivered",
            "created_at": datetime.utcnow()
        },
        {
            "user_id": delivery["merchant_id"],
            "type": "delivery_completed",
            "delivery_id": delivery_id,
            "message": "Order has been delivered to customer",
            "created_at": datetime.utcnow()
        }
    ])
    
    return {"message": "Delivery completed", "status": "delivered"}


@router.post("/{delivery_id}/cancel")
async def cancel_delivery(
    delivery_id: str,
    reason: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Cancel a delivery
    """
    delivery = await db.deliveries.find_one({"_id": delivery_id})
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    
    user_id = str(current_user["_id"])
    is_customer = delivery["customer_id"] == user_id
    is_rider = delivery.get("rider_id") == user_id
    is_merchant = delivery["merchant_id"] == user_id
    
    if not (is_customer or is_rider or is_merchant):
        raise HTTPException(status_code=403, detail="Not your delivery")
    
    if delivery["status"] == "delivered":
        raise HTTPException(status_code=400, detail="Cannot cancel completed delivery")
    
    await db.deliveries.update_one(
        {"_id": delivery_id},
        {
            "$set": {
                "status": "cancelled",
                "cancel_reason": reason or "cancelled_by_user",
                "cancellation_time": datetime.utcnow()
            }
        }
    )
    
    return {"message": "Delivery cancelled", "delivery_id": delivery_id}


@router.post("/{delivery_id}/location")
async def update_location(
    delivery_id: str,
    location: DeliveryLocationUpdate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Update rider location during delivery (for tracking)
    """
    delivery = await db.deliveries.find_one({"_id": delivery_id})
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    
    if delivery["rider_id"] != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Not your delivery")
    
    # Store location update for real-time tracking
    await db.delivery_locations.insert_one({
        "delivery_id": delivery_id,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "timestamp": datetime.utcnow()
    })
    
    return {"message": "Location updated"}


@router.get("/{delivery_id}")
async def get_delivery(
    delivery_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Get delivery details
    """
    delivery = await db.deliveries.find_one({"_id": delivery_id})
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    
    return Delivery(**delivery).dict()


@router.post("/{delivery_id}/rate")
async def rate_delivery(
    delivery_id: str,
    rating: int,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Rate the delivery (1-5 stars)
    """
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    delivery = await db.deliveries.find_one({"_id": delivery_id})
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    
    user_id = str(current_user["_id"])
    
    if delivery["customer_id"] == user_id:
        await db.deliveries.update_one(
            {"_id": delivery_id},
            {"$set": {"customer_rating": rating}}
        )
    elif delivery.get("rider_id") == user_id:
        await db.deliveries.update_one(
            {"_id": delivery_id},
            {"$set": {"rider_rating": rating}}
        )
    else:
        raise HTTPException(status_code=403, detail="Not authorized to rate this delivery")
    
    return {"message": "Rating submitted", "rating": rating}
