"""
APEX - Autonomous Programming & Execution Engine

A comprehensive agent-based build orchestration and code intelligence system.

Usage:
    from apex import main
    main.cli()  # Run CLI

    # Or programmatically:
    from apex.main import apex_state, app
    await apex_state.initialize()
"""

__version__ = "2.0.0"
__author__ = "APEX Core Team"

# Make main components available at package level
try:
    from .main import cli, main, apex_state, app, APEXConfig
except ImportError:
    # Fallback when imports fail
    pass

# Integration layer
try:
    from .integration import (
        APEXIntegration,
        APEXConfig as IntegrationConfig,
        CheckpointResult,
        ComponentHealth,
        ServiceStatus,
        MetricsCollector,
        CircuitBreaker,
        run_integration_test,
        run_performance_benchmark,
    )
except ImportError:
    pass

__all__ = [
    "cli",
    "main", 
    "apex_state",
    "app",
    "APEXConfig",
    "__version__",
    # Integration layer
    "APEXIntegration",
    "IntegrationConfig",
    "CheckpointResult",
    "ComponentHealth",
    "ServiceStatus",
    "MetricsCollector",
    "CircuitBreaker",
    "run_integration_test",
    "run_performance_benchmark",
]
