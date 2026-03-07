#!/usr/bin/env python3
"""
Test Fixtures

Test data and fixtures for MasterBuilder7 test suite.
"""

# Sample agent configurations
SAMPLE_AGENT_CONFIGS = {
    "code_generator": {
        "type": "code_generator",
        "capabilities": ["python", "javascript", "typescript"],
        "max_concurrent_tasks": 4
    },
    "security_scanner": {
        "type": "security_scanner",
        "capabilities": ["security", "audit"],
        "max_concurrent_tasks": 2
    },
    "test_runner": {
        "type": "test_runner",
        "capabilities": ["testing", "pytest", "jest"],
        "max_concurrent_tasks": 8
    }
}

# Sample task payloads
SAMPLE_TASK_PAYLOADS = {
    "code_review": {
        "files": ["src/main.py", "src/utils.py"],
        "options": {"strict": True, "auto_fix": False}
    },
    "security_audit": {
        "scope": "full",
        "checks": ["sql_injection", "xss", "csrf"]
    },
    "performance_test": {
        "endpoint": "/api/v1/users",
        "concurrent_users": 100,
        "duration": 60
    }
}

# Sample messages
SAMPLE_MESSAGES = {
    "task_request": {
        "task_type": "code_review",
        "data": {"file": "test.py"},
        "priority": "high"
    },
    "status_update": {
        "status": "in_progress",
        "progress": 50,
        "message": "Processing..."
    }
}

# Sample state values
SAMPLE_STATE_VALUES = {
    "build_config": {
        "target": "production",
        "optimize": True,
        "tests": True
    },
    "agent_status": {
        "agent_1": {"status": "idle", "load": 0.2},
        "agent_2": {"status": "busy", "load": 0.8}
    }
}

# Performance benchmarks
PERFORMANCE_BENCHMARKS = {
    "message_latency_ms": 10,
    "state_write_ms": 50,
    "state_read_ms": 10,
    "task_throughput_per_sec": 50,
    "max_concurrent_agents": 64
}
