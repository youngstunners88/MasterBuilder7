#!/usr/bin/env python3
"""
Test Suite: Health Monitor

Comprehensive tests for agent health monitoring system.

Coverage:
- Agent registration and lifecycle
- Heartbeat tracking
- Health score calculation
- Alert generation
- Automatic recovery
- Resource monitoring
- Dashboard data
- Database persistence
"""

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from apex.agents.health_monitor import (
    HealthStatus,
    AlertSeverity,
    AlertChannel,
    AgentHealth,
    Alert,
    SystemMetrics,
    HealthMonitor
)


# =============================================================================
# AgentHealth Tests
# =============================================================================

class TestAgentHealth:
    """Test AgentHealth dataclass."""
    
    def test_health_creation_defaults(self):
        """Test agent health creation with defaults."""
        health = AgentHealth(agent_id="agent-1")
        
        assert health.agent_id == "agent-1"
        assert health.agent_type == "unknown"
        assert health.status == HealthStatus.UNKNOWN
        assert health.health_score == 1.0
        assert health.heartbeat_count == 0
        assert health.missed_heartbeats == 0
    
    def test_health_creation_custom(self):
        """Test agent health creation with custom values."""
        now = datetime.now()
        health = AgentHealth(
            agent_id="agent-1",
            agent_type="code_generator",
            status=HealthStatus.HEALTHY,
            health_score=0.95,
            last_heartbeat=now,
            heartbeat_count=100,
            cpu_percent=50.0,
            memory_mb=512.0
        )
        
        assert health.agent_type == "code_generator"
        assert health.status == HealthStatus.HEALTHY
        assert health.health_score == 0.95
        assert health.last_heartbeat == now
    
    def test_health_to_dict(self):
        """Test health serialization."""
        health = AgentHealth(
            agent_id="agent-1",
            status=HealthStatus.HEALTHY,
            health_score=0.9
        )
        
        data = health.to_dict()
        
        assert data["agent_id"] == "agent-1"
        assert data["status"] == "healthy"
        assert data["health_score"] == 0.9


# =============================================================================
# Alert Tests
# =============================================================================

class TestAlert:
    """Test Alert dataclass."""
    
    def test_alert_creation(self):
        """Test alert creation."""
        alert = Alert(
            alert_id="ALT-123",
            severity=AlertSeverity.ERROR,
            channel=AlertChannel.LOG,
            agent_id="agent-1",
            title="Test Alert",
            message="Something went wrong"
        )
        
        assert alert.alert_id == "ALT-123"
        assert alert.severity == AlertSeverity.ERROR
        assert alert.channel == AlertChannel.LOG
        assert alert.agent_id == "agent-1"
        assert alert.title == "Test Alert"
        assert alert.acknowledged is False
        assert alert.resolved is False
    
    def test_alert_to_dict(self):
        """Test alert serialization."""
        alert = Alert(
            alert_id="ALT-123",
            severity=AlertSeverity.WARNING,
            channel=AlertChannel.WEBHOOK,
            title="Warning",
            message="Disk space low"
        )
        
        data = alert.to_dict()
        
        assert data["alert_id"] == "ALT-123"
        assert data["severity"] == "warning"
        assert data["channel"] == "webhook"


# =============================================================================
# SystemMetrics Tests
# =============================================================================

class TestSystemMetrics:
    """Test SystemMetrics dataclass."""
    
    def test_metrics_creation(self):
        """Test metrics creation."""
        metrics = SystemMetrics(
            total_agents=10,
            healthy_agents=8,
            degraded_agents=1,
            failed_agents=1,
            avg_health_score=0.85
        )
        
        assert metrics.total_agents == 10
        assert metrics.healthy_agents == 8
        assert metrics.degraded_agents == 1
        assert metrics.failed_agents == 1
        assert metrics.avg_health_score == 0.85
    
    def test_metrics_to_dict(self):
        """Test metrics serialization."""
        metrics = SystemMetrics(
            total_agents=5,
            cpu_percent=45.5
        )
        
        data = metrics.to_dict()
        
        assert data["total_agents"] == 5
        assert data["cpu_percent"] == 45.5
        assert "timestamp" in data


# =============================================================================
# HealthMonitor Tests
# =============================================================================

