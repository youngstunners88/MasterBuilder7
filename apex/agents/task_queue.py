#!/usr/bin/env python3
"""
APEX Distributed Task Queue
Production-ready distributed task queue for agent task management with:
- Priority-based task scheduling (CRITICAL, HIGH, NORMAL, LOW, BACKGROUND)
- Capability-based task assignment to specific agents
- Exponential backoff retry mechanism
- Dead letter queue for failed tasks
- Task progress tracking
- Worker pool management
- Task timeout handling
- Redis-backed with SQLite fallback

Optimized for 64+ parallel agents with high-throughput task processing.

Author: APEX Infrastructure Team
Version: 1.0.0
"""

import asyncio
import hashlib
import json
import logging
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union, AsyncGenerator
from contextlib import asynccontextmanager
import heapq

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger('TaskQueue')

# Redis imports with graceful fallback
try:
    import redis.asyncio as aioredis
    from redis.asyncio import Redis
    from redis.exceptions import (
        RedisError, ConnectionError as RedisConnectionError,
        TimeoutError as RedisTimeoutError
    )
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis-py not available. Using SQLite fallback.")
    # Define placeholder classes for type hints
    class Redis: pass
    class RedisConnectionError(Exception): pass


# ============================================================================
# Enums and Constants
# ============================================================================

class TaskPriority(IntEnum):
    """Task priority levels with numeric values for queue ordering."""
    CRITICAL = 10      # System-critical tasks, immediate execution
    HIGH = 7           # Important tasks, execute ASAP
    NORMAL = 5         # Standard tasks
    LOW = 3            # Background tasks, execute when idle
    BACKGROUND = 1     # Maintenance tasks, lowest priority


class TaskStatus(Enum):
    """Task lifecycle states."""
    PENDING = "pending"              # Waiting in queue
    SCHEDULED = "scheduled"          # Scheduled for future execution
    ASSIGNED = "assigned"            # Assigned to agent, not yet started
    RUNNING = "running"              # Currently executing
    PAUSED = "paused"                # Temporarily paused
    COMPLETED = "completed"          # Successfully finished
    FAILED = "failed"                # Execution failed
    RETRYING = "retrying"            # Scheduled for retry
    CANCELLED = "cancelled"          # Manually cancelled
    TIMED_OUT = "timed_out"          # Execution exceeded timeout
    DEAD_LETTER = "dead_letter"      # Moved to DLQ after max retries


class WorkerStatus(Enum):
    """Worker agent status."""
    IDLE = "idle"                    # Ready to accept tasks
    BUSY = "busy"                    # Currently processing task
    OFFLINE = "offline"              # Not available
    PAUSED = "paused"                # Temporarily not accepting tasks
    ERROR = "error"                  # Error state


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class TaskProgress:
    """Task progress tracking information."""
    percent: float = 0.0             # 0-100 completion percentage
    current_step: str = ""           # Current processing step
    steps_total: int = 0             # Total number of steps
    steps_completed: int = 0         # Steps completed so far
    metadata: Dict[str, Any] = field(default_factory=dict)
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskProgress':
        return cls(**data)


