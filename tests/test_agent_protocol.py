#!/usr/bin/env python3
"""
Test Suite: Agent Protocol

Comprehensive tests for agent-to-agent messaging system.

Coverage:
- Message creation and serialization
- AgentBus connection and messaging
- Message routing and delivery
- Broadcast functionality
- State sharing
- Request-response patterns
- Consensus building
- Workflow coordination
- Error handling and recovery
"""

import asyncio
import json
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from apex.agents.agent_protocol import (
    MessageType,
    MessagePriority,
    DeliveryStatus,
    AgentMessage,
    MessageDelivery,
    SQLiteMessageStore,
    AgentBus,
    AgentCoordinator,
    create_agent_bus,
    send_task_request,
    broadcast_task_completion
)


# =============================================================================
# Message Tests
# =============================================================================

class TestAgentMessage:
    """Test AgentMessage dataclass."""
    
    def test_message_creation_defaults(self):
        """Test message creation with default values."""
        msg = AgentMessage(
            sender="agent-1",
            recipient="agent-2",
            payload={"test": "data"}
        )
        
        assert msg.sender == "agent-1"
        assert msg.recipient == "agent-2"
        assert msg.payload == {"test": "data"}
        assert msg.message_type == MessageType.DIRECT
        assert msg.priority == MessagePriority.NORMAL
        assert msg.ttl_seconds == 300
        assert msg.id is not None
        assert msg.timestamp is not None
    
    def test_message_creation_custom(self):
        """Test message creation with custom values."""
        msg = AgentMessage(
            sender="agent-1",
            recipient="*",
            message_type=MessageType.BROADCAST,
            payload={"announcement": "hello"},
            priority=MessagePriority.CRITICAL,
            ttl_seconds=600,
            correlation_id="corr-123",
            reply_to="agent-3",
            metadata={"key": "value"}
        )
        
        assert msg.message_type == MessageType.BROADCAST
        assert msg.priority == MessagePriority.CRITICAL
        assert msg.ttl_seconds == 600
        assert msg.correlation_id == "corr-123"
        assert msg.reply_to == "agent-3"
        assert msg.metadata == {"key": "value"}
    
    def test_message_to_dict(self):
        """Test message serialization to dict."""
        msg = AgentMessage(
            sender="agent-1",
            recipient="agent-2",
            message_type=MessageType.TASK_REQUEST,
            payload={"task": "test"},
            priority=MessagePriority.HIGH
        )
        
        data = msg.to_dict()
        
        assert data["sender"] == "agent-1"
        assert data["recipient"] == "agent-2"
        assert data["message_type"] == "task_request"
        assert data["priority"] == 1  # HIGH value
        assert data["payload"] == {"task": "test"}
    
    def test_message_from_dict(self):
        """Test message deserialization from dict."""
        data = {
            "id": "msg-123",
            "sender": "agent-1",
            "recipient": "agent-2",
            "message_type": "task_complete",
            "payload": {"result": "success"},
            "timestamp": "2024-01-01T00:00:00",
            "priority": 0,
            "ttl_seconds": 120
        }
        
        msg = AgentMessage.from_dict(data)
        
        assert msg.id == "msg-123"
        assert msg.sender == "agent-1"
        assert msg.message_type == MessageType.TASK_COMPLETE
        assert msg.priority == MessagePriority.CRITICAL
    
    def test_message_to_json(self):
        """Test message serialization to JSON."""
        msg = AgentMessage(
            sender="agent-1",
            recipient="agent-2",
            payload={"test": "data"}
        )
        
        json_str = msg.to_json()
        
        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["sender"] == "agent-1"
    
    def test_message_from_json(self):
        """Test message deserialization from JSON."""
        json_str = json.dumps({
            "id": "msg-123",
            "sender": "agent-1",
            "recipient": "agent-2",
            "message_type": "direct",
            "payload": {"test": "data"},
            "timestamp": datetime.utcnow().isoformat(),
            "priority": 2
        })
        
        msg = AgentMessage.from_json(json_str)
        
        assert msg.id == "msg-123"
        assert msg.payload == {"test": "data"}
    
    def test_message_is_expired(self):
        """Test message expiration check."""
        # Expired message (old timestamp)
        old_time = (datetime.utcnow() - timedelta(seconds=600)).isoformat()
        expired_msg = AgentMessage(
            sender="agent-1",
            recipient="agent-2",
            timestamp=old_time,
            ttl_seconds=300
        )
        assert expired_msg.is_expired() is True
        
        # Valid message (current timestamp)
        valid_msg = AgentMessage(
            sender="agent-1",
            recipient="agent-2",
            ttl_seconds=300
        )
        assert valid_msg.is_expired() is False
    
    def test_create_reply(self):
        """Test creating a reply message."""
        original = AgentMessage(
            sender="agent-1",
            recipient="agent-2",
            message_type=MessageType.HELP_REQUEST,
            payload={"question": "help?"},
            priority=MessagePriority.HIGH,
            correlation_id="corr-123"
        )
        
        reply = original.create_reply(
            payload={"answer": "here!"},
            message_type=MessageType.HELP_RESPONSE
        )
        
        assert reply.sender == "agent-2"
        assert reply.recipient == "agent-1"
        assert reply.message_type == MessageType.HELP_RESPONSE
        assert reply.correlation_id == "corr-123"
        assert reply.reply_to == "agent-1"


