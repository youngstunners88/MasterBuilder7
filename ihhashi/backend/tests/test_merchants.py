"""
Tests for merchant operations.

Covers:
- Merchant listing and search
- Merchant details
- Merchant menu/products
- Merchant protected endpoints (create, update, delete)
- Merchant orders and stats
"""
import pytest
from datetime import datetime
from bson import ObjectId
from httpx import AsyncClient
from fastapi import status


# ============ PUBLIC ENDPOINTS TESTS ============

class TestMerchantListing:
    """Tests for merchant listing endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_merchants_list(
        self,
        async_client: AsyncClient,
        test_store
    ):
        """Test getting list of merchants."""
        response = await async_client.get("/api/v1/merchants/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "merchants" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert isinstance(data["merchants"], list)
    
    @pytest.mark.asyncio
    async def test_get_merchants_with_category_filter(
        self,
        async_client: AsyncClient,
        test_store
    ):
        """Test filtering merchants by category."""
        response = await async_client.get("/api/v1/merchants/?category=restaurant")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for merchant in data["merchants"]:
            assert merchant["category"] == "restaurant"
    
    @pytest.mark.asyncio
    async def test_get_merchants_with_city_filter(
        self,
        async_client: AsyncClient,
        test_store
    ):
        """Test filtering merchants by city."""
        response = await async_client.get("/api/v1/merchants/?city=Johannesburg")
        
        assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.asyncio
    async def test_get_merchants_with_search(
        self,
        async_client: AsyncClient,
        test_store
    ):
        """Test searching merchants."""
        response = await async_client.get("/api/v1/merchants/?search=Test")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should find our test store
        assert len(data["merchants"]) > 0
    
    @pytest.mark.asyncio
    async def test_get_merchants_pagination(
        self,
        async_client: AsyncClient,
        test_store
    ):
        """Test merchant pagination."""
        response = await async_client.get("/api/v1/merchants/?limit=5&offset=0")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["limit"] == 5
        assert data["offset"] == 0


class TestMerchantDetails:
    """Tests for merchant detail endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_merchant_details(
        self,
        async_client: AsyncClient,
        test_store
    ):
        """Test getting single merchant details."""
        response = await async_client.get(f"/api/v1/merchants/{test_store['id']}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "merchant" in data
        assert data["merchant"]["id"] == test_store["id"]
        assert "stats" in data
    
    @pytest.mark.asyncio
    async def test_get_merchant_not_found(
        self,
        async_client: AsyncClient
    ):
        """Test getting non-existent merchant."""
        fake_id = str(ObjectId())
        response = await async_client.get(f"/api/v1/merchants/{fake_id}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestMerchantMenu:
    """Tests for merchant menu endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_merchant_menu(
        self,
        async_client: AsyncClient,
        test_store,
        test_product
    ):
        """Test getting merchant menu."""
        response = await async_client.get(f"/api/v1/merchants/{test_store['id']}/menu")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "menu" in data
        assert "categories" in data
        assert "total_products" in data
        assert isinstance(data["menu"], dict)
    
    @pytest.mark.asyncio
    async def test_get_product_details(
        self,
        async_client: AsyncClient,
        test_store,
        test_product
    ):
        """Test getting single product details."""
        response = await async_client.get(
            f"/api/v1/merchants/{test_store['id']}/products/{test_product['id']}"
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "product" in data
        assert data["product"]["id"] == test_product["id"]
    
    @pytest.mark.asyncio
    async def test_get_product_not_found(
        self,
        async_client: AsyncClient,
        test_store
    ):
        """Test getting non-existent product."""
        fake_id = str(ObjectId())
        response = await async_client.get(
            f"/api/v1/merchants/{test_store['id']}/products/{fake_id}"
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ============ PROTECTED ENDPOINTS TESTS ============

class TestMerchantCreation:
    """Tests for merchant creation."""
    
    @pytest.mark.asyncio
    async def test_create_merchant_store(
        self,
        async_client: AsyncClient,
        test_merchant,
        merchant_auth_headers
    ):
        """Test creating a merchant store."""
        # First delete any existing store for this merchant
        from app.database import get_collection
        stores_col = get_collection("stores")
        await stores_col.delete_many({"owner_id": test_merchant["id"]})
        
        response = await async_client.post(
            "/api/v1/merchants/",
            headers=merchant_auth_headers,
            params={
                "name": "New Test Store",
                "category": "restaurant",
                "address_line1": "123 Test Street",
                "city": "Johannesburg",
                "phone": "+27821234568",
                "description": "A test restaurant",
                "latitude": -26.2041,
                "longitude": 28.0473
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "store_id" in data
        assert "message" in data
        assert data["status"] == "pending"
    
    @pytest.mark.asyncio
    async def test_create_merchant_store_already_exists(
        self,
        async_client: AsyncClient,
        test_merchant,
        test_store,
        merchant_auth_headers
    ):
        """Test creating store when one already exists."""
        response = await async_client.post(
            "/api/v1/merchants/",
            headers=merchant_auth_headers,
            params={
                "name": "Another Store",
                "category": "restaurant",
                "address_line1": "456 Test Street",
                "city": "Johannesburg",
                "phone": "+27821234568"
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.asyncio
    async def test_create_merchant_store_unauthorized(
        self,
        async_client: AsyncClient,
        buyer_auth_headers
    ):
        """Test creating store as non-merchant."""
        response = await async_client.post(
            "/api/v1/merchants/",
            headers=buyer_auth_headers,
            params={
                "name": "Unauthorized Store",
                "category": "restaurant",
                "address_line1": "789 Test Street",
                "city": "Johannesburg",
                "phone": "+27821234567"
            }
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestMerchantStoreManagement:
    """Tests for merchant store management."""
    
    @pytest.mark.asyncio
    async def test_get_my_store(
        self,
        async_client: AsyncClient,
        test_merchant,
        test_store,
        merchant_auth_headers
    ):
        """Test merchant getting their own store."""
        response = await async_client.get(
            "/api/v1/merchants/my/store",
            headers=merchant_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "store" in data
        assert data["store"]["id"] == test_store["id"]
    
    @pytest.mark.asyncio
    async def test_update_my_store(
        self,
        async_client: AsyncClient,
        test_merchant,
        test_store,
        merchant_auth_headers
    ):
        """Test updating merchant store."""
        response = await async_client.put(
            "/api/v1/merchants/my/store",
            headers=merchant_auth_headers,
            params={
                "name": "Updated Store Name",
                "description": "Updated description"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Store updated"
    
    @pytest.mark.asyncio
    async def test_get_my_store_not_found(
        self,
        async_client: AsyncClient,
        test_merchant,
        merchant_auth_headers
    ):
        """Test getting store when none exists."""
        # Delete the store first
        from app.database import get_collection
        stores_col = get_collection("stores")
        await stores_col.delete_many({"owner_id": test_merchant["id"]})
        
        response = await async_client.get(
            "/api/v1/merchants/my/store",
            headers=merchant_auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestMerchantProducts:
    """Tests for merchant product management."""
    
    @pytest.mark.asyncio
    async def test_create_product(
        self,
        async_client: AsyncClient,
        test_merchant,
        test_store,
        merchant_auth_headers
    ):
        """Test creating a product."""
        response = await async_client.post(
            "/api/v1/merchants/my/products",
            headers=merchant_auth_headers,
            params={
                "name": "New Product",
                "price": 99.99,
                "category": "burgers",
                "description": "A tasty burger",
                "stock_quantity": 50
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "product_id" in data
        assert "message" in data
    
    @pytest.mark.asyncio
    async def test_get_my_products(
        self,
        async_client: AsyncClient,
        test_merchant,
        test_store,
        test_product,
        merchant_auth_headers
    ):
        """Test getting merchant's products."""
        response = await async_client.get(
            "/api/v1/merchants/my/products",
            headers=merchant_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "products" in data
        assert "total" in data
    
    @pytest.mark.asyncio
    async def test_update_product(
        self,
        async_client: AsyncClient,
        test_merchant,
        test_store,
        test_product,
        merchant_auth_headers
    ):
        """Test updating a product."""
        response = await async_client.put(
            f"/api/v1/merchants/my/products/{test_product['id']}",
            headers=merchant_auth_headers,
            params={
                "name": "Updated Product Name",
                "price": 109.99
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Product updated"
    
    @pytest.mark.asyncio
    async def test_update_product_not_found(
        self,
        async_client: AsyncClient,
        test_merchant,
        test_store,
        merchant_auth_headers
    ):
        """Test updating non-existent product."""
        fake_id = str(ObjectId())
        response = await async_client.put(
            f"/api/v1/merchants/my/products/{fake_id}",
            headers=merchant_auth_headers,
            params={"name": "Non-existent"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_delete_product(
        self,
        async_client: AsyncClient,
        test_merchant,
        test_store,
        test_product,
        merchant_auth_headers
    ):
        """Test deleting a product."""
        response = await async_client.delete(
            f"/api/v1/merchants/my/products/{test_product['id']}",
            headers=merchant_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Product deleted"
    
    @pytest.mark.asyncio
    async def test_create_product_unauthorized(
        self,
        async_client: AsyncClient,
        buyer_auth_headers
    ):
        """Test creating product as non-merchant."""
        response = await async_client.post(
            "/api/v1/merchants/my/products",
            headers=buyer_auth_headers,
            params={
                "name": "Unauthorized Product",
                "price": 50.00,
                "category": "test"
            }
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestMerchantOrders:
    """Tests for merchant order management."""
    
    @pytest.mark.asyncio
    async def test_get_merchant_orders(
        self,
        async_client: AsyncClient,
        test_merchant,
        test_store,
        test_order,
        merchant_auth_headers
    ):
        """Test getting merchant's orders."""
        response = await async_client.get(
            "/api/v1/merchants/my/orders",
            headers=merchant_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "orders" in data
        assert "total" in data
    
    @pytest.mark.asyncio
    async def test_get_merchant_orders_with_status_filter(
        self,
        async_client: AsyncClient,
        test_merchant,
        test_store,
        test_order,
        merchant_auth_headers
    ):
        """Test filtering merchant orders by status."""
        response = await async_client.get(
            "/api/v1/merchants/my/orders?status=pending",
            headers=merchant_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for order in data["orders"]:
            assert order["status"] == "pending"


class TestMerchantStats:
    """Tests for merchant statistics."""
    
    @pytest.mark.asyncio
    async def test_get_merchant_stats(
        self,
        async_client: AsyncClient,
        test_merchant,
        test_store,
        merchant_auth_headers
    ):
        """Test getting merchant dashboard stats."""
        response = await async_client.get(
            "/api/v1/merchants/my/stats",
            headers=merchant_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "store" in data
        assert "orders" in data
        assert "revenue" in data
        
        # Check store info
        assert "name" in data["store"]
        assert "status" in data["store"]
        assert "is_open" in data["store"]
        assert "rating" in data["store"]
        
        # Check order stats
        assert "total" in data["orders"]
        assert "pending" in data["orders"]
        assert "completed" in data["orders"]
        
        # Check revenue
        assert "total" in data["revenue"]
        assert "platform_fees" in data["revenue"]
        assert "net" in data["revenue"]
    
    @pytest.mark.asyncio
    async def test_get_merchant_stats_unauthorized(
        self,
        async_client: AsyncClient,
        buyer_auth_headers
    ):
        """Test getting stats as non-merchant."""
        response = await async_client.get(
            "/api/v1/merchants/my/stats",
            headers=buyer_auth_headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ============ MERCHANT CATEGORY TESTS ============

class TestMerchantCategories:
    """Tests for merchant category handling."""
    
    @pytest.mark.asyncio
    async def test_get_merchants_by_category_grocery(
        self,
        async_client: AsyncClient,
        test_store
    ):
        """Test filtering by grocery category."""
        response = await async_client.get("/api/v1/merchants/?category=grocery")
        
        assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.asyncio
    async def test_get_merchants_by_category_pharmacy(
        self,
        async_client: AsyncClient
    ):
        """Test filtering by pharmacy category."""
        response = await async_client.get("/api/v1/merchants/?category=pharmacy")
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_merchant_categories_enum(self):
        """Test merchant category enum values."""
        from app.routes.merchants import MerchantCategory
        
        categories = list(MerchantCategory)
        
        assert MerchantCategory.GROCERY in categories
        assert MerchantCategory.RESTAURANT in categories
        assert MerchantCategory.PHARMACY in categories
        assert MerchantCategory.RETAIL in categories
        assert MerchantCategory.CONVENIENCE in categories
        assert MerchantCategory.STATIONERY in categories
        assert MerchantCategory.HARDWARE in categories
        assert MerchantCategory.OTHER in categories
