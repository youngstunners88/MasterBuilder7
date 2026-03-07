"""
Merchant API routes - Full implementation with MongoDB
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from enum import Enum

from app.services.auth import get_current_user
from app.models import User, UserRole
from app.database import get_collection

router = APIRouter(prefix="/merchants", tags=["merchants"])


class MerchantCategory(str, Enum):
    GROCERY = "grocery"
    PHARMACY = "pharmacy"
    RESTAURANT = "restaurant"
    RETAIL = "retail"
    CONVENIENCE = "convenience"
    STATIONERY = "stationery"
    HARDWARE = "hardware"
    OTHER = "other"


class StoreStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


# ============ PUBLIC ENDPOINTS ============

@router.get("/")
async def get_merchants(
    category: Optional[MerchantCategory] = None,
    city: Optional[str] = None,
    lat: Optional[float] = Query(None),
    lng: Optional[float] = Query(None),
    radius_km: float = Query(5.0),
    search: Optional[str] = None,
    limit: int = Query(20, le=50),
    offset: int = Query(0, ge=0)
):
    """Search merchants with geolocation"""
    stores_col = get_collection("stores")
    
    query = {"status": StoreStatus.ACTIVE.value}
    
    if category:
        query["category"] = category.value
    
    if city:
        query["city"] = {"$regex": city, "$options": "i"}
    
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]
    
    # Geo query if location provided
    if lat and lng:
        # Use geoNear if index exists
        try:
            pipeline = [
                {
                    "$geoNear": {
                        "near": {"type": "Point", "coordinates": [lng, lat]},
                        "distanceField": "distance",
                        "maxDistance": radius_km * 1000,
                        "query": query,
                        "spherical": True
                    }
                },
                {"$skip": offset},
                {"$limit": limit}
            ]
            
            cursor = stores_col.aggregate(pipeline)
            stores = await cursor.to_list(length=limit)
            
            for store in stores:
                store["id"] = str(store["_id"])
                store["distance_km"] = round(store.get("distance", 0) / 1000, 2)
            
            return {
                "merchants": stores,
                "total": len(stores),
                "limit": limit,
                "offset": offset
            }
        except Exception:
            pass
    
    # Fallback to regular query
    total = await stores_col.count_documents(query)
    cursor = stores_col.find(query).skip(offset).limit(limit)
    stores = await cursor.to_list(length=limit)
    
    for store in stores:
        store["id"] = str(store["_id"])
    
    return {
        "merchants": stores,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/{merchant_id}")
async def get_merchant(merchant_id: str):
    """Get single merchant details"""
    stores_col = get_collection("stores")
    
    try:
        store = await stores_col.find_one({"_id": ObjectId(merchant_id)})
    except Exception:
        store = await stores_col.find_one({"id": merchant_id})
    
    if not store:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    store["id"] = str(store["_id"])
    
    # Get store stats
    orders_col = get_collection("orders")
    total_orders = await orders_col.count_documents({"store_id": merchant_id})
    
    store["stats"] = {
        "total_orders": total_orders,
        "rating": store.get("rating", 4.5)
    }
    
    return {"merchant": store}


@router.get("/{merchant_id}/menu")
async def get_merchant_menu(merchant_id: str):
    """Get merchant's product catalog"""
    products_col = get_collection("products")
    
    # Get all products for this store
    query = {
        "store_id": merchant_id,
        "is_available": True
    }
    
    cursor = products_col.find(query).sort("category", 1)
    products = await cursor.to_list(length=200)
    
    # Group by category
    categorized = {}
    for product in products:
        product["id"] = str(product["_id"])
        category = product.get("category", "Other")
        if category not in categorized:
            categorized[category] = []
        categorized[category].append(product)
    
    return {
        "menu": categorized,
        "categories": list(categorized.keys()),
        "total_products": len(products)
    }


@router.get("/{merchant_id}/products/{product_id}")
async def get_product(merchant_id: str, product_id: str):
    """Get single product details"""
    products_col = get_collection("products")
    
    try:
        product = await products_col.find_one({
            "_id": ObjectId(product_id),
            "store_id": merchant_id
        })
    except Exception:
        product = await products_col.find_one({
            "id": product_id,
            "store_id": merchant_id
        })
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product["id"] = str(product["_id"])
    return {"product": product}


# ============ MERCHANT PROTECTED ENDPOINTS ============