@pytest.mark.asyncio
class TestHealthMonitor:
    """Test HealthMonitor."""
    
    def test_monitor_initialization(self, temp_db_path):
        """Test monitor initialization."""
        monitor = HealthMonitor(
            db_path=str(temp_db_path),
            heartbeat_interval=30,
            auto_restart=True
        )
        
        assert monitor.db_path == str(temp_db_path)
        assert monitor.heartbeat_interval == 30
        assert monitor.auto_restart is True
        assert monitor.max_restarts == 5
    
    def test_register_agent(self, health_monitor, sample_agent_config):
        """Test agent registration."""
        monitor = health_monitor
        
        health = monitor.register_agent(
            "agent-1",
            config=sample_agent_config,
            agent_type="test_agent"
        )
        
        assert health.agent_id == "agent-1"
        assert health.agent_type == "test_agent"
        assert health.status == HealthStatus.STARTING
        assert "agent-1" in monitor.agents
    
    def test_register_duplicate_agent(self, health_monitor):
        """Test registering duplicate agent."""
        monitor = health_monitor
        
        monitor.register_agent("agent-1", agent_type="type1")
        health = monitor.register_agent("agent-1", agent_type="type2")
        
        # Should update existing
        assert health.agent_type == "type2"
        assert len(monitor.agents) == 1
    
    def test_unregister_agent(self, health_monitor):
        """Test agent unregistration."""
        monitor = health_monitor
        
        monitor.register_agent("agent-1", agent_type="test")
        result = monitor.unregister_agent("agent-1", reason="test")
        
        assert result is True
        assert "agent-1" not in monitor.agents
    
    def test_heartbeat(self, health_monitor):
        """Test heartbeat recording."""
        monitor = health_monitor
        
        monitor.register_agent("agent-1", agent_type="test")
        
        result = monitor.heartbeat("agent-1", {
            "cpu_percent": 50.0,
            "memory_mb": 512.0,
            "status": "healthy"
        })
        
        assert result is not None
        assert result.heartbeat_count == 1
        assert result.cpu_percent == 50.0
        assert result.memory_mb == 512.0
        assert result.status == HealthStatus.HEALTHY
    
    def test_heartbeat_unregistered_agent(self, health_monitor):
        """Test heartbeat from unregistered agent."""
        monitor = health_monitor
        
        result = monitor.heartbeat("unregistered-agent", {})
        
        assert result is None
    
    def test_check_health_single_agent(self, health_monitor):
        """Test health check for single agent."""
        monitor = health_monitor
        
        monitor.register_agent("agent-1", agent_type="test")
        monitor.heartbeat("agent-1", {"status": "healthy"})
        
        health = monitor.check_health("agent-1")
        
        assert health is not None
        assert health.agent_id == "agent-1"
    
    def test_check_health_system_wide(self, health_monitor):
        """Test system-wide health check."""
        monitor = health_monitor
        
        # Register multiple agents
        monitor.register_agent("agent-1", agent_type="test")
        monitor.register_agent("agent-2", agent_type="test")
        monitor.register_agent("agent-3", agent_type="test")
        
        # Simulate different health states
        monitor.heartbeat("agent-1", {"status": "healthy"})
        monitor.agents["agent-2"].status = HealthStatus.DEGRADED
        monitor.agents["agent-3"].status = HealthStatus.FAILED
        
        summary = monitor.check_health()
        
        assert summary["total_agents"] == 3
        assert summary["healthy_agents"] == 1
        assert summary["degraded_agents"] == 1
        assert summary["failed_agents"] == 1
        assert summary["system_status"] == "degraded"
    
    def test_health_score_calculation(self, health_monitor):
        """Test health score calculation."""
        monitor = health_monitor
        
        monitor.register_agent("agent-1", agent_type="test")
        agent = monitor.agents["agent-1"]
        
        # Test with recent heartbeat
        monitor.heartbeat("agent-1", {
            "cpu_percent": 30.0,
            "memory_mb": 512.0,
            "response_time_ms": 50.0
        })
        
        score = monitor._calculate_health_score(agent)
        
        assert 0.0 <= score <= 1.0
        assert agent.status == HealthStatus.HEALTHY
    
    def test_health_score_with_missed_heartbeats(self, health_monitor):
        """Test health score with missed heartbeats."""
        monitor = health_monitor
        
        monitor.register_agent("agent-1", agent_type="test")
        agent = monitor.agents["agent-1"]
        
        # Old heartbeat
        agent.last_heartbeat = datetime.now() - timedelta(minutes=10)
        agent.heartbeat_count = 1
        
        score = monitor._calculate_health_score(agent)
        
        # Should be low due to missed heartbeats
        assert score < 0.5
        assert agent.status == HealthStatus.FAILED
    
    def test_health_score_with_high_resource_usage(self, health_monitor):
        """Test health score with high resource usage."""
        monitor = health_monitor
        
        monitor.register_agent("agent-1", agent_type="test")
        agent = monitor.agents["agent-1"]
        
        monitor.heartbeat("agent-1", {
            "cpu_percent": 95.0,
            "memory_mb": 2048.0,  # > 1GB
            "disk_usage_mb": 6000.0,  # > 5GB
            "response_time_ms": 600.0  # > 500ms
        })
        
        score = monitor._calculate_health_score(agent)
        
        # Should be degraded due to high resource usage
        assert score < 0.8
    
    def test_score_to_status(self, health_monitor):
        """Test score to status conversion."""
        monitor = health_monitor
        
        assert monitor._score_to_status(0.9) == HealthStatus.HEALTHY
        assert monitor._score_to_status(0.7) == HealthStatus.DEGRADED
        assert monitor._score_to_status(0.4) == HealthStatus.FAILED
    
    def test_generate_alert(self, health_monitor):
        """Test alert generation."""
        monitor = health_monitor
        
        alert = monitor._generate_alert(
            severity=AlertSeverity.ERROR,
            title="Test Error",
            message="Something failed",
            agent_id="agent-1"
        )
        
        assert alert is not None
        assert alert.severity == AlertSeverity.ERROR
        assert alert.title == "Test Error"
        assert alert.agent_id == "agent-1"
        assert len(monitor.alerts) == 1
    
    def test_get_alerts_filtering(self, health_monitor):
        """Test alert filtering."""
        monitor = health_monitor
        
        # Generate various alerts
        monitor._generate_alert(AlertSeverity.ERROR, "Error 1", "msg", agent_id="agent-1")
        monitor._generate_alert(AlertSeverity.WARNING, "Warning 1", "msg", agent_id="agent-2")
        monitor._generate_alert(AlertSeverity.ERROR, "Error 2", "msg", agent_id="agent-1")
        
        # Filter by severity
        errors = monitor.get_alerts(severity=AlertSeverity.ERROR)
        assert len(errors) == 2
        
        # Filter by agent
        agent1_alerts = monitor.get_alerts(agent_id="agent-1")
        assert len(agent1_alerts) == 2
    
    def test_acknowledge_alert(self, health_monitor):
        """Test alert acknowledgment."""
        monitor = health_monitor
        
        alert = monitor._generate_alert(
            AlertSeverity.WARNING,
            "Test",
            "Test message"
        )
        
        result = monitor.acknowledge_alert(alert.alert_id)
        
        assert result is True
        assert monitor.alerts[0].acknowledged is True
    
    def test_resolve_alert(self, health_monitor):
        """Test alert resolution."""
        monitor = health_monitor
        
        alert = monitor._generate_alert(
            AlertSeverity.WARNING,
            "Test",
            "Test message"
        )
        
        result = monitor.resolve_alert(alert.alert_id)
        
        assert result is True
        assert monitor.alerts[0].resolved is True
    
    async def test_restart_failed_agents_disabled(self, health_monitor):
        """Test restart with auto_restart disabled."""
        monitor = health_monitor
        monitor.auto_restart = False
        
        results = await monitor.restart_failed_agents()
        
        assert results["reason"] == "auto_restart_disabled"
    
    async def test_restart_failed_agents(self, health_monitor):
        """Test restarting failed agents."""
        monitor = health_monitor
        monitor.auto_restart = True
        
        # Register a failed agent
        monitor.register_agent("agent-1", agent_type="test")
        monitor.agents["agent-1"].status = HealthStatus.FAILED
        monitor.agents["agent-1"].restart_count = 0
        
        # Note: Actual restart would require restart_command in config
        results = await monitor.restart_failed_agents()
        
        # Agent without restart_command will be skipped/failed
        assert "agent-1" in results["failed"] or "agent-1" in results["skipped"]
    
    async def test_respawn_agent_max_restarts(self, health_monitor):
        """Test respawn with max restarts exceeded."""
        monitor = health_monitor
        
        monitor.register_agent("agent-1", agent_type="test")
        monitor.agents["agent-1"].status = HealthStatus.FAILED
        monitor.agents["agent-1"].restart_count = 5  # At max
        
        result = await monitor.respawn_agent("agent-1")
        
        assert result is False
    
    def test_get_resource_usage(self, health_monitor):
        """Test resource usage retrieval."""
        monitor = health_monitor
        
        resources = monitor.get_resource_usage()
        
        assert "timestamp" in resources
        assert "cpu_percent" in resources
        assert "memory" in resources
        assert "disk" in resources
        assert "network" in resources
    
    def test_get_agent_resource_usage(self, health_monitor):
        """Test agent-specific resource usage."""
        monitor = health_monitor
        
        monitor.register_agent("agent-1", agent_type="test")
        monitor.heartbeat("agent-1", {
            "cpu_percent": 50.0,
            "memory_mb": 512.0
        })
        
        usage = monitor.get_agent_resource_usage("agent-1")
        
        assert usage is not None
        assert usage["cpu_percent"] == 50.0
        assert usage["memory_mb"] == 512.0
    
    def test_get_dashboard_data(self, health_monitor):
        """Test dashboard data generation."""
        monitor = health_monitor
        
        monitor.register_agent("agent-1", agent_type="test")
        monitor._generate_alert(AlertSeverity.INFO, "Test", "Test")
        
        dashboard = monitor.get_dashboard_data()
        
        assert "timestamp" in dashboard
        assert "system" in dashboard
        assert "resources" in dashboard
        assert "agents_by_status" in dashboard
        assert "recent_alerts" in dashboard
        assert "configuration" in dashboard
    
    async def test_start_stop_monitoring(self, health_monitor):
        """Test starting and stopping monitoring."""
        monitor = health_monitor
        
        # Start
        await monitor.start_monitoring()
        assert monitor._monitoring is True
        assert monitor.start_time is not None
        
        # Stop
        await monitor.stop_monitoring()
        assert monitor._monitoring is False
    
    async def test_monitor_loop_checks_heartbeats(self, health_monitor):
        """Test that monitor loop checks missed heartbeats."""
        monitor = health_monitor
        monitor.heartbeat_interval = 1  # Short for test
        
        monitor.register_agent("agent-1", agent_type="test")
        
        # Send initial heartbeat
        monitor.heartbeat("agent-1", {})
        
        # Wait past heartbeat interval
        await asyncio.sleep(0.1)
        
        # Manually trigger check
        await monitor._check_missed_heartbeats()
        
        # Agent should have missed heartbeats recorded
        assert monitor.agents["agent-1"].missed_heartbeats > 0
    
    async def test_health_check_loop(self, health_monitor):
        """Test health check loop collects metrics."""
        monitor = health_monitor
        
        monitor.register_agent("agent-1", agent_type="test")
        monitor.heartbeat("agent-1", {"status": "healthy"})
        
        await monitor._collect_system_metrics()
        
        assert len(monitor.system_metrics) == 1
        assert monitor.system_metrics[0].total_agents == 1


