"""SQLAlchemy models for MasterBuilder7 database.

This module defines all database models for the MasterBuilder7 agent system,
including agents, builds, tasks, checkpoints, and related entities.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy import (
    Column, String, Text, Integer, BigInteger, Boolean, DateTime, 
    ForeignKey, Numeric, Enum, ARRAY, JSON, UniqueConstraint, 
    CheckConstraint, Index, create_engine
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship, Session
from sqlalchemy.sql import func

# Create base class
Base = declarative_base()


# ============================================================================
# ENUM DEFINITIONS
# ============================================================================

import enum


class AgentStatus(str, enum.Enum):
    """Agent status enumeration."""
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class AgentType(str, enum.Enum):
    """Agent type enumeration (8 specialist agents)."""
    META_ROUTER = "meta_router"
    PLANNING = "planning"
    FRONTEND = "frontend"
    BACKEND = "backend"
    TESTING = "testing"
    DEVOPS = "devops"
    RELIABILITY = "reliability"
    EVOLUTION = "evolution"


class BuildStatus(str, enum.Enum):
    """Build status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"


class TaskPriority(str, enum.Enum):
    """Task priority enumeration."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BACKGROUND = "background"


class TaskStatus(str, enum.Enum):
    """Task status enumeration."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class CheckpointTier(str, enum.Enum):
    """Checkpoint tier enumeration (3-tier system)."""
    TIER_1 = "tier_1"  # Quick checkpoint (every 30s)
    TIER_2 = "tier_2"  # Standard checkpoint (on stage completion)
    TIER_3 = "tier_3"  # Deep checkpoint (on build success)


class ConsensusStatus(str, enum.Enum):
    """Consensus status enumeration."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIE = "tie"
    EXPIRED = "expired"


class MessageType(str, enum.Enum):
    """Message type enumeration."""
    COMMAND = "command"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    HEARTBEAT = "heartbeat"
    ALERT = "alert"
    LOG = "log"


class HealthStatus(str, enum.Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ProjectStatus(str, enum.Enum):
    """Project status enumeration."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    PAUSED = "paused"
    DELETED = "deleted"


# ============================================================================
# MODELS
# ============================================================================

class Agent(Base):
    """Agent registration and status model.
    
    Represents one of the 8 specialist agents in the APEX pipeline.
    """
    __tablename__ = 'agents'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    agent_type = Column(Enum(AgentType), nullable=False)
    status = Column(Enum(AgentStatus), nullable=False, default=AgentStatus.IDLE)
    version = Column(String(20), nullable=False, default='1.0.0')
    
    # Capabilities and configuration
    capabilities = Column(JSONB, nullable=False, default=list)
    config = Column(JSONB, nullable=False, default=dict)
    
    # Resource limits
    max_concurrent_tasks = Column(Integer, nullable=False, default=5)
    memory_limit_mb = Column(Integer, nullable=True)
    cpu_limit_percent = Column(Integer, nullable=True)
    
    # Status tracking
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)
    last_task_at = Column(DateTime(timezone=True), nullable=True)
    task_count = Column(Integer, nullable=False, default=0)
    success_rate = Column(Numeric(5, 2), nullable=False, default=Decimal('100.00'))
    
    # Cost tracking
    total_cost_usd = Column(Numeric(10, 4), nullable=False, default=Decimal('0.0000'))
    cost_per_task_avg = Column(Numeric(8, 4), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    tasks = relationship("Task", back_populates="agent", lazy='dynamic')
    checkpoints = relationship("Checkpoint", back_populates="agent", lazy='dynamic')
    states = relationship("AgentState", back_populates="agent", lazy='dynamic')
    costs = relationship("CostTracking", back_populates="agent", lazy='dynamic')
    health_metrics = relationship("HealthMetric", back_populates="agent", lazy='dynamic')
    
    __table_args__ = (
        CheckConstraint('success_rate >= 0 AND success_rate <= 100'),
        CheckConstraint('max_concurrent_tasks > 0'),
    )
    
    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name='{self.name}', type={self.agent_type}, status={self.status})>"


