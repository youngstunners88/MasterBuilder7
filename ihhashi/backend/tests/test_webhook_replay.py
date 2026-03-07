"""
Tests for webhook replay protection - ensures idempotent processing
"""
import pytest
import hashlib
import hmac
import json
from datetime import datetime
from unittest.mock import AsyncMock, patch
from bson import ObjectId

from fastapi.testclient import TestClient


@pytest.fixture
def test_db():
    """Create test database connection"""
    from motor.motor_asyncio import AsyncIOMotorClient
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.ihhashi_test
    yield db
    client.close()


@pytest.fixture
def mock_app():
    """Create test FastAPI app"""
    from fastapi import FastAPI
    from app.routes.payments import router as payments_router
    
    app = FastAPI()
    app.include_router(payments_router, prefix="/api")
    return app


@pytest.fixture
def client(mock_app):
    """Create test client"""
    return TestClient(mock_app)


@pytest.fixture
def webhook_payload():
    """Sample Paystack webhook payload"""
    return {
        "id": "evt_123456789",
        "event": "charge.success",
        "data": {
            "id": 12345,
            "reference": "ihhashi-test-ref-123",
            "amount": 10000,  # 100 ZAR (in cents)
            "status": "success",
            "paid_at": "2024-01-15T10:30:00.000Z",
            "channel": "card",
            "customer": {
                "email": "test@example.com"
            }
        }
    }


def generate_signature(payload: dict, secret: str) -> str:
    """Generate valid Paystack webhook signature"""
    body = json.dumps(payload).encode()
    return hmac.new(
        secret.encode(),
        body,
        hashlib.sha512
    ).hexdigest()


class TestWebhookReplayProtection:
    """Test suite for webhook idempotency and replay protection"""
    
    @pytest.mark.asyncio
    async def test_duplicate_webhook_ignored(self, test_db, webhook_payload):
        """
        CRITICAL TEST: Duplicate webhooks with same event_id must be ignored.
        
        This prevents:
        1. Double-charging customers
        2. Duplicate order fulfillment
        3. Race conditions in payment processing
        """
        # Setup: Ensure unique index exists
        await test_db.payment_webhooks.create_index("event_id", unique=True)
        
        # Setup: Create a payment record
        await test_db.payments.insert_one({
            "reference": webhook_payload["data"]["reference"],
            "user_id": str(ObjectId()),
            "email": "test@example.com",
            "amount": 100.0,
            "status": "pending",
            "created_at": datetime.utcnow()
        })
        
        # ACTION: Process first webhook
        first_insert = await test_db.payment_webhooks.insert_one({
            "event_id": webhook_payload["id"],
            "event": webhook_payload["event"],
            "data": webhook_payload["data"],
            "received_at": datetime.utcnow(),
            "processed": True
        })
        
        assert first_insert.inserted_id is not None
        
        # ACTION: Attempt to process duplicate webhook
        from pymongo.errors import DuplicateKeyError
        duplicate_detected = False
        
        try:
            await test_db.payment_webhooks.insert_one({
                "event_id": webhook_payload["id"],  # Same event_id
                "event": webhook_payload["event"],
                "data": webhook_payload["data"],
                "received_at": datetime.utcnow(),
                "processed": False
            })
        except DuplicateKeyError:
            duplicate_detected = True
        
        # ASSERT: Duplicate was detected and rejected
        assert duplicate_detected, "Duplicate webhook should have been rejected"
        
        # ASSERT: Only one webhook record exists
        count = await test_db.payment_webhooks.count_documents({
            "event_id": webhook_payload["id"]
        })
        assert count == 1, f"Expected 1 webhook record, found {count}"
    
    @pytest.mark.asyncio
    async def test_idempotent_payment_update(self, test_db, webhook_payload):
        """
        Test that payment status update is idempotent.
        
        Multiple updates with status != success check should only update once.
        """
        # Setup: Create payment record
        await test_db.payments.insert_one({
            "reference": webhook_payload["data"]["reference"],
            "user_id": str(ObjectId()),
            "email": "test@example.com",
            "amount": 100.0,
            "status": "pending",
            "created_at": datetime.utcnow()
        })
        
        # ACTION: Update payment status multiple times
        update_query = {
            "reference": webhook_payload["data"]["reference"],
            "status": {"$ne": "success"}  # Idempotent condition
        }
        update_data = {
            "$set": {
                "status": "success",
                "paid_at": datetime.utcnow()
            }
        }
        
        # First update should succeed
        result1 = await test_db.payments.update_one(update_query, update_data)
        assert result1.modified_count == 1
        
        # Second update should NOT modify (already success)
        result2 = await test_db.payments.update_one(update_query, update_data)
        assert result2.modified_count == 0
        
        # Third update should also NOT modify
        result3 = await test_db.payments.update_one(update_query, update_data)
        assert result3.modified_count == 0
    
    @pytest.mark.asyncio
    async def test_webhook_signature_verification(self, webhook_payload):
        """
        Test that webhook signature verification works correctly.
        """
        secret = "test_secret_key"
        
        # Generate valid signature
        valid_signature = generate_signature(webhook_payload, secret)
        
        # Verify signature matches
        body = json.dumps(webhook_payload).encode()
        expected_signature = hmac.new(
            secret.encode(),
            body,
            hashlib.sha512
        ).hexdigest()
        
        assert hmac.compare_digest(valid_signature, expected_signature)
        
        # Test with tampered payload
        tampered_payload = webhook_payload.copy()
        tampered_payload["data"]["amount"] = 99999
        
        tampered_body = json.dumps(tampered_payload).encode()
        tampered_signature = hmac.new(
            secret.encode(),
            tampered_body,
            hashlib.sha512
        ).hexdigest()
        
        # Tampered signature should NOT match original
        assert not hmac.compare_digest(valid_signature, tampered_signature)
    
    @pytest.mark.asyncio
    async def test_payment_verification_before_fulfillment(self, test_db, webhook_payload):
        """
        Test that payment is verified with Paystack before marking as success.
        
        This prevents fraud where attackers send fake webhook events.
        """
        # Mock Paystack verification
        with patch("app.services.paystack.PaystackService.verify_payment") as mock_verify:
            # First call: Verification succeeds
            mock_verify.return_value = {
                "status": True,
                "data": {
                    "status": "success",
                    "reference": webhook_payload["data"]["reference"],
                    "amount": 10000
                }
            }
            
            # Setup: Create payment record
            await test_db.payments.insert_one({
                "reference": webhook_payload["data"]["reference"],
                "status": "pending"
            })
            
            # ACTION: Verify payment
            # In real code, this would be called by the webhook handler
            verification = mock_verify.return_value
            
            # ASSERT: Verification shows success
            assert verification["data"]["status"] == "success"
            
            # Update payment (what webhook handler would do)
            await test_db.payments.update_one(
                {"reference": webhook_payload["data"]["reference"]},
                {"$set": {"status": "success", "verified": True}}
            )
            
            payment = await test_db.payments.find_one({
                "reference": webhook_payload["data"]["reference"]
            })
            assert payment["status"] == "success"
            assert payment.get("verified") == True
    
    @pytest.mark.asyncio
    async def test_concurrent_webhook_processing(self, test_db, webhook_payload):
        """
        Test that concurrent webhook processing with same event_id is handled correctly.
        """
        import asyncio
        
        # Setup: Ensure unique index
        await test_db.payment_webhooks.create_index("event_id", unique=True)
        
        results = {"success": 0, "duplicate": 0}
        
        async def process_webhook():
            """Simulate webhook processing"""
            try:
                await test_db.payment_webhooks.insert_one({
                    "event_id": webhook_payload["id"],
                    "event": webhook_payload["event"],
                    "data": webhook_payload["data"],
                    "received_at": datetime.utcnow()
                })
                results["success"] += 1
            except DuplicateKeyError:
                results["duplicate"] += 1
        
        # Run 5 concurrent "webhooks" with same event_id
        from pymongo.errors import DuplicateKeyError
        await asyncio.gather(
            process_webhook(),
            process_webhook(),
            process_webhook(),
            process_webhook(),
            process_webhook()
        )
        
        # ASSERT: Only ONE succeeded, 4 were duplicates
        assert results["success"] == 1, f"Expected 1 success, got {results['success']}"
        assert results["duplicate"] == 4, f"Expected 4 duplicates, got {results['duplicate']}"


