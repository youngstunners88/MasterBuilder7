"""
Pytest configuration and fixtures for iHhashi test suite.

Sets up:
- In-memory MongoDB for testing (mongomock)
- Test client with FastAPI app
- Fixtures for users, orders, payments, and riders
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from bson import ObjectId

# Set test environment before importing app
os.environ["ENVIRONMENT"] = "test"
os.environ["MONGODB_URL"] = "mongodb://localhost:27017"
os.environ["DB_NAME"] = "ihhashi_test"
os.environ["SECRET_KEY"] = "test_secret_key_for_testing_only"
os.environ["PAYSTACK_SECRET_KEY"] = "sk_test_dummy_key"

# =============================================================================
# TEST CONSTANTS - Centralized test credentials (NOT for production use)
# =============================================================================
TEST_PASSWORD = "testpassword123"  # Used only in test suite - can be rotated

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from motor.motor_asyncio import AsyncIOMotorClient

from app.main import app
from app.database import get_collection
from app.models import (
    User, UserCreate, UserRole,
    Order, OrderStatus, OrderItem, DeliveryInfo,
    Driver, DriverStatus, VehicleInfo, VehicleType
)
from app.services.auth import create_access_token, get_password_hash


# ============ EVENT LOOP ============

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============ DATABASE FIXTURES ============

@pytest_asyncio.fixture(scope="function")
async def test_db():
    """Set up test database with mongomock or test MongoDB."""
    from app import database as db_module
    
    # Use test database
    test_mongodb_url = "mongodb://localhost:27017"
    test_db_name = "ihhashi_test"
    
    client = AsyncIOMotorClient(test_mongodb_url)
    db = client[test_db_name]
    
    # Override global database
    db_module.client = client
    db_module.database = db
    
    yield db
    
    # Cleanup: drop all collections
    collections = await db.list_collection_names()
    for collection in collections:
        await db.drop_collection(collection)
    
    client.close()


@pytest_asyncio.fixture
async def clean_db(test_db):
    """Ensure clean database for each test."""
    collections = await test_db.list_collection_names()
    for collection in collections:
        await test_db.drop_collection(collection)
    return test_db


# ============ CLIENT FIXTURES ============

@pytest.fixture
def client() -> Generator:
    """Synchronous test client."""
    with TestClient(app) as c:
        yield c


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator:
    """Asynchronous test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


# ============ USER FIXTURES ============