# =============================================================================
# Alert Handler Tests
# =============================================================================

@pytest.mark.asyncio
class TestAlertHandlers:
    """Test alert handler functionality."""
    
    def test_register_alert_handler(self, health_monitor):
        """Test custom alert handler registration."""
        monitor = health_monitor
        
        handler_called = False
        
        def custom_handler(alert):
            nonlocal handler_called
            handler_called = True
        
        monitor.register_alert_handler(AlertChannel.LOG, custom_handler)
        
        # Generate alert
        monitor._generate_alert(AlertSeverity.INFO, "Test", "Test")
        
        assert handler_called is True
    
    def test_set_webhook_url(self, health_monitor):
        """Test webhook URL configuration."""
        monitor = health_monitor
        
        monitor.set_webhook_url("https://example.com/webhook")
        
        assert monitor.webhook_url == "https://example.com/webhook"
        assert AlertChannel.WEBHOOK in monitor.alert_channels


# =============================================================================
# Error Handling Tests
# =============================================================================

@pytest.mark.asyncio
class TestHealthMonitorErrors:
    """Test error handling."""
    
    def test_unregister_nonexistent_agent(self, health_monitor):
        """Test unregistering non-existent agent."""
        monitor = health_monitor
        
        result = monitor.unregister_agent("nonexistent")
        
        assert result is False
    
    def test_acknowledge_nonexistent_alert(self, health_monitor):
        """Test acknowledging non-existent alert."""
        monitor = health_monitor
        
        result = monitor.acknowledge_alert("ALT-NONEXISTENT")
        
        assert result is False
    
    async def test_respawn_nonexistent_agent(self, health_monitor):
        """Test respawning non-existent agent."""
        monitor = health_monitor
        
        result = await monitor.respawn_agent("nonexistent")
        
        assert result is False
    
    def test_get_health_nonexistent_agent(self, health_monitor):
        """Test getting health of non-existent agent."""
        monitor = health_monitor
        
        result = monitor.check_health("nonexistent")
        
        assert result is None
