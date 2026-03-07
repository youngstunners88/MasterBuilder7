"""
Order API routes - Production ready with MongoDB transactions
SECURITY: Rate limiting, atomic operations, input validation
CONCURRENCY: MongoDB transactions for order creation
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
import logging

from app.services.auth import get_current_user
from app.models import (
    Order, OrderCreate, OrderStatus, OrderStatusUpdate,
    OrderItem, DeliveryInfo, User, UserRole
)
from app.database import get_collection, database
from app.utils.validation import (
    safe_object_id, validate_order_notes, validate_sa_coordinates,
    is_nosql_injection_attempt, sanitize_search_query
)
from app.middleware.rate_limit import limiter

router = APIRouter(prefix="/orders", tags=["orders"])
logger = logging.getLogger(__name__)

# Constants for validation
MAX_QUANTITY_PER_ITEM = 99
MAX_NOTES_LENGTH = 500
MAX_ORDER_ITEMS = 50


class OrderCancellationRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=200)


def validate_coordinates(lat: Optional[float], lng: Optional[float]) -> bool:
    """Validate latitude and longitude coordinates are within valid ranges"""
    if lat is None or lng is None:
        return True  # Optional fields
    try:
        return -90 <= float(lat) <= 90 and -180 <= float(lng) <= 180
    except (TypeError, ValueError):
        return False


async def calculate_delivery_fee(store_location: dict, delivery_location: dict) -> float:
    """Calculate delivery fee based on distance"""
    import math
    
    lat1 = store_location.get("latitude", 0)
    lon1 = store_location.get("longitude", 0)
    lat2 = delivery_location.get("latitude", 0)
    lon2 = delivery_location.get("longitude", 0)
    
    # Validate coordinates
    if not validate_coordinates(lat1, lon1) or not validate_coordinates(lat2, lon2):
        return 30.0  # Default fee if invalid coordinates
    
    # Validate coordinates are in South Africa
    if not validate_sa_coordinates(lat2, lon2):
        logger.warning(f"Delivery location outside SA: {lat2}, {lon2}")
        return 30.0
    
    # Haversine formula
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    
    # Calculate fee
    base_fee = 15.0
    per_km = 8.0
    fee = base_fee + (distance * per_km)
    
    return min(fee, 150.0)  # Cap at R150


@router.post("/", response_model=dict)
@limiter.limit("10/minute")  # Stricter rate limit for order creation
async def create_order(
    request: Request,
    order_data: OrderCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new order with atomic stock management using MongoDB transactions.
    
    Uses transactions to ensure stock consistency across concurrent requests.
    """
    orders_col = get_collection("orders")
    buyers_col = get_collection("buyers")
    products_col = get_collection("products")
    stores_col = get_collection("stores")
    
    # Validate item count
    if len(order_data.items) > MAX_ORDER_ITEMS:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_ORDER_ITEMS} items per order allowed"
        )
    
    # Validate store_id for NoSQL injection
    if is_nosql_injection_attempt(order_data.store_id):
        raise HTTPException(status_code=400, detail="Invalid store ID format")
    
    # Validate buyer exists
    buyer = await buyers_col.find_one({"id": current_user.id})
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer profile not found")
    
    # Get delivery address
    delivery_address = None
    for addr in buyer.get("addresses", []):
        if addr.get("id") == order_data.delivery_address_id:
            delivery_address = addr
            break
    
    if not delivery_address:
        raise HTTPException(status_code=400, detail="Delivery address not found")
    
    # Validate delivery location coordinates
    if not validate_coordinates(
        delivery_address.get("latitude"),
        delivery_address.get("longitude")
    ):
        raise HTTPException(status_code=400, detail="Invalid delivery coordinates")
    
    # Validate coordinates are in South Africa
    if not validate_sa_coordinates(
        delivery_address.get("latitude"),
        delivery_address.get("longitude")
    ):
        raise HTTPException(status_code=400, detail="Delivery address must be in South Africa")
    
    # Get store info - using safe ObjectId
    store_id = safe_object_id(order_data.store_id)
    if not store_id:
        raise HTTPException(status_code=400, detail="Invalid store ID format")
    
    store = await stores_col.find_one({"_id": store_id})
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    
    # Validate store is active
    if not store.get("is_active", True):
        raise HTTPException(status_code=400, detail="Store is currently not accepting orders")
    
    # Validate quantity limits upfront
    for item in order_data.items:
        product_id = item.get("product_id", "")
        
        # Validate product_id for NoSQL injection
        if is_nosql_injection_attempt(product_id):
            raise HTTPException(status_code=400, detail="Invalid product ID format")
        
        quantity = item.get("quantity", 0)
        if quantity > MAX_QUANTITY_PER_ITEM:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum {MAX_QUANTITY_PER_ITEM} items per product allowed"
            )
        if quantity < 1:
            raise HTTPException(
                status_code=400,
                detail="Quantity must be at least 1"
            )
    
    # Sanitize buyer notes
    buyer_notes = validate_order_notes(order_data.buyer_notes)
    
    # Use MongoDB transaction for atomic order creation
    client = database.client
    
    try:
        async with await client.start_session() as session:
            async with session.start_transaction():
                # Atomic stock check and decrement within transaction
                items = []
                subtotal = 0.0
                
                for item in order_data.items:
                    product_oid = safe_object_id(item["product_id"])
                    if not product_oid:
                        raise HTTPException(status_code=400, detail=f"Invalid product ID: {item['product_id']}")
                    
                    # Atomic stock check and decrement within transaction
                    product = await products_col.find_one_and_update(
                        {
                            "_id": product_oid,
                            "store_id": order_data.store_id,
                            "is_available": True,
                            "stock_quantity": {"$gte": item["quantity"]}
                        },
                        {"$inc": {"stock_quantity": -item["quantity"]}},
                        return_document=True,
                        session=session
                    )
                    
                    if not product:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Product not available or insufficient stock: {item['product_id']}"
                        )
                    
                    item_total = product["price"] * item["quantity"]
                    items.append({
                        "product_id": item["product_id"],
                        "product_name": product["name"],
                        "quantity": item["quantity"],
                        "unit_price": product["price"],
                        "total_price": item_total
                    })
                    subtotal += item_total
                
                # Calculate delivery fee
                delivery_fee = await calculate_delivery_fee(
                    store.get("location", {}),
                    delivery_address
                )
                
                # Create order document
                order_doc = {
                    "buyer_id": current_user.id,
                    "store_id": order_data.store_id,
                    "items": items,
                    "subtotal": round(subtotal, 2),
                    "delivery_fee": round(delivery_fee, 2),
                    "total": round(subtotal + delivery_fee, 2),
                    "currency": "ZAR",
                    "status": OrderStatus.PENDING.value,
                    "status_history": [{
                        "status": OrderStatus.PENDING.value,
                        "timestamp": datetime.utcnow().isoformat(),
                        "by": current_user.id
                    }],
                    "delivery_info": {
                        "address_label": delivery_address.get("label", ""),
                        "address_line1": delivery_address.get("address_line1", ""),
                        "address_line2": delivery_address.get("address_line2"),
                        "city": delivery_address.get("city", ""),
                        "area": delivery_address.get("area"),
                        "latitude": delivery_address.get("latitude"),
                        "longitude": delivery_address.get("longitude"),
                        "delivery_instructions": delivery_address.get("delivery_instructions"),
                        "recipient_phone": buyer.get("phone_number", "")
                    },
                    "created_at": datetime.utcnow(),
                    "payment_method": order_data.payment_method,
                    "payment_status": "pending",
                    "buyer_notes": buyer_notes,
                    "metadata": {
                        "user_agent": request.headers.get("user-agent"),
                        "ip_address": request.client.host if request.client else None
                    }
                }
                
                result = await orders_col.insert_one(order_doc, session=session)
                order_doc["id"] = str(result.inserted_id)
                
                # Transaction commits automatically
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Order creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create order. Please try again.")
    
    # TODO: Send notification to merchant (outside transaction)
    # TODO: Initiate payment if card/wallet (outside transaction)
    
    logger.info(f"Order created: {order_doc['id']} by user {current_user.id}")
    
    return {
        "message": "Order created successfully",
        "order_id": order_doc["id"],
        "total": order_doc["total"],
        "delivery_fee": delivery_fee,
        "estimated_delivery": "30-45 minutes"
    }


@router.get("/{order_id}")
@limiter.limit("60/minute")
async def get_order(
    request: Request,
    order_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get order details with access control"""
    orders_col = get_collection("orders")
    
    # Validate order_id
    if is_nosql_injection_attempt(order_id):
        raise HTTPException(status_code=400, detail="Invalid order ID format")
    
    order = None
    order_oid = safe_object_id(order_id)
    
    if order_oid:
        order = await orders_col.find_one({"_id": order_oid})
    
    if not order:
        # Try by string ID
        order = await orders_col.find_one({"id": order_id})
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check access permissions
    is_buyer = order["buyer_id"] == current_user.id
    is_rider = order.get("rider_id") == current_user.id
    is_merchant = order["store_id"] == current_user.id
    is_admin = current_user.role == UserRole.ADMIN
    
    if not (is_buyer or is_rider or is_merchant or is_admin):
        raise HTTPException(status_code=403, detail="Access denied to this order")
    
    # Convert ObjectId to string
    order["id"] = str(order.get("_id", order_id))
    if "_id" in order:
        del order["_id"]
    
    # Filter sensitive data based on role
    if not (is_buyer or is_admin):
        # Remove sensitive delivery info for non-buyers
        if "delivery_info" in order:
            order["delivery_info"].pop("delivery_instructions", None)
            order["delivery_info"].pop("recipient_phone", None)
    
    return {"order": order}


@router.get("/{order_id}/track")
@limiter.limit("30/minute")
async def track_order(
    request: Request,
    order_id: str
):
    """
    Track order status and rider location (public endpoint for order page).
    Rate limited to prevent enumeration attacks.
    """
    orders_col = get_collection("orders")
    drivers_col = get_collection("drivers")
    
    # Validate order_id
    if is_nosql_injection_attempt(order_id):
        raise HTTPException(status_code=400, detail="Invalid order ID format")
    
    order = None
    order_oid = safe_object_id(order_id)
    
    if order_oid:
        order = await orders_col.find_one({"_id": order_oid})
    
    if not order:
        order = await orders_col.find_one({"id": order_id})
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Build public response
    response = {
        "order_id": order_id,
        "status": order["status"],
        "created_at": order.get("created_at"),
        "estimated_delivery": order.get("estimated_delivery"),
        "rider": None,
        "rider_location": None
    }
    
    # If rider assigned, get their public details
    if order.get("rider_id"):
        rider = await drivers_col.find_one({"id": order["rider_id"]})
        if rider:
            response["rider"] = {
                "name": rider.get("full_name", "Driver"),
                "rating": rider.get("rating", 5.0),
                "vehicle_type": rider.get("vehicle", {}).get("type", "bike")
                # Note: Phone is intentionally NOT exposed here
            }
            
            # Only show approximate location for privacy
            if rider.get("current_location"):
                loc = rider["current_location"]
                # Round to 3 decimal places (~100m precision) for privacy
                response["rider_location"] = {
                    "latitude": round(loc.get("latitude", 0), 3),
                    "longitude": round(loc.get("longitude", 0), 3),
                    "last_updated": loc.get("last_updated")
                }
    
    return response


@router.put("/{order_id}/status")
@limiter.limit("30/minute")
async def update_order_status(
    request: Request,
    order_id: str,
    status_update: OrderStatusUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update order status (merchant/rider only)"""
    orders_col = get_collection("orders")
    
    # Validate order_id
    if is_nosql_injection_attempt(order_id):
        raise HTTPException(status_code=400, detail="Invalid order ID format")
    
    order = None
    order_oid = safe_object_id(order_id)
    
    if order_oid:
        order = await orders_col.find_one({"_id": order_oid})
    
    if not order:
        order = await orders_col.find_one({"id": order_id})
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Validate permissions
    valid_roles = [UserRole.MERCHANT, UserRole.DRIVER, UserRole.ADMIN]
    if current_user.role not in valid_roles:
        raise HTTPException(status_code=403, detail="Not authorized to update order status")
    
    # Verify user owns the order or is admin
    if current_user.role == UserRole.MERCHANT and order["store_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this order")
    
    if current_user.role == UserRole.DRIVER and order.get("rider_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Not assigned to this order")
    
    # Validate status transition
    current_status = OrderStatus(order["status"])
    new_status = status_update.status
    
    valid_transitions = {
        OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
        OrderStatus.CONFIRMED: [OrderStatus.PREPARING, OrderStatus.CANCELLED],
        OrderStatus.PREPARING: [OrderStatus.READY, OrderStatus.CANCELLED],
        OrderStatus.READY: [OrderStatus.PICKED_UP, OrderStatus.CANCELLED],
        OrderStatus.PICKED_UP: [OrderStatus.IN_TRANSIT],
        OrderStatus.IN_TRANSIT: [OrderStatus.DELIVERED, OrderStatus.CANCELLED],
        OrderStatus.DELIVERED: [],
        OrderStatus.CANCELLED: []
    }
    
    if new_status not in valid_transitions.get(current_status, []):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from {current_status} to {new_status}"
        )
    
    # Update order
    update_doc = {
        "status": new_status.value,
        "updated_at": datetime.utcnow()
    }
    
    # Add to status history
    status_entry = {
        "status": new_status.value,
        "timestamp": datetime.utcnow().isoformat(),
        "by": current_user.id,
        "notes": validate_order_notes(status_update.notes)
    }
    
    await orders_col.update_one(
        {"_id": order.get("_id") or order.get("id")},
        {
            "$set": update_doc,
            "$push": {"status_history": status_entry}
        }
    )
    
    # If delivered, update stats
    if new_status == OrderStatus.DELIVERED:
        await orders_col.update_one(
            {"_id": order.get("_id") or order.get("id")},
            {"$set": {"delivered_at": datetime.utcnow()}}
        )
        logger.info(f"Order delivered: {order_id}")
    
    return {
        "message": "Status updated",
        "order_id": order_id,
        "status": new_status.value
    }


