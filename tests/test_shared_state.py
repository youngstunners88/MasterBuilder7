#!/usr/bin/env python3
"""
Test Suite: Shared State Management

Comprehensive tests for distributed state management.

Coverage:
- State value creation and serialization
- SQLite state backend operations
- Redis/SQLite state manager operations
- Distributed locking
- State snapshots
- Build progress tracking
- Agent status management
- Event system
- Conflict resolution
"""

import asyncio
import json
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from apex.agents.shared_state import (
    StateType,
    ConflictResolutionStrategy,
    StateEventType,
    LockStatus,
    StateValue,
    StateLock,
    StateSnapshot,
    StateEvent,
    BuildProgress,
    AgentStatusInfo,
    SQLiteStateBackend,
    SharedStateManager
)


# =============================================================================
# State Value Tests
# =============================================================================

class TestStateValue:
    """Test StateValue dataclass."""
    
    def test_state_value_creation(self):
        """Test state value creation."""
        sv = StateValue(
            key="test-key",
            value="test-value",
            state_type=StateType.STRING,
            owner="agent-1",
            tags=["tag1", "tag2"]
        )
        
        assert sv.key == "test-key"
        assert sv.value == "test-value"
        assert sv.state_type == StateType.STRING
        assert sv.owner == "agent-1"
        assert sv.tags == ["tag1", "tag2"]
        assert sv.version == 1
        assert sv.checksum is not None
    
    def test_state_value_checksum_calculation(self):
        """Test checksum calculation."""
        sv1 = StateValue(key="key", value="value", state_type=StateType.STRING)
        sv2 = StateValue(key="key", value="value", state_type=StateType.STRING)
        sv3 = StateValue(key="key", value="different", state_type=StateType.STRING)
        
        # Same content should have same checksum
        assert sv1.checksum == sv2.checksum
        # Different content should have different checksum
        assert sv1.checksum != sv3.checksum
    
    def test_state_value_expiration(self):
        """Test state value expiration."""
        # Expired value
        expired_sv = StateValue(
            key="expired",
            value="old",
            state_type=StateType.STRING,
            expires_at=(datetime.utcnow() - timedelta(hours=1)).isoformat()
        )
        assert expired_sv.is_expired() is True
        
        # Valid value
        valid_sv = StateValue(
            key="valid",
            value="new",
            state_type=StateType.STRING,
            expires_at=(datetime.utcnow() + timedelta(hours=1)).isoformat()
        )
        assert valid_sv.is_expired() is False
        
        # No expiration
        no_expire_sv = StateValue(
            key="no-expire",
            value="forever",
            state_type=StateType.STRING,
            expires_at=None
        )
        assert no_expire_sv.is_expired() is False
    
    def test_state_value_to_dict(self):
        """Test state value serialization."""
        sv = StateValue(
            key="test",
            value={"nested": "dict"},
            state_type=StateType.DICT,
            version=5
        )
        
        data = sv.to_dict()
        
        assert data["key"] == "test"
        assert data["value"] == {"nested": "dict"}
        assert data["state_type"] == "dict"
        assert data["version"] == 5
    
    def test_state_value_from_dict(self):
        """Test state value deserialization."""
        data = {
            "key": "test",
            "value": "value",
            "state_type": "string",
            "version": 3,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "checksum": "abc123"
        }
        
        sv = StateValue.from_dict(data)
        
        assert sv.key == "test"
        assert sv.value == "value"
        assert sv.state_type == StateType.STRING
        assert sv.version == 3
    
    def test_binary_value_serialization(self):
        """Test binary value serialization."""
        binary_data = b"\x00\x01\x02\x03"
        sv = StateValue(
            key="binary",
            value=binary_data,
            state_type=StateType.BINARY
        )
        
        data = sv.to_dict()
        assert isinstance(data["value"], str)  # Base64 encoded
        
        # Deserialize
        sv2 = StateValue.from_dict(data)
        assert sv2.value == binary_data


# =============================================================================
# State Lock Tests
# =============================================================================

