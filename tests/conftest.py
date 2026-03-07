#!/usr/bin/env python3
"""
MasterBuilder7 Test Suite - Pytest Configuration and Fixtures

This module provides shared fixtures and configuration for all tests.
"""

import asyncio
import json
import os
import pytest
import pytest_asyncio
import sqlite3
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional
from unittest.mock import MagicMock, AsyncMock, patch

# Ensure test database paths don't conflict
TEST_DB_DIR = Path(tempfile.gettempdir()) / "masterbuilder7_test"


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m not slow')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "load: marks tests as load/performance tests")
    config.addinivalue_line("markers", "redis: marks tests that require Redis")


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment before all tests."""
    # Create test directory
    TEST_DB_DIR.mkdir(parents=True, exist_ok=True)
    
    # Set environment variables for testing
    os.environ.setdefault("REDIS_HOST", "localhost")
    os.environ.setdefault("REDIS_PORT", "6379")
    os.environ.setdefault("TEST_MODE", "true")
    
    yield
    
    # Cleanup after all tests
    if TEST_DB_DIR.exists():
        shutil.rmtree(TEST_DB_DIR, ignore_errors=True)


@pytest.fixture
def temp_db_path() -> Generator[Path, None, None]:
    """Provide a temporary database file path."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    db_path = TEST_DB_DIR / f"test_{timestamp}.db"
    yield db_path
    # Cleanup
    if db_path.exists():
        db_path.unlink(missing_ok=True)


@pytest.fixture
def temp_directory() -> Generator[Path, None, None]:
    """Provide a temporary directory."""
    temp_dir = Path(tempfile.mkdtemp(prefix="mb7_test_"))
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_agent_config() -> Dict[str, Any]:
    """Provide sample agent configuration."""
    return {
        "type": "test_agent",
        "capabilities": ["python", "fastapi", "testing"],
        "max_concurrent_tasks": 4,
        "restart_command": "echo 'restart'",
        "metadata": {"version": "1.0.0", "env": "test"}
    }


@pytest.fixture
def sample_task_payload() -> Dict[str, Any]:
    """Provide sample task payload."""
    return {
        "task_type": "test_task",
        "data": {
            "files": ["test.py"],
            "options": {"strict": True}
        },
        "metadata": {"priority": "high"}
    }


@pytest.fixture
def sample_message_payload() -> Dict[str, Any]:
    """Provide sample message payload."""
    return {
        "action": "test_action",
        "data": {"key": "value"},
        "timestamp": datetime.utcnow().isoformat()
    }


# =============================================================================
# Agent Protocol Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def agent_bus(temp_db_path):
    """Provide a connected AgentBus instance."""
    from apex.agents.agent_protocol import AgentBus
    
    bus = AgentBus(sqlite_path=str(temp_db_path))
    await bus.connect()
    yield bus
    await bus.disconnect()
    
    # Cleanup
    if temp_db_path.exists():
        temp_db_path.unlink(missing_ok=True)


@pytest.fixture
def message_handler_mock():
    """Provide a mock message handler."""
    handler = AsyncMock()
    handler.return_value = None
    return handler


# =============================================================================
# Shared State Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def shared_state_manager(temp_db_path):
    """Provide a SharedStateManager instance."""
    from apex.agents.shared_state import SharedStateManager
    
    manager = SharedStateManager(
        sqlite_path=str(temp_db_path),
        instance_id=f"test-{datetime.now().strftime('%H%M%S')}"
    )
    await manager.connect()
    yield manager
    await manager.disconnect()


@pytest.fixture
def sample_state_values() -> Dict[str, Any]:
    """Provide sample state values for testing."""
    return {
        "string_key": "test_value",
        "int_key": 42,
        "float_key": 3.14,
        "bool_key": True,
        "list_key": [1, 2, 3],
        "dict_key": {"nested": "value"},
    }


# =============================================================================
# Task Queue Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def task_queue(temp_db_path):
    """Provide a TaskQueue instance."""
    from apex.agents.task_queue import TaskQueue, QueueConfig
    
    config = QueueConfig(
        sqlite_path=str(temp_db_path),
        max_workers=10,
        task_timeout_seconds=30
    )
    
    queue = TaskQueue(config)
    await queue.connect()
    await queue.start()
    yield queue
    await queue.disconnect()


@pytest.fixture
def sample_task_data() -> List[Dict[str, Any]]:
    """Provide sample task data for batch operations."""
    return [
        {
            "type": "code_review",
            "payload": {"file": f"test_{i}.py"},
            "priority": i % 5  # Mix of priorities
        }
        for i in range(10)
    ]


# =============================================================================
# Health Monitor Fixtures
# =============================================================================

@pytest.fixture
def health_monitor(temp_db_path):
    """Provide a HealthMonitor instance."""
    from apex.agents.health_monitor import HealthMonitor
    
    monitor = HealthMonitor(
        db_path=str(temp_db_path),
        heartbeat_interval=5,
        check_interval=2,
        auto_restart=False,  # Disable for tests
        max_restarts=3
    )
    yield monitor
    # Cleanup is handled by temp_db_path fixture


@pytest.fixture
def sample_agents_registry() -> List[tuple]:
    """Provide sample agent registrations."""
    return [
        ("agent_001", "security_scanner", {"type": "security"}),
        ("agent_002", "code_generator", {"type": "code"}),
        ("agent_003", "performance_profiler", {"type": "perf"}),
        ("agent_004", "test_runner", {"type": "test"}),
    ]


# =============================================================================
# Cost Tracker Fixtures
# =============================================================================

@pytest.fixture
def cost_tracker(temp_directory):
    """Provide a CostTracker instance."""
    from apex.agents.cost_tracker import CostTracker
    
    storage_path = temp_directory / "cost_tracker_data.json"
    
    tracker = CostTracker(
        daily_budget=100.0,
        storage_path=str(storage_path),
        enable_kill_switch=True
    )
    yield tracker
    # Cleanup handled by temp_directory fixture


@pytest.fixture
def sample_usage_records() -> List[Dict[str, Any]]:
    """Provide sample usage records."""
    return [
        {
            "agent_id": "agent_001",
            "provider": "chatgpt",
            "model": "gpt-4",
            "tokens_input": 1000,
            "tokens_output": 500,
            "request_type": "code_generation"
        },
        {
            "agent_id": "agent_002",
            "provider": "claude",
            "model": "claude-3-sonnet",
            "tokens_input": 2000,
            "tokens_output": 1000,
            "request_type": "analysis"
        },
        {
            "agent_id": "agent_001",
            "provider": "kimi",
            "model": "kimi-v1",
            "tokens_input": 1500,
            "tokens_output": 750,
            "request_type": "general"
        },
    ]


# =============================================================================
# MCP Server Fixtures
# =============================================================================

@pytest.fixture
def mcp_server():
    """Provide an MCP server instance."""
    from mcp_server import MasterBuilder7MCPServer
    
    server = MasterBuilder7MCPServer()
    yield server


# =============================================================================
# Integration Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def integrated_system(temp_db_path):
    """Provide fully integrated system with all components."""
    from apex.agents.agent_protocol import AgentBus
    from apex.agents.shared_state import SharedStateManager
    from apex.agents.task_queue import TaskQueue, QueueConfig
    from apex.agents.health_monitor import HealthMonitor
    from apex.agents.cost_tracker import CostTracker
    
    # Create all components
    bus = AgentBus(sqlite_path=str(temp_db_path.with_suffix('.bus.db')))
    await bus.connect()
    
    state_manager = SharedStateManager(
        sqlite_path=str(temp_db_path.with_suffix('.state.db'))
    )
    await state_manager.connect()
    
    config = QueueConfig(sqlite_path=str(temp_db_path.with_suffix('.queue.db')))
    queue = TaskQueue(config)
    await queue.connect()
    await queue.start()
    
    monitor = HealthMonitor(
        db_path=str(temp_db_path.with_suffix('.health.db')),
        auto_restart=False
    )
    
    tracker = CostTracker(
        daily_budget=500.0,
        storage_path=str(temp_db_path.with_suffix('.cost.json'))
    )
    
    system = {
        "bus": bus,
        "state_manager": state_manager,
        "queue": queue,
        "monitor": monitor,
        "tracker": tracker
    }
    
    yield system
    
    # Cleanup
    await bus.disconnect()
    await state_manager.disconnect()
    await queue.disconnect()


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_redis():
    """Provide a mock Redis client."""
    mock = MagicMock()
    mock.ping = AsyncMock(return_value=True)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.setex = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.keys = AsyncMock(return_value=[])
    mock.publish = AsyncMock(return_value=1)
    mock.pubsub = MagicMock()
    mock.pubsub.return_value.subscribe = AsyncMock()
    mock.pubsub.return_value.listen = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def mock_aiohttp_session():
    """Provide a mock aiohttp ClientSession."""
    mock_session = MagicMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"success": True})
    mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
    return mock_session


# =============================================================================
# Benchmark Fixtures
# =============================================================================

@pytest.fixture
def benchmark_data() -> Dict[str, Any]:
    """Provide benchmark data for performance tests."""
    return {
        "concurrent_agents": 64,
        "tasks_per_agent": 10,
        "messages_per_agent": 50,
        "state_operations": 1000,
        "timeout_seconds": 60
    }
