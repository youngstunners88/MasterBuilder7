"""
Tests for order endpoints and services.

Covers:
- Order creation
- Status transitions
- Order cancellation
- Order retrieval
- Access control
"""
import pytest
from datetime import datetime, timedelta
from bson import ObjectId
from unittest.mock import patch, AsyncMock

from fastapi import status
from httpx import AsyncClient

from app.models import OrderStatus, UserRole


# ============ ORDER CREATION TESTS ============

class TestOrderCreation:
    """Tests for order creation endpoint."""
    
    @pytest.mark.asyncio
    async def test_create_order_success(
        self,
        async_client: AsyncClient,
        test_user,
        test_store,
        test_product,
        buyer_auth_headers
    ):
        """Test successful order creation."""
        # Create buyer profile with address
        from app.database import get_collection
        buyers_col = get_collection("buyers")
        await buyers_col.insert_one({
            "_id": ObjectId(),
            "user_id": test_user["id"],
            "phone_number": test_user["phone"],
            "addresses": [{
                "id": "addr_001",
                "label": "Home",
                "address_line1": "123 Delivery Street",
                "city": "Johannesburg",
                "area": "Sandton",
                "latitude": -26.1076,
                "longitude": 28.0567
            }],
            "created_at": datetime.utcnow()
        })
        
        response = await async_client.post(
            "/api/orders/",
            headers=buyer_auth_headers,
            json={
                "store_id": test_store["id"],
                "items": [{"product_id": test_product["id"], "quantity": 2}],
                "delivery_address_id": "addr_001",
                "payment_method": "card"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "order_id" in data
        assert data["total"] > 0
        assert "delivery_fee" in data
    
    @pytest.mark.asyncio
    async def test_create_order_invalid_store(
        self,
        async_client: AsyncClient,
        test_user,
        test_product,
        buyer_auth_headers
    ):
        """Test order creation with invalid store fails."""
        from app.database import get_collection
        buyers_col = get_collection("buyers")
        await buyers_col.insert_one({
            "_id": ObjectId(),
            "user_id": test_user["id"],
            "phone_number": test_user["phone"],
            "addresses": [{
                "id": "addr_002",
                "label": "Work",
                "address_line1": "456 Office Park",
                "city": "Johannesburg",
                "area": "Sandton"
            }],
            "created_at": datetime.utcnow()
        })
        
        response = await async_client.post(
            "/api/orders/",
            headers=buyer_auth_headers,
            json={
                "store_id": str(ObjectId()),  # Non-existent store
                "items": [{"product_id": test_product["id"], "quantity": 1}],
                "delivery_address_id": "addr_002",
                "payment_method": "card"
            }
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_create_order_invalid_product(
        self,
        async_client: AsyncClient,
        test_user,
        test_store,
        buyer_auth_headers
    ):
        """Test order creation with invalid product fails."""
        from app.database import get_collection
        buyers_col = get_collection("buyers")
        await buyers_col.insert_one({
            "_id": ObjectId(),
            "user_id": test_user["id"],
            "phone_number": test_user["phone"],
            "addresses": [{
                "id": "addr_003",
                "label": "Home",
                "address_line1": "123 Street",
                "city": "Johannesburg"
            }],
            "created_at": datetime.utcnow()
        })
        
        response = await async_client.post(
            "/api/orders/",
            headers=buyer_auth_headers,
            json={
                "store_id": test_store["id"],
                "items": [{"product_id": str(ObjectId()), "quantity": 1}],  # Non-existent product
                "delivery_address_id": "addr_003",
                "payment_method": "card"
            }
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_create_order_invalid_address(
        self,
        async_client: AsyncClient,
        test_user,
        test_store,
        test_product,
        buyer_auth_headers
    ):
        """Test order creation with invalid address fails."""
        # No buyer profile created
        response = await async_client.post(
            "/api/orders/",
            headers=buyer_auth_headers,
            json={
                "store_id": test_store["id"],
                "items": [{"product_id": test_product["id"], "quantity": 1}],
                "delivery_address_id": "nonexistent_addr",
                "payment_method": "card"
            }
        )
        
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND]
    
    @pytest.mark.asyncio
    async def test_create_order_insufficient_stock(
        self,
        async_client: AsyncClient,
        test_user,
        test_store,
        test_product,
        buyer_auth_headers
    ):
        """Test order creation with insufficient stock fails."""
        from app.database import get_collection
        buyers_col = get_collection("buyers")
        await buyers_col.insert_one({
            "_id": ObjectId(),
            "user_id": test_user["id"],
            "phone_number": test_user["phone"],
            "addresses": [{
                "id": "addr_004",
                "label": "Home",
                "address_line1": "123 Street",
                "city": "Johannesburg"
            }],
            "created_at": datetime.utcnow()
        })
        
        # Request more than available stock
        response = await async_client.post(
            "/api/orders/",
            headers=buyer_auth_headers,
            json={
                "store_id": test_store["id"],
                "items": [{"product_id": test_product["id"], "quantity": 10000}],  # Way too many
                "delivery_address_id": "addr_004",
                "payment_method": "card"
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.asyncio
    async def test_create_order_unauthenticated(self, async_client: AsyncClient, test_store):
        """Test order creation without authentication fails."""
        response = await async_client.post(
            "/api/orders/",
            json={
                "store_id": test_store["id"],
                "items": [],
                "delivery_address_id": "any",
                "payment_method": "card"
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_create_order_calculates_delivery_fee(
        self,
        async_client: AsyncClient,
        test_user,
        test_store,
        test_product,
        buyer_auth_headers
    ):
        """Test that delivery fee is calculated based on distance."""
        from app.database import get_collection
        buyers_col = get_collection("buyers")
        await buyers_col.insert_one({
            "_id": ObjectId(),
            "user_id": test_user["id"],
            "phone_number": test_user["phone"],
            "addresses": [{
                "id": "addr_005",
                "label": "Far Away",
                "address_line1": "Distant Location",
                "city": "Pretoria",
                "latitude": -25.7479,  # Further from Johannesburg
                "longitude": 28.2293
            }],
            "created_at": datetime.utcnow()
        })
        
        response = await async_client.post(
            "/api/orders/",
            headers=buyer_auth_headers,
            json={
                "store_id": test_store["id"],
                "items": [{"product_id": test_product["id"], "quantity": 1}],
                "delivery_address_id": "addr_005",
                "payment_method": "card"
            }
        )
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert data["delivery_fee"] > 0


# ============ ORDER RETRIEVAL TESTS ============

class TestOrderRetrieval:
    """Tests for order retrieval endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_order_by_id_success(
        self,
        async_client: AsyncClient,
        test_order,
        buyer_auth_headers
    ):
        """Test getting order by ID."""
        response = await async_client.get(
            f"/api/orders/{test_order['id']}",
            headers=buyer_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["order"]["id"] == test_order["id"]
    
    @pytest.mark.asyncio
    async def test_get_order_nonexistent(
        self,
        async_client: AsyncClient,
        buyer_auth_headers
    ):
        """Test getting non-existent order fails."""
        fake_id = str(ObjectId())
        response = await async_client.get(
            f"/api/orders/{fake_id}",
            headers=buyer_auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_get_order_unauthorized(
        self,
        async_client: AsyncClient,
        test_order
    ):
        """Test getting order without auth fails."""
        response = await async_client.get(f"/api/orders/{test_order['id']}")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_get_order_wrong_user(
        self,
        async_client: AsyncClient,
        test_order,
        test_merchant
    ):
        """Test getting another user's order fails."""
        # Create token for different user
        from app.services.auth import create_access_token
        
        token = create_access_token(
            data={"sub": str(ObjectId()), "role": UserRole.BUYER},
            expires_delta=timedelta(hours=1)
        )
        
        response = await async_client.get(
            f"/api/orders/{test_order['id']}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_get_orders_list(
        self,
        async_client: AsyncClient,
        test_order,
        buyer_auth_headers
    ):
        """Test getting list of orders."""
        response = await async_client.get(
            "/api/orders/",
            headers=buyer_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "orders" in data
        assert "total" in data
        assert isinstance(data["orders"], list)
    
    @pytest.mark.asyncio
    async def test_get_orders_filter_by_status(
        self,
        async_client: AsyncClient,
        test_order,
        buyer_auth_headers
    ):
        """Test filtering orders by status."""
        response = await async_client.get(
            "/api/orders/?status=pending",
            headers=buyer_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for order in data["orders"]:
            assert order["status"] == "pending"
    
    @pytest.mark.asyncio
    async def test_get_orders_pagination(
        self,
        async_client: AsyncClient,
        test_order,
        buyer_auth_headers
    ):
        """Test orders list pagination."""
        response = await async_client.get(
            "/api/orders/?limit=10&offset=0",
            headers=buyer_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 0


# ============ ORDER STATUS TESTS ============

class TestOrderStatusTransitions:
    """Tests for order status transitions."""
    
    @pytest.mark.asyncio
    async def test_confirm_pending_order(
        self,
        async_client: AsyncClient,
        test_order,
        merchant_auth_headers
    ):
        """Test confirming a pending order."""
        response = await async_client.put(
            f"/api/orders/{test_order['id']}/status",
            headers=merchant_auth_headers,
            json={"status": "confirmed"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "confirmed"
    
    @pytest.mark.asyncio
    async def test_preparing_order(
        self,
        async_client: AsyncClient,
        test_order_confirmed,
        merchant_auth_headers
    ):
        """Test transitioning to preparing status."""
        response = await async_client.put(
            f"/api/orders/{test_order_confirmed['id']}/status",
            headers=merchant_auth_headers,
            json={"status": "preparing"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "preparing"
    
    @pytest.mark.asyncio
    async def test_ready_for_pickup(
        self,
        async_client: AsyncClient,
        test_order,
        merchant_auth_headers,
        clean_db
    ):
        """Test transitioning to ready status."""
        from app.database import get_collection
        orders_col = get_collection("orders")
        
        # Set order to preparing
        await orders_col.update_one(
            {"_id": ObjectId(test_order["id"])},
            {"$set": {"status": OrderStatus.PREPARING.value}}
        )
        
        response = await async_client.put(
            f"/api/orders/{test_order['id']}/status",
            headers=merchant_auth_headers,
            json={"status": "ready"}
        )
        
        assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.asyncio
    async def test_picked_up_by_driver(
        self,
        async_client: AsyncClient,
        test_order,
        driver_auth_headers,
        clean_db
    ):
        """Test driver picking up order."""
        from app.database import get_collection
        orders_col = get_collection("orders")
        
        # Set order to ready
        await orders_col.update_one(
            {"_id": ObjectId(test_order["id"])},
            {"$set": {"status": OrderStatus.READY.value}}
        )
        
        response = await async_client.put(
            f"/api/orders/{test_order['id']}/status",
            headers=driver_auth_headers,
            json={"status": "picked_up"}
        )
        
        assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.asyncio
    async def test_in_transit(
        self,
        async_client: AsyncClient,
        test_order,
        driver_auth_headers,
        clean_db
    ):
        """Test marking order as in transit."""
        from app.database import get_collection
        orders_col = get_collection("orders")
        
        # Set order to picked_up
        await orders_col.update_one(
            {"_id": ObjectId(test_order["id"])},
            {"$set": {"status": OrderStatus.PICKED_UP.value}}
        )
        
        response = await async_client.put(
            f"/api/orders/{test_order['id']}/status",
            headers=driver_auth_headers,
            json={"status": "in_transit"}
        )
        
        assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.asyncio
    async def test_delivered(
        self,
        async_client: AsyncClient,
        test_order,
        driver_auth_headers,
        clean_db
    ):
        """Test marking order as delivered."""
        from app.database import get_collection
        orders_col = get_collection("orders")
        
        # Set order to in_transit
        await orders_col.update_one(
            {"_id": ObjectId(test_order["id"])},
            {"$set": {"status": OrderStatus.IN_TRANSIT.value}}
        )
        
        response = await async_client.put(
            f"/api/orders/{test_order['id']}/status",
            headers=driver_auth_headers,
            json={"status": "delivered"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "delivered"
    
    @pytest.mark.asyncio
    async def test_invalid_status_transition(
        self,
        async_client: AsyncClient,
        test_order,
        merchant_auth_headers
    ):
        """Test invalid status transition fails."""
        # Try to go from pending directly to delivered
        response = await async_client.put(
            f"/api/orders/{test_order['id']}/status",
            headers=merchant_auth_headers,
            json={"status": "delivered"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.asyncio
    async def test_status_transition_by_buyer_fails(
        self,
        async_client: AsyncClient,
        test_order,
        buyer_auth_headers
    ):
        """Test that buyer cannot change order status."""
        response = await async_client.put(
            f"/api/orders/{test_order['id']}/status",
            headers=buyer_auth_headers,
            json={"status": "confirmed"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ============ ORDER CANCELLATION TESTS ============

class TestOrderCancellation:
    """Tests for order cancellation."""
    
    @pytest.mark.asyncio
    async def test_cancel_pending_order(
        self,
        async_client: AsyncClient,
        test_order,
        buyer_auth_headers
    ):
        """Test cancelling a pending order."""
        response = await async_client.post(
            f"/api/orders/{test_order['id']}/cancel",
            headers=buyer_auth_headers,
            params={"reason": "Changed my mind"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "cancelled" in data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_cancel_confirmed_order(
        self,
        async_client: AsyncClient,
        test_order_confirmed,
        buyer_auth_headers
    ):
        """Test cancelling a confirmed order."""
        response = await async_client.post(
            f"/api/orders/{test_order_confirmed['id']}/cancel",
            headers=buyer_auth_headers,
            params={"reason": "Taking too long"}
        )
        
        assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.asyncio
    async def test_cancel_in_transit_order_fails(
        self,
        async_client: AsyncClient,
        test_order,
        buyer_auth_headers,
        clean_db
    ):
        """Test cancelling an in-transit order fails."""
        from app.database import get_collection
        orders_col = get_collection("orders")
        
        # Set order to in_transit
        await orders_col.update_one(
            {"_id": ObjectId(test_order["id"])},
            {"$set": {"status": OrderStatus.IN_TRANSIT.value}}
        )
        
        response = await async_client.post(
            f"/api/orders/{test_order['id']}/cancel",
            headers=buyer_auth_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.asyncio
    async def test_cancel_by_non_buyer_fails(
        self,
        async_client: AsyncClient,
        test_order,
        merchant_auth_headers
    ):
        """Test that non-buyer cannot cancel order."""
        response = await async_client.post(
            f"/api/orders/{test_order['id']}/cancel",
            headers=merchant_auth_headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_cancel_sets_cancellation_reason(
        self,
        async_client: AsyncClient,
        test_order,
        buyer_auth_headers
    ):
        """Test that cancellation reason is saved."""
        response = await async_client.post(
            f"/api/orders/{test_order['id']}/cancel",
            headers=buyer_auth_headers,
            params={"reason": "Found better deal elsewhere"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify reason was saved
        from app.database import get_collection
        orders_col = get_collection("orders")
        order = await orders_col.find_one({"_id": ObjectId(test_order["id"])})
        
        assert order["cancellation_reason"] == "Found better deal elsewhere"


# ============ ORDER TRACKING TESTS ============

class TestOrderTracking:
    """Tests for order tracking endpoint."""
    
    @pytest.mark.asyncio
    async def test_track_order_success(
        self,
        async_client: AsyncClient,
        test_order
    ):
        """Test tracking an order (public endpoint)."""
        response = await async_client.get(
            f"/api/orders/{test_order['id']}/track"
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert "order_id" in data
    
    @pytest.mark.asyncio
    async def test_track_order_with_rider(
        self,
        async_client: AsyncClient,
        test_order,
        test_driver,
        clean_db
    ):
        """Test tracking order with assigned rider."""
        from app.database import get_collection
        orders_col = get_collection("orders")
        
        # Assign rider to order
        await orders_col.update_one(
            {"_id": ObjectId(test_order["id"])},
            {
                "$set": {
                    "rider_id": test_driver["id"],
                    "status": OrderStatus.IN_TRANSIT.value
                }
            }
        )
        
        response = await async_client.get(
            f"/api/orders/{test_order['id']}/track"
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        if data.get("rider"):
            assert "name" in data["rider"]
            assert "phone" in data["rider"]
    
    @pytest.mark.asyncio
    async def test_track_nonexistent_order(
        self,
        async_client: AsyncClient
    ):
        """Test tracking non-existent order."""
        fake_id = str(ObjectId())
        response = await async_client.get(f"/api/orders/{fake_id}/track")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ============ DELIVERY FEE TESTS ============

class TestDeliveryFeeCalculation:
    """Tests for delivery fee calculation."""
    
    @pytest.mark.asyncio
    async def test_delivery_fee_within_range(
        self,
        test_store,
        clean_db
    ):
        """Test delivery fee for nearby location."""
        from app.routes.orders import calculate_delivery_fee
        
        store_location = {
            "latitude": -26.2041,
            "longitude": 28.0473
        }
        delivery_location = {
            "latitude": -26.1076,  # ~10km away
            "longitude": 28.0567
        }
        
        fee = await calculate_delivery_fee(store_location, delivery_location)
        
        assert fee > 0
        assert fee < 150  # Should not exceed cap
    
    @pytest.mark.asyncio
    async def test_delivery_fee_far_distance(self, clean_db):
        """Test delivery fee for far location is capped."""
        from app.routes.orders import calculate_delivery_fee
        
        store_location = {
            "latitude": -26.2041,
            "longitude": 28.0473
        }
        delivery_location = {
            "latitude": -25.7479,  # Pretoria, ~50km away
            "longitude": 28.2293
        }
        
        fee = await calculate_delivery_fee(store_location, delivery_location)
        
        assert fee <= 150  # Capped at R150
    
    @pytest.mark.asyncio
    async def test_delivery_fee_same_location(self, clean_db):
        """Test delivery fee for same location."""
        from app.routes.orders import calculate_delivery_fee
        
        location = {
            "latitude": -26.2041,
            "longitude": 28.0473
        }
        
        fee = await calculate_delivery_fee(location, location)
        
        # Should still have base fee even for same location
        assert fee >= 15  # Base fee


# ============ ACCESS CONTROL TESTS ============

class TestOrderAccessControl:
    """Tests for order access control."""
    
    @pytest.mark.asyncio
    async def test_merchant_can_see_their_orders(
        self,
        async_client: AsyncClient,
        test_order,
        merchant_auth_headers
    ):
        """Test merchant can see orders for their store."""
        response = await async_client.get(
            "/api/orders/",
            headers=merchant_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.asyncio
    async def test_driver_can_see_assigned_orders(
        self,
        async_client: AsyncClient,
        test_order,
        test_driver,
        driver_auth_headers,
        clean_db
    ):
        """Test driver can see orders assigned to them."""
        from app.database import get_collection
        orders_col = get_collection("orders")
        
        # Assign order to driver
        await orders_col.update_one(
            {"_id": ObjectId(test_order["id"])},
            {"$set": {"rider_id": test_driver["id"]}}
        )
        
        response = await async_client.get(
            "/api/orders/",
            headers=driver_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.asyncio
    async def test_admin_can_see_all_orders(
        self,
        async_client: AsyncClient,
        test_order,
        admin_auth_headers
    ):
        """Test admin can see all orders."""
        response = await async_client.get(
            "/api/orders/",
            headers=admin_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
