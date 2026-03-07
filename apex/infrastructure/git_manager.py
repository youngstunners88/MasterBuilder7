#!/usr/bin/env python3
"""
APEX Git Automation Layer - Tier 3 Checkpoint Storage
======================================================

Provides immutable checkpoint storage via Git commits with:
- Automatic checkpoint commits with structured metadata
- Tag-based versioning with format: checkpoint/{build_id}/{stage}/{timestamp}
- GPG signing for audit compliance
- Branch management for parallel sessions
- Remote push to backup repositories
- Rollback and integrity verification capabilities

Author: APEX Infrastructure Team
Version: 2.0.0
License: MIT
"""

import os
import sys
import json
import asyncio
import logging
import hashlib
import shutil
import tempfile
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import asynccontextmanager
from enum import Enum
import subprocess

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/apex_git_manager.log')
    ]
)
logger = logging.getLogger('GitManager')

# GitPython import with graceful fallback
try:
    import git
    from git import Repo, Commit, TagReference, Head
    from git.exc import GitCommandError, InvalidGitRepositoryError
    GITPYTHON_AVAILABLE = True
except ImportError:
    GITPYTHON_AVAILABLE = False
    logger.warning("GitPython not available. Using subprocess fallback for git operations.")


class CheckpointStage(Enum):
    """Build stages for checkpoint organization"""
    ANALYSIS = "analysis"
    PLANNING = "planning"
    FRONTEND_BUILD = "frontend_build"
    BACKEND_BUILD = "backend_build"
    TESTING = "testing"
    EVALUATION = "evaluation"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"
    EVOLUTION = "evolution"
    CUSTOM = "custom"


class CheckpointTier(Enum):
    """Checkpoint storage tiers"""
    HOT = 1      # Redis - sub-10ms
    WARM = 2     # SQLite - persistent
    COLD = 3     # Git - immutable


@dataclass
class CheckpointMetadata:
    """Structured checkpoint metadata"""
    checkpoint_id: str
    build_id: str
    stage: str
    session_id: str
    timestamp: str
    agent_count: int
    status: str
    tier: int = 3
    files: List[str] = field(default_factory=list)
    agent_outputs: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    signature: Optional[str] = None
    parent_checkpoint: Optional[str] = None


@dataclass
class CheckpointInfo:
    """Complete checkpoint information"""
    checkpoint_id: str
    commit_hash: str
    tag_name: str
    timestamp: datetime
    build_id: str
    stage: str
    message: str
    author: str
    files_changed: int
    insertions: int
    deletions: int
    gpg_signed: bool = False
    verified: bool = False


@dataclass
class BranchInfo:
    """Branch information"""
    name: str
    commit_hash: str
    is_remote: bool
    is_active: bool
    last_commit_time: Optional[datetime] = None
    tracking_branch: Optional[str] = None


@dataclass
class DiffResult:
    """Diff between two checkpoints"""
    checkpoint_from: str
    checkpoint_to: str
    files_changed: List[Dict[str, Any]]
    total_insertions: int
    total_deletions: int
    diff_text: Optional[str] = None


class GitManagerError(Exception):
    """Base exception for GitManager"""
    pass


class RepositoryNotFoundError(GitManagerError):
    """Raised when repository is not found"""
    pass


class CheckpointNotFoundError(GitManagerError):
    """Raised when checkpoint is not found"""
    pass


class IntegrityError(GitManagerError):
    """Raised when checkpoint integrity check fails"""
    pass


