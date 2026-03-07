"""
APEX Agents Module
Dynamic sub-agent spawning, lifecycle management, and agent-to-agent communication.
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

from .agent_protocol import (
    # Core classes
    AgentMessage,
    AgentBus,
    AgentCoordinator,
    MessageDelivery,
    SQLiteMessageStore,
    
    # Enums
    MessageType,
    MessagePriority,
    DeliveryStatus,
    
    # Convenience functions
    create_agent_bus,
    send_task_request,
    broadcast_task_completion,
)

from .health_monitor import (
    # Core classes
    HealthMonitor,
    AgentHealth,
    Alert,
    SystemMetrics,
    
    # Enums
    HealthStatus,
    AlertSeverity,
    AlertChannel,
)

from .shared_state import (
    # Core class
    SharedStateManager,
    SQLiteStateBackend,
    
    # Data classes
    StateValue,
    StateLock,
    StateSnapshot,
    StateEvent,
    BuildProgress,
    AgentStatusInfo,
    
    # Enums
    StateType,
    ConflictResolutionStrategy,
    StateEventType,
    LockStatus,
    
    # Convenience functions
    create_shared_state_manager,
)

from .task_queue import (
    # Core classes
    TaskQueue,
    Task,
    Worker,
    WorkerPool,
    TaskProgress,
    QueueConfig,
    TaskQueueStats,
    
    # Enums
    TaskPriority,
    TaskStatus,
    WorkerStatus,
    
    # Fallback
    SQLiteTaskStore,
    
    # Decorator
    task_handler,
    
    # Factory functions
    create_task_queue,
    create_worker_pool,
)

__version__ = "1.0.0"
__all__ = [
    # SubAgent Spawner
    "SubAgentSpawner",
    "SubAgentConfig", 
    "SpawnedAgent",
    "SubAgentType",
    "AgentStatus",
    "BudgetExceededError",
    "MaxAgentsError",
    "SkillNotFoundError",
    "SKILL_REGISTRY",
    
    # Agent Protocol
    "AgentMessage",
    "AgentBus",
    "AgentCoordinator",
    "MessageDelivery",
    "SQLiteMessageStore",
    "MessageType",
    "MessagePriority",
    "DeliveryStatus",
    "create_agent_bus",
    "send_task_request",
    "broadcast_task_completion",
    
    # Health Monitoring
    "HealthMonitor",
    "AgentHealth",
    "Alert",
    "SystemMetrics",
    "HealthStatus",
    "AlertSeverity",
    "AlertChannel",
    
    # Shared State Management
    "SharedStateManager",
    "SQLiteStateBackend",
    "StateValue",
    "StateLock",
    "StateSnapshot",
    "StateEvent",
    "BuildProgress",
    "AgentStatusInfo",
    "StateType",
    "ConflictResolutionStrategy",
    "StateEventType",
    "LockStatus",
    "create_shared_state_manager",
    
    # Task Queue
    "TaskQueue",
    "Task",
    "Worker",
    "WorkerPool",
    "TaskProgress",
    "QueueConfig",
    "TaskQueueStats",
    "TaskPriority",
    "TaskStatus",
    "WorkerStatus",
    "SQLiteTaskStore",
    "task_handler",
    "create_task_queue",
    "create_worker_pool",
]
