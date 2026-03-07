#!/usr/bin/env python3
"""
APEX PostgreSQL Persistence Layer

Production-grade checkpoint and agent state storage with:
- Connection pooling using asyncpg
- Automatic schema migrations
- Read replica support for scaling
- Connection health monitoring

Replaces SQLite for production deployments.

Author: APEX Infrastructure Team
Version: 1.0.0
"""

import json
import os
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('PostgresManager')

# Optional asyncpg import with graceful fallback
try:
    import asyncpg
    from asyncpg import Pool, Connection
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    logger.warning("asyncpg not available. PostgreSQL persistence will be unavailable.")


class AgentStatus(str, Enum):
    """Agent status states"""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Checkpoint:
    """Checkpoint data model"""
    id: str
    session_id: str
    build_id: str
    stage: str
    agent_outputs: Dict[str, Any]
    metadata: Dict[str, Any]
    git_commit_hash: Optional[str]
    created_at: datetime
    tier: int = 2


@dataclass
class AgentState:
    """Agent state data model"""
    agent_id: str
    agent_type: str
    status: AgentStatus
    current_task: Optional[str]
    success_rate: float
    last_heartbeat: datetime
    metadata: Dict[str, Any]


@dataclass
class TaskRecord:
    """Task execution record"""
    task_id: str
    task_type: str
    agent_id: str
    input_data: Dict[str, Any]
    result: Optional[Dict[str, Any]]
    status: TaskStatus
    started_at: datetime
    completed_at: Optional[datetime]


@dataclass
class ConsensusRecord:
    """Consensus evaluation record"""
    task_id: str
    verifier_results: Dict[str, Any]
    consensus_score: float
    decision: str
    created_at: datetime


@dataclass
class EvaluationReport:
    """Evaluation report data model"""
    id: str
    change_id: str
    scores: Dict[str, float]
    findings: List[Dict[str, Any]]
    recommendations: List[str]
    timestamp: datetime


@dataclass
class ConnectionHealth:
    """Connection health metrics"""
    is_healthy: bool
    total_connections: int
    free_connections: int
    used_connections: int
    waiting_requests: int
    latency_ms: float
    last_check: datetime


class PostgresManager:
    """
    Production-ready PostgreSQL persistence manager for APEX.
    
    Features:
    - Async connection pooling with configurable min/max connections
    - Read replica support for scaling read operations
    - Automatic schema migrations
    - Connection health monitoring
    - Query timeout enforcement
    - SSL/TLS encryption for production
    """
    
    # Schema version for migrations
    SCHEMA_VERSION = 1
    
    # Default configuration
    DEFAULT_MIN_CONNECTIONS = 5
    DEFAULT_MAX_CONNECTIONS = 20
    DEFAULT_QUERY_TIMEOUT = 30  # seconds
    DEFAULT_CONNECT_TIMEOUT = 10  # seconds
    
    def __init__(
        self,
        database_url: Optional[str] = None,
        read_replica_urls: Optional[List[str]] = None,
        min_connections: int = DEFAULT_MIN_CONNECTIONS,
        max_connections: int = DEFAULT_MAX_CONNECTIONS,
        query_timeout: int = DEFAULT_QUERY_TIMEOUT,
        ssl_mode: str = "require",
        enable_logging: bool = True
    ):
        """
        Initialize PostgreSQL manager.
        
        Args:
            database_url: Primary database URL (postgresql://user:pass@host/db)
            read_replica_urls: List of read replica URLs for load balancing
            min_connections: Minimum connections in pool
            max_connections: Maximum connections in pool
            query_timeout: Query timeout in seconds
            ssl_mode: SSL mode ('disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full')
            enable_logging: Enable operation logging
        """
        if not ASYNCPG_AVAILABLE:
            raise RuntimeError("asyncpg is required for PostgreSQL persistence. Install with: pip install asyncpg")
        
        self.database_url = database_url or os.getenv(
            'DATABASE_URL', 
            'postgresql://apex:apex@localhost/apex'
        )
        self.read_replica_urls = read_replica_urls or []
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.query_timeout = query_timeout
        self.ssl_mode = ssl_mode
        self.enable_logging = enable_logging
        
        # Connection pools
        self._primary_pool: Optional[Pool] = None
        self._replica_pools: List[Pool] = []
        self._replica_index = 0  # Round-robin index
        
        # Health tracking
        self._health_metrics: Dict[str, Any] = {}
        self._last_health_check: Optional[datetime] = None
        
        # Migration tracking
        self._schema_initialized = False
        
        if enable_logging:
            logger.info(f"PostgresManager initialized (pool: {min_connections}-{max_connections}, timeout: {query_timeout}s)")
    
    # ==================== Connection Management ====================
    
    async def connect(self) -> None:
        """Initialize connection pools to primary and read replicas."""
        try:
            # Create primary connection pool
            self._primary_pool = await asyncpg.create_pool(
                self.database_url,
                min_size=self.min_connections,
                max_size=self.max_connections,
                command_timeout=self.query_timeout,
                ssl=self._get_ssl_context(),
                init=self._init_connection
            )
            
            if self.enable_logging:
                logger.info(f"Primary PostgreSQL pool created: {self.min_connections}-{self.max_connections} connections")
            
            # Create read replica pools
            for replica_url in self.read_replica_urls:
                try:
                    replica_pool = await asyncpg.create_pool(
                        replica_url,
                        min_size=max(1, self.min_connections // 2),
                        max_size=max(5, self.max_connections // 2),
                        command_timeout=self.query_timeout,
                        ssl=self._get_ssl_context(),
                        init=self._init_connection
                    )
                    self._replica_pools.append(replica_pool)
                    if self.enable_logging:
                        logger.info(f"Read replica pool added")
                except Exception as e:
                    logger.warning(f"Failed to connect to read replica: {e}")
            
            # Run migrations if needed
            await self.init_schema()
            
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close all connection pools."""
        try:
            if self._primary_pool:
                await self._primary_pool.close()
                if self.enable_logging:
                    logger.info("Primary PostgreSQL pool closed")
            
            for pool in self._replica_pools:
                await pool.close()
            
            self._replica_pools.clear()
            self._primary_pool = None
            
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
            raise
    
    def _get_ssl_context(self) -> Union[str, bool]:
        """Get SSL context based on ssl_mode."""
        ssl_modes = {
            'disable': False,
            'allow': 'prefer',
            'prefer': 'prefer',
            'require': 'require',
            'verify-ca': 'verify-ca',
            'verify-full': 'verify-full'
        }
        return ssl_modes.get(self.ssl_mode, 'require')
    
    async def _init_connection(self, conn: Connection) -> None:
        """Initialize connection with custom types."""
        # Set JSON encoder/decoder
        await conn.set_type_codec(
            'json',
            encoder=json.dumps,
            decoder=json.loads,
            schema='pg_catalog'
        )
        await conn.set_type_codec(
            'jsonb',
            encoder=json.dumps,
            decoder=json.loads,
            schema='pg_catalog'
        )
    
    @asynccontextmanager
    async def _get_connection(self, use_replica: bool = False):
        """
        Get connection from pool (primary or replica).
        
        Args:
            use_replica: If True, use read replica for load balancing
        """
        if use_replica and self._replica_pools:
            # Round-robin selection
            pool = self._replica_pools[self._replica_index % len(self._replica_pools)]
            self._replica_index += 1
        else:
            pool = self._primary_pool
        
        if not pool:
            raise RuntimeError("Not connected to PostgreSQL. Call connect() first.")
        
        async with pool.acquire() as conn:
            yield conn
    
    async def health_check(self) -> ConnectionHealth:
        """
        Check connection pool health.
        
        Returns:
            ConnectionHealth with current metrics
        """
        start_time = datetime.utcnow()
        
        try:
            async with self._get_connection() as conn:
                # Test query
                await conn.fetchval('SELECT 1')
                
                # Get pool stats
                pool = self._primary_pool
                size = pool.get_size()
                free = pool.get_free_size()
                
                latency = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                health = ConnectionHealth(
                    is_healthy=True,
                    total_connections=size,
                    free_connections=free,
                    used_connections=size - free,
                    waiting_requests=pool.get_max_size() - size if size < pool.get_max_size() else 0,
                    latency_ms=latency,
                    last_check=datetime.utcnow()
                )
                
                self._health_metrics = asdict(health)
                self._last_health_check = health.last_check
                
                return health
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return ConnectionHealth(
                is_healthy=False,
                total_connections=0,
                free_connections=0,
                used_connections=0,
                waiting_requests=0,
                latency_ms=-1,
                last_check=datetime.utcnow()
            )
    
    # ==================== Schema Management ====================
    
    async def init_schema(self) -> None:
        """Initialize database schema with all tables and indexes."""
        if self._schema_initialized:
            return
        
        async with self._get_connection() as conn:
            async with conn.transaction():
                # Create schema version table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version INTEGER PRIMARY KEY,
                        applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        description TEXT
                    )
                """)
                
                # Check current version
                current_version = await conn.fetchval(
                    "SELECT MAX(version) FROM schema_migrations"
                ) or 0
                
                if current_version < self.SCHEMA_VERSION:
                    await self._run_migrations(conn, current_version)
                
                self._schema_initialized = True
        
        if self.enable_logging:
            logger.info(f"Database schema initialized (version {self.SCHEMA_VERSION})")
    
    async def _run_migrations(self, conn: Connection, from_version: int) -> None:
        """Run migrations from current version to target."""
        migrations = [
            # Version 1: Initial schema
            self._migration_v1,
        ]
        
        for version, migration in enumerate(migrations, start=1):
            if version > from_version:
                await migration(conn)
                await conn.execute(
                    "INSERT INTO schema_migrations (version, description) VALUES ($1, $2)",
                    version,
                    f"Migration to version {version}"
                )
                if self.enable_logging:
                    logger.info(f"Applied migration to version {version}")
    
    async def _migration_v1(self, conn: Connection) -> None:
        """Initial schema migration - create all tables and indexes."""
        # Checkpoints table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                id VARCHAR(255) PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL,
                build_id VARCHAR(255) NOT NULL,
                stage VARCHAR(100) NOT NULL,
                agent_outputs JSONB DEFAULT '{}',
                metadata JSONB DEFAULT '{}',
                git_commit_hash VARCHAR(40),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                tier INTEGER DEFAULT 2
            )
        """)
        
        # Agent states table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_states (
                agent_id VARCHAR(255) PRIMARY KEY,
                agent_type VARCHAR(100) NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'idle',
                current_task VARCHAR(255),
                success_rate DECIMAL(5,4) DEFAULT 1.0,
                last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB DEFAULT '{}',
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Task history table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS task_history (
                task_id VARCHAR(255) PRIMARY KEY,
                task_type VARCHAR(100) NOT NULL,
                agent_id VARCHAR(255) NOT NULL,
                input_data JSONB DEFAULT '{}',
                result JSONB,
                status VARCHAR(50) NOT NULL DEFAULT 'pending',
                started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Consensus records table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS consensus_records (
                id SERIAL PRIMARY KEY,
                task_id VARCHAR(255) NOT NULL,
                verifier_results JSONB NOT NULL,
                consensus_score DECIMAL(5,4) NOT NULL,
                decision VARCHAR(50) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Evaluation reports table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS evaluation_reports (
                id VARCHAR(255) PRIMARY KEY,
                change_id VARCHAR(255) NOT NULL,
                scores JSONB NOT NULL,
                findings JSONB DEFAULT '[]',
                recommendations JSONB DEFAULT '[]',
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_checkpoints_session_id 
            ON checkpoints(session_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_checkpoints_build_id 
            ON checkpoints(build_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_checkpoints_created_at 
            ON checkpoints(created_at DESC)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_checkpoints_session_build 
            ON checkpoints(session_id, build_id)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_states_agent_id 
            ON agent_states(agent_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_states_status 
            ON agent_states(status)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_states_heartbeat 
            ON agent_states(last_heartbeat DESC)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_history_task_id 
            ON task_history(task_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_history_agent_id 
            ON task_history(agent_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_history_started_at 
            ON task_history(started_at DESC)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_history_status 
            ON task_history(status)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_consensus_task_id 
            ON consensus_records(task_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_consensus_created_at 
            ON consensus_records(created_at DESC)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_evaluations_change_id 
            ON evaluation_reports(change_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_evaluations_timestamp 
            ON evaluation_reports(timestamp DESC)
        """)
    
    async def run_migrations(self) -> None:
        """Public method to manually trigger migrations."""
        async with self._get_connection() as conn:
            current_version = await conn.fetchval(
                "SELECT MAX(version) FROM schema_migrations"
            ) or 0
            
            if current_version < self.SCHEMA_VERSION:
                async with conn.transaction():
                    await self._run_migrations(conn, current_version)
                if self.enable_logging:
                    logger.info(f"Migrations completed (v{current_version} -> v{self.SCHEMA_VERSION})")
            else:
                if self.enable_logging:
                    logger.info(f"Schema is up to date (v{current_version})")
    
    async def reset_schema(self) -> None:
        """
        WARNING: Drops all tables and recreates schema.
        Use with extreme caution in production!
        """
        async with self._get_connection() as conn:
            async with conn.transaction():
                await conn.execute("DROP TABLE IF EXISTS schema_migrations CASCADE")
                await conn.execute("DROP TABLE IF EXISTS checkpoints CASCADE")
                await conn.execute("DROP TABLE IF EXISTS agent_states CASCADE")
                await conn.execute("DROP TABLE IF EXISTS task_history CASCADE")
                await conn.execute("DROP TABLE IF EXISTS consensus_records CASCADE")
                await conn.execute("DROP TABLE IF EXISTS evaluation_reports CASCADE")
        
        self._schema_initialized = False
        await self.init_schema()
        
        logger.warning("Database schema has been reset!")
    
    # ==================== Checkpoint Operations ====================
    
    async def store_checkpoint(self, checkpoint: Checkpoint) -> None:
        """
        Store a checkpoint in the database.
        
        Args:
            checkpoint: Checkpoint object to store
        """
        async with self._get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO checkpoints 
                (id, session_id, build_id, stage, agent_outputs, metadata, git_commit_hash, created_at, tier)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (id) DO UPDATE SET
                    agent_outputs = EXCLUDED.agent_outputs,
                    metadata = EXCLUDED.metadata,
                    git_commit_hash = EXCLUDED.git_commit_hash,
                    tier = EXCLUDED.tier
                """,
                checkpoint.id,
                checkpoint.session_id,
                checkpoint.build_id,
                checkpoint.stage,
                json.dumps(checkpoint.agent_outputs),
                json.dumps(checkpoint.metadata),
                checkpoint.git_commit_hash,
                checkpoint.created_at,
                checkpoint.tier
            )
        
        if self.enable_logging:
            logger.debug(f"Checkpoint stored: {checkpoint.id}")
    
    async def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """
        Retrieve a checkpoint by ID.
        
        Args:
            checkpoint_id: Checkpoint identifier
            
        Returns:
            Checkpoint object or None if not found
        """
        async with self._get_connection(use_replica=True) as conn:
            row = await conn.fetchrow(
                "SELECT * FROM checkpoints WHERE id = $1",
                checkpoint_id
            )
            
            if row:
                return Checkpoint(
                    id=row['id'],
                    session_id=row['session_id'],
                    build_id=row['build_id'],
                    stage=row['stage'],
                    agent_outputs=row['agent_outputs'] or {},
                    metadata=row['metadata'] or {},
                    git_commit_hash=row['git_commit_hash'],
                    created_at=row['created_at'],
                    tier=row['tier']
                )
            return None
    
    async def query_checkpoints(
        self,
        session_id: Optional[str] = None,
        build_id: Optional[str] = None,
        stage: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Checkpoint]:
        """
        Query checkpoints with filters.
        
        Args:
            session_id: Filter by session ID
            build_id: Filter by build ID
            stage: Filter by stage
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            List of matching checkpoints
        """
        conditions = []
        params = []
        param_idx = 1
        
        if session_id:
            conditions.append(f"session_id = ${param_idx}")
            params.append(session_id)
            param_idx += 1
        
        if build_id:
            conditions.append(f"build_id = ${param_idx}")
            params.append(build_id)
            param_idx += 1
        
        if stage:
            conditions.append(f"stage = ${param_idx}")
            params.append(stage)
            param_idx += 1
        
        if start_time:
            conditions.append(f"created_at >= ${param_idx}")
            params.append(start_time)
            param_idx += 1
        
        if end_time:
            conditions.append(f"created_at <= ${param_idx}")
            params.append(end_time)
            param_idx += 1
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        query = f"""
            SELECT * FROM checkpoints
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([limit, offset])
        
        async with self._get_connection(use_replica=True) as conn:
            rows = await conn.fetch(query, *params)
            
            return [
                Checkpoint(
                    id=row['id'],
                    session_id=row['session_id'],
                    build_id=row['build_id'],
                    stage=row['stage'],
                    agent_outputs=row['agent_outputs'] or {},
                    metadata=row['metadata'] or {},
                    git_commit_hash=row['git_commit_hash'],
                    created_at=row['created_at'],
                    tier=row['tier']
                )
                for row in rows
            ]
    
    # ==================== Agent State Operations ====================
    
    async def store_agent_state(self, agent_state: AgentState) -> None:
        """
        Store or update an agent state.
        
        Args:
            agent_state: AgentState object to store
        """
        async with self._get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO agent_states 
                (agent_id, agent_type, status, current_task, success_rate, last_heartbeat, metadata, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, CURRENT_TIMESTAMP)
                ON CONFLICT (agent_id) DO UPDATE SET
                    agent_type = EXCLUDED.agent_type,
                    status = EXCLUDED.status,
                    current_task = EXCLUDED.current_task,
                    success_rate = EXCLUDED.success_rate,
                    last_heartbeat = EXCLUDED.last_heartbeat,
                    metadata = EXCLUDED.metadata,
                    updated_at = CURRENT_TIMESTAMP
                """,
                agent_state.agent_id,
                agent_state.agent_type,
                agent_state.status.value,
                agent_state.current_task,
                agent_state.success_rate,
                agent_state.last_heartbeat,
                json.dumps(agent_state.metadata)
            )
        
        if self.enable_logging:
            logger.debug(f"Agent state stored: {agent_state.agent_id}")
    
    async def get_agent_state(self, agent_id: str) -> Optional[AgentState]:
        """
        Retrieve an agent state by ID.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            AgentState object or None if not found
        """
        async with self._get_connection(use_replica=True) as conn:
            row = await conn.fetchrow(
                "SELECT * FROM agent_states WHERE agent_id = $1",
                agent_id
            )
            
            if row:
                return AgentState(
                    agent_id=row['agent_id'],
                    agent_type=row['agent_type'],
                    status=AgentStatus(row['status']),
                    current_task=row['current_task'],
                    success_rate=row['success_rate'],
                    last_heartbeat=row['last_heartbeat'],
                    metadata=row['metadata'] or {}
                )
            return None
    
    async def update_agent_state(
        self,
        agent_id: str,
        status: Optional[AgentStatus] = None,
        current_task: Optional[str] = None,
        success_rate: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        heartbeat: bool = True
    ) -> bool:
        """
        Update specific fields of an agent state.
        
        Args:
            agent_id: Agent identifier
            status: New status
            current_task: New current task
            success_rate: New success rate
            metadata: Metadata updates (merged with existing)
            heartbeat: Update last_heartbeat timestamp
            
        Returns:
            True if agent was found and updated
        """
        updates = []
        params = []
        param_idx = 1
        
        if status:
            updates.append(f"status = ${param_idx}")
            params.append(status.value)
            param_idx += 1
        
        if current_task is not None:
            updates.append(f"current_task = ${param_idx}")
            params.append(current_task)
            param_idx += 1
        
        if success_rate is not None:
            updates.append(f"success_rate = ${param_idx}")
            params.append(success_rate)
            param_idx += 1
        
        if heartbeat:
            updates.append(f"last_heartbeat = CURRENT_TIMESTAMP")
        
        if metadata:
            # Merge with existing metadata
            updates.append(f"metadata = COALESCE(metadata, '{{}}'::jsonb) || ${param_idx}::jsonb")
            params.append(json.dumps(metadata))
            param_idx += 1
        
        if not updates:
            return False
        
        updates.append(f"updated_at = CURRENT_TIMESTAMP")
        
        query = f"""
            UPDATE agent_states 
            SET {', '.join(updates)}
            WHERE agent_id = ${param_idx}
            RETURNING agent_id
        """
        params.append(agent_id)
        
        async with self._get_connection() as conn:
            row = await conn.fetchrow(query, *params)
            return row is not None
    
    async def get_active_agents(self, max_heartbeat_age: int = 300) -> List[AgentState]:
        """
        Get all agents with recent heartbeat.
        
        Args:
            max_heartbeat_age: Maximum seconds since last heartbeat
            
        Returns:
            List of active agent states
        """
        cutoff = datetime.utcnow() - timedelta(seconds=max_heartbeat_age)
        
        async with self._get_connection(use_replica=True) as conn:
            rows = await conn.fetch(
                "SELECT * FROM agent_states WHERE last_heartbeat > $1 ORDER BY last_heartbeat DESC",
                cutoff
            )
            
            return [
                AgentState(
                    agent_id=row['agent_id'],
                    agent_type=row['agent_type'],
                    status=AgentStatus(row['status']),
                    current_task=row['current_task'],
                    success_rate=row['success_rate'],
                    last_heartbeat=row['last_heartbeat'],
                    metadata=row['metadata'] or {}
                )
                for row in rows
            ]
    
    # ==================== Task History Operations ====================
    
    async def store_task(self, task: TaskRecord) -> None:
        """
        Store a task execution record.
        
        Args:
            task: TaskRecord object to store
        """
        async with self._get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO task_history 
                (task_id, task_type, agent_id, input_data, result, status, started_at, completed_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (task_id) DO UPDATE SET
                    result = EXCLUDED.result,
                    status = EXCLUDED.status,
                    completed_at = EXCLUDED.completed_at
                """,
                task.task_id,
                task.task_type,
                task.agent_id,
                json.dumps(task.input_data),
                json.dumps(task.result) if task.result else None,
                task.status.value,
                task.started_at,
                task.completed_at
            )
        
        if self.enable_logging:
            logger.debug(f"Task stored: {task.task_id}")
    
    async def get_task_history(
        self,
        agent_id: Optional[str] = None,
        task_type: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[TaskRecord]:
        """
        Query task history with filters.
        
        Args:
            agent_id: Filter by agent ID
            task_type: Filter by task type
            status: Filter by status
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            List of matching task records
        """
        conditions = []
        params = []
        param_idx = 1
        
        if agent_id:
            conditions.append(f"agent_id = ${param_idx}")
            params.append(agent_id)
            param_idx += 1
        
        if task_type:
            conditions.append(f"task_type = ${param_idx}")
            params.append(task_type)
            param_idx += 1
        
        if status:
            conditions.append(f"status = ${param_idx}")
            params.append(status.value)
            param_idx += 1
        
        if start_time:
            conditions.append(f"started_at >= ${param_idx}")
            params.append(start_time)
            param_idx += 1
        
        if end_time:
            conditions.append(f"started_at <= ${param_idx}")
            params.append(end_time)
            param_idx += 1
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        query = f"""
            SELECT * FROM task_history
            {where_clause}
            ORDER BY started_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([limit, offset])
        
        async with self._get_connection(use_replica=True) as conn:
            rows = await conn.fetch(query, *params)
            
            return [
                TaskRecord(
                    task_id=row['task_id'],
                    task_type=row['task_type'],
                    agent_id=row['agent_id'],
                    input_data=row['input_data'] or {},
                    result=row['result'],
                    status=TaskStatus(row['status']),
                    started_at=row['started_at'],
                    completed_at=row['completed_at']
                )
                for row in rows
            ]
    
    async def get_agent_performance(
        self,
        agent_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get performance metrics for an agent.
        
        Args:
            agent_id: Agent identifier
            days: Number of days to analyze
            
        Returns:
            Performance metrics dictionary
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        async with self._get_connection(use_replica=True) as conn:
            # Overall stats
            stats = await conn.fetchrow(
                """
                SELECT 
                    COUNT(*) as total_tasks,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed_tasks,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed_tasks,
                    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) FILTER (WHERE completed_at IS NOT NULL) as avg_duration
                FROM task_history
                WHERE agent_id = $1 AND started_at >= $2
                """,
                agent_id,
                start_date
            )
            
            # Daily breakdown
            daily = await conn.fetch(
                """
                SELECT 
                    DATE(started_at) as date,
                    COUNT(*) as tasks,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed
                FROM task_history
                WHERE agent_id = $1 AND started_at >= $2
                GROUP BY DATE(started_at)
                ORDER BY date DESC
                """,
                agent_id,
                start_date
            )
            
            total = stats['total_tasks'] or 0
            completed = stats['completed_tasks'] or 0
            failed = stats['failed_tasks'] or 0
            
            return {
                'agent_id': agent_id,
                'period_days': days,
                'total_tasks': total,
                'completed_tasks': completed,
                'failed_tasks': failed,
                'success_rate': completed / total if total > 0 else 0,
                'avg_duration_seconds': stats['avg_duration'] or 0,
                'daily_breakdown': [
                    {
                        'date': row['date'].isoformat(),
                        'tasks': row['tasks'],
                        'completed': row['completed'],
                        'failed': row['failed']
                    }
                    for row in daily
                ]
            }
    
    # ==================== Consensus Operations ====================
    
    async def store_consensus_record(self, record: ConsensusRecord) -> None:
        """
        Store a consensus evaluation record.
        
        Args:
            record: ConsensusRecord object to store
        """
        async with self._get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO consensus_records 
                (task_id, verifier_results, consensus_score, decision, created_at)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT DO NOTHING
                """,
                record.task_id,
                json.dumps(record.verifier_results),
                record.consensus_score,
                record.decision,
                record.created_at
            )
        
        if self.enable_logging:
            logger.debug(f"Consensus record stored: {record.task_id}")
    
    async def get_consensus_history(
        self,
        task_id: Optional[str] = None,
        decision: Optional[str] = None,
        min_score: Optional[float] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[ConsensusRecord]:
        """
        Query consensus history with filters.
        
        Args:
            task_id: Filter by task ID
            decision: Filter by decision (PROCEED, REVIEW, REJECT)
            min_score: Minimum consensus score
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum results
            
        Returns:
            List of matching consensus records
        """
        conditions = []
        params = []
        param_idx = 1
        
        if task_id:
            conditions.append(f"task_id = ${param_idx}")
            params.append(task_id)
            param_idx += 1
        
        if decision:
            conditions.append(f"decision = ${param_idx}")
            params.append(decision)
            param_idx += 1
        
        if min_score is not None:
            conditions.append(f"consensus_score >= ${param_idx}")
            params.append(min_score)
            param_idx += 1
        
        if start_time:
            conditions.append(f"created_at >= ${param_idx}")
            params.append(start_time)
            param_idx += 1
        
        if end_time:
            conditions.append(f"created_at <= ${param_idx}")
            params.append(end_time)
            param_idx += 1
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        query = f"""
            SELECT * FROM consensus_records
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_idx}
        """
        params.append(limit)
        
        async with self._get_connection(use_replica=True) as conn:
            rows = await conn.fetch(query, *params)
            
            return [
                ConsensusRecord(
                    task_id=row['task_id'],
                    verifier_results=row['verifier_results'] or {},
                    consensus_score=row['consensus_score'],
                    decision=row['decision'],
                    created_at=row['created_at']
                )
                for row in rows
            ]
    
    async def get_consensus_statistics(
        self,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get consensus statistics for a time period.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Statistics dictionary
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        async with self._get_connection(use_replica=True) as conn:
            stats = await conn.fetchrow(
                """
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE decision = 'PROCEED') as proceed,
                    COUNT(*) FILTER (WHERE decision = 'REVIEW') as review,
                    COUNT(*) FILTER (WHERE decision = 'REJECT') as reject,
                    AVG(consensus_score) as avg_score
                FROM consensus_records
                WHERE created_at >= $1
                """,
                start_date
            )
            
            total = stats['total'] or 0
            
            return {
                'period_days': days,
                'total_evaluations': total,
                'proceed_count': stats['proceed'] or 0,
                'review_count': stats['review'] or 0,
                'reject_count': stats['reject'] or 0,
                'proceed_rate': (stats['proceed'] or 0) / total if total > 0 else 0,
                'average_score': stats['avg_score'] or 0
            }
    
    # ==================== Evaluation Operations ====================
    
    async def store_evaluation(self, evaluation: EvaluationReport) -> None:
        """
        Store an evaluation report.
        
        Args:
            evaluation: EvaluationReport object to store
        """
        async with self._get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO evaluation_reports 
                (id, change_id, scores, findings, recommendations, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (id) DO UPDATE SET
                    scores = EXCLUDED.scores,
                    findings = EXCLUDED.findings,
                    recommendations = EXCLUDED.recommendations,
                    timestamp = EXCLUDED.timestamp
                """,
                evaluation.id,
                evaluation.change_id,
                json.dumps(evaluation.scores),
                json.dumps(evaluation.findings),
                json.dumps(evaluation.recommendations),
                evaluation.timestamp
            )
        
        if self.enable_logging:
            logger.debug(f"Evaluation stored: {evaluation.id}")
    
    async def get_evaluation_trends(
        self,
        change_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get evaluation trends over time.
        
        Args:
            change_id: Optional change ID to filter
            days: Number of days to analyze
            
        Returns:
            Trends dictionary with time series data
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        async with self._get_connection(use_replica=True) as conn:
            # Build query
            if change_id:
                rows = await conn.fetch(
                    """
                    SELECT 
                        timestamp,
                        scores
                    FROM evaluation_reports
                    WHERE change_id = $1 AND timestamp >= $2
                    ORDER BY timestamp ASC
                    """,
                    change_id,
                    start_date
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT 
                        DATE(timestamp) as date,
                        AVG((scores->>'overall')::float) as avg_overall,
                        AVG((scores->>'syntax')::float) as avg_syntax,
                        AVG((scores->>'logic')::float) as avg_logic,
                        AVG((scores->>'security')::float) as avg_security,
                        COUNT(*) as count
                    FROM evaluation_reports
                    WHERE timestamp >= $1
                    GROUP BY DATE(timestamp)
                    ORDER BY date ASC
                    """,
                    start_date
                )
            
            if change_id:
                # Return individual evaluations for specific change
                return {
                    'change_id': change_id,
                    'period_days': days,
                    'evaluations': [
                        {
                            'timestamp': row['timestamp'].isoformat(),
                            'scores': row['scores']
                        }
                        for row in rows
                    ]
                }
            else:
                # Return aggregated trends
                return {
                    'period_days': days,
                    'daily_trends': [
                        {
                            'date': row['date'].isoformat(),
                            'avg_overall': row['avg_overall'] or 0,
                            'avg_syntax': row['avg_syntax'] or 0,
                            'avg_logic': row['avg_logic'] or 0,
                            'avg_security': row['avg_security'] or 0,
                            'count': row['count']
                        }
                        for row in rows
                    ]
                }
    
    async def get_latest_evaluation(
        self,
        change_id: str
    ) -> Optional[EvaluationReport]:
        """
        Get the most recent evaluation for a change.
        
        Args:
            change_id: Change identifier
            
        Returns:
            Latest EvaluationReport or None
        """
        async with self._get_connection(use_replica=True) as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM evaluation_reports
                WHERE change_id = $1
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                change_id
            )
            
            if row:
                return EvaluationReport(
                    id=row['id'],
                    change_id=row['change_id'],
                    scores=row['scores'] or {},
                    findings=row['findings'] or [],
                    recommendations=row['recommendations'] or [],
                    timestamp=row['timestamp']
                )
            return None


# ==================== Demo / Test Code ====================

async def demo():
    """
    Demonstration and test of PostgresManager functionality.
    Requires a running PostgreSQL instance.
    """
    print("=" * 60)
    print("APEX PostgreSQL Persistence Layer Demo")
    print("=" * 60)
    
    # Configuration from environment or defaults
    database_url = os.getenv(
        'DATABASE_URL',
        'postgresql://apex:apex@localhost:5432/apex'
    )
    
    print(f"\n1. Initializing PostgresManager...")
    print(f"   Database: {database_url.split('@')[-1]}")  # Hide credentials
    
    try:
        manager = PostgresManager(
            database_url=database_url,
            min_connections=2,
            max_connections=5,
            query_timeout=30,
            ssl_mode='disable' if 'localhost' in database_url else 'require',
            enable_logging=True
        )
        
        # Connect and initialize
        print("\n2. Connecting to PostgreSQL...")
        await manager.connect()
        print("   ✓ Connected successfully")
        
        # Health check
        print("\n3. Running health check...")
        health = await manager.health_check()
        print(f"   ✓ Healthy: {health.is_healthy}")
        print(f"   ✓ Total connections: {health.total_connections}")
        print(f"   ✓ Free connections: {health.free_connections}")
        print(f"   ✓ Latency: {health.latency_ms:.2f}ms")
        
        # Store checkpoint
        print("\n4. Storing checkpoint...")
        checkpoint = Checkpoint(
            id="demo-checkpoint-001",
            session_id="session-abc",
            build_id="build-123",
            stage="planning",
            agent_outputs={"planner": {"files": ["plan.md"]}},
            metadata={"test": True, "demo": True},
            git_commit_hash="abc123def456",
            created_at=datetime.utcnow(),
            tier=2
        )
        await manager.store_checkpoint(checkpoint)
        print("   ✓ Checkpoint stored")
        
        # Retrieve checkpoint
        print("\n5. Retrieving checkpoint...")
        retrieved = await manager.get_checkpoint("demo-checkpoint-001")
        if retrieved:
            print(f"   ✓ Found: {retrieved.id}")
            print(f"   ✓ Build: {retrieved.build_id}")
            print(f"   ✓ Stage: {retrieved.stage}")
        
        # Query checkpoints
        print("\n6. Querying checkpoints...")
        checkpoints = await manager.query_checkpoints(
            session_id="session-abc",
            limit=10
        )
        print(f"   ✓ Found {len(checkpoints)} checkpoint(s)")
        
        # Store agent state
        print("\n7. Storing agent state...")
        agent_state = AgentState(
            agent_id="agent-demo-001",
            agent_type="planner",
            status=AgentStatus.BUSY,
            current_task="task-123",
            success_rate=0.95,
            last_heartbeat=datetime.utcnow(),
            metadata={"version": "1.0.0"}
        )
        await manager.store_agent_state(agent_state)
        print("   ✓ Agent state stored")
        
        # Update agent state
        print("\n8. Updating agent state...")
        updated = await manager.update_agent_state(
            agent_id="agent-demo-001",
            status=AgentStatus.IDLE,
            current_task=None,
            metadata={"last_task": "task-123"}
        )
        print(f"   ✓ Update successful: {updated}")
        
        # Store task
        print("\n9. Storing task record...")
        task = TaskRecord(
            task_id="task-demo-001",
            task_type="code_generation",
            agent_id="agent-demo-001",
            input_data={"prompt": "Create a function"},
            result={"files": ["output.py"]},
            status=TaskStatus.COMPLETED,
            started_at=datetime.utcnow() - timedelta(minutes=5),
            completed_at=datetime.utcnow()
        )
        await manager.store_task(task)
        print("   ✓ Task stored")
        
        # Get task history
        print("\n10. Querying task history...")
        tasks = await manager.get_task_history(
            agent_id="agent-demo-001",
            limit=10
        )
        print(f"    ✓ Found {len(tasks)} task(s)")
        
        # Get agent performance
        print("\n11. Getting agent performance...")
        performance = await manager.get_agent_performance(
            agent_id="agent-demo-001",
            days=7
        )
        print(f"    ✓ Total tasks: {performance['total_tasks']}")
        print(f"    ✓ Success rate: {performance['success_rate']:.2%}")
        
        # Store consensus record
        print("\n12. Storing consensus record...")
        consensus = ConsensusRecord(
            task_id="task-demo-001",
            verifier_results={
                "syntax": {"score": 0.95},
                "logic": {"score": 0.88},
                "security": {"score": 0.92}
            },
            consensus_score=0.91,
            decision="PROCEED",
            created_at=datetime.utcnow()
        )
        await manager.store_consensus_record(consensus)
        print("   ✓ Consensus record stored")
        
        # Get consensus history
        print("\n13. Querying consensus history...")
        consensus_records = await manager.get_consensus_history(
            decision="PROCEED",
            limit=10
        )
        print(f"    ✓ Found {len(consensus_records)} record(s)")
        
        # Store evaluation
        print("\n14. Storing evaluation report...")
        evaluation = EvaluationReport(
            id="eval-demo-001",
            change_id="change-123",
            scores={
                "overall": 0.92,
                "syntax": 0.95,
                "logic": 0.88,
                "security": 0.92
            },
            findings=[
                {"severity": "low", "message": "Minor style issue"}
            ],
            recommendations=["Consider adding more comments"],
            timestamp=datetime.utcnow()
        )
        await manager.store_evaluation(evaluation)
        print("   ✓ Evaluation stored")
        
        # Get evaluation trends
        print("\n15. Getting evaluation trends...")
        trends = await manager.get_evaluation_trends(days=7)
        print(f"    ✓ Daily trends: {len(trends.get('daily_trends', []))} days")
        
        # Cleanup demo data
        print("\n16. Cleaning up demo data...")
        async with manager._get_connection() as conn:
            await conn.execute("DELETE FROM checkpoints WHERE id LIKE 'demo-%'")
            await conn.execute("DELETE FROM agent_states WHERE agent_id LIKE 'agent-demo-%'")
            await conn.execute("DELETE FROM task_history WHERE task_id LIKE 'task-demo-%'")
            await conn.execute("DELETE FROM consensus_records WHERE task_id LIKE 'task-demo-%'")
            await conn.execute("DELETE FROM evaluation_reports WHERE id LIKE 'eval-demo-%'")
        print("    ✓ Demo data cleaned up")
        
        # Disconnect
        print("\n17. Disconnecting...")
        await manager.disconnect()
        print("   ✓ Disconnected successfully")
        
        print("\n" + "=" * 60)
        print("Demo completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Demo failed: {e}")
        logger.exception("Demo error")
        raise


if __name__ == "__main__":
    # Run demo
    asyncio.run(demo())