@dataclass
class Task:
    """
    Task representation for the distributed queue.
    
    Attributes:
        id: Unique task identifier (UUID)
        type: Task type/category for routing
        payload: Task data/payload
        priority: Task priority level
        required_capabilities: List of required agent capabilities
        assigned_to: Agent ID assigned to this task
        status: Current task status
        retry_count: Number of retry attempts
        max_retries: Maximum allowed retries
        created_at: Task creation timestamp
        scheduled_at: When task should execute (for delayed tasks)
        started_at: When execution began
        completed_at: When execution finished
        timeout_seconds: Maximum execution time
        progress: Task progress tracking
        result: Task execution result
        error: Error information if failed
        parent_task_id: Parent task for sub-tasks
        correlation_id: Correlation ID for related tasks
        tags: Optional tags for categorization
        metadata: Additional task metadata
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "default"
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    required_capabilities: List[str] = field(default_factory=list)
    assigned_to: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    scheduled_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    timeout_seconds: int = 300  # 5 minutes default
    progress: TaskProgress = field(default_factory=TaskProgress)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    parent_task_id: Optional[str] = None
    correlation_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if isinstance(self.priority, int):
            self.priority = TaskPriority(self.priority)
        if isinstance(self.status, str):
            self.status = TaskStatus(self.status)
        if isinstance(self.progress, dict):
            self.progress = TaskProgress.from_dict(self.progress)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for serialization."""
        data = asdict(self)
        data['priority'] = self.priority.value
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create task from dictionary."""
        return cls(**data)
    
    @property
    def is_active(self) -> bool:
        """Check if task is in an active state."""
        return self.status in [
            TaskStatus.PENDING, TaskStatus.SCHEDULED,
            TaskStatus.ASSIGNED, TaskStatus.RUNNING, TaskStatus.RETRYING
        ]
    
    @property
    def is_terminal(self) -> bool:
        """Check if task is in a terminal state."""
        return self.status in [
            TaskStatus.COMPLETED, TaskStatus.CANCELLED,
            TaskStatus.DEAD_LETTER, TaskStatus.TIMED_OUT
        ]
    
    @property
    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return (
            self.status in [TaskStatus.FAILED, TaskStatus.TIMED_OUT] and
            self.retry_count < self.max_retries
        )
    
    @property
    def wait_time_seconds(self) -> float:
        """Calculate how long task has been waiting."""
        created = datetime.fromisoformat(self.created_at)
        return (datetime.utcnow() - created).total_seconds()
    
    @property
    def execution_time_seconds(self) -> Optional[float]:
        """Calculate task execution time if running or completed."""
        if self.started_at:
            end = datetime.fromisoformat(self.completed_at) if self.completed_at else datetime.utcnow()
            start = datetime.fromisoformat(self.started_at)
            return (end - start).total_seconds()
        return None


@dataclass
class Worker:
    """
    Worker agent representation.
    
    Attributes:
        id: Unique worker identifier
        name: Human-readable worker name
        capabilities: List of agent capabilities/skills
        status: Current worker status
        current_task_id: ID of task currently being processed
        last_heartbeat: Last heartbeat timestamp
        max_concurrent_tasks: Maximum tasks this worker can handle
        current_load: Current number of assigned tasks
        metadata: Additional worker metadata
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "unnamed"
    capabilities: List[str] = field(default_factory=list)
    status: WorkerStatus = WorkerStatus.IDLE
    current_task_id: Optional[str] = None
    last_heartbeat: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    max_concurrent_tasks: int = 1
    current_load: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if isinstance(self.status, str):
            self.status = WorkerStatus(self.status)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert worker to dictionary."""
        data = asdict(self)
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Worker':
        """Create worker from dictionary."""
        return cls(**data)
    
    def can_handle_task(self, task: Task) -> bool:
        """Check if worker can handle the given task."""
        if self.status not in [WorkerStatus.IDLE, WorkerStatus.BUSY]:
            return False
        if self.current_load >= self.max_concurrent_tasks:
            return False
        if not task.required_capabilities:
            return True
        return all(cap in self.capabilities for cap in task.required_capabilities)
    
    def update_heartbeat(self):
        """Update worker heartbeat timestamp."""
        self.last_heartbeat = datetime.utcnow().isoformat()


@dataclass
class TaskQueueStats:
    """Task queue statistics."""
    total_pending: int = 0
    total_running: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_dead_letter: int = 0
    priority_breakdown: Dict[str, int] = field(default_factory=dict)
    worker_count: int = 0
    active_workers: int = 0
    avg_wait_time_seconds: float = 0.0
    avg_execution_time_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QueueConfig:
    """Task queue configuration."""
    # Redis settings
    redis_url: Optional[str] = None
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0
    
    # SQLite fallback
    sqlite_path: str = "/tmp/apex_task_queue.db"
    
    # Queue settings
    max_workers: int = 64
    task_timeout_seconds: int = 300
    max_retries: int = 3
    retry_base_delay_seconds: float = 1.0
    retry_max_delay_seconds: float = 300.0
    retry_exponential_base: float = 2.0
    dead_letter_max_age_days: int = 30
    
    # Worker settings
    worker_heartbeat_interval_seconds: int = 30
    worker_timeout_seconds: int = 120
    task_poll_interval_seconds: float = 0.1
    
    # Batch settings
    batch_size: int = 100
    max_concurrent_tasks: int = 1000
    
    def __post_init__(self):
        # Override from environment
        import os
        self.redis_url = os.getenv('REDIS_URL', self.redis_url)
        self.redis_host = os.getenv('REDIS_HOST', self.redis_host)
        self.redis_port = int(os.getenv('REDIS_PORT', self.redis_port))
        self.redis_password = os.getenv('REDIS_PASSWORD', self.redis_password)


# ============================================================================
# SQLite Fallback Implementation
# ============================================================================

class SQLiteTaskStore:
    """SQLite-backed task storage for fallback when Redis is unavailable."""
    
    def __init__(self, db_path: str = "/tmp/apex_task_queue.db"):
        self.db_path = db_path
        self._local = threading.local()
        self._lock = threading.RLock()
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    def _init_db(self):
        """Initialize SQLite database schema."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    assigned_to TEXT,
                    created_at TIMESTAMP NOT NULL,
                    scheduled_at TIMESTAMP,
                    retry_count INTEGER DEFAULT 0,
                    expires_at TIMESTAMP
                )
            """)
            
            # Workers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workers (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    status TEXT NOT NULL,
                    last_heartbeat TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP
                )
            """)
            
            # Dead letter queue table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dead_letter_queue (
                    id TEXT PRIMARY KEY,
                    task_data TEXT NOT NULL,
                    failed_at TIMESTAMP NOT NULL,
                    failure_reason TEXT,
                    retry_count INTEGER DEFAULT 0
                )
            """)
            
            # Task history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON tasks(assigned_to)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_workers_status ON workers(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_workers_heartbeat ON workers(last_heartbeat)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_task ON task_history(task_id)")
            
            conn.commit()
            logger.info(f"SQLite task store initialized: {self.db_path}")
    
    def _cleanup_expired(self):
        """Remove expired entries."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            now = datetime.utcnow().isoformat()
            
            cursor.execute("DELETE FROM tasks WHERE expires_at < ?", (now,))
            cursor.execute("DELETE FROM workers WHERE expires_at < ?", (now,))
            conn.commit()
    
    # Task operations
    def enqueue_task(self, task: Task, ttl_seconds: int = 86400) -> bool:
        """Add task to queue."""
        try:
            self._cleanup_expired()
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                expires_at = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()
                
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO tasks 
                    (id, data, priority, status, assigned_to, created_at, scheduled_at, retry_count, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task.id,
                        json.dumps(task.to_dict()),
                        task.priority.value,
                        task.status.value,
                        task.assigned_to,
                        task.created_at,
                        task.scheduled_at,
                        task.retry_count,
                        expires_at
                    )
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"SQLite enqueue_task error: {e}")
            return False
    
    def dequeue_task(self, worker_capabilities: List[str] = None, 
                     worker_id: str = None) -> Optional[Task]:
        """Get next available task matching worker capabilities."""
        try:
            self._cleanup_expired()
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                now = datetime.utcnow().isoformat()
                
                # Find pending tasks that are scheduled for now or earlier
                cursor.execute(
                    """
                    SELECT data FROM tasks 
                    WHERE status = ? AND (scheduled_at IS NULL OR scheduled_at <= ?)
                    ORDER BY priority DESC, created_at ASC
                    LIMIT ?
                    """,
                    (TaskStatus.PENDING.value, now, 100)
                )
                
                rows = cursor.fetchall()
                
                for row in rows:
                    task_data = json.loads(row['data'])
                    task = Task.from_dict(task_data)
                    
                    # Check capabilities match
                    if task.required_capabilities and worker_capabilities:
                        if not all(cap in worker_capabilities for cap in task.required_capabilities):
                            continue
                    
                    # Assign to worker
                    task.status = TaskStatus.ASSIGNED
                    task.assigned_to = worker_id
                    
                    cursor.execute(
                        "UPDATE tasks SET status = ?, assigned_to = ?, data = ? WHERE id = ?",
                        (task.status.value, worker_id, json.dumps(task.to_dict()), task.id)
                    )
                    conn.commit()
                    return task
                
                return None
        except Exception as e:
            logger.error(f"SQLite dequeue_task error: {e}")
            return None
    
    def update_task(self, task: Task) -> bool:
        """Update task in storage."""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    UPDATE tasks SET 
                        data = ?, priority = ?, status = ?, assigned_to = ?, 
                        retry_count = ?
                    WHERE id = ?
                    """,
                    (
                        json.dumps(task.to_dict()),
                        task.priority.value,
                        task.status.value,
                        task.assigned_to,
                        task.retry_count,
                        task.id
                    )
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"SQLite update_task error: {e}")
            return False
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute("SELECT data FROM tasks WHERE id = ?", (task_id,))
                row = cursor.fetchone()
                
                if row:
                    return Task.from_dict(json.loads(row['data']))
                return None
        except Exception as e:
            logger.error(f"SQLite get_task error: {e}")
            return None
    
    def get_tasks_by_status(self, status: TaskStatus, limit: int = 100) -> List[Task]:
        """Get tasks by status."""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT data FROM tasks WHERE status = ? LIMIT ?",
                    (status.value, limit)
                )
                
                return [Task.from_dict(json.loads(row['data'])) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"SQLite get_tasks_by_status error: {e}")
            return []
    
    def move_to_dead_letter(self, task: Task, reason: str) -> bool:
        """Move failed task to dead letter queue."""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # Add to DLQ
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO dead_letter_queue 
                    (id, task_data, failed_at, failure_reason, retry_count)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        task.id,
                        json.dumps(task.to_dict()),
                        datetime.utcnow().isoformat(),
                        reason,
                        task.retry_count
                    )
                )
                
                # Remove from tasks
                cursor.execute("DELETE FROM tasks WHERE id = ?", (task.id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"SQLite move_to_dead_letter error: {e}")
            return False
    
    def get_dead_letter_tasks(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get tasks from dead letter queue."""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT * FROM dead_letter_queue ORDER BY failed_at DESC LIMIT ?",
                    (limit,)
                )
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"SQLite get_dead_letter_tasks error: {e}")
            return []
    
    # Worker operations
    def register_worker(self, worker: Worker, ttl_seconds: int = 120) -> bool:
        """Register a worker."""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                expires_at = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()
                
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO workers 
                    (id, data, status, last_heartbeat, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        worker.id,
                        json.dumps(worker.to_dict()),
                        worker.status.value,
                        worker.last_heartbeat,
                        expires_at
                    )
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"SQLite register_worker error: {e}")
            return False
    
    def update_worker(self, worker: Worker) -> bool:
        """Update worker information."""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute(
                    "UPDATE workers SET data = ?, status = ?, last_heartbeat = ? WHERE id = ?",
                    (json.dumps(worker.to_dict()), worker.status.value, worker.last_heartbeat, worker.id)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"SQLite update_worker error: {e}")
            return False
    
    def get_worker(self, worker_id: str) -> Optional[Worker]:
        """Get worker by ID."""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute("SELECT data FROM workers WHERE id = ?", (worker_id,))
                row = cursor.fetchone()
                
                if row:
                    return Worker.from_dict(json.loads(row['data']))
                return None
        except Exception as e:
            logger.error(f"SQLite get_worker error: {e}")
            return None
    
    def get_available_workers(self) -> List[Worker]:
        """Get all available workers."""
        try:
            self._cleanup_expired()
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    SELECT data FROM workers 
                    WHERE status IN (?, ?) 
                    ORDER BY last_heartbeat DESC
                    """,
                    (WorkerStatus.IDLE.value, WorkerStatus.BUSY.value)
                )
                
                return [Worker.from_dict(json.loads(row['data'])) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"SQLite get_available_workers error: {e}")
            return []
    
    def get_stats(self) -> TaskQueueStats:
        """Get queue statistics."""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                stats = TaskQueueStats()
                
                # Count by status
                cursor.execute(
                    "SELECT status, COUNT(*) FROM tasks GROUP BY status"
                )
                for row in cursor.fetchall():
                    status, count = row
                    if status == TaskStatus.PENDING.value:
                        stats.total_pending = count
                    elif status == TaskStatus.RUNNING.value:
                        stats.total_running = count
                    elif status == TaskStatus.COMPLETED.value:
                        stats.total_completed = count
                    elif status == TaskStatus.FAILED.value:
                        stats.total_failed = count
                
                # Count dead letter
                cursor.execute("SELECT COUNT(*) FROM dead_letter_queue")
                stats.total_dead_letter = cursor.fetchone()[0]
                
                # Priority breakdown
                cursor.execute(
                    "SELECT priority, COUNT(*) FROM tasks WHERE status = ? GROUP BY priority",
                    (TaskStatus.PENDING.value,)
                )
                stats.priority_breakdown = {str(row[0]): row[1] for row in cursor.fetchall()}
                
                # Worker counts
                cursor.execute(
                    "SELECT status, COUNT(*) FROM workers GROUP BY status"
                )
                worker_counts = {row[0]: row[1] for row in cursor.fetchall()}
                stats.worker_count = sum(worker_counts.values())
                stats.active_workers = worker_counts.get(WorkerStatus.IDLE.value, 0) + \
                                       worker_counts.get(WorkerStatus.BUSY.value, 0)
                
                return stats
        except Exception as e:
            logger.error(f"SQLite get_stats error: {e}")
            return TaskQueueStats()


# ============================================================================
# Main Task Queue Implementation
# ============================================================================

class TaskQueue:
    """
    Distributed Task Queue for APEX Agent Layer.
    
    Features:
    - Priority-based scheduling (CRITICAL > HIGH > NORMAL > LOW > BACKGROUND)
    - Capability-based task assignment
    - Exponential backoff retry
    - Dead letter queue
    - Progress tracking
    - Worker pool management
    - Task timeouts
    - Redis-backed with SQLite fallback
    
    Optimized for 64+ parallel agents.
    """
    
    # Redis key prefixes
    PREFIX_TASK = "apex:task:"
    PREFIX_QUEUE = "apex:queue:"
    PREFIX_WORKER = "apex:worker:"
    PREFIX_DLQ = "apex:dlq:"
    PREFIX_PROGRESS = "apex:progress:"
    PREFIX_LOCK = "apex:tasklock:"
    
    def __init__(self, config: Optional[QueueConfig] = None):
        """
        Initialize Task Queue.
        
        Args:
            config: Queue configuration. If None, uses defaults.
        """
        self.config = config or QueueConfig()
        self._redis: Optional[Redis] = None
        self._sqlite = SQLiteTaskStore(self.config.sqlite_path)
        self._connected = False
        self._lock = asyncio.Lock()
        
        # In-memory caches for performance
        self._worker_cache: Dict[str, Worker] = {}
        self._task_cache: Dict[str, Task] = {}
        
        # Worker pool management
        self._worker_semaphores: Dict[str, asyncio.Semaphore] = {}
        self._shutdown_event = asyncio.Event()
        
        # Background tasks
        self._maintenance_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        
        # Callbacks
        self._task_callbacks: Dict[str, List[Callable]] = {
            'created': [],
            'assigned': [],
            'started': [],
            'completed': [],
            'failed': [],
            'cancelled': [],
            'dead_letter': []
        }
        
        logger.info("TaskQueue initialized")
    
    # ==================== Connection Management ====================
    
    async def connect(self) -> bool:
        """Connect to Redis or fallback to SQLite."""
        async with self._lock:
            if self._connected and self._redis:
                try:
                    await self._redis.ping()
                    return True
                except Exception:
                    self._connected = False
            
            if not REDIS_AVAILABLE:
                logger.warning("Redis not available, using SQLite fallback")
                return False
            
            # Try to connect to Redis
            for attempt in range(3):
                try:
                    if self.config.redis_url:
                        self._redis = aioredis.from_url(
                            self.config.redis_url,
                            decode_responses=True,
                            max_connections=20
                        )
                    else:
                        self._redis = aioredis.Redis(
                            host=self.config.redis_host,
                            port=self.config.redis_port,
                            password=self.config.redis_password,
                            db=self.config.redis_db,
                            decode_responses=True,
                            max_connections=20
                        )
                    
                    await self._redis.ping()
                    self._connected = True
                    logger.info("TaskQueue connected to Redis")
                    
                    # Initialize Redis data structures
                    await self._init_redis()
                    
                    return True
                    
                except Exception as e:
                    delay = min(2 ** attempt, 10)
                    logger.warning(f"Redis connection attempt {attempt + 1}/3 failed: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
            
            logger.warning("Failed to connect to Redis, using SQLite fallback")
            return False
    
    async def _init_redis(self):
        """Initialize Redis data structures."""
        # Create priority queues
        for priority in TaskPriority:
            await self._redis.delete(f"{self.PREFIX_QUEUE}{priority.name}")
        
        # Clear old locks
        pattern = f"{self.PREFIX_LOCK}*"
        async for key in self._redis.scan_iter(match=pattern):
            await self._redis.delete(key)
    
    async def disconnect(self):
        """Disconnect from Redis and cleanup."""
        async with self._lock:
            self._shutdown_event.set()
            
            # Cancel background tasks
            if self._maintenance_task:
                self._maintenance_task.cancel()
                try:
                    await self._maintenance_task
                except asyncio.CancelledError:
                    pass
            
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    pass
            
            if self._redis:
                await self._redis.close()
                self._redis = None
            
            self._connected = False
            logger.info("TaskQueue disconnected")
    
    async def start(self):
        """Start background maintenance tasks."""
        if not self._maintenance_task or self._maintenance_task.done():
            self._maintenance_task = asyncio.create_task(self._maintenance_loop())
        
        if not self._heartbeat_task or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        logger.info("TaskQueue background tasks started")
    
    # ==================== Core Task Operations ====================
    
    async def enqueue(
        self,
        task_type: str,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        required_capabilities: List[str] = None,
        scheduled_at: Optional[datetime] = None,
        max_retries: int = None,
        timeout_seconds: int = None,
        parent_task_id: str = None,
        correlation_id: str = None,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Task:
        """
        Enqueue a new task.
        
        Args:
            task_type: Task type/category
            payload: Task data
            priority: Task priority level
            required_capabilities: Required agent capabilities
            scheduled_at: When to execute (None = immediate)
            max_retries: Maximum retry attempts
            timeout_seconds: Task timeout
            parent_task_id: Parent task ID
            correlation_id: Correlation ID for grouping
            tags: Optional tags
            metadata: Additional metadata
            
        Returns:
            Created Task object
        """
        task = Task(
            type=task_type,
            payload=payload,
            priority=priority,
            required_capabilities=required_capabilities or [],
            max_retries=max_retries or self.config.max_retries,
            timeout_seconds=timeout_seconds or self.config.task_timeout_seconds,
            scheduled_at=scheduled_at.isoformat() if scheduled_at else None,
            parent_task_id=parent_task_id,
            correlation_id=correlation_id,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        # Store task
        if self._connected:
            await self._enqueue_redis(task)
        else:
            self._sqlite.enqueue_task(task)
        
        # Cache task
        self._task_cache[task.id] = task
        
        # Trigger callbacks
        await self._trigger_callbacks('created', task)
        
        logger.info(f"Task enqueued: {task.id} (type={task_type}, priority={priority.name})")
        return task
    
    async def _enqueue_redis(self, task: Task):
        """Enqueue task in Redis."""
        pipe = self._redis.pipeline()
        
        # Store task data
        task_key = f"{self.PREFIX_TASK}{task.id}"
        pipe.setex(task_key, 86400, json.dumps(task.to_dict()))
        
        # Add to priority queue
        queue_key = f"{self.PREFIX_QUEUE}{task.priority.name}"
        # Use score: priority * 1e12 + timestamp for ordering
        score = task.priority.value * 1e12 + time.time()
        pipe.zadd(queue_key, {task.id: score})
        
        # Add to pending set
        pipe.sadd(f"{self.PREFIX_QUEUE}PENDING", task.id)
        
        await pipe.execute()
    
    async def dequeue(self, worker_id: str, worker_capabilities: List[str] = None) -> Optional[Task]:
        """
        Dequeue next available task for a worker.
        
        Args:
            worker_id: Worker agent ID
            worker_capabilities: Worker's capabilities
            
        Returns:
            Assigned Task or None if no tasks available
        """
        if self._connected:
            task = await self._dequeue_redis(worker_id, worker_capabilities)
        else:
            task = self._sqlite.dequeue_task(worker_capabilities, worker_id)
        
        if task:
            # Update cache
            self._task_cache[task.id] = task
            
            # Update worker
            await self._update_worker_task(worker_id, task.id)
            
            # Trigger callbacks
            await self._trigger_callbacks('assigned', task)
            
            logger.info(f"Task {task.id} assigned to worker {worker_id}")
        
        return task
    
    async def _dequeue_redis(self, worker_id: str, worker_capabilities: List[str] = None) -> Optional[Task]:
        """Dequeue task from Redis."""
        # Try priority queues in order
        for priority in sorted(TaskPriority, key=lambda p: p.value, reverse=True):
            queue_key = f"{self.PREFIX_QUEUE}{priority.name}"
            
            # Get tasks from this priority level
            task_ids = await self._redis.zrange(queue_key, 0, 99)
            
            for task_id in task_ids:
                # Try to acquire lock
                lock_key = f"{self.PREFIX_LOCK}{task_id}"
                lock_acquired = await self._redis.set(
                    lock_key, worker_id, nx=True, ex=30
                )
                
                if not lock_acquired:
                    continue
                
                # Get task data
                task_key = f"{self.PREFIX_TASK}{task_id}"
                task_data = await self._redis.get(task_key)
                
                if not task_data:
                    await self._redis.delete(lock_key)
                    continue
                
                task = Task.from_dict(json.loads(task_data))
                
                # Check scheduled time
                if task.scheduled_at:
                    scheduled = datetime.fromisoformat(task.scheduled_at)
                    if scheduled > datetime.utcnow():
                        await self._redis.delete(lock_key)
                        continue
                
                # Check capabilities
                if task.required_capabilities and worker_capabilities:
                    if not all(cap in worker_capabilities for cap in task.required_capabilities):
                        await self._redis.delete(lock_key)
                        continue
                
                # Assign task
                task.status = TaskStatus.ASSIGNED
                task.assigned_to = worker_id
                
                # Update in Redis
                pipe = self._redis.pipeline()
                pipe.setex(task_key, 86400, json.dumps(task.to_dict()))
                pipe.zrem(queue_key, task_id)
                pipe.sadd(f"{self.PREFIX_QUEUE}ASSIGNED", task_id)
                pipe.delete(lock_key)
                await pipe.execute()
                
                return task
        
        return None
    
    async def complete(self, task_id: str, result: Dict[str, Any] = None) -> bool:
        """
        Mark task as completed.
        
        Args:
            task_id: Task ID
            result: Task execution result
            
        Returns:
            True if successful
        """
        task = await self._get_task(task_id)
        if not task:
            return False
        
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow().isoformat()
        task.result = result or {}
        task.progress.percent = 100.0
        task.progress.current_step = "completed"
        
        # Update storage
        if self._connected:
            await self._update_task_redis(task)
            await self._redis.srem(f"{self.PREFIX_QUEUE}ASSIGNED", task_id)
            await self._redis.sadd(f"{self.PREFIX_QUEUE}COMPLETED", task_id)
        else:
            self._sqlite.update_task(task)
        
        # Update worker
        if task.assigned_to:
            await self._update_worker_task(task.assigned_to, None)
        
        # Trigger callbacks
        await self._trigger_callbacks('completed', task)
        
        logger.info(f"Task {task_id} completed")
        return True
    
    async def fail(self, task_id: str, error: str) -> bool:
        """
        Mark task as failed.
        
        Args:
            task_id: Task ID
            error: Error message
            
        Returns:
            True if task will be retried, False if moved to DLQ
        """
        task = await self._get_task(task_id)
        if not task:
            return False
        
        task.error = error
        task.retry_count += 1
        
        if task.can_retry:
            # Schedule retry with exponential backoff
            await self.retry(task_id, error)
            return True
        else:
            # Move to dead letter queue
            await self._move_to_dead_letter(task, error)
            return False
    
    async def retry(self, task_id: str, error: str = None) -> bool:
        """
        Schedule task for retry with exponential backoff.
        
        Args:
            task_id: Task ID
            error: Error message (for logging)
            
        Returns:
            True if scheduled for retry
        """
        task = await self._get_task(task_id)
        if not task or not task.can_retry:
            return False
        
        # Calculate backoff delay
        delay = min(
            self.config.retry_base_delay_seconds * 
            (self.config.retry_exponential_base ** task.retry_count),
            self.config.retry_max_delay_seconds
        )
        
        scheduled_at = datetime.utcnow() + timedelta(seconds=delay)
        
        task.status = TaskStatus.RETRYING
        task.error = error
        task.scheduled_at = scheduled_at.isoformat()
        task.assigned_to = None
        
        # Update storage
        if self._connected:
            await self._enqueue_redis(task)
        else:
            self._sqlite.enqueue_task(task)
        
        # Update worker
        if task.assigned_to:
            await self._update_worker_task(task.assigned_to, None)
        
        logger.info(f"Task {task_id} scheduled for retry {task.retry_count}/{task.max_retries} in {delay:.1f}s")
        return True
    
    async def _move_to_dead_letter(self, task: Task, reason: str):
        """Move task to dead letter queue."""
        task.status = TaskStatus.DEAD_LETTER
        task.completed_at = datetime.utcnow().isoformat()
        
        if self._connected:
            # Store in DLQ
            dlq_key = f"{self.PREFIX_DLQ}{task.id}"
            await self._redis.setex(
                dlq_key,
                self.config.dead_letter_max_age_days * 86400,
                json.dumps({
                    'task': task.to_dict(),
                    'failed_at': datetime.utcnow().isoformat(),
                    'reason': reason
                })
            )
            
            # Cleanup from active queues
            pipe = self._redis.pipeline()
            pipe.delete(f"{self.PREFIX_TASK}{task.id}")
            for priority in TaskPriority:
                pipe.zrem(f"{self.PREFIX_QUEUE}{priority.name}", task.id)
            pipe.srem(f"{self.PREFIX_QUEUE}ASSIGNED", task.id)
            pipe.srem(f"{self.PREFIX_QUEUE}PENDING", task.id)
            await pipe.execute()
        else:
            self._sqlite.move_to_dead_letter(task, reason)
        
        # Update worker
        if task.assigned_to:
            await self._update_worker_task(task.assigned_to, None)
        
        # Trigger callbacks
        await self._trigger_callbacks('dead_letter', task)
        
        logger.warning(f"Task {task.id} moved to dead letter queue: {reason}")
    
    async def cancel(self, task_id: str, reason: str = None) -> bool:
        """
        Cancel a pending or scheduled task.
        
        Args:
            task_id: Task ID
            reason: Cancellation reason
            
        Returns:
            True if cancelled
        """
        task = await self._get_task(task_id)
        if not task or task.status not in [TaskStatus.PENDING, TaskStatus.SCHEDULED, TaskStatus.RETRYING]:
            return False
        
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.utcnow().isoformat()
        task.metadata['cancel_reason'] = reason
        
        if self._connected:
            pipe = self._redis.pipeline()
            pipe.delete(f"{self.PREFIX_TASK}{task_id}")
            for priority in TaskPriority:
                pipe.zrem(f"{self.PREFIX_QUEUE}{priority.name}", task_id)
            pipe.srem(f"{self.PREFIX_QUEUE}PENDING", task_id)
            pipe.srem(f"{self.PREFIX_QUEUE}ASSIGNED", task_id)
            await pipe.execute()
        else:
            self._sqlite.update_task(task)
        
        await self._trigger_callbacks('cancelled', task)
        
        logger.info(f"Task {task_id} cancelled: {reason}")
        return True
    
    # ==================== Progress Tracking ====================
    
    async def update_progress(
        self,
        task_id: str,
        percent: float = None,
        current_step: str = None,
        steps_completed: int = None,
        steps_total: int = None,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        Update task progress.
        
        Args:
            task_id: Task ID
            percent: Completion percentage (0-100)
            current_step: Current processing step
            steps_completed: Steps completed
            steps_total: Total steps
            metadata: Additional progress metadata
            
        Returns:
            True if updated
        """
        task = await self._get_task(task_id)
        if not task:
            return False
        
        if percent is not None:
            task.progress.percent = max(0.0, min(100.0, percent))
        if current_step:
            task.progress.current_step = current_step
        if steps_completed is not None:
            task.progress.steps_completed = steps_completed
        if steps_total is not None:
            task.progress.steps_total = steps_total
        if metadata:
            task.progress.metadata.update(metadata)
        
        task.progress.updated_at = datetime.utcnow().isoformat()
        
        # Update storage
        if self._connected:
            progress_key = f"{self.PREFIX_PROGRESS}{task_id}"
            await self._redis.setex(progress_key, 86400, json.dumps(task.progress.to_dict()))
            await self._redis.setex(
                f"{self.PREFIX_TASK}{task_id}",
                86400,
                json.dumps(task.to_dict())
            )
        else:
            self._sqlite.update_task(task)
        
        return True
    
    async def get_progress(self, task_id: str) -> Optional[TaskProgress]:
        """Get task progress."""
        if self._connected:
            progress_key = f"{self.PREFIX_PROGRESS}{task_id}"
            data = await self._redis.get(progress_key)
            if data:
                return TaskProgress.from_dict(json.loads(data))
        
        task = await self._get_task(task_id)
        return task.progress if task else None
    
    # ==================== Worker Management ====================
    
    async def register_worker(
        self,
        worker_id: str = None,
        name: str = None,
        capabilities: List[str] = None,
        max_concurrent_tasks: int = 1
    ) -> Worker:
        """
        Register a worker agent.
        
        Args:
            worker_id: Worker ID (generated if None)
            name: Worker name
            capabilities: Worker capabilities
            max_concurrent_tasks: Max concurrent tasks
            
        Returns:
            Registered Worker
        """
        worker = Worker(
            id=worker_id or str(uuid.uuid4()),
            name=name or f"worker-{uuid.uuid4().hex[:8]}",
            capabilities=capabilities or [],
            max_concurrent_tasks=max_concurrent_tasks,
            status=WorkerStatus.IDLE
        )
        
        # Create semaphore for concurrency control
        self._worker_semaphores[worker.id] = asyncio.Semaphore(max_concurrent_tasks)
        
        if self._connected:
            worker_key = f"{self.PREFIX_WORKER}{worker.id}"
            await self._redis.setex(
                worker_key,
                self.config.worker_timeout_seconds,
                json.dumps(worker.to_dict())
            )
            await self._redis.sadd(f"{self.PREFIX_WORKER}ACTIVE", worker.id)
        else:
            self._sqlite.register_worker(worker, self.config.worker_timeout_seconds)
        
        self._worker_cache[worker.id] = worker
        
        logger.info(f"Worker registered: {worker.id} ({worker.name})")
        return worker
    
    async def unregister_worker(self, worker_id: str) -> bool:
        """Unregister a worker."""
        if self._connected:
            await self._redis.delete(f"{self.PREFIX_WORKER}{worker_id}")
            await self._redis.srem(f"{self.PREFIX_WORKER}ACTIVE", worker_id)
        else:
            worker = self._sqlite.get_worker(worker_id)
            if worker:
                worker.status = WorkerStatus.OFFLINE
                self._sqlite.update_worker(worker)
        
        self._worker_cache.pop(worker_id, None)
        self._worker_semaphores.pop(worker_id, None)
        
        logger.info(f"Worker unregistered: {worker_id}")
        return True
    
    async def heartbeat(self, worker_id: str, status: WorkerStatus = None, metrics: Dict[str, Any] = None):
        """Send worker heartbeat."""
        worker = self._worker_cache.get(worker_id)
        if not worker:
            worker = self._sqlite.get_worker(worker_id)
        
        if worker:
            worker.update_heartbeat()
            if status:
                worker.status = status
            if metrics:
                worker.metadata['metrics'] = metrics
            
            if self._connected:
                worker_key = f"{self.PREFIX_WORKER}{worker_id}"
                await self._redis.setex(
                    worker_key,
                    self.config.worker_timeout_seconds,
                    json.dumps(worker.to_dict())
                )
            else:
                self._sqlite.update_worker(worker)
            
            self._worker_cache[worker_id] = worker
    
    async def _update_worker_task(self, worker_id: str, task_id: Optional[str]):
        """Update worker's current task."""
        worker = self._worker_cache.get(worker_id)
        if not worker:
            return
        
        worker.current_task_id = task_id
        worker.current_load = 1 if task_id else 0
        worker.status = WorkerStatus.BUSY if task_id else WorkerStatus.IDLE
        
        if self._connected:
            worker_key = f"{self.PREFIX_WORKER}{worker_id}"
            await self._redis.setex(
                worker_key,
                self.config.worker_timeout_seconds,
                json.dumps(worker.to_dict())
            )
    
    async def get_workers(self, status: WorkerStatus = None) -> List[Worker]:
        """Get workers, optionally filtered by status."""
        if self._connected:
            worker_ids = await self._redis.smembers(f"{self.PREFIX_WORKER}ACTIVE")
            workers = []
            for wid in worker_ids:
                data = await self._redis.get(f"{self.PREFIX_WORKER}{wid}")
                if data:
                    worker = Worker.from_dict(json.loads(data))
                    if status is None or worker.status == status:
                        workers.append(worker)
            return workers
        else:
            workers = self._sqlite.get_available_workers()
            if status:
                workers = [w for w in workers if w.status == status]
            return workers
    
    async def find_capable_workers(self, required_capabilities: List[str]) -> List[Worker]:
        """Find workers with required capabilities."""
        workers = await self.get_workers(WorkerStatus.IDLE)
        capable = []
        for worker in workers:
            if all(cap in worker.capabilities for cap in required_capabilities):
                capable.append(worker)
        return capable
    
    # ==================== Query Operations ====================
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        return await self._get_task(task_id)
    
    async def _get_task(self, task_id: str) -> Optional[Task]:
        """Internal method to get task."""
        # Check cache first
        if task_id in self._task_cache:
            return self._task_cache[task_id]
        
        if self._connected:
            task_key = f"{self.PREFIX_TASK}{task_id}"
            data = await self._redis.get(task_key)
            if data:
                task = Task.from_dict(json.loads(data))
                self._task_cache[task_id] = task
                return task
        else:
            task = self._sqlite.get_task(task_id)
            if task:
                self._task_cache[task_id] = task
            return task
        
        return None
    
    async def get_tasks(
        self,
        status: TaskStatus = None,
        task_type: str = None,
        limit: int = 100
    ) -> List[Task]:
        """Get tasks with optional filtering."""
        if status and not task_type:
            if self._connected:
                # Get from Redis sets
                task_ids = await self._redis.smembers(f"{self.PREFIX_QUEUE}{status.name}")
                tasks = []
                for tid in list(task_ids)[:limit]:
                    task = await self._get_task(tid)
                    if task:
                        tasks.append(task)
                return tasks
            else:
                return self._sqlite.get_tasks_by_status(status, limit)
        
        # For complex queries, scan all tasks
        # This is inefficient for large datasets - use with caution
        all_tasks = []
        if self._connected:
            pattern = f"{self.PREFIX_TASK}*"
            async for key in self._redis.scan_iter(match=pattern, count=limit):
                data = await self._redis.get(key)
                if data:
                    task = Task.from_dict(json.loads(data))
                    if status and task.status != status:
                        continue
                    if task_type and task.type != task_type:
                        continue
                    all_tasks.append(task)
        else:
            # Get all pending and running from SQLite
            for status in [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.ASSIGNED]:
                all_tasks.extend(self._sqlite.get_tasks_by_status(status))
        
        return all_tasks[:limit]
    
    async def get_stats(self) -> TaskQueueStats:
        """Get queue statistics."""
        if self._connected:
            stats = TaskQueueStats()
            
            # Count by status
            stats.total_pending = await self._redis.scard(f"{self.PREFIX_QUEUE}PENDING")
            stats.total_running = await self._redis.scard(f"{self.PREFIX_QUEUE}ASSIGNED")
            stats.total_completed = await self._redis.scard(f"{self.PREFIX_QUEUE}COMPLETED")
            
            # Priority breakdown
            for priority in TaskPriority:
                count = await self._redis.zcard(f"{self.PREFIX_QUEUE}{priority.name}")
                stats.priority_breakdown[priority.name] = count
            
            # Worker counts
            stats.worker_count = await self._redis.scard(f"{self.PREFIX_WORKER}ACTIVE")
            
            return stats
        else:
            return self._sqlite.get_stats()
    
    async def get_dead_letter_tasks(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get tasks from dead letter queue."""
        if self._connected:
            tasks = []
            pattern = f"{self.PREFIX_DLQ}*"
            async for key in self._redis.scan_iter(match=pattern, count=limit):
                data = await self._redis.get(key)
                if data:
                    tasks.append(json.loads(data))
            return tasks[:limit]
        else:
            return self._sqlite.get_dead_letter_tasks(limit)
    
    # ==================== Background Tasks ====================
    
    async def _maintenance_loop(self):
        """Background maintenance task."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                pass
            
            if self._shutdown_event.is_set():
                break
            
            try:
                # Check for timed out tasks
                await self._check_timeouts()
                
                # Requeue orphaned tasks (assigned but worker dead)
                await self._check_orphaned_tasks()
                
            except Exception as e:
                logger.error(f"Maintenance loop error: {e}")
    
    async def _heartbeat_loop(self):
        """Worker heartbeat monitoring."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self.config.worker_heartbeat_interval_seconds
                )
            except asyncio.TimeoutError:
                pass
            
            if self._shutdown_event.is_set():
                break
            
            try:
                # Check for stale workers
                await self._check_stale_workers()
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
    
    async def _check_timeouts(self):
        """Check for and handle timed out tasks."""
        running_tasks = await self.get_tasks(TaskStatus.RUNNING)
        
        for task in running_tasks:
            exec_time = task.execution_time_seconds
            if exec_time and exec_time > task.timeout_seconds:
                logger.warning(f"Task {task.id} timed out after {exec_time:.1f}s")
                task.status = TaskStatus.TIMED_OUT
                
                if self._connected:
                    await self._redis.setex(
                        f"{self.PREFIX_TASK}{task.id}",
                        86400,
                        json.dumps(task.to_dict())
                    )
                else:
                    self._sqlite.update_task(task)
                
                # Trigger retry or DLQ
                await self.fail(task.id, f"Task timed out after {exec_time:.1f}s")
    
    async def _check_orphaned_tasks(self):
        """Check for tasks assigned to dead workers."""
        assigned_tasks = await self.get_tasks(TaskStatus.ASSIGNED)
        active_workers = {w.id for w in await self.get_workers()}
        
        for task in assigned_tasks:
            if task.assigned_to and task.assigned_to not in active_workers:
                logger.warning(f"Task {task.id} orphaned (worker {task.assigned_to} dead)")
                task.status = TaskStatus.PENDING
                task.assigned_to = None
                
                if self._connected:
                    await self._enqueue_redis(task)
                else:
                    self._sqlite.update_task(task)
    
    async def _check_stale_workers(self):
        """Check for and handle stale workers."""
        if not self._connected:
            return
        
        # Redis auto-expires workers, so we just need to update our cache
        active_ids = await self._redis.smembers(f"{self.PREFIX_WORKER}ACTIVE")
        
        # Remove from cache if no longer in Redis
        stale = set(self._worker_cache.keys()) - set(active_ids)
        for worker_id in stale:
            self._worker_cache.pop(worker_id, None)
            self._worker_semaphores.pop(worker_id, None)
    
    # ==================== Callback System ====================
    
    def on(self, event: str, callback: Callable[[Task], Any]):
        """
        Register a callback for task events.
        
        Args:
            event: Event type ('created', 'assigned', 'started', 'completed', 'failed', 'cancelled', 'dead_letter')
            callback: Callback function(task)
        """
        if event in self._task_callbacks:
            self._task_callbacks[event].append(callback)
    
    def off(self, event: str, callback: Callable[[Task], Any]):
        """Remove a callback."""
        if event in self._task_callbacks:
            self._task_callbacks[event] = [
                cb for cb in self._task_callbacks[event] if cb != callback
            ]
    
    async def _trigger_callbacks(self, event: str, task: Task):
        """Trigger callbacks for an event."""
        for callback in self._task_callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(task))
                else:
                    callback(task)
            except Exception as e:
                logger.error(f"Callback error for {event}: {e}")
    
    # ==================== Batch Operations ====================
    
    async def enqueue_many(self, tasks_data: List[Dict[str, Any]]) -> List[Task]:
        """
        Enqueue multiple tasks efficiently.
        
        Args:
            tasks_data: List of task data dicts with keys:
                type, payload, priority, required_capabilities, etc.
        
        Returns:
            List of created Task objects
        """
        tasks = []
        
        if self._connected:
            # Use Redis pipeline for batch insert
            pipe = self._redis.pipeline()
            
            for data in tasks_data:
                task = Task(
                    type=data.get('type', 'default'),
                    payload=data.get('payload', {}),
                    priority=data.get('priority', TaskPriority.NORMAL),
                    required_capabilities=data.get('required_capabilities', []),
                    max_retries=data.get('max_retries', self.config.max_retries),
                    timeout_seconds=data.get('timeout_seconds', self.config.task_timeout_seconds),
                    scheduled_at=data.get('scheduled_at'),
                    parent_task_id=data.get('parent_task_id'),
                    correlation_id=data.get('correlation_id'),
                    tags=data.get('tags', []),
                    metadata=data.get('metadata', {})
                )
                tasks.append(task)
                
                # Add to pipeline
                task_key = f"{self.PREFIX_TASK}{task.id}"
                pipe.setex(task_key, 86400, json.dumps(task.to_dict()))
                
                queue_key = f"{self.PREFIX_QUEUE}{task.priority.name}"
                score = task.priority.value * 1e12 + time.time()
                pipe.zadd(queue_key, {task.id: score})
                pipe.sadd(f"{self.PREFIX_QUEUE}PENDING", task.id)
            
            await pipe.execute()
        else:
            # SQLite fallback - insert one by one
            for data in tasks_data:
                task = await self.enqueue(**data)
                tasks.append(task)
        
        logger.info(f"Batch enqueued {len(tasks)} tasks")
        return tasks
    
    async def cancel_many(self, task_ids: List[str], reason: str = None) -> int:
        """Cancel multiple tasks."""
        cancelled = 0
        for task_id in task_ids:
            if await self.cancel(task_id, reason):
                cancelled += 1
        return cancelled


# ============================================================================
# Worker Pool for Processing Tasks
# ============================================================================

class WorkerPool:
    """
    Worker pool for processing tasks from the queue.
    
    Manages a pool of worker coroutines that consume and process tasks.
    Optimized for 64+ parallel workers.
    """
    
    def __init__(
        self,
        queue: TaskQueue,
        worker_id: str,
        capabilities: List[str] = None,
        max_concurrent: int = 1,
        task_handler: Callable[[Task], Any] = None
    ):
        self.queue = queue
        self.worker_id = worker_id
        self.capabilities = capabilities or []
        self.max_concurrent = max_concurrent
        self.task_handler = task_handler or self._default_handler
        
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._shutdown_event = asyncio.Event()
        self._worker_task: Optional[asyncio.Task] = None
        self._current_tasks: Dict[str, asyncio.Task] = {}
        
        self.stats = {
            'tasks_processed': 0,
            'tasks_failed': 0,
            'tasks_succeeded': 0,
            'start_time': None
        }
    
    def _default_handler(self, task: Task) -> Dict[str, Any]:
        """Default task handler - should be overridden."""
        logger.warning(f"No task handler defined for task {task.id}")
        return {'status': 'no_handler', 'task_id': task.id}
    
    async def start(self):
        """Start the worker pool."""
        # Register worker
        await self.queue.register_worker(
            worker_id=self.worker_id,
            capabilities=self.capabilities,
            max_concurrent_tasks=self.max_concurrent
        )
        
        self.stats['start_time'] = datetime.utcnow().isoformat()
        
        # Start worker loop
        self._worker_task = asyncio.create_task(self._worker_loop())
        
        # Start heartbeat
        asyncio.create_task(self._heartbeat_loop())
        
        logger.info(f"Worker pool {self.worker_id} started")
    
    async def stop(self):
        """Stop the worker pool."""
        self._shutdown_event.set()
        
        # Cancel current tasks
        for task in self._current_tasks.values():
            task.cancel()
        
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        
        # Unregister worker
        await self.queue.unregister_worker(self.worker_id)
        
        logger.info(f"Worker pool {self.worker_id} stopped")
    
    async def _worker_loop(self):
        """Main worker loop."""
        while not self._shutdown_event.is_set():
            try:
                # Acquire semaphore slot
                async with self._semaphore:
                    # Dequeue task
                    task = await self.queue.dequeue(self.worker_id, self.capabilities)
                    
                    if task:
                        # Process task
                        process_task = asyncio.create_task(self._process_task(task))
                        self._current_tasks[task.id] = process_task
                        
                        try:
                            await process_task
                        finally:
                            self._current_tasks.pop(task.id, None)
                    else:
                        # No tasks available, wait before polling again
                        await asyncio.wait_for(
                            self._shutdown_event.wait(),
                            timeout=self.queue.config.task_poll_interval_seconds
                        )
                        
            except asyncio.TimeoutError:
                pass
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                await asyncio.sleep(1)
    
    async def _process_task(self, task: Task):
        """Process a single task."""
        start_time = time.time()
        
        try:
            # Mark as running
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow().isoformat()
            
            # Execute handler
            result = await asyncio.wait_for(
                self._execute_handler(task),
                timeout=task.timeout_seconds
            )
            
            # Mark complete
            await self.queue.complete(task.id, result)
            
            self.stats['tasks_succeeded'] += 1
            
            execution_time = time.time() - start_time
            logger.info(f"Task {task.id} completed in {execution_time:.2f}s")
            
        except asyncio.TimeoutError:
            await self.queue.fail(task.id, f"Task timed out after {task.timeout_seconds}s")
            self.stats['tasks_failed'] += 1
            
        except Exception as e:
            logger.error(f"Task {task.id} failed: {e}")
            await self.queue.fail(task.id, str(e))
            self.stats['tasks_failed'] += 1
            
        finally:
            self.stats['tasks_processed'] += 1
    
    async def _execute_handler(self, task: Task) -> Any:
        """Execute the task handler."""
        if asyncio.iscoroutinefunction(self.task_handler):
            return await self.task_handler(task)
        else:
            # Run sync handler in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.task_handler, task)
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats."""
        while not self._shutdown_event.is_set():
            try:
                await self.queue.heartbeat(
                    self.worker_id,
                    status=WorkerStatus.BUSY if self._current_tasks else WorkerStatus.IDLE,
                    metrics={
                        'current_tasks': len(self._current_tasks),
                        'tasks_processed': self.stats['tasks_processed']
                    }
                )
                
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self.queue.config.worker_heartbeat_interval_seconds
                )
            except asyncio.TimeoutError:
                pass
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")