@router.get("/")
@limiter.limit("60/minute")
async def get_orders(
    request: Request,
    status: Optional[OrderStatus] = None,
    limit: int = Query(20, le=100, ge=1),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user)
):
    """Get orders based on user role with pagination"""
    orders_col = get_collection("orders")
    
    # Build query based on role
    query = {}
    
    if current_user.role == UserRole.BUYER:
        query["buyer_id"] = current_user.id
    elif current_user.role == UserRole.DRIVER:
        query["rider_id"] = current_user.id
    elif current_user.role == UserRole.MERCHANT:
        query["store_id"] = current_user.id
    # Admin sees all
    
    if status:
        query["status"] = status.value
    
    # Get total count
    total = await orders_col.count_documents(query)
    
    # Get orders with projection for performance
    cursor = orders_col.find(
        query,
        projection={
            "_id": 1,
            "buyer_id": 1,
            "store_id": 1,
            "rider_id": 1,
            "items": {"$slice": 3},  # Limit items per order
            "total": 1,
            "status": 1,
            "created_at": 1,
            "delivery_info.city": 1,
            "delivery_info.area": 1
        }
    ).sort("created_at", -1).skip(offset).limit(limit)
    
    orders = await cursor.to_list(length=limit)
    
    # Convert ObjectIds
    for order in orders:
        order["id"] = str(order.pop("_id"))
    
    return {
        "orders": orders,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.post("/{order_id}/cancel")
@limiter.limit("5/minute")  # Very strict limit for cancellations
async def cancel_order(
    request: Request,
    order_id: str,
    cancellation: OrderCancellationRequest,
    current_user: User = Depends(get_current_user)
):
    """Cancel an order (buyer only, before rider pickup)"""
    orders_col = get_collection("orders")
    products_col = get_collection("products")
    
    # Validate order_id
    if is_nosql_injection_attempt(order_id):
        raise HTTPException(status_code=400, detail="Invalid order ID format")
    
    order = None
    order_oid = safe_object_id(order_id)
    
    if order_oid:
        order = await orders_col.find_one({"_id": order_oid})
    
    if not order:
        order = await orders_col.find_one({"id": order_id})
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Only buyer can cancel
    if order["buyer_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Only the buyer can cancel")
    
    # Check if cancellable
    if order["status"] not in [OrderStatus.PENDING.value, OrderStatus.CONFIRMED.value]:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel order at this stage"
        )
    
    # Sanitize reason
    safe_reason = validate_order_notes(cancellation.reason)
    
    # Use transaction for atomic cancellation
    client = database.client
    
    try:
        async with await client.start_session() as session:
            async with session.start_transaction():
                # Update order
                status_entry = {
                    "status": OrderStatus.CANCELLED.value,
                    "timestamp": datetime.utcnow().isoformat(),
                    "by": current_user.id,
                    "notes": f"Cancelled by buyer. Reason: {safe_reason or 'Not specified'}"
                }
                
                await orders_col.update_one(
                    {"_id": order.get("_id")},
                    {
                        "$set": {
                            "status": OrderStatus.CANCELLED.value,
                            "cancelled_at": datetime.utcnow(),
                            "cancellation_reason": safe_reason
                        },
                        "$push": {"status_history": status_entry}
                    },
                    session=session
                )
                
                # RESTORE STOCK for cancelled order
                for item in order.get("items", []):
                    product_oid = safe_object_id(item.get("product_id"))
                    if product_oid:
                        await products_col.update_one(
                            {"_id": product_oid},
                            {"$inc": {"stock_quantity": item["quantity"]}},
                            session=session
                        )
    
    except Exception as e:
        logger.error(f"Order cancellation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel order")
    
    logger.info(f"Order cancelled: {order_id} by user {current_user.id}")
    
    # TODO: Refund if paid (trigger async refund process)
    
    return {
        "message": "Order cancelled",
        "order_id": order_id,
        "refund_amount": order["total"] if order.get("payment_status") == "paid" else 0
    }
