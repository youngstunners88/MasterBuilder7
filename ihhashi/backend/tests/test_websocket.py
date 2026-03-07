"""
Tests for WebSocket connections.

Covers:
- WebSocket authentication
- Order tracking
- Rider location updates
- User notifications
- Connection management
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.routes.websocket import (
    ConnectionManager, validate_coordinates, validate_location_data,
    verify_websocket_token, manager
)


# ============ VALIDATION TESTS ============

class TestCoordinateValidation:
    """Tests for coordinate validation functions."""
    
    def test_valid_coordinates(self):
        """Test valid latitude and longitude."""
        assert validate_coordinates(-26.2041, 28.0473) is True
    
    def test_invalid_latitude_too_high(self):
        """Test latitude above maximum."""
        assert validate_coordinates(91.0, 28.0473) is False
    
    def test_invalid_latitude_too_low(self):
        """Test latitude below minimum."""
        assert validate_coordinates(-91.0, 28.0473) is False
    
    def test_invalid_longitude_too_high(self):
        """Test longitude above maximum."""
        assert validate_coordinates(-26.2041, 181.0) is False
    
    def test_invalid_longitude_too_low(self):
        """Test longitude below minimum."""
        assert validate_coordinates(-26.2041, -181.0) is False
    
    def test_null_coordinates(self):
        """Test null coordinates."""
        assert validate_coordinates(None, 28.0473) is False
        assert validate_coordinates(-26.2041, None) is False
    
    def test_invalid_type_coordinates(self):
        """Test non-numeric coordinates."""
        assert validate_coordinates("invalid", 28.0473) is False
        assert validate_coordinates(-26.2041, "invalid") is False


class TestLocationValidation:
    """Tests for location data validation."""
    
    def test_valid_location(self):
        """Test valid location data."""
        location = {
            "latitude": -26.2041,
            "longitude": 28.0473,
            "heading": 90.0,
            "speed": 30.5
        }
        
        result = validate_location_data(location)
        
        assert result is not None
        assert result["latitude"] == -26.2041
        assert result["longitude"] == 28.0473
        assert result["heading"] == 90.0
        assert result["speed"] == 30.5
        assert "last_updated" in result
    
    def test_location_without_optional_fields(self):
        """Test location without heading and speed."""
        location = {
            "latitude": -26.2041,
            "longitude": 28.0473
        }
        
        result = validate_location_data(location)
        
        assert result is not None
        assert result["latitude"] == -26.2041
        assert result["longitude"] == 28.0473
        assert result["heading"] is None
        assert result["speed"] is None
    
    def test_invalid_heading(self):
        """Test location with invalid heading."""
        location = {
            "latitude": -26.2041,
            "longitude": 28.0473,
            "heading": 400  # Invalid - should be 0-360
        }
        
        result = validate_location_data(location)
        
        assert result is not None
        assert result["heading"] is None  # Should be sanitized to None
    
    def test_invalid_speed(self):
        """Test location with invalid speed."""
        location = {
            "latitude": -26.2041,
            "longitude": 28.0473,
            "speed": 300  # Above MAX_SPEED
        }
        
        result = validate_location_data(location)
        
        assert result is not None
        assert result["speed"] is None  # Should be sanitized to None
    
    def test_negative_speed(self):
        """Test location with negative speed."""
        location = {
            "latitude": -26.2041,
            "longitude": 28.0473,
            "speed": -10
        }
        
        result = validate_location_data(location)
        
        assert result is not None
        assert result["speed"] is None  # Should be sanitized to None
    
    def test_empty_location(self):
        """Test empty location data."""
        assert validate_location_data({}) is None
        assert validate_location_data(None) is None


class TestWebSocketTokenVerification:
    """Tests for WebSocket token verification."""
    
    @pytest.mark.asyncio
    async def test_verify_valid_token(self, test_user):
        """Test verifying a valid token."""
        from app.services.auth import create_access_token
        
        token = create_access_token(
            data={"sub": test_user["id"], "role": test_user["role"]}
        )
        
        payload = await verify_websocket_token(token)
        
        assert payload is not None
        assert payload["sub"] == test_user["id"]
        assert payload["role"] == test_user["role"]
    
    @pytest.mark.asyncio
    async def test_verify_invalid_token(self):
        """Test verifying an invalid token."""
        payload = await verify_websocket_token("invalid_token")
        
        assert payload is None
    
    @pytest.mark.asyncio
    async def test_verify_expired_token(self, test_user):
        """Test verifying an expired token."""
        from datetime import timedelta
        from app.services.auth import create_access_token
        
        token = create_access_token(
            data={"sub": test_user["id"], "role": test_user["role"]},
            expires_delta=timedelta(seconds=-1)
        )
        
        payload = await verify_websocket_token(token)
        
        assert payload is None


# ============ CONNECTION MANAGER TESTS ============

class TestConnectionManager:
    """Tests for the WebSocket connection manager."""
    
    @pytest.fixture
    def connection_manager(self):
        """Create a fresh connection manager."""
        return ConnectionManager()
    
    @pytest.mark.asyncio
    async def test_connect_order_tracker(self, connection_manager):
        """Test connecting an order tracker."""
        mock_ws = AsyncMock()
        
        await connection_manager.connect_order_tracker(
            mock_ws, "order123", "user123", is_owner=True
        )
        
        assert "order123" in connection_manager.order_connections
        assert len(connection_manager.order_connections["order123"]) == 1
        assert connection_manager.order_connections["order123"][0][1] == "user123"
        mock_ws.accept.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_rider(self, connection_manager):
        """Test connecting a rider."""
        mock_ws = AsyncMock()
        
        await connection_manager.connect_rider(mock_ws, "rider123")
        
        assert "rider123" in connection_manager.rider_connections
        mock_ws.accept.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_user(self, connection_manager):
        """Test connecting a user."""
        mock_ws = AsyncMock()
        
        await connection_manager.connect_user(mock_ws, "user123")
        
        assert "user123" in connection_manager.user_connections
        mock_ws.accept.assert_called_once()
    
    def test_disconnect_order(self, connection_manager):
        """Test disconnecting from an order."""
        mock_ws = MagicMock()
        connection_manager.order_connections["order123"] = [
            (mock_ws, "user123", True)
        ]
        
        connection_manager.disconnect(mock_ws, order_id="order123")
        
        assert len(connection_manager.order_connections["order123"]) == 0
    
    def test_disconnect_rider(self, connection_manager):
        """Test disconnecting a rider."""
        mock_ws = MagicMock()
        connection_manager.rider_connections["rider123"] = mock_ws
        
        connection_manager.disconnect(mock_ws, rider_id="rider123")
        
        assert "rider123" not in connection_manager.rider_connections
    
    @pytest.mark.asyncio
    async def test_broadcast_order_update(self, connection_manager):
        """Test broadcasting to order trackers."""
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        
        connection_manager.order_connections["order123"] = [
            (mock_ws1, "user1", True),
            (mock_ws2, "user2", False)
        ]
        
        message = {"type": "status_update", "status": "delivered"}
        await connection_manager.broadcast_order_update("order123", message)
        
        mock_ws1.send_json.assert_called_once()
        mock_ws2.send_json.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_broadcast_order_update_with_sensitive_data(self, connection_manager):
        """Test that sensitive data is filtered for non-owners."""
        mock_ws_owner = AsyncMock()
        mock_ws_non_owner = AsyncMock()
        
        connection_manager.order_connections["order123"] = [
            (mock_ws_owner, "owner", True),
            (mock_ws_non_owner, "other", False)
        ]
        
        message = {
            "type": "delivery_info",
            "recipient_phone": "+27821234567",
            "delivery_instructions": "Leave at door"
        }
        await connection_manager.broadcast_order_update("order123", message)
        
        # Owner should receive full message
        owner_call = mock_ws_owner.send_json.call_args[0][0]
        assert "recipient_phone" in owner_call
        
        # Non-owner should have sensitive fields removed
        non_owner_call = mock_ws_non_owner.send_json.call_args[0][0]
        assert "recipient_phone" not in non_owner_call
        assert "delivery_instructions" not in non_owner_call
    
    @pytest.mark.asyncio
    async def test_send_to_rider(self, connection_manager):
        """Test sending message to specific rider."""
        mock_ws = AsyncMock()
        connection_manager.rider_connections["rider123"] = mock_ws
        
        message = {"type": "new_order", "order_id": "order456"}
        await connection_manager.send_to_rider("rider123", message)
        
        mock_ws.send_json.assert_called_once_with(message)
    
    @pytest.mark.asyncio
    async def test_send_to_user(self, connection_manager):
        """Test sending message to specific user."""
        mock_ws = AsyncMock()
        connection_manager.user_connections["user123"] = mock_ws
        
        message = {"type": "notification", "text": "Order delivered!"}
        await connection_manager.send_to_user("user123", message)
        
        mock_ws.send_json.assert_called_once_with(message)
    
    @pytest.mark.asyncio
    async def test_broadcast_removes_dead_connections(self, connection_manager):
        """Test that dead connections are cleaned up."""
        dead_ws = AsyncMock()
        dead_ws.send_json.side_effect = Exception("Connection closed")
        
        alive_ws = AsyncMock()
        
        connection_manager.order_connections["order123"] = [
            (dead_ws, "dead_user", False),
            (alive_ws, "alive_user", False)
        ]
        
        message = {"type": "update"}
        await connection_manager.broadcast_order_update("order123", message)
        
        # Dead connection should be removed
        assert len(connection_manager.order_connections["order123"]) == 1
        assert connection_manager.order_connections["order123"][0][1] == "alive_user"


# ============ WEBSOCKET ENDPOINT TESTS ============

@pytest.mark.asyncio
async def test_track_order_websocket_no_token(async_client):
    """Test tracking endpoint without token."""
    # This test would require a WebSocket client
    # For now, we test the validation logic
    from app.routes.websocket import verify_websocket_token
    
    result = await verify_websocket_token(None)
    assert result is None


@pytest.mark.asyncio
async def test_rider_websocket_no_token(async_client):
    """Test rider endpoint without token."""
    from app.routes.websocket import verify_websocket_token
    
    result = await verify_websocket_token("")
    assert result is None


@pytest.mark.asyncio
async def test_user_websocket_no_token(async_client):
    """Test user endpoint without token."""
    from app.routes.websocket import verify_websocket_token
    
    result = await verify_websocket_token("Bearer invalid")
    assert result is None


# ============ HELPER FUNCTION TESTS ============

class TestNotifyFunctions:
    """Tests for notification helper functions."""
    
    @pytest.mark.asyncio
    async def test_notify_order_update(self):
        """Test notify_order_update helper."""
        from app.routes.websocket import notify_order_update
        
        with patch.object(manager, 'broadcast_order_update') as mock_broadcast:
            await notify_order_update(
                "order123",
                "status_change",
                {"status": "delivered"}
            )
            
            mock_broadcast.assert_called_once()
            call_args = mock_broadcast.call_args[0]
            assert call_args[0] == "order123"
            assert "type" in call_args[1]
            assert "timestamp" in call_args[1]
    
    @pytest.mark.asyncio
    async def test_notify_rider(self):
        """Test notify_rider helper."""
        from app.routes.websocket import notify_rider
        
        with patch.object(manager, 'send_to_rider') as mock_send:
            await notify_rider(
                "rider123",
                "new_delivery",
                {"order_id": "order456"}
            )
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0]
            assert call_args[0] == "rider123"
            assert "type" in call_args[1]
    
    @pytest.mark.asyncio
    async def test_notify_user(self):
        """Test notify_user helper."""
        from app.routes.websocket import notify_user
        
        with patch.object(manager, 'send_to_user') as mock_send:
            await notify_user(
                "user123",
                "order_update",
                {"message": "Your order is ready"}
            )
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0]
            assert call_args[0] == "user123"
            assert "type" in call_args[1]


# ============ WEBSOCKET CONSTANTS TESTS ============

def test_websocket_constants():
    """Test WebSocket constants are properly defined."""
    from app.routes.websocket import (
        MIN_LATITUDE, MAX_LATITUDE, MIN_LONGITUDE, MAX_LONGITUDE, MAX_SPEED
    )
    
    assert MIN_LATITUDE == -90.0
    assert MAX_LATITUDE == 90.0
    assert MIN_LONGITUDE == -180.0
    assert MAX_LONGITUDE == 180.0
    assert MAX_SPEED == 200.0  # km/h
