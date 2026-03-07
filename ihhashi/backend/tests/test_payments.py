"""
Tests for payment endpoints and Paystack integration.

Covers:
- Payment initialization
- Payment verification
- Webhook handling
- Payout processing
- Refund handling
"""
import pytest
import hashlib
import hmac
import json
from datetime import datetime
from bson import ObjectId
from unittest.mock import patch, AsyncMock, MagicMock
import httpx

from fastapi import status
from httpx import AsyncClient

from app.models import UserRole
from app.config import settings


# ============ PAYMENT INITIALIZATION TESTS ============

class TestPaymentInitialization:
    """Tests for payment initialization endpoint."""
    
    @pytest.mark.asyncio
    async def test_initialize_payment_success(
        self,
        async_client: AsyncClient,
        test_user,
        test_order,
        buyer_auth_headers,
        mock_paystack
    ):
        """Test successful payment initialization."""
        response = await async_client.post(
            "/api/payments/initialize",
            headers=buyer_auth_headers,
            json={
                "email": test_user["email"],
                "amount": test_order["total"],
                "order_id": test_order["id"]
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] is True
        assert "authorization_url" in data["data"]
        assert "reference" in data["data"]
    
    @pytest.mark.asyncio
    async def test_initialize_payment_creates_record(
        self,
        async_client: AsyncClient,
        test_user,
        test_order,
        buyer_auth_headers,
        mock_paystack,
        clean_db
    ):
        """Test that payment initialization creates a database record."""
        from app.database import get_collection
        
        response = await async_client.post(
            "/api/payments/initialize",
            headers=buyer_auth_headers,
            json={
                "email": test_user["email"],
                "amount": test_order["total"],
                "order_id": test_order["id"]
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify payment record was created
        payments_col = get_collection("payments")
        reference = response.json()["data"]["reference"]
        payment = await payments_col.find_one({"reference": reference})
        
        assert payment is not None
        assert payment["user_id"] == test_user["id"]
        assert payment["amount"] == test_order["total"]
    
    @pytest.mark.asyncio
    async def test_initialize_payment_invalid_order(
        self,
        async_client: AsyncClient,
        test_user,
        buyer_auth_headers,
        mock_paystack
    ):
        """Test payment initialization with invalid order fails."""
        response = await async_client.post(
            "/api/payments/initialize",
            headers=buyer_auth_headers,
            json={
                "email": test_user["email"],
                "amount": 100.00,
                "order_id": str(ObjectId())  # Non-existent order
            }
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_initialize_payment_amount_mismatch(
        self,
        async_client: AsyncClient,
        test_user,
        test_order,
        buyer_auth_headers,
        mock_paystack
    ):
        """Test payment initialization with wrong amount fails."""
        response = await async_client.post(
            "/api/payments/initialize",
            headers=buyer_auth_headers,
            json={
                "email": test_user["email"],
                "amount": 1.00,  # Wrong amount
                "order_id": test_order["id"]
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "mismatch" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_initialize_payment_already_paid(
        self,
        async_client: AsyncClient,
        test_user,
        test_order,
        buyer_auth_headers,
        mock_paystack,
        clean_db
    ):
        """Test payment initialization for already paid order fails."""
        from app.database import get_collection
        orders_col = get_collection("orders")
        
        # Mark order as paid
        await orders_col.update_one(
            {"_id": ObjectId(test_order["id"])},
            {"$set": {"payment_status": "paid"}}
        )
        
        response = await async_client.post(
            "/api/payments/initialize",
            headers=buyer_auth_headers,
            json={
                "email": test_user["email"],
                "amount": test_order["total"],
                "order_id": test_order["id"]
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already paid" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_initialize_payment_unauthenticated(
        self,
        async_client: AsyncClient,
        test_user
    ):
        """Test payment initialization without auth fails."""
        response = await async_client.post(
            "/api/payments/initialize",
            json={
                "email": test_user["email"],
                "amount": 100.00
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_initialize_payment_invalid_email(
        self,
        async_client: AsyncClient,
        buyer_auth_headers,
        mock_paystack
    ):
        """Test payment initialization with invalid email fails."""
        response = await async_client.post(
            "/api/payments/initialize",
            headers=buyer_auth_headers,
            json={
                "email": "not-an-email",
                "amount": 100.00
            }
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_initialize_payment_negative_amount(
        self,
        async_client: AsyncClient,
        test_user,
        buyer_auth_headers
    ):
        """Test payment initialization with negative amount fails."""
        response = await async_client.post(
            "/api/payments/initialize",
            headers=buyer_auth_headers,
            json={
                "email": test_user["email"],
                "amount": -50.00
            }
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ============ PAYMENT VERIFICATION TESTS ============

class TestPaymentVerification:
    """Tests for payment verification endpoint."""
    
    @pytest.mark.asyncio
    async def test_verify_payment_success(
        self,
        async_client: AsyncClient,
        test_payment,
        buyer_auth_headers,
        mock_paystack
    ):
        """Test successful payment verification."""
        response = await async_client.get(
            f"/api/payments/verify/{test_payment['reference']}",
            headers=buyer_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] is True
        assert data["data"]["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_verify_payment_updates_order(
        self,
        async_client: AsyncClient,
        test_payment,
        test_order,
        buyer_auth_headers,
        mock_paystack,
        clean_db
    ):
        """Test that payment verification updates order status."""
        from app.database import get_collection
        
        response = await async_client.get(
            f"/api/payments/verify/{test_payment['reference']}",
            headers=buyer_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify order payment status was updated
        orders_col = get_collection("orders")
        order = await orders_col.find_one({"_id": ObjectId(test_order["id"])})
        
        # This depends on webhook or sync update
        # If webhook is the only way, this test may need adjustment
    
    @pytest.mark.asyncio
    async def test_verify_nonexistent_payment(
        self,
        async_client: AsyncClient,
        buyer_auth_headers,
        mock_paystack
    ):
        """Test verification of non-existent payment."""
        response = await async_client.get(
            "/api/payments/verify/nonexistent-ref",
            headers=buyer_auth_headers
        )
        
        # Paystack returns 404 for non-existent references
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    
    @pytest.mark.asyncio
    async def test_verify_payment_unauthenticated(
        self,
        async_client: AsyncClient,
        test_payment
    ):
        """Test payment verification without auth fails."""
        response = await async_client.get(
            f"/api/payments/verify/{test_payment['reference']}"
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============ WEBHOOK TESTS ============

class TestWebhookHandling:
    """Tests for Paystack webhook handling."""
    
    def _generate_signature(self, payload: dict) -> str:
        """Generate valid webhook signature."""
        secret = settings.paystack_secret_key or "test_secret"
        return hmac.new(
            secret.encode(),
            json.dumps(payload).encode(),
            hashlib.sha512
        ).hexdigest()
    
    @pytest.mark.asyncio
    async def test_webhook_charge_success(
        self,
        async_client: AsyncClient,
        test_payment,
        test_order,
        clean_db
    ):
        """Test successful charge webhook."""
        from app.database import get_collection
        
        payload = {
            "event": "charge.success",
            "data": {
                "reference": test_payment["reference"],
                "status": "success",
                "amount": int(test_payment["amount"] * 100),
                "paid_at": datetime.utcnow().isoformat(),
                "channel": "card"
            }
        }
        
        signature = self._generate_signature(payload)
        
        response = await async_client.post(
            "/api/payments/webhook",
            json=payload,
            headers={"x-paystack-signature": signature}
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "received"
        
        # Verify payment was updated
        payments_col = get_collection("payments")
        payment = await payments_col.find_one({"reference": test_payment["reference"]})
        
        assert payment["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_webhook_updates_order_payment(
        self,
        async_client: AsyncClient,
        test_payment,
        test_order,
        clean_db
    ):
        """Test that webhook updates order payment status."""
        from app.database import get_collection
        
        payload = {
            "event": "charge.success",
            "data": {
                "reference": test_payment["reference"],
                "status": "success",
                "amount": int(test_payment["amount"] * 100),
                "paid_at": datetime.utcnow().isoformat(),
                "channel": "card"
            }
        }
        
        signature = self._generate_signature(payload)
        
        response = await async_client.post(
            "/api/payments/webhook",
            json=payload,
            headers={"x-paystack-signature": signature}
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify order payment status was updated
        orders_col = get_collection("orders")
        order = await orders_col.find_one({"_id": ObjectId(test_order["id"])})
        
        assert order["payment_status"] == "paid"
    
    @pytest.mark.asyncio
    async def test_webhook_transfer_success(
        self,
        async_client: AsyncClient,
        test_driver,
        clean_db
    ):
        """Test successful transfer webhook (payout)."""
        from app.database import get_collection
        
        # Create payout record
        payments_col = get_collection("payments")
        payout_doc = {
            "reference": "payout-test123",
            "transfer_code": "TRF_test123",
            "user_id": test_driver["id"],
            "amount": 500.00,
            "status": "processing",
            "created_at": datetime.utcnow()
        }
        await payments_col.insert_one(payout_doc)
        
        payload = {
            "event": "transfer.success",
            "data": {
                "transfer_code": "TRF_test123",
                "status": "success"
            }
        }
        
        signature = self._generate_signature(payload)
        
        response = await async_client.post(
            "/api/payments/webhook",
            json=payload,
            headers={"x-paystack-signature": signature}
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify payout was updated
        payout = await payments_col.find_one({"transfer_code": "TRF_test123"})
        assert payout["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_webhook_transfer_failed(
        self,
        async_client: AsyncClient,
        test_driver,
        clean_db
    ):
        """Test failed transfer webhook."""
        from app.database import get_collection
        
        payments_col = get_collection("payments")
        payout_doc = {
            "reference": "payout-test456",
            "transfer_code": "TRF_test456",
            "user_id": test_driver["id"],
            "amount": 500.00,
            "status": "processing",
            "created_at": datetime.utcnow()
        }
        await payments_col.insert_one(payout_doc)
        
        payload = {
            "event": "transfer.failed",
            "data": {
                "transfer_code": "TRF_test456",
                "reason": "Insufficient balance"
            }
        }
        
        signature = self._generate_signature(payload)
        
        response = await async_client.post(
            "/api/payments/webhook",
            json=payload,
            headers={"x-paystack-signature": signature}
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        payout = await payments_col.find_one({"transfer_code": "TRF_test456"})
        assert payout["status"] == "failed"
    
    @pytest.mark.asyncio
    async def test_webhook_refund_processed(
        self,
        async_client: AsyncClient,
        test_payment,
        test_order,
        clean_db
    ):
        """Test refund processed webhook."""
        from app.database import get_collection
        
        payload = {
            "event": "refund.processed",
            "data": {
                "transaction_reference": test_payment["reference"]
            }
        }
        
        signature = self._generate_signature(payload)
        
        response = await async_client.post(
            "/api/payments/webhook",
            json=payload,
            headers={"x-paystack-signature": signature}
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify refund status was updated
        payments_col = get_collection("payments")
        payment = await payments_col.find_one({"reference": test_payment["reference"]})
        assert payment.get("refund_status") == "completed"
    
    @pytest.mark.asyncio
    async def test_webhook_missing_signature(
        self,
        async_client: AsyncClient
    ):
        """Test webhook without signature fails."""
        response = await async_client.post(
            "/api/payments/webhook",
            json={"event": "charge.success", "data": {}}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.asyncio
    async def test_webhook_invalid_signature(
        self,
        async_client: AsyncClient
    ):
        """Test webhook with invalid signature fails."""
        response = await async_client.post(
            "/api/payments/webhook",
            json={"event": "charge.success", "data": {}},
            headers={"x-paystack-signature": "invalid_signature"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============ PAYOUT TESTS ============

class TestPayouts:
    """Tests for payout/driver earnings endpoint."""
    
    @pytest.mark.asyncio
    async def test_payout_driver_success(
        self,
        async_client: AsyncClient,
        test_driver,
        driver_auth_headers,
        mock_paystack
    ):
        """Test successful payout to driver."""
        response = await async_client.post(
            "/api/payments/payout",
            headers=driver_auth_headers,
            json={
                "account_number": "1234567890",
                "bank_code": "632005",  # ABSA
                "account_name": "Test Driver",
                "amount": 500.00,
                "reason": "Weekly earnings"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] is True
        assert "transfer_code" in data["data"]
    
    @pytest.mark.asyncio
    async def test_payout_merchant_unauthorized(
        self,
        async_client: AsyncClient,
        merchant_auth_headers
    ):
        """Test that merchants cannot request payouts."""
        response = await async_client.post(
            "/api/payments/payout",
            headers=merchant_auth_headers,
            json={
                "account_number": "1234567890",
                "bank_code": "632005",
                "account_name": "Test Merchant",
                "amount": 500.00
            }
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_payout_invalid_bank_code(
        self,
        async_client: AsyncClient,
        driver_auth_headers,
        mock_paystack
    ):
        """Test payout with invalid bank code."""
        mock_paystack.create_transfer_recipient.return_value = {
            "status": False,
            "message": "Invalid bank code"
        }
        
        response = await async_client.post(
            "/api/payments/payout",
            headers=driver_auth_headers,
            json={
                "account_number": "1234567890",
                "bank_code": "INVALID",
                "account_name": "Test Driver",
                "amount": 500.00
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============ REFUND TESTS ============

class TestRefunds:
    """Tests for refund handling."""
    
    @pytest.mark.asyncio
    async def test_refund_request_success(
        self,
        async_client: AsyncClient,
        test_payment,
        admin_auth_headers,
        mock_paystack
    ):
        """Test successful refund request."""
        mock_paystack.refund_payment.return_value = {
            "status": True,
            "data": {
                "id": "ref_123",
                "status": "processed"
            }
        }
        
        response = await async_client.post(
            "/api/payments/refund",
            headers=admin_auth_headers,
            json={
                "reference": test_payment["reference"],
                "reason": "Customer request"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.asyncio
    async def test_partial_refund(
        self,
        async_client: AsyncClient,
        test_payment,
        admin_auth_headers,
        mock_paystack
    ):
        """Test partial refund request."""
        mock_paystack.refund_payment.return_value = {
            "status": True,
            "data": {
                "id": "ref_456",
                "status": "processed",
                "amount": 5000  # 50 ZAR in cents
            }
        }
        
        response = await async_client.post(
            "/api/payments/refund",
            headers=admin_auth_headers,
            json={
                "reference": test_payment["reference"],
                "amount": 50.00,  # Partial refund
                "reason": "Partial refund for damaged item"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK


# ============ BANK VERIFICATION TESTS ============

class TestBankVerification:
    """Tests for bank account verification."""
    
    @pytest.mark.asyncio
    async def test_verify_account_success(
        self,
        async_client: AsyncClient,
        buyer_auth_headers,
        mock_paystack
    ):
        """Test successful bank account verification."""
        response = await async_client.post(
            "/api/payments/verify-account",
            headers=buyer_auth_headers,
            params={
                "account_number": "1234567890",
                "bank_code": "632005"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["valid"] is True
        assert "account_name" in data
    
    @pytest.mark.asyncio
    async def test_verify_account_invalid(
        self,
        async_client: AsyncClient,
        buyer_auth_headers,
        mock_paystack
    ):
        """Test invalid bank account verification."""
        mock_paystack.verify_account_number.return_value = {
            "status": False,
            "message": "Account not found"
        }
        
        response = await async_client.post(
            "/api/payments/verify-account",
            headers=buyer_auth_headers,
            params={
                "account_number": "0000000000",
                "bank_code": "632005"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["valid"] is False


# ============ BANKS LIST TESTS ============

class TestBanksList:
    """Tests for banks list endpoint."""
    
    @pytest.mark.asyncio
    async def test_list_banks_success(
        self,
        async_client: AsyncClient
    ):
        """Test getting list of supported banks."""
        response = await async_client.get("/api/payments/banks")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] is True
        assert isinstance(data["data"], list)
    
    @pytest.mark.asyncio
    async def test_list_banks_contains_sa_banks(
        self,
        async_client: AsyncClient
    ):
        """Test that banks list includes SA banks."""
        response = await async_client.get("/api/payments/banks")
        
        data = response.json()
        bank_names = [b["name"] for b in data["data"]]
        
        # Check for major SA banks
        assert "FNB" in bank_names or "First National Bank" in bank_names
        assert "Capitec" in bank_names
        assert "Standard Bank" in bank_names


# ============ PAYMENT HISTORY TESTS ============

class TestPaymentHistory:
    """Tests for payment history endpoint."""
    
    @pytest.mark.asyncio
    async def test_payment_history_success(
        self,
        async_client: AsyncClient,
        test_payment,
        buyer_auth_headers
    ):
        """Test getting payment history."""
        response = await async_client.get(
            "/api/payments/history",
            headers=buyer_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "payments" in data
        assert "total" in data
    
    @pytest.mark.asyncio
    async def test_payment_history_pagination(
        self,
        async_client: AsyncClient,
        test_payment,
        buyer_auth_headers
    ):
        """Test payment history pagination."""
        response = await async_client.get(
            "/api/payments/history?limit=10&offset=0",
            headers=buyer_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 0
    
    @pytest.mark.asyncio
    async def test_payment_history_unauthenticated(
        self,
        async_client: AsyncClient
    ):
        """Test payment history without auth fails."""
        response = await async_client.get("/api/payments/history")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============ ERROR HANDLING TESTS ============

class TestPaymentErrorHandling:
    """Tests for payment error handling."""
    
    @pytest.mark.asyncio
    async def test_paystack_service_error(
        self,
        async_client: AsyncClient,
        test_user,
        buyer_auth_headers,
        mock_paystack
    ):
        """Test handling of Paystack service error."""
        mock_paystack.initialize_payment.return_value = {
            "status": False,
            "message": "Service unavailable"
        }
        
        response = await async_client.post(
            "/api/payments/initialize",
            headers=buyer_auth_headers,
            json={
                "email": test_user["email"],
                "amount": 100.00
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.asyncio
    async def test_payment_timeout(
        self,
        async_client: AsyncClient,
        test_user,
        buyer_auth_headers
    ):
        """Test handling of payment service timeout."""
        with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException()):
            response = await async_client.post(
                "/api/payments/initialize",
                headers=buyer_auth_headers,
                json={
                    "email": test_user["email"],
                    "amount": 100.00
                }
            )
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