class TestMessageDelivery:
    """Test MessageDelivery tracking."""
    
    def test_delivery_status_tracking(self):
        """Test delivery status transitions."""
        delivery = MessageDelivery(message_id="msg-123")
        
        assert delivery.status == DeliveryStatus.PENDING
        assert delivery.attempts == 0
        
        delivery.mark_delivered()
        assert delivery.status == DeliveryStatus.DELIVERED
        assert delivery.delivered_at is not None
        
        delivery.mark_read()
        assert delivery.status == DeliveryStatus.READ
        assert delivery.read_at is not None
    
    def test_delivery_failure(self):
        """Test delivery failure tracking."""
        delivery = MessageDelivery(message_id="msg-123")
        
        delivery.mark_failed("Connection timeout")
        
        assert delivery.status == DeliveryStatus.FAILED
        assert delivery.last_error == "Connection timeout"


# =============================================================================
# SQLite Message Store Tests
# =============================================================================

class TestSQLiteMessageStore:
    """Test SQLite message store functionality."""
    
    def test_store_message(self, temp_db_path):
        """Test storing a message."""
        store = SQLiteMessageStore(db_path=str(temp_db_path))
        
        msg = AgentMessage(
            sender="agent-1",
            recipient="agent-2",
            payload={"test": "data"}
        )
        
        result = store.store_message(msg)
        
        assert result is True
    
    def test_get_messages_for_recipient(self, temp_db_path):
        """Test retrieving messages for recipient."""
        store = SQLiteMessageStore(db_path=str(temp_db_path))
        
        # Store multiple messages
        for i in range(3):
            msg = AgentMessage(
                sender="agent-1",
                recipient="agent-2",
                payload={"index": i}
            )
            store.store_message(msg)
        
        # Also store a message for different recipient
        other_msg = AgentMessage(
            sender="agent-1",
            recipient="agent-3",
            payload={"other": True}
        )
        store.store_message(other_msg)
        
        # Get messages for agent-2
        messages = store.get_messages_for_recipient("agent-2")
        
        assert len(messages) == 3
        assert all(m.recipient == "agent-2" for m in messages)
    
    def test_get_messages_with_type_filter(self, temp_db_path):
        """Test retrieving messages with type filter."""
        store = SQLiteMessageStore(db_path=str(temp_db_path))
        
        # Store different message types
        store.store_message(AgentMessage(
            sender="agent-1",
            recipient="agent-2",
            message_type=MessageType.TASK_REQUEST,
            payload={"type": "task"}
        ))
        store.store_message(AgentMessage(
            sender="agent-1",
            recipient="agent-2",
            message_type=MessageType.STATE_UPDATE,
            payload={"type": "state"}
        ))
        
        # Get only task requests
        messages = store.get_messages_for_recipient(
            "agent-2",
            message_type=MessageType.TASK_REQUEST
        )
        
        assert len(messages) == 1
        assert messages[0].message_type == MessageType.TASK_REQUEST
    
    def test_update_delivery_status(self, temp_db_path):
        """Test updating delivery status."""
        store = SQLiteMessageStore(db_path=str(temp_db_path))
        
        msg = AgentMessage(
            sender="agent-1",
            recipient="agent-2",
            payload={"test": "data"}
        )
        store.store_message(msg)
        
        store.update_delivery_status(msg.id, DeliveryStatus.DELIVERED)
        
        status = store.get_delivery_status(msg.id)
        assert status is not None
        assert status.status == DeliveryStatus.DELIVERED
    
    def test_cleanup_expired(self, temp_db_path):
        """Test cleanup of expired messages."""
        store = SQLiteMessageStore(db_path=str(temp_db_path))
        
        # Store expired message
        old_msg = AgentMessage(
            sender="agent-1",
            recipient="agent-2",
            timestamp=(datetime.utcnow() - timedelta(hours=1)).isoformat(),
            ttl_seconds=60,  # 1 minute TTL
            payload={"expired": True}
        )
        store.store_message(old_msg)
        
        # Store valid message
        valid_msg = AgentMessage(
            sender="agent-1",
            recipient="agent-2",
            ttl_seconds=3600,
            payload={"valid": True}
        )
        store.store_message(valid_msg)
        
        # Cleanup
        store.cleanup_expired()
        
        # Check only valid message remains
        messages = store.get_messages_for_recipient("agent-2")
        assert len(messages) == 1
        assert messages[0].payload == {"valid": True}
    
    def test_agent_state_storage(self, temp_db_path):
        """Test agent state storage and retrieval."""
        store = SQLiteMessageStore(db_path=str(temp_db_path))
        
        state = {"status": "idle", "load": 0.5}
        result = store.store_agent_state("agent-1", state, ttl_seconds=3600)
        
        assert result is True
        
        retrieved = store.get_agent_state("agent-1")
        assert retrieved == state
    
    def test_agent_state_expiration(self, temp_db_path):
        """Test agent state expiration."""
        store = SQLiteMessageStore(db_path=str(temp_db_path))
        
        # Store expired state
        store.store_agent_state(
            "agent-1",
            {"status": "old"},
            ttl_seconds=-1  # Already expired
        )
        
        retrieved = store.get_agent_state("agent-1")
        assert retrieved is None