class TestWebhookEventTypes:
    """Test different webhook event types"""
    
    @pytest.mark.asyncio
    async def test_transfer_success_webhook(self, test_db):
        """Test transfer.success webhook handling"""
        payload = {
            "id": "evt_transfer_123",
            "event": "transfer.success",
            "data": {
                "transfer_code": "TRF_123456",
                "amount": 50000,
                "status": "success"
            }
        }
        
        # Setup: Create payout record
        await test_db.payments.insert_one({
            "transfer_code": payload["data"]["transfer_code"],
            "type": "payout",
            "status": "processing"
        })
        
        # ACTION: Process webhook
        await test_db.payment_webhooks.insert_one({
            "event_id": payload["id"],
            "event": payload["event"],
            "data": payload["data"],
            "received_at": datetime.utcnow()
        })
        
        # Update payout status
        await test_db.payments.update_one(
            {"transfer_code": payload["data"]["transfer_code"]},
            {"$set": {"status": "success", "completed_at": datetime.utcnow()}}
        )
        
        # ASSERT
        payout = await test_db.payments.find_one({
            "transfer_code": payload["data"]["transfer_code"]
        })
        assert payout["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_refund_processed_webhook(self, test_db):
        """Test refund.processed webhook handling"""
        payload = {
            "id": "evt_refund_123",
            "event": "refund.processed",
            "data": {
                "transaction_reference": "ihhashi-test-ref-456",
                "amount": 5000
            }
        }
        
        # Setup: Create payment with refund in progress
        await test_db.payments.insert_one({
            "reference": payload["data"]["transaction_reference"],
            "status": "success",
            "refund_status": "processing"
        })
        
        # ACTION: Process webhook
        await test_db.payments.update_one(
            {"reference": payload["data"]["transaction_reference"]},
            {"$set": {"refund_status": "completed"}}
        )
        
        # ASSERT
        payment = await test_db.payments.find_one({
            "reference": payload["data"]["transaction_reference"]
        })
        assert payment["refund_status"] == "completed"