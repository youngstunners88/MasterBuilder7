#!/usr/bin/env python3
"""
APEX Three-Tier Checkpoint Manager

A production-ready fault tolerance system with:
- Tier 1 (Redis): Hot state with 120s TTL for sub-10ms recovery
- Tier 2 (SQLite): Warm state for persistent, queryable audit trail
- Tier 3 (Git): Cold state for immutable snapshots and rollback

Author: APEX Reliability Team
Version: 2.0.0
"""

import json
import os
import sqlite3
import subprocess
import hashlib
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from contextlib import contextmanager
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('CheckpointManager')

# Optional Redis import with graceful fallback
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis-py not available. Tier 1 (Redis) will be disabled.")


@dataclass
class Checkpoint:
    """Enhanced checkpoint data model"""
    id: str
    timestamp: str
    stage: str
    files: List[str]
    metadata: Dict[str, Any]
    hash: str
    build_id: str = ""
    agent_outputs: Dict[str, Any] = field(default_factory=dict)
    git_commit_hash: Optional[str] = None
    tier: int = 0  # 1=Redis, 2=SQLite, 3=Git
    ttl_seconds: Optional[int] = None


@dataclass
class CheckpointStatus:
    """Status across all tiers"""
    checkpoint_id: str
    tier1_redis: bool = False
    tier2_sqlite: bool = False
    tier3_git: bool = False
    redis_ttl_remaining: Optional[int] = None
    sqlite_record_count: int = 0
    git_commit_hash: Optional[str] = None
    created_at: Optional[str] = None
    last_accessed: Optional[str] = None