class TestStateLock:
    """Test StateLock dataclass."""
    
    def test_lock_creation(self):
        """Test lock creation."""
        lock = StateLock(
            lock_id="lock-123",
            resource="critical-section",
            owner="agent-1",
            acquired_at=datetime.utcnow().isoformat(),
            expires_at=(datetime.utcnow() + timedelta(seconds=30)).isoformat(),
            ttl_seconds=30
        )
        
        assert lock.lock_id == "lock-123"
        assert lock.resource == "critical-section"
        assert lock.owner == "agent-1"
    
    def test_lock_expiration(self):
        """Test lock expiration."""
        expired_lock = StateLock(
            lock_id="lock-1",
            resource="resource",
            owner="agent",
            acquired_at=(datetime.utcnow() - timedelta(minutes=5)).isoformat(),
            expires_at=(datetime.utcnow() - timedelta(minutes=1)).isoformat(),
            ttl_seconds=240
        )
        assert expired_lock.is_expired() is True
        
        valid_lock = StateLock(
            lock_id="lock-2",
            resource="resource",
            owner="agent",
            acquired_at=datetime.utcnow().isoformat(),
            expires_at=(datetime.utcnow() + timedelta(minutes=5)).isoformat(),
            ttl_seconds=300
        )
        assert valid_lock.is_expired() is False


# =============================================================================
# State Snapshot Tests
# =============================================================================

class TestStateSnapshot:
    """Test StateSnapshot dataclass."""
    
    def test_snapshot_creation(self):
        """Test snapshot creation."""
        snapshot = StateSnapshot(
            snapshot_id="snap-123",
            name="test-snapshot",
            created_at=datetime.utcnow().isoformat(),
            state_data={"key1": "value1", "key2": "value2"},
            metadata={"version": "1.0"}
        )
        
        assert snapshot.snapshot_id == "snap-123"
        assert snapshot.name == "test-snapshot"
        assert len(snapshot.state_data) == 2
    
    def test_snapshot_serialization(self):
        """Test snapshot serialization."""
        snapshot = StateSnapshot(
            snapshot_id="snap-123",
            name="test",
            created_at=datetime.utcnow().isoformat(),
            state_data={"key": "value"}
        )
        
        data = snapshot.to_dict()
        snapshot2 = StateSnapshot.from_dict(data)
        
        assert snapshot2.snapshot_id == snapshot.snapshot_id
        assert snapshot2.state_data == snapshot.state_data


# =============================================================================
# State Event Tests
# =============================================================================

class TestStateEvent:
    """Test StateEvent dataclass."""
    
    def test_event_creation(self):
        """Test event creation."""
        event = StateEvent(
            event_type=StateEventType.SET,
            key="test-key",
            value="new-value",
            previous_value="old-value",
            source="agent-1"
        )
        
        assert event.event_type == StateEventType.SET
        assert event.key == "test-key"
        assert event.value == "new-value"
        assert event.previous_value == "old-value"
        assert event.source == "agent-1"
        assert event.timestamp is not None


# =============================================================================
# Build Progress Tests
# =============================================================================

class TestBuildProgress:
    """Test BuildProgress dataclass."""
    
    def test_progress_creation(self):
        """Test build progress creation."""
        progress = BuildProgress(
            build_id="build-123",
            stage="compiling",
            progress_percent=50.0,
            status="running",
            agent_id="agent-1"
        )
        
        assert progress.build_id == "build-123"
        assert progress.stage == "compiling"
        assert progress.progress_percent == 50.0
        assert progress.status == "running"
    
    def test_progress_serialization(self):
        """Test progress serialization."""
        progress = BuildProgress(
            build_id="build-123",
            stage="testing",
            progress_percent=75.0,
            status="running"
        )
        
        data = progress.to_dict()
        progress2 = BuildProgress.from_dict(data)
        
        assert progress2.build_id == progress.build_id
        assert progress2.progress_percent == progress.progress_percent


# =============================================================================
# Agent Status Tests
# =============================================================================

class TestAgentStatusInfo:
    """Test AgentStatusInfo dataclass."""
    
    def test_status_creation(self):
        """Test agent status creation."""
        status = AgentStatusInfo(
            agent_id="agent-1",
            agent_type="code_generator",
            status="busy",
            current_task="task-123",
            capabilities=["python", "fastapi"],
            metrics={"cpu": 50.0}
        )
        
        assert status.agent_id == "agent-1"
        assert status.agent_type == "code_generator"
        assert status.status == "busy"
        assert status.current_task == "task-123"
        assert "python" in status.capabilities


