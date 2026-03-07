#!/usr/bin/env python3
"""
APEX Agent Health Monitoring System
Production-ready 24/7 health monitoring for all agents.

Features:
- Heartbeat tracking from all agents
- Automatic restart of failed agents
- Health score calculation (0.0 - 1.0)
- Alert generation for system issues
- Resource usage monitoring (CPU, memory, disk)
- Dashboard data generation
- Multi-channel alerting (log, webhook, notification)

Health Score Thresholds:
- HEALTHY: >0.8 (green)
- DEGRADED: 0.5-0.8 (yellow)
- FAILED: <0.5 (red)

Usage:
    monitor = HealthMonitor()
    await monitor.start_monitoring()
    
    # Register an agent
    monitor.register_agent("agent_001", agent_config)
    
    # Agent sends heartbeat
    monitor.heartbeat("agent_001", status_data)
    
    # Check system health
    health = monitor.check_health()
    
    # Get dashboard data
    dashboard = monitor.get_dashboard_data()

Author: APEX Reliability Team
Version: 1.0.0
"""

import asyncio
import json
import logging
import os
import sqlite3
import subprocess
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from contextlib import contextmanager
import hashlib
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Optional imports with graceful fallback
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available. Resource monitoring will be limited.")

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    logger.warning("aiohttp not available. Webhook alerts will be disabled.")