# =============================================================================
# AgentBus Tests
# =============================================================================

@pytest.mark.asyncio
class TestAgentBus:
    """Test AgentBus functionality."""
    
    async def test_bus_initialization(self, temp_db_path):
        """Test bus initialization."""
        bus = AgentBus(sqlite_path=str(temp_db_path))
        
        assert bus._sqlite is not None
        assert bus._connected is False
        assert bus.max_retries == 3
    
    async def test_bus_connect_sqlite_fallback(self, temp_db_path):
        """Test bus connection with SQLite fallback."""
        bus = AgentBus(sqlite_path=str(temp_db_path))
        
        result = await bus.connect()
        
        # Should fall back to SQLite (no Redis in test env)
        assert result is False
        assert bus._connected is False  # SQLite mode
    
    async def test_send_message_sqlite(self, temp_db_path):
        """Test sending message in SQLite mode."""
        bus = AgentBus(sqlite_path=str(temp_db_path))
        await bus.connect()
        
        msg = AgentMessage(
            sender="agent-1",
            recipient="agent-2",
            payload={"test": "message"}
        )
        
        result = await bus.send_message(msg)
        
        assert result is True
        
        # Verify message is stored
        messages = await bus.get_messages("agent-2")
        assert len(messages) == 1
        assert messages[0].payload == {"test": "message"}
    
    async def test_send_direct(self, temp_db_path):
        """Test send_direct convenience method."""
        bus = AgentBus(sqlite_path=str(temp_db_path))
        await bus.connect()
        
        msg = await bus.send_direct(
            sender="agent-1",
            recipient="agent-2",
            payload={"direct": True},
            message_type=MessageType.TASK_REQUEST
        )
        
        assert msg.sender == "agent-1"
        assert msg.recipient == "agent-2"
        assert msg.message_type == MessageType.TASK_REQUEST
    
    async def test_broadcast(self, temp_db_path):
        """Test broadcast functionality."""
        bus = AgentBus(sqlite_path=str(temp_db_path))
        await bus.connect()
        
        msg = await bus.broadcast(
            sender="agent-1",
            payload={"announcement": "hello all"},
            message_type=MessageType.BROADCAST
        )
        
        assert msg.recipient == "*"
        
        # Verify multiple agents can receive
        messages_1 = await bus.get_messages("agent-2")
        messages_2 = await bus.get_messages("agent-3")
        
        assert len(messages_1) == 1
        assert len(messages_2) == 1
    
    async def test_subscribe_and_receive(self, temp_db_path, message_handler_mock):
        """Test subscription and message receiving."""
        bus = AgentBus(sqlite_path=str(temp_db_path))
        await bus.connect()
        
        # Subscribe handler
        await bus.subscribe("agent-2", handler=message_handler_mock)
        
        # Send message
        await bus.send_direct(
            sender="agent-1",
            recipient="agent-2",
            payload={"test": True}
        )
        
        # Note: In SQLite mode, handlers are not auto-triggered
        # but subscription should be registered
        assert "agent-2" in bus._subscriptions
    
    async def test_unsubscribe(self, temp_db_path, message_handler_mock):
        """Test unsubscription."""
        bus = AgentBus(sqlite_path=str(temp_db_path))
        await bus.connect()
        
        await bus.subscribe("agent-1", handler=message_handler_mock)
        await bus.unsubscribe("agent-1", handler=message_handler_mock)
        
        assert "agent-1" not in bus._subscriptions
    
    async def test_share_state(self, temp_db_path):
        """Test state sharing."""
        bus = AgentBus(sqlite_path=str(temp_db_path))
        await bus.connect()
        
        result = await bus.share_state(
            agent_id="agent-1",
            state={"status": "active", "load": 0.5},
            recipients=["agent-2", "agent-3"]
        )
        
        assert result is True
        
        # Verify state was stored
        state = await bus.get_agent_state("agent-1")
        assert state is not None
        assert state["status"] == "active"
    
    async def test_request_help_timeout(self, temp_db_path):
        """Test help request timeout."""
        bus = AgentBus(sqlite_path=str(temp_db_path))
        await bus.connect()
        
        # Request help with short timeout
        response = await bus.request_help(
            requester="agent-1",
            specialist_type="code_review",
            task_description="Review my code",
            context={"file": "test.py"},
            timeout_seconds=0.1  # Short timeout for test
        )
        
        # Should timeout
        assert response is None
    
    async def test_get_delivery_status(self, temp_db_path):
        """Test delivery status retrieval."""
        bus = AgentBus(sqlite_path=str(temp_db_path))
        await bus.connect()
        
        msg = await bus.send_direct(
            sender="agent-1",
            recipient="agent-2",
            payload={"test": True}
        )
        
        status = await bus.get_delivery_status(msg.id)
        
        assert status is not None
        assert status.message_id == msg.id