# ============================================================================
# Decorator for Task Handlers
# ============================================================================

def task_handler(capabilities: List[str] = None, max_concurrent: int = 1):
    """
    Decorator to mark a function as a task handler.
    
    Usage:
        @task_handler(capabilities=['python', 'fastapi'], max_concurrent=4)
        async def my_handler(task: Task) -> Dict[str, Any]:
            # Process task
            return {'result': 'success'}
    """
    def decorator(func: Callable):
        func._task_capabilities = capabilities or []
        func._task_max_concurrent = max_concurrent
        return func
    return decorator


# ============================================================================
# Convenience Functions
# ============================================================================

async def create_task_queue(
    redis_url: Optional[str] = None,
    redis_host: str = "localhost",
    redis_port: int = 6379,
    sqlite_path: str = "/tmp/apex_task_queue.db"
) -> TaskQueue:
    """
    Factory function to create and initialize a TaskQueue.
    
    Args:
        redis_url: Redis URL (overrides host/port)
        redis_host: Redis host
        redis_port: Redis port
        sqlite_path: SQLite fallback path
        
    Returns:
        Configured TaskQueue instance
    """
    config = QueueConfig(
        redis_url=redis_url,
        redis_host=redis_host,
        redis_port=redis_port,
        sqlite_path=sqlite_path
    )
    
    queue = TaskQueue(config)
    await queue.connect()
    await queue.start()
    
    return queue


async def create_worker_pool(
    queue: TaskQueue,
    name: str = None,
    capabilities: List[str] = None,
    max_concurrent: int = 1,
    task_handler: Callable = None
) -> WorkerPool:
    """
    Factory function to create and start a WorkerPool.
    
    Args:
        queue: TaskQueue instance
        name: Worker pool name
        capabilities: Worker capabilities
        max_concurrent: Max concurrent tasks
        task_handler: Task handler function
        
    Returns:
        Configured and started WorkerPool
    """
    worker_id = name or f"worker-{uuid.uuid4().hex[:8]}"
    
    pool = WorkerPool(
        queue=queue,
        worker_id=worker_id,
        capabilities=capabilities,
        max_concurrent=max_concurrent,
        task_handler=task_handler
    )
    
    await pool.start()
    return pool


# ============================================================================
# Demo/Test Code
# ============================================================================

async def demo_task_queue():
    """Demonstrate TaskQueue functionality."""
    print("=" * 70)
    print("APEX Distributed Task Queue - Demo")
    print("=" * 70)
    
    # Create queue
    print("\n1. Initializing TaskQueue...")
    queue = await create_task_queue(sqlite_path="/tmp/apex_task_queue_demo.db")
    print(f"   Connected to Redis: {queue._connected}")
    
    # Register workers with different capabilities
    print("\n2. Registering Workers...")
    workers = []
    
    # Python workers
    for i in range(3):
        worker = await queue.register_worker(
            name=f"python-worker-{i+1}",
            capabilities=['python', 'fastapi', 'django'],
            max_concurrent_tasks=2
        )
        workers.append(worker)
        print(f"   ✓ Registered {worker.name} ({worker.id[:8]}...)")
    
    # JavaScript workers
    for i in range(2):
        worker = await queue.register_worker(
            name=f"js-worker-{i+1}",
            capabilities=['javascript', 'nodejs', 'react'],
            max_concurrent_tasks=2
        )
        workers.append(worker)
        print(f"   ✓ Registered {worker.name} ({worker.id[:8]}...)")
    
    # General workers
    for i in range(2):
        worker = await queue.register_worker(
            name=f"general-worker-{i+1}",
            capabilities=['general'],
            max_concurrent_tasks=4
        )
        workers.append(worker)
        print(f"   ✓ Registered {worker.name} ({worker.id[:8]}...)")
    
    # Enqueue tasks
    print("\n3. Enqueuing Tasks...")
    
    # Critical priority task
    task1 = await queue.enqueue(
        task_type="security_audit",
        payload={"target": "api-endpoints", "scan_type": "full"},
        priority=TaskPriority.CRITICAL,
        required_capabilities=['python', 'fastapi'],
        tags=['security', 'audit']
    )
    print(f"   ✓ Enqueued CRITICAL task: {task1.id[:8]}...")
    
    # High priority tasks
    for i in range(3):
        task = await queue.enqueue(
            task_type="code_review",
            payload={"file": f"module_{i}.py", "lines": 150 + i * 50},
            priority=TaskPriority.HIGH,
            required_capabilities=['python'],
            tags=['review']
        )
        print(f"   ✓ Enqueued HIGH task: {task.id[:8]}...")
    
    # Normal priority tasks
    for i in range(5):
        task = await queue.enqueue(
            task_type="documentation",
            payload={"component": f"api_{i}", "format": "markdown"},
            priority=TaskPriority.NORMAL,
            required_capabilities=['general'],
            tags=['docs']
        )
        print(f"   ✓ Enqueued NORMAL task: {task.id[:8]}...")
    
    # Low priority tasks
    for i in range(3):
        task = await queue.enqueue(
            task_type="cleanup",
            payload={"target": f"logs_{i}"},
            priority=TaskPriority.LOW,
            tags=['maintenance']
        )
        print(f"   ✓ Enqueued LOW task: {task.id[:8]}...")
    
    # Background priority task
    task_bg = await queue.enqueue(
        task_type="analytics",
        payload={"metric": "daily_usage"},
        priority=TaskPriority.BACKGROUND,
        tags=['analytics']
    )
    print(f"   ✓ Enqueued BACKGROUND task: {task_bg.id[:8]}...")
    
    # Get stats
    print("\n4. Queue Statistics...")
    stats = await queue.get_stats()
    print(f"   Total Pending: {stats.total_pending}")
    print(f"   Workers: {stats.worker_count}")
    print(f"   Priority Breakdown: {stats.priority_breakdown}")
    
    # Simulate task processing
    print("\n5. Simulating Task Processing...")
    
    async def mock_handler(task: Task) -> Dict[str, Any]:
        """Mock task handler."""
        # Update progress
        await queue.update_progress(task.id, percent=0, current_step="starting")
        await asyncio.sleep(0.1)
        
        await queue.update_progress(task.id, percent=50, current_step="processing")
        await asyncio.sleep(0.1)
        
        await queue.update_progress(task.id, percent=100, current_step="completed")
        
        return {'status': 'success', 'task_type': task.type}
    
    # Process some tasks
    for i, worker in enumerate(workers[:3]):
        task = await queue.dequeue(worker.id, worker.capabilities)
        if task:
            print(f"   Worker {worker.name} dequeued: {task.id[:8]}... (priority={task.priority.name})")
            
            # Simulate processing
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow().isoformat()
            
            await mock_handler(task)
            await queue.complete(task.id, {'processed_by': worker.name})
            print(f"   ✓ Task completed by {worker.name}")
    
    # Show remaining tasks
    print("\n6. Remaining Tasks...")
    remaining = await queue.get_tasks(status=TaskStatus.PENDING)
    print(f"   Pending tasks: {len(remaining)}")
    
    # Test retry mechanism
    print("\n7. Testing Retry Mechanism...")
    
    # Create a task that will fail
    fail_task = await queue.enqueue(
        task_type="unreliable_task",
        payload={"should_fail": True},
        priority=TaskPriority.HIGH,
        max_retries=2
    )
    print(f"   Created task: {fail_task.id[:8]}...")
    
    # Simulate failure and retry
    await queue.fail(fail_task.id, "Simulated failure")
    
    # Check task status after fail
    updated_task = await queue.get_task(fail_task.id)
    if updated_task:
        print(f"   Task status after fail: {updated_task.status.value}")
        print(f"   Retry count: {updated_task.retry_count}/{updated_task.max_retries}")
    
    # Test batch operations
    print("\n8. Testing Batch Operations...")
    batch_tasks = await queue.enqueue_many([
        {'type': 'batch_task', 'payload': {'index': i}, 'priority': TaskPriority.NORMAL}
        for i in range(10)
    ])
    print(f"   ✓ Batch enqueued {len(batch_tasks)} tasks")
    
    # Final stats
    print("\n9. Final Statistics...")
    stats = await queue.get_stats()
    print(f"   Total Pending: {stats.total_pending}")
    print(f"   Total Running: {stats.total_running}")
    print(f"   Total Completed: {stats.total_completed}")
    print(f"   Total Failed: {stats.total_failed}")
    
    # Cleanup
    print("\n10. Cleanup...")
    await queue.disconnect()
    print("   ✓ Queue disconnected")
    
    # Cleanup SQLite file
    import os
    try:
        os.remove("/tmp/apex_task_queue_demo.db")
        print("   ✓ Demo database removed")
    except:
        pass
    
    print("\n" + "=" * 70)
    print("Demo completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(demo_task_queue())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise
