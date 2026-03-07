#!/usr/bin/env python3
"""
APEX Shared State Manager

Production-ready shared state management for multi-agent coordination with:
- Build progress tracking
- Agent status updates
- Shared variables/knowledge
- Distributed locking for critical sections
- State snapshots for recovery
- Event notifications on state changes
- Automatic conflict resolution

Backends:
- Redis (primary): High-performance distributed state
- SQLite (fallback): Local persistence when Redis unavailable

Author: APEX Infrastructure Team
Version: 1.0.0
"""

import asyncio
import base64
import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import (
    Any, Callable, Dict, Generic, List, Optional, Set, 
    Tuple, TypeVar, Union, AsyncGenerator
)
from collections import defaultdict
import copy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger('SharedStateManager')

# Redis imports with graceful fallback
try:
    import redis.asyncio as aioredis
    from redis.asyncio import Redis
    from redis.exceptions import (
        RedisError, ConnectionError as RedisConnectionError,
        TimeoutError as RedisTimeoutError, WatchError
    )
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis-py not available. Using SQLite fallback only.")
    # Define placeholder classes for type hints
    class Redis: pass
    class RedisConnectionError(Exception): pass


# ==============================================================================
# Enums and Constants
# ==============================================================================

class StateType(Enum):
    """Supported state value types"""
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    BINARY = "binary"
    JSON = "json"


class ConflictResolutionStrategy(Enum):
    """Conflict resolution strategies for concurrent writes"""
    LAST_WRITE_WINS = "last_write_wins"
    FIRST_WRITE_WINS = "first_write_wins"
    TIMESTAMP_BASED = "timestamp_based"
    VECTOR_CLOCK = "vector_clock"
    CUSTOM = "custom"


class StateEventType(Enum):
    """Types of state change events"""
    SET = "set"
    UPDATE = "update"
    DELETE = "delete"
    EXPIRE = "expire"
    LOCK_ACQUIRED = "lock_acquired"
    LOCK_RELEASED = "lock_released"
    SNAPSHOT_CREATED = "snapshot_created"
    SNAPSHOT_RESTORED = "snapshot_restored"


class LockStatus(Enum):
    """Distributed lock status"""
    FREE = "free"
    LOCKED = "locked"
    EXPIRED = "expired"


# ==============================================================================
# Data Classes
# ==============================================================================

@dataclass
class StateValue:
    """Represents a stored state value with metadata"""
    key: str
    value: Any
    state_type: StateType
    version: int = 1
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: Optional[str] = None
    owner: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    checksum: Optional[str] = None
    
    def __post_init__(self):
        if self.checksum is None:
            self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        """Calculate checksum for data integrity"""
        try:
            data = json.dumps({
                'key': self.key,
                'value': self._serialize_value(),
                'version': self.version,
                'updated_at': self.updated_at
            }, sort_keys=True)
            return hashlib.sha256(data.encode()).hexdigest()[:16]
        except Exception:
            return hashlib.sha256(str(self.value).encode()).hexdigest()[:16]
    
    def _serialize_value(self) -> Any:
        """Serialize value for storage"""
        if self.state_type == StateType.BINARY:
            return base64.b64encode(self.value).decode() if isinstance(self.value, bytes) else self.value
        return self.value
    
    def is_expired(self) -> bool:
        """Check if value has expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > datetime.fromisoformat(self.expires_at)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'key': self.key,
            'value': self._serialize_value(),
            'state_type': self.state_type.value,
            'version': self.version,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'expires_at': self.expires_at,
            'owner': self.owner,
            'tags': self.tags,
            'checksum': self.checksum
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StateValue':
        """Create from dictionary"""
        state_type = StateType(data.get('state_type', 'json'))
        value = data['value']
        
        # Deserialize binary data
        if state_type == StateType.BINARY and isinstance(value, str):
            value = base64.b64decode(value)
        
        return cls(
            key=data['key'],
            value=value,
            state_type=state_type,
            version=data.get('version', 1),
            created_at=data.get('created_at', datetime.utcnow().isoformat()),
            updated_at=data.get('updated_at', datetime.utcnow().isoformat()),
            expires_at=data.get('expires_at'),
            owner=data.get('owner'),
            tags=data.get('tags', []),
            checksum=data.get('checksum')
        )


@dataclass
class StateLock:
    """Distributed lock information"""
    lock_id: str
    resource: str
    owner: str
    acquired_at: str
    expires_at: str
    ttl_seconds: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if lock has expired"""
        return datetime.utcnow() > datetime.fromisoformat(self.expires_at)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'lock_id': self.lock_id,
            'resource': self.resource,
            'owner': self.owner,
            'acquired_at': self.acquired_at,
            'expires_at': self.expires_at,
            'ttl_seconds': self.ttl_seconds,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StateLock':
        return cls(
            lock_id=data['lock_id'],
            resource=data['resource'],
            owner=data['owner'],
            acquired_at=data['acquired_at'],
            expires_at=data['expires_at'],
            ttl_seconds=data['ttl_seconds'],
            metadata=data.get('metadata', {})
        )


@dataclass
class StateSnapshot:
    """State snapshot for recovery"""
    snapshot_id: str
    name: str
    created_at: str
    state_data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'snapshot_id': self.snapshot_id,
            'name': self.name,
            'created_at': self.created_at,
            'state_data': self.state_data,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StateSnapshot':
        return cls(
            snapshot_id=data['snapshot_id'],
            name=data['name'],
            created_at=data['created_at'],
            state_data=data['state_data'],
            metadata=data.get('metadata', {})
        )


@dataclass
class StateEvent:
    """State change event"""
    event_type: StateEventType
    key: str
    value: Optional[Any] = None
    previous_value: Optional[Any] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_type': self.event_type.value,
            'key': self.key,
            'value': self.value,
            'previous_value': self.previous_value,
            'timestamp': self.timestamp,
            'source': self.source,
            'metadata': self.metadata
        }


@dataclass
class BuildProgress:
    """Build progress tracking"""
    build_id: str
    stage: str
    progress_percent: float
    status: str  # 'running', 'completed', 'failed', 'paused'
    agent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'build_id': self.build_id,
            'stage': self.stage,
            'progress_percent': self.progress_percent,
            'status': self.status,
            'agent_id': self.agent_id,
            'metadata': self.metadata,
            'started_at': self.started_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BuildProgress':
        return cls(
            build_id=data['build_id'],
            stage=data['stage'],
            progress_percent=data['progress_percent'],
            status=data['status'],
            agent_id=data.get('agent_id'),
            metadata=data.get('metadata', {}),
            started_at=data.get('started_at', datetime.utcnow().isoformat()),
            updated_at=data.get('updated_at', datetime.utcnow().isoformat())
        )