# =============================================================================
# SQLite State Backend Tests
# =============================================================================

class TestSQLiteStateBackend:
    """Test SQLite state backend."""
    
    def test_set_and_get_value(self, temp_db_path):
        """Test setting and getting values."""
        backend = SQLiteStateBackend(db_path=str(temp_db_path))
        
        sv = StateValue(
            key="test-key",
            value="test-value",
            state_type=StateType.STRING
        )
        
        assert backend.set_value(sv) is True
        
        retrieved = backend.get_value("test-key")
        assert retrieved is not None
        assert retrieved.value == "test-value"
        assert retrieved.state_type == StateType.STRING
    
    def test_delete_value(self, temp_db_path):
        """Test value deletion."""
        backend = SQLiteStateBackend(db_path=str(temp_db_path))
        
        backend.set_value(StateValue(
            key="delete-me",
            value="value",
            state_type=StateType.STRING
        ))
        
        assert backend.delete_value("delete-me") is True
        assert backend.get_value("delete-me") is None
    
    def test_list_keys(self, temp_db_path):
        """Test key listing."""
        backend = SQLiteStateBackend(db_path=str(temp_db_path))
        
        # Add multiple values
        for i in range(5):
            backend.set_value(StateValue(
                key=f"key-{i}",
                value=f"value-{i}",
                state_type=StateType.STRING
            ))
        
        keys = backend.list_keys("key-*")
        assert len(keys) == 5
    
    def test_lock_operations(self, temp_db_path):
        """Test lock operations."""
        backend = SQLiteStateBackend(db_path=str(temp_db_path))
        
        lock = StateLock(
            lock_id="lock-1",
            resource="resource-1",
            owner="agent-1",
            acquired_at=datetime.utcnow().isoformat(),
            expires_at=(datetime.utcnow() + timedelta(minutes=5)).isoformat(),
            ttl_seconds=300
        )
        
        # Acquire lock
        assert backend.acquire_lock(lock) is True
        
        # Try to acquire same lock (should fail)
        lock2 = StateLock(
            lock_id="lock-2",
            resource="resource-1",
            owner="agent-2",
            acquired_at=datetime.utcnow().isoformat(),
            expires_at=(datetime.utcnow() + timedelta(minutes=5)).isoformat(),
            ttl_seconds=300
        )
        assert backend.acquire_lock(lock2) is False
        
        # Release lock
        assert backend.release_lock("resource-1", "lock-1") is True
        
        # Now can acquire
        assert backend.acquire_lock(lock2) is True
    
    def test_snapshot_operations(self, temp_db_path):
        """Test snapshot operations."""
        backend = SQLiteStateBackend(db_path=str(temp_db_path))
        
        snapshot = StateSnapshot(
            snapshot_id="snap-1",
            name="test-snapshot",
            created_at=datetime.utcnow().isoformat(),
            state_data={"key": "value"}
        )
        
        # Save snapshot
        assert backend.save_snapshot(snapshot) is True
        
        # Get snapshot
        retrieved = backend.get_snapshot("snap-1")
        assert retrieved is not None
        assert retrieved.name == "test-snapshot"
        
        # List snapshots
        snapshots = backend.list_snapshots()
        assert len(snapshots) == 1
        
        # Delete snapshot
        assert backend.delete_snapshot("snap-1") is True
        assert backend.get_snapshot("snap-1") is None
    
    def test_event_logging(self, temp_db_path):
        """Test event logging."""
        backend = SQLiteStateBackend(db_path=str(temp_db_path))
        
        event = StateEvent(
            event_type=StateEventType.SET,
            key="test-key",
            value="new-value",
            source="agent-1"
        )
        
        backend.log_event(event)
        
        events = backend.get_recent_events(limit=10)
        assert len(events) == 1
        assert events[0].event_type == StateEventType.SET
        assert events[0].key == "test-key"


# =============================================================================
# SharedStateManager Tests
# =============================================================================