class Project(Base):
    """Project configuration model.
    
    Represents a software project being managed by MasterBuilder7.
    """
    __tablename__ = 'projects'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Repository info
    repo_url = Column(String(500), nullable=True)
    repo_branch = Column(String(100), nullable=False, default='main')
    
    # Stack information
    stack_detected = Column(JSONB, nullable=True)
    stack_config = Column(JSONB, nullable=False, default=dict)
    
    # Build configuration
    build_config = Column(JSONB, nullable=False, default=dict)
    env_vars = Column(JSONB, nullable=True)
    
    # Status
    status = Column(Enum(ProjectStatus), nullable=False, default=ProjectStatus.ACTIVE)
    
    # Statistics
    total_builds = Column(Integer, nullable=False, default=0)
    successful_builds = Column(Integer, nullable=False, default=0)
    failed_builds = Column(Integer, nullable=False, default=0)
    
    # Cost tracking
    total_cost_usd = Column(Numeric(12, 4), nullable=False, default=Decimal('0.0000'))
    budget_limit_usd = Column(Numeric(12, 4), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    created_by = Column(UUID(as_uuid=True), nullable=True)
    
    # Relationships
    builds = relationship("Build", back_populates="project", lazy='dynamic', cascade='all, delete-orphan')
    
    __table_args__ = (
        CheckConstraint('budget_limit_usd IS NULL OR budget_limit_usd > 0'),
    )
    
    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name='{self.name}', slug='{self.slug}')>"