# =============================================================================
# AgentCoordinator Tests
# =============================================================================

@pytest.mark.asyncio
class TestAgentCoordinator:
    """Test AgentCoordinator functionality."""
    
    async def test_distribute_task_race(self, temp_db_path):
        """Test task distribution with race strategy."""
        bus = AgentBus(sqlite_path=str(temp_db_path))
        await bus.connect()
        
        coordinator = AgentCoordinator(bus)
        
        # This will timeout since no agents are listening
        with pytest.raises(asyncio.TimeoutError):
            await coordinator.distribute_task(
                task_id="task-1",
                task_type="test",
                agents=["agent-1", "agent-2"],
                payload={"data": "test"},
                strategy="race"
            )
    
    async def test_build_consensus(self, temp_db_path):
        """Test consensus building."""
        bus = AgentBus(sqlite_path=str(temp_db_path))
        await bus.connect()
        
        coordinator = AgentCoordinator(bus)
        
        # Build consensus (will timeout since no agents voting)
        result = await coordinator.build_consensus(
            proposal_id="prop-1",
            agents=["agent-1", "agent-2"],
            proposal={"action": "deploy"},
            timeout_seconds=0.1
        )
        
        assert result["proposal_id"] == "prop-1"
        assert result["total_votes"] == 0
        assert result["passed"] is False
    
    async def test_start_workflow(self, temp_db_path):
        """Test workflow starting."""
        bus = AgentBus(sqlite_path=str(temp_db_path))
        await bus.connect()
        
        coordinator = AgentCoordinator(bus)
        
        workflow_id = await coordinator.start_workflow(
            workflow_id="wf-1",
            steps=[
                {"type": "validate"},
                {"type": "build"}
            ],
            agents=["agent-1", "agent-2"]
        )
        
        assert workflow_id == "wf-1"
        assert "wf-1" in coordinator._workflows


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
class TestAgentProtocolIntegration:
    """Integration tests for agent protocol."""
    
    async def test_end_to_end_messaging(self, temp_db_path):
        """Test end-to-end messaging flow."""
        bus = AgentBus(sqlite_path=str(temp_db_path))
        await bus.connect()
        
        received_messages = []
        
        async def handler(message):
            received_messages.append(message)
        
        # Subscribe and send
        await bus.subscribe("agent-2", handler=handler)
        await bus.send_direct(
            sender="agent-1",
            recipient="agent-2",
            payload={"hello": "world"}
        )
        
        # Allow time for processing
        await asyncio.sleep(0.1)
        
        # Verify message was stored
        messages = await bus.get_messages("agent-2")
        assert len(messages) == 1
    
    async def test_multiple_agents_communication(self, temp_db_path):
        """Test communication between multiple agents."""
        bus = AgentBus(sqlite_path=str(temp_db_path))
        await bus.connect()
        
        # Send messages between multiple agents
        for i in range(5):
            await bus.send_direct(
                sender=f"agent-{i}",
                recipient=f"agent-{(i+1) % 5}",
                payload={"index": i}
            )
        
        # Verify each agent received one message
        for i in range(5):
            messages = await bus.get_messages(f"agent-{i}")
            assert len(messages) == 1
            assert messages[0].payload["index"] == (i - 1) % 5


# =============================================================================
# Error Handling Tests
# =============================================================================

@pytest.mark.asyncio
class TestAgentProtocolErrors:
    """Test error handling in agent protocol."""
    
    async def test_invalid_message_type(self):
        """Test handling of invalid message type."""
        with pytest.raises(ValueError):
            MessageType("invalid_type")
    
    async def test_corrupted_json(self):
        """Test handling of corrupted JSON."""
        with pytest.raises(json.JSONDecodeError):
            AgentMessage.from_json("{invalid json")
    
    async def test_missing_required_fields(self):
        """Test message creation with missing fields."""
        # Should handle gracefully with defaults
        msg = AgentMessage.from_dict({})
        
        assert msg.sender == ""
        assert msg.recipient == ""
        assert msg.payload == {}
