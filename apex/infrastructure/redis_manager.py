#!/usr/bin/env python3
"""
APEX Redis Integration Layer

Enterprise-grade Redis connectivity for the APEX Agent Layer with:
- Connection pooling with health checks
- Automatic reconnection with exponential backoff
- Support for Redis Sentinel (HA) and Redis Cluster
- Pub/Sub for real-time agent communication
- Stream support for event sourcing
- Tier 1 checkpoint storage integration
- Distributed locking and rate limiting

Author: APEX Infrastructure Team
Version: 1.0.0
"""

import asyncio
import json
import logging
import os
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union, AsyncGenerator
import hashlib
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger('RedisManager')

# Redis imports with graceful fallback
try:
    import redis.asyncio as aioredis
    from redis.asyncio import Redis, Sentinel, ClusterRedis
    from redis.asyncio.sentinel import Sentinel as AsyncSentinel
    from redis.asyncio.cluster import RedisCluster as AsyncRedisCluster
    from redis.exceptions import (
        RedisError, ConnectionError as RedisConnectionError,
        TimeoutError as RedisTimeoutError, BusyLoadingError,
        ResponseError, AuthenticationError
    )
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis-py not available. Redis functionality will be disabled.")
    # Define placeholder classes for type hints
    class Redis: pass
    class RedisConnectionError(Exception): pass


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RedisConfig:
    """Redis configuration with environment variable support"""
    url: Optional[str] = None
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0
    ssl: bool = False
    ssl_cert_reqs: Optional[str] = None
    
    # Connection pool settings
    connection_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    socket_timeout: float = 5.0
    max_connections: int = 20
    max_retries: int = 3
    
    # Retry settings
    retry_delay_base: float = 1.0
    retry_delay_max: float = 30.0
    retry_exponential_base: float = 2.0
    
    # Circuit breaker settings
    circuit_failure_threshold: int = 5
    circuit_recovery_timeout: float = 30.0
    circuit_half_open_max_calls: int = 3
    
    # Sentinel settings
    sentinel_enabled: bool = False
    sentinel_hosts: List[Tuple[str, int]] = None
    sentinel_master_name: str = "mymaster"
    
    # Cluster settings
    cluster_enabled: bool = False
    cluster_startup_nodes: List[Dict[str, Any]] = None
    
    # SQLite fallback
    sqlite_fallback_path: str = "/tmp/redis_fallback.db"
    
    def __post_init__(self):
        # Override from environment variables
        self.url = os.getenv('REDIS_URL', self.url)
        self.host = os.getenv('REDIS_HOST', self.host)
        self.port = int(os.getenv('REDIS_PORT', self.port))
        self.password = os.getenv('REDIS_PASSWORD', self.password)
        
        if self.sentinel_hosts is None:
            sentinel_env = os.getenv('REDIS_SENTINEL_HOSTS')
            if sentinel_env:
                self.sentinel_hosts = [
                    tuple(h.split(':')) for h in sentinel_env.split(',')
                ]
                self.sentinel_hosts = [(h, int(p)) for h, p in self.sentinel_hosts]
            else:
                self.sentinel_hosts = []


@dataclass
class CheckpointData:
    """Tier 1 checkpoint data structure"""
    id: str
    timestamp: str
    stage: str
    files: List[str]
    metadata: Dict[str, Any]
    hash: str
    build_id: str = ""
    agent_outputs: Dict[str, Any] = None
    git_commit_hash: Optional[str] = None
    ttl_seconds: Optional[int] = None
    
    def __post_init__(self):
        if self.agent_outputs is None:
            self.agent_outputs = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CheckpointData':
        return cls(**data)


@dataclass
class AgentHeartbeat:
    """Agent heartbeat data structure"""
    agent_id: str
    timestamp: str
    status: str  # 'healthy', 'busy', 'error', 'offline'
    current_task: Optional[str] = None
    metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metrics is None:
            self.metrics = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LockInfo:
    """Distributed lock information"""
    lock_id: str
    resource: str
    owner: str
    acquired_at: str
    expires_at: str
    ttl_seconds: int