class Build(Base):
    """Build tracking model.
    
    Represents a single build execution within a project.
    """
    __tablename__ = 'builds'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    
    # Build info
    build_number = Column(Integer, nullable=False)
    git_commit = Column(String(40), nullable=True)
    git_branch = Column(String(100), nullable=True)
    git_tag = Column(String(100), nullable=True)
    
    # Status
    status = Column(Enum(BuildStatus), nullable=False, default=BuildStatus.PENDING)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Pipeline stages
    stages = Column(JSONB, nullable=False, default=list)
    current_stage = Column(String(50), nullable=True)
    
    # Outputs
    outputs = Column(JSONB, nullable=True)
    artifacts = Column(JSONB, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    error_details = Column(JSONB, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    parent_build_id = Column(UUID(as_uuid=True), ForeignKey('builds.id', ondelete='SET NULL'), nullable=True)
    
    # Cost tracking
    estimated_cost_usd = Column(Numeric(8, 4), nullable=True)
    actual_cost_usd = Column(Numeric(8, 4), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    triggered_by = Column(UUID(as_uuid=True), nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="builds")
    tasks = relationship("Task", back_populates="build", lazy='dynamic', cascade='all, delete-orphan')
    checkpoints = relationship("Checkpoint", back_populates="build", lazy='dynamic', cascade='all, delete-orphan')
    costs = relationship("CostTracking", back_populates="build", lazy='dynamic')
    consensus_records = relationship("ConsensusRecord", back_populates="build", lazy='dynamic')
    parent_build = relationship("Build", remote_side=[id], backref='child_builds')
    
    __table_args__ = (
        UniqueConstraint('project_id', 'build_number'),
    )
    
    def __repr__(self) -> str:
        return f"<Build(id={self.id}, project_id={self.project_id}, build_number={self.build_number}, status={self.status})>"


class Task(Base):
    """Task queue persistence model.
    
    Represents a single task to be executed by an agent.
    """
    __tablename__ = 'tasks'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    build_id = Column(UUID(as_uuid=True), ForeignKey('builds.id', ondelete='CASCADE'), nullable=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.id', ondelete='SET NULL'), nullable=True)
    
    # Task info
    task_type = Column(String(50), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(Enum(TaskPriority), nullable=False, default=TaskPriority.MEDIUM)
    
    # Execution
    status = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    input_data = Column(JSONB, nullable=True)
    output_data = Column(JSONB, nullable=True)
    result = Column(JSONB, nullable=True)
    
    # Timing
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Retry logic
    max_retries = Column(Integer, nullable=False, default=3)
    retry_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    
    # Dependencies
    depends_on = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    
    # Cost tracking
    estimated_cost_usd = Column(Numeric(8, 4), nullable=True)
    actual_cost_usd = Column(Numeric(8, 4), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    build = relationship("Build", back_populates="tasks")
    agent = relationship("Agent", back_populates="tasks")
    checkpoints = relationship("Checkpoint", back_populates="task", lazy='dynamic')
    states = relationship("AgentState", back_populates="task", lazy='dynamic')
    costs = relationship("CostTracking", back_populates="task", lazy='dynamic')
    consensus_records = relationship("ConsensusRecord", back_populates="task", lazy='dynamic')
    
    def __repr__(self) -> str:
        return f"<Task(id={self.id}, name='{self.name}', type={self.task_type}, status={self.status})>"


class Checkpoint(Base):
    """3-tier checkpoint data model.
    
    Represents a snapshot of build state for rollback capability.
    """
    __tablename__ = 'checkpoints'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    build_id = Column(UUID(as_uuid=True), ForeignKey('builds.id', ondelete='CASCADE'), nullable=False)
    task_id = Column(UUID(as_uuid=True), ForeignKey('tasks.id', ondelete='SET NULL'), nullable=True)
    
    # Checkpoint info
    tier = Column(Enum(CheckpointTier), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Snapshot data
    snapshot_data = Column(JSONB, nullable=False)
    file_manifest = Column(JSONB, nullable=True)
    
    # Storage
    storage_path = Column(String(500), nullable=True)
    storage_size_bytes = Column(BigInteger, nullable=True)
    checksum = Column(String(64), nullable=True)
    
    # Restoration
    can_rollback = Column(Boolean, nullable=False, default=True)
    rolled_back_at = Column(DateTime(timezone=True), nullable=True)
    rolled_back_to = Column(UUID(as_uuid=True), ForeignKey('checkpoints.id', ondelete='SET NULL'), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    created_by_agent = Column(UUID(as_uuid=True), ForeignKey('agents.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    build = relationship("Build", back_populates="checkpoints")
    task = relationship("Task", back_populates="checkpoints")
    agent = relationship("Agent", back_populates="checkpoints")
    states = relationship("AgentState", back_populates="checkpoint", lazy='dynamic')
    
    def __repr__(self) -> str:
        return f"<Checkpoint(id={self.id}, build_id={self.build_id}, tier={self.tier}, name='{self.name}')>"


class AgentState(Base):
    """Agent state snapshot model.
    
    Captures agent memory and context for recovery.
    """
    __tablename__ = 'agent_states'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.id', ondelete='CASCADE'), nullable=False)
    task_id = Column(UUID(as_uuid=True), ForeignKey('tasks.id', ondelete='SET NULL'), nullable=True)
    checkpoint_id = Column(UUID(as_uuid=True), ForeignKey('checkpoints.id', ondelete='SET NULL'), nullable=True)
    
    # State data
    state_type = Column(String(50), nullable=False)
    state_data = Column(JSONB, nullable=False)
    memory_state = Column(JSONB, nullable=True)
    context_window = Column(JSONB, nullable=True)
    
    # Performance
    tokens_used = Column(Integer, nullable=True)
    tokens_input = Column(Integer, nullable=True)
    tokens_output = Column(Integer, nullable=True)
    
    # Cost
    cost_usd = Column(Numeric(8, 4), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    agent = relationship("Agent", back_populates="states")
    task = relationship("Task", back_populates="states")
    checkpoint = relationship("Checkpoint", back_populates="states")
    
    def __repr__(self) -> str:
        return f"<AgentState(id={self.id}, agent_id={self.agent_id}, type='{self.state_type}')>"


class ConsensusRecord(Base):
    """Consensus voting record model.
    
    Tracks 3-verifier consensus decisions.
    """
    __tablename__ = 'consensus_records'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False)
    build_id = Column(UUID(as_uuid=True), ForeignKey('builds.id', ondelete='SET NULL'), nullable=True)
    
    # Consensus info
    decision_type = Column(String(50), nullable=False)
    subject = Column(Text, nullable=False)
    
    # Voting
    required_votes = Column(Integer, nullable=False, default=3)
    votes_received = Column(Integer, nullable=False, default=0)
    status = Column(Enum(ConsensusStatus), nullable=False, default=ConsensusStatus.PENDING)
    
    # Results
    votes = Column(JSONB, nullable=False, default=list)
    final_decision = Column(Boolean, nullable=True)
    confidence_score = Column(Numeric(5, 2), nullable=True)
    
    # Resolution
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Timing
    timeout_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    task = relationship("Task", back_populates="consensus_records")
    build = relationship("Build", back_populates="consensus_records")
    
    __table_args__ = (
        CheckConstraint('required_votes >= 2'),
        CheckConstraint('confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 100)'),
    )
    
    def __repr__(self) -> str:
        return f"<ConsensusRecord(id={self.id}, task_id={self.task_id}, status={self.status})>"


class CostTracking(Base):
    """Cost tracking model.
    
    Tracks detailed costs per agent/AI operation.
    """
    __tablename__ = 'cost_tracking'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.id', ondelete='CASCADE'), nullable=False)
    task_id = Column(UUID(as_uuid=True), ForeignKey('tasks.id', ondelete='SET NULL'), nullable=True)
    build_id = Column(UUID(as_uuid=True), ForeignKey('builds.id', ondelete='SET NULL'), nullable=True)
    
    # Cost breakdown
    ai_provider = Column(String(50), nullable=False)
    ai_model = Column(String(100), nullable=False)
    
    # Token usage
    tokens_input = Column(Integer, nullable=False, default=0)
    tokens_output = Column(Integer, nullable=False, default=0)
    tokens_total = Column(Integer, nullable=False, default=0)
    
    # Pricing
    input_cost_per_1k = Column(Numeric(8, 6), nullable=False)
    output_cost_per_1k = Column(Numeric(8, 6), nullable=False)
    
    # Calculated costs
    input_cost_usd = Column(Numeric(10, 6), nullable=False)
    output_cost_usd = Column(Numeric(10, 6), nullable=False)
    total_cost_usd = Column(Numeric(10, 6), nullable=False)
    
    # Additional costs
    api_cost_usd = Column(Numeric(10, 6), nullable=False, default=Decimal('0'))
    storage_cost_usd = Column(Numeric(10, 6), nullable=False, default=Decimal('0'))
    compute_cost_usd = Column(Numeric(10, 6), nullable=False, default=Decimal('0'))
    
    # Time tracking
    duration_seconds = Column(Integer, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    agent = relationship("Agent", back_populates="costs")
    task = relationship("Task", back_populates="costs")
    build = relationship("Build", back_populates="costs")
    
    def __repr__(self) -> str:
        return f"<CostTracking(id={self.id}, agent_id={self.agent_id}, provider='{self.ai_provider}', cost={self.total_cost_usd})>"


class HealthMetric(Base):
    """Health check data model.
    
    Records system and agent health metrics.
    """
    __tablename__ = 'health_metrics'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.id', ondelete='CASCADE'), nullable=True)
    service_name = Column(String(100), nullable=False)
    
    # Health status
    status = Column(Enum(HealthStatus), nullable=False)
    check_type = Column(String(50), nullable=False)
    
    # Metrics
    response_time_ms = Column(Integer, nullable=True)
    cpu_percent = Column(Numeric(5, 2), nullable=True)
    memory_percent = Column(Numeric(5, 2), nullable=True)
    disk_percent = Column(Numeric(5, 2), nullable=True)
    
    # Custom metrics
    metrics = Column(JSONB, nullable=True)
    
    # Details
    message = Column(Text, nullable=True)
    details = Column(JSONB, nullable=True)
    
    # Alerting
    alert_level = Column(String(20), nullable=True)
    alert_sent = Column(Boolean, nullable=False, default=False)
    
    # Metadata
    checked_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    agent = relationship("Agent", back_populates="health_metrics")
    
    __table_args__ = (
        CheckConstraint('(cpu_percent IS NULL OR (cpu_percent >= 0 AND cpu_percent <= 100)) AND (memory_percent IS NULL OR (memory_percent >= 0 AND memory_percent <= 100)) AND (disk_percent IS NULL OR (disk_percent >= 0 AND disk_percent <= 100))'),
    )
    
    def __repr__(self) -> str:
        return f"<HealthMetric(id={self.id}, service='{self.service_name}', status={self.status})>"


class Message(Base):
    """Agent communication log model.
    
    Records all inter-agent communication.
    """
    __tablename__ = 'messages'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Sender/Receiver
    sender_id = Column(UUID(as_uuid=True), ForeignKey('agents.id', ondelete='SET NULL'), nullable=True)
    sender_type = Column(String(20), nullable=False)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey('agents.id', ondelete='SET NULL'), nullable=True)
    recipient_type = Column(String(20), nullable=False)
    
    # Message content
    message_type = Column(Enum(MessageType), nullable=False)
    channel = Column(String(50), nullable=True)
    priority = Column(Integer, nullable=False, default=5)
    
    # Content
    subject = Column(String(200), nullable=True)
    content = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=True)
    
    # Status
    is_read = Column(Boolean, nullable=False, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    
    # Threading
    thread_id = Column(UUID(as_uuid=True), ForeignKey('messages.id', ondelete='SET NULL'), nullable=True)
    reply_to = Column(UUID(as_uuid=True), ForeignKey('messages.id', ondelete='SET NULL'), nullable=True)
    
    # Context
    context = Column(JSONB, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        CheckConstraint('priority >= 1 AND priority <= 10'),
    )
    
    def __repr__(self) -> str:
        return f"<Message(id={self.id}, type={self.message_type}, sender={self.sender_id}, recipient={self.recipient_id})>"


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_database_engine(database_url: str):
    """Create a SQLAlchemy engine for the database.
    
    Args:
        database_url: PostgreSQL connection URL
        
    Returns:
        SQLAlchemy engine instance
    """
    return create_engine(database_url)


def init_database(engine):
    """Initialize the database by creating all tables.
    
    Args:
        engine: SQLAlchemy engine instance
    """
    Base.metadata.create_all(engine)


def get_session(engine) -> Session:
    """Get a new database session.
    
    Args:
        engine: SQLAlchemy engine instance
        
    Returns:
        New SQLAlchemy session
    """
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()