class HealthStatus(Enum):
    """Health status enumeration based on health score thresholds."""
    HEALTHY = "healthy"      # > 0.8
    DEGRADED = "degraded"    # 0.5 - 0.8
    FAILED = "failed"        # < 0.5
    UNKNOWN = "unknown"      # No data yet
    STARTING = "starting"    # Agent is starting up
    STOPPING = "stopping"    # Agent is shutting down


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Available alert channels."""
    LOG = "log"
    WEBHOOK = "webhook"
    NOTIFICATION = "notification"
    EMAIL = "email"
    SMS = "sms"
    PAGERDUTY = "pagerduty"
    SLACK = "slack"


@dataclass
class AgentHealth:
    """
    Health data for a single agent.
    
    Attributes:
        agent_id: Unique agent identifier
        agent_type: Type of agent (e.g., 'security_audit', 'code_generator')
        status: Current health status
        health_score: Health score from 0.0 to 1.0
        last_heartbeat: Timestamp of last heartbeat
        heartbeat_count: Total number of heartbeats received
        missed_heartbeats: Number of missed heartbeats
        restart_count: Number of times agent was restarted
        last_restart: Timestamp of last restart
        uptime_seconds: Total uptime in seconds
        cpu_percent: Current CPU usage percentage
        memory_mb: Current memory usage in MB
        disk_usage_mb: Current disk usage in MB
        response_time_ms: Average response time in milliseconds
        error_count: Number of errors encountered
        last_error: Last error message
        metadata: Additional agent-specific metadata
        created_at: When the agent was first registered
        updated_at: When health data was last updated
    """
    agent_id: str
    agent_type: str = "unknown"
    status: HealthStatus = HealthStatus.UNKNOWN
    health_score: float = 1.0
    last_heartbeat: Optional[datetime] = None
    heartbeat_count: int = 0
    missed_heartbeats: int = 0
    restart_count: int = 0
    last_restart: Optional[datetime] = None
    uptime_seconds: float = 0.0
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    disk_usage_mb: float = 0.0
    response_time_ms: float = 0.0
    error_count: int = 0
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": self.status.value,
            "health_score": round(self.health_score, 3),
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "heartbeat_count": self.heartbeat_count,
            "missed_heartbeats": self.missed_heartbeats,
            "restart_count": self.restart_count,
            "last_restart": self.last_restart.isoformat() if self.last_restart else None,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "cpu_percent": round(self.cpu_percent, 2),
            "memory_mb": round(self.memory_mb, 2),
            "disk_usage_mb": round(self.disk_usage_mb, 2),
            "response_time_ms": round(self.response_time_ms, 2),
            "error_count": self.error_count,
            "last_error": self.last_error,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class Alert:
    """
    Alert data structure.
    
    Attributes:
        alert_id: Unique alert identifier
        severity: Alert severity level
        channel: Alert channel
        agent_id: Related agent ID (if applicable)
        title: Alert title
        message: Alert message
        timestamp: When the alert was generated
        acknowledged: Whether the alert has been acknowledged
        resolved: Whether the alert has been resolved
        metadata: Additional alert metadata
    """
    alert_id: str
    severity: AlertSeverity
    channel: AlertChannel
    agent_id: Optional[str] = None
    title: str = ""
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "alert_id": self.alert_id,
            "severity": self.severity.value,
            "channel": self.channel.value,
            "agent_id": self.agent_id,
            "title": self.title,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "acknowledged": self.acknowledged,
            "resolved": self.resolved,
            "metadata": self.metadata,
        }


@dataclass
class SystemMetrics:
    """System-wide metrics."""
    timestamp: datetime = field(default_factory=datetime.now)
    total_agents: int = 0
    healthy_agents: int = 0
    degraded_agents: int = 0
    failed_agents: int = 0
    unknown_agents: int = 0
    avg_health_score: float = 0.0
    total_restarts: int = 0
    total_alerts: int = 0
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_percent: float = 0.0
    network_io_mb: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_agents": self.total_agents,
            "healthy_agents": self.healthy_agents,
            "degraded_agents": self.degraded_agents,
            "failed_agents": self.failed_agents,
            "unknown_agents": self.unknown_agents,
            "avg_health_score": round(self.avg_health_score, 3),
            "total_restarts": self.total_restarts,
            "total_alerts": self.total_alerts,
            "cpu_percent": round(self.cpu_percent, 2),
            "memory_percent": round(self.memory_percent, 2),
            "disk_percent": round(self.disk_percent, 2),
            "network_io_mb": round(self.network_io_mb, 2),
        }


class HealthMonitor:
    """
    Production-ready 24/7 agent health monitoring system.
    
    Features:
    - Heartbeat tracking with configurable intervals
    - Automatic health score calculation
    - Automatic restart of failed agents
    - Multi-channel alerting
    - Resource monitoring
    - Dashboard data generation
    - Persistent storage in SQLite
    
    Configuration:
    - HEALTHY_THRESHOLD: >0.8 (default)
    - DEGRADED_THRESHOLD: 0.5 (default)
    - HEARTBEAT_INTERVAL: 30 seconds (default)
    - MISSED_HEARTBEAT_TOLERANCE: 3 (default)
    - AUTO_RESTART_ENABLED: True (default)
    - MAX_RESTART_ATTEMPTS: 5 (default)
    
    Example:
        monitor = HealthMonitor(
            db_path="/path/to/health.db",
            heartbeat_interval=30,
            auto_restart=True
        )
        
        # Start monitoring
        await monitor.start_monitoring()
        
        # Register agents
        monitor.register_agent("agent_001", {"type": "security"})
        
        # Agents send heartbeats
        monitor.heartbeat("agent_001", {"status": "working"})
        
        # Get health status
        health = monitor.check_health()
        
        # Stop monitoring
        await monitor.stop_monitoring()
    """
    
    # Health score thresholds
    HEALTHY_THRESHOLD = 0.8
    DEGRADED_THRESHOLD = 0.5
    
    # Default configuration
    DEFAULT_HEARTBEAT_INTERVAL = 30  # seconds
    DEFAULT_CHECK_INTERVAL = 10      # seconds
    DEFAULT_MISSED_TOLERANCE = 3
    DEFAULT_MAX_RESTARTS = 5
    DEFAULT_RESTART_COOLDOWN = 60    # seconds
    
    def __init__(
        self,
        db_path: str = "/home/teacherchris37/MasterBuilder7/apex/agents/health_monitor.db",
        heartbeat_interval: int = DEFAULT_HEARTBEAT_INTERVAL,
        check_interval: int = DEFAULT_CHECK_INTERVAL,
        missed_tolerance: int = DEFAULT_MISSED_TOLERANCE,
        auto_restart: bool = True,
        max_restarts: int = DEFAULT_MAX_RESTARTS,
        restart_cooldown: int = DEFAULT_RESTART_COOLDOWN,
        webhook_url: Optional[str] = None,
        alert_channels: Optional[List[AlertChannel]] = None
    ):
        """
        Initialize the health monitor.
        
        Args:
            db_path: Path to SQLite database
            heartbeat_interval: Expected heartbeat interval in seconds
            check_interval: Health check interval in seconds
            missed_tolerance: Number of missed heartbeats before marking failed
            auto_restart: Enable automatic restart of failed agents
            max_restarts: Maximum restart attempts per agent
            restart_cooldown: Cooldown period between restarts in seconds
            webhook_url: URL for webhook alerts
            alert_channels: List of enabled alert channels
        """
        self.db_path = db_path
        self.heartbeat_interval = heartbeat_interval
        self.check_interval = check_interval
        self.missed_tolerance = missed_tolerance
        self.auto_restart = auto_restart
        self.max_restarts = max_restarts
        self.restart_cooldown = restart_cooldown
        self.webhook_url = webhook_url
        self.alert_channels = alert_channels or [AlertChannel.LOG]
        
        # Agent tracking
        self.agents: Dict[str, AgentHealth] = {}
        self.agent_configs: Dict[str, Dict[str, Any]] = {}
        self.restart_history: Dict[str, List[datetime]] = {}
        
        # Alert tracking
        self.alerts: List[Alert] = []
        self.alert_handlers: Dict[AlertChannel, List[Callable]] = {
            channel: [] for channel in AlertChannel
        }
        
        # Monitoring state
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._resource_monitor_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.system_metrics: List[SystemMetrics] = []
        self.start_time: Optional[datetime] = None
        
        # Initialize
        self._init_database()
        self._register_default_alert_handlers()
        
        logger.info(
            f"HealthMonitor initialized: db={db_path}, "
            f"heartbeat={heartbeat_interval}s, auto_restart={auto_restart}"
        )
    
    def _init_database(self):
        """Initialize SQLite database for persistence."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Agent health table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_health (
                agent_id TEXT PRIMARY KEY,
                agent_type TEXT DEFAULT 'unknown',
                status TEXT DEFAULT 'unknown',
                health_score REAL DEFAULT 1.0,
                last_heartbeat TEXT,
                heartbeat_count INTEGER DEFAULT 0,
                missed_heartbeats INTEGER DEFAULT 0,
                restart_count INTEGER DEFAULT 0,
                last_restart TEXT,
                uptime_seconds REAL DEFAULT 0.0,
                cpu_percent REAL DEFAULT 0.0,
                memory_mb REAL DEFAULT 0.0,
                disk_usage_mb REAL DEFAULT 0.0,
                response_time_ms REAL DEFAULT 0.0,
                error_count INTEGER DEFAULT 0,
                last_error TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Alerts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id TEXT PRIMARY KEY,
                severity TEXT NOT NULL,
                channel TEXT NOT NULL,
                agent_id TEXT,
                title TEXT,
                message TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                acknowledged INTEGER DEFAULT 0,
                resolved INTEGER DEFAULT 0,
                metadata TEXT
            )
        ''')
        
        # System metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                total_agents INTEGER DEFAULT 0,
                healthy_agents INTEGER DEFAULT 0,
                degraded_agents INTEGER DEFAULT 0,
                failed_agents INTEGER DEFAULT 0,
                unknown_agents INTEGER DEFAULT 0,
                avg_health_score REAL DEFAULT 0.0,
                total_restarts INTEGER DEFAULT 0,
                total_alerts INTEGER DEFAULT 0,
                cpu_percent REAL DEFAULT 0.0,
                memory_percent REAL DEFAULT 0.0,
                disk_percent REAL DEFAULT 0.0,
                network_io_mb REAL DEFAULT 0.0
            )
        ''')
        
        # Restart history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS restart_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                restart_time TEXT DEFAULT CURRENT_TIMESTAMP,
                reason TEXT,
                success INTEGER DEFAULT 1
            )
        ''')
        
        # Indexes
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_agent_status ON agent_health(status)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON system_metrics(timestamp)
        ''')
        
        conn.commit()
        conn.close()
        logger.debug("Database initialized")
    
    def _register_default_alert_handlers(self):
        """Register default alert handlers for each channel."""
        # Log handler
        self.alert_handlers[AlertChannel.LOG].append(self._log_alert)
        
        # Webhook handler
        if self.webhook_url and AIOHTTP_AVAILABLE:
            self.alert_handlers[AlertChannel.WEBHOOK].append(self._webhook_alert)
    
    # =========================================================================
    # AGENT REGISTRATION & LIFECYCLE
    # =========================================================================
    
    def register_agent(
        self,
        agent_id: str,
        config: Optional[Dict[str, Any]] = None,
        agent_type: str = "unknown"
    ) -> AgentHealth:
        """
        Register a new agent for health monitoring.
        
        Args:
            agent_id: Unique agent identifier
            config: Agent configuration dict with 'type', 'restart_policy', etc.
            agent_type: Type of agent (if not in config)
            
        Returns:
            AgentHealth object for the registered agent
        """
        config = config or {}
        agent_type = config.get("type", agent_type)
        
        if agent_id in self.agents:
            logger.warning(f"Agent {agent_id} already registered, updating config")
            self.agents[agent_id].agent_type = agent_type
            self.agents[agent_id].metadata.update(config)
            return self.agents[agent_id]
        
        agent_health = AgentHealth(
            agent_id=agent_id,
            agent_type=agent_type,
            status=HealthStatus.STARTING,
            metadata=config,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.agents[agent_id] = agent_health
        self.agent_configs[agent_id] = config
        self.restart_history[agent_id] = []
        
        # Persist to database
        self._persist_agent_health(agent_health)
        
        logger.info(f"Registered agent {agent_id} (type: {agent_type})")
        return agent_health
    
    def unregister_agent(self, agent_id: str, reason: str = "requested") -> bool:
        """
        Unregister an agent from monitoring.
        
        Args:
            agent_id: Agent identifier
            reason: Reason for unregistering
            
        Returns:
            True if successfully unregistered
        """
        if agent_id not in self.agents:
            logger.warning(f"Cannot unregister: agent {agent_id} not found")
            return False
        
        self.agents[agent_id].status = HealthStatus.STOPPING
        self.agents[agent_id].updated_at = datetime.now()
        
        # Persist final state
        self._persist_agent_health(self.agents[agent_id])
        
        # Remove from tracking
        del self.agents[agent_id]
        del self.agent_configs[agent_id]
        if agent_id in self.restart_history:
            del self.restart_history[agent_id]
        
        logger.info(f"Unregistered agent {agent_id} (reason: {reason})")
        return True
    
    def heartbeat(
        self,
        agent_id: str,
        status_data: Optional[Dict[str, Any]] = None
    ) -> Optional[AgentHealth]:
        """
        Record a heartbeat from an agent.
        
        Args:
            agent_id: Agent identifier
            status_data: Optional status data from agent:
                - cpu_percent: CPU usage
                - memory_mb: Memory usage in MB
                - disk_usage_mb: Disk usage in MB
                - response_time_ms: Response time
                - error_count: Error count
                - status: Agent status string
                - metadata: Additional metadata
                
        Returns:
            Updated AgentHealth or None if agent not registered
        """
        if agent_id not in self.agents:
            logger.warning(f"Heartbeat from unregistered agent: {agent_id}")
            return None
        
        status_data = status_data or {}
        agent = self.agents[agent_id]
        
        now = datetime.now()
        
        # Update heartbeat data
        agent.last_heartbeat = now
        agent.heartbeat_count += 1
        agent.updated_at = now
        
        # Update resource metrics if provided
        if "cpu_percent" in status_data:
            agent.cpu_percent = status_data["cpu_percent"]
        if "memory_mb" in status_data:
            agent.memory_mb = status_data["memory_mb"]
        if "disk_usage_mb" in status_data:
            agent.disk_usage_mb = status_data["disk_usage_mb"]
        if "response_time_ms" in status_data:
            # Moving average
            agent.response_time_ms = (
                agent.response_time_ms * 0.7 + status_data["response_time_ms"] * 0.3
            )
        if "error_count" in status_data:
            agent.error_count = status_data["error_count"]
        
        # Update metadata
        if "metadata" in status_data:
            agent.metadata.update(status_data["metadata"])
        
        # Update status if provided
        if "status" in status_data:
            try:
                agent.status = HealthStatus(status_data["status"])
            except ValueError:
                pass
        
        # Calculate uptime
        if agent.last_restart:
            agent.uptime_seconds = (now - agent.last_restart).total_seconds()
        else:
            agent.uptime_seconds = (now - agent.created_at).total_seconds()
        
        # Recalculate health score
        self._calculate_health_score(agent)
        
        # Persist
        self._persist_agent_health(agent)
        
        logger.debug(f"Heartbeat from {agent_id}: score={agent.health_score:.3f}")
        return agent
    
    # =========================================================================
    # HEALTH CHECK & SCORING
    # =========================================================================
    
    def check_health(self, agent_id: Optional[str] = None) -> Union[AgentHealth, Dict[str, Any]]:
        """
        Check health status of an agent or all agents.
        
        Args:
            agent_id: Optional agent ID to check specific agent
            
        Returns:
            AgentHealth for specific agent, or dict with system health summary
        """
        if agent_id:
            if agent_id not in self.agents:
                return None
            return self.agents[agent_id]
        
        # System-wide health check
        total = len(self.agents)
        healthy = sum(1 for a in self.agents.values() if a.status == HealthStatus.HEALTHY)
        degraded = sum(1 for a in self.agents.values() if a.status == HealthStatus.DEGRADED)
        failed = sum(1 for a in self.agents.values() if a.status == HealthStatus.FAILED)
        unknown = total - healthy - degraded - failed
        
        avg_score = sum(a.health_score for a in self.agents.values()) / total if total > 0 else 0.0
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_agents": total,
            "healthy_agents": healthy,
            "degraded_agents": degraded,
            "failed_agents": failed,
            "unknown_agents": unknown,
            "average_health_score": round(avg_score, 3),
            "system_status": self._get_system_status_from_counts(healthy, degraded, failed, total),
            "agents": {aid: a.to_dict() for aid, a in self.agents.items()}
        }
    
    def _calculate_health_score(self, agent: AgentHealth) -> float:
        """
        Calculate health score based on multiple factors.
        
        Factors:
        - Heartbeat recency (40%)
        - Error rate (25%)
        - Resource usage (20%)
        - Response time (15%)
        
        Returns:
            Health score between 0.0 and 1.0
        """
        scores = []
        
        # Heartbeat recency score (40%)
        if agent.last_heartbeat:
            seconds_since = (datetime.now() - agent.last_heartbeat).total_seconds()
            if seconds_since < self.heartbeat_interval:
                heartbeat_score = 1.0
            elif seconds_since < self.heartbeat_interval * self.missed_tolerance:
                heartbeat_score = 1.0 - (seconds_since / (self.heartbeat_interval * self.missed_tolerance)) * 0.5
            else:
                heartbeat_score = 0.0
        else:
            heartbeat_score = 0.5  # Starting up
        scores.append((heartbeat_score, 0.4))
        
        # Error rate score (25%)
        if agent.heartbeat_count > 0:
            error_rate = agent.error_count / agent.heartbeat_count
            error_score = max(0.0, 1.0 - error_rate * 10)  # 10 errors = 0 score
        else:
            error_score = 1.0
        scores.append((error_score, 0.25))
        
        # Resource usage score (20%)
        resource_score = 1.0
        if agent.cpu_percent > 80:
            resource_score -= 0.3
        if agent.memory_mb > 1024:  # 1GB threshold
            resource_score -= 0.2
        if agent.disk_usage_mb > 5120:  # 5GB threshold
            resource_score -= 0.1
        scores.append((max(0.0, resource_score), 0.2))
        
        # Response time score (15%)
        if agent.response_time_ms > 0:
            # Ideal < 100ms, degraded 100-500ms, failed > 500ms
            if agent.response_time_ms < 100:
                response_score = 1.0
            elif agent.response_time_ms < 500:
                response_score = 1.0 - (agent.response_time_ms - 100) / 400 * 0.5
            else:
                response_score = max(0.0, 1.0 - (agent.response_time_ms - 500) / 500)
        else:
            response_score = 1.0
        scores.append((response_score, 0.15))
        
        # Calculate weighted average
        total_score = sum(score * weight for score, weight in scores)
        total_weight = sum(weight for _, weight in scores)
        agent.health_score = total_score / total_weight if total_weight > 0 else 0.0
        
        # Update status based on score
        agent.status = self._score_to_status(agent.health_score)
        
        return agent.health_score
    
    def _score_to_status(self, score: float) -> HealthStatus:
        """Convert health score to status."""
        if score > self.HEALTHY_THRESHOLD:
            return HealthStatus.HEALTHY
        elif score > self.DEGRADED_THRESHOLD:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.FAILED
    
    def _get_system_status_from_counts(
        self, healthy: int, degraded: int, failed: int, total: int
    ) -> str:
        """Determine overall system status from counts."""
        if total == 0:
            return "unknown"
        if failed > total * 0.5:  # More than 50% failed
            return "critical"
        if failed > 0 or degraded > total * 0.3:
            return "degraded"
        if degraded > 0:
            return "warning"
        return "healthy"
    
    # =========================================================================
    # AUTOMATIC RECOVERY
    # =========================================================================
    
    async def restart_failed_agents(self) -> Dict[str, Any]:
        """
        Automatically restart all failed agents.
        
        Returns:
            Dict with restart results
        """
        if not self.auto_restart:
            return {"restarted": [], "skipped": [], "reason": "auto_restart_disabled"}
        
        failed_agents = [
            aid for aid, a in self.agents.items()
            if a.status == HealthStatus.FAILED
        ]
        
        results = {
            "restarted": [],
            "failed": [],
            "skipped": [],
            "timestamp": datetime.now().isoformat()
        }
        
        for agent_id in failed_agents:
            try:
                success = await self.respawn_agent(agent_id)
                if success:
                    results["restarted"].append(agent_id)
                else:
                    results["failed"].append(agent_id)
            except Exception as e:
                logger.error(f"Failed to restart agent {agent_id}: {e}")
                results["failed"].append(agent_id)
        
        logger.info(f"Restart cycle complete: {len(results['restarted'])} restarted, "
                   f"{len(results['failed'])} failed, {len(results['skipped'])} skipped")
        return results
    
    async def respawn_agent(self, agent_id: str) -> bool:
        """
        Respawn a failed agent.
        
        Args:
            agent_id: Agent to respawn
            
        Returns:
            True if respawn successful
        """
        if agent_id not in self.agents:
            logger.error(f"Cannot respawn unknown agent: {agent_id}")
            return False
        
        agent = self.agents[agent_id]
        
        # Check restart limit
        if agent.restart_count >= self.max_restarts:
            logger.error(f"Agent {agent_id} exceeded max restarts ({self.max_restarts})")
            self._generate_alert(
                severity=AlertSeverity.CRITICAL,
                title=f"Agent {agent_id} restart limit exceeded",
                message=f"Agent has been restarted {agent.restart_count} times and will not be restarted again.",
                agent_id=agent_id
            )
            return False
        
        # Check cooldown
        if agent.last_restart:
            seconds_since = (datetime.now() - agent.last_restart).total_seconds()
            if seconds_since < self.restart_cooldown:
                logger.warning(f"Agent {agent_id} in restart cooldown ({seconds_since:.0f}s)")
                return False
        
        logger.info(f"Respawning agent {agent_id} (attempt {agent.restart_count + 1})")
        
        try:
            # Get agent config
            config = self.agent_configs.get(agent_id, {})
            restart_command = config.get("restart_command")
            
            if restart_command:
                # Execute restart command
                proc = await asyncio.create_subprocess_shell(
                    restart_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=60
                )
                
                if proc.returncode != 0:
                    raise RuntimeError(f"Restart command failed: {stderr.decode()}")
            else:
                # No restart command, just reset the agent state
                logger.info(f"No restart command for {agent_id}, resetting state")
            
            # Update agent state
            agent.restart_count += 1
            agent.last_restart = datetime.now()
            agent.status = HealthStatus.STARTING
            agent.health_score = 1.0
            agent.missed_heartbeats = 0
            agent.error_count = 0
            agent.last_error = None
            
            # Track restart history
            if agent_id not in self.restart_history:
                self.restart_history[agent_id] = []
            self.restart_history[agent_id].append(datetime.now())
            
            # Persist
            self._persist_agent_health(agent)
            self._persist_restart(agent_id, "respawn", True)
            
            # Generate alert
            self._generate_alert(
                severity=AlertSeverity.WARNING,
                title=f"Agent {agent_id} restarted",
                message=f"Agent restarted successfully (attempt {agent.restart_count}/{self.max_restarts})",
                agent_id=agent_id
            )
            
            logger.info(f"Agent {agent_id} respawned successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to respawn agent {agent_id}: {e}")
            self._persist_restart(agent_id, str(e), False)
            self._generate_alert(
                severity=AlertSeverity.ERROR,
                title=f"Agent {agent_id} restart failed",
                message=f"Failed to restart agent: {str(e)}",
                agent_id=agent_id
            )
            return False
    
    # =========================================================================
    # ALERTING SYSTEM
    # =========================================================================
    
    def _generate_alert(
        self,
        severity: AlertSeverity,
        title: str,
        message: str,
        agent_id: Optional[str] = None,
        channels: Optional[List[AlertChannel]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Alert:
        """Generate and dispatch an alert."""
        channels = channels or self.alert_channels
        
        alert = Alert(
            alert_id=f"ALT-{uuid.uuid4().hex[:12].upper()}",
            severity=severity,
            channel=AlertChannel.LOG,  # Default, will be overridden per channel
            agent_id=agent_id,
            title=title,
            message=message,
            metadata=metadata or {}
        )
        
        self.alerts.append(alert)
        
        # Persist to database
        self._persist_alert(alert)
        
        # Dispatch to channels
        for channel in channels:
            alert_copy = Alert(
                alert_id=alert.alert_id,
                severity=severity,
                channel=channel,
                agent_id=agent_id,
                title=title,
                message=message,
                metadata=metadata or {}
            )
            for handler in self.alert_handlers.get(channel, []):
                try:
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.create_task(handler(alert_copy))
                    else:
                        handler(alert_copy)
                except Exception as e:
                    logger.error(f"Alert handler error for {channel}: {e}")
        
        return alert
    
    def _log_alert(self, alert: Alert):
        """Log an alert to the logging system."""
        log_message = f"[{alert.severity.value.upper()}] {alert.title}: {alert.message}"
        if alert.agent_id:
            log_message += f" (Agent: {alert.agent_id})"
        
        if alert.severity == AlertSeverity.CRITICAL:
            logger.critical(log_message)
        elif alert.severity == AlertSeverity.ERROR:
            logger.error(log_message)
        elif alert.severity == AlertSeverity.WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    async def _webhook_alert(self, alert: Alert):
        """Send an alert via webhook."""
        if not self.webhook_url or not AIOHTTP_AVAILABLE:
            return
        
        payload = {
            "alert_id": alert.alert_id,
            "severity": alert.severity.value,
            "title": alert.title,
            "message": alert.message,
            "agent_id": alert.agent_id,
            "timestamp": alert.timestamp.isoformat(),
            "metadata": alert.metadata
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status >= 400:
                        logger.error(f"Webhook alert failed: HTTP {response.status}")
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                self._update_alert_in_db(alert)
                logger.info(f"Alert {alert_id} acknowledged")
                return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved."""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                self._update_alert_in_db(alert)
                logger.info(f"Alert {alert_id} resolved")
                return True
        return False
    
    def get_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        agent_id: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 100
    ) -> List[Alert]:
        """Get alerts with optional filtering."""
        alerts = self.alerts
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if agent_id:
            alerts = [a for a in alerts if a.agent_id == agent_id]
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]
        
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)[:limit]
    
    # =========================================================================
    # RESOURCE MONITORING
    # =========================================================================
    
    def get_resource_usage(self) -> Dict[str, Any]:
        """
        Get current resource usage for the system.
        
        Returns:
            Dict with CPU, memory, disk, and network metrics
        """
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": 0.0,
            "memory": {"percent": 0.0, "used_mb": 0.0, "total_mb": 0.0},
            "disk": {"percent": 0.0, "used_gb": 0.0, "total_gb": 0.0},
            "network": {"sent_mb": 0.0, "received_mb": 0.0},
        }
        
        if not PSUTIL_AVAILABLE:
            return metrics
        
        try:
            # CPU
            metrics["cpu_percent"] = psutil.cpu_percent(interval=0.1)
            
            # Memory
            mem = psutil.virtual_memory()
            metrics["memory"] = {
                "percent": mem.percent,
                "used_mb": mem.used / (1024 * 1024),
                "total_mb": mem.total / (1024 * 1024)
            }
            
            # Disk
            disk = psutil.disk_usage('/')
            metrics["disk"] = {
                "percent": disk.percent,
                "used_gb": disk.used / (1024 * 1024 * 1024),
                "total_gb": disk.total / (1024 * 1024 * 1024)
            }
            
            # Network
            net_io = psutil.net_io_counters()
            metrics["network"] = {
                "sent_mb": net_io.bytes_sent / (1024 * 1024),
                "received_mb": net_io.bytes_recv / (1024 * 1024)
            }
            
        except Exception as e:
            logger.error(f"Failed to get resource usage: {e}")
        
        return metrics
    
    def get_agent_resource_usage(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get resource usage for a specific agent (if tracked)."""
        if agent_id not in self.agents:
            return None
        
        agent = self.agents[agent_id]
        return {
            "agent_id": agent_id,
            "cpu_percent": agent.cpu_percent,
            "memory_mb": agent.memory_mb,
            "disk_usage_mb": agent.disk_usage_mb,
            "uptime_seconds": agent.uptime_seconds,
        }
    
    # =========================================================================
    # DASHBOARD DATA
    # =========================================================================
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Get comprehensive dashboard data for the monitoring UI.
        
        Returns:
            Dict with all data needed for the dashboard
        """
        health_summary = self.check_health()
        resources = self.get_resource_usage()
        
        # Agent breakdown by status
        status_breakdown = {
            "healthy": [],
            "degraded": [],
            "failed": [],
            "unknown": [],
            "starting": [],
            "stopping": []
        }
        
        for agent_id, agent in self.agents.items():
            status_breakdown[agent.status.value].append(agent.to_dict())
        
        # Recent alerts
        recent_alerts = [a.to_dict() for a in self.get_alerts(limit=10)]
        
        # Top resource consumers
        top_cpu = sorted(
            self.agents.values(),
            key=lambda a: a.cpu_percent,
            reverse=True
        )[:5]
        
        top_memory = sorted(
            self.agents.values(),
            key=lambda a: a.memory_mb,
            reverse=True
        )[:5]
        
        # Historical metrics (last hour)
        recent_metrics = [m.to_dict() for m in self.system_metrics[-60:]]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "monitoring_active": self._monitoring,
            "uptime_seconds": (
                (datetime.now() - self.start_time).total_seconds()
                if self.start_time else 0
            ),
            "system": health_summary,
            "resources": resources,
            "agents_by_status": status_breakdown,
            "top_cpu_consumers": [a.to_dict() for a in top_cpu],
            "top_memory_consumers": [a.to_dict() for a in top_memory],
            "recent_alerts": recent_alerts,
            "historical_metrics": recent_metrics,
            "configuration": {
                "heartbeat_interval": self.heartbeat_interval,
                "check_interval": self.check_interval,
                "auto_restart": self.auto_restart,
                "max_restarts": self.max_restarts,
                "healthy_threshold": self.HEALTHY_THRESHOLD,
                "degraded_threshold": self.DEGRADED_THRESHOLD,
            }
        }
    
    def get_health_history(self, agent_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get health history for an agent from database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            # Query metrics from system_metrics table
            cursor.execute('''
                SELECT * FROM system_metrics
                WHERE timestamp > ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (since, hours * 6))  # Assuming 10-min intervals
            
            rows = cursor.fetchall()
            conn.close()
            
            return [
                {
                    "timestamp": row[1],
                    "avg_health_score": row[7],
                    "total_restarts": row[8],
                    "total_alerts": row[9],
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Failed to get health history: {e}")
            return []
    
    # =========================================================================
    # BACKGROUND MONITORING
    # =========================================================================
    
    async def start_monitoring(self):
        """Start background monitoring tasks."""
        if self._monitoring:
            logger.warning("Monitoring already active")
            return
        
        self._monitoring = True
        self.start_time = datetime.now()
        
        # Start background tasks
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        if PSUTIL_AVAILABLE:
            self._resource_monitor_task = asyncio.create_task(self._resource_monitor_loop())
        
        logger.info("Health monitoring started")
        
        # Generate startup alert
        self._generate_alert(
            severity=AlertSeverity.INFO,
            title="Health monitoring started",
            message=f"Monitoring {len(self.agents)} agents"
        )
    
    async def stop_monitoring(self):
        """Stop background monitoring tasks."""
        if not self._monitoring:
            return
        
        self._monitoring = False
        
        # Cancel tasks
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        if self._resource_monitor_task:
            self._resource_monitor_task.cancel()
            try:
                await self._resource_monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Health monitoring stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop for heartbeat checking."""
        while self._monitoring:
            try:
                await self._check_missed_heartbeats()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _health_check_loop(self):
        """Health check loop for automatic recovery."""
        while self._monitoring:
            try:
                # Collect system metrics
                await self._collect_system_metrics()
                
                # Auto-restart failed agents
                if self.auto_restart:
                    await self.restart_failed_agents()
                
                await asyncio.sleep(self.check_interval * 6)  # Every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(self.check_interval * 6)
    
    async def _resource_monitor_loop(self):
        """Resource monitoring loop."""
        while self._monitoring:
            try:
                resources = self.get_resource_usage()
                
                # Alert on high resource usage
                if resources["cpu_percent"] > 90:
                    self._generate_alert(
                        severity=AlertSeverity.WARNING,
                        title="High CPU usage",
                        message=f"System CPU usage is {resources['cpu_percent']:.1f}%"
                    )
                
                if resources["memory"]["percent"] > 90:
                    self._generate_alert(
                        severity=AlertSeverity.WARNING,
                        title="High memory usage",
                        message=f"System memory usage is {resources['memory']['percent']:.1f}%"
                    )
                
                if resources["disk"]["percent"] > 90:
                    self._generate_alert(
                        severity=AlertSeverity.ERROR,
                        title="Critical disk usage",
                        message=f"System disk usage is {resources['disk']['percent']:.1f}%"
                    )
                
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Resource monitor loop error: {e}")
                await asyncio.sleep(60)
    
    async def _check_missed_heartbeats(self):
        """Check for agents with missed heartbeats."""
        now = datetime.now()
        
        for agent_id, agent in self.agents.items():
            if agent.status in (HealthStatus.STOPPING, HealthStatus.UNKNOWN):
                continue
            
            if agent.last_heartbeat:
                seconds_since = (now - agent.last_heartbeat).total_seconds()
                expected_intervals = seconds_since / self.heartbeat_interval
                
                if expected_intervals > 1:
                    missed = int(expected_intervals) - 1
                    agent.missed_heartbeats = missed
                    
                    if missed >= self.missed_tolerance:
                        old_status = agent.status
                        agent.status = HealthStatus.FAILED
                        agent.health_score = 0.0
                        agent.last_error = f"Missed {missed} heartbeats"
                        
                        if old_status != HealthStatus.FAILED:
                            self._generate_alert(
                                severity=AlertSeverity.ERROR,
                                title=f"Agent {agent_id} failed",
                                message=f"Agent missed {missed} heartbeats",
                                agent_id=agent_id
                            )
                            
                            self._persist_agent_health(agent)
    
    async def _collect_system_metrics(self):
        """Collect and store system-wide metrics."""
        resources = self.get_resource_usage()
        
        total = len(self.agents)
        healthy = sum(1 for a in self.agents.values() if a.status == HealthStatus.HEALTHY)
        degraded = sum(1 for a in self.agents.values() if a.status == HealthStatus.DEGRADED)
        failed = sum(1 for a in self.agents.values() if a.status == HealthStatus.FAILED)
        unknown = total - healthy - degraded - failed
        
        avg_score = sum(a.health_score for a in self.agents.values()) / total if total > 0 else 0.0
        total_restarts = sum(a.restart_count for a in self.agents.values())
        
        metrics = SystemMetrics(
            timestamp=datetime.now(),
            total_agents=total,
            healthy_agents=healthy,
            degraded_agents=degraded,
            failed_agents=failed,
            unknown_agents=unknown,
            avg_health_score=avg_score,
            total_restarts=total_restarts,
            total_alerts=len([a for a in self.alerts if not a.resolved]),
            cpu_percent=resources["cpu_percent"],
            memory_percent=resources["memory"]["percent"],
            disk_percent=resources["disk"]["percent"],
            network_io_mb=resources["network"]["sent_mb"] + resources["network"]["received_mb"]
        )
        
        self.system_metrics.append(metrics)
        
        # Keep only last 24 hours (assuming 10-min intervals = 144 records)
        if len(self.system_metrics) > 144:
            self.system_metrics = self.system_metrics[-144:]
        
        # Persist to database
        self._persist_system_metrics(metrics)
    
    # =========================================================================
    # DATABASE OPERATIONS
    # =========================================================================
    
    def _persist_agent_health(self, agent: AgentHealth):
        """Save agent health to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO agent_health
                (agent_id, agent_type, status, health_score, last_heartbeat,
                 heartbeat_count, missed_heartbeats, restart_count, last_restart,
                 uptime_seconds, cpu_percent, memory_mb, disk_usage_mb, response_time_ms,
                 error_count, last_error, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                agent.agent_id,
                agent.agent_type,
                agent.status.value,
                agent.health_score,
                agent.last_heartbeat.isoformat() if agent.last_heartbeat else None,
                agent.heartbeat_count,
                agent.missed_heartbeats,
                agent.restart_count,
                agent.last_restart.isoformat() if agent.last_restart else None,
                agent.uptime_seconds,
                agent.cpu_percent,
                agent.memory_mb,
                agent.disk_usage_mb,
                agent.response_time_ms,
                agent.error_count,
                agent.last_error,
                json.dumps(agent.metadata),
                agent.created_at.isoformat(),
                agent.updated_at.isoformat()
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to persist agent health: {e}")
    
    def _persist_alert(self, alert: Alert):
        """Save alert to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO alerts
                (alert_id, severity, channel, agent_id, title, message,
                 timestamp, acknowledged, resolved, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert.alert_id,
                alert.severity.value,
                alert.channel.value,
                alert.agent_id,
                alert.title,
                alert.message,
                alert.timestamp.isoformat(),
                int(alert.acknowledged),
                int(alert.resolved),
                json.dumps(alert.metadata)
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to persist alert: {e}")
    
    def _update_alert_in_db(self, alert: Alert):
        """Update alert status in database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE alerts
                SET acknowledged = ?, resolved = ?
                WHERE alert_id = ?
            ''', (int(alert.acknowledged), int(alert.resolved), alert.alert_id))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to update alert: {e}")
    
    def _persist_system_metrics(self, metrics: SystemMetrics):
        """Save system metrics to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO system_metrics
                (timestamp, total_agents, healthy_agents, degraded_agents,
                 failed_agents, unknown_agents, avg_health_score, total_restarts,
                 total_alerts, cpu_percent, memory_percent, disk_percent, network_io_mb)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metrics.timestamp.isoformat(),
                metrics.total_agents,
                metrics.healthy_agents,
                metrics.degraded_agents,
                metrics.failed_agents,
                metrics.unknown_agents,
                metrics.avg_health_score,
                metrics.total_restarts,
                metrics.total_alerts,
                metrics.cpu_percent,
                metrics.memory_percent,
                metrics.disk_percent,
                metrics.network_io_mb
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to persist system metrics: {e}")
    
    def _persist_restart(self, agent_id: str, reason: str, success: bool):
        """Save restart history to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO restart_history
                (agent_id, restart_time, reason, success)
                VALUES (?, ?, ?, ?)
            ''', (agent_id, datetime.now().isoformat(), reason, int(success)))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to persist restart history: {e}")
    
    # =========================================================================
    # ALERT HANDLER REGISTRATION
    # =========================================================================
    
    def register_alert_handler(
        self,
        channel: AlertChannel,
        handler: Callable[[Alert], Any]
    ):
        """
        Register a custom alert handler for a channel.
        
        Args:
            channel: Alert channel to handle
            handler: Function to call when alert is generated
        """
        if channel not in self.alert_handlers:
            self.alert_handlers[channel] = []
        self.alert_handlers[channel].append(handler)
        logger.info(f"Registered alert handler for {channel.value}")
    
    def set_webhook_url(self, url: str):
        """Set or update the webhook URL for alerts."""
        self.webhook_url = url
        if AlertChannel.WEBHOOK not in self.alert_channels:
            self.alert_channels.append(AlertChannel.WEBHOOK)
        logger.info(f"Webhook URL updated: {url}")


# =============================================================================
# EXAMPLE USAGE & TESTING
# =============================================================================

async def example_usage():
    """Example demonstrating health monitoring capabilities."""
    
    print("=" * 70)
    print("APEX Agent Health Monitor - Example Usage")
    print("=" * 70)
    
    # Initialize health monitor
    monitor = HealthMonitor(
        db_path="/tmp/health_monitor_example.db",
        heartbeat_interval=5,  # 5 seconds for demo
        check_interval=3,
        auto_restart=True,
        max_restarts=3
    )
    
    print("\n--- Registering Agents ---")
    
    # Register some agents
    agents = [
        ("agent_001", "security_scanner", {"restart_command": "echo 'restart agent_001'"}),
        ("agent_002", "code_generator", {"restart_command": "echo 'restart agent_002'"}),
        ("agent_003", "performance_profiler", {"restart_command": "echo 'restart agent_003'"}),
    ]
    
    for agent_id, agent_type, config in agents:
        health = monitor.register_agent(agent_id, config, agent_type)
        print(f"Registered: {agent_id} (type: {agent_type})")
    
    print("\n--- Starting Monitoring ---")
    await monitor.start_monitoring()
    
    print("\n--- Simulating Heartbeats ---")
    
    # Simulate heartbeats
    for i in range(3):
        for agent_id, _, _ in agents:
            status_data = {
                "cpu_percent": 20.0 + i * 5,
                "memory_mb": 100.0 + i * 10,
                "response_time_ms": 50.0 + i * 5,
                "status": "healthy"
            }
            monitor.heartbeat(agent_id, status_data)
            print(f"Heartbeat from {agent_id}")
        await asyncio.sleep(1)
    
    print("\n--- Checking Health ---")
    
    # Check health
    health = monitor.check_health()
    print(f"Total agents: {health['total_agents']}")
    print(f"Healthy: {health['healthy_agents']}")
    print(f"Average health score: {health['average_health_score']:.3f}")
    print(f"System status: {health['system_status']}")
    
    print("\n--- Simulating Agent Failure ---")
    
    # Stop sending heartbeats from one agent to simulate failure
    print("Stopping heartbeats from agent_002...")
    await asyncio.sleep(12)  # Wait for missed heartbeats
    
    # Check health again
    health = monitor.check_health()
    print(f"\nAfter failure:")
    print(f"Failed agents: {health['failed_agents']}")
    print(f"System status: {health['system_status']}")
    
    print("\n--- Dashboard Data ---")
    
    # Get dashboard data
    dashboard = monitor.get_dashboard_data()
    print(f"Monitoring active: {dashboard['monitoring_active']}")
    print(f"Total agents: {dashboard['system']['total_agents']}")
    print(f"Recent alerts: {len(dashboard['recent_alerts'])}")
    
    print("\n--- Alerts ---")
    
    # Get alerts
    alerts = monitor.get_alerts(limit=5)
    for alert in alerts:
        print(f"[{alert.severity.value.upper()}] {alert.title}")
    
    print("\n--- Resource Usage ---")
    
    # Get resource usage
    resources = monitor.get_resource_usage()
    print(f"CPU: {resources['cpu_percent']:.1f}%")
    print(f"Memory: {resources['memory']['percent']:.1f}%")
    print(f"Disk: {resources['disk']['percent']:.1f}%")
    
    print("\n--- Stopping Monitoring ---")
    await monitor.stop_monitoring()
    
    # Cleanup
    try:
        os.remove("/tmp/health_monitor_example.db")
    except:
        pass
    
    print("\n" + "=" * 70)
    print("Example complete!")
    print("=" * 70)


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())