@pytest.mark.asyncio
class TestSharedStateManager:
    """Test SharedStateManager."""
    
    async def test_manager_initialization(self, temp_db_path):
        """Test manager initialization."""
        manager = SharedStateManager(sqlite_path=str(temp_db_path))
        
        assert manager._sqlite is not None
        assert manager.conflict_strategy == ConflictResolutionStrategy.LAST_WRITE_WINS
        assert manager.instance_id is not None
    
    async def test_connect_disconnect(self, temp_db_path):
        """Test connection lifecycle."""
        manager = SharedStateManager(sqlite_path=str(temp_db_path))
        
        result = await manager.connect()
        # Should fall back to SQLite
        assert result is False
        
        await manager.disconnect()
    
    async def test_set_and_get(self, shared_state_manager):
        """Test basic set and get operations."""
        manager = shared_state_manager
        
        # Set value
        result = await manager.set("test-key", "test-value")
        assert result is True
        
        # Get value
        value = await manager.get("test-key")
        assert value == "test-value"
    
    async def test_set_with_type(self, shared_state_manager):
        """Test set with explicit type."""
        manager = shared_state_manager
        
        await manager.set("int-key", 42, state_type=StateType.INTEGER)
        await manager.set("float-key", 3.14, state_type=StateType.FLOAT)
        await manager.set("bool-key", True, state_type=StateType.BOOLEAN)
        await manager.set("list-key", [1, 2, 3], state_type=StateType.LIST)
        await manager.set("dict-key", {"a": 1}, state_type=StateType.DICT)
        
        assert await manager.get("int-key") == 42
        assert await manager.get("float-key") == 3.14
        assert await manager.get("bool-key") is True
        assert await manager.get("list-key") == [1, 2, 3]
        assert await manager.get("dict-key") == {"a": 1}
    
    async def test_set_with_ttl(self, shared_state_manager):
        """Test set with TTL."""
        manager = shared_state_manager
        
        # Set with very short TTL
        await manager.set("temp-key", "temp-value", ttl_seconds=1)
        
        # Should be available immediately
        assert await manager.get("temp-key") == "temp-value"
        
        # Wait for expiration
        await asyncio.sleep(2)
        
        # Should be expired
        assert await manager.get("temp-key") is None
    
    async def test_delete(self, shared_state_manager):
        """Test delete operation."""
        manager = shared_state_manager
        
        await manager.set("delete-key", "value")
        assert await manager.exists("delete-key") is True
        
        await manager.delete("delete-key")
        assert await manager.exists("delete-key") is False
    
    async def test_increment(self, shared_state_manager):
        """Test increment operation."""
        manager = shared_state_manager
        
        # Integer increment
        new_val = await manager.increment("counter", amount=1, default=0)
        assert new_val == 1
        
        new_val = await manager.increment("counter", amount=5)
        assert new_val == 6
        
        # Float increment
        new_val = await manager.increment("float-counter", amount=0.5, default=0.0)
        assert new_val == 0.5
    
    async def test_list_operations(self, shared_state_manager):
        """Test list operations."""
        manager = shared_state_manager
        
        await manager.append_to_list("my-list", "item1")
        await manager.append_to_list("my-list", "item2", "item3")
        
        result = await manager.get("my-list")
        assert result == ["item1", "item2", "item3"]
    
    async def test_dict_operations(self, shared_state_manager):
        """Test dict operations."""
        manager = shared_state_manager
        
        await manager.update_dict("my-dict", {"key1": "value1"})
        await manager.update_dict("my-dict", {"key2": "value2"})
        
        result = await manager.get("my-dict")
        assert result == {"key1": "value1", "key2": "value2"}
    
    async def test_lock_context_manager(self, shared_state_manager):
        """Test lock context manager."""
        manager = shared_state_manager
        
        async with manager.lock("critical-section", owner="test-agent", ttl_seconds=5) as lock_id:
            assert lock_id is not None
            
            # Verify lock is held
            lock_info = await manager.get_lock_info("critical-section")
            assert lock_info is not None
            assert lock_info.owner == "test-agent"
        
        # Lock should be released
        lock_info = await manager.get_lock_info("critical-section")
        assert lock_info is None
    
    async def test_snapshot_and_restore(self, shared_state_manager):
        """Test snapshot and restore."""
        manager = shared_state_manager
        
        # Set some values
        await manager.set("key1", "value1")
        await manager.set("key2", "value2")
        await manager.set("key3", "value3")
        
        # Create snapshot
        snapshot_id = await manager.snapshot(name="test-snapshot")
        assert snapshot_id is not None
        
        # Modify values
        await manager.set("key1", "modified")
        await manager.delete("key2")
        
        # Restore snapshot
        result = await manager.restore(snapshot_id)
        assert result is True
        
        # Verify restored values
        assert await manager.get("key1") == "value1"
        assert await manager.get("key2") == "value2"
        assert await manager.get("key3") == "value3"
    
    async def test_build_progress_tracking(self, shared_state_manager):
        """Test build progress tracking."""
        manager = shared_state_manager
        
        await manager.track_build_progress(
            build_id="build-123",
            stage="compiling",
            progress_percent=50.0,
            status="running",
            agent_id="agent-1"
        )
        
        progress = await manager.get_build_progress("build-123")
        assert progress is not None
        assert progress["stage"] == "compiling"
        assert progress["progress_percent"] == 50.0
    
    async def test_agent_status_management(self, shared_state_manager):
        """Test agent status management."""
        manager = shared_state_manager
        
        await manager.update_agent_status(
            agent_id="agent-1",
            agent_type="code_generator",
            status="idle",
            capabilities=["python", "fastapi"],
            metrics={"cpu": 30.0}
        )
        
        status = await manager.get_agent_status("agent-1")
        assert status is not None
        assert status["agent_id"] == "agent-1"
        assert status["status"] == "idle"
        assert "python" in status["capabilities"]
    
    async def test_keys_pattern(self, shared_state_manager):
        """Test key listing with pattern."""
        manager = shared_state_manager
        
        await manager.set("user:1:name", "Alice")
        await manager.set("user:1:email", "alice@test.com")
        await manager.set("user:2:name", "Bob")
        await manager.set("config:app", "settings")
        
        user_keys = await manager.keys("user:*")
        assert len(user_keys) == 3
        
        all_keys = await manager.keys("*")
        assert len(all_keys) == 4


