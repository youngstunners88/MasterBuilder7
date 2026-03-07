"""
Product API routes - Full implementation with MongoDB
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from typing import Optional, List
from datetime import datetime, timezone
from bson import ObjectId
from pydantic import BaseModel

from app.services.auth import get_current_user
from app.models import User
from app.database import get_collection
from app.middleware.rate_limit import limiter

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/{product_id}")
@limiter.limit("60/minute")
async def get_product(
    request: Request,
    product_id: str
):
    """Get product details"""
    products_col = get_collection("products")
    
    try:
        product = await products_col.find_one({"_id": ObjectId(product_id)})
    except Exception:
        product = await products_col.find_one({"id": product_id})
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product["id"] = str(product["_id"])
    return {"product": product}


@router.get("/search")
@limiter.limit("60/minute")
async def search_products(
    request: Request,
    q: str = Query(..., min_length=2),
    merchant_id: Optional[str] = None,
    limit: int = Query(20, le=50)
):
    """Search products by name"""
    products_col = get_collection("products")
    
    query = {
        "is_available": True,
        "$or": [
            {"name": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"category": {"$regex": q, "$options": "i"}}
        ]
    }
    
    if merchant_id:
        query["store_id"] = merchant_id
    
    cursor = products_col.find(query).limit(limit)
    products = await cursor.to_list(length=limit)
    
    for product in products:
        product["id"] = str(product["_id"])
    
    return {
        "products": products,
        "query": q,
        "total": len(products)
    }


@router.get("/categories")
@limiter.limit("60/minute")
async def get_categories(
    request: Request,
    merchant_id: Optional[str] = None
):
    """Get product categories"""
    products_col = get_collection("products")
    
    query = {"is_available": True}
    if merchant_id:
        query["store_id"] = merchant_id
    
    pipeline = [
        {"$match": query},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    
    cursor = products_col.aggregate(pipeline)
    categories = await cursor.to_list(length=50)
    
    return {
        "categories": [
            {"name": cat["_id"], "product_count": cat["count"]}
            for cat in categories
            if cat["_id"]
        ]
    }
