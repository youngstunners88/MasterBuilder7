#!/usr/bin/env python3
"""
APEX Integration Layer - Main Orchestration Hub
===============================================

The APEXIntegration class serves as the single entry point for all APEX operations,
tying together infrastructure components (Redis, PostgreSQL, Git, Kimi API, n8n)
with the agent layer.

Features:
- Unified initialization of all components
- Health monitoring with graceful degradation
- Circuit breakers and retry logic
- Event wiring between layers
- Distributed tracing and metrics
- Three-tier checkpoint management
- A/B testing integration
- Pattern database access

Author: APEX Core Team
Version: 2.0.0
License: MIT
"""

import os
import sys
import json
import yaml
import asyncio
import logging
import hashlib
import time
import uuid
import sqlite3
from typing import Dict, List, Any, Optional, Callable, Union, Tuple, AsyncGenerator
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from contextlib import asynccontextmanager
from collections import defaultdict
import threading
import traceback

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | [%(filename)s:%(lineno)d] | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/apex_integration.log')
    ]
)
logger = logging.getLogger('APEXIntegration')

# =============================================================================
# COMPONENT IMPORTS WITH GRACEFUL FALLBACK
# =============================================================================

# Infrastructure components
try:
    from infrastructure.redis_manager import RedisManager, RedisConfig, CheckpointData
    REDIS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"RedisManager not available: {e}")
    REDIS_AVAILABLE = False
    RedisManager = None
    RedisConfig = None
    CheckpointData = None

try:
    from infrastructure.postgres_manager import PostgresManager, Checkpoint, AgentState
    POSTGRES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"PostgresManager not available: {e}")
    POSTGRES_AVAILABLE = False
    PostgresManager = None
    Checkpoint = None
    AgentState = None

try:
    from infrastructure.git_manager import GitManager, CheckpointMetadata, CheckpointTier
    GIT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"GitManager not available: {e}")
    GIT_AVAILABLE = False
    GitManager = None
    CheckpointMetadata = None
    CheckpointTier = None

try:
    from infrastructure.kimi_client import KimiClient, ExecutionResult, AgentSpec, ErrorType
    KIMI_AVAILABLE = True
except ImportError as e:
    logger.warning(f"KimiClient not available: {e}")
    KIMI_AVAILABLE = False
    KimiClient = None
    ExecutionResult = None
    AgentSpec = None

try:
    from infrastructure.n8n_integration import N8NIntegration, WorkflowType, WebhookEventType
    N8N_AVAILABLE = True
except ImportError as e:
    logger.warning(f"N8NIntegration not available: {e}")
    N8N_AVAILABLE = False
    N8NIntegration = None
    WorkflowType = None
    WebhookEventType = None

# Evolution components
try:
    from evolution.pattern_database import PatternDatabase, Pattern, PatternType, SearchResult
    PATTERN_DB_AVAILABLE = True
except ImportError as e:
    logger.warning(f"PatternDatabase not available: {e}")
    PATTERN_DB_AVAILABLE = False
    PatternDatabase = None
    Pattern = None
    PatternType = None
    SearchResult = None

try:
    from evolution.ab_testing import ABTestFramework, ABTest, TestStatus, Variant
    AB_TEST_AVAILABLE = True
except ImportError as e:
    logger.warning(f"ABTestFramework not available: {e}")
    AB_TEST_AVAILABLE = False
    ABTestFramework = None
    ABTest = None
    TestStatus = None

# Agent layer
try:
    from agent_layer import AgentLayer, BuildContext, BuildStage
    AGENT_LAYER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AgentLayer not available: {e}")
    AGENT_LAYER_AVAILABLE = False
    AgentLayer = None
    BuildContext = None
    BuildStage = None

# Skills
try:
    sys.path.insert(0, '/home/teacherchris37/MasterBuilder7/skills/paystack-security-agent')
    from paystack_security_agent import PaystackSecurityAgent
    SECURITY_AGENT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"PaystackSecurityAgent not available: {e}")
    SECURITY_AGENT_AVAILABLE = False
    PaystackSecurityAgent = None

try:
    sys.path.insert(0, '/home/teacherchris37/MasterBuilder7/skills/ai-route-optimizer')
    from ai_route_optimizer import AIRouteOptimizer
    ROUTE_OPTIMIZER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AIRouteOptimizer not available: {e}")
    ROUTE_OPTIMIZER_AVAILABLE = False
    AIRouteOptimizer = None

try:
    sys.path.insert(0, '/home/teacherchris37/MasterBuilder7/skills/reward-verification-agent')
    from reward_verification_agent import RewardVerificationAgent
    REWARD_AGENT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"RewardVerificationAgent not available: {e}")
    REWARD_AGENT_AVAILABLE = False
    RewardVerificationAgent = None


# =============================================================================
# DATA CLASSES AND ENUMS
# =============================================================================