# =============================================================================
# Event System Tests
# =============================================================================

@pytest.mark.asyncio
class TestEventSystem:
    """Test event system."""
    
    async def test_event_handler_registration(self, shared_state_manager):
        """Test event handler registration."""
        manager = shared_state_manager
        
        events_received = []
        
        @manager.on(StateEventType.SET)
        def handler(event):
            events_received.append(event)
        
        await manager.set("test-key", "value")
        
        # Give time for event processing
        await asyncio.sleep(0.1)
        
        assert len(events_received) == 1
        assert events_received[0].event_type == StateEventType.SET
    
    async def test_key_pattern_handler(self, shared_state_manager):
        """Test key pattern event handler."""
        manager = shared_state_manager
        
        events_received = []
        
        @manager.on(StateEventType.SET, key_pattern="user:*")
        def handler(event):
            events_received.append(event)
        
        await manager.set("user:1", "Alice")
        await manager.set("user:2", "Bob")
        await manager.set("config:app", "settings")
        
        await asyncio.sleep(0.1)
        
        assert len(events_received) == 2


# =============================================================================
# Error Handling Tests
# =============================================================================

@pytest.mark.asyncio
class TestSharedStateErrors:
    """Test error handling."""
    
    async def test_get_nonexistent_key(self, shared_state_manager):
        """Test getting non-existent key."""
        manager = shared_state_manager
        
        result = await manager.get("nonexistent-key")
        assert result is None
    
    async def test_get_with_default(self, shared_state_manager):
        """Test get with default value."""
        manager = shared_state_manager
        
        result = await manager.get("nonexistent-key", default="default-value")
        assert result == "default-value"
    
    async def test_set_nx_xx(self, shared_state_manager):
        """Test set with nx/xx flags."""
        manager = shared_state_manager
        
        # nx=True - only set if not exists
        result1 = await manager.set("nx-key", "value1", nx=True)
        assert result1 is True
        
        result2 = await manager.set("nx-key", "value2", nx=True)
        assert result2 is False  # Already exists
        
        # xx=True - only set if exists
        result3 = await manager.set("new-key", "value", xx=True)
        assert result3 is False  # Doesn't exist
        
        await manager.set("existing-key", "value")
        result4 = await manager.set("existing-key", "new-value", xx=True)
        assert result4 is True  # Exists