@router.post("/")
async def create_merchant(
    name: str,
    category: MerchantCategory,
    address_line1: str,
    city: str,
    phone: str,
    description: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    current_user: User = Depends(get_current_user)
):
    """Create merchant/store (requires merchant role)"""
    if current_user.role != UserRole.MERCHANT:
        raise HTTPException(
            status_code=403,
            detail="Only merchants can create stores"
        )
    
    stores_col = get_collection("stores")
    
    # Check if merchant already has a store
    existing = await stores_col.find_one({"owner_id": current_user.id})
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Merchant already has a store. Use update endpoint."
        )
    
    store_doc = {
        "owner_id": current_user.id,
        "name": name,
        "category": category.value,
        "description": description,
        "address": {
            "line1": address_line1,
            "city": city
        },
        "location": {
            "latitude": latitude,
            "longitude": longitude
        } if latitude and longitude else None,
        "phone": phone,
        "status": StoreStatus.PENDING.value,
        "rating": 5.0,
        "total_orders": 0,
        "is_open": True,
        "opening_hours": {
            "monday": {"open": "08:00", "close": "18:00"},
            "tuesday": {"open": "08:00", "close": "18:00"},
            "wednesday": {"open": "08:00", "close": "18:00"},
            "thursday": {"open": "08:00", "close": "18:00"},
            "friday": {"open": "08:00", "close": "18:00"},
            "saturday": {"open": "09:00", "close": "14:00"},
            "sunday": {"open": None, "close": None}
        },
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await stores_col.insert_one(store_doc)
    store_doc["id"] = str(result.inserted_id)
    
    return {
        "message": "Store created successfully",
        "store_id": store_doc["id"],
        "status": "pending",
        "note": "Your store is pending verification. You will be notified once approved."
    }


@router.get("/my/store")
async def get_my_store(current_user: User = Depends(get_current_user)):
    """Get merchant's own store"""
    if current_user.role != UserRole.MERCHANT:
        raise HTTPException(status_code=403, detail="Not a merchant")
    
    stores_col = get_collection("stores")
    
    store = await stores_col.find_one({"owner_id": current_user.id})
    if not store:
        raise HTTPException(status_code=404, detail="No store found")
    
    store["id"] = str(store["_id"])
    return {"store": store}


@router.put("/my/store")
async def update_my_store(
    name: Optional[str] = None,
    description: Optional[str] = None,
    phone: Optional[str] = None,
    is_open: Optional[bool] = None,
    opening_hours: Optional[dict] = None,
    current_user: User = Depends(get_current_user)
):
    """Update merchant's store"""
    if current_user.role != UserRole.MERCHANT:
        raise HTTPException(status_code=403, detail="Not a merchant")
    
    stores_col = get_collection("stores")
    
    update_fields = {"updated_at": datetime.utcnow()}
    
    if name:
        update_fields["name"] = name
    if description is not None:
        update_fields["description"] = description
    if phone:
        update_fields["phone"] = phone
    if is_open is not None:
        update_fields["is_open"] = is_open
    if opening_hours:
        update_fields["opening_hours"] = opening_hours
    
    result = await stores_col.update_one(
        {"owner_id": current_user.id},
        {"$set": update_fields}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Store not found")
    
    return {"message": "Store updated"}


@router.post("/my/products")
async def create_product(
    name: str,
    price: float,
    category: str,
    description: Optional[str] = None,
    stock_quantity: int = 0,
    sku: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Add product to store"""
    if current_user.role != UserRole.MERCHANT:
        raise HTTPException(status_code=403, detail="Not a merchant")
    
    stores_col = get_collection("stores")
    products_col = get_collection("products")
    
    # Get merchant's store
    store = await stores_col.find_one({"owner_id": current_user.id})
    if not store:
        raise HTTPException(status_code=404, detail="No store found")
    
    product_doc = {
        "store_id": str(store["_id"]),
        "name": name,
        "description": description,
        "price": price,
        "category": category,
        "stock_quantity": stock_quantity,
        "sku": sku,
        "is_available": stock_quantity > 0,
        "images": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await products_col.insert_one(product_doc)
    product_doc["id"] = str(result.inserted_id)
    
    return {
        "message": "Product created",
        "product_id": product_doc["id"]
    }


@router.get("/my/products")
async def get_my_products(
    category: Optional[str] = None,
    limit: int = Query(50, le=200),
    current_user: User = Depends(get_current_user)
):
    """Get merchant's products"""
    if current_user.role != UserRole.MERCHANT:
        raise HTTPException(status_code=403, detail="Not a merchant")
    
    stores_col = get_collection("stores")
    products_col = get_collection("products")
    
    # Get merchant's store
    store = await stores_col.find_one({"owner_id": current_user.id})
    if not store:
        raise HTTPException(status_code=404, detail="No store found")
    
    query = {"store_id": str(store["_id"])}
    if category:
        query["category"] = category
    
    cursor = products_col.find(query).sort("name", 1).limit(limit)
    products = await cursor.to_list(length=limit)
    
    for product in products:
        product["id"] = str(product["_id"])
    
    return {
        "products": products,
        "total": len(products)
    }


@router.put("/my/products/{product_id}")
async def update_product(
    product_id: str,
    name: Optional[str] = None,
    price: Optional[float] = None,
    stock_quantity: Optional[int] = None,
    is_available: Optional[bool] = None,
    current_user: User = Depends(get_current_user)
):
    """Update product"""
    if current_user.role != UserRole.MERCHANT:
        raise HTTPException(status_code=403, detail="Not a merchant")
    
    stores_col = get_collection("stores")
    products_col = get_collection("products")
    
    # Get merchant's store
    store = await stores_col.find_one({"owner_id": current_user.id})
    if not store:
        raise HTTPException(status_code=404, detail="No store found")
    
    update_fields = {"updated_at": datetime.utcnow()}
    
    if name:
        update_fields["name"] = name
    if price is not None:
        update_fields["price"] = price
    if stock_quantity is not None:
        update_fields["stock_quantity"] = stock_quantity
        update_fields["is_available"] = stock_quantity > 0
    if is_available is not None:
        update_fields["is_available"] = is_available
    
    result = await products_col.update_one(
        {
            "_id": ObjectId(product_id),
            "store_id": str(store["_id"])
        },
        {"$set": update_fields}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {"message": "Product updated"}


@router.delete("/my/products/{product_id}")
async def delete_product(
    product_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete product"""
    if current_user.role != UserRole.MERCHANT:
        raise HTTPException(status_code=403, detail="Not a merchant")
    
    stores_col = get_collection("stores")
    products_col = get_collection("products")
    
    store = await stores_col.find_one({"owner_id": current_user.id})
    if not store:
        raise HTTPException(status_code=404, detail="No store found")
    
    result = await products_col.delete_one({
        "_id": ObjectId(product_id),
        "store_id": str(store["_id"])
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {"message": "Product deleted"}


@router.get("/my/orders")
async def get_merchant_orders(
    status: Optional[str] = None,
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user)
):
    """Get orders for merchant's store"""
    if current_user.role != UserRole.MERCHANT:
        raise HTTPException(status_code=403, detail="Not a merchant")
    
    stores_col = get_collection("stores")
    orders_col = get_collection("orders")
    
    store = await stores_col.find_one({"owner_id": current_user.id})
    if not store:
        raise HTTPException(status_code=404, detail="No store found")
    
    query = {"store_id": str(store["_id"])}
    if status:
        query["status"] = status
    
    total = await orders_col.count_documents(query)
    
    cursor = orders_col.find(query).sort("created_at", -1).skip(offset).limit(limit)
    orders = await cursor.to_list(length=limit)
    
    for order in orders:
        order["id"] = str(order["_id"])
    
    return {
        "orders": orders,
        "total": total
    }


@router.get("/my/stats")
async def get_merchant_stats(current_user: User = Depends(get_current_user)):
    """Get merchant dashboard stats"""
    if current_user.role != UserRole.MERCHANT:
        raise HTTPException(status_code=403, detail="Not a merchant")
    
    stores_col = get_collection("stores")
    orders_col = get_collection("orders")
    
    store = await stores_col.find_one({"owner_id": current_user.id})
    if not store:
        raise HTTPException(status_code=404, detail="No store found")
    
    store_id = str(store["_id"])
    
    # Get stats
    total_orders = await orders_col.count_documents({"store_id": store_id})
    pending_orders = await orders_col.count_documents({
        "store_id": store_id,
        "status": "pending"
    })
    completed_orders = await orders_col.count_documents({
        "store_id": store_id,
        "status": "delivered"
    })
    
    # Calculate revenue
    pipeline = [
        {
            "$match": {
                "store_id": store_id,
                "status": "delivered"
            }
        },
        {
            "$group": {
                "_id": None,
                "total_revenue": {"$sum": "$subtotal"},
                "total_delivery_fees": {"$sum": "$delivery_fee"}
            }
        }
    ]
    
    cursor = orders_col.aggregate(pipeline)
    revenue_result = await cursor.to_list(length=1)
    
    total_revenue = revenue_result[0]["total_revenue"] if revenue_result else 0
    
    return {
        "store": {
            "name": store["name"],
            "status": store["status"],
            "is_open": store.get("is_open", True),
            "rating": store.get("rating", 5.0)
        },
        "orders": {
            "total": total_orders,
            "pending": pending_orders,
            "completed": completed_orders
        },
        "revenue": {
            "total": round(total_revenue, 2),
            "platform_fees": round(total_revenue * 0.15, 2),  # 15% platform fee
            "net": round(total_revenue * 0.85, 2)
        }
    }