class ServiceStatus(Enum):
    """Status of a service/component"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class ComponentHealth:
    """Health status of a component"""
    name: str
    status: ServiceStatus
    latency_ms: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_check: datetime = field(default_factory=datetime.utcnow)


@dataclass
class IntegrationMetrics:
    """Collected metrics for the integration layer"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    checkpoint_count: int = 0
    agent_executions: int = 0
    workflow_triggers: int = 0
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def average_latency_ms(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_latency_ms / self.total_requests


@dataclass
class CheckpointResult:
    """Result of creating a checkpoint across all tiers"""
    checkpoint_id: str
    tier1_success: bool
    tier2_success: bool
    tier3_success: bool
    redis_id: Optional[str] = None
    postgres_id: Optional[str] = None
    git_commit_hash: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def all_tiers_success(self) -> bool:
        return self.tier1_success and self.tier2_success and self.tier3_success


@dataclass
class APEXConfig:
    """Configuration for APEX Integration"""
    # Redis Configuration
    redis_url: Optional[str] = None
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0
    
    # PostgreSQL Configuration
    postgres_url: Optional[str] = None
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "apex"
    postgres_password: str = "apex"
    postgres_db: str = "apex"
    
    # Git Configuration
    git_repo_path: str = "/tmp/apex_checkpoints"
    git_user_name: str = "APEX Integration"
    git_user_email: str = "apex@masterbuilder7.local"
    git_signing_key: Optional[str] = None
    
    # Kimi API Configuration
    kimi_api_key: Optional[str] = None
    kimi_base_url: str = "https://api.moonshot.cn/v1"
    kimi_timeout: int = 120
    kimi_max_retries: int = 3
    
    # n8n Configuration
    n8n_base_url: str = "http://localhost:5678"
    n8n_api_key: Optional[str] = None
    n8n_webhook_secret: Optional[str] = None
    
    # Pattern Database Configuration
    pattern_db_path: str = "./pattern_vectors"
    pattern_sqlite_path: str = "/tmp/pattern_db.sqlite"
    enable_chroma: bool = True
    
    # A/B Testing Configuration
    ab_test_postgres_dsn: str = "postgresql://localhost/ab_testing"
    ab_test_redis_url: str = "redis://localhost:6379"
    
    # Feature Flags
    enable_redis: bool = True
    enable_postgres: bool = True
    enable_git: bool = True
    enable_kimi: bool = True
    enable_n8n: bool = True
    enable_pattern_db: bool = True
    enable_ab_testing: bool = True
    enable_mock_mode: bool = False
    
    # Circuit Breaker Configuration
    circuit_failure_threshold: int = 5
    circuit_recovery_timeout: float = 30.0
    
    @classmethod
    def from_env(cls) -> 'APEXConfig':
        """Load configuration from environment variables"""
        return cls(
            redis_url=os.getenv('REDIS_URL'),
            redis_host=os.getenv('REDIS_HOST', 'localhost'),
            redis_port=int(os.getenv('REDIS_PORT', '6379')),
            redis_password=os.getenv('REDIS_PASSWORD'),
            redis_db=int(os.getenv('REDIS_DB', '0')),
            
            postgres_url=os.getenv('DATABASE_URL'),
            postgres_host=os.getenv('POSTGRES_HOST', 'localhost'),
            postgres_port=int(os.getenv('POSTGRES_PORT', '5432')),
            postgres_user=os.getenv('POSTGRES_USER', 'apex'),
            postgres_password=os.getenv('POSTGRES_PASSWORD', 'apex'),
            postgres_db=os.getenv('POSTGRES_DB', 'apex'),
            
            git_repo_path=os.getenv('CHECKPOINTS_REPO_PATH', '/tmp/apex_checkpoints'),
            git_user_name=os.getenv('GIT_USER_NAME', 'APEX Integration'),
            git_user_email=os.getenv('GIT_USER_EMAIL', 'apex@masterbuilder7.local'),
            git_signing_key=os.getenv('GIT_SIGNING_KEY'),
            
            kimi_api_key=os.getenv('KIMI_API_KEY'),
            kimi_base_url=os.getenv('KIMI_BASE_URL', 'https://api.moonshot.cn/v1'),
            kimi_timeout=int(os.getenv('KIMI_TIMEOUT', '120')),
            kimi_max_retries=int(os.getenv('KIMI_MAX_RETRIES', '3')),
            
            n8n_base_url=os.getenv('N8N_BASE_URL', 'http://localhost:5678'),
            n8n_api_key=os.getenv('N8N_API_KEY'),
            n8n_webhook_secret=os.getenv('WEBHOOK_SECRET'),
            
            enable_mock_mode=os.getenv('APEX_MOCK_MODE', 'false').lower() == 'true'
        )
    
    @classmethod
    def from_file(cls, filepath: str) -> 'APEXConfig':
        """Load configuration from JSON or YAML file"""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {filepath}")
        
        with open(path, 'r') as f:
            if path.suffix in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
        
        return cls(**data)


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

class CircuitBreaker:
    """Circuit breaker pattern for external service resilience"""
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = threading.Lock()
        
        logger.debug(f"Circuit breaker initialized: {name}")
    
    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._last_failure_time:
                    elapsed = time.time() - self._last_failure_time
                    if elapsed >= self.recovery_timeout:
                        self._state = CircuitState.HALF_OPEN
                        self._half_open_calls = 0
                        logger.info(f"Circuit {self.name} entering HALF_OPEN state")
            return self._state
    
    def record_success(self):
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1
                self._success_count += 1
                if self._half_open_calls >= self.half_open_max_calls:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    logger.info(f"Circuit {self.name} CLOSED (recovered)")
            else:
                self._failure_count = 0
                self._success_count += 1
    
    def record_failure(self):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                logger.warning(f"Circuit {self.name} OPEN (recovery failed)")
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(f"Circuit {self.name} OPEN ({self._failure_count} failures)")
    
    def can_execute(self) -> bool:
        state = self.state
        if state == CircuitState.CLOSED:
            return True
        elif state == CircuitState.HALF_OPEN:
            with self._lock:
                return self._half_open_calls < self.half_open_max_calls
        return False
    
    async def execute(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation with circuit breaker protection"""
        if not self.can_execute():
            raise Exception(f"Circuit breaker {self.name} is OPEN")
        
        try:
            if asyncio.iscoroutinefunction(operation):
                result = await operation(*args, **kwargs)
            else:
                result = operation(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise


# =============================================================================
# METRICS COLLECTOR
# =============================================================================

class MetricsCollector:
    """Collect and aggregate metrics for observability"""
    
    def __init__(self):
        self.metrics = IntegrationMetrics()
        self._latency_history: List[float] = []
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()
    
    def record_request(self, success: bool, latency_ms: float):
        with self._lock:
            self.metrics.total_requests += 1
            self.metrics.total_latency_ms += latency_ms
            if success:
                self.metrics.successful_requests += 1
            else:
                self.metrics.failed_requests += 1
            self._latency_history.append(latency_ms)
            # Keep last 1000 entries
            if len(self._latency_history) > 1000:
                self._latency_history = self._latency_history[-1000:]
    
    def record_cache_hit(self):
        with self._lock:
            self.metrics.cache_hits += 1
    
    def record_cache_miss(self):
        with self._lock:
            self.metrics.cache_misses += 1
    
    def record_error(self, error_type: str):
        with self._lock:
            self._error_counts[error_type] += 1
    
    def record_checkpoint(self):
        with self._lock:
            self.metrics.checkpoint_count += 1
    
    def record_agent_execution(self):
        with self._lock:
            self.metrics.agent_executions += 1
    
    def record_workflow_trigger(self):
        with self._lock:
            self.metrics.workflow_triggers += 1
    
    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'total_requests': self.metrics.total_requests,
                'success_rate': self.metrics.success_rate,
                'average_latency_ms': self.metrics.average_latency_ms,
                'cache_hit_rate': self.metrics.cache_hits / max(1, self.metrics.cache_hits + self.metrics.cache_misses),
                'checkpoint_count': self.metrics.checkpoint_count,
                'agent_executions': self.metrics.agent_executions,
                'workflow_triggers': self.metrics.workflow_triggers,
                'error_counts': dict(self._error_counts),
                'p99_latency_ms': self._calculate_percentile(99) if self._latency_history else 0
            }
    
    def _calculate_percentile(self, percentile: int) -> float:
        if not self._latency_history:
            return 0.0
        sorted_latencies = sorted(self._latency_history)
        index = int(len(sorted_latencies) * percentile / 100)
        return sorted_latencies[min(index, len(sorted_latencies) - 1)]


# =============================================================================
# MAIN INTEGRATION CLASS
# =============================================================================

class APEXIntegration:
    """
    Main integration layer for APEX - single entry point for all operations.
    
    Manages:
    - RedisManager (Tier 1 checkpoints)
    - PostgresManager (Tier 2 checkpoints)
    - GitManager (Tier 3 checkpoints)
    - KimiClient (agent execution)
    - N8NIntegration (workflow automation)
    - PatternDatabase (pattern storage)
    - ABTestFramework (experimentation)
    
    Usage:
        config = APEXConfig.from_env()
        apex = APEXIntegration(config)
        await apex.initialize()
        
        # Execute build
        result = await apex.execute_build("/path/to/project", {"name": "my-project"})
        
        # Cleanup
        await apex.shutdown()
    """
    
    def __init__(self, config: Optional[APEXConfig] = None):
        """
        Initialize APEX Integration Layer
        
        Args:
            config: Configuration object. If None, loads from environment.
        """
        self.config = config or APEXConfig.from_env()
        self.metrics = MetricsCollector()
        
        # Component instances
        self.redis: Optional[RedisManager] = None
        self.postgres: Optional[PostgresManager] = None
        self.git: Optional[GitManager] = None
        self.kimi: Optional[KimiClient] = None
        self.n8n: Optional[N8NIntegration] = None
        self.pattern_db: Optional[PatternDatabase] = None
        self.ab_test: Optional[Any] = None
        self.agent_layer: Optional[AgentLayer] = None
        
        # Skill agents
        self.security_agent: Optional[Any] = None
        self.route_optimizer: Optional[Any] = None
        self.reward_verifier: Optional[Any] = None
        
        # Circuit breakers
        self._circuits: Dict[str, CircuitBreaker] = {}
        
        # Event handlers
        self._event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        
        # State
        self._initialized = False
        self._health_status: Dict[str, ComponentHealth] = {}
        self._lock = asyncio.Lock()
        
        logger.info("APEXIntegration created")
    
    # =========================================================================
    # INITIALIZATION
    # =========================================================================
    
    async def initialize(self) -> bool:
        """
        Initialize all components with graceful degradation
        
        Returns:
            True if initialization completed (even with some degraded services)
        """
        logger.info("Initializing APEX Integration Layer...")
        
        async with self._lock:
            try:
                # Initialize circuit breakers
                await self._init_circuits()
                
                # Initialize Redis (Tier 1)
                if self.config.enable_redis and REDIS_AVAILABLE:
                    await self._init_redis()
                else:
                    self._health_status['redis'] = ComponentHealth(
                        name='redis',
                        status=ServiceStatus.DISABLED,
                        latency_ms=0.0
                    )
                
                # Initialize PostgreSQL (Tier 2)
                if self.config.enable_postgres and POSTGRES_AVAILABLE:
                    await self._init_postgres()
                else:
                    self._health_status['postgres'] = ComponentHealth(
                        name='postgres',
                        status=ServiceStatus.DISABLED,
                        latency_ms=0.0
                    )
                
                # Initialize Git (Tier 3)
                if self.config.enable_git and GIT_AVAILABLE:
                    await self._init_git()
                else:
                    self._health_status['git'] = ComponentHealth(
                        name='git',
                        status=ServiceStatus.DISABLED,
                        latency_ms=0.0
                    )
                
                # Initialize Kimi API
                if self.config.enable_kimi and KIMI_AVAILABLE:
                    await self._init_kimi()
                else:
                    self._health_status['kimi'] = ComponentHealth(
                        name='kimi',
                        status=ServiceStatus.DISABLED,
                        latency_ms=0.0
                    )
                
                # Initialize n8n
                if self.config.enable_n8n and N8N_AVAILABLE:
                    await self._init_n8n()
                else:
                    self._health_status['n8n'] = ComponentHealth(
                        name='n8n',
                        status=ServiceStatus.DISABLED,
                        latency_ms=0.0
                    )
                
                # Initialize Pattern Database
                if self.config.enable_pattern_db and PATTERN_DB_AVAILABLE:
                    await self._init_pattern_db()
                else:
                    self._health_status['pattern_db'] = ComponentHealth(
                        name='pattern_db',
                        status=ServiceStatus.DISABLED,
                        latency_ms=0.0
                    )
                
                # Initialize A/B Testing
                if self.config.enable_ab_testing and AB_TEST_AVAILABLE:
                    await self._init_ab_testing()
                else:
                    self._health_status['ab_testing'] = ComponentHealth(
                        name='ab_testing',
                        status=ServiceStatus.DISABLED,
                        latency_ms=0.0
                    )
                
                # Initialize Agent Layer
                if AGENT_LAYER_AVAILABLE:
                    await self._init_agent_layer()
                
                # Initialize Skill Agents
                await self._init_skill_agents()
                
                # Wire events
                await self._wire_events()
                
                self._initialized = True
                
                healthy_count = sum(
                    1 for h in self._health_status.values()
                    if h.status == ServiceStatus.HEALTHY
                )
                total_count = len(self._health_status)
                
                logger.info(
                    f"APEX Integration initialized: "
                    f"{healthy_count}/{total_count} components healthy"
                )
                
                return True
                
            except Exception as e:
                logger.error(f"Initialization failed: {e}")
                logger.error(traceback.format_exc())
                return False
    
    async def _init_circuits(self):
        """Initialize circuit breakers for external services"""
        services = ['redis', 'postgres', 'git', 'kimi', 'n8n', 'pattern_db']
        for service in services:
            self._circuits[service] = CircuitBreaker(
                name=service,
                failure_threshold=self.config.circuit_failure_threshold,
                recovery_timeout=self.config.circuit_recovery_timeout
            )
        logger.debug("Circuit breakers initialized")
    
    async def _init_redis(self):
        """Initialize Redis connection"""
        try:
            start = time.time()
            
            redis_config = RedisConfig(
                url=self.config.redis_url,
                host=self.config.redis_host,
                port=self.config.redis_port,
                password=self.config.redis_password,
                db=self.config.redis_db
            )
            
            self.redis = RedisManager(redis_config)
            connected = await self.redis.connect()
            
            latency = (time.time() - start) * 1000
            
            if connected:
                self._health_status['redis'] = ComponentHealth(
                    name='redis',
                    status=ServiceStatus.HEALTHY,
                    latency_ms=latency
                )
                logger.info(f"Redis connected ({latency:.2f}ms)")
            else:
                self._health_status['redis'] = ComponentHealth(
                    name='redis',
                    status=ServiceStatus.DEGRADED,
                    latency_ms=latency,
                    error="Using SQLite fallback"
                )
                logger.warning("Redis using SQLite fallback")
                
        except Exception as e:
            self._health_status['redis'] = ComponentHealth(
                name='redis',
                status=ServiceStatus.UNAVAILABLE,
                latency_ms=0.0,
                error=str(e)
            )
            logger.error(f"Redis initialization failed: {e}")
    
    async def _init_postgres(self):
        """Initialize PostgreSQL connection"""
        try:
            start = time.time()
            
            if self.config.postgres_url:
                db_url = self.config.postgres_url
            else:
                db_url = (
                    f"postgresql://{self.config.postgres_user}:{self.config.postgres_password}"
                    f"@{self.config.postgres_host}:{self.config.postgres_port}"
                    f"/{self.config.postgres_db}"
                )
            
            self.postgres = PostgresManager(database_url=db_url)
            await self.postgres.connect()
            
            health = await self.postgres.health_check()
            latency = (time.time() - start) * 1000
            
            self._health_status['postgres'] = ComponentHealth(
                name='postgres',
                status=ServiceStatus.HEALTHY if health.is_healthy else ServiceStatus.DEGRADED,
                latency_ms=health.latency_ms,
                metadata={
                    'total_connections': health.total_connections,
                    'free_connections': health.free_connections
                }
            )
            logger.info(f"PostgreSQL connected ({health.latency_ms:.2f}ms)")
            
        except Exception as e:
            self._health_status['postgres'] = ComponentHealth(
                name='postgres',
                status=ServiceStatus.UNAVAILABLE,
                latency_ms=0.0,
                error=str(e)
            )
            logger.error(f"PostgreSQL initialization failed: {e}")
    
    async def _init_git(self):
        """Initialize Git repository"""
        try:
            start = time.time()
            
            self.git = GitManager(
                repo_path=self.config.git_repo_path,
                user_name=self.config.git_user_name,
                user_email=self.config.git_user_email,
                signing_key=self.config.git_signing_key
            )
            
            # Initialize repo if it doesn't exist
            if not Path(self.config.git_repo_path).exists():
                await self.git.init_repo()
            else:
                await self.git.open_repo()
            
            latency = (time.time() - start) * 1000
            
            self._health_status['git'] = ComponentHealth(
                name='git',
                status=ServiceStatus.HEALTHY,
                latency_ms=latency,
                metadata={'repo_path': self.config.git_repo_path}
            )
            logger.info(f"Git initialized ({latency:.2f}ms)")
            
        except Exception as e:
            self._health_status['git'] = ComponentHealth(
                name='git',
                status=ServiceStatus.UNAVAILABLE,
                latency_ms=0.0,
                error=str(e)
            )
            logger.error(f"Git initialization failed: {e}")
    
    async def _init_kimi(self):
        """Initialize Kimi API client"""
        try:
            start = time.time()
            
            self.kimi = KimiClient(
                api_key=self.config.kimi_api_key,
                base_url=self.config.kimi_base_url,
                timeout=self.config.kimi_timeout,
                max_retries=self.config.kimi_max_retries
            )
            
            health = await self.kimi.health_check()
            latency = (time.time() - start) * 1000
            
            if health['status'] == 'healthy':
                self._health_status['kimi'] = ComponentHealth(
                    name='kimi',
                    status=ServiceStatus.HEALTHY,
                    latency_ms=health.get('latency_ms', latency),
                    metadata={'available_models': health.get('available_models', 0)}
                )
                logger.info(f"Kimi API connected ({health.get('latency_ms', latency):.2f}ms)")
            else:
                raise Exception(health.get('error', 'Unknown error'))
                
        except Exception as e:
            self._health_status['kimi'] = ComponentHealth(
                name='kimi',
                status=ServiceStatus.UNAVAILABLE,
                latency_ms=0.0,
                error=str(e)
            )
            logger.error(f"Kimi API initialization failed: {e}")
    
    async def _init_n8n(self):
        """Initialize n8n integration"""
        try:
            start = time.time()
            
            self.n8n = N8NIntegration(
                base_url=self.config.n8n_base_url,
                api_key=self.config.n8n_api_key,
                webhook_secret=self.config.n8n_webhook_secret
            )
            
            latency = (time.time() - start) * 1000
            
            self._health_status['n8n'] = ComponentHealth(
                name='n8n',
                status=ServiceStatus.HEALTHY,
                latency_ms=latency
            )
            logger.info(f"n8n integration initialized ({latency:.2f}ms)")
            
        except Exception as e:
            self._health_status['n8n'] = ComponentHealth(
                name='n8n',
                status=ServiceStatus.UNAVAILABLE,
                latency_ms=0.0,
                error=str(e)
            )
            logger.error(f"n8n initialization failed: {e}")
    
    async def _init_pattern_db(self):
        """Initialize Pattern Database"""
        try:
            start = time.time()
            
            self.pattern_db = PatternDatabase(
                vector_store_path=self.config.pattern_db_path,
                sqlite_path=self.config.pattern_sqlite_path,
                redis_url=self.config.redis_url,
                enable_chroma=self.config.enable_chroma
            )
            
            await self.pattern_db.connect()
            
            latency = (time.time() - start) * 1000
            
            self._health_status['pattern_db'] = ComponentHealth(
                name='pattern_db',
                status=ServiceStatus.HEALTHY,
                latency_ms=latency
            )
            logger.info(f"Pattern Database initialized ({latency:.2f}ms)")
            
        except Exception as e:
            self._health_status['pattern_db'] = ComponentHealth(
                name='pattern_db',
                status=ServiceStatus.UNAVAILABLE,
                latency_ms=0.0,
                error=str(e)
            )
            logger.error(f"Pattern Database initialization failed: {e}")
    
    async def _init_ab_testing(self):
        """Initialize A/B Testing Framework"""
        try:
            start = time.time()
            
            # Note: ABTestFramework may need to be initialized differently
            # This is a placeholder - adjust based on actual implementation
            self.ab_test = None  # Will be initialized when needed
            
            latency = (time.time() - start) * 1000
            
            self._health_status['ab_testing'] = ComponentHealth(
                name='ab_testing',
                status=ServiceStatus.HEALTHY,
                latency_ms=latency
            )
            logger.info(f"A/B Testing initialized ({latency:.2f}ms)")
            
        except Exception as e:
            self._health_status['ab_testing'] = ComponentHealth(
                name='ab_testing',
                status=ServiceStatus.UNAVAILABLE,
                latency_ms=0.0,
                error=str(e)
            )
            logger.error(f"A/B Testing initialization failed: {e}")
    
    async def _init_agent_layer(self):
        """Initialize Agent Layer"""
        try:
            self.agent_layer = AgentLayer(max_budget_usd=500.0)
            self.agent_layer.initialize()
            logger.info("Agent Layer initialized")
        except Exception as e:
            logger.error(f"Agent Layer initialization failed: {e}")
    
    async def _init_skill_agents(self):
        """Initialize specialized skill agents"""
        # Security Agent
        if SECURITY_AGENT_AVAILABLE:
            try:
                self.security_agent = PaystackSecurityAgent()
                logger.info("Paystack Security Agent initialized")
            except Exception as e:
                logger.warning(f"Security Agent initialization failed: {e}")
        
        # Route Optimizer
        if ROUTE_OPTIMIZER_AVAILABLE:
            try:
                self.route_optimizer = AIRouteOptimizer()
                logger.info("AI Route Optimizer initialized")
            except Exception as e:
                logger.warning(f"Route Optimizer initialization failed: {e}")
        
        # Reward Verifier
        if REWARD_AGENT_AVAILABLE:
            try:
                self.reward_verifier = RewardVerificationAgent()
                logger.info("Reward Verification Agent initialized")
            except Exception as e:
                logger.warning(f"Reward Verifier initialization failed: {e}")
    
    async def _wire_events(self):
        """Wire events between components"""
        if self.n8n:
            # Wire agent layer events to n8n
            if self.agent_layer:
                self.agent_layer.events.on('checkpoint_created', 
                    lambda data: self._on_checkpoint_created(data))
                self.agent_layer.events.on('consensus_reached', 
                    lambda data: self._on_consensus_reached(data))
                self.agent_layer.events.on('evaluation_complete', 
                    lambda data: self._on_evaluation_complete(data))
        
        logger.debug("Events wired")
    
    # =========================================================================
    # HEALTH CHECK
    # =========================================================================
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of all services
        
        Returns:
            Health status report with all component statuses
        """
        if not self._initialized:
            return {'status': 'not_initialized', 'components': {}}
        
        # Update health statuses
        for name, circuit in self._circuits.items():
            if name in self._health_status:
                health = self._health_status[name]
                if circuit.state == CircuitState.OPEN:
                    health.status = ServiceStatus.DEGRADED
                    health.error = "Circuit breaker OPEN"
        
        # Count statuses
        healthy = sum(1 for h in self._health_status.values() if h.status == ServiceStatus.HEALTHY)
        degraded = sum(1 for h in self._health_status.values() if h.status == ServiceStatus.DEGRADED)
        unavailable = sum(1 for h in self._health_status.values() if h.status == ServiceStatus.UNAVAILABLE)
        disabled = sum(1 for h in self._health_status.values() if h.status == ServiceStatus.DISABLED)
        
        overall_status = 'healthy' if healthy == len(self._health_status) else \
                        'degraded' if degraded > 0 else \
                        'unavailable' if unavailable > 0 else 'unknown'
        
        return {
            'status': overall_status,
            'timestamp': datetime.utcnow().isoformat(),
            'summary': {
                'healthy': healthy,
                'degraded': degraded,
                'unavailable': unavailable,
                'disabled': disabled,
                'total': len(self._health_status)
            },
            'components': {
                name: {
                    'status': health.status.value,
                    'latency_ms': health.latency_ms,
                    'error': health.error,
                    'metadata': health.metadata,
                    'last_check': health.last_check.isoformat() if health.last_check else None
                }
                for name, health in self._health_status.items()
            },
            'metrics': self.metrics.get_summary()
        }
    
    # =========================================================================
    # UNIFIED WORKFLOW METHODS
    # =========================================================================
    
    async def execute_build(
        self,
        project_path: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute end-to-end build workflow
        
        Args:
            project_path: Path to project directory
            config: Build configuration (name, stack, etc.)
            
        Returns:
            Build results with all stage outputs
        """
        start_time = time.time()
        build_id = f"build-{uuid.uuid4().hex[:8]}"
        project_name = config.get('name', 'unnamed-project')
        
        logger.info(f"Starting build {build_id} for {project_name}")
        
        try:
            # Create initial checkpoint
            await self.create_checkpoint(build_id, 'build_start', {
                'project_path': project_path,
                'config': config
            })
            
            results = {
                'build_id': build_id,
                'project_name': project_name,
                'stages': {}
            }
            
            # Stage 1: Analysis
            if self.agent_layer:
                analysis = await self.agent_layer.analyze_project(project_path, project_name)
                results['stages']['analysis'] = analysis
                await self.create_checkpoint(build_id, 'analysis_complete', analysis)
            
            # Stage 2: Planning
            if self.agent_layer:
                plan = await self.agent_layer.plan_architecture(project_name, analysis)
                results['stages']['planning'] = plan
                await self.create_checkpoint(build_id, 'planning_complete', plan)
            
            # Stage 3: Build (Frontend/Backend)
            if self.agent_layer:
                build_context = BuildContext(
                    build_id=build_id,
                    project_path=project_path,
                    project_name=project_name,
                    stack_detected=analysis.get('stack_detection', {})
                )
                
                # Frontend
                frontend_result = await self.agent_layer.build_frontend(build_context, plan)
                results['stages']['frontend'] = frontend_result
                await self.create_checkpoint(build_id, 'frontend_complete', frontend_result)
                
                # Backend
                backend_result = await self.agent_layer.build_backend(build_context, plan)
                results['stages']['backend'] = backend_result
                await self.create_checkpoint(build_id, 'backend_complete', backend_result)
                
                # Testing
                test_result = await self.agent_layer.run_tests(
                    build_context, frontend_result, backend_result
                )
                results['stages']['testing'] = test_result
                await self.create_checkpoint(build_id, 'testing_complete', test_result)
            
            # Final checkpoint
            results['duration_seconds'] = time.time() - start_time
            await self.create_checkpoint(build_id, 'build_complete', results)
            
            # Trigger n8n workflow if available
            if self.n8n:
                await self.n8n.trigger_workflow(
                    'apex-build-complete',
                    {'build_id': build_id, 'results': results}
                )
            
            self.metrics.record_request(success=True, latency_ms=(time.time() - start_time) * 1000)
            
            logger.info(f"Build {build_id} completed in {results['duration_seconds']:.2f}s")
            return results
            
        except Exception as e:
            logger.error(f"Build {build_id} failed: {e}")
            self.metrics.record_request(success=False, latency_ms=(time.time() - start_time) * 1000)
            raise
    
    async def process_change_with_full_stack(
        self,
        change: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a change request through the full stack
        
        Args:
            change: Change request with description, files, etc.
            
        Returns:
            Processing results with agent outputs
        """
        change_id = change.get('id', f"change-{uuid.uuid4().hex[:8]}")
        logger.info(f"Processing change: {change_id}")
        
        results = {
            'change_id': change_id,
            'agents': {},
            'checkpoints': []
        }
        
        # Route to appropriate agents
        if self.agent_layer:
            # Spawn sub-agents for parallel processing
            tasks = []
            
            for agent_type in ['frontend', 'backend', 'testing']:
                task_id = await self.agent_layer.subagent_spawner.spawn_task(
                    parent_agent='integration',
                    task_type=f'process_change_{agent_type}',
                    description=f"Process change {change_id} for {agent_type}",
                    input_data={'change': change, 'agent_type': agent_type}
                )
                tasks.append((agent_type, task_id))
            
            # Collect results
            for agent_type, task_id in tasks:
                result = await self.agent_layer.subagent_spawner.get_result(task_id)
                results['agents'][agent_type] = result
        
        # Create checkpoint for change
        checkpoint = await self.create_checkpoint(change_id, 'change_processed', results)
        results['checkpoints'].append(checkpoint.checkpoint_id)
        
        return results
    
    async def run_security_audit(
        self,
        project_path: str
    ) -> Dict[str, Any]:
        """
        Run security audit using Paystack Security Agent
        
        Args:
            project_path: Path to project directory
            
        Returns:
            Security audit results
        """
        logger.info(f"Running security audit for: {project_path}")
        
        if not self.security_agent:
            return {
                'status': 'unavailable',
                'error': 'Security agent not initialized',
                'recommendations': ['Enable SECURITY_AGENT_AVAILABLE and ensure dependencies are installed']
            }
        
        try:
            # Run security audit
            audit_result = await self.security_agent.scan_repository(project_path)
            
            # Store results in pattern database
            if self.pattern_db:
                pattern = Pattern(
                    id=f"security-audit-{uuid.uuid4().hex[:8]}",
                    type=PatternType.UTILITY,
                    content=json.dumps(audit_result),
                    metadata={'project_path': project_path}
                )
                await self.pattern_db.add_pattern(pattern)
            
            # Trigger n8n notification if critical issues found
            if audit_result.get('critical_issues', 0) > 0 and self.n8n:
                await self.n8n.send_notification(
                    channel='slack',
                    message=f"🚨 Security audit found {audit_result['critical_issues']} critical issues in {project_path}",
                    priority='critical',
                    title='Security Alert'
                )
            
            return audit_result
            
        except Exception as e:
            logger.error(f"Security audit failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    async def optimize_performance(
        self,
        route_code: str
    ) -> Dict[str, Any]:
        """
        Optimize performance using AI Route Optimizer
        
        Args:
            route_code: Code to optimize (function, route handler, etc.)
            
        Returns:
            Optimization results with improved code
        """
        logger.info("Running performance optimization")
        
        if not self.route_optimizer:
            return {
                'status': 'unavailable',
                'error': 'Route optimizer not initialized',
                'original_code': route_code
            }
        
        try:
            result = await self.route_optimizer.optimize(route_code)
            
            # Store optimization pattern
            if self.pattern_db and result.get('optimized_code'):
                pattern = Pattern(
                    id=f"perf-opt-{uuid.uuid4().hex[:8]}",
                    type=PatternType.UTILITY,
                    content=result['optimized_code'],
                    metadata={'original_hash': hashlib.sha256(route_code.encode()).hexdigest()[:16]}
                )
                await self.pattern_db.add_pattern(pattern)
            
            return result
            
        except Exception as e:
            logger.error(f"Performance optimization failed: {e}")
            return {'status': 'error', 'error': str(e), 'original_code': route_code}
    
    async def verify_rewards(
        self,
        reward_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Verify reward data using Reward Verification Agent
        
        Args:
            reward_data: Reward data to verify
            
        Returns:
            Verification results
        """
        logger.info("Verifying reward data")
        
        if not self.reward_verifier:
            return {
                'status': 'unavailable',
                'error': 'Reward verifier not initialized',
                'verified': False
            }
        
        try:
            result = await self.reward_verifier.verify(reward_data)
            
            # Log verification result
            if self.n8n:
                await self.n8n.handle_agent_event(
                    'reward_verification_complete',
                    {'reward_id': reward_data.get('id'), 'verified': result.get('verified', False)}
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Reward verification failed: {e}")
            return {'status': 'error', 'error': str(e), 'verified': False}
    
    # =========================================================================
    # CHECKPOINT MANAGEMENT
    # =========================================================================
    
    async def create_checkpoint(
        self,
        build_id: str,
        stage: str,
        data: Dict[str, Any]
    ) -> CheckpointResult:
        """
        Create checkpoint across all 3 tiers
        
        Args:
            build_id: Build identifier
            stage: Build stage
            data: Checkpoint data
            
        Returns:
            CheckpointResult with all tier statuses
        """
        checkpoint_id = f"{build_id}-{stage}-{int(time.time())}"
        result = CheckpointResult(checkpoint_id=checkpoint_id)
        
        # Tier 1: Redis
        if self.redis and self._health_status.get('redis', ComponentHealth('', ServiceStatus.DISABLED, 0)).status in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]:
            try:
                await self.redis.set_checkpoint(
                    checkpoint_id,
                    {
                        'id': checkpoint_id,
                        'timestamp': datetime.utcnow().isoformat(),
                        'stage': stage,
                        'build_id': build_id,
                        'data': data
                    },
                    ttl_seconds=300  # 5 minutes for hot checkpoint
                )
                result.tier1_success = True
                result.redis_id = checkpoint_id
                logger.debug(f"Tier 1 checkpoint created: {checkpoint_id}")
            except Exception as e:
                logger.warning(f"Tier 1 checkpoint failed: {e}")
        
        # Tier 2: PostgreSQL
        if self.postgres and self._health_status.get('postgres', ComponentHealth('', ServiceStatus.DISABLED, 0)).status == ServiceStatus.HEALTHY:
            try:
                checkpoint = Checkpoint(
                    id=checkpoint_id,
                    session_id=build_id,
                    build_id=build_id,
                    stage=stage,
                    agent_outputs=data,
                    metadata={'tier': 2},
                    git_commit_hash=None,
                    created_at=datetime.utcnow()
                )
                await self.postgres.store_checkpoint(checkpoint)
                result.tier2_success = True
                result.postgres_id = checkpoint_id
                logger.debug(f"Tier 2 checkpoint created: {checkpoint_id}")
            except Exception as e:
                logger.warning(f"Tier 2 checkpoint failed: {e}")
        
        # Tier 3: Git
        if self.git and self._health_status.get('git', ComponentHealth('', ServiceStatus.DISABLED, 0)).status == ServiceStatus.HEALTHY:
            try:
                files = data.get('files_created', [])
                cp_id, commit_hash = await self.git.create_checkpoint_commit(
                    build_id=build_id,
                    stage=stage,
                    files=files,
                    metadata={'checkpoint_id': checkpoint_id},
                    agent_outputs=data
                )
                result.tier3_success = True
                result.git_commit_hash = commit_hash
                logger.debug(f"Tier 3 checkpoint created: {checkpoint_id} ({commit_hash[:8]})")
            except Exception as e:
                logger.warning(f"Tier 3 checkpoint failed: {e}")
        
        self.metrics.record_checkpoint()
        
        # Emit event
        if self.agent_layer:
            self.agent_layer.events.emit('checkpoint_created', {
                'checkpoint_id': checkpoint_id,
                'build_id': build_id,
                'stage': stage,
                'result': result.to_dict() if hasattr(result, 'to_dict') else vars(result)
            })
        
        return result
    
    async def rollback_to_checkpoint(
        self,
        checkpoint_id: str
    ) -> Dict[str, Any]:
        """
        Rollback to a specific checkpoint
        
        Args:
            checkpoint_id: Checkpoint identifier
            
        Returns:
            Rollback results
        """
        logger.info(f"Rolling back to checkpoint: {checkpoint_id}")
        
        results = {
            'checkpoint_id': checkpoint_id,
            'tier1_rollback': False,
            'tier2_rollback': False,
            'tier3_rollback': False
        }
        
        # Attempt Git rollback (Tier 3) first as it's the source of truth
        if self.git:
            try:
                rollback_result = await self.git.rollback_to_checkpoint(checkpoint_id)
                results['tier3_rollback'] = rollback_result.get('success', False)
                results['git_result'] = rollback_result
            except Exception as e:
                logger.error(f"Tier 3 rollback failed: {e}")
        
        return results
    
    # =========================================================================
    # A/B TESTING
    # =========================================================================
    
    async def run_ab_test(
        self,
        test_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create and run an A/B test
        
        Args:
            test_config: Test configuration with variants, metrics, etc.
            
        Returns:
            Test results and analysis
        """
        if not self.ab_test and AB_TEST_AVAILABLE:
            # Initialize on first use
            self.ab_test = ABTestFramework(
                postgres_dsn=self.config.ab_test_postgres_dsn,
                redis_url=self.config.ab_test_redis_url
            )
            await self.ab_test.initialize()
        
        if not self.ab_test:
            return {'status': 'unavailable', 'error': 'A/B testing not initialized'}
        
        try:
            # Create test
            test = ABTest(
                test_id=f"test-{uuid.uuid4().hex[:8]}",
                name=test_config.get('name', 'Unnamed Test'),
                test_type=test_config.get('test_type', 'prompt_variation'),
                variants=test_config.get('variants', []),
                status=TestStatus.DRAFT,
                hypothesis=test_config.get('hypothesis', ''),
                primary_metric=test_config.get('primary_metric', 'success_rate'),
                min_sample_size=test_config.get('min_sample_size', 100)
            )
            
            # Save and start test
            await self.ab_test.save_test(test)
            await self.ab_test.start_test(test.test_id)
            
            return {
                'status': 'started',
                'test_id': test.test_id,
                'message': 'A/B test started successfully'
            }
            
        except Exception as e:
            logger.error(f"A/B test creation failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    # =========================================================================
    # PATTERN DATABASE
    # =========================================================================
    
    async def search_patterns(
        self,
        query: str,
        pattern_type: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search pattern database
        
        Args:
            query: Search query
            pattern_type: Filter by pattern type
            top_k: Number of results to return
            
        Returns:
            List of matching patterns
        """
        if not self.pattern_db:
            return []
        
        try:
            results = await self.pattern_db.search(
                query=query,
                pattern_type=PatternType(pattern_type) if pattern_type else None,
                top_k=top_k
            )
            
            return [
                {
                    'id': r.pattern.id,
                    'type': r.pattern.type.value,
                    'content': r.pattern.content[:200] + '...' if len(r.pattern.content) > 200 else r.pattern.content,
                    'similarity_score': r.similarity_score,
                    'success_score': r.pattern.success_score
                }
                for r in results
            ]
            
        except Exception as e:
            logger.error(f"Pattern search failed: {e}")
            return []
    
    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================
    
    async def _on_checkpoint_created(self, data: Dict[str, Any]):
        """Handle checkpoint created event"""
        logger.debug(f"Checkpoint created event: {data.get('checkpoint_id')}")
        
        # Trigger n8n workflow
        if self.n8n:
            await self.n8n.handle_agent_event('checkpoint_created', data)
    
    async def _on_consensus_reached(self, data: Dict[str, Any]):
        """Handle consensus reached event"""
        logger.debug(f"Consensus reached event: {data.get('task_id')}")
        
        # Store consensus in pattern database
        if self.pattern_db and data.get('decision') == 'APPROVE':
            pattern = Pattern(
                id=f"consensus-{uuid.uuid4().hex[:8]}",
                type=PatternType.WORKFLOW,
                content=json.dumps(data),
                success_score=100.0
            )
            await self.pattern_db.add_pattern(pattern)
        
        # Trigger n8n workflow
        if self.n8n:
            await self.n8n.handle_agent_event('consensus_reached', data)
    
    async def _on_evaluation_complete(self, data: Dict[str, Any]):
        """Handle evaluation complete event"""
        logger.debug(f"Evaluation complete event: {data.get('evaluation_id')}")
        
        # Forward to A/B testing framework
        if self.ab_test:
            # Could record evaluation as test result
            pass
        
        # Trigger n8n workflow
        if self.n8n:
            await self.n8n.handle_agent_event('evaluation_complete', data)
    
    # =========================================================================
    # DASHBOARD DATA
    # =========================================================================
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Get data for health status dashboard
        
        Returns:
            Dashboard data with health, metrics, and recent activity
        """
        health = await self.health_check()
        
        # Get recent checkpoints
        recent_checkpoints = []
        if self.postgres:
            try:
                checkpoints = await self.postgres.query_checkpoints(limit=10)
                recent_checkpoints = [
                    {
                        'id': cp.id,
                        'build_id': cp.build_id,
                        'stage': cp.stage,
                        'created_at': cp.created_at.isoformat()
                    }
                    for cp in checkpoints
                ]
            except Exception as e:
                logger.warning(f"Failed to fetch checkpoints: {e}")
        
        return {
            'health': health,
            'metrics': self.metrics.get_summary(),
            'recent_checkpoints': recent_checkpoints,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    # =========================================================================
    # SHUTDOWN
    # =========================================================================
    
    async def shutdown(self):
        """Gracefully shutdown all components"""
        logger.info("Shutting down APEX Integration...")
        
        if self.redis:
            await self.redis.disconnect()
        
        if self.postgres:
            await self.postgres.disconnect()
        
        if self.kimi:
            await self.kimi.close()
        
        if self.n8n:
            await self.n8n.close()
        
        if self.pattern_db:
            await self.pattern_db.disconnect()
        
        if self.ab_test and hasattr(self.ab_test, 'close'):
            await self.ab_test.close()
        
        self._initialized = False
        logger.info("APEX Integration shutdown complete")
    
    # =========================================================================
    # CONTEXT MANAGER
    # =========================================================================
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()


# =============================================================================
# DEMO AND TESTING
# =============================================================================

async def run_integration_test():
    """Run full integration test"""
    print("\n" + "="*60)
    print("APEX Integration Test")
    print("="*60)
    
    # Create config
    config = APEXConfig(
        enable_mock_mode=True,
        enable_redis=False,  # Use mock/SQLite fallback
        enable_postgres=False,
        enable_git=True,
        enable_kimi=False,
        enable_n8n=False,
        enable_pattern_db=False,
        enable_ab_testing=False
    )
    
    # Initialize integration
    apex = APEXIntegration(config)
    
    try:
        # Initialize
        print("\n1. Initializing APEX Integration...")
        initialized = await apex.initialize()
        print(f"   Status: {'✅ Initialized' if initialized else '❌ Failed'}")
        
        # Health check
        print("\n2. Running health check...")
        health = await apex.health_check()
        print(f"   Overall Status: {health['status']}")
        print(f"   Components: {health['summary']}")
        
        # Create checkpoint
        print("\n3. Creating test checkpoint...")
        checkpoint = await apex.create_checkpoint(
            build_id='test-build',
            stage='test',
            data={'test': 'data', 'files_created': ['test.py']}
        )
        print(f"   Checkpoint ID: {checkpoint.checkpoint_id}")
        print(f"   Tier 1 (Redis): {'✅' if checkpoint.tier1_success else '❌'}")
        print(f"   Tier 2 (Postgres): {'✅' if checkpoint.tier2_success else '❌'}")
        print(f"   Tier 3 (Git): {'✅' if checkpoint.tier3_success else '❌'}")
        
        # Get dashboard data
        print("\n4. Fetching dashboard data...")
        dashboard = await apex.get_dashboard_data()
        print(f"   Metrics: {json.dumps(dashboard['metrics'], indent=2)}")
        
        print("\n" + "="*60)
        print("Integration Test Complete")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        traceback.print_exc()
    
    finally:
        await apex.shutdown()


async def run_performance_benchmark():
    """Run performance benchmarks"""
    print("\n" + "="*60)
    print("APEX Performance Benchmark")
    print("="*60)
    
    config = APEXConfig(enable_mock_mode=True)
    apex = APEXIntegration(config)
    
    try:
        await apex.initialize()
        
        # Benchmark checkpoint creation
        print("\n1. Checkpoint Creation Benchmark")
        times = []
        for i in range(10):
            start = time.time()
            await apex.create_checkpoint(f'bench-{i}', 'benchmark', {'iteration': i})
            times.append((time.time() - start) * 1000)
        
        avg_time = sum(times) / len(times)
        print(f"   Average: {avg_time:.2f}ms")
        print(f"   Min: {min(times):.2f}ms")
        print(f"   Max: {max(times):.2f}ms")
        
        # Benchmark health check
        print("\n2. Health Check Benchmark")
        times = []
        for _ in range(10):
            start = time.time()
            await apex.health_check()
            times.append((time.time() - start) * 1000)
        
        avg_time = sum(times) / len(times)
        print(f"   Average: {avg_time:.2f}ms")
        
        print("\n" + "="*60)
        print("Benchmark Complete")
        print("="*60)
        
    finally:
        await apex.shutdown()


if __name__ == "__main__":
    # Run tests
    asyncio.run(run_integration_test())
    # asyncio.run(run_performance_benchmark())