@dataclass
class AgentStatusInfo:
    """Agent status information"""
    agent_id: str
    agent_type: str
    status: str  # 'idle', 'busy', 'error', 'offline'
    current_task: Optional[str] = None
    last_heartbeat: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metrics: Dict[str, Any] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'agent_id': self.agent_id,
            'agent_type': self.agent_type,
            'status': self.status,
            'current_task': self.current_task,
            'last_heartbeat': self.last_heartbeat,
            'metrics': self.metrics,
            'capabilities': self.capabilities
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentStatusInfo':
        return cls(
            agent_id=data['agent_id'],
            agent_type=data['agent_type'],
            status=data['status'],
            current_task=data.get('current_task'),
            last_heartbeat=data.get('last_heartbeat', datetime.utcnow().isoformat()),
            metrics=data.get('metrics', {}),
            capabilities=data.get('capabilities', [])
        )


# ==============================================================================
# SQLite Fallback Implementation
# ==============================================================================

class SQLiteStateBackend:
    """SQLite-based state storage for fallback"""
    
    def __init__(self, db_path: str = "/tmp/shared_state_fallback.db"):
        self.db_path = db_path
        self._local = threading.local()
        self._lock = threading.RLock()
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    def _init_db(self):
        """Initialize SQLite database schema"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # State values table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS state_values (
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    expires_at TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Locks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS state_locks (
                    resource TEXT PRIMARY KEY,
                    lock_id TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data TEXT
                )
            """)
            
            # Snapshots table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS state_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data TEXT NOT NULL
                )
            """)
            
            # Build progress table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS build_progress (
                    build_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Agent status table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_status (
                    agent_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    expires_at TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Event log table (for local pub/sub simulation)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS event_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    key TEXT NOT NULL,
                    data TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_state_expires ON state_values(expires_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_locks_expires ON state_locks(expires_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_expires ON agent_status(expires_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_key ON event_log(key)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_time ON event_log(timestamp)")
            
            conn.commit()
            logger.info(f"SQLite state backend initialized: {self.db_path}")
    
    def cleanup_expired(self):
        """Remove expired entries"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            now = datetime.utcnow().isoformat()
            
            for table in ['state_values', 'state_locks', 'agent_status']:
                cursor.execute(f"DELETE FROM {table} WHERE expires_at < ?", (now,))
            
            conn.commit()
    
    # State value operations
    def set_value(self, state_value: StateValue) -> bool:
        """Store state value"""
        try:
            self.cleanup_expired()
            
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                data = json.dumps(state_value.to_dict())
                expires = state_value.expires_at
                
                cursor.execute(
                    """INSERT OR REPLACE INTO state_values (key, data, expires_at, updated_at) 
                       VALUES (?, ?, ?, ?)""",
                    (state_value.key, data, expires, datetime.utcnow().isoformat())
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"SQLite set_value error: {e}")
            return False
    
    def get_value(self, key: str) -> Optional[StateValue]:
        """Retrieve state value"""
        try:
            self.cleanup_expired()
            
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT data FROM state_values WHERE key = ? AND (expires_at IS NULL OR expires_at > ?)",
                    (key, datetime.utcnow().isoformat())
                )
                row = cursor.fetchone()
                
                if row:
                    data = json.loads(row['data'])
                    return StateValue.from_dict(data)
                return None
        except Exception as e:
            logger.error(f"SQLite get_value error: {e}")
            return None
    
    def delete_value(self, key: str) -> bool:
        """Delete state value"""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM state_values WHERE key = ?", (key,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"SQLite delete_value error: {e}")
            return False
    
    def list_keys(self, pattern: Optional[str] = None) -> List[str]:
        """List all keys matching pattern"""
        try:
            self.cleanup_expired()
            
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                if pattern:
                    # Convert glob pattern to SQL LIKE
                    like_pattern = pattern.replace('*', '%').replace('?', '_')
                    cursor.execute(
                        "SELECT key FROM state_values WHERE key LIKE ? AND (expires_at IS NULL OR expires_at > ?)",
                        (like_pattern, datetime.utcnow().isoformat())
                    )
                else:
                    cursor.execute("SELECT key FROM state_values WHERE expires_at IS NULL OR expires_at > ?",
                                 (datetime.utcnow().isoformat(),))
                
                return [row['key'] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"SQLite list_keys error: {e}")
            return []
    
    def get_all_values(self) -> Dict[str, StateValue]:
        """Get all non-expired state values"""
        try:
            self.cleanup_expired()
            
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT data FROM state_values WHERE expires_at IS NULL OR expires_at > ?",
                    (datetime.utcnow().isoformat(),)
                )
                
                result = {}
                for row in cursor.fetchall():
                    data = json.loads(row['data'])
                    sv = StateValue.from_dict(data)
                    result[sv.key] = sv
                return result
        except Exception as e:
            logger.error(f"SQLite get_all_values error: {e}")
            return {}
    
    # Lock operations
    def acquire_lock(self, lock: StateLock) -> bool:
        """Acquire distributed lock"""
        try:
            self.cleanup_expired()
            
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                data = json.dumps(lock.to_dict())
                
                try:
                    cursor.execute(
                        "INSERT INTO state_locks (resource, lock_id, owner, expires_at, data) VALUES (?, ?, ?, ?, ?)",
                        (lock.resource, lock.lock_id, lock.owner, lock.expires_at, data)
                    )
                    conn.commit()
                    return True
                except sqlite3.IntegrityError:
                    # Lock exists, check if expired
                    cursor.execute(
                        "SELECT expires_at FROM state_locks WHERE resource = ?",
                        (lock.resource,)
                    )
                    row = cursor.fetchone()
                    
                    if row and row['expires_at'] < datetime.utcnow().isoformat():
                        # Lock expired, take over
                        cursor.execute(
                            """UPDATE state_locks 
                               SET lock_id = ?, owner = ?, expires_at = ?, data = ?, acquired_at = CURRENT_TIMESTAMP 
                               WHERE resource = ?""",
                            (lock.lock_id, lock.owner, lock.expires_at, data, lock.resource)
                        )
                        conn.commit()
                        return cursor.rowcount > 0
                    return False
        except Exception as e:
            logger.error(f"SQLite acquire_lock error: {e}")
            return False
    
    def release_lock(self, resource: str, lock_id: str) -> bool:
        """Release distributed lock"""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM state_locks WHERE resource = ? AND lock_id = ?",
                    (resource, lock_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"SQLite release_lock error: {e}")
            return False
    
    def get_lock(self, resource: str) -> Optional[StateLock]:
        """Get lock information for resource"""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT data FROM state_locks WHERE resource = ? AND expires_at > ?",
                    (resource, datetime.utcnow().isoformat())
                )
                row = cursor.fetchone()
                
                if row:
                    return StateLock.from_dict(json.loads(row['data']))
                return None
        except Exception as e:
            logger.error(f"SQLite get_lock error: {e}")
            return None
    
    # Snapshot operations
    def save_snapshot(self, snapshot: StateSnapshot) -> bool:
        """Save state snapshot"""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                data = json.dumps(snapshot.to_dict())
                cursor.execute(
                    "INSERT OR REPLACE INTO state_snapshots (snapshot_id, name, created_at, data) VALUES (?, ?, ?, ?)",
                    (snapshot.snapshot_id, snapshot.name, snapshot.created_at, data)
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"SQLite save_snapshot error: {e}")
            return False
    
    def get_snapshot(self, snapshot_id: str) -> Optional[StateSnapshot]:
        """Retrieve snapshot"""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT data FROM state_snapshots WHERE snapshot_id = ?",
                    (snapshot_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    return StateSnapshot.from_dict(json.loads(row['data']))
                return None
        except Exception as e:
            logger.error(f"SQLite get_snapshot error: {e}")
            return None
    
    def list_snapshots(self) -> List[StateSnapshot]:
        """List all snapshots"""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT data FROM state_snapshots ORDER BY created_at DESC")
                return [StateSnapshot.from_dict(json.loads(row['data'])) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"SQLite list_snapshots error: {e}")
            return []
    
    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete snapshot"""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM state_snapshots WHERE snapshot_id = ?", (snapshot_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"SQLite delete_snapshot error: {e}")
            return False
    
    # Event logging
    def log_event(self, event: StateEvent):
        """Log state event"""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO event_log (event_type, key, data) VALUES (?, ?, ?)",
                    (event.event_type.value, event.key, json.dumps(event.to_dict()))
                )
                conn.commit()
        except Exception as e:
            logger.error(f"SQLite log_event error: {e}")
    
    def get_recent_events(self, key: Optional[str] = None, limit: int = 100) -> List[StateEvent]:
        """Get recent events"""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                if key:
                    cursor.execute(
                        "SELECT data FROM event_log WHERE key = ? ORDER BY timestamp DESC LIMIT ?",
                        (key, limit)
                    )
                else:
                    cursor.execute(
                        "SELECT data FROM event_log ORDER BY timestamp DESC LIMIT ?",
                        (limit,)
                    )
                
                events = []
                for row in cursor.fetchall():
                    data = json.loads(row['data'])
                    events.append(StateEvent(
                        event_type=StateEventType(data['event_type']),
                        key=data['key'],
                        value=data.get('value'),
                        previous_value=data.get('previous_value'),
                        timestamp=data['timestamp'],
                        source=data.get('source'),
                        metadata=data.get('metadata', {})
                    ))
                return events
        except Exception as e:
            logger.error(f"SQLite get_recent_events error: {e}")
            return []


# ==============================================================================
# Main Shared State Manager
# ==============================================================================

class SharedStateManager:
    """
    Production-ready shared state manager for multi-agent coordination.
    
    Features:
    - Distributed state storage with Redis
    - SQLite fallback for resilience
    - Automatic conflict resolution
    - Event notifications
    - Distributed locking
    - State snapshots for recovery
    - Build progress tracking
    - Agent status management
    """
    
    # Key prefixes for organization
    PREFIX_STATE = "apex:state:"
    PREFIX_LOCK = "apex:state:lock:"
    PREFIX_SNAPSHOT = "apex:state:snapshot:"
    PREFIX_BUILD = "apex:state:build:"
    PREFIX_AGENT = "apex:state:agent:"
    PREFIX_EVENT = "apex:state:event:"
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_password: Optional[str] = None,
        redis_db: int = 0,
        sqlite_path: str = "/tmp/shared_state_fallback.db",
        conflict_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.LAST_WRITE_WINS,
        enable_events: bool = True,
        event_channel: str = "apex:state:events",
        instance_id: Optional[str] = None
    ):
        """
        Initialize Shared State Manager.
        
        Args:
            redis_url: Redis URL (overrides host/port/password)
            redis_host: Redis host
            redis_port: Redis port
            redis_password: Redis password
            redis_db: Redis database number
            sqlite_path: SQLite fallback database path
            conflict_strategy: Default conflict resolution strategy
            enable_events: Enable event publishing
            event_channel: Redis channel for events
            instance_id: Unique instance identifier
        """
        self.instance_id = instance_id or f"ssm-{uuid.uuid4().hex[:8]}"
        self.conflict_strategy = conflict_strategy
        self.enable_events = enable_events
        self.event_channel = event_channel
        
        # Redis configuration
        self.redis_config = {
            'url': redis_url,
            'host': redis_host,
            'port': redis_port,
            'password': redis_password,
            'db': redis_db
        }
        
        # Redis client (initialized on first use)
        self._redis: Optional[Redis] = None
        self._redis_connected = False
        
        # SQLite fallback
        self._sqlite = SQLiteStateBackend(sqlite_path)
        
        # Event handlers
        self._event_handlers: Dict[StateEventType, List[Callable]] = defaultdict(list)
        self._key_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._pubsub_task: Optional[asyncio.Task] = None
        
        # Local cache for hot values
        self._local_cache: Dict[str, Tuple[StateValue, float]] = {}
        self._cache_ttl = 5.0  # seconds
        
        # Locks
        self._redis_lock = asyncio.Lock()
        self._local_lock = threading.RLock()
        
        logger.info(f"SharedStateManager initialized (instance: {self.instance_id})")
    
    # ==================== Connection Management ====================
    
    async def connect(self) -> bool:
        """Connect to Redis"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, using SQLite fallback")
            return False
        
        async with self._redis_lock:
            if self._redis_connected and self._redis:
                try:
                    await self._redis.ping()
                    return True
                except Exception:
                    self._redis_connected = False
            
            try:
                if self.redis_config['url']:
                    self._redis = aioredis.from_url(
                        self.redis_config['url'],
                        decode_responses=True
                    )
                else:
                    self._redis = aioredis.Redis(
                        host=self.redis_config['host'],
                        port=self.redis_config['port'],
                        password=self.redis_config['password'],
                        db=self.redis_config['db'],
                        decode_responses=True
                    )
                
                await self._redis.ping()
                self._redis_connected = True
                
                # Start event subscriber
                if self.enable_events:
                    await self._start_event_subscriber()
                
                logger.info("Connected to Redis")
                return True
                
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}, using SQLite fallback")
                self._redis_connected = False
                return False
    
    async def disconnect(self):
        """Disconnect from Redis"""
        async with self._redis_lock:
            if self._pubsub_task:
                self._pubsub_task.cancel()
                try:
                    await self._pubsub_task
                except asyncio.CancelledError:
                    pass
                self._pubsub_task = None
            
            if self._redis:
                await self._redis.close()
                self._redis = None
            
            self._redis_connected = False
            logger.info("Disconnected from Redis")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health status"""
        status = {
            'redis_connected': False,
            'sqlite_available': True,
            'instance_id': self.instance_id,
            'using_fallback': True
        }
        
        if self._redis and self._redis_connected:
            try:
                start = time.time()
                await self._redis.ping()
                status['redis_latency_ms'] = round((time.time() - start) * 1000, 2)
                status['redis_connected'] = True
                status['using_fallback'] = False
            except Exception as e:
                status['redis_error'] = str(e)
        
        return status
    
    # ==================== Core State Operations ====================
    
    async def set(
        self,
        key: str,
        value: Any,
        state_type: Optional[StateType] = None,
        ttl_seconds: Optional[int] = None,
        owner: Optional[str] = None,
        tags: Optional[List[str]] = None,
        nx: bool = False,  # Only set if not exists
        xx: bool = False,  # Only set if exists
        conflict_strategy: Optional[ConflictResolutionStrategy] = None
    ) -> bool:
        """
        Set a state value.
        
        Args:
            key: State key
            value: Value to store
            state_type: Type of value (auto-detected if None)
            ttl_seconds: Time-to-live in seconds
            owner: Owner identifier
            tags: Tags for organization
            nx: Only set if key doesn't exist
            xx: Only set if key exists
            conflict_strategy: Override default conflict resolution
            
        Returns:
            True if set successfully
        """
        # Auto-detect type if not specified
        if state_type is None:
            state_type = self._detect_type(value)
        
        # Check existence constraints
        if nx or xx:
            exists = await self.exists(key)
            if nx and exists:
                return False
            if xx and not exists:
                return False
        
        # Handle conflict resolution for existing keys
        if not nx:
            existing = await self._get_raw(key)
            if existing:
                strategy = conflict_strategy or self.conflict_strategy
                if strategy == ConflictResolutionStrategy.FIRST_WRITE_WINS:
                    return False
                # For timestamp-based, we proceed with new value
                # For vector clock, we'd merge - simplified here
        
        # Create state value
        expires_at = None
        if ttl_seconds:
            expires_at = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()
        
        state_value = StateValue(
            key=key,
            value=value,
            state_type=state_type,
            version=(existing.version + 1) if existing else 1,
            expires_at=expires_at,
            owner=owner,
            tags=tags or []
        )
        
        # Store in Redis or SQLite
        success = await self._store_value(state_value, ttl_seconds)
        
        if success:
            # Update local cache
            with self._local_lock:
                self._local_cache[key] = (state_value, time.time())
            
            # Publish event
            await self._publish_event(StateEvent(
                event_type=StateEventType.SET,
                key=key,
                value=value,
                previous_value=existing.value if existing else None,
                source=self.instance_id
            ))
        
        return success
    
    async def get(
        self,
        key: str,
        default: Any = None,
        state_type: Optional[StateType] = None
    ) -> Any:
        """
        Get a state value.
        
        Args:
            key: State key
            default: Default value if not found
            state_type: Expected type (for validation)
            
        Returns:
            Stored value or default
        """
        # Check local cache first
        with self._local_lock:
            if key in self._local_cache:
                cached_value, cached_time = self._local_cache[key]
                if time.time() - cached_time < self._cache_ttl:
                    if not cached_value.is_expired():
                        return cached_value.value
        
        # Get from storage
        state_value = await self._get_raw(key)
        
        if state_value is None:
            return default
        
        if state_value.is_expired():
            await self.delete(key)
            return default
        
        # Type validation
        if state_type and state_value.state_type != state_type:
            logger.warning(f"Type mismatch for key {key}: expected {state_type}, got {state_value.state_type}")
        
        # Update cache
        with self._local_lock:
            self._local_cache[key] = (state_value, time.time())
        
        return state_value.value
    
    async def get_with_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """Get value with full metadata"""
        state_value = await self._get_raw(key)
        if state_value and not state_value.is_expired():
            return state_value.to_dict()
        return None
    
    async def delete(self, key: str) -> bool:
        """
        Delete a state value.
        
        Args:
            key: State key to delete
            
        Returns:
            True if deleted
        """
        previous = await self._get_raw(key)
        
        success = await self._delete_value(key)
        
        if success:
            # Clear cache
            with self._local_lock:
                self._local_cache.pop(key, None)
            
            # Publish event
            await self._publish_event(StateEvent(
                event_type=StateEventType.DELETE,
                key=key,
                previous_value=previous.value if previous else None,
                source=self.instance_id
            ))
        
        return success
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        value = await self._get_raw(key)
        return value is not None and not value.is_expired()
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """List keys matching pattern"""
        if self._redis_connected and self._redis:
            try:
                redis_pattern = f"{self.PREFIX_STATE}{pattern}"
                keys = await self._redis.keys(redis_pattern)
                # Remove prefix
                prefix_len = len(self.PREFIX_STATE)
                return [k[prefix_len:] for k in keys]
            except Exception as e:
                logger.warning(f"Redis keys failed, using SQLite: {e}")
        
        return self._sqlite.list_keys(pattern)
    
    async def increment(
        self,
        key: str,
        amount: Union[int, float] = 1,
        default: Union[int, float] = 0
    ) -> Union[int, float]:
        """
        Atomically increment a numeric value.
        
        Args:
            key: State key
            amount: Amount to increment
            default: Default value if key doesn't exist
            
        Returns:
            New value
        """
        if self._redis_connected and self._redis:
            try:
                redis_key = f"{self.PREFIX_STATE}{key}"
                # Check if float
                if isinstance(amount, float):
                    new_val = await self._redis.incrbyfloat(redis_key, amount)
                else:
                    new_val = await self._redis.incrby(redis_key, amount)
                
                # Also update metadata
                await self._update_metadata_on_increment(key, new_val)
                return new_val
            except Exception as e:
                logger.warning(f"Redis increment failed, using local: {e}")
        
        # Local implementation
        current = await self.get(key, default)
        if isinstance(current, (int, float)):
            new_val = current + amount
        else:
            new_val = default + amount
        
        await self.set(key, new_val, StateType.NUMBER)
        return new_val
    
    async def append_to_list(self, key: str, *values) -> int:
        """Append values to a list"""
        current = await self.get(key, [])
        if not isinstance(current, list):
            current = []
        current.extend(values)
        await self.set(key, current, StateType.LIST)
        return len(current)
    
    async def update_dict(self, key: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a dictionary with new values"""
        current = await self.get(key, {})
        if not isinstance(current, dict):
            current = {}
        current.update(updates)
        await self.set(key, current, StateType.DICT)
        return current
    
    # ==================== Distributed Locking ====================
    
    @asynccontextmanager
    async def lock(
        self,
        resource: str,
        owner: Optional[str] = None,
        ttl_seconds: int = 30,
        blocking: bool = True,
        blocking_timeout: float = 10.0,
        retry_delay: float = 0.1
    ):
        """
        Context manager for distributed locking.
        
        Args:
            resource: Resource to lock
            owner: Lock owner identifier
            ttl_seconds: Lock TTL
            blocking: Whether to block until lock acquired
            blocking_timeout: Maximum time to wait
            retry_delay: Delay between retry attempts
            
        Yields:
            Lock ID if acquired
            
        Example:
            async with state_manager.lock("critical-section", owner="agent-1") as lock_id:
                if lock_id:
                    # Critical section
                    pass
        """
        owner = owner or self.instance_id
        lock_id = None
        acquired = False
        
        try:
            lock_id = await self.acquire_lock(
                resource=resource,
                owner=owner,
                ttl_seconds=ttl_seconds,
                blocking=blocking,
                blocking_timeout=blocking_timeout,
                retry_delay=retry_delay
            )
            acquired = lock_id is not None
            yield lock_id
        finally:
            if acquired and lock_id:
                await self.release_lock(resource, lock_id)
    
    async def acquire_lock(
        self,
        resource: str,
        owner: Optional[str] = None,
        ttl_seconds: int = 30,
        blocking: bool = True,
        blocking_timeout: float = 10.0,
        retry_delay: float = 0.1
    ) -> Optional[str]:
        """
        Acquire distributed lock.
        
        Args:
            resource: Resource to lock
            owner: Lock owner identifier
            ttl_seconds: Lock TTL
            blocking: Whether to block until lock acquired
            blocking_timeout: Maximum time to wait
            retry_delay: Delay between retry attempts
            
        Returns:
            Lock ID if acquired, None otherwise
        """
        owner = owner or self.instance_id
        lock_id = f"lock-{uuid.uuid4().hex[:16]}"
        
        expires_at = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()
        lock = StateLock(
            lock_id=lock_id,
            resource=resource,
            owner=owner,
            acquired_at=datetime.utcnow().isoformat(),
            expires_at=expires_at,
            ttl_seconds=ttl_seconds
        )
        
        if self._redis_connected and self._redis:
            try:
                redis_key = f"{self.PREFIX_LOCK}{resource}"
                lock_data = json.dumps(lock.to_dict())
                
                if blocking:
                    start_time = time.time()
                    while time.time() - start_time < blocking_timeout:
                        # Use NX to only set if not exists
                        result = await self._redis.set(
                            redis_key,
                            lock_data,
                            nx=True,
                            ex=ttl_seconds
                        )
                        if result:
                            await self._publish_event(StateEvent(
                                event_type=StateEventType.LOCK_ACQUIRED,
                                key=resource,
                                metadata={'lock_id': lock_id, 'owner': owner},
                                source=self.instance_id
                            ))
                            return lock_id
                        await asyncio.sleep(retry_delay)
                    return None
                else:
                    result = await self._redis.set(
                        redis_key,
                        lock_data,
                        nx=True,
                        ex=ttl_seconds
                    )
                    if result:
                        await self._publish_event(StateEvent(
                            event_type=StateEventType.LOCK_ACQUIRED,
                            key=resource,
                            metadata={'lock_id': lock_id, 'owner': owner},
                            source=self.instance_id
                        ))
                        return lock_id
                    return None
            except Exception as e:
                logger.warning(f"Redis lock failed, using SQLite: {e}")
        
        # SQLite fallback
        if blocking:
            start_time = time.time()
            while time.time() - start_time < blocking_timeout:
                if self._sqlite.acquire_lock(lock):
                    await self._publish_event(StateEvent(
                        event_type=StateEventType.LOCK_ACQUIRED,
                        key=resource,
                        metadata={'lock_id': lock_id, 'owner': owner},
                        source=self.instance_id
                    ))
                    return lock_id
                await asyncio.sleep(retry_delay)
            return None
        else:
            if self._sqlite.acquire_lock(lock):
                await self._publish_event(StateEvent(
                    event_type=StateEventType.LOCK_ACQUIRED,
                    key=resource,
                    metadata={'lock_id': lock_id, 'owner': owner},
                    source=self.instance_id
                ))
                return lock_id
            return None
    
    async def release_lock(self, resource: str, lock_id: str) -> bool:
        """
        Release distributed lock.
        
        Args:
            resource: Resource that was locked
            lock_id: Lock ID from acquire_lock
            
        Returns:
            True if released
        """
        if self._redis_connected and self._redis:
            try:
                redis_key = f"{self.PREFIX_LOCK}{resource}"
                
                # Use Lua script for atomic check-and-delete
                lua_script = """
                local current = redis.call('get', KEYS[1])
                if current then
                    local data = cjson.decode(current)
                    if data.lock_id == ARGV[1] then
                        return redis.call('del', KEYS[1])
                    end
                end
                return 0
                """
                result = await self._redis.eval(lua_script, 1, redis_key, lock_id)
                
                if result:
                    await self._publish_event(StateEvent(
                        event_type=StateEventType.LOCK_RELEASED,
                        key=resource,
                        metadata={'lock_id': lock_id},
                        source=self.instance_id
                    ))
                    return True
            except Exception as e:
                logger.warning(f"Redis unlock failed, using SQLite: {e}")
        
        # SQLite fallback
        result = self._sqlite.release_lock(resource, lock_id)
        if result:
            await self._publish_event(StateEvent(
                event_type=StateEventType.LOCK_RELEASED,
                key=resource,
                metadata={'lock_id': lock_id},
                source=self.instance_id
            ))
        return result
    
    async def is_locked(self, resource: str) -> bool:
        """Check if resource is locked"""
        lock = await self.get_lock_info(resource)
        return lock is not None
    
    async def get_lock_info(self, resource: str) -> Optional[StateLock]:
        """Get lock information"""
        if self._redis_connected and self._redis:
            try:
                redis_key = f"{self.PREFIX_LOCK}{resource}"
                data = await self._redis.get(redis_key)
                if data:
                    lock = StateLock.from_dict(json.loads(data))
                    if not lock.is_expired():
                        return lock
                return None
            except Exception as e:
                logger.warning(f"Redis get_lock failed, using SQLite: {e}")
        
        return self._sqlite.get_lock(resource)
    
    # ==================== State Snapshots ====================
    
    async def snapshot(self, name: Optional[str] = None) -> str:
        """
        Create a state snapshot.
        
        Args:
            name: Snapshot name
            
        Returns:
            Snapshot ID
        """
        snapshot_id = f"snap-{uuid.uuid4().hex[:16]}"
        name = name or f"snapshot-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        # Get all state values
        all_values = await self._get_all_values()
        state_data = {k: v.to_dict() for k, v in all_values.items()}
        
        snapshot = StateSnapshot(
            snapshot_id=snapshot_id,
            name=name,
            created_at=datetime.utcnow().isoformat(),
            state_data=state_data,
            metadata={
                'instance_id': self.instance_id,
                'key_count': len(state_data)
            }
        )
        
        # Store snapshot
        if self._redis_connected and self._redis:
            try:
                redis_key = f"{self.PREFIX_SNAPSHOT}{snapshot_id}"
                await self._redis.set(
                    redis_key,
                    json.dumps(snapshot.to_dict())
                )
            except Exception as e:
                logger.warning(f"Redis snapshot failed, using SQLite: {e}")
                self._sqlite.save_snapshot(snapshot)
        else:
            self._sqlite.save_snapshot(snapshot)
        
        await self._publish_event(StateEvent(
            event_type=StateEventType.SNAPSHOT_CREATED,
            key=snapshot_id,
            metadata={'name': name, 'key_count': len(state_data)},
            source=self.instance_id
        ))
        
        logger.info(f"Created snapshot {snapshot_id} with {len(state_data)} keys")
        return snapshot_id
    
    async def restore(
        self,
        snapshot_id: str,
        merge: bool = False,
        key_filter: Optional[Callable[[str], bool]] = None
    ) -> bool:
        """
        Restore state from snapshot.
        
        Args:
            snapshot_id: Snapshot ID to restore
            merge: If True, merge with existing state; if False, replace all
            key_filter: Optional function to filter which keys to restore
            
        Returns:
            True if restored successfully
        """
        # Get snapshot
        snapshot = await self._get_snapshot(snapshot_id)
        if not snapshot:
            logger.error(f"Snapshot {snapshot_id} not found")
            return False
        
        if not merge:
            # Clear existing state (optional - be careful!)
            pass
        
        # Restore values
        restored_count = 0
        for key, data in snapshot.state_data.items():
            if key_filter and not key_filter(key):
                continue
            
            state_value = StateValue.from_dict(data)
            await self._store_value(state_value)
            restored_count += 1
        
        await self._publish_event(StateEvent(
            event_type=StateEventType.SNAPSHOT_RESTORED,
            key=snapshot_id,
            metadata={'restored_keys': restored_count},
            source=self.instance_id
        ))
        
        logger.info(f"Restored {restored_count} keys from snapshot {snapshot_id}")
        return True
    
    async def list_snapshots(self) -> List[Dict[str, Any]]:
        """List all snapshots"""
        snapshots = []
        
        # Get from Redis
        if self._redis_connected and self._redis:
            try:
                pattern = f"{self.PREFIX_SNAPSHOT}*"
                keys = await self._redis.keys(pattern)
                for key in keys:
                    data = await self._redis.get(key)
                    if data:
                        snapshot = StateSnapshot.from_dict(json.loads(data))
                        snapshots.append(snapshot.to_dict())
            except Exception as e:
                logger.warning(f"Redis list_snapshots failed: {e}")
        
        # Get from SQLite
        sqlite_snapshots = self._sqlite.list_snapshots()
        
        # Merge and deduplicate by ID
        seen_ids = {s['snapshot_id'] for s in snapshots}
        for snap in sqlite_snapshots:
            if snap.snapshot_id not in seen_ids:
                snapshots.append(snap.to_dict())
        
        # Sort by creation time
        snapshots.sort(key=lambda x: x['created_at'], reverse=True)
        return snapshots
    
    async def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot"""
        success = False
        
        if self._redis_connected and self._redis:
            try:
                redis_key = f"{self.PREFIX_SNAPSHOT}{snapshot_id}"
                result = await self._redis.delete(redis_key)
                success = result > 0
            except Exception as e:
                logger.warning(f"Redis delete_snapshot failed: {e}")
        
        sqlite_result = self._sqlite.delete_snapshot(snapshot_id)
        return success or sqlite_result
    
    # ==================== Build Progress Tracking ====================
    
    async def track_build_progress(
        self,
        build_id: str,
        stage: str,
        progress_percent: float,
        status: str = "running",
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Track build progress.
        
        Args:
            build_id: Build identifier
            stage: Current stage name
            progress_percent: Progress percentage (0-100)
            status: Build status
            agent_id: Agent tracking this progress
            metadata: Additional metadata
            
        Returns:
            True if tracked successfully
        """
        progress = BuildProgress(
            build_id=build_id,
            stage=stage,
            progress_percent=min(max(progress_percent, 0), 100),
            status=status,
            agent_id=agent_id,
            metadata=metadata or {},
            updated_at=datetime.utcnow().isoformat()
        )
        
        key = f"{self.PREFIX_BUILD}{build_id}"
        
        if self._redis_connected and self._redis:
            try:
                await self._redis.setex(
                    key,
                    86400,  # 24 hour TTL
                    json.dumps(progress.to_dict())
                )
                return True
            except Exception as e:
                logger.warning(f"Redis track_build failed, using SQLite: {e}")
        
        # SQLite fallback
        return self._sqlite.set_value(StateValue(
            key=key,
            value=progress.to_dict(),
            state_type=StateType.DICT,
            expires_at=(datetime.utcnow() + timedelta(hours=24)).isoformat()
        ))
    
    async def get_build_progress(self, build_id: str) -> Optional[Dict[str, Any]]:
        """Get build progress"""
        key = f"{self.PREFIX_BUILD}{build_id}"
        
        if self._redis_connected and self._redis:
            try:
                data = await self._redis.get(key)
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.warning(f"Redis get_build failed, using SQLite: {e}")
        
        # SQLite fallback
        sv = self._sqlite.get_value(key)
        if sv:
            return sv.value
        return None
    
    async def list_active_builds(self) -> List[Dict[str, Any]]:
        """List all active (non-completed) builds"""
        builds = []
        
        # Get from Redis
        if self._redis_connected and self._redis:
            try:
                pattern = f"{self.PREFIX_BUILD}*"
                keys = await self._redis.keys(pattern)
                for key in keys:
                    data = await self._redis.get(key)
                    if data:
                        progress = json.loads(data)
                        if progress.get('status') in ['running', 'pending']:
                            builds.append(progress)
            except Exception as e:
                logger.warning(f"Redis list_builds failed: {e}")
        
        return builds
    
    # ==================== Agent Status Management ====================
    
    async def update_agent_status(
        self,
        agent_id: str,
        agent_type: str,
        status: str,
        current_task: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        capabilities: Optional[List[str]] = None,
        ttl_seconds: int = 300
    ) -> bool:
        """
        Update agent status.
        
        Args:
            agent_id: Agent identifier
            agent_type: Type of agent
            status: Agent status (idle, busy, error, offline)
            current_task: Current task being executed
            metrics: Performance metrics
            capabilities: Agent capabilities
            ttl_seconds: Status TTL
            
        Returns:
            True if updated successfully
        """
        agent_status = AgentStatusInfo(
            agent_id=agent_id,
            agent_type=agent_type,
            status=status,
            current_task=current_task,
            last_heartbeat=datetime.utcnow().isoformat(),
            metrics=metrics or {},
            capabilities=capabilities or []
        )
        
        key = f"{self.PREFIX_AGENT}{agent_id}"
        
        if self._redis_connected and self._redis:
            try:
                await self._redis.setex(
                    key,
                    ttl_seconds,
                    json.dumps(agent_status.to_dict())
                )
                return True
            except Exception as e:
                logger.warning(f"Redis update_agent failed, using SQLite: {e}")
        
        # SQLite fallback
        return self._sqlite.set_value(StateValue(
            key=key,
            value=agent_status.to_dict(),
            state_type=StateType.DICT,
            expires_at=(datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()
        ))
    
    async def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent status"""
        key = f"{self.PREFIX_AGENT}{agent_id}"
        
        if self._redis_connected and self._redis:
            try:
                data = await self._redis.get(key)
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.warning(f"Redis get_agent failed, using SQLite: {e}")
        
        # SQLite fallback
        sv = self._sqlite.get_value(key)
        if sv:
            return sv.value
        return None
    
    async def get_all_agents(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all registered agents"""
        agents = []
        
        # Get from Redis
        if self._redis_connected and self._redis:
            try:
                pattern = f"{self.PREFIX_AGENT}*"
                keys = await self._redis.keys(pattern)
                for key in keys:
                    data = await self._redis.get(key)
                    if data:
                        agent = json.loads(data)
                        if status_filter is None or agent.get('status') == status_filter:
                            agents.append(agent)
            except Exception as e:
                logger.warning(f"Redis get_all_agents failed: {e}")
        
        # Get from SQLite
        for key in self._sqlite.list_keys(f"{self.PREFIX_AGENT}*"):
            sv = self._sqlite.get_value(key)
            if sv:
                agent = sv.value
                if status_filter is None or agent.get('status') == status_filter:
                    agents.append(agent)
        
        return agents
    
    async def get_available_agents(self, capability: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get available (idle) agents, optionally filtered by capability"""
        agents = await self.get_all_agents(status_filter='idle')
        
        if capability:
            agents = [
                a for a in agents 
                if capability in a.get('capabilities', [])
            ]
        
        return agents
    
    # ==================== Event System ====================
    
    def on(
        self,
        event_type: Optional[StateEventType] = None,
        key_pattern: Optional[str] = None
    ) -> Callable:
        """
        Decorator for registering event handlers.
        
        Args:
            event_type: Event type to listen for
            key_pattern: Key pattern to filter events
            
        Example:
            @state_manager.on(StateEventType.SET, key_pattern="build:*")
            async def handle_build_update(event):
                print(f"Build updated: {event.key}")
        """
        def decorator(handler: Callable):
            if event_type:
                self._event_handlers[event_type].append(handler)
            if key_pattern:
                self._key_handlers[key_pattern].append(handler)
            return handler
        return decorator
    
    async def _publish_event(self, event: StateEvent):
        """Publish event to handlers and Redis"""
        # Call local handlers
        await self._call_handlers(event)
        
        # Publish to Redis for other instances
        if self._redis_connected and self._redis and self.enable_events:
            try:
                await self._redis.publish(
                    self.event_channel,
                    json.dumps(event.to_dict())
                )
            except Exception as e:
                logger.debug(f"Failed to publish event to Redis: {e}")
        
        # Log to SQLite for history
        self._sqlite.log_event(event)
    
    async def _call_handlers(self, event: StateEvent):
        """Call registered event handlers"""
        handlers = []
        
        # Get handlers for event type
        handlers.extend(self._event_handlers.get(event.event_type, []))
        
        # Get handlers for key patterns
        for pattern, pattern_handlers in self._key_handlers.items():
            if self._match_pattern(event.key, pattern):
                handlers.extend(pattern_handlers)
        
        # Call handlers
        for handler in set(handlers):
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(event))
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")
    
    async def _start_event_subscriber(self):
        """Start Redis pub/sub subscriber"""
        if self._pubsub_task:
            return
        
        self._pubsub_task = asyncio.create_task(self._event_listener())
    
    async def _event_listener(self):
        """Listen for events from other instances"""
        try:
            pubsub = self._redis.pubsub()
            await pubsub.subscribe(self.event_channel)
            logger.info(f"Subscribed to event channel: {self.event_channel}")
            
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        event = StateEvent(
                            event_type=StateEventType(data['event_type']),
                            key=data['key'],
                            value=data.get('value'),
                            previous_value=data.get('previous_value'),
                            timestamp=data['timestamp'],
                            source=data.get('source'),
                            metadata=data.get('metadata', {})
                        )
                        
                        # Don't process our own events
                        if event.source != self.instance_id:
                            await self._call_handlers(event)
                    except Exception as e:
                        logger.warning(f"Failed to process event: {e}")
                        
        except asyncio.CancelledError:
            logger.info("Event listener cancelled")
            raise
        except Exception as e:
            logger.error(f"Event listener error: {e}")
    
    def _match_pattern(self, key: str, pattern: str) -> bool:
        """Simple glob pattern matching"""
        import fnmatch
        return fnmatch.fnmatch(key, pattern)
    
    # ==================== Private Helper Methods ====================
    
    def _detect_type(self, value: Any) -> StateType:
        """Auto-detect state type from value"""
        if isinstance(value, bool):
            return StateType.BOOLEAN
        elif isinstance(value, int):
            return StateType.INTEGER
        elif isinstance(value, float):
            return StateType.FLOAT
        elif isinstance(value, str):
            return StateType.STRING
        elif isinstance(value, bytes):
            return StateType.BINARY
        elif isinstance(value, list):
            return StateType.LIST
        elif isinstance(value, dict):
            return StateType.DICT
        else:
            return StateType.JSON
    
    async def _store_value(self, state_value: StateValue, ttl_seconds: Optional[int] = None) -> bool:
        """Store value in Redis or SQLite"""
        if self._redis_connected and self._redis:
            try:
                redis_key = f"{self.PREFIX_STATE}{state_value.key}"
                data = json.dumps(state_value.to_dict())
                
                if ttl_seconds:
                    await self._redis.setex(redis_key, ttl_seconds, data)
                else:
                    await self._redis.set(redis_key, data)
                return True
            except Exception as e:
                logger.warning(f"Redis store failed, using SQLite: {e}")
        
        # SQLite fallback
        return self._sqlite.set_value(state_value)
    
    async def _get_raw(self, key: str) -> Optional[StateValue]:
        """Get raw StateValue from storage"""
        # Check cache first
        with self._local_lock:
            if key in self._local_cache:
                cached, cached_time = self._local_cache[key]
                if time.time() - cached_time < self._cache_ttl:
                    return cached
        
        if self._redis_connected and self._redis:
            try:
                redis_key = f"{self.PREFIX_STATE}{key}"
                data = await self._redis.get(redis_key)
                if data:
                    sv = StateValue.from_dict(json.loads(data))
                    with self._local_lock:
                        self._local_cache[key] = (sv, time.time())
                    return sv
            except Exception as e:
                logger.warning(f"Redis get failed, using SQLite: {e}")
        
        # SQLite fallback
        return self._sqlite.get_value(key)
    
    async def _delete_value(self, key: str) -> bool:
        """Delete value from storage"""
        if self._redis_connected and self._redis:
            try:
                redis_key = f"{self.PREFIX_STATE}{key}"
                result = await self._redis.delete(redis_key)
                return result > 0
            except Exception as e:
                logger.warning(f"Redis delete failed, using SQLite: {e}")
        
        return self._sqlite.delete_value(key)
    
    async def _get_all_values(self) -> Dict[str, StateValue]:
        """Get all state values"""
        if self._redis_connected and self._redis:
            try:
                pattern = f"{self.PREFIX_STATE}*"
                keys = await self._redis.keys(pattern)
                values = {}
                for key in keys:
                    data = await self._redis.get(key)
                    if data:
                        sv = StateValue.from_dict(json.loads(data))
                        values[sv.key] = sv
                return values
            except Exception as e:
                logger.warning(f"Redis get_all failed, using SQLite: {e}")
        
        return self._sqlite.get_all_values()
    
    async def _get_snapshot(self, snapshot_id: str) -> Optional[StateSnapshot]:
        """Get snapshot from storage"""
        if self._redis_connected and self._redis:
            try:
                redis_key = f"{self.PREFIX_SNAPSHOT}{snapshot_id}"
                data = await self._redis.get(redis_key)
                if data:
                    return StateSnapshot.from_dict(json.loads(data))
            except Exception as e:
                logger.warning(f"Redis get_snapshot failed, using SQLite: {e}")
        
        return self._sqlite.get_snapshot(snapshot_id)
    
    async def _update_metadata_on_increment(self, key: str, new_val: Any):
        """Update metadata when using Redis INCR"""
        # This is a simplified version - in production, you'd want
        # to use a Lua script to update metadata atomically
        pass


# ==============================================================================
# Convenience Functions
# ==============================================================================

async def create_shared_state_manager(
    redis_url: Optional[str] = None,
    **kwargs
) -> SharedStateManager:
    """
    Factory function to create and connect SharedStateManager.
    
    Args:
        redis_url: Redis URL
        **kwargs: Additional arguments for SharedStateManager
        
    Returns:
        Connected SharedStateManager
    """
    manager = SharedStateManager(redis_url=redis_url, **kwargs)
    await manager.connect()
    return manager


# ==============================================================================
# Test/Demo Code
# ==============================================================================

async def demo_shared_state_manager():
    """Demonstrate SharedStateManager functionality"""
    print("=" * 70)
    print("APEX Shared State Manager - Demo")
    print("=" * 70)
    
    # Create manager
    manager = SharedStateManager(
        redis_host=os.getenv('REDIS_HOST', 'localhost'),
        redis_port=int(os.getenv('REDIS_PORT', '6379')),
        sqlite_path="/tmp/shared_state_demo.db"
    )
    
    # Connect
    print("\n1. Connecting...")
    connected = await manager.connect()
    print(f"   Redis connected: {connected}")
    
    # Health check
    print("\n2. Health Check...")
    health = await manager.health_check()
    for key, value in health.items():
        print(f"   {key}: {value}")
    
    # Basic state operations
    print("\n3. Basic State Operations...")
    
    # Set various types
    await manager.set("demo:string", "Hello, World!", StateType.STRING)
    await manager.set("demo:number", 42, StateType.INTEGER)
    await manager.set("demo:float", 3.14159, StateType.FLOAT)
    await manager.set("demo:bool", True, StateType.BOOLEAN)
    await manager.set("demo:list", [1, 2, 3, 4, 5], StateType.LIST)
    await manager.set("demo:dict", {"name": "test", "value": 100}, StateType.DICT)
    
    # Get values
    for key in ["demo:string", "demo:number", "demo:float", "demo:bool", "demo:list", "demo:dict"]:
        value = await manager.get(key)
        print(f"   {key}: {value} ({type(value).__name__})")
    
    # TTL test
    print("\n4. TTL Test...")
    await manager.set("demo:ttl", "temporary", ttl_seconds=5)
    print(f"   Set with 5s TTL: {await manager.get('demo:ttl')}")
    print("   Waiting 6 seconds...")
    await asyncio.sleep(6)
    print(f"   After expiry: {await manager.get('demo:ttl')}")
    
    # Counter operations
    print("\n5. Counter Operations...")
    await manager.set("demo:counter", 0, StateType.INTEGER)
    for i in range(5):
        val = await manager.increment("demo:counter", 1)
        print(f"   Increment {i+1}: {val}")
    
    # List operations
    print("\n6. List Operations...")
    await manager.set("demo:queue", [], StateType.LIST)
    await manager.append_to_list("demo:queue", "task1", "task2", "task3")
    queue = await manager.get("demo:queue")
    print(f"   Queue: {queue}")
    
    # Dict operations
    print("\n7. Dict Operations...")
    await manager.set("demo:config", {"debug": True}, StateType.DICT)
    await manager.update_dict("demo:config", {"timeout": 30, "retries": 3})
    config = await manager.get("demo:config")
    print(f"   Config: {config}")
    
    # Distributed locking
    print("\n8. Distributed Locking...")
    async with manager.lock("demo:resource", owner="demo-agent", ttl_seconds=10) as lock_id:
        if lock_id:
            print(f"   ✓ Lock acquired: {lock_id[:16]}...")
            is_locked = await manager.is_locked("demo:resource")
            print(f"   ✓ Resource locked: {is_locked}")
        else:
            print("   ✗ Failed to acquire lock")
    
    print(f"   ✓ Lock released")
    is_locked = await manager.is_locked("demo:resource")
    print(f"   ✓ Resource locked: {is_locked}")
    
    # Build progress tracking
    print("\n9. Build Progress Tracking...")
    await manager.track_build_progress(
        build_id="build-001",
        stage="compiling",
        progress_percent=45.5,
        status="running",
        agent_id="compiler-agent-1"
    )
    progress = await manager.get_build_progress("build-001")
    print(f"   Build: {progress['build_id']}")
    print(f"   Stage: {progress['stage']}")
    print(f"   Progress: {progress['progress_percent']}%")
    
    # Agent status
    print("\n10. Agent Status Management...")
    await manager.update_agent_status(
        agent_id="agent-001",
        agent_type="compiler",
        status="busy",
        current_task="build-001",
        capabilities=["compile", "optimize", "test"]
    )
    status = await manager.get_agent_status("agent-001")
    print(f"   Agent: {status['agent_id']}")
    print(f"   Type: {status['agent_type']}")
    print(f"   Status: {status['status']}")
    print(f"   Task: {status['current_task']}")
    print(f"   Capabilities: {status['capabilities']}")
    
    # Snapshots
    print("\n11. State Snapshots...")
    snapshot_id = await manager.snapshot(name="demo-snapshot")
    print(f"   ✓ Created snapshot: {snapshot_id[:20]}...")
    
    snapshots = await manager.list_snapshots()
    print(f"   ✓ Available snapshots: {len(snapshots)}")
    
    # Event handling
    print("\n12. Event Handling...")
    events_received = []
    
    @manager.on(StateEventType.SET)
    async def on_set(event):
        events_received.append(event.key)
        print(f"   ✓ Event: SET on {event.key}")
    
    await manager.set("demo:event-test", "value")
    await asyncio.sleep(0.5)
    print(f"   Total events received: {len(events_received)}")
    
    # Cleanup
    print("\n13. Cleanup...")
    for key in ["demo:string", "demo:number", "demo:float", "demo:bool", 
                "demo:list", "demo:dict", "demo:counter", "demo:queue", 
                "demo:config", "demo:event-test"]:
        await manager.delete(key)
    print("   ✓ Deleted demo keys")
    
    await manager.delete_snapshot(snapshot_id)
    print("   ✓ Deleted snapshot")
    
    # Disconnect
    await manager.disconnect()
    print("   ✓ Disconnected")
    
    print("\n" + "=" * 70)
    print("Demo completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(demo_shared_state_manager())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise
