#!/usr/bin/env python3
"""
MasterBuilder7 Test Suite

Comprehensive test suite for MasterBuilder7 agent system.

Usage:
    # Run all tests
    pytest tests/
    
    # Run unit tests only
    pytest tests/ -m "not integration and not load"
    
    # Run integration tests
    pytest tests/ -m integration
    
    # Run load tests
    pytest tests/ -m load
    
    # Run with coverage
    pytest tests/ --cov=apex --cov-report=html

Test Organization:
    - test_agent_protocol.py: Agent messaging tests
    - test_shared_state.py: State management tests
    - test_task_queue.py: Task scheduling tests
    - test_health_monitor.py: Health check tests
    - test_cost_tracker.py: Cost tracking tests
    - test_mcp_server.py: MCP endpoint tests
    - test_integration.py: End-to-end tests
    - test_load.py: Performance tests

Fixtures:
    - conftest.py: Shared fixtures and configuration
    - fixtures/: Test data files
"""

__version__ = "1.0.0"