class CircuitBreaker:
    """Circuit breaker pattern for Redis resilience"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = threading.Lock()
    
    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if self._last_failure_time:
                    elapsed = time.time() - self._last_failure_time
                    if elapsed >= self.recovery_timeout:
                        self._state = CircuitState.HALF_OPEN
                        self._half_open_calls = 0
                        logger.info("Circuit breaker entering HALF_OPEN state")
            return self._state
    
    def record_success(self):
        """Record a successful call"""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1
                if self._half_open_calls >= self.half_open_max_calls:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    logger.info("Circuit breaker CLOSED (recovered)")
            else:
                self._failure_count = 0
    
    def record_failure(self):
        """Record a failed call"""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                logger.warning("Circuit breaker OPEN (recovery failed)")
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(f"Circuit breaker OPEN ({self._failure_count} failures)")
    
    def can_execute(self) -> bool:
        """Check if execution is allowed"""
        state = self.state
        if state == CircuitState.CLOSED:
            return True
        elif state == CircuitState.HALF_OPEN:
            with self._lock:
                return self._half_open_calls < self.half_open_max_calls
        return False


class SQLiteFallback:
    """SQLite fallback storage when Redis is unavailable"""
    
    def __init__(self, db_path: str = "/tmp/redis_fallback.db"):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    def _init_db(self):
        """Initialize SQLite database"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Checkpoints table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Key-value store
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kv_store (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Counters
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS counters (
                key TEXT PRIMARY KEY,
                value INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Agent heartbeats
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_heartbeats (
                agent_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                expires_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Locks
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS locks (
                resource TEXT PRIMARY KEY,
                lock_id TEXT NOT NULL,
                owner TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kv_expires ON kv_store(expires_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_checkpoints_expires ON checkpoints(expires_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_heartbeats_expires ON agent_heartbeats(expires_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_locks_expires ON locks(expires_at)")
        
        conn.commit()
        logger.info(f"SQLite fallback initialized: {self.db_path}")
    
    def cleanup_expired(self):
        """Remove expired entries"""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        
        for table in ['kv_store', 'checkpoints', 'agent_heartbeats', 'locks']:
            cursor.execute(f"DELETE FROM {table} WHERE expires_at < ?", (now,))
        
        conn.commit()
    
    # Checkpoint operations
    def set_checkpoint(self, checkpoint_id: str, data: Dict[str, Any], ttl_seconds: int = 120) -> bool:
        """Store checkpoint in SQLite fallback"""
        try:
            self.cleanup_expired()
            conn = self._get_connection()
            cursor = conn.cursor()
            
            expires_at = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()
            cursor.execute(
                "INSERT OR REPLACE INTO checkpoints (id, data, expires_at) VALUES (?, ?, ?)",
                (checkpoint_id, json.dumps(data), expires_at)
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"SQLite fallback set_checkpoint error: {e}")
            return False
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve checkpoint from SQLite fallback"""
        try:
            self.cleanup_expired()
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT data FROM checkpoints WHERE id = ? AND expires_at > ?",
                (checkpoint_id, datetime.utcnow().isoformat())
            )
            row = cursor.fetchone()
            
            if row:
                return json.loads(row['data'])
            return None
        except Exception as e:
            logger.error(f"SQLite fallback get_checkpoint error: {e}")
            return None
    
    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete checkpoint from SQLite fallback"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM checkpoints WHERE id = ?", (checkpoint_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"SQLite fallback delete_checkpoint error: {e}")
            return False
    
    # Heartbeat operations
    def track_heartbeat(self, agent_id: str, data: Dict[str, Any], ttl_seconds: int = 60) -> bool:
        """Track agent heartbeat in SQLite fallback"""
        try:
            self.cleanup_expired()
            conn = self._get_connection()
            cursor = conn.cursor()
            
            expires_at = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()
            cursor.execute(
                "INSERT OR REPLACE INTO agent_heartbeats (agent_id, data, expires_at) VALUES (?, ?, ?)",
                (agent_id, json.dumps(data), expires_at)
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"SQLite fallback track_heartbeat error: {e}")
            return False
    
    def check_agent_health(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Check agent health from SQLite fallback"""
        try:
            self.cleanup_expired()
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT data FROM agent_heartbeats WHERE agent_id = ? AND expires_at > ?",
                (agent_id, datetime.utcnow().isoformat())
            )
            row = cursor.fetchone()
            
            if row:
                return json.loads(row['data'])
            return None
        except Exception as e:
            logger.error(f"SQLite fallback check_agent_health error: {e}")
            return None
    
    # Counter operations
    def increment_counter(self, key: str, amount: int = 1) -> int:
        """Increment counter in SQLite fallback"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO counters (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = value + ?",
                (key, amount, amount)
            )
            conn.commit()
            
            cursor.execute("SELECT value FROM counters WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row['value'] if row else 0
        except Exception as e:
            logger.error(f"SQLite fallback increment_counter error: {e}")
            return 0
    
    def get_counter(self, key: str) -> int:
        """Get counter value from SQLite fallback"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT value FROM counters WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row['value'] if row else 0
        except Exception as e:
            logger.error(f"SQLite fallback get_counter error: {e}")
            return 0
    
    # Lock operations
    def acquire_lock(self, resource: str, lock_id: str, owner: str, ttl_seconds: int) -> bool:
        """Acquire lock in SQLite fallback"""
        try:
            self.cleanup_expired()
            conn = self._get_connection()
            cursor = conn.cursor()
            
            expires_at = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()
            
            # Try to insert new lock
            try:
                cursor.execute(
                    "INSERT INTO locks (resource, lock_id, owner, expires_at) VALUES (?, ?, ?, ?)",
                    (resource, lock_id, owner, expires_at)
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # Lock exists, check if expired
                cursor.execute(
                    "SELECT expires_at FROM locks WHERE resource = ?",
                    (resource,)
                )
                row = cursor.fetchone()
                
                if row and row['expires_at'] < datetime.utcnow().isoformat():
                    # Lock expired, take over
                    cursor.execute(
                        "UPDATE locks SET lock_id = ?, owner = ?, expires_at = ?, acquired_at = CURRENT_TIMESTAMP WHERE resource = ?",
                        (lock_id, owner, expires_at, resource)
                    )
                    conn.commit()
                    return cursor.rowcount > 0
                return False
        except Exception as e:
            logger.error(f"SQLite fallback acquire_lock error: {e}")
            return False
    
    def release_lock(self, resource: str, lock_id: str) -> bool:
        """Release lock in SQLite fallback"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM locks WHERE resource = ? AND lock_id = ?",
                (resource, lock_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"SQLite fallback release_lock error: {e}")
            return False


class RedisManager:
    """
    Enterprise-grade Redis Manager for APEX Agent Layer
    
    Features:
    - Connection pooling with health checks
    - Automatic reconnection with exponential backoff
    - Support for Redis Sentinel (HA) and Redis Cluster
    - Pub/Sub for real-time agent communication
    - Stream support for event sourcing
    - Tier 1 checkpoint storage
    - Agent heartbeat tracking
    - Distributed locking
    - Rate limiting
    - Circuit breaker pattern
    - SQLite fallback for graceful degradation
    """
    
    # Key prefixes
    PREFIX_CHECKPOINT = "apex:checkpoint:"
    PREFIX_HEARTBEAT = "apex:agent:heartbeat:"
    PREFIX_LOCK = "apex:lock:"
    PREFIX_COUNTER = "apex:counter:"
    PREFIX_RATE_LIMIT = "apex:ratelimit:"
    PREFIX_STREAM = "apex:stream:"
    PREFIX_SESSION = "apex:session:"
    
    def __init__(self, config: Optional[RedisConfig] = None):
        """
        Initialize Redis Manager
        
        Args:
            config: Redis configuration. If None, uses environment variables.
        """
        self.config = config or RedisConfig()
        self._client: Optional[Redis] = None
        self._sentinel: Optional[AsyncSentinel] = None
        
        # Circuit breaker for resilience
        self._circuit = CircuitBreaker(
            failure_threshold=self.config.circuit_failure_threshold,
            recovery_timeout=self.config.circuit_recovery_timeout,
            half_open_max_calls=self.config.circuit_half_open_max_calls
        )
        
        # SQLite fallback
        self._fallback = SQLiteFallback(self.config.sqlite_fallback_path)
        
        # Pub/Sub handlers
        self._pubsub_handlers: Dict[str, List[Callable]] = {}
        self._pubsub_task: Optional[asyncio.Task] = None
        
        # Connection state
        self._connected = False
        self._connection_lock = asyncio.Lock()
        
        logger.info("RedisManager initialized")
    
    # ==================== Connection Management ====================
    
    async def connect(self) -> bool:
        """
        Establish Redis connection with retry logic
        
        Returns:
            True if connected successfully, False otherwise
        """
        async with self._connection_lock:
            if self._connected and self._client:
                try:
                    await self._client.ping()
                    return True
                except Exception:
                    self._connected = False
            
            if not REDIS_AVAILABLE:
                logger.warning("Redis not available, using SQLite fallback")
                return False
            
            for attempt in range(self.config.max_retries):
                try:
                    if self.config.cluster_enabled:
                        await self._connect_cluster()
                    elif self.config.sentinel_enabled:
                        await self._connect_sentinel()
                    else:
                        await self._connect_standalone()
                    
                    # Test connection
                    await self._client.ping()
                    self._connected = True
                    self._circuit.record_success()
                    
                    logger.info("Redis connected successfully")
                    return True
                    
                except Exception as e:
                    delay = min(
                        self.config.retry_delay_base * (self.config.retry_exponential_base ** attempt),
                        self.config.retry_delay_max
                    )
                    logger.warning(f"Redis connection attempt {attempt + 1}/{self.config.max_retries} failed: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
            
            logger.error("Failed to connect to Redis after all retries")
            self._circuit.record_failure()
            return False
    
    async def _connect_standalone(self):
        """Connect to standalone Redis instance"""
        if self.config.url:
            self._client = aioredis.from_url(
                self.config.url,
                decode_responses=True,
                max_connections=self.config.max_connections,
                socket_connect_timeout=self.config.socket_connect_timeout,
                socket_timeout=self.config.socket_timeout
            )
        else:
            self._client = aioredis.Redis(
                host=self.config.host,
                port=self.config.port,
                password=self.config.password,
                db=self.config.db,
                ssl=self.config.ssl,
                decode_responses=True,
                max_connections=self.config.max_connections,
                socket_connect_timeout=self.config.socket_connect_timeout,
                socket_timeout=self.config.socket_timeout
            )
    
    async def _connect_sentinel(self):
        """Connect via Redis Sentinel for HA"""
        if not self.config.sentinel_hosts:
            raise ValueError("Sentinel hosts not configured")
        
        self._sentinel = AsyncSentinel(
            self.config.sentinel_hosts,
            password=self.config.password,
            decode_responses=True,
            max_connections=self.config.max_connections,
            socket_connect_timeout=self.config.socket_connect_timeout,
            socket_timeout=self.config.socket_timeout
        )
        self._client = self._sentinel.master_for(self.config.sentinel_master_name)
        logger.info(f"Connected to Redis Sentinel (master: {self.config.sentinel_master_name})")
    
    async def _connect_cluster(self):
        """Connect to Redis Cluster"""
        startup_nodes = self.config.cluster_startup_nodes or [
            {"host": self.config.host, "port": self.config.port}
        ]
        
        self._client = AsyncRedisCluster(
            startup_nodes=startup_nodes,
            password=self.config.password,
            decode_responses=True,
            skip_full_coverage_check=True,
            max_connections=self.config.max_connections,
            socket_connect_timeout=self.config.socket_connect_timeout,
            socket_timeout=self.config.socket_timeout
        )
        logger.info(f"Connected to Redis Cluster ({len(startup_nodes)} nodes)")
    
    async def disconnect(self):
        """Close Redis connection"""
        async with self._connection_lock:
            if self._client:
                await self._client.close()
                self._client = None
            
            self._connected = False
            
            # Stop pub/sub task
            if self._pubsub_task:
                self._pubsub_task.cancel()
                try:
                    await self._pubsub_task
                except asyncio.CancelledError:
                    pass
                self._pubsub_task = None
            
            logger.info("Redis disconnected")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check
        
        Returns:
            Health status dictionary
        """
        status = {
            "connected": False,
            "circuit_state": self._circuit.state.value,
            "mode": "unknown",
            "latency_ms": None,
            "error": None,
            "fallback_active": False
        }
        
        if not REDIS_AVAILABLE:
            status["error"] = "Redis not installed"
            status["fallback_active"] = True
            return status
        
        if self.config.cluster_enabled:
            status["mode"] = "cluster"
        elif self.config.sentinel_enabled:
            status["mode"] = "sentinel"
        else:
            status["mode"] = "standalone"
        
        try:
            start = time.time()
            await self._client.ping()
            status["latency_ms"] = round((time.time() - start) * 1000, 2)
            status["connected"] = True
        except Exception as e:
            status["error"] = str(e)
            status["fallback_active"] = True
        
        return status
    
    async def _execute_with_retry(self, operation: Callable, *args, **kwargs) -> Any:
        """
        Execute Redis operation with retry logic and circuit breaker
        
        Args:
            operation: Async function to execute
            *args, **kwargs: Arguments for the operation
            
        Returns:
            Operation result
            
        Raises:
            RedisConnectionError: If all retries exhausted
        """
        if not self._circuit.can_execute():
            raise RedisConnectionError("Circuit breaker is OPEN")
        
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                # Ensure connection
                if not self._connected:
                    await self.connect()
                
                if not self._client:
                    raise RedisConnectionError("Redis client not available")
                
                result = await operation(*args, **kwargs)
                self._circuit.record_success()
                return result
                
            except (RedisConnectionError, RedisTimeoutError, BusyLoadingError) as e:
                last_error = e
                self._connected = False
                
                delay = min(
                    self.config.retry_delay_base * (self.config.retry_exponential_base ** attempt),
                    self.config.retry_delay_max
                )
                logger.warning(f"Redis operation failed (attempt {attempt + 1}/{self.config.max_retries}): {e}")
                await asyncio.sleep(delay)
            
            except Exception as e:
                # Non-retryable error
                self._circuit.record_failure()
                raise
        
        # All retries exhausted
        self._circuit.record_failure()
        raise RedisConnectionError(f"Operation failed after {self.config.max_retries} attempts: {last_error}")
    
    # ==================== Tier 1 Checkpoint Operations ====================
    
    async def set_checkpoint(
        self,
        checkpoint_id: str,
        checkpoint: Union[CheckpointData, Dict[str, Any]],
        ttl_seconds: int = 120
    ) -> bool:
        """
        Store Tier 1 checkpoint in Redis with TTL
        
        Args:
            checkpoint_id: Unique checkpoint identifier
            checkpoint: Checkpoint data (CheckpointData or dict)
            ttl_seconds: Time-to-live in seconds (default: 120)
            
        Returns:
            True if successful, False otherwise
        """
        if isinstance(checkpoint, CheckpointData):
            data = checkpoint.to_dict()
        else:
            data = checkpoint
        
        data['ttl_seconds'] = ttl_seconds
        key = f"{self.PREFIX_CHECKPOINT}{checkpoint_id}"
        
        async def _set():
            json_data = json.dumps(data)
            pipe = self._client.pipeline()
            pipe.setex(key, ttl_seconds, json_data)
            # Also index by build_id for quick lookup
            if 'build_id' in data and data['build_id']:
                pipe.sadd(f"{self.PREFIX_CHECKPOINT}build:{data['build_id']}", checkpoint_id)
                pipe.expire(f"{self.PREFIX_CHECKPOINT}build:{data['build_id']}", ttl_seconds)
            await pipe.execute()
            return True
        
        try:
            return await self._execute_with_retry(_set)
        except Exception as e:
            logger.warning(f"Redis set_checkpoint failed, using fallback: {e}")
            return self._fallback.set_checkpoint(checkpoint_id, data, ttl_seconds)
    
    async def get_checkpoint(self, checkpoint_id: str) -> Optional[CheckpointData]:
        """
        Retrieve Tier 1 checkpoint from Redis
        
        Args:
            checkpoint_id: Checkpoint identifier
            
        Returns:
            CheckpointData if found, None otherwise
        """
        key = f"{self.PREFIX_CHECKPOINT}{checkpoint_id}"
        
        async def _get():
            data = await self._client.get(key)
            if data:
                checkpoint_dict = json.loads(data)
                # Get remaining TTL
                ttl = await self._client.ttl(key)
                checkpoint_dict['ttl_seconds'] = ttl if ttl > 0 else 0
                return CheckpointData.from_dict(checkpoint_dict)
            return None
        
        try:
            result = await self._execute_with_retry(_get)
            if result:
                return result
        except Exception as e:
            logger.warning(f"Redis get_checkpoint failed, trying fallback: {e}")
        
        # Try fallback
        fallback_data = self._fallback.get_checkpoint(checkpoint_id)
        if fallback_data:
            return CheckpointData.from_dict(fallback_data)
        return None
    
    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Delete Tier 1 checkpoint from Redis
        
        Args:
            checkpoint_id: Checkpoint identifier
            
        Returns:
            True if deleted, False otherwise
        """
        key = f"{self.PREFIX_CHECKPOINT}{checkpoint_id}"
        
        async def _delete():
            result = await self._client.delete(key)
            return result > 0
        
        try:
            return await self._execute_with_retry(_delete)
        except Exception as e:
            logger.warning(f"Redis delete_checkpoint failed, using fallback: {e}")
            return self._fallback.delete_checkpoint(checkpoint_id)
    
    async def get_checkpoints_by_build(self, build_id: str) -> List[CheckpointData]:
        """
        Get all checkpoints for a build
        
        Args:
            build_id: Build identifier
            
        Returns:
            List of CheckpointData objects
        """
        key = f"{self.PREFIX_CHECKPOINT}build:{build_id}"
        
        async def _get():
            checkpoint_ids = await self._client.smembers(key)
            checkpoints = []
            for cp_id in checkpoint_ids:
                cp = await self.get_checkpoint(cp_id)
                if cp:
                    checkpoints.append(cp)
            return checkpoints
        
        try:
            return await self._execute_with_retry(_get)
        except Exception as e:
            logger.error(f"Failed to get checkpoints by build: {e}")
            return []
    
    # ==================== Agent Heartbeat Operations ====================
    
    async def track_heartbeat(
        self,
        agent_id: str,
        status: str = "healthy",
        current_task: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        ttl_seconds: int = 60
    ) -> bool:
        """
        Track agent heartbeat with TTL
        
        Args:
            agent_id: Unique agent identifier
            status: Agent status ('healthy', 'busy', 'error', 'offline')
            current_task: Current task identifier
            metrics: Additional metrics dictionary
            ttl_seconds: Heartbeat TTL (default: 60)
            
        Returns:
            True if successful, False otherwise
        """
        heartbeat = AgentHeartbeat(
            agent_id=agent_id,
            timestamp=datetime.utcnow().isoformat(),
            status=status,
            current_task=current_task,
            metrics=metrics or {}
        )
        
        key = f"{self.PREFIX_HEARTBEAT}{agent_id}"
        
        async def _track():
            await self._client.setex(key, ttl_seconds, json.dumps(heartbeat.to_dict()))
            # Add to active agents set
            await self._client.sadd(f"{self.PREFIX_HEARTBEAT}active", agent_id)
            return True
        
        try:
            return await self._execute_with_retry(_track)
        except Exception as e:
            logger.warning(f"Redis track_heartbeat failed, using fallback: {e}")
            return self._fallback.track_heartbeat(agent_id, heartbeat.to_dict(), ttl_seconds)
    
    async def check_agent_health(self, agent_id: str) -> Optional[AgentHeartbeat]:
        """
        Check agent health status
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            AgentHeartbeat if agent is healthy, None otherwise
        """
        key = f"{self.PREFIX_HEARTBEAT}{agent_id}"
        
        async def _check():
            data = await self._client.get(key)
            if data:
                return AgentHeartbeat(**json.loads(data))
            return None
        
        try:
            result = await self._execute_with_retry(_check)
            if result:
                return result
        except Exception as e:
            logger.warning(f"Redis check_agent_health failed, trying fallback: {e}")
        
        # Try fallback
        fallback_data = self._fallback.check_agent_health(agent_id)
        if fallback_data:
            return AgentHeartbeat(**fallback_data)
        return None
    
    async def get_active_agents(self) -> List[str]:
        """
        Get list of active agent IDs
        
        Returns:
            List of active agent IDs
        """
        async def _get():
            return list(await self._client.smembers(f"{self.PREFIX_HEARTBEAT}active"))
        
        try:
            return await self._execute_with_retry(_get)
        except Exception as e:
            logger.error(f"Failed to get active agents: {e}")
            return []
    
    async def get_all_agent_health(self) -> Dict[str, Optional[AgentHeartbeat]]:
        """
        Get health status for all active agents
        
        Returns:
            Dictionary mapping agent_id to AgentHeartbeat or None
        """
        agent_ids = await self.get_active_agents()
        result = {}
        
        for agent_id in agent_ids:
            result[agent_id] = await self.check_agent_health(agent_id)
        
        return result
    
    # ==================== Pub/Sub Operations ====================
    
    async def publish_event(self, channel: str, message: Dict[str, Any]) -> bool:
        """
        Publish event to a channel
        
        Args:
            channel: Channel name
            message: Message dictionary
            
        Returns:
            True if published successfully
        """
        async def _publish():
            await self._client.publish(channel, json.dumps(message))
            return True
        
        try:
            return await self._execute_with_retry(_publish)
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            return False
    
    async def subscribe_to_events(
        self,
        channels: List[str],
        handler: Callable[[str, Dict[str, Any]], Any]
    ) -> bool:
        """
        Subscribe to events on specified channels
        
        Args:
            channels: List of channel names
            handler: Callback function(channel, message)
            
        Returns:
            True if subscribed successfully
        """
        for channel in channels:
            if channel not in self._pubsub_handlers:
                self._pubsub_handlers[channel] = []
            self._pubsub_handlers[channel].append(handler)
        
        # Start pub/sub listener if not already running
        if not self._pubsub_task or self._pubsub_task.done():
            self._pubsub_task = asyncio.create_task(self._pubsub_listener())
        
        return True
    
    async def _pubsub_listener(self):
        """Background task for pub/sub listening"""
        try:
            if not self._client:
                return
            
            pubsub = self._client.pubsub()
            await pubsub.subscribe(*self._pubsub_handlers.keys())
            
            logger.info(f"Pub/Sub listener started for channels: {list(self._pubsub_handlers.keys())}")
            
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    channel = message['channel']
                    try:
                        data = json.loads(message['data'])
                        # Call all handlers for this channel
                        for handler in self._pubsub_handlers.get(channel, []):
                            try:
                                if asyncio.iscoroutinefunction(handler):
                                    asyncio.create_task(handler(channel, data))
                                else:
                                    handler(channel, data)
                            except Exception as e:
                                logger.error(f"Pub/Sub handler error: {e}")
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in pub/sub message: {message['data']}")
                        
        except asyncio.CancelledError:
            logger.info("Pub/Sub listener cancelled")
            raise
        except Exception as e:
            logger.error(f"Pub/Sub listener error: {e}")
    
    async def unsubscribe(self, channels: Optional[List[str]] = None):
        """
        Unsubscribe from channels
        
        Args:
            channels: List of channels to unsubscribe. If None, unsubscribes from all.
        """
        if channels is None:
            self._pubsub_handlers.clear()
        else:
            for channel in channels:
                self._pubsub_handlers.pop(channel, None)
    
    # ==================== Distributed Locking ====================
    
    async def acquire_lock(
        self,
        resource: str,
        owner: str,
        ttl_seconds: int = 30,
        blocking: bool = False,
        blocking_timeout: float = 10.0
    ) -> Optional[str]:
        """
        Acquire distributed lock for resource
        
        Args:
            resource: Resource to lock
            owner: Lock owner identifier
            ttl_seconds: Lock TTL (auto-expires)
            blocking: Whether to block until lock is acquired
            blocking_timeout: Maximum time to wait for lock
            
        Returns:
            Lock ID if acquired, None otherwise
        """
        lock_id = str(uuid.uuid4())
        key = f"{self.PREFIX_LOCK}{resource}"
        lock_info = LockInfo(
            lock_id=lock_id,
            resource=resource,
            owner=owner,
            acquired_at=datetime.utcnow().isoformat(),
            expires_at=(datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat(),
            ttl_seconds=ttl_seconds
        )
        
        async def _acquire():
            # Use NX (only set if not exists) for atomic lock acquisition
            result = await self._client.set(
                key,
                json.dumps(lock_info.__dict__),
                nx=True,
                ex=ttl_seconds
            )
            return result is not None
        
        async def _acquire_blocking():
            start_time = time.time()
            while time.time() - start_time < blocking_timeout:
                if await _acquire():
                    return True
                await asyncio.sleep(0.1)
            return False
        
        try:
            if blocking:
                acquired = await _acquire_blocking()
            else:
                acquired = await self._execute_with_retry(_acquire)
            
            if acquired:
                return lock_id
        except Exception as e:
            logger.warning(f"Redis acquire_lock failed, trying fallback: {e}")
            if self._fallback.acquire_lock(resource, lock_id, owner, ttl_seconds):
                return lock_id
        
        return None
    
    async def release_lock(self, resource: str, lock_id: str) -> bool:
        """
        Release distributed lock
        
        Args:
            resource: Resource that was locked
            lock_id: Lock ID returned from acquire_lock
            
        Returns:
            True if released, False otherwise
        """
        key = f"{self.PREFIX_LOCK}{resource}"
        
        async def _release():
            # Get current lock value
            current = await self._client.get(key)
            if current:
                current_info = json.loads(current)
                if current_info.get('lock_id') == lock_id:
                    await self._client.delete(key)
                    return True
            return False
        
        try:
            return await self._execute_with_retry(_release)
        except Exception as e:
            logger.warning(f"Redis release_lock failed, using fallback: {e}")
            return self._fallback.release_lock(resource, lock_id)
    
    async def extend_lock(self, resource: str, lock_id: str, additional_ttl: int) -> bool:
        """
        Extend lock TTL
        
        Args:
            resource: Resource that was locked
            lock_id: Lock ID
            additional_ttl: Additional seconds to add
            
        Returns:
            True if extended, False otherwise
        """
        key = f"{self.PREFIX_LOCK}{resource}"
        
        async def _extend():
            current = await self._client.get(key)
            if current:
                current_info = json.loads(current)
                if current_info.get('lock_id') == lock_id:
                    new_ttl = current_info['ttl_seconds'] + additional_ttl
                    current_info['ttl_seconds'] = new_ttl
                    current_info['expires_at'] = (datetime.utcnow() + timedelta(seconds=new_ttl)).isoformat()
                    await self._client.setex(key, new_ttl, json.dumps(current_info))
                    return True
            return False
        
        try:
            return await self._execute_with_retry(_extend)
        except Exception as e:
            logger.error(f"Failed to extend lock: {e}")
            return False
    
    # ==================== Rate Limiting ====================
    
    async def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> Tuple[bool, int, int]:
        """
        Check if request is within rate limit
        
        Args:
            key: Rate limit key (e.g., user_id, ip_address)
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            
        Returns:
            Tuple of (allowed: bool, remaining: int, reset_after: int)
        """
        rate_key = f"{self.PREFIX_RATE_LIMIT}{key}"
        
        async def _check():
            pipe = self._client.pipeline()
            now = time.time()
            window_start = now - window_seconds
            
            # Remove old entries
            pipe.zremrangebyscore(rate_key, 0, window_start)
            
            # Count current entries
            pipe.zcard(rate_key)
            
            # Add current request
            pipe.zadd(rate_key, {str(now): now})
            
            # Set expiry on the key
            pipe.expire(rate_key, window_seconds)
            
            results = await pipe.execute()
            current_count = results[1]
            
            if current_count <= max_requests:
                remaining = max_requests - current_count
                reset_after = window_seconds
                return True, remaining, reset_after
            else:
                # Remove the request we just added
                await self._client.zrem(rate_key, str(now))
                # Get oldest entry for reset time
                oldest = await self._client.zrange(rate_key, 0, 0, withscores=True)
                reset_after = int(oldest[0][1] + window_seconds - now) if oldest else window_seconds
                return False, 0, reset_after
        
        try:
            return await self._execute_with_retry(_check)
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open (allow request) if Redis is down
            return True, max_requests, window_seconds
    
    # ==================== Counter Operations ====================
    
    async def increment_counter(self, key: str, amount: int = 1) -> int:
        """
        Increment counter atomically
        
        Args:
            key: Counter key
            amount: Amount to increment (default: 1)
            
        Returns:
            New counter value
        """
        counter_key = f"{self.PREFIX_COUNTER}{key}"
        
        async def _increment():
            return await self._client.incrby(counter_key, amount)
        
        try:
            return await self._execute_with_retry(_increment)
        except Exception as e:
            logger.warning(f"Redis increment_counter failed, using fallback: {e}")
            return self._fallback.increment_counter(key, amount)
    
    async def get_counter(self, key: str) -> int:
        """
        Get counter value
        
        Args:
            key: Counter key
            
        Returns:
            Current counter value
        """
        counter_key = f"{self.PREFIX_COUNTER}{key}"
        
        async def _get():
            value = await self._client.get(counter_key)
            return int(value) if value else 0
        
        try:
            return await self._execute_with_retry(_get)
        except Exception as e:
            logger.warning(f"Redis get_counter failed, using fallback: {e}")
            return self._fallback.get_counter(key)
    
    async def reset_counter(self, key: str) -> bool:
        """
        Reset counter to 0
        
        Args:
            key: Counter key
            
        Returns:
            True if reset successfully
        """
        counter_key = f"{self.PREFIX_COUNTER}{key}"
        
        async def _reset():
            await self._client.set(counter_key, 0)
            return True
        
        try:
            return await self._execute_with_retry(_reset)
        except Exception as e:
            logger.error(f"Failed to reset counter: {e}")
            return False
    
    # ==================== Stream Operations (Event Sourcing) ====================
    
    async def add_stream_event(
        self,
        stream_name: str,
        event_data: Dict[str, Any],
        max_length: Optional[int] = 10000
    ) -> str:
        """
        Add event to Redis Stream
        
        Args:
            stream_name: Stream name
            event_data: Event data dictionary
            max_length: Maximum stream length (for trimming)
            
        Returns:
            Event ID
        """
        stream_key = f"{self.PREFIX_STREAM}{stream_name}"
        
        # Add metadata
        event_data['_timestamp'] = datetime.utcnow().isoformat()
        event_data['_event_id'] = str(uuid.uuid4())
        
        async def _add():
            if max_length:
                event_id = await self._client.xadd(
                    stream_key,
                    event_data,
                    maxlen=max_length,
                    approximate=True
                )
            else:
                event_id = await self._client.xadd(stream_key, event_data)
            return event_id
        
        try:
            return await self._execute_with_retry(_add)
        except Exception as e:
            logger.error(f"Failed to add stream event: {e}")
            raise
    
    async def read_stream(
        self,
        stream_name: str,
        last_id: str = "0",
        count: int = 100,
        block_ms: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Read events from Redis Stream
        
        Args:
            stream_name: Stream name
            last_id: Last event ID to start from (default: "0" for beginning)
            count: Maximum number of events to return
            block_ms: Block for milliseconds if no data (None = don't block)
            
        Returns:
            List of event dictionaries
        """
        stream_key = f"{self.PREFIX_STREAM}{stream_name}"
        
        async def _read():
            if block_ms:
                result = await self._client.xread(
                    {stream_key: last_id},
                    count=count,
                    block=block_ms
                )
            else:
                result = await self._client.xrange(stream_key, min=last_id, count=count)
            
            events = []
            if block_ms and result:
                # xread returns [(stream_name, [(id, fields), ...]), ...]
                for stream, messages in result:
                    for msg_id, fields in messages:
                        events.append({'id': msg_id, **fields})
            else:
                # xrange returns [(id, fields), ...]
                for msg_id, fields in result:
                    events.append({'id': msg_id, **fields})
            
            return events
        
        try:
            return await self._execute_with_retry(_read)
        except Exception as e:
            logger.error(f"Failed to read stream: {e}")
            return []
    
    async def create_consumer_group(
        self,
        stream_name: str,
        group_name: str,
        start_id: str = "0"
    ) -> bool:
        """
        Create consumer group for stream
        
        Args:
            stream_name: Stream name
            group_name: Consumer group name
            start_id: Starting event ID
            
        Returns:
            True if created or already exists
        """
        stream_key = f"{self.PREFIX_STREAM}{stream_name}"
        
        async def _create():
            try:
                await self._client.xgroup_create(stream_key, group_name, id=start_id, mkstream=True)
                return True
            except ResponseError as e:
                if "already exists" in str(e):
                    return True
                raise
        
        try:
            return await self._execute_with_retry(_create)
        except Exception as e:
            logger.error(f"Failed to create consumer group: {e}")
            return False
    
    async def read_consumer_group(
        self,
        stream_name: str,
        group_name: str,
        consumer_name: str,
        count: int = 100,
        block_ms: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Read events as consumer group member
        
        Args:
            stream_name: Stream name
            group_name: Consumer group name
            consumer_name: Consumer name
            count: Number of events
            block_ms: Block time in milliseconds
            
        Returns:
            List of event dictionaries
        """
        stream_key = f"{self.PREFIX_STREAM}{stream_name}"
        
        async def _read():
            result = await self._client.xreadgroup(
                group_name,
                consumer_name,
                {stream_key: ">"},
                count=count,
                block=block_ms
            )
            
            events = []
            for stream, messages in result:
                for msg_id, fields in messages:
                    events.append({'id': msg_id, **fields})
            
            return events
        
        try:
            return await self._execute_with_retry(_read)
        except Exception as e:
            logger.error(f"Failed to read from consumer group: {e}")
            return []
    
    async def ack_stream_event(
        self,
        stream_name: str,
        group_name: str,
        event_id: str
    ) -> bool:
        """
        Acknowledge event processing
        
        Args:
            stream_name: Stream name
            group_name: Consumer group name
            event_id: Event ID to acknowledge
            
        Returns:
            True if acknowledged
        """
        stream_key = f"{self.PREFIX_STREAM}{stream_name}"
        
        async def _ack():
            result = await self._client.xack(stream_key, group_name, event_id)
            return result > 0
        
        try:
            return await self._execute_with_retry(_ack)
        except Exception as e:
            logger.error(f"Failed to ack event: {e}")
            return False
    
    # ==================== Session Management ====================
    
    async def set_session(
        self,
        session_id: str,
        data: Dict[str, Any],
        ttl_seconds: int = 3600
    ) -> bool:
        """
        Store session state
        
        Args:
            session_id: Session identifier
            data: Session data
            ttl_seconds: Session TTL
            
        Returns:
            True if stored successfully
        """
        key = f"{self.PREFIX_SESSION}{session_id}"
        
        async def _set():
            await self._client.setex(key, ttl_seconds, json.dumps(data))
            return True
        
        try:
            return await self._execute_with_retry(_set)
        except Exception as e:
            logger.error(f"Failed to set session: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session state
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data or None
        """
        key = f"{self.PREFIX_SESSION}{session_id}"
        
        async def _get():
            data = await self._client.get(key)
            return json.loads(data) if data else None
        
        try:
            return await self._execute_with_retry(_get)
        except Exception as e:
            logger.error(f"Failed to get session: {e}")
            return None
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete session
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deleted
        """
        key = f"{self.PREFIX_SESSION}{session_id}"
        
        async def _delete():
            result = await self._client.delete(key)
            return result > 0
        
        try:
            return await self._execute_with_retry(_delete)
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False
    
    async def extend_session(self, session_id: str, additional_ttl: int) -> bool:
        """
        Extend session TTL
        
        Args:
            session_id: Session identifier
            additional_ttl: Additional seconds
            
        Returns:
            True if extended
        """
        key = f"{self.PREFIX_SESSION}{session_id}"
        
        async def _extend():
            current_ttl = await self._client.ttl(key)
            if current_ttl > 0:
                new_ttl = current_ttl + additional_ttl
                await self._client.expire(key, new_ttl)
                return True
            return False
        
        try:
            return await self._execute_with_retry(_extend)
        except Exception as e:
            logger.error(f"Failed to extend session: {e}")
            return False


# ==================== Convenience Functions ====================

async def create_redis_manager(
    url: Optional[str] = None,
    host: str = "localhost",
    port: int = 6379,
    password: Optional[str] = None
) -> RedisManager:
    """
    Factory function to create RedisManager
    
    Args:
        url: Redis URL (overrides host/port/password)
        host: Redis host
        port: Redis port
        password: Redis password
        
    Returns:
        Configured RedisManager instance
    """
    config = RedisConfig(
        url=url,
        host=host,
        port=port,
        password=password
    )
    manager = RedisManager(config)
    await manager.connect()
    return manager


# ==================== Test/Demo Code ====================

async def demo_redis_manager():
    """Demonstrate RedisManager functionality"""
    print("=" * 70)
    print("APEX Redis Integration Layer - Demo")
    print("=" * 70)
    
    # Initialize manager
    config = RedisConfig(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', '6379')),
        password=os.getenv('REDIS_PASSWORD'),
        max_retries=2,
        sqlite_fallback_path="/tmp/redis_fallback_demo.db"
    )
    
    manager = RedisManager(config)
    
    # Connect
    print("\n1. Connecting to Redis...")
    connected = await manager.connect()
    if connected:
        print("   ✓ Connected to Redis")
    else:
        print("   ⚠ Redis unavailable, using SQLite fallback")
    
    # Health check
    print("\n2. Health Check...")
    health = await manager.health_check()
    print(f"   Connected: {health['connected']}")
    print(f"   Circuit State: {health['circuit_state']}")
    print(f"   Mode: {health['mode']}")
    print(f"   Latency: {health['latency_ms']}ms" if health['latency_ms'] else "   Latency: N/A")
    
    # Tier 1 Checkpoint Operations
    print("\n3. Tier 1 Checkpoint Operations...")
    checkpoint_id = f"demo-checkpoint-{int(time.time())}"
    checkpoint = CheckpointData(
        id=checkpoint_id,
        timestamp=datetime.utcnow().isoformat(),
        stage="demo",
        files=["/tmp/demo1.txt", "/tmp/demo2.txt"],
        metadata={"agent": "demo-agent", "test": True},
        hash="abc123def456",
        build_id="demo-build-001",
        agent_outputs={"result": "success", "confidence": 0.95}
    )
    
    success = await manager.set_checkpoint(checkpoint_id, checkpoint, ttl_seconds=60)
    print(f"   ✓ Set checkpoint: {success}")
    
    retrieved = await manager.get_checkpoint(checkpoint_id)
    if retrieved:
        print(f"   ✓ Get checkpoint: {retrieved.id}")
        print(f"   ✓ Stage: {retrieved.stage}")
        print(f"   ✓ Files: {len(retrieved.files)}")
    
    # Agent Heartbeat
    print("\n4. Agent Heartbeat Tracking...")
    agent_id = "demo-agent-001"
    heartbeat_success = await manager.track_heartbeat(
        agent_id=agent_id,
        status="healthy",
        current_task="demo-task",
        metrics={"cpu": 45, "memory": 60},
        ttl_seconds=30
    )
    print(f"   ✓ Track heartbeat: {heartbeat_success}")
    
    health_status = await manager.check_agent_health(agent_id)
    if health_status:
        print(f"   ✓ Agent health: {health_status.status}")
        print(f"   ✓ Current task: {health_status.current_task}")
    
    active_agents = await manager.get_active_agents()
    print(f"   ✓ Active agents: {active_agents}")
    
    # Distributed Locking
    print("\n5. Distributed Locking...")
    lock_id = await manager.acquire_lock(
        resource="demo-resource",
        owner=agent_id,
        ttl_seconds=10
    )
    if lock_id:
        print(f"   ✓ Lock acquired: {lock_id[:8]}...")
        released = await manager.release_lock("demo-resource", lock_id)
        print(f"   ✓ Lock released: {released}")
    else:
        print("   ✗ Failed to acquire lock")
    
    # Rate Limiting
    print("\n6. Rate Limiting...")
    for i in range(5):
        allowed, remaining, reset_after = await manager.check_rate_limit(
            key="demo-user",
            max_requests=3,
            window_seconds=60
        )
        status = "✓ Allowed" if allowed else "✗ Blocked"
        print(f"   Request {i+1}: {status} (remaining: {remaining})")
    
    # Counters
    print("\n7. Counter Operations...")
    for i in range(3):
        value = await manager.increment_counter("demo-counter", amount=1)
        print(f"   Increment {i+1}: value = {value}")
    
    counter_value = await manager.get_counter("demo-counter")
    print(f"   Final counter value: {counter_value}")
    
    await manager.reset_counter("demo-counter")
    print(f"   After reset: {await manager.get_counter('demo-counter')}")
    
    # Session Management
    print("\n8. Session Management...")
    session_id = f"demo-session-{int(time.time())}"
    session_data = {
        "user_id": "demo-user",
        "preferences": {"theme": "dark", "language": "en"},
        "last_activity": datetime.utcnow().isoformat()
    }
    
    session_set = await manager.set_session(session_id, session_data, ttl_seconds=60)
    print(f"   ✓ Session created: {session_set}")
    
    session_retrieved = await manager.get_session(session_id)
    if session_retrieved:
        print(f"   ✓ Session retrieved: {session_retrieved['user_id']}")
    
    # Pub/Sub (brief demo)
    print("\n9. Pub/Sub...")
    messages_received = []
    
    async def message_handler(channel: str, message: Dict[str, Any]):
        messages_received.append(message)
        print(f"   ✓ Received on {channel}: {message.get('event')}")
    
    subscribed = await manager.subscribe_to_events(["demo-channel"], message_handler)
    print(f"   ✓ Subscribed: {subscribed}")
    
    # Publish a message
    await manager.publish_event("demo-channel", {
        "event": "demo-message",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    await asyncio.sleep(0.5)  # Wait for message delivery
    
    # Streams
    print("\n10. Redis Streams...")
    stream_name = f"demo-stream-{int(time.time())}"
    
    # Add events
    for i in range(3):
        event_id = await manager.add_stream_event(
            stream_name=stream_name,
            event_data={"type": "demo", "index": i, "data": f"event-{i}"}
        )
        print(f"   ✓ Added event: {event_id[:10]}...")
    
    # Read events
    events = await manager.read_stream(stream_name, count=10)
    print(f"   ✓ Read {len(events)} events from stream")
    
    # Create consumer group
    group_created = await manager.create_consumer_group(stream_name, "demo-group")
    print(f"   ✓ Consumer group created: {group_created}")
    
    # Cleanup
    print("\n11. Cleanup...")
    await manager.delete_checkpoint(checkpoint_id)
    print("   ✓ Checkpoint deleted")
    
    await manager.delete_session(session_id)
    print("   ✓ Session deleted")
    
    await manager.unsubscribe()
    print("   ✓ Unsubscribed from channels")
    
    # Disconnect
    await manager.disconnect()
    print("   ✓ Disconnected from Redis")
    
    print("\n" + "=" * 70)
    print("Demo completed successfully!")
    print("=" * 70)
    
    return True


if __name__ == "__main__":
    try:
        asyncio.run(demo_redis_manager())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise
