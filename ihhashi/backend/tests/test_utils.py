"""
Test utilities and helpers for iHhashi tests.

Provides:
- Database helpers
- Mock data generators
- Authentication utilities
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from bson import ObjectId

from app.database import get_collection
from app.services.auth import get_password_hash, create_access_token
from app.models import UserRole, OrderStatus, DriverStatus, VehicleType


# ============ USER UTILITIES ============

async def create_test_user(
    email: str = "test@example.com",
    password: str = "testpassword123",
    role: UserRole = UserRole.BUYER,
    phone: str = "+27821234567",
    full_name: str = "Test User",
    is_active: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """Create a test user in the database."""
    users_col = get_collection("users")
    
    user_doc = {
        "_id": ObjectId(),
        "email": email,
        "phone": phone,
        "full_name": full_name,
        "hashed_password": get_password_hash(password),
        "role": role,
        "is_active": is_active,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        **kwargs
    }
    
    await users_col.insert_one(user_doc)
    user_doc["id"] = str(user_doc["_id"])
    return user_doc


async def create_test_driver(
    email: str = "driver@example.com",
    password: str = "testpassword123",
    phone: str = "+27821234568",
    full_name: str = "Test Driver",
    vehicle_type: VehicleType = VehicleType.MOTORCYCLE,
    is_verified: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """Create a test driver with user account."""
    user = await create_test_user(
        email=email,
        password=password,
        role=UserRole.DRIVER,
        phone=phone,
        full_name=full_name,
        **kwargs
    )
    
    drivers_col = get_collection("drivers")
    driver_doc = {
        "_id": ObjectId(),
        "user_id": user["id"],
        "status": DriverStatus.AVAILABLE,
        "vehicle": {
            "type": vehicle_type,
            "make": kwargs.get("vehicle_make", "Honda"),
            "model": kwargs.get("vehicle_model", "CG125"),
            "year": kwargs.get("vehicle_year", 2020),
            "plate_number": kwargs.get("plate_number", "CA123456")
        },
        "current_location": {
            "latitude": kwargs.get("lat", -26.2041),
            "longitude": kwargs.get("lng", 28.0473),
            "last_updated": datetime.utcnow()
        },
        "rating": kwargs.get("rating", 4.8),
        "total_deliveries": kwargs.get("total_deliveries", 0),
        "earnings": kwargs.get("earnings", 0.0),
        "is_verified": is_verified,
        "created_at": datetime.utcnow()
    }
    
    await drivers_col.insert_one(driver_doc)
    driver_doc["id"] = str(driver_doc["_id"])
    
    return {**user, "driver": driver_doc}


async def create_test_merchant(
    email: str = "merchant@example.com",
    password: str = "testpassword123",
    phone: str = "+27821234569",
    full_name: str = "Test Merchant",
    **kwargs
) -> Dict[str, Any]:
    """Create a test merchant with store."""
    user = await create_test_user(
        email=email,
        password=password,
        role=UserRole.MERCHANT,
        phone=phone,
        full_name=full_name,
        **kwargs
    )
    
    stores_col = get_collection("stores")
    store_doc = {
        "_id": ObjectId(),
        "owner_id": user["id"],
        "name": kwargs.get("store_name", "Test Store"),
        "description": kwargs.get("description", "A test store"),
        "category": kwargs.get("category", "restaurant"),
        "address": {
            "line1": kwargs.get("address_line1", "123 Test Street"),
            "city": kwargs.get("city", "Johannesburg")
        },
        "location": {
            "latitude": kwargs.get("lat", -26.2041),
            "longitude": kwargs.get("lng", 28.0473)
        },
        "phone": phone,
        "status": kwargs.get("status", "active"),
        "is_open": kwargs.get("is_open", True),
        "rating": kwargs.get("rating", 4.5),
        "total_reviews": kwargs.get("total_reviews", 0),
        "created_at": datetime.utcnow()
    }
    
    await stores_col.insert_one(store_doc)
    store_doc["id"] = str(store_doc["_id"])
    
    return {**user, "store": store_doc}


# ============ AUTH UTILITIES ============

def create_auth_headers(user_id: str, role: str, expires_hours: int = 1) -> Dict[str, str]:
    """Create authentication headers with JWT token."""
    token = create_access_token(
        data={"sub": user_id, "role": role},
        expires_delta=timedelta(hours=expires_hours)
    )
    return {"Authorization": f"Bearer {token}"}


# ============ DATABASE CLEANUP ============

async def clear_all_collections():
    """Clear all database collections (use with caution)."""
    collections = [
        "users", "drivers", "stores", "products", "orders",
        "payments", "referral_codes", "referrals", 
        "customer_reward_accounts", "coin_transactions"
    ]
    
    for collection_name in collections:
        try:
            col = get_collection(collection_name)
            await col.delete_many({})
        except Exception:
            pass  # Collection might not exist


# ============ MOCK DATA GENERATORS ============

def generate_mock_product(overrides: Dict = None) -> Dict:
    """Generate a mock product."""
    product = {
        "name": "Test Product",
        "description": "A test product description",
        "price": 85.00,
        "category": "burgers",
        "stock_quantity": 100,
        "is_available": True,
        "images": ["https://example.com/image.jpg"],
        "preparation_time_minutes": 15,
    }
    if overrides:
        product.update(overrides)
    return product


def generate_mock_order_item(overrides: Dict = None) -> Dict:
    """Generate a mock order item."""
    item = {
        "product_id": str(ObjectId()),
        "product_name": "Test Burger",
        "quantity": 2,
        "unit_price": 85.00,
        "total_price": 170.00,
    }
    if overrides:
        item.update(overrides)
    return item


def generate_mock_address(overrides: Dict = None) -> Dict:
    """Generate a mock delivery address."""
    address = {
        "label": "Home",
        "address_line1": "123 Test Street",
        "city": "Johannesburg",
        "area": "Sandton",
        "latitude": -26.1076,
        "longitude": 28.0567,
    }
    if overrides:
        address.update(overrides)
    return address