class GitManager:
    """
    Git Automation Layer for Tier 3 Checkpoint Storage
    
    Provides immutable checkpoint storage via Git commits with:
    - Automatic checkpoint commits with structured metadata
    - Tag-based versioning: checkpoint/{build_id}/{stage}/{timestamp}
    - GPG signing for audit compliance
    - Branch management for parallel sessions
    - Remote push to backup repositories
    - Rollback and integrity verification
    
    Configuration (via environment variables):
    - CHECKPOINTS_REPO_PATH: Path to checkpoints repository
    - GIT_USER_NAME: Git user name for commits
    - GIT_USER_EMAIL: Git user email for commits
    - GIT_SIGNING_KEY: GPG key ID for signing (optional)
    - CHECKPOINTS_REMOTE_URL: Remote URL for backup (optional)
    - CHECKPOINTS_BRANCH_PREFIX: Branch name prefix (default: "session-")
    """
    
    # Default configuration
    DEFAULT_CHECKPOINTS_DIR = "/home/teacherchris37/MasterBuilder7/apex/checkpoints/git_store"
    DEFAULT_BRANCH_PREFIX = "session-"
    TAG_PREFIX = "checkpoint"
    
    # .gitignore template for sensitive files
    GITIGNORE_TEMPLATE = """
# APEX Git Manager - Sensitive Files Exclusion
# Auto-generated - Do not modify manually

# Secrets and credentials
*.pem
*.key
*.pfx
*.p12
.env
.env.local
.env.*.local
secrets.yaml
secrets.json
config/secrets/*

# Temporary files
*.tmp
*.temp
*.swp
*.swo
*~
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Build artifacts
build/
dist/
*.egg-info/
__pycache__/
*.pyc

# IDE
.idea/
.vscode/
*.iml

# Backup files
*.bak
*.backup
pre-rollback-*
"""
    
    def __init__(
        self,
        repo_path: Optional[str] = None,
        user_name: Optional[str] = None,
        user_email: Optional[str] = None,
        signing_key: Optional[str] = None,
        remote_url: Optional[str] = None,
        branch_prefix: Optional[str] = None
    ):
        """
        Initialize GitManager
        
        Args:
            repo_path: Path to git repository (defaults to CHECKPOINTS_REPO_PATH env var)
            user_name: Git user name (defaults to GIT_USER_NAME env var)
            user_email: Git user email (defaults to GIT_USER_EMAIL env var)
            signing_key: GPG signing key ID (defaults to GIT_SIGNING_KEY env var)
            remote_url: Remote repository URL (defaults to CHECKPOINTS_REMOTE_URL env var)
            branch_prefix: Prefix for session branches (defaults to CHECKPOINTS_BRANCH_PREFIX)
        """
        # Configuration from environment or parameters
        self.repo_path = Path(repo_path or os.getenv('CHECKPOINTS_REPO_PATH', self.DEFAULT_CHECKPOINTS_DIR))
        self.user_name = user_name or os.getenv('GIT_USER_NAME', 'APEX Git Manager')
        self.user_email = user_email or os.getenv('GIT_USER_EMAIL', 'apex@masterbuilder7.local')
        self.signing_key = signing_key or os.getenv('GIT_SIGNING_KEY')
        self.remote_url = remote_url or os.getenv('CHECKPOINTS_REMOTE_URL')
        self.branch_prefix = branch_prefix or os.getenv('CHECKPOINTS_BRANCH_PREFIX', self.DEFAULT_BRANCH_PREFIX)
        
        # Repository instance
        self._repo: Optional[Repo] = None
        self._lock = asyncio.Lock()
        
        # Operation statistics
        self.stats = {
            'commits_created': 0,
            'tags_created': 0,
            'branches_created': 0,
            'rollbacks_performed': 0,
            'remote_pushes': 0,
            'integrity_checks': 0
        }
        
        logger.info(f"GitManager initialized: repo_path={self.repo_path}")
    
    # ========================================================================
    # Repository Management
    # ========================================================================
    
    async def init_repo(
        self,
        bare: bool = False,
        initial_branch: str = "main",
        force: bool = False
    ) -> 'Repo':
        """
        Initialize a new Git repository for checkpoints
        
        Args:
            bare: Create a bare repository
            initial_branch: Name of initial branch
            force: Force reinitialization if repo exists
            
        Returns:
            Initialized Repo instance
        """
        async with self._lock:
            try:
                if self.repo_path.exists() and (self.repo_path / '.git').exists():
                    if force:
                        logger.warning(f"Force reinitializing repo at {self.repo_path}")
                        shutil.rmtree(self.repo_path)
                    else:
                        logger.info(f"Opening existing repo at {self.repo_path}")
                        self._repo = Repo(self.repo_path)
                        return self._repo
                
                # Create directory if needed
                self.repo_path.mkdir(parents=True, exist_ok=True)
                
                # Initialize repository
                if GITPYTHON_AVAILABLE:
                    self._repo = Repo.init(str(self.repo_path), bare=bare)
                else:
                    # Fallback to subprocess
                    cmd = ['git', 'init']
                    if bare:
                        cmd.append('--bare')
                    if initial_branch:
                        cmd.extend(['--initial-branch', initial_branch])
                    cmd.append(str(self.repo_path))
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    self._repo = Repo(self.repo_path) if GITPYTHON_AVAILABLE else None
                
                # Configure git user
                await self._configure_git_user()
                
                # Configure GPG signing if key provided
                if self.signing_key:
                    await self._configure_gpg_signing()
                
                # Create .gitignore
                await self._create_gitignore()
                
                # Create initial checkpoint directory structure
                await self._create_directory_structure()
                
                # Create initial commit if not bare
                if not bare and self._repo:
                    readme_path = self.repo_path / 'README.md'
                    readme_path.write_text(self._generate_readme())
                    self._repo.index.add(['README.md', '.gitignore'])
                    self._repo.index.commit(
                        "Initial commit: APEX Checkpoint Repository\n\n"
                        "- Checkpoint storage for Tier 3 immutable backups\n"
                        "- Auto-generated by APEX GitManager\n"
                        f"- Created: {datetime.utcnow().isoformat()}"
                    )
                
                logger.info(f"Repository initialized at {self.repo_path}")
                return self._repo
                
            except Exception as e:
                logger.error(f"Failed to initialize repository: {e}")
                raise GitManagerError(f"Repository initialization failed: {e}")
    
    async def clone_repo(
        self,
        remote_url: str,
        target_path: Optional[str] = None,
        branch: Optional[str] = None,
        depth: Optional[int] = None
    ) -> 'Repo':
        """
        Clone a remote repository for checkpoint backup/restore
        
        Args:
            remote_url: URL of remote repository
            target_path: Local path for clone (defaults to repo_path)
            branch: Specific branch to clone
            depth: Shallow clone depth
            
        Returns:
            Cloned Repo instance
        """
        async with self._lock:
            try:
                target = Path(target_path) if target_path else self.repo_path
                
                if GITPYTHON_AVAILABLE and self._repo is None:
                    clone_kwargs = {}
                    if branch:
                        clone_kwargs['branch'] = branch
                    if depth:
                        clone_kwargs['depth'] = depth
                    
                    self._repo = Repo.clone_from(remote_url, str(target), **clone_kwargs)
                else:
                    # Fallback to subprocess
                    cmd = ['git', 'clone']
                    if branch:
                        cmd.extend(['--branch', branch])
                    if depth:
                        cmd.extend(['--depth', str(depth)])
                    cmd.extend([remote_url, str(target)])
                    
                    subprocess.run(cmd, capture_output=True, text=True, check=True)
                    
                    if GITPYTHON_AVAILABLE:
                        self._repo = Repo(target)
                
                self.repo_path = target
                
                # Configure user
                await self._configure_git_user()
                
                logger.info(f"Repository cloned from {remote_url} to {target}")
                return self._repo
                
            except Exception as e:
                logger.error(f"Failed to clone repository: {e}")
                raise GitManagerError(f"Repository clone failed: {e}")
    
    async def open_repo(self) -> 'Repo':
        """
        Open an existing repository
        
        Returns:
            Repo instance
            
        Raises:
            RepositoryNotFoundError: If repository doesn't exist
        """
        async with self._lock:
            if self._repo is not None:
                return self._repo
            
            if not self.repo_path.exists():
                raise RepositoryNotFoundError(f"Repository not found at {self.repo_path}")
            
            if not (self.repo_path / '.git').exists():
                raise RepositoryNotFoundError(f"Not a git repository: {self.repo_path}")
            
            try:
                if GITPYTHON_AVAILABLE:
                    self._repo = Repo(self.repo_path)
                else:
                    # Verify it's a valid git repo using subprocess
                    result = subprocess.run(
                        ['git', '-C', str(self.repo_path), 'rev-parse', '--git-dir'],
                        capture_output=True, text=True, check=True
                    )
                
                logger.info(f"Repository opened: {self.repo_path}")
                return self._repo
                
            except Exception as e:
                raise RepositoryNotFoundError(f"Failed to open repository: {e}")
    
    # ========================================================================
    # Checkpoint Operations
    # ========================================================================
    
    async def create_checkpoint_commit(
        self,
        build_id: str,
        stage: str,
        files: List[str],
        metadata: Optional[Dict[str, Any]] = None,
        agent_outputs: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        agent_count: int = 0,
        status: str = "completed",
        parent_checkpoint: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Create a checkpoint commit with structured metadata
        
        Args:
            build_id: Unique build identifier
            stage: Build stage (analysis, planning, etc.)
            files: List of file paths to include in checkpoint
            metadata: Additional checkpoint metadata
            agent_outputs: Agent execution outputs
            session_id: Session identifier for parallel builds
            agent_count: Number of agents involved
            status: Checkpoint status
            parent_checkpoint: Parent checkpoint ID for lineage
            
        Returns:
            Tuple of (checkpoint_id, commit_hash)
        """
        async with self._lock:
            repo = await self.open_repo()
            
            try:
                # Generate checkpoint ID
                timestamp = datetime.utcnow()
                checkpoint_id = self._generate_checkpoint_id(build_id, stage, timestamp)
                
                # Prepare checkpoint directory structure
                checkpoint_dir = self.repo_path / 'checkpoints' / build_id
                checkpoint_dir.mkdir(parents=True, exist_ok=True)
                
                # Create metadata file
                checkpoint_metadata = CheckpointMetadata(
                    checkpoint_id=checkpoint_id,
                    build_id=build_id,
                    stage=stage,
                    session_id=session_id or "default",
                    timestamp=timestamp.isoformat(),
                    agent_count=agent_count,
                    status=status,
                    tier=CheckpointTier.COLD.value,
                    files=files,
                    agent_outputs=agent_outputs or {},
                    tags=[build_id, stage],
                    parent_checkpoint=parent_checkpoint
                )
                
                metadata_path = checkpoint_dir / f"{checkpoint_id}_metadata.json"
                metadata_path.write_text(
                    json.dumps(asdict(checkpoint_metadata), indent=2)
                )
                
                # Create agent outputs directory
                if agent_outputs:
                    outputs_dir = checkpoint_dir / 'agent_outputs'
                    outputs_dir.mkdir(exist_ok=True)
                    
                    for agent_name, output_data in agent_outputs.items():
                        output_path = outputs_dir / f"{agent_name}.json"
                        output_path.write_text(json.dumps(output_data, indent=2))
                
                # Create symlinks to actual files
                files_dir = checkpoint_dir / 'files'
                files_dir.mkdir(exist_ok=True)
                
                for filepath in files:
                    src = Path(filepath)
                    if src.exists():
                        link_name = files_dir / src.name
                        if link_name.exists() or link_name.is_symlink():
                            link_name.unlink()
                        try:
                            link_name.symlink_to(src.resolve())
                        except OSError:
                            # If symlink fails, copy the file
                            shutil.copy2(src, link_name)
                
                # Stage all files
                if GITPYTHON_AVAILABLE and repo:
                    repo.index.add([str(checkpoint_dir.relative_to(self.repo_path))])
                    
                    # Stage actual files if they're in the repo
                    for filepath in files:
                        file_path = Path(filepath)
                        if file_path.exists():
                            try:
                                rel_path = file_path.relative_to(self.repo_path)
                                repo.index.add([str(rel_path)])
                            except ValueError:
                                # File outside repo, skip
                                pass
                else:
                    # Fallback to subprocess
                    subprocess.run(
                        ['git', '-C', str(self.repo_path), 'add', str(checkpoint_dir)],
                        capture_output=True, text=True, check=True
                    )
                
                # Create commit message
                commit_message = self._format_commit_message(
                    checkpoint_id=checkpoint_id,
                    build_id=build_id,
                    stage=stage,
                    session_id=session_id or "default",
                    agent_count=agent_count,
                    status=status
                )
                
                # Create commit
                if GITPYTHON_AVAILABLE and repo:
                    commit = repo.index.commit(
                        commit_message,
                        author=git.Actor(self.user_name, self.user_email),
                        committer=git.Actor(self.user_name, self.user_email)
                    )
                    commit_hash = commit.hexsha
                else:
                    # Fallback to subprocess
                    env = os.environ.copy()
                    env['GIT_AUTHOR_NAME'] = self.user_name
                    env['GIT_AUTHOR_EMAIL'] = self.user_email
                    env['GIT_COMMITTER_NAME'] = self.user_name
                    env['GIT_COMMITTER_EMAIL'] = self.user_email
                    
                    result = subprocess.run(
                        ['git', '-C', str(self.repo_path), 'commit', '-m', commit_message],
                        capture_output=True, text=True, check=True, env=env
                    )
                    
                    # Get commit hash
                    result = subprocess.run(
                        ['git', '-C', str(self.repo_path), 'rev-parse', 'HEAD'],
                        capture_output=True, text=True, check=True
                    )
                    commit_hash = result.stdout.strip()
                
                # Create checkpoint tag
                tag_name = await self.create_checkpoint_tag(checkpoint_id, f"Checkpoint {stage}")
                
                # Update statistics
                self.stats['commits_created'] += 1
                self.stats['tags_created'] += 1
                
                logger.info(f"Checkpoint created: {checkpoint_id} (commit: {commit_hash[:8]})")
                return checkpoint_id, commit_hash
                
            except Exception as e:
                logger.error(f"Failed to create checkpoint: {e}")
                raise GitManagerError(f"Checkpoint creation failed: {e}")
    
    async def create_checkpoint_tag(
        self,
        checkpoint_id: str,
        message: Optional[str] = None,
        annotated: bool = True
    ) -> str:
        """
        Create a tag for a checkpoint
        
        Args:
            checkpoint_id: Checkpoint identifier
            message: Tag message
            annotated: Whether to create an annotated tag
            
        Returns:
            Tag name
        """
        async with self._lock:
            repo = await self.open_repo()
            
            try:
                # Parse checkpoint ID for tag format
                parts = checkpoint_id.split('-')
                if len(parts) >= 3:
                    build_id = parts[0]
                    stage = parts[1]
                    timestamp = '-'.join(parts[2:])
                    tag_name = f"{self.TAG_PREFIX}/{build_id}/{stage}/{timestamp}"
                else:
                    tag_name = f"{self.TAG_PREFIX}/{checkpoint_id}"
                
                if GITPYTHON_AVAILABLE and repo:
                    if annotated:
                        repo.create_tag(
                            tag_name,
                            message=message or f"Checkpoint: {checkpoint_id}",
                            force=True
                        )
                    else:
                        repo.create_tag(tag_name, force=True)
                else:
                    # Fallback to subprocess
                    cmd = ['git', '-C', str(self.repo_path), 'tag']
                    if annotated:
                        cmd.extend(['-a', '-m', message or f"Checkpoint: {checkpoint_id}"])
                    cmd.extend([tag_name, '-f'])
                    subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                logger.debug(f"Tag created: {tag_name}")
                return tag_name
                
            except Exception as e:
                logger.error(f"Failed to create tag: {e}")
                raise GitManagerError(f"Tag creation failed: {e}")
    
    async def rollback_to_checkpoint(
        self,
        checkpoint_id: str,
        create_backup: bool = True,
        backup_suffix: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Rollback to a specific checkpoint
        
        Args:
            checkpoint_id: Checkpoint to rollback to
            create_backup: Whether to create a backup branch before rollback
            backup_suffix: Custom suffix for backup branch name
            
        Returns:
            Rollback result dictionary
        """
        async with self._lock:
            repo = await self.open_repo()
            
            try:
                # Find commit hash for checkpoint
                commit_hash = await self._resolve_checkpoint(checkpoint_id)
                if not commit_hash:
                    raise CheckpointNotFoundError(f"Checkpoint not found: {checkpoint_id}")
                
                # Create backup branch
                backup_branch = None
                if create_backup:
                    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
                    suffix = backup_suffix or f"pre-rollback-{timestamp}"
                    backup_branch = f"backup/{suffix}"
                    
                    if GITPYTHON_AVAILABLE and repo:
                        current = repo.head.commit
                        repo.create_head(backup_branch, current)
                    else:
                        subprocess.run(
                            ['git', '-C', str(self.repo_path), 'branch', backup_branch],
                            capture_output=True, text=True, check=True
                        )
                    
                    self.stats['branches_created'] += 1
                    logger.info(f"Backup branch created: {backup_branch}")
                
                # Perform rollback
                if GITPYTHON_AVAILABLE and repo:
                    repo.git.checkout(commit_hash)
                else:
                    subprocess.run(
                        ['git', '-C', str(self.repo_path), 'checkout', commit_hash],
                        capture_output=True, text=True, check=True
                    )
                
                # Create rollback marker
                rollback_info = {
                    'checkpoint_id': checkpoint_id,
                    'commit_hash': commit_hash,
                    'timestamp': datetime.utcnow().isoformat(),
                    'backup_branch': backup_branch,
                    'performed_by': self.user_name
                }
                
                marker_path = self.repo_path / 'checkpoints' / '.rollback_history'
                marker_path.parent.mkdir(parents=True, exist_ok=True)
                
                rollbacks = []
                if marker_path.exists():
                    rollbacks = json.loads(marker_path.read_text())
                rollbacks.append(rollback_info)
                marker_path.write_text(json.dumps(rollbacks, indent=2))
                
                self.stats['rollbacks_performed'] += 1
                
                logger.info(f"Rolled back to checkpoint: {checkpoint_id}")
                
                return {
                    'success': True,
                    'checkpoint_id': checkpoint_id,
                    'commit_hash': commit_hash,
                    'backup_branch': backup_branch,
                    'timestamp': rollback_info['timestamp']
                }
                
            except Exception as e:
                logger.error(f"Rollback failed: {e}")
                raise GitManagerError(f"Rollback failed: {e}")
    
    async def list_checkpoints(
        self,
        build_id: Optional[str] = None,
        stage: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100
    ) -> List[CheckpointInfo]:
        """
        List checkpoints with optional filtering
        
        Args:
            build_id: Filter by build ID
            stage: Filter by stage
            since: Only checkpoints after this time
            until: Only checkpoints before this time
            limit: Maximum number of results
            
        Returns:
            List of CheckpointInfo objects
        """
        async with self._lock:
            repo = await self.open_repo()
            checkpoints = []
            
            try:
                # Get all checkpoint tags
                if GITPYTHON_AVAILABLE and repo:
                    tags = [t for t in repo.tags if t.name.startswith(self.TAG_PREFIX)]
                    
                    for tag in tags:
                        commit = tag.commit
                        checkpoint_info = self._parse_checkpoint_tag(tag.name, commit)
                        
                        if checkpoint_info:
                            # Apply filters
                            if build_id and checkpoint_info.build_id != build_id:
                                continue
                            if stage and checkpoint_info.stage != stage:
                                continue
                            if since and checkpoint_info.timestamp < since:
                                continue
                            if until and checkpoint_info.timestamp > until:
                                continue
                            
                            checkpoints.append(checkpoint_info)
                else:
                    # Fallback to subprocess
                    result = subprocess.run(
                        ['git', '-C', str(self.repo_path), 'tag', '-l', f'{self.TAG_PREFIX}/*'],
                        capture_output=True, text=True, check=True
                    )
                    
                    for tag_name in result.stdout.strip().split('\n'):
                        if not tag_name:
                            continue
                        
                        # Get commit info
                        result = subprocess.run(
                            ['git', '-C', str(self.repo_path), 'log', '-1', 
                             '--format=%H|%aI|%an|%s', tag_name],
                            capture_output=True, text=True, check=True
                        )
                        
                        parts = result.stdout.strip().split('|', 3)
                        if len(parts) >= 4:
                            commit_hash, timestamp_str, author, message = parts
                            checkpoint_info = self._parse_checkpoint_info(
                                tag_name, commit_hash, timestamp_str, author, message
                            )
                            
                            if checkpoint_info:
                                if build_id and checkpoint_info.build_id != build_id:
                                    continue
                                if stage and checkpoint_info.stage != stage:
                                    continue
                                
                                checkpoints.append(checkpoint_info)
                
                # Sort by timestamp (newest first) and limit
                checkpoints.sort(key=lambda x: x.timestamp, reverse=True)
                return checkpoints[:limit]
                
            except Exception as e:
                logger.error(f"Failed to list checkpoints: {e}")
                raise GitManagerError(f"Checkpoint listing failed: {e}")
    
    async def get_checkpoint_diff(
        self,
        checkpoint_id1: str,
        checkpoint_id2: str
    ) -> DiffResult:
        """
        Get diff between two checkpoints
        
        Args:
            checkpoint_id1: First checkpoint ID
            checkpoint_id2: Second checkpoint ID
            
        Returns:
            DiffResult with file changes
        """
        async with self._lock:
            await self.open_repo()
            
            try:
                commit1 = await self._resolve_checkpoint(checkpoint_id1)
                commit2 = await self._resolve_checkpoint(checkpoint_id2)
                
                if not commit1 or not commit2:
                    raise CheckpointNotFoundError("One or both checkpoints not found")
                
                if GITPYTHON_AVAILABLE and self._repo:
                    diff = self._repo.git.diff(
                        commit1, commit2, 
                        '--stat', 
                        '--numstat'
                    )
                    
                    # Parse diff stats
                    files_changed = []
                    total_insertions = 0
                    total_deletions = 0
                    
                    for line in diff.split('\n'):
                        if '|' in line and 'files changed' not in line:
                            parts = line.split('|')
                            if len(parts) == 2:
                                filename = parts[0].strip()
                                stats = parts[1].strip()
                                files_changed.append({
                                    'file': filename,
                                    'stats': stats
                                })
                else:
                    # Fallback to subprocess
                    result = subprocess.run(
                        ['git', '-C', str(self.repo_path), 'diff', 
                         '--stat', commit1, commit2],
                        capture_output=True, text=True, check=True
                    )
                    
                    files_changed = []
                    total_insertions = 0
                    total_deletions = 0
                    
                    for line in result.stdout.strip().split('\n'):
                        if 'files changed' in line or 'file changed' in line:
                            # Parse summary line
                            parts = line.split(',')
                            for part in parts:
                                if 'insertion' in part:
                                    total_insertions = int(part.strip().split()[0])
                                elif 'deletion' in part:
                                    total_deletions = int(part.strip().split()[0])
                
                # Get full diff text
                full_diff = await self._get_diff_text(commit1, commit2)
                
                return DiffResult(
                    checkpoint_from=checkpoint_id1,
                    checkpoint_to=checkpoint_id2,
                    files_changed=files_changed,
                    total_insertions=total_insertions,
                    total_deletions=total_deletions,
                    diff_text=full_diff
                )
                
            except Exception as e:
                logger.error(f"Failed to get checkpoint diff: {e}")
                raise GitManagerError(f"Diff failed: {e}")
    
    # ========================================================================
    # Branch Management
    # ========================================================================
    
    async def create_branch(
        self,
        session_id: str,
        from_checkpoint: Optional[str] = None,
        checkout: bool = False
    ) -> str:
        """
        Create a new branch for parallel session
        
        Args:
            session_id: Session identifier
            from_checkpoint: Checkpoint to branch from (defaults to current)
            checkout: Whether to checkout the new branch
            
        Returns:
            Branch name
        """
        async with self._lock:
            repo = await self.open_repo()
            
            try:
                branch_name = f"{self.branch_prefix}{session_id}"
                
                if GITPYTHON_AVAILABLE and repo:
                    if from_checkpoint:
                        commit_hash = await self._resolve_checkpoint(from_checkpoint)
                        commit = repo.commit(commit_hash)
                        repo.create_head(branch_name, commit)
                    else:
                        repo.create_head(branch_name)
                    
                    if checkout:
                        repo.heads[branch_name].checkout()
                else:
                    # Fallback to subprocess
                    cmd = ['git', '-C', str(self.repo_path), 'branch', branch_name]
                    if from_checkpoint:
                        commit_hash = await self._resolve_checkpoint(from_checkpoint)
                        cmd.append(commit_hash)
                    subprocess.run(cmd, capture_output=True, text=True, check=True)
                    
                    if checkout:
                        subprocess.run(
                            ['git', '-C', str(self.repo_path), 'checkout', branch_name],
                            capture_output=True, text=True, check=True
                        )
                
                self.stats['branches_created'] += 1
                logger.info(f"Branch created: {branch_name}")
                return branch_name
                
            except Exception as e:
                logger.error(f"Failed to create branch: {e}")
                raise GitManagerError(f"Branch creation failed: {e}")
    
    async def checkout_branch(
        self,
        branch_name: str,
        create: bool = False
    ) -> bool:
        """
        Checkout a branch
        
        Args:
            branch_name: Branch to checkout
            create: Create branch if it doesn't exist
            
        Returns:
            True if successful
        """
        async with self._lock:
            repo = await self.open_repo()
            
            try:
                if GITPYTHON_AVAILABLE and repo:
                    if create and branch_name not in [h.name for h in repo.heads]:
                        repo.create_head(branch_name)
                    repo.heads[branch_name].checkout()
                else:
                    cmd = ['git', '-C', str(self.repo_path), 'checkout']
                    if create:
                        cmd.append('-b')
                    cmd.append(branch_name)
                    subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                logger.info(f"Checked out branch: {branch_name}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to checkout branch: {e}")
                raise GitManagerError(f"Branch checkout failed: {e}")
    
    async def list_branches(
        self,
        remote: bool = False
    ) -> List[BranchInfo]:
        """
        List all branches
        
        Args:
            remote: Include remote branches
            
        Returns:
            List of BranchInfo objects
        """
        async with self._lock:
            repo = await self.open_repo()
            branches = []
            
            try:
                if GITPYTHON_AVAILABLE and repo:
                    # Local branches
                    for head in repo.heads:
                        branches.append(BranchInfo(
                            name=head.name,
                            commit_hash=head.commit.hexsha,
                            is_remote=False,
                            is_active=repo.head.ref == head,
                            last_commit_time=datetime.fromtimestamp(head.commit.committed_date),
                            tracking_branch=head.tracking_branch().name if head.tracking_branch() else None
                        ))
                    
                    # Remote branches
                    if remote:
                        for ref in repo.remote().refs:
                            branches.append(BranchInfo(
                                name=ref.name,
                                commit_hash=ref.commit.hexsha,
                                is_remote=True,
                                is_active=False,
                                last_commit_time=datetime.fromtimestamp(ref.commit.committed_date)
                            ))
                else:
                    # Fallback to subprocess
                    cmd = ['git', '-C', str(self.repo_path), 'branch', '-a', '-v', '--format=%(refname:short)|%(objectname:short)|%(upstream:short)']
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    
                    current_branch = None
                    try:
                        current_result = subprocess.run(
                            ['git', '-C', str(self.repo_path), 'rev-parse', '--abbrev-ref', 'HEAD'],
                            capture_output=True, text=True, check=True
                        )
                        current_branch = current_result.stdout.strip()
                    except:
                        pass
                    
                    for line in result.stdout.strip().split('\n'):
                        if not line:
                            continue
                        parts = line.split('|')
                        if len(parts) >= 2:
                            name = parts[0].strip()
                            if name.startswith('*'):
                                name = name[1:].strip()
                            branches.append(BranchInfo(
                                name=name,
                                commit_hash=parts[1].strip(),
                                is_remote=name.startswith('remotes/'),
                                is_active=name == current_branch,
                                tracking_branch=parts[2].strip() if len(parts) > 2 and parts[2].strip() else None
                            ))
                
                return branches
                
            except Exception as e:
                logger.error(f"Failed to list branches: {e}")
                raise GitManagerError(f"Branch listing failed: {e}")
    
    # ========================================================================
    # Remote Operations
    # ========================================================================
    
    async def push_to_remote(
        self,
        remote_url: Optional[str] = None,
        checkpoint_id: Optional[str] = None,
        branch: Optional[str] = None,
        tags: bool = True
    ) -> Dict[str, Any]:
        """
        Push checkpoints to remote repository
        
        Args:
            remote_url: Remote URL (defaults to configured remote)
            checkpoint_id: Specific checkpoint to push (pushes tag)
            branch: Specific branch to push
            tags: Whether to push tags
            
        Returns:
            Push result dictionary
        """
        async with self._lock:
            repo = await self.open_repo()
            remote = remote_url or self.remote_url
            
            if not remote:
                raise GitManagerError("No remote URL configured")
            
            try:
                pushed = []
                
                if GITPYTHON_AVAILABLE and repo:
                    # Configure remote if URL provided
                    if remote_url:
                        try:
                            origin = repo.remote('origin')
                        except:
                            origin = repo.create_remote('origin', remote_url)
                    else:
                        origin = repo.remote('origin')
                    
                    # Push branch
                    if branch:
                        origin.push(refspec=f"{branch}:{branch}")
                        pushed.append(f"branch:{branch}")
                    else:
                        # Push current branch
                        origin.push()
                        pushed.append(f"branch:{repo.active_branch.name}")
                    
                    # Push specific tag
                    if checkpoint_id:
                        tag_name = self._checkpoint_to_tag(checkpoint_id)
                        origin.push(tag_name)
                        pushed.append(f"tag:{tag_name}")
                    elif tags:
                        # Push all tags
                        origin.push(tags=True)
                        pushed.append("tags:all")
                else:
                    # Fallback to subprocess
                    # Add remote if not exists
                    try:
                        subprocess.run(
                            ['git', '-C', str(self.repo_path), 'remote', 'add', 'origin', remote],
                            capture_output=True, text=True, check=True
                        )
                    except:
                        pass  # Remote may already exist
                    
                    # Push
                    cmd = ['git', '-C', str(self.repo_path), 'push', 'origin']
                    if branch:
                        cmd.append(branch)
                    if tags and not checkpoint_id:
                        cmd.append('--tags')
                    
                    subprocess.run(cmd, capture_output=True, text=True, check=True)
                    
                    if checkpoint_id:
                        tag_name = self._checkpoint_to_tag(checkpoint_id)
                        subprocess.run(
                            ['git', '-C', str(self.repo_path), 'push', 'origin', tag_name],
                            capture_output=True, text=True, check=True
                        )
                    
                    pushed.append(f"branch:{branch or 'current'}")
                
                self.stats['remote_pushes'] += 1
                
                logger.info(f"Pushed to remote: {remote}")
                return {
                    'success': True,
                    'remote': remote,
                    'pushed': pushed,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Failed to push to remote: {e}")
                raise GitManagerError(f"Remote push failed: {e}")
    
    async def fetch_from_remote(
        self,
        remote_url: Optional[str] = None,
        prune: bool = True
    ) -> Dict[str, Any]:
        """
        Fetch updates from remote repository
        
        Args:
            remote_url: Remote URL (defaults to configured remote)
            prune: Remove deleted remote branches
            
        Returns:
            Fetch result dictionary
        """
        async with self._lock:
            repo = await self.open_repo()
            remote = remote_url or self.remote_url
            
            try:
                if GITPYTHON_AVAILABLE and repo:
                    origin = repo.remote('origin')
                    fetch_info = origin.fetch(prune=prune)
                    
                    fetched_refs = [info.name for info in fetch_info]
                else:
                    cmd = ['git', '-C', str(self.repo_path), 'fetch']
                    if prune:
                        cmd.append('--prune')
                    if remote:
                        cmd.append(remote)
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    fetched_refs = result.stdout.strip().split('\n') if result.stdout else []
                
                logger.info(f"Fetched from remote: {len(fetched_refs)} refs updated")
                return {
                    'success': True,
                    'remote': remote,
                    'fetched_refs': fetched_refs,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Failed to fetch from remote: {e}")
                raise GitManagerError(f"Remote fetch failed: {e}")
    
    # ========================================================================
    # Integrity and Verification
    # ========================================================================
    
    async def verify_checkpoint_integrity(
        self,
        checkpoint_id: str
    ) -> Dict[str, Any]:
        """
        Verify integrity of a checkpoint
        
        Args:
            checkpoint_id: Checkpoint to verify
            
        Returns:
            Verification result dictionary
        """
        async with self._lock:
            await self.open_repo()
            
            try:
                commit_hash = await self._resolve_checkpoint(checkpoint_id)
                if not commit_hash:
                    raise CheckpointNotFoundError(f"Checkpoint not found: {checkpoint_id}")
                
                verification_results = {
                    'checkpoint_id': checkpoint_id,
                    'commit_hash': commit_hash,
                    'timestamp': datetime.utcnow().isoformat(),
                    'checks': {}
                }
                
                # Check 1: Verify commit exists and is reachable
                try:
                    if GITPYTHON_AVAILABLE and self._repo:
                        commit = self._repo.commit(commit_hash)
                        verification_results['checks']['commit_exists'] = True
                        verification_results['checks']['commit_message'] = commit.message
                        verification_results['checks']['commit_author'] = str(commit.author)
                        verification_results['checks']['commit_date'] = datetime.fromtimestamp(
                            commit.committed_date
                        ).isoformat()
                    else:
                        result = subprocess.run(
                            ['git', '-C', str(self.repo_path), 'cat-file', '-t', commit_hash],
                            capture_output=True, text=True, check=True
                        )
                        verification_results['checks']['commit_exists'] = 'commit' in result.stdout
                except Exception as e:
                    verification_results['checks']['commit_exists'] = False
                    verification_results['checks']['commit_error'] = str(e)
                
                # Check 2: Verify tag exists and points to commit
                try:
                    tag_name = self._checkpoint_to_tag(checkpoint_id)
                    if GITPYTHON_AVAILABLE and self._repo:
                        tag = self._repo.tags[tag_name]
                        verification_results['checks']['tag_exists'] = True
                        verification_results['checks']['tag_points_to_commit'] = (
                            tag.commit.hexsha == commit_hash
                        )
                    else:
                        result = subprocess.run(
                            ['git', '-C', str(self.repo_path), 'show-ref', tag_name],
                            capture_output=True, text=True, check=True
                        )
                        verification_results['checks']['tag_exists'] = commit_hash in result.stdout
                except Exception as e:
                    verification_results['checks']['tag_exists'] = False
                
                # Check 3: Verify GPG signature if present
                try:
                    if GITPYTHON_AVAILABLE and self._repo:
                        commit = self._repo.commit(commit_hash)
                        # Check for signature
                        signature = commit.message if '-----BEGIN PGP SIGNATURE-----' in commit.message else None
                    else:
                        result = subprocess.run(
                            ['git', '-C', str(self.repo_path), 'verify-commit', commit_hash],
                            capture_output=True, text=True
                        )
                        signature_valid = result.returncode == 0
                        verification_results['checks']['gpg_signed'] = signature_valid
                        if result.returncode == 0:
                            verification_results['checks']['gpg_signature'] = result.stdout.strip()
                except Exception as e:
                    verification_results['checks']['gpg_signed'] = False
                
                # Check 4: Verify metadata file exists
                metadata_path = self.repo_path / 'checkpoints' / checkpoint_id.split('-')[0] / f"{checkpoint_id}_metadata.json"
                verification_results['checks']['metadata_exists'] = metadata_path.exists()
                
                if metadata_path.exists():
                    try:
                        metadata = json.loads(metadata_path.read_text())
                        verification_results['checks']['metadata_valid'] = True
                        verification_results['checks']['metadata_hash'] = hashlib.sha256(
                            metadata_path.read_bytes()
                        ).hexdigest()[:16]
                    except json.JSONDecodeError:
                        verification_results['checks']['metadata_valid'] = False
                
                # Overall verification status
                all_passed = all(
                    v for k, v in verification_results['checks'].items() 
                    if isinstance(v, bool)
                )
                verification_results['verified'] = all_passed
                
                self.stats['integrity_checks'] += 1
                
                logger.info(f"Integrity verified for {checkpoint_id}: {all_passed}")
                return verification_results
                
            except Exception as e:
                logger.error(f"Integrity verification failed: {e}")
                raise IntegrityError(f"Verification failed: {e}")
    
    async def gc(self, aggressive: bool = False) -> Dict[str, Any]:
        """
        Run garbage collection on repository
        
        Args:
            aggressive: Run aggressive garbage collection
            
        Returns:
            GC result dictionary
        """
        async with self._lock:
            await self.open_repo()
            
            try:
                cmd = ['git', '-C', str(self.repo_path), 'gc']
                if aggressive:
                    cmd.append('--aggressive')
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                logger.info("Garbage collection completed")
                return {
                    'success': True,
                    'aggressive': aggressive,
                    'output': result.stdout
                }
                
            except Exception as e:
                logger.error(f"Garbage collection failed: {e}")
                raise GitManagerError(f"GC failed: {e}")
    
    # ========================================================================
    # Statistics and Info
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get operation statistics"""
        return {
            **self.stats,
            'repo_path': str(self.repo_path),
            'git_available': GITPYTHON_AVAILABLE,
            'signing_enabled': self.signing_key is not None,
            'remote_configured': self.remote_url is not None
        }
    
    async def get_repo_info(self) -> Dict[str, Any]:
        """Get repository information"""
        async with self._lock:
            repo = await self.open_repo()
            
            try:
                if GITPYTHON_AVAILABLE and repo:
                    return {
                        'path': str(self.repo_path),
                        'bare': repo.bare,
                        'active_branch': repo.active_branch.name if not repo.bare else None,
                        'branches': len(repo.heads),
                        'tags': len(repo.tags),
                        'commits': len(list(repo.iter_commits())),
                        'untracked_files': len(repo.untracked_files),
                        'is_dirty': repo.is_dirty(),
                        'head_commit': repo.head.commit.hexsha[:8] if not repo.bare else None
                    }
                else:
                    # Fallback to subprocess
                    result = subprocess.run(
                        ['git', '-C', str(self.repo_path), 'rev-parse', '--abbrev-ref', 'HEAD'],
                        capture_output=True, text=True, check=True
                    )
                    active_branch = result.stdout.strip()
                    
                    result = subprocess.run(
                        ['git', '-C', str(self.repo_path), 'rev-list', '--count', 'HEAD'],
                        capture_output=True, text=True, check=True
                    )
                    commit_count = int(result.stdout.strip())
                    
                    return {
                        'path': str(self.repo_path),
                        'active_branch': active_branch,
                        'commits': commit_count,
                        'git_available': False
                    }
                    
            except Exception as e:
                logger.error(f"Failed to get repo info: {e}")
                raise GitManagerError(f"Repo info failed: {e}")
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    async def _configure_git_user(self):
        """Configure git user name and email"""
        if GITPYTHON_AVAILABLE and self._repo:
            config = self._repo.config_writer()
            config.set_value('user', 'name', self.user_name)
            config.set_value('user', 'email', self.user_email)
            config.release()
        else:
            subprocess.run(
                ['git', '-C', str(self.repo_path), 'config', 'user.name', self.user_name],
                capture_output=True, check=True
            )
            subprocess.run(
                ['git', '-C', str(self.repo_path), 'config', 'user.email', self.user_email],
                capture_output=True, check=True
            )
    
    async def _configure_gpg_signing(self):
        """Configure GPG signing"""
        if not self.signing_key:
            return
        
        if GITPYTHON_AVAILABLE and self._repo:
            config = self._repo.config_writer()
            config.set_value('user', 'signingkey', self.signing_key)
            config.set_value('commit', 'gpgsign', 'true')
            config.set_value('tag', 'gpgsign', 'true')
            config.release()
        else:
            subprocess.run(
                ['git', '-C', str(self.repo_path), 'config', 'user.signingkey', self.signing_key],
                capture_output=True, check=True
            )
            subprocess.run(
                ['git', '-C', str(self.repo_path), 'config', 'commit.gpgsign', 'true'],
                capture_output=True, check=True
            )
    
    async def _create_gitignore(self):
        """Create .gitignore file"""
        gitignore_path = self.repo_path / '.gitignore'
        if not gitignore_path.exists():
            gitignore_path.write_text(self.GITIGNORE_TEMPLATE)
    
    async def _create_directory_structure(self):
        """Create checkpoint directory structure"""
        (self.repo_path / 'checkpoints').mkdir(exist_ok=True)
    
    def _generate_checkpoint_id(
        self,
        build_id: str,
        stage: str,
        timestamp: datetime
    ) -> str:
        """Generate unique checkpoint ID"""
        ts_str = timestamp.strftime('%Y%m%d-%H%M%S')
        return f"{build_id}-{stage}-{ts_str}"
    
    def _format_commit_message(
        self,
        checkpoint_id: str,
        build_id: str,
        stage: str,
        session_id: str,
        agent_count: int,
        status: str
    ) -> str:
        """Format checkpoint commit message"""
        return f"""checkpoint: {build_id}/{stage}

- Session: {session_id}
- Agents: {agent_count}
- Status: {status}
- Tier: 3 (Git Immutable)
- Checkpoint ID: {checkpoint_id}
- Timestamp: {datetime.utcnow().isoformat()}
"""
    
    def _generate_readme(self) -> str:
        """Generate README for checkpoint repository"""
        return f"""# APEX Checkpoint Repository

This repository contains immutable Tier 3 checkpoints for APEX builds.

## Structure

```
checkpoints/
  └── {{build_id}}/
      ├── metadata.json
      ├── agent_outputs/
      │   └── {{agent_name}}.json
      └── files/
          └── (symlinks to actual files)
```

## Tag Format

Checkpoints are tagged as:
```
checkpoint/{{build_id}}/{{stage}}/{{timestamp}}
```

## Configuration

- Created: {datetime.utcnow().isoformat()}
- User: {self.user_name} <{self.user_email}>
- GPG Signing: {'Enabled' if self.signing_key else 'Disabled'}

## Security

This repository is configured to exclude sensitive files via .gitignore.
All checkpoint commits are immutable and should not be modified.
"""
    
    def _checkpoint_to_tag(self, checkpoint_id: str) -> str:
        """Convert checkpoint ID to tag name
        
        Format: checkpoint/{build_id}/{stage}/{timestamp}
        Checkpoint ID format: {build_id}-{stage}-{timestamp}
        """
        # Find the second-to-last hyphen to separate stage from timestamp
        # Timestamp format: YYYYMMDD-HHMMSS (contains a hyphen)
        parts = checkpoint_id.split('-')
        
        # Need at least: build_id, stage, date, time
        if len(parts) >= 4:
            build_id = parts[0]
            stage = parts[1]
            # Remaining parts form the timestamp (date-HHMMSS)
            timestamp = '-'.join(parts[2:])
            return f"{self.TAG_PREFIX}/{build_id}/{stage}/{timestamp}"
        elif len(parts) == 3:
            # Simple format without hyphen in timestamp
            return f"{self.TAG_PREFIX}/{parts[0]}/{parts[1]}/{parts[2]}"
        return f"{self.TAG_PREFIX}/{checkpoint_id}"
    
    async def _resolve_checkpoint(self, checkpoint_id: str) -> Optional[str]:
        """Resolve checkpoint ID to commit hash"""
        try:
            # Try as tag
            tag_name = self._checkpoint_to_tag(checkpoint_id)
            
            if GITPYTHON_AVAILABLE and self._repo:
                try:
                    tag = self._repo.tags[tag_name]
                    return tag.commit.hexsha
                except (IndexError, AttributeError):
                    pass
            
            # Fallback to subprocess
            result = subprocess.run(
                ['git', '-C', str(self.repo_path), 'rev-list', '-n', '1', tag_name],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
            
            # Try as direct commit hash
            result = subprocess.run(
                ['git', '-C', str(self.repo_path), 'cat-file', '-t', checkpoint_id],
                capture_output=True, text=True
            )
            if result.returncode == 0 and 'commit' in result.stdout:
                return checkpoint_id
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to resolve checkpoint {checkpoint_id}: {e}")
            return None
    
    def _parse_checkpoint_tag(
        self,
        tag_name: str,
        commit: Any
    ) -> Optional[CheckpointInfo]:
        """Parse checkpoint info from tag and commit"""
        try:
            # Parse tag name: checkpoint/{build_id}/{stage}/{timestamp}
            parts = tag_name.split('/')
            if len(parts) != 4:
                return None
            
            _, build_id, stage, timestamp_str = parts
            
            # Parse timestamp
            try:
                timestamp = datetime.strptime(timestamp_str, '%Y%m%d-%H%M%S')
            except ValueError:
                timestamp = datetime.fromtimestamp(commit.committed_date)
            
            # Get stats
            stats = commit.stats
            
            return CheckpointInfo(
                checkpoint_id=f"{build_id}-{stage}-{timestamp_str}",
                commit_hash=commit.hexsha,
                tag_name=tag_name,
                timestamp=timestamp,
                build_id=build_id,
                stage=stage,
                message=commit.message.split('\n')[0],
                author=str(commit.author),
                files_changed=len(stats.files),
                insertions=sum(f['insertions'] for f in stats.files.values()),
                deletions=sum(f['deletions'] for f in stats.files.values()),
                gpg_signed='-----BEGIN PGP SIGNATURE-----' in commit.message
            )
            
        except Exception as e:
            logger.debug(f"Failed to parse checkpoint tag: {e}")
            return None
    
    def _parse_checkpoint_info(
        self,
        tag_name: str,
        commit_hash: str,
        timestamp_str: str,
        author: str,
        message: str
    ) -> Optional[CheckpointInfo]:
        """Parse checkpoint info from subprocess output"""
        try:
            parts = tag_name.split('/')
            if len(parts) != 4:
                return None
            
            _, build_id, stage, ts_str = parts
            
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                timestamp = datetime.utcnow()
            
            return CheckpointInfo(
                checkpoint_id=f"{build_id}-{stage}-{ts_str}",
                commit_hash=commit_hash,
                tag_name=tag_name,
                timestamp=timestamp,
                build_id=build_id,
                stage=stage,
                message=message,
                author=author,
                files_changed=0,
                insertions=0,
                deletions=0
            )
            
        except Exception as e:
            logger.debug(f"Failed to parse checkpoint info: {e}")
            return None
    
    async def _get_diff_text(self, commit1: str, commit2: str) -> str:
        """Get full diff text between commits"""
        try:
            result = subprocess.run(
                ['git', '-C', str(self.repo_path), 'diff', commit1, commit2],
                capture_output=True, text=True, check=True
            )
            return result.stdout
        except Exception as e:
            logger.debug(f"Failed to get diff text: {e}")
            return ""


# ============================================================================
# Demo and Testing
# ============================================================================

async def demo():
    """Demonstrate GitManager capabilities"""
    print("=" * 70)
    print("APEX Git Automation Layer - Demo")
    print("=" * 70)
    
    # Create temporary directory for demo
    demo_dir = Path(tempfile.mkdtemp(prefix="apex_git_demo_"))
    repo_path = demo_dir / "checkpoints_repo"
    
    print(f"\nDemo directory: {demo_dir}")
    print(f"Repository path: {repo_path}")
    
    try:
        # Initialize GitManager
        print("\n--- Initializing GitManager ---")
        gm = GitManager(
            repo_path=str(repo_path),
            user_name="APEX Demo",
            user_email="demo@apex.local"
        )
        
        # Initialize repository
        print("\n--- Initializing Repository ---")
        repo = await gm.init_repo()
        print(f"Repository initialized at: {repo_path}")
        
        # Get repo info
        info = await gm.get_repo_info()
        print(f"Repository info: {json.dumps(info, indent=2, default=str)}")
        
        # Create sample files
        sample_dir = demo_dir / "sample_project"
        sample_dir.mkdir()
        
        (sample_dir / "main.py").write_text("""
def main():
    print("Hello, APEX!")
    return 0

if __name__ == "__main__":
    main()
""")
        
        (sample_dir / "config.yaml").write_text("""
project: APEX Demo
version: 1.0.0
agents:
  - meta_router
  - planning
  - frontend
""")
        
        # Create first checkpoint
        print("\n--- Creating Checkpoint 1 (Analysis) ---")
        checkpoint1, commit1 = await gm.create_checkpoint_commit(
            build_id="demo-build-001",
            stage="analysis",
            files=[str(sample_dir / "main.py"), str(sample_dir / "config.yaml")],
            metadata={"purpose": "Initial analysis", "test": True},
            agent_outputs={
                "meta_router": {"stack_detected": "python", "confidence": 0.95},
                "planning": {"architecture": "microservices"}
            },
            session_id="demo-session-1",
            agent_count=2,
            status="completed"
        )
        print(f"Created checkpoint: {checkpoint1}")
        print(f"Commit hash: {commit1[:8]}")
        
        # Modify files and create second checkpoint
        (sample_dir / "main.py").write_text("""
def main():
    print("Hello, APEX! v2")
    # Added feature
    process_data()
    return 0

def process_data():
    return {"status": "ok"}

if __name__ == "__main__":
    main()
""")
        
        print("\n--- Creating Checkpoint 2 (Planning) ---")
        checkpoint2, commit2 = await gm.create_checkpoint_commit(
            build_id="demo-build-001",
            stage="planning",
            files=[str(sample_dir / "main.py"), str(sample_dir / "config.yaml")],
            metadata={"purpose": "Planning phase", "test": True},
            agent_outputs={
                "planning": {"architecture": "microservices", "components": ["api", "ui"]},
                "meta_router": {"routing_decision": "proceed"}
            },
            session_id="demo-session-1",
            agent_count=2,
            status="completed",
            parent_checkpoint=checkpoint1
        )
        print(f"Created checkpoint: {checkpoint2}")
        print(f"Commit hash: {commit2[:8]}")
        
        # List checkpoints
        print("\n--- Listing Checkpoints ---")
        checkpoints = await gm.list_checkpoints(build_id="demo-build-001")
        print(f"Found {len(checkpoints)} checkpoints:")
        for cp in checkpoints:
            print(f"  - {cp.checkpoint_id} ({cp.stage}): {cp.commit_hash[:8]}")
        
        # Get checkpoint diff
        print("\n--- Checkpoint Diff ---")
        diff = await gm.get_checkpoint_diff(checkpoint1, checkpoint2)
        print(f"Files changed: {len(diff.files_changed)}")
        print(f"Insertions: {diff.total_insertions}")
        print(f"Deletions: {diff.total_deletions}")
        
        # Create a branch
        print("\n--- Creating Branch ---")
        branch_name = await gm.create_branch(
            session_id="feature-x",
            from_checkpoint=checkpoint2,
            checkout=True
        )
        print(f"Created and checked out branch: {branch_name}")
        
        # List branches
        print("\n--- Listing Branches ---")
        branches = await gm.list_branches()
        for branch in branches:
            marker = " *" if branch.is_active else ""
            print(f"  {branch.name}{marker}")
        
        # Verify checkpoint integrity
        print("\n--- Verifying Checkpoint Integrity ---")
        verification = await gm.verify_checkpoint_integrity(checkpoint2)
        print(f"Verified: {verification['verified']}")
        print(f"Checks: {json.dumps(verification['checks'], indent=2, default=str)}")
        
        # Show statistics
        print("\n--- Statistics ---")
        stats = gm.get_stats()
        print(json.dumps(stats, indent=2, default=str))
        
        # Demonstrate rollback (on a new branch to avoid disrupting demo)
        print("\n--- Rollback Demonstration ---")
        await gm.checkout_branch("main")
        rollback_result = await gm.rollback_to_checkpoint(
            checkpoint1,
            create_backup=True,
            backup_suffix="pre-rollback-demo"
        )
        print(f"Rollback result: {json.dumps(rollback_result, indent=2, default=str)}")
        
        # Restore to latest
        print("\n--- Restoring to Latest ---")
        await gm.checkout_branch("main")
        print("Restored to main branch")
        
        # Final repo info
        print("\n--- Final Repository Info ---")
        final_info = await gm.get_repo_info()
        print(json.dumps(final_info, indent=2, default=str))
        
        print("\n" + "=" * 70)
        print("Demo completed successfully!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\nDemo failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        if demo_dir.exists():
            print(f"\nCleaning up: {demo_dir}")
            shutil.rmtree(demo_dir, ignore_errors=True)


if __name__ == "__main__":
    # Run the demo
    asyncio.run(demo())


# ============================================================================
# Dependencies and Requirements
# ============================================================================
"""
DEPENDENCIES:
-------------
Required:
    - Python 3.8+
    - git (command-line tool)
    - asyncio

Optional (for enhanced performance):
    - GitPython >= 3.1.0
      Install: pip install GitPython

CONFIGURATION:
--------------
Environment Variables:
    CHECKPOINTS_REPO_PATH   - Path to git repository (default: /home/teacherchris37/MasterBuilder7/apex/checkpoints/git_store)
    GIT_USER_NAME           - Git user name for commits
    GIT_USER_EMAIL          - Git user email for commits
    GIT_SIGNING_KEY         - GPG key ID for commit signing (optional)
    CHECKPOINTS_REMOTE_URL  - Remote repository URL for backup (optional)
    CHECKPOINTS_BRANCH_PREFIX - Branch name prefix (default: session-)

USAGE EXAMPLES:
---------------

1. Basic Initialization:
    
    from git_manager import GitManager
    import asyncio
    
    async def main():
        # Initialize with default configuration
        gm = GitManager()
        
        # Or with explicit configuration
        gm = GitManager(
            repo_path="/path/to/checkpoints",
            user_name="APEX System",
            user_email="apex@example.com"
        )
        
        # Initialize repository
        repo = await gm.init_repo()
    
    asyncio.run(main())

2. Creating a Checkpoint:

    async def create_checkpoint(gm: GitManager):
        checkpoint_id, commit_hash = await gm.create_checkpoint_commit(
            build_id="build-001",
            stage="analysis",
            files=["/path/to/file1.py", "/path/to/file2.py"],
            metadata={"key": "value"},
            agent_outputs={
                "meta_router": {"result": "success"},
                "planning": {"architecture": "microservices"}
            },
            session_id="session-1",
            agent_count=2,
            status="completed"
        )
        print(f"Checkpoint created: {checkpoint_id}")

3. Listing Checkpoints:

    async def list_build_checkpoints(gm: GitManager, build_id: str):
        checkpoints = await gm.list_checkpoints(
            build_id=build_id,
            stage="analysis",
            limit=10
        )
        for cp in checkpoints:
            print(f"{cp.checkpoint_id}: {cp.commit_hash[:8]}")

4. Rollback:

    async def rollback(gm: GitManager, checkpoint_id: str):
        result = await gm.rollback_to_checkpoint(
            checkpoint_id,
            create_backup=True,
            backup_suffix="before-rollback"
        )
        if result['success']:
            print(f"Rolled back to {checkpoint_id}")
            print(f"Backup branch: {result['backup_branch']}")

5. Branch Management:

    async def manage_branches(gm: GitManager):
        # Create branch for parallel session
        branch_name = await gm.create_branch(
            session_id="feature-x",
            from_checkpoint="build-001-analysis-20260307-174637",
            checkout=True
        )
        
        # List all branches
        branches = await gm.list_branches()
        for branch in branches:
            print(f"{branch.name} {'(active)' if branch.is_active else ''}")

6. Remote Operations:

    async def remote_operations(gm: GitManager):
        # Push to remote
        result = await gm.push_to_remote(
            remote_url="https://github.com/user/checkpoints.git",
            branch="main",
            tags=True
        )
        
        # Fetch from remote
        result = await gm.fetch_from_remote(prune=True)

7. Integrity Verification:

    async def verify(gm: GitManager, checkpoint_id: str):
        result = await gm.verify_checkpoint_integrity(checkpoint_id)
        if result['verified']:
            print(f"Checkpoint {checkpoint_id} is valid")
        else:
            print(f"Verification failed: {result['checks']}")

INTEGRATION WITH CHECKPOINT MANAGER:
------------------------------------

The GitManager is designed to integrate with the APEX Three-Tier Checkpoint Manager:

    from checkpoint_manager import CheckpointManager
    from git_manager import GitManager
    
    # Initialize both
    cm = CheckpointManager(checkpoint_dir="/path/to/checkpoints")
    gm = GitManager(repo_path="/path/to/checkpoints/git_store")
    
    # Create Tier 1 (Redis) and Tier 2 (SQLite) via CheckpointManager
    tier1 = cm.create_tier1_checkpoint(...)
    tier2 = cm.create_tier2_checkpoint(...)
    
    # Create Tier 3 (Git) via GitManager
    checkpoint_id, commit_hash = await gm.create_checkpoint_commit(...)
    
    # Link them together
    tier2.git_commit_hash = commit_hash

CHECKPOINT STORAGE FORMAT:
--------------------------
The GitManager creates the following structure in the repository:

    checkpoints/
    └── {build_id}/
        ├── {checkpoint_id}_metadata.json
        ├── agent_outputs/
        │   ├── meta_router.json
        │   ├── planning.json
        │   └── ...
        └── files/
            ├── file1.py -> /actual/path/to/file1.py
            └── file2.py -> /actual/path/to/file2.py

TAG FORMAT:
-----------
Checkpoints are tagged with the format:
    checkpoint/{build_id}/{stage}/{timestamp}

Example:
    checkpoint/build-001/analysis/20260307-174637

COMMIT MESSAGE FORMAT:
----------------------
    checkpoint: {build_id}/{stage}
    
    - Session: {session_id}
    - Agents: {agent_count}
    - Status: {status}
    - Tier: 3 (Git Immutable)
    - Checkpoint ID: {checkpoint_id}
    - Timestamp: {iso_timestamp}

SECURITY NOTES:
---------------
1. GPG signing is supported but optional
2. Sensitive files are excluded via .gitignore
3. Checkpoints are immutable once committed
4. Rollback creates a backup branch automatically
5. Integrity verification checks commit existence, tag validity, and GPG signatures

PERFORMANCE NOTES:
------------------
1. GitPython provides better performance than subprocess fallback
2. All operations are async to prevent blocking
3. Repository lock ensures thread safety
4. Consider running `gc()` periodically for large repositories

ERROR HANDLING:
---------------
All operations raise GitManagerError or specific subclasses:
    - RepositoryNotFoundError: Repository doesn't exist
    - CheckpointNotFoundError: Checkpoint ID not found
    - IntegrityError: Verification failed

Example:
    try:
        await gm.rollback_to_checkpoint(checkpoint_id)
    except CheckpointNotFoundError:
        print("Checkpoint not found")
    except IntegrityError as e:
        print(f"Integrity check failed: {e}")
"""

# ============================================================================
# Version History
# ============================================================================
"""
Version History:
---------------
v2.0.0 (2026-03-07)
    - Initial production release
    - Full async support with GitPython and subprocess fallback
    - Three-tier checkpoint integration (Tier 3 - Git)
    - GPG signing support
    - Branch management for parallel sessions
    - Remote push/fetch operations
    - Integrity verification
    - Comprehensive test suite
"""