@pytest_asyncio.fixture
async def test_user(clean_db) -> dict:
    """Create a test buyer user."""
    users_col = get_collection("users")
    user_doc = {
        "_id": ObjectId(),
        "email": "buyer@test.com",
        "phone": "+27821234567",
        "full_name": "Test Buyer",
        "hashed_password": get_password_hash(TEST_PASSWORD),
        "role": UserRole.BUYER,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    await users_col.insert_one(user_doc)
    user_doc["id"] = str(user_doc["_id"])
    return user_doc


@pytest_asyncio.fixture
async def test_merchant(clean_db) -> dict:
    """Create a test merchant user."""
    users_col = get_collection("users")
    user_doc = {
        "_id": ObjectId(),
        "email": "merchant@test.com",
        "phone": "+27821234568",
        "full_name": "Test Merchant",
        "hashed_password": get_password_hash(TEST_PASSWORD),
        "role": UserRole.MERCHANT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    await users_col.insert_one(user_doc)
    user_doc["id"] = str(user_doc["_id"])
    return user_doc


@pytest_asyncio.fixture
async def test_driver(clean_db) -> dict:
    """Create a test driver/rider user."""
    users_col = get_collection("users")
    drivers_col = get_collection("drivers")
    
    user_doc = {
        "_id": ObjectId(),
        "email": "driver@test.com",
        "phone": "+27821234569",
        "full_name": "Test Driver",
        "hashed_password": get_password_hash(TEST_PASSWORD),
        "role": UserRole.DRIVER,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    await users_col.insert_one(user_doc)
    
    driver_doc = {
        "_id": ObjectId(),
        "user_id": str(user_doc["_id"]),
        "status": DriverStatus.AVAILABLE,
        "vehicle": {
            "type": VehicleType.MOTORCYCLE,
            "make": "Honda",
            "model": "CG125",
            "year": 2020,
            "plate_number": "CA123456"
        },
        "current_location": {
            "latitude": -26.2041,
            "longitude": 28.0473,
            "last_updated": datetime.utcnow()
        },
        "rating": 4.8,
        "total_deliveries": 150,
        "earnings": 15000.00,
        "is_verified": True,
        "created_at": datetime.utcnow()
    }
    await drivers_col.insert_one(driver_doc)
    
    user_doc["id"] = str(user_doc["_id"])
    driver_doc["id"] = str(driver_doc["_id"])
    return {**user_doc, "driver": driver_doc}


@pytest_asyncio.fixture
async def test_admin(clean_db) -> dict:
    """Create a test admin user."""
    users_col = get_collection("users")
    user_doc = {
        "_id": ObjectId(),
        "email": "admin@test.com",
        "phone": "+27821234570",
        "full_name": "Test Admin",
        "hashed_password": get_password_hash(TEST_PASSWORD),
        "role": UserRole.ADMIN,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    await users_col.insert_one(user_doc)
    user_doc["id"] = str(user_doc["_id"])
    return user_doc


@pytest_asyncio.fixture
async def test_customer(clean_db) -> dict:
    """Create a test customer user for rewards testing."""
    users_col = get_collection("users")
    user_doc = {
        "_id": ObjectId(),
        "email": "customer@test.com",
        "phone": "+27821234571",
        "full_name": "Test Customer",
        "hashed_password": get_password_hash(TEST_PASSWORD),
        "role": UserRole.BUYER,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    await users_col.insert_one(user_doc)
    user_doc["id"] = str(user_doc["_id"])
    return user_doc


# ============ AUTH FIXTURES ============

@pytest.fixture
def auth_headers(test_user) -> dict:
    """Generate auth headers for test user."""
    token = create_access_token(
        data={"sub": test_user["id"], "role": test_user["role"]},
        expires_delta=timedelta(hours=1)
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def buyer_auth_headers(test_user) -> dict:
    """Generate auth headers for buyer."""
    token = create_access_token(
        data={"sub": test_user["id"], "role": test_user["role"]},
        expires_delta=timedelta(hours=1)
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def merchant_auth_headers(test_merchant) -> dict:
    """Generate auth headers for merchant."""
    token = create_access_token(
        data={"sub": test_merchant["id"], "role": test_merchant["role"]},
        expires_delta=timedelta(hours=1)
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def driver_auth_headers(test_driver) -> dict:
    """Generate auth headers for driver."""
    token = create_access_token(
        data={"sub": test_driver["id"], "role": test_driver["role"]},
        expires_delta=timedelta(hours=1)
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_auth_headers(test_admin) -> dict:
    """Generate auth headers for admin."""
    token = create_access_token(
        data={"sub": test_admin["id"], "role": test_admin["role"]},
        expires_delta=timedelta(hours=1)
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def customer_auth_headers(test_customer) -> dict:
    """Generate auth headers for customer."""
    token = create_access_token(
        data={"sub": test_customer["id"], "role": test_customer["role"]},
        expires_delta=timedelta(hours=1)
    )
    return {"Authorization": f"Bearer {token}"}


# ============ STORE FIXTURES ============

@pytest_asyncio.fixture
async def test_store(clean_db, test_merchant) -> dict:
    """Create a test store/merchant."""
    stores_col = get_collection("stores")
    store_doc = {
        "_id": ObjectId(),
        "merchant_id": test_merchant["id"],
        "name": "Test Restaurant",
        "description": "A test restaurant for testing",
        "category": "restaurant",
        "location": {
            "latitude": -26.2041,
            "longitude": 28.0473,
            "address": "123 Test Street, Johannesburg"
        },
        "opening_hours": {
            "monday": {"open": "09:00", "close": "21:00"},
            "tuesday": {"open": "09:00", "close": "21:00"},
            "wednesday": {"open": "09:00", "close": "21:00"},
            "thursday": {"open": "09:00", "close": "21:00"},
            "friday": {"open": "09:00", "close": "22:00"},
            "saturday": {"open": "10:00", "close": "22:00"},
            "sunday": {"open": "10:00", "close": "20:00"}
        },
        "rating": 4.5,
        "total_reviews": 100,
        "is_active": True,
        "is_verified": True,
        "created_at": datetime.utcnow()
    }
    await stores_col.insert_one(store_doc)
    store_doc["id"] = str(store_doc["_id"])
    return store_doc


# ============ PRODUCT FIXTURES ============

@pytest_asyncio.fixture
async def test_product(clean_db, test_store) -> dict:
    """Create a test product."""
    products_col = get_collection("products")
    product_doc = {
        "_id": ObjectId(),
        "store_id": test_store["id"],
        "name": "Test Burger",
        "description": "A delicious test burger",
        "price": 85.00,
        "category": "burgers",
        "images": ["https://example.com/burger.jpg"],
        "stock_quantity": 100,
        "is_available": True,
        "preparation_time_minutes": 15,
        "created_at": datetime.utcnow()
    }
    await products_col.insert_one(product_doc)
    product_doc["id"] = str(product_doc["_id"])
    return product_doc


# ============ ORDER FIXTURES ============

@pytest_asyncio.fixture
async def test_order(clean_db, test_user, test_store, test_product) -> dict:
    """Create a test order."""
    orders_col = get_collection("orders")
    buyers_col = get_collection("buyers")
    
    # Create buyer profile
    buyer_doc = {
        "_id": ObjectId(),
        "user_id": test_user["id"],
        "phone_number": test_user["phone"],
        "addresses": [{
            "id": "addr_123",
            "label": "Home",
            "address_line1": "456 Test Avenue",
            "city": "Johannesburg",
            "area": "Sandton",
            "latitude": -26.1076,
            "longitude": 28.0567
        }],
        "created_at": datetime.utcnow()
    }
    await buyers_col.insert_one(buyer_doc)
    
    order_doc = {
        "_id": ObjectId(),
        "buyer_id": test_user["id"],
        "store_id": test_store["id"],
        "items": [{
            "product_id": test_product["id"],
            "product_name": test_product["name"],
            "quantity": 2,
            "unit_price": test_product["price"],
            "total_price": test_product["price"] * 2
        }],
        "subtotal": 170.00,
        "delivery_fee": 25.00,
        "total": 195.00,
        "currency": "ZAR",
        "status": OrderStatus.PENDING.value,
        "status_history": [{
            "status": OrderStatus.PENDING.value,
            "timestamp": datetime.utcnow().isoformat(),
            "by": test_user["id"]
        }],
        "delivery_info": {
            "address_label": "Home",
            "address_line1": "456 Test Avenue",
            "city": "Johannesburg",
            "area": "Sandton",
            "latitude": -26.1076,
            "longitude": 28.0567,
            "recipient_phone": test_user["phone"]
        },
        "payment_method": "card",
        "payment_status": "pending",
        "created_at": datetime.utcnow()
    }
    await orders_col.insert_one(order_doc)
    order_doc["id"] = str(order_doc["_id"])
    return order_doc


@pytest_asyncio.fixture
async def test_order_confirmed(clean_db, test_order) -> dict:
    """Create a confirmed test order."""
    orders_col = get_collection("orders")
    await orders_col.update_one(
        {"_id": ObjectId(test_order["id"])},
        {
            "$set": {
                "status": OrderStatus.CONFIRMED.value,
                "confirmed_at": datetime.utcnow()
            },
            "$push": {
                "status_history": {
                    "status": OrderStatus.CONFIRMED.value,
                    "timestamp": datetime.utcnow().isoformat(),
                    "by": test_order["store_id"]
                }
            }
        }
    )
    test_order["status"] = OrderStatus.CONFIRMED.value
    return test_order


# ============ REFERRAL FIXTURES ============

@pytest_asyncio.fixture
async def test_referral_code(clean_db, test_customer) -> dict:
    """Create a test referral code."""
    referral_codes_col = get_collection("referral_codes")
    referral_code_doc = {
        "_id": ObjectId(),
        "user_id": test_customer["id"],
        "code": "IH-C-TEST12",
        "referral_type": "customer",
        "is_active": True,
        "created_at": datetime.utcnow()
    }
    await referral_codes_col.insert_one(referral_code_doc)
    referral_code_doc["id"] = str(referral_code_doc["_id"])
    return referral_code_doc


@pytest_asyncio.fixture
async def test_vendor_referral_code(clean_db, test_merchant) -> dict:
    """Create a test vendor referral code."""
    referral_codes_col = get_collection("referral_codes")
    referral_code_doc = {
        "_id": ObjectId(),
        "user_id": test_merchant["id"],
        "code": "IH-V-TEST12",
        "referral_type": "vendor",
        "is_active": True,
        "created_at": datetime.utcnow()
    }
    await referral_codes_col.insert_one(referral_code_doc)
    referral_code_doc["id"] = str(referral_code_doc["_id"])
    return referral_code_doc


@pytest_asyncio.fixture
async def test_customer_reward_account(clean_db, test_customer) -> dict:
    """Create a test customer reward account."""
    reward_accounts_col = get_collection("customer_reward_accounts")
    account_doc = {
        "_id": ObjectId(),
        "customer_id": test_customer["id"],
        "referral_code": "IH-C-TEST12",
        "tier": "bronze",
        "hashi_coins_balance": 100,
        "total_coins_earned": 150,
        "total_coins_spent": 50,
        "total_referrals": 2,
        "completed_referrals": 2,
        "pending_referrals": 0,
        "free_delivery_credits": 1,
        "discount_credits": 15.0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    await reward_accounts_col.insert_one(account_doc)
    account_doc["id"] = str(account_doc["_id"])
    return account_doc


# ============ PAYMENT FIXTURES ============

@pytest_asyncio.fixture
async def test_payment(clean_db, test_user, test_order) -> dict:
    """Create a test payment record."""
    payments_col = get_collection("payments")
    payment_doc = {
        "_id": ObjectId(),
        "reference": "ihhashi-test123abc",
        "user_id": test_user["id"],
        "email": test_user["email"],
        "amount": test_order["total"],
        "order_id": test_order["id"],
        "status": "pending",
        "created_at": datetime.utcnow()
    }
    await payments_col.insert_one(payment_doc)
    payment_doc["id"] = str(payment_doc["_id"])
    return payment_doc


# ============ MOCK FIXTURES ============

@pytest.fixture
def mock_paystack():
    """Mock Paystack service."""
    with patch("app.services.paystack.PaystackService") as mock:
        instance = mock.return_value
        instance.initialize_payment = AsyncMock(return_value={
            "status": True,
            "data": {
                "authorization_url": "https://checkout.paystack.com/test",
                "reference": "ihhashi-test123abc",
                "access_code": "test_access_code"
            }
        })
        instance.verify_payment = AsyncMock(return_value={
            "status": True,
            "data": {
                "status": "success",
                "reference": "ihhashi-test123abc",
                "amount": 19500,
                "paid_at": datetime.utcnow().isoformat(),
                "channel": "card"
            }
        })
        instance.create_transfer_recipient = AsyncMock(return_value={
            "status": True,
            "data": {
                "recipient_code": "RCP_test123"
            }
        })
        instance.initiate_transfer = AsyncMock(return_value={
            "status": True,
            "data": {
                "transfer_code": "TRF_test123"
            }
        })
        instance.verify_account_number = AsyncMock(return_value={
            "status": True,
            "data": {
                "account_name": "Test Account",
                "account_number": "1234567890"
            }
        })
        instance.refund_payment = AsyncMock(return_value={
            "status": True,
            "data": {
                "id": "ref_test123",
                "status": "processed"
            }
        })
        yield instance


@pytest.fixture
def mock_redis():
    """Mock Redis for token blacklist."""
    with patch("app.core.redis_client.redis_client") as mock:
        instance = MagicMock()
        instance.get = MagicMock(return_value=None)
        instance.set = MagicMock(return_value=True)
        instance.delete = MagicMock(return_value=True)
        instance.exists = MagicMock(return_value=False)
        mock.return_value = instance
        yield instance


@pytest.fixture
def mock_token_blacklist():
    """Mock TokenBlacklist."""
    with patch("app.core.redis_client.TokenBlacklist") as mock:
        mock.is_blacklisted = AsyncMock(return_value=False)
        mock.add = AsyncMock(return_value=True)
        yield mock


# ============ WEBSOCKET FIXTURES ============

@pytest.fixture
def websocket_token(test_user):
    """Generate a valid WebSocket token."""
    return create_access_token(
        data={"sub": test_user["id"], "role": test_user["role"]},
        expires_delta=timedelta(hours=1)
    )


@pytest.fixture
def mock_websocket_manager():
    """Mock WebSocket connection manager."""
    with patch("app.routes.websocket.manager") as mock:
        mock.connect_order_tracker = AsyncMock()
        mock.connect_rider = AsyncMock()
        mock.connect_user = AsyncMock()
        mock.disconnect = MagicMock()
        mock.broadcast_order_update = AsyncMock()
        mock.send_to_rider = AsyncMock()
        mock.send_to_user = AsyncMock()
        yield mock


# ============ HELPER FUNCTIONS ============

def create_test_token(user_id: str, role: str, expires_hours: int = 1) -> str:
    """Create a JWT token for testing."""
    return create_access_token(
        data={"sub": user_id, "role": role},
        expires_delta=timedelta(hours=expires_hours)
    )


async def create_test_user_direct(
    email: str,
    role: UserRole = UserRole.BUYER,
    phone: str = "+27820000000"
) -> dict:
    """Create a test user directly in database."""
    users_col = get_collection("users")
    user_doc = {
        "_id": ObjectId(),
        "email": email,
        "phone": phone,
        "full_name": f"Test {role.value}",
        "hashed_password": get_password_hash(TEST_PASSWORD),
        "role": role,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    await users_col.insert_one(user_doc)
    user_doc["id"] = str(user_doc["_id"])
    return user_doc
