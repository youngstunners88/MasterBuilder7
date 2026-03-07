"""
APEX Agents Module
Dynamic sub-agent spawning and lifecycle management.
"""

from .subagent_spawner import (
    # Core classes
    SubAgentSpawner,
    SubAgentConfig,
    SpawnedAgent,
    
    # Enums
    SubAgentType,
    AgentStatus,
    
    # Exceptions
    BudgetExceededError,
    MaxAgentsError,
    SkillNotFoundError,
    
    # Registry
    SKILL_REGISTRY,
)

__version__ = "1.0.0"
__all__ = [
    "SubAgentSpawner",
    "SubAgentConfig", 
    "SpawnedAgent",
    "SubAgentType",
    "AgentStatus",
    "BudgetExceededError",
    "MaxAgentsError",
    "SkillNotFoundError",
    "SKILL_REGISTRY",
]
