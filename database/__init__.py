"""MasterBuilder7 Database Package.

This package provides database models, migrations, and utilities for the
MasterBuilder7 agent orchestration system.

Usage:
    from database import Agent, Project, get_session
    
    # Create a session
    session = get_session(database_url)
    
    # Query agents
    agents = session.query(Agent).all()
"""

from .models import (
    # Base
    Base,
    
    # Models
    Agent,
    Project,
    Build,
    Task,
    Checkpoint,
    AgentState,
    ConsensusRecord,
    CostTracking,
    HealthMetric,
    Message,
    
    # Enums
    AgentStatus,
    AgentType,
    BuildStatus,
    TaskPriority,
    TaskStatus,
    CheckpointTier,
    ConsensusStatus,
    MessageType,
    HealthStatus,
    ProjectStatus,
    
    # Utilities
    create_database_engine,
    init_database,
    get_session,
)

__version__ = "1.0.0"
__all__ = [
    # Base
    "Base",
    
    # Models
    "Agent",
    "Project",
    "Build",
    "Task",
    "Checkpoint",
    "AgentState",
    "ConsensusRecord",
    "CostTracking",
    "HealthMetric",
    "Message",
    
    # Enums
    "AgentStatus",
    "AgentType",
    "BuildStatus",
    "TaskPriority",
    "TaskStatus",
    "CheckpointTier",
    "ConsensusStatus",
    "MessageType",
    "HealthStatus",
    "ProjectStatus",
    
    # Utilities
    "create_database_engine",
    "init_database",
    "get_session",
]
