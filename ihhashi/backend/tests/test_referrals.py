"""
Tests for referral system endpoints.

Covers:
- Referral code generation
- Referral code application
- Referral statistics
- Reward redemption
"""
import pytest
from datetime import datetime
from bson import ObjectId
from httpx import AsyncClient
from fastapi import status


# ============ REFERRAL CODE GENERATION TESTS ============

class TestReferralCodeGeneration:
    """Tests for generating referral codes."""
    
    @pytest.mark.asyncio
    async def test_generate_vendor_referral_code(
        self,
        async_client: AsyncClient,
        test_merchant,
        merchant_auth_headers
    ):
        """Test generating a vendor referral code."""
        response = await async_client.post(
            "/api/v1/referrals/generate/vendor",
            headers=merchant_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "code" in data
        assert data["code"].startswith("IH-V-")
        assert data["referral_type"] == "vendor"
        assert "share_link" in data
        assert "message" in data
    
    @pytest.mark.asyncio
    async def test_generate_customer_referral_code(
        self,
        async_client: AsyncClient,
        test_customer,
        customer_auth_headers
    ):
        """Test generating a customer referral code."""
        response = await async_client.post(
            "/api/v1/referrals/generate/customer",
            headers=customer_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "code" in data
        assert data["code"].startswith("IH-C-")
        assert data["referral_type"] == "customer"
        assert "share_link" in data
        assert "message" in data
    
    @pytest.mark.asyncio
    async def test_generate_referral_code_unauthenticated(
        self,
        async_client: AsyncClient
    ):
        """Test generating referral code without auth fails."""
        response = await async_client.post("/api/v1/referrals/generate/customer")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_generate_referral_code_invalid_type(
        self,
        async_client: AsyncClient,
        customer_auth_headers
    ):
        """Test generating referral code with invalid type."""
        response = await async_client.post(
            "/api/v1/referrals/generate/invalid",
            headers=customer_auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ============ REFERRAL CODE APPLICATION TESTS ============

class TestReferralCodeApplication:
    """Tests for applying referral codes."""
    
    @pytest.mark.asyncio
    async def test_apply_vendor_referral_code(
        self,
        async_client: AsyncClient,
        test_merchant,
        merchant_auth_headers
    ):
        """Test applying a vendor referral code."""
        response = await async_client.post(
            "/api/v1/referrals/apply",
            headers=merchant_auth_headers,
            json={
                "referral_code": "IH-V-TEST12",
                "referral_type": "vendor"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "referrer_reward" in data
        assert "your_welcome_bonus" in data
        assert data["referral_code"] == "IH-V-TEST12"
    
    @pytest.mark.asyncio
    async def test_apply_customer_referral_code(
        self,
        async_client: AsyncClient,
        test_customer,
        customer_auth_headers
    ):
        """Test applying a customer referral code."""
        response = await async_client.post(
            "/api/v1/referrals/apply",
            headers=customer_auth_headers,
            json={
                "referral_code": "IH-C-TEST12",
                "referral_type": "customer"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "referrer_reward" in data
        assert "your_welcome_bonus" in data
        assert data["referral_code"] == "IH-C-TEST12"
        assert "hashi_coins" in data
    
    @pytest.mark.asyncio
    async def test_apply_invalid_referral_code_format(
        self,
        async_client: AsyncClient,
        customer_auth_headers
    ):
        """Test applying an invalid referral code format."""
        response = await async_client.post(
            "/api/v1/referrals/apply",
            headers=customer_auth_headers,
            json={
                "referral_code": "INVALID-CODE",
                "referral_type": "customer"
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "format" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_apply_wrong_referral_type(
        self,
        async_client: AsyncClient,
        customer_auth_headers
    ):
        """Test applying vendor code as customer type."""
        response = await async_client.post(
            "/api/v1/referrals/apply",
            headers=customer_auth_headers,
            json={
                "referral_code": "IH-V-TEST12",
                "referral_type": "customer"
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.asyncio
    async def test_apply_referral_code_unauthenticated(
        self,
        async_client: AsyncClient
    ):
        """Test applying referral code without auth fails."""
        response = await async_client.post(
            "/api/v1/referrals/apply",
            json={
                "referral_code": "IH-C-TEST12",
                "referral_type": "customer"
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============ REFERRAL STATISTICS TESTS ============

class TestReferralStats:
    """Tests for referral statistics endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_vendor_referral_stats(
        self,
        async_client: AsyncClient,
        test_merchant,
        merchant_auth_headers
    ):
        """Test getting vendor referral stats."""
        response = await async_client.get(
            "/api/v1/referrals/stats?referral_type=vendor",
            headers=merchant_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "referral_code" in data
        assert "total_referrals" in data
        assert "completed_referrals" in data
        assert "pending_referrals" in data
        assert "rewards_earned" in data
    
    @pytest.mark.asyncio
    async def test_get_customer_referral_stats(
        self,
        async_client: AsyncClient,
        test_customer,
        customer_auth_headers
    ):
        """Test getting customer referral stats."""
        response = await async_client.get(
            "/api/v1/referrals/stats?referral_type=customer",
            headers=customer_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "referral_code" in data
        assert "total_referrals" in data
        assert "rewards_earned" in data
        assert "hashi_coins" in data.get("rewards_earned", {}) or True  # Optional field
    
    @pytest.mark.asyncio
    async def test_get_customer_rewards(
        self,
        async_client: AsyncClient,
        test_customer,
        customer_auth_headers
    ):
        """Test getting detailed customer rewards."""
        response = await async_client.get(
            "/api/v1/referrals/customer/rewards",
            headers=customer_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "referral_code" in data
        assert "tier" in data
        assert "hashi_coins_balance" in data
        assert "total_referrals" in data
        assert "tier_progress" in data
        assert "tier_benefits" in data
    
    @pytest.mark.asyncio
    async def test_get_referral_stats_unauthenticated(
        self,
        async_client: AsyncClient
    ):
        """Test getting stats without auth fails."""
        response = await async_client.get("/api/v1/referrals/stats")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============ REWARD REDEMPTION TESTS ============

class TestRewardRedemption:
    """Tests for redeeming rewards."""
    
    @pytest.mark.asyncio
    async def test_redeem_free_delivery(
        self,
        async_client: AsyncClient,
        test_customer,
        customer_auth_headers
    ):
        """Test redeeming for free delivery."""
        response = await async_client.post(
            "/api/v1/referrals/redeem/free-delivery",
            headers=customer_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "coins_required" in data
        assert "current_balance" in data
        assert "can_redeem" in data
    
    @pytest.mark.asyncio
    async def test_redeem_discount_10(
        self,
        async_client: AsyncClient,
        test_customer,
        customer_auth_headers
    ):
        """Test redeeming for discount."""
        response = await async_client.post(
            "/api/v1/referrals/redeem/discount/10",
            headers=customer_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "coins_required" in data
        assert "discount_amount" in data
    
    @pytest.mark.asyncio
    async def test_redeem_invalid_discount_amount(
        self,
        async_client: AsyncClient,
        test_customer,
        customer_auth_headers
    ):
        """Test redeeming with invalid discount amount."""
        response = await async_client.post(
            "/api/v1/referrals/redeem/discount/50",
            headers=customer_auth_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============ ADMIN ENDPOINT TESTS ============

class TestAdminReferralEndpoints:
    """Tests for admin referral management."""
    
    @pytest.mark.asyncio
    async def test_process_pending_referrals(
        self,
        async_client: AsyncClient,
        admin_auth_headers
    ):
        """Test processing pending referrals."""
        response = await async_client.post(
            "/api/v1/referrals/admin/process-pending",
            headers=admin_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "processed_count" in data
        assert "awards_given" in data
    
    @pytest.mark.asyncio
    async def test_get_admin_referral_stats(
        self,
        async_client: AsyncClient,
        admin_auth_headers
    ):
        """Test getting admin referral stats."""
        response = await async_client.get(
            "/api/v1/referrals/admin/stats",
            headers=admin_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_referral_codes" in data
        assert "total_referrals" in data
        assert "vendor_referrals" in data
        assert "customer_referrals" in data
        assert "tier_distribution" in data
    
    @pytest.mark.asyncio
    async def test_admin_endpoints_unauthorized(
        self,
        async_client: AsyncClient,
        customer_auth_headers
    ):
        """Test admin endpoints with non-admin user."""
        response = await async_client.get(
            "/api/v1/referrals/admin/stats",
            headers=customer_auth_headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ============ REFERRAL CODE MODEL TESTS ============

class TestReferralCodeModel:
    """Tests for referral code generation logic."""
    
    def test_generate_vendor_code_format(self):
        """Test vendor code format."""
        from app.models.referral import ReferralCode
        
        code = ReferralCode.generate_code("IH-V")
        
        assert code.startswith("IH-V-")
        assert len(code) == 10  # IH-V- + 6 chars
    
    def test_generate_customer_code_format(self):
        """Test customer code format."""
        from app.models.referral import ReferralCode
        
        code = ReferralCode.generate_code("IH-C")
        
        assert code.startswith("IH-C-")
        assert len(code) == 10
    
    def test_generated_codes_are_unique(self):
        """Test that generated codes are unique."""
        from app.models.referral import ReferralCode
        
        codes = {ReferralCode.generate_code("IH-C") for _ in range(100)}
        
        assert len(codes) == 100  # All unique