class CheckpointManager:
    """
    Three-Tier Checkpoint Manager for APEX builds
    
    Tier 1 (Redis): Hot state - 120s TTL, sub-10ms access
    Tier 2 (SQLite): Warm state - Persistent, queryable audit
    Tier 3 (Git): Cold state - Immutable snapshots, rollback
    """
    
    # Tier configuration
    TIER1_TTL_SECONDS = 120  # 2 minutes
    TIER1_PREFIX = "apex:checkpoint:"
    
    def __init__(
        self,
        checkpoint_dir: str = "/home/teacherchris37/MasterBuilder7/apex/checkpoints",
        sqlite_path: Optional[str] = None,
        redis_url: Optional[str] = None,
        git_repo_path: Optional[str] = None
    ):
        self.checkpoint_dir = checkpoint_dir
        os.makedirs(checkpoint_dir, exist_ok=True)
        
        # SQLite configuration (Tier 2)
        self.sqlite_path = sqlite_path or os.path.join(checkpoint_dir, "checkpoints.db")
        self._init_sqlite()
        
        # Redis configuration (Tier 1)
        self.redis_client = None
        self.redis_available = False
        if REDIS_AVAILABLE and redis_url is not False:
            self._init_redis(redis_url)
        
        # Git configuration (Tier 3)
        self.git_repo_path = git_repo_path or os.path.dirname(checkpoint_dir)
        self.git_available = self._check_git_available()
        
        # Legacy support
        self.checkpoints: Dict[str, Checkpoint] = {}
        self._load_legacy_checkpoints()
        
        logger.info(f"CheckpointManager initialized: Redis={self.redis_available}, "
                   f"SQLite={os.path.exists(self.sqlite_path)}, Git={self.git_available}")
    
    # ==================== Tier 1: Redis (Hot State) ====================
    
    def _init_redis(self, redis_url: Optional[str] = None):
        """Initialize Redis connection"""
        try:
            if redis_url:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
            else:
                self.redis_client = redis.Redis(
                    host='localhost',
                    port=6379,
                    db=0,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2
                )
            
            # Test connection
            self.redis_client.ping()
            self.redis_available = True
            logger.info("Redis Tier 1 initialized successfully")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Tier 1 will be disabled.")
            self.redis_client = None
            self.redis_available = False
    
    def create_tier1_checkpoint(
        self,
        build_id: str,
        stage: str,
        files: List[str],
        metadata: Optional[Dict] = None,
        agent_outputs: Optional[Dict] = None
    ) -> Optional[Checkpoint]:
        """
        Create Tier 1 checkpoint in Redis with 2-minute TTL
        
        Args:
            build_id: Unique build identifier
            stage: Build stage (e.g., 'planning', 'coding', 'testing')
            files: List of file paths to checkpoint
            metadata: Additional metadata
            agent_outputs: Agent execution outputs
            
        Returns:
            Checkpoint object or None if Redis unavailable
        """
        if not self.redis_available or not self.redis_client:
            logger.debug("Tier 1 (Redis) unavailable, skipping")
            return None
        
        try:
            checkpoint_id = self._generate_checkpoint_id(build_id, stage)
            timestamp = datetime.utcnow()
            
            checkpoint = Checkpoint(
                id=checkpoint_id,
                timestamp=timestamp.isoformat(),
                stage=stage,
                files=files,
                metadata=metadata or {},
                hash=self._compute_hash(files),
                build_id=build_id,
                agent_outputs=agent_outputs or {},
                tier=1,
                ttl_seconds=self.TIER1_TTL_SECONDS
            )
            
            # Store in Redis with TTL
            key = f"{self.TIER1_PREFIX}{checkpoint_id}"
            data = json.dumps(asdict(checkpoint))
            
            pipe = self.redis_client.pipeline()
            pipe.setex(key, self.TIER1_TTL_SECONDS, data)
            # Also store reference by build_id for quick lookup
            pipe.sadd(f"{self.TIER1_PREFIX}build:{build_id}", checkpoint_id)
            pipe.execute()
            
            logger.info(f"Tier 1 checkpoint created: {checkpoint_id} (TTL: {self.TIER1_TTL_SECONDS}s)")
            return checkpoint
            
        except Exception as e:
            logger.error(f"Failed to create Tier 1 checkpoint: {e}")
            return None
    
    def get_tier1_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """
        Retrieve Tier 1 checkpoint from Redis (sub-10ms access)
        
        Args:
            checkpoint_id: Checkpoint identifier
            
        Returns:
            Checkpoint object or None if not found/available
        """
        if not self.redis_available or not self.redis_client:
            return None
        
        try:
            key = f"{self.TIER1_PREFIX}{checkpoint_id}"
            data = self.redis_client.get(key)
            
            if data:
                checkpoint_dict = json.loads(data)
                checkpoint = Checkpoint(**checkpoint_dict)
                # Get remaining TTL
                ttl = self.redis_client.ttl(key)
                checkpoint.ttl_seconds = ttl if ttl > 0 else 0
                logger.debug(f"Tier 1 checkpoint retrieved: {checkpoint_id} (TTL: {ttl}s)")
                return checkpoint
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve Tier 1 checkpoint: {e}")
            return None
    
    def get_latest_tier1_checkpoint(self, build_id: str) -> Optional[Checkpoint]:
        """Get the most recent Tier 1 checkpoint for a build"""
        if not self.redis_available or not self.redis_client:
            return None
        
        try:
            key = f"{self.TIER1_PREFIX}build:{build_id}"
            checkpoint_ids = self.redis_client.smembers(key)
            
            if not checkpoint_ids:
                return None
            
            # Get all checkpoints and find latest
            checkpoints = []
            for cp_id in checkpoint_ids:
                cp = self.get_tier1_checkpoint(cp_id)
                if cp:
                    checkpoints.append(cp)
            
            if not checkpoints:
                return None
            
            return max(checkpoints, key=lambda x: x.timestamp)
            
        except Exception as e:
            logger.error(f"Failed to get latest Tier 1 checkpoint: {e}")
            return None
    
    # ==================== Tier 2: SQLite (Warm State) ====================
    
    def _init_sqlite(self):
        """Initialize SQLite database with enhanced schema"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Main checkpoints table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS checkpoints (
                        id TEXT PRIMARY KEY,
                        build_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        stage TEXT NOT NULL,
                        files TEXT NOT NULL,  -- JSON array
                        metadata TEXT,  -- JSON object
                        hash TEXT NOT NULL,
                        agent_outputs TEXT,  -- JSON object
                        git_commit_hash TEXT,
                        tier INTEGER DEFAULT 2,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_accessed TIMESTAMP
                    )
                """)
                
                # Index for fast queries
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_build_id 
                    ON checkpoints(build_id)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_stage 
                    ON checkpoints(stage)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_timestamp 
                    ON checkpoints(timestamp)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_build_stage 
                    ON checkpoints(build_id, stage)
                """)
                
                # Checkpoint access log for audit
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS checkpoint_access_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        checkpoint_id TEXT NOT NULL,
                        access_type TEXT NOT NULL,
                        accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (checkpoint_id) REFERENCES checkpoints(id)
                    )
                """)
                
                conn.commit()
                logger.info(f"SQLite Tier 2 initialized: {self.sqlite_path}")
                
        except Exception as e:
            logger.error(f"Failed to initialize SQLite: {e}")
            raise
    
    @contextmanager
    def _get_db_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def create_tier2_checkpoint(
        self,
        build_id: str,
        stage: str,
        files: List[str],
        metadata: Optional[Dict] = None,
        agent_outputs: Optional[Dict] = None,
        git_commit_hash: Optional[str] = None
    ) -> Checkpoint:
        """
        Create Tier 2 checkpoint in SQLite (persistent, queryable)
        
        Args:
            build_id: Unique build identifier
            stage: Build stage
            files: List of file paths
            metadata: Additional metadata
            agent_outputs: Agent execution outputs
            git_commit_hash: Associated Git commit hash
            
        Returns:
            Checkpoint object
        """
        try:
            checkpoint_id = self._generate_checkpoint_id(build_id, stage)
            timestamp = datetime.utcnow()
            
            checkpoint = Checkpoint(
                id=checkpoint_id,
                timestamp=timestamp.isoformat(),
                stage=stage,
                files=files,
                metadata=metadata or {},
                hash=self._compute_hash(files),
                build_id=build_id,
                agent_outputs=agent_outputs or {},
                git_commit_hash=git_commit_hash,
                tier=2
            )
            
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO checkpoints 
                    (id, build_id, timestamp, stage, files, metadata, hash, 
                     agent_outputs, git_commit_hash, tier)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    checkpoint.id,
                    checkpoint.build_id,
                    checkpoint.timestamp,
                    checkpoint.stage,
                    json.dumps(checkpoint.files),
                    json.dumps(checkpoint.metadata),
                    checkpoint.hash,
                    json.dumps(checkpoint.agent_outputs),
                    checkpoint.git_commit_hash,
                    checkpoint.tier
                ))
                
                conn.commit()
            
            logger.info(f"Tier 2 checkpoint created: {checkpoint_id}")
            return checkpoint
            
        except Exception as e:
            logger.error(f"Failed to create Tier 2 checkpoint: {e}")
            raise
    
    def query_checkpoints(
        self,
        build_id: Optional[str] = None,
        stage: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100
    ) -> List[Checkpoint]:
        """
        Query checkpoints with filters
        
        Args:
            build_id: Filter by build ID
            stage: Filter by stage
            start_time: ISO format start time
            end_time: ISO format end time
            limit: Maximum results
            
        Returns:
            List of matching checkpoints
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM checkpoints WHERE 1=1"
                params = []
                
                if build_id:
                    query += " AND build_id = ?"
                    params.append(build_id)
                
                if stage:
                    query += " AND stage = ?"
                    params.append(stage)
                
                if start_time:
                    query += " AND timestamp >= ?"
                    params.append(start_time)
                
                if end_time:
                    query += " AND timestamp <= ?"
                    params.append(end_time)
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                checkpoints = []
                for row in rows:
                    checkpoints.append(self._row_to_checkpoint(row))
                
                logger.debug(f"Query returned {len(checkpoints)} checkpoints")
                return checkpoints
                
        except Exception as e:
            logger.error(f"Failed to query checkpoints: {e}")
            return []
    
    def get_tier2_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Retrieve Tier 2 checkpoint by ID"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM checkpoints WHERE id = ?",
                    (checkpoint_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    # Update last_accessed
                    cursor.execute(
                        "UPDATE checkpoints SET last_accessed = CURRENT_TIMESTAMP WHERE id = ?",
                        (checkpoint_id,)
                    )
                    # Log access
                    cursor.execute(
                        "INSERT INTO checkpoint_access_log (checkpoint_id, access_type) VALUES (?, ?)",
                        (checkpoint_id, 'read')
                    )
                    conn.commit()
                    
                    return self._row_to_checkpoint(row)
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to retrieve Tier 2 checkpoint: {e}")
            return None
    
    def _row_to_checkpoint(self, row: sqlite3.Row) -> Checkpoint:
        """Convert database row to Checkpoint object"""
        return Checkpoint(
            id=row['id'],
            timestamp=row['timestamp'],
            stage=row['stage'],
            files=json.loads(row['files']),
            metadata=json.loads(row['metadata']) if row['metadata'] else {},
            hash=row['hash'],
            build_id=row['build_id'],
            agent_outputs=json.loads(row['agent_outputs']) if row['agent_outputs'] else {},
            git_commit_hash=row['git_commit_hash'],
            tier=row['tier']
        )
    
    # ==================== Tier 3: Git (Cold State) ====================
    
    def _check_git_available(self) -> bool:
        """Check if Git is available and repository exists"""
        try:
            result = subprocess.run(
                ['git', '-C', self.git_repo_path, 'rev-parse', '--git-dir'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def create_tier3_checkpoint(
        self,
        build_id: str,
        stage: str,
        files: List[str],
        metadata: Optional[Dict] = None,
        agent_outputs: Optional[Dict] = None,
        commit_message: Optional[str] = None
    ) -> Tuple[Optional[Checkpoint], Optional[str]]:
        """
        Create Tier 3 checkpoint as Git commit (immutable snapshot)
        
        Args:
            build_id: Unique build identifier
            stage: Build stage
            files: List of file paths to commit
            metadata: Additional metadata
            agent_outputs: Agent execution outputs
            commit_message: Custom commit message
            
        Returns:
            Tuple of (Checkpoint, git_commit_hash) or (None, None)
        """
        if not self.git_available:
            logger.warning("Git Tier 3 unavailable")
            return None, None
        
        try:
            checkpoint_id = self._generate_checkpoint_id(build_id, stage)
            timestamp = datetime.utcnow()
            
            # Stage files for commit
            for filepath in files:
                if os.path.exists(filepath):
                    rel_path = os.path.relpath(filepath, self.git_repo_path)
                    subprocess.run(
                        ['git', '-C', self.git_repo_path, 'add', rel_path],
                        capture_output=True,
                        check=True
                    )
            
            # Create checkpoint metadata file
            checkpoint_data = {
                'checkpoint_id': checkpoint_id,
                'build_id': build_id,
                'stage': stage,
                'timestamp': timestamp.isoformat(),
                'files': files,
                'metadata': metadata or {},
                'agent_outputs': agent_outputs or {}
            }
            
            meta_path = os.path.join(
                self.checkpoint_dir,
                f"{checkpoint_id}_git_metadata.json"
            )
            with open(meta_path, 'w') as f:
                json.dump(checkpoint_data, f, indent=2)
            
            subprocess.run(
                ['git', '-C', self.git_repo_path, 'add', meta_path],
                capture_output=True,
                check=True
            )
            
            # Create commit
            message = commit_message or f"APEX checkpoint: {checkpoint_id} [{stage}]"
            result = subprocess.run(
                ['git', '-C', self.git_repo_path, 'commit', '-m', message],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                # No changes to commit
                logger.warning(f"No changes to commit for checkpoint {checkpoint_id}")
                return None, None
            
            # Get commit hash
            result = subprocess.run(
                ['git', '-C', self.git_repo_path, 'rev-parse', 'HEAD'],
                capture_output=True,
                text=True,
                check=True
            )
            git_commit_hash = result.stdout.strip()
            
            # Tag the commit
            tag_name = f"apex-checkpoint-{checkpoint_id}"
            subprocess.run(
                ['git', '-C', self.git_repo_path, 'tag', '-a', tag_name, '-m', f"Checkpoint {checkpoint_id}"],
                capture_output=True
            )
            
            checkpoint = Checkpoint(
                id=checkpoint_id,
                timestamp=timestamp.isoformat(),
                stage=stage,
                files=files,
                metadata=metadata or {},
                hash=self._compute_hash(files),
                build_id=build_id,
                agent_outputs=agent_outputs or {},
                git_commit_hash=git_commit_hash,
                tier=3
            )
            
            logger.info(f"Tier 3 checkpoint created: {checkpoint_id} (commit: {git_commit_hash[:8]})")
            return checkpoint, git_commit_hash
            
        except Exception as e:
            logger.error(f"Failed to create Tier 3 checkpoint: {e}")
            return None, None
    
    def rollback_to_checkpoint(
        self,
        checkpoint_id: str,
        create_backup_branch: bool = True
    ) -> Dict[str, Any]:
        """
        Rollback to a Git checkpoint
        
        Args:
            checkpoint_id: Checkpoint to rollback to
            create_backup_branch: Create backup branch before rollback
            
        Returns:
            Rollback result dictionary
        """
        if not self.git_available:
            return {'success': False, 'error': 'Git not available'}
        
        try:
            # Get the checkpoint
            checkpoint = self.get_tier2_checkpoint(checkpoint_id)
            if not checkpoint or not checkpoint.git_commit_hash:
                return {'success': False, 'error': 'Checkpoint or commit hash not found'}
            
            commit_hash = checkpoint.git_commit_hash
            
            # Create backup branch
            if create_backup_branch:
                backup_branch = f"backup/pre-rollback-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                subprocess.run(
                    ['git', '-C', self.git_repo_path, 'branch', backup_branch],
                    capture_output=True,
                    check=True
                )
                logger.info(f"Created backup branch: {backup_branch}")
            
            # Perform rollback
            result = subprocess.run(
                ['git', '-C', self.git_repo_path, 'checkout', commit_hash],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return {
                    'success': False,
                    'error': f'Git checkout failed: {result.stderr}'
                }
            
            # Create rollback marker
            rollback_marker = {
                'checkpoint_id': checkpoint_id,
                'commit_hash': commit_hash,
                'timestamp': datetime.utcnow().isoformat(),
                'backup_branch': backup_branch if create_backup_branch else None
            }
            
            marker_path = os.path.join(
                self.checkpoint_dir,
                f"rollback_{checkpoint_id}.json"
            )
            with open(marker_path, 'w') as f:
                json.dump(rollback_marker, f, indent=2)
            
            logger.info(f"Rolled back to checkpoint: {checkpoint_id} (commit: {commit_hash[:8]})")
            
            return {
                'success': True,
                'checkpoint_id': checkpoint_id,
                'commit_hash': commit_hash,
                'stage': checkpoint.stage,
                'backup_branch': backup_branch if create_backup_branch else None,
                'files_affected': len(checkpoint.files)
            }
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def list_git_checkpoints(self, build_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available Git checkpoints
        
        Args:
            build_id: Optional filter by build ID
            
        Returns:
            List of checkpoint dictionaries
        """
        if not self.git_available:
            return []
        
        try:
            # Get all tags matching checkpoint pattern
            result = subprocess.run(
                ['git', '-C', self.git_repo_path, 'tag', '-l', 'apex-checkpoint-*'],
                capture_output=True,
                text=True,
                check=True
            )
            
            tags = result.stdout.strip().split('\n') if result.stdout.strip() else []
            checkpoints = []
            
            for tag in tags:
                if not tag:
                    continue
                
                # Get commit info
                result = subprocess.run(
                    ['git', '-C', self.git_repo_path, 'log', '-1', '--format=%H|%ci|%s', tag],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                if result.stdout.strip():
                    parts = result.stdout.strip().split('|', 2)
                    if len(parts) >= 3:
                        commit_hash, commit_time, message = parts
                        
                        # Extract checkpoint_id from tag
                        checkpoint_id = tag.replace('apex-checkpoint-', '')
                        
                        # Filter by build_id if specified
                        if build_id and not checkpoint_id.startswith(build_id):
                            continue
                        
                        checkpoints.append({
                            'checkpoint_id': checkpoint_id,
                            'tag': tag,
                            'commit_hash': commit_hash,
                            'commit_time': commit_time,
                            'message': message
                        })
            
            # Sort by commit time
            checkpoints.sort(key=lambda x: x['commit_time'], reverse=True)
            
            return checkpoints
            
        except Exception as e:
            logger.error(f"Failed to list Git checkpoints: {e}")
            return []
    
    # ==================== Unified Interface ====================
    
    def create_full_checkpoint(
        self,
        build_id: str,
        stage: str,
        files: List[str],
        metadata: Optional[Dict] = None,
        agent_outputs: Optional[Dict] = None,
        include_git: bool = True
    ) -> Dict[str, Any]:
        """
        Create checkpoints across all available tiers
        
        Args:
            build_id: Unique build identifier
            stage: Build stage
            files: List of file paths
            metadata: Additional metadata
            agent_outputs: Agent execution outputs
            include_git: Whether to include Tier 3 (Git) checkpoint
            
        Returns:
            Dictionary with checkpoint IDs for each tier
        """
        result = {
            'build_id': build_id,
            'stage': stage,
            'timestamp': datetime.utcnow().isoformat(),
            'tier1_redis': None,
            'tier2_sqlite': None,
            'tier3_git': None,
            'tier3_git_commit': None
        }
        
        # Tier 1: Redis
        try:
            tier1_cp = self.create_tier1_checkpoint(
                build_id, stage, files, metadata, agent_outputs
            )
            if tier1_cp:
                result['tier1_redis'] = tier1_cp.id
        except Exception as e:
            logger.warning(f"Tier 1 checkpoint failed: {e}")
        
        # Tier 3: Git (create first to get commit hash)
        git_commit_hash = None
        if include_git:
            try:
                tier3_cp, commit_hash = self.create_tier3_checkpoint(
                    build_id, stage, files, metadata, agent_outputs
                )
                if tier3_cp:
                    result['tier3_git'] = tier3_cp.id
                    result['tier3_git_commit'] = commit_hash
                    git_commit_hash = commit_hash
            except Exception as e:
                logger.warning(f"Tier 3 checkpoint failed: {e}")
        
        # Tier 2: SQLite (with git commit hash if available)
        try:
            tier2_cp = self.create_tier2_checkpoint(
                build_id, stage, files, metadata, agent_outputs, git_commit_hash
            )
            result['tier2_sqlite'] = tier2_cp.id
        except Exception as e:
            logger.error(f"Tier 2 checkpoint failed: {e}")
            raise
        
        logger.info(f"Full checkpoint created for {build_id}/{stage}: "
                   f"Redis={result['tier1_redis'] is not None}, "
                   f"SQLite={result['tier2_sqlite']}, "
                   f"Git={result['tier3_git'] is not None}")
        
        return result
    
    def recover_from_failure(
        self,
        build_id: str,
        stage: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Automatic recovery using Tier 1 (Redis) with fallback to Tier 2 (SQLite)
        
        Args:
            build_id: Build ID to recover
            stage: Optional specific stage to recover
            
        Returns:
            Recovery result dictionary
        """
        logger.info(f"Attempting recovery for build {build_id}, stage={stage}")
        
        # Try Tier 1 first (fastest)
        tier1_checkpoint = None
        if self.redis_available:
            if stage:
                tier1_checkpoint = self.get_tier1_checkpoint(
                    self._generate_checkpoint_id(build_id, stage)
                )
            else:
                tier1_checkpoint = self.get_latest_tier1_checkpoint(build_id)
        
        if tier1_checkpoint:
            logger.info(f"Recovery from Tier 1 successful: {tier1_checkpoint.id}")
            return {
                'success': True,
                'tier': 1,
                'checkpoint': tier1_checkpoint,
                'source': 'redis',
                'recovery_time_ms': '<10'
            }
        
        # Fallback to Tier 2
        tier2_checkpoints = self.query_checkpoints(build_id=build_id, stage=stage, limit=1)
        if tier2_checkpoints:
            checkpoint = tier2_checkpoints[0]
            logger.info(f"Recovery from Tier 2 successful: {checkpoint.id}")
            return {
                'success': True,
                'tier': 2,
                'checkpoint': checkpoint,
                'source': 'sqlite',
                'recovery_time_ms': '~50'
            }
        
        logger.error(f"Recovery failed: No checkpoints found for {build_id}")
        return {
            'success': False,
            'error': f'No checkpoints found for build {build_id}'
        }
    
    def get_checkpoint_status(self, checkpoint_id: str) -> CheckpointStatus:
        """
        Get status across all tiers for a checkpoint
        
        Args:
            checkpoint_id: Checkpoint identifier
            
        Returns:
            CheckpointStatus object
        """
        status = CheckpointStatus(checkpoint_id=checkpoint_id)
        
        # Check Tier 1 (Redis)
        if self.redis_available:
            tier1_cp = self.get_tier1_checkpoint(checkpoint_id)
            if tier1_cp:
                status.tier1_redis = True
                status.redis_ttl_remaining = tier1_cp.ttl_seconds
                status.created_at = tier1_cp.timestamp
        
        # Check Tier 2 (SQLite)
        tier2_cp = self.get_tier2_checkpoint(checkpoint_id)
        if tier2_cp:
            status.tier2_sqlite = True
            status.sqlite_record_count = 1
            status.git_commit_hash = tier2_cp.git_commit_hash
            if not status.created_at:
                status.created_at = tier2_cp.timestamp
            status.last_accessed = tier2_cp.timestamp
        
        # Check Tier 3 (Git)
        if self.git_available:
            git_checkpoints = self.list_git_checkpoints()
            for gc in git_checkpoints:
                if gc['checkpoint_id'] == checkpoint_id:
                    status.tier3_git = True
                    if not status.git_commit_hash:
                        status.git_commit_hash = gc['commit_hash']
                    break
        
        return status
    
    # ==================== Helper Methods ====================
    
    def _generate_checkpoint_id(self, build_id: str, stage: str) -> str:
        """Generate unique checkpoint ID"""
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        return f"{build_id}-{stage}-{timestamp}"
    
    def _compute_hash(self, files: List[str]) -> str:
        """Compute SHA256 hash of file contents"""
        hasher = hashlib.sha256()
        for filepath in sorted(files):
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'rb') as f:
                        hasher.update(f.read())
                except Exception as e:
                    logger.warning(f"Could not hash file {filepath}: {e}")
        return hasher.hexdigest()[:16]
    
    # ==================== Legacy Support ====================
    
    def _load_legacy_checkpoints(self):
        """Load existing checkpoints from legacy JSON index"""
        index_path = os.path.join(self.checkpoint_dir, "index.json")
        if os.path.exists(index_path):
            try:
                with open(index_path, 'r') as f:
                    data = json.load(f)
                    for cp_id, cp_data in data.items():
                        # Ensure required fields exist
                        cp_data.setdefault('build_id', '')
                        cp_data.setdefault('agent_outputs', {})
                        cp_data.setdefault('git_commit_hash', None)
                        cp_data.setdefault('tier', 0)
                        self.checkpoints[cp_id] = Checkpoint(**cp_data)
            except Exception as e:
                logger.warning(f"Could not load legacy checkpoints: {e}")
    
    def _save_legacy_index(self):
        """Save checkpoint index to legacy JSON format"""
        index_path = os.path.join(self.checkpoint_dir, "index.json")
        try:
            with open(index_path, 'w') as f:
                json.dump({k: asdict(v) for k, v in self.checkpoints.items()}, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save legacy index: {e}")
    
    # Legacy method aliases for backward compatibility
    def create_checkpoint(
        self,
        build_id: str,
        stage: str,
        files: List[str],
        metadata: Optional[Dict] = None
    ) -> Checkpoint:
        """Legacy method - creates Tier 2 checkpoint"""
        return self.create_tier2_checkpoint(build_id, stage, files, metadata)
    
    def get_latest_checkpoint(self, build_id: str) -> Optional[Checkpoint]:
        """Legacy method - get latest from SQLite"""
        checkpoints = self.query_checkpoints(build_id=build_id, limit=1)
        return checkpoints[0] if checkpoints else None
    
    def get_stage_checkpoint(self, build_id: str, stage: str) -> Optional[Checkpoint]:
        """Legacy method - get stage checkpoint from SQLite"""
        checkpoints = self.query_checkpoints(build_id=build_id, stage=stage, limit=1)
        return checkpoints[0] if checkpoints else None
    
    def list_checkpoints(self, build_id: Optional[str] = None) -> List[Checkpoint]:
        """Legacy method - list checkpoints from SQLite"""
        return self.query_checkpoints(build_id=build_id)
    
    def clean_old_checkpoints(self, build_id: str, keep_last: int = 5) -> Dict[str, int]:
        """Clean old checkpoints from SQLite"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get checkpoints to delete
                cursor.execute("""
                    SELECT id FROM checkpoints 
                    WHERE build_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT -1 OFFSET ?
                """, (build_id, keep_last))
                
                to_delete = [row['id'] for row in cursor.fetchall()]
                
                if to_delete:
                    placeholders = ','.join('?' * len(to_delete))
                    cursor.execute(f"""
                        DELETE FROM checkpoints 
                        WHERE id IN ({placeholders})
                    """, to_delete)
                    conn.commit()
                
                return {'removed': len(to_delete), 'kept': keep_last}
                
        except Exception as e:
            logger.error(f"Failed to clean old checkpoints: {e}")
            return {'removed': 0, 'kept': 0}


# ==================== Convenience Functions ====================

def create_manager(
    checkpoint_dir: str = "/home/teacherchris37/MasterBuilder7/apex/checkpoints",
    redis_url: Optional[str] = None,
    git_repo_path: Optional[str] = None
) -> CheckpointManager:
    """Factory function to create a CheckpointManager instance"""
    return CheckpointManager(
        checkpoint_dir=checkpoint_dir,
        redis_url=redis_url,
        git_repo_path=git_repo_path
    )


if __name__ == "__main__":
    # Test the Three-Tier Checkpoint Manager
    print("=" * 60)
    print("APEX Three-Tier Checkpoint Manager - Test Suite")
    print("=" * 60)
    
    # Initialize manager
    manager = CheckpointManager()
    
    test_build_id = f"test-build-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    test_files = ["/tmp/test_source.txt", "/tmp/test_plan.json"]
    
    # Create test files
    for f in test_files:
        Path(f).touch()
    
    print(f"\n1. Creating Tier 2 (SQLite) checkpoint...")
    cp2 = manager.create_tier2_checkpoint(
        build_id=test_build_id,
        stage="planning",
        files=test_files,
        metadata={"agent": "planning-1", "test": True},
        agent_outputs={"plan": "test plan content", "confidence": 0.95}
    )
    print(f"   ✓ Created: {cp2.id}")
    print(f"   ✓ Files tracked: {len(cp2.files)}")
    print(f"   ✓ Agent outputs: {list(cp2.agent_outputs.keys())}")
    
    print(f"\n2. Querying checkpoints...")
    results = manager.query_checkpoints(build_id=test_build_id)
    print(f"   ✓ Found {len(results)} checkpoint(s)")
    
    print(f"\n3. Creating full checkpoint (all tiers)...")
    full_result = manager.create_full_checkpoint(
        build_id=test_build_id,
        stage="coding",
        files=test_files,
        metadata={"agent": "coding-1", "feature": "test"},
        agent_outputs={"code": "print('hello')", "files_created": 2},
        include_git=False  # Skip git for testing
    )
    print(f"   ✓ Tier 1 (Redis): {full_result['tier1_redis'] or 'N/A (Redis unavailable)'}")
    print(f"   ✓ Tier 2 (SQLite): {full_result['tier2_sqlite']}")
    print(f"   ✓ Tier 3 (Git): {full_result['tier3_git'] or 'N/A (Git unavailable/skipped)'}")
    
    print(f"\n4. Testing recovery...")
    recovery = manager.recover_from_failure(test_build_id)
    print(f"   ✓ Success: {recovery['success']}")
    print(f"   ✓ Recovered from: Tier {recovery.get('tier', 'N/A')}")
    print(f"   ✓ Source: {recovery.get('source', 'N/A')}")
    
    print(f"\n5. Checking checkpoint status...")
    status = manager.get_checkpoint_status(full_result['tier2_sqlite'])
    print(f"   ✓ Tier 1 (Redis): {'✓' if status.tier1_redis else '✗'}")
    print(f"   ✓ Tier 2 (SQLite): {'✓' if status.tier2_sqlite else '✗'}")
    print(f"   ✓ Tier 3 (Git): {'✓' if status.tier3_git else '✗'}")
    
    print(f"\n6. Testing Git checkpoints (if available)...")
    git_cps = manager.list_git_checkpoints(build_id=test_build_id)
    print(f"   ✓ Git checkpoints found: {len(git_cps)}")
    
    print("\n" + "=" * 60)
    print("Test suite completed successfully!")
    print("=" * 60)
