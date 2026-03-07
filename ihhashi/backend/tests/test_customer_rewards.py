"""
Tests for customer rewards system.

Covers:
- Rewards dashboard
- Coin transactions
- Tier system
- Redemptions
- Referral link
"""
import pytest
from datetime import datetime
from bson import ObjectId
from httpx import AsyncClient
from fastapi import status


# ============ REWARDS DASHBOARD TESTS ============

class TestRewardsDashboard:
    """Tests for rewards dashboard endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_rewards_dashboard(
        self,
        async_client: AsyncClient,
        test_customer,
        customer_auth_headers
    ):
        """Test getting full rewards dashboard."""
        response = await async_client.get(
            "/api/v1/customer-rewards/dashboard",
            headers=customer_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "tier" in data
        assert "tier_name" in data
        assert "tier_icon" in data
        assert "tier_color" in data
        assert "hashi_coins_balance" in data
        assert "total_referrals" in data
        assert "referral_code" in data
        assert "free_delivery_credits" in data
        assert "tier_progress" in data
        assert "tier_benefits" in data
        assert "referral_history" in data
        assert "coin_history" in data
    
    @pytest.mark.asyncio
    async def test_get_referral_link(
        self,
        async_client: AsyncClient,
        test_customer,
        customer_auth_headers
    ):
        """Test getting referral link."""
        response = await async_client.get(
            "/api/v1/customer-rewards/referral-link",
            headers=customer_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "referral_code" in data
        assert "share_link" in data
        assert "message" in data
        assert "coins_for_referrer" in data
        assert "coins_for_friend" in data
        assert data["coins_for_referrer"] == 50  # REFERRAL_BONUS_REFERRER
        assert data["coins_for_friend"] == 25    # REFERRAL_BONUS_REFEREE
    
    @pytest.mark.asyncio
    async def test_get_tier_info(
        self,
        async_client: AsyncClient
    ):
        """Test getting tier information."""
        response = await async_client.get("/api/v1/customer-rewards/tiers")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "tiers" in data
        assert len(data["tiers"]) == 4  # Bronze, Silver, Gold, Platinum
        assert "how_to_level_up" in data
        assert "referral_reward" in data
        
        # Check each tier has required fields
        for tier in data["tiers"]:
            assert "tier" in tier
            assert "name" in tier
            assert "discount_percent" in tier
            assert "free_deliveries_per_month" in tier
            assert "support_level" in tier
            assert "icon" in tier
            assert "color" in tier
    
    @pytest.mark.asyncio
    async def test_dashboard_unauthenticated(
        self,
        async_client: AsyncClient
    ):
        """Test getting dashboard without auth fails."""
        response = await async_client.get("/api/v1/customer-rewards/dashboard")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============ COIN REDEMPTION TESTS ============

class TestCoinRedemption:
    """Tests for coin redemption endpoints."""
    
    @pytest.mark.asyncio
    async def test_redeem_free_delivery(
        self,
        async_client: AsyncClient,
        test_customer,
        customer_auth_headers
    ):
        """Test redeeming coins for free delivery."""
        response = await async_client.post(
            "/api/v1/customer-rewards/redeem/free-delivery",
            headers=customer_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "success" in data
        assert "message" in data
        assert "coins_spent" in data
        assert "new_balance" in data
        assert "reward_type" in data
        assert "reward_value" in data
    
    @pytest.mark.asyncio
    async def test_redeem_discount_15(
        self,
        async_client: AsyncClient,
        test_customer,
        customer_auth_headers
    ):
        """Test redeeming coins for R15 discount."""
        response = await async_client.post(
            "/api/v1/customer-rewards/redeem/discount/15",
            headers=customer_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "success" in data
        assert "message" in data
        assert data["reward_type"] == "discount_15"
    
    @pytest.mark.asyncio
    async def test_redeem_discount_30(
        self,
        async_client: AsyncClient,
        test_customer,
        customer_auth_headers
    ):
        """Test redeeming coins for R30 discount."""
        response = await async_client.post(
            "/api/v1/customer-rewards/redeem/discount/30",
            headers=customer_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "success" in data
        assert data["reward_type"] == "discount_30"
    
    @pytest.mark.asyncio
    async def test_redeem_invalid_discount(
        self,
        async_client: AsyncClient,
        test_customer,
        customer_auth_headers
    ):
        """Test redeeming with invalid discount amount."""
        response = await async_client.post(
            "/api/v1/customer-rewards/redeem/discount/100",
            headers=customer_auth_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "discount" in response.json()["detail"].lower()


# ============ HISTORY TESTS ============

class TestRewardsHistory:
    """Tests for rewards history endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_coin_history(
        self,
        async_client: AsyncClient,
        test_customer,
        customer_auth_headers
    ):
        """Test getting coin transaction history."""
        response = await async_client.get(
            "/api/v1/customer-rewards/coin-history",
            headers=customer_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "transactions" in data
        assert "total_earned" in data
        assert "total_spent" in data
        assert "current_balance" in data
    
    @pytest.mark.asyncio
    async def test_get_coin_history_with_limit(
        self,
        async_client: AsyncClient,
        test_customer,
        customer_auth_headers
    ):
        """Test getting coin history with limit."""
        response = await async_client.get(
            "/api/v1/customer-rewards/coin-history?limit=5",
            headers=customer_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.asyncio
    async def test_get_referral_history(
        self,
        async_client: AsyncClient,
        test_customer,
        customer_auth_headers
    ):
        """Test getting referral history."""
        response = await async_client.get(
            "/api/v1/customer-rewards/referral-history",
            headers=customer_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "referrals" in data
        assert "total_referrals" in data
        assert "completed_referrals" in data
        assert "pending_referrals" in data
        assert "coins_earned_from_referrals" in data


# ============ PROMOTIONS TESTS ============

class TestPromotions:
    """Tests for promotions endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_active_promotions(
        self,
        async_client: AsyncClient
    ):
        """Test getting active promotions."""
        response = await async_client.get("/api/v1/customer-rewards/promotions")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "promotions" in data
        assert isinstance(data["promotions"], list)
        
        # Check promotion structure
        for promo in data["promotions"]:
            assert "id" in promo
            assert "title" in promo
            assert "description" in promo
            assert "is_active" in promo


# ============ APPLY REFERRAL CODE TESTS ============

class TestApplyReferralCode:
    """Tests for applying referral codes."""
    
    @pytest.mark.asyncio
    async def test_apply_referral_code(
        self,
        async_client: AsyncClient,
        test_customer,
        customer_auth_headers
    ):
        """Test applying a referral code."""
        response = await async_client.post(
            "/api/v1/customer-rewards/apply-referral?referral_code=IH-C-FRIEND1",
            headers=customer_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "message" in data
        assert "coins_received" in data
        assert data["referral_code"] == "IH-C-FRIEND1"
    
    @pytest.mark.asyncio
    async def test_apply_invalid_vendor_code(
        self,
        async_client: AsyncClient,
        test_customer,
        customer_auth_headers
    ):
        """Test applying vendor code as customer."""
        response = await async_client.post(
            "/api/v1/customer-rewards/apply-referral?referral_code=IH-V-VENDOR1",
            headers=customer_auth_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============ CUSTOMER TIER MODEL TESTS ============

class TestCustomerTierModel:
    """Tests for customer tier logic."""
    
    def test_tier_benefits_bronze(self):
        """Test bronze tier benefits."""
        from app.models.customer_rewards import CustomerRewardAccount, CustomerTier
        
        benefits = CustomerRewardAccount.get_tier_benefits(CustomerTier.BRONZE)
        
        assert benefits["name"] == "Bronze"
        assert benefits["discount_percent"] == 5
        assert benefits["free_deliveries_per_month"] == 0
        assert benefits["icon"] == "🥉"
    
    def test_tier_benefits_silver(self):
        """Test silver tier benefits."""
        from app.models.customer_rewards import CustomerRewardAccount, CustomerTier
        
        benefits = CustomerRewardAccount.get_tier_benefits(CustomerTier.SILVER)
        
        assert benefits["name"] == "Silver"
        assert benefits["discount_percent"] == 10
        assert benefits["free_deliveries_per_month"] == 1
        assert benefits["icon"] == "🥈"
    
    def test_tier_benefits_gold(self):
        """Test gold tier benefits."""
        from app.models.customer_rewards import CustomerRewardAccount, CustomerTier
        
        benefits = CustomerRewardAccount.get_tier_benefits(CustomerTier.GOLD)
        
        assert benefits["name"] == "Gold"
        assert benefits["discount_percent"] == 15
        assert benefits["free_deliveries_per_month"] == 2
        assert benefits["early_access"] is True
        assert benefits["icon"] == "🥇"
    
    def test_tier_benefits_platinum(self):
        """Test platinum tier benefits."""
        from app.models.customer_rewards import CustomerRewardAccount, CustomerTier
        
        benefits = CustomerRewardAccount.get_tier_benefits(CustomerTier.PLATINUM)
        
        assert benefits["name"] == "Platinum"
        assert benefits["discount_percent"] == 20
        assert benefits["free_deliveries_per_month"] == -1  # Unlimited
        assert benefits["icon"] == "💎"
    
    def test_tier_upgrade_logic(self):
        """Test tier upgrade logic."""
        from app.models.customer_rewards import CustomerRewardAccount, CustomerTier
        
        # Create a mock account
        account = CustomerRewardAccount(
            customer_id="test123",
            referral_code="IH-C-TEST",
            completed_referrals=0
        )
        
        # Test upgrade to bronze (1 referral)
        account.completed_referrals = 1
        changed = account.update_tier()
        assert account.tier == CustomerTier.BRONZE
        assert changed is True
        
        # Test upgrade to silver (6 referrals)
        account.completed_referrals = 6
        changed = account.update_tier()
        assert account.tier == CustomerTier.SILVER
        
        # Test upgrade to gold (16 referrals)
        account.completed_referrals = 16
        changed = account.update_tier()
        assert account.tier == CustomerTier.GOLD
        
        # Test upgrade to platinum (51 referrals)
        account.completed_referrals = 51
        changed = account.update_tier()
        assert account.tier == CustomerTier.PLATINUM


# ============ COIN TRANSACTION MODEL TESTS ============

class TestCoinTransactions:
    """Tests for coin transaction logic."""
    
    def test_add_coins(self):
        """Test adding coins to account."""
        from app.models.customer_rewards import CustomerRewardAccount
        
        account = CustomerRewardAccount(
            customer_id="test123",
            referral_code="IH-C-TEST"
        )
        
        transaction = account.add_coins(50, "Referral bonus")
        
        assert account.hashi_coins_balance == 50
        assert account.total_coins_earned == 50
        assert transaction.amount == 50
        assert transaction.balance_after == 50
        assert transaction.description == "Referral bonus"
    
    def test_spend_coins_success(self):
        """Test spending coins with sufficient balance."""
        from app.models.customer_rewards import CustomerRewardAccount
        
        account = CustomerRewardAccount(
            customer_id="test123",
            referral_code="IH-C-TEST",
            hashi_coins_balance=100
        )
        
        transaction = account.spend_coins(50, "Free delivery redemption")
        
        assert transaction is not None
        assert account.hashi_coins_balance == 50
        assert account.total_coins_spent == 50
        assert transaction.amount == -50
        assert transaction.balance_after == 50
    
    def test_spend_coins_insufficient_balance(self):
        """Test spending coins with insufficient balance."""
        from app.models.customer_rewards import CustomerRewardAccount
        
        account = CustomerRewardAccount(
            customer_id="test123",
            referral_code="IH-C-TEST",
            hashi_coins_balance=30
        )
        
        transaction = account.spend_coins(50, "Free delivery redemption")
        
        assert transaction is None
        assert account.hashi_coins_balance == 30  # Unchanged


# ============ COIN VALUES TESTS ============

class TestCoinValues:
    """Tests for coin value constants."""
    
    def test_coin_value_zar(self):
        """Test coin to ZAR conversion rate."""
        from app.models.customer_rewards import CoinValues
        
        assert CoinValues.COIN_VALUE_ZAR == 0.10  # 10 cents per coin
    
    def test_referral_bonuses(self):
        """Test referral bonus amounts."""
        from app.models.customer_rewards import CoinValues
        
        assert CoinValues.REFERRAL_BONUS_REFERRER == 50
        assert CoinValues.REFERRAL_BONUS_REFEREE == 25
        assert CoinValues.FIRST_ORDER_BONUS == 20
    
    def test_redemption_costs(self):
        """Test coin redemption costs."""
        from app.models.customer_rewards import CoinValues
        
        assert CoinValues.FREE_DELIVERY_COST == 100
        assert CoinValues.DISCOUNT_15_COST == 150
        assert CoinValues.DISCOUNT_30_COST == 300
    
    def test_tier_thresholds(self):
        """Test tier threshold constants."""
        from app.models.customer_rewards import CoinValues
        
        assert CoinValues.BRONZE_MIN == 1
        assert CoinValues.SILVER_MIN == 6
        assert CoinValues.GOLD_MIN == 16
        assert CoinValues.PLATINUM_MIN == 51
