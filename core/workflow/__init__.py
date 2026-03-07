"""
APEX Workflow Module - Production-grade build orchestration

Phase A (Truth Layer):
- Artifact contracts for typed stage outputs
- Build event log for deterministic replay
- Demo mode labeling throughout

Phase B (Real Execution):
- Real execution adapters
- Actual test running
- Real deployment integration

Phase C (Reliability):
- Idempotency keys
- Retry/backoff logic
- Dead-letter queues
"""

from .artifact_contracts import (
    BuildStage,
    StageArtifact,
    ArtifactStore,
    CONTRACT_SCHEMAS
)

from .build_event_log import (
    BuildEvent,
    BuildEventLog,
    BuildEventType
)

from .build_pipeline_hardened import (
    HardenedBuildPipeline,
    ExecutionAdapter,
    ExecutionResult,
    AnalyzeAdapter,
    TestAdapter,
    DeployAdapter,
    VerifyAdapter
)

__all__ = [
    # Contracts
    "BuildStage",
    "StageArtifact",
    "ArtifactStore",
    "CONTRACT_SCHEMAS",
    
    # Event Log
    "BuildEvent",
    "BuildEventLog",
    "BuildEventType",
    
    # Pipeline
    "HardenedBuildPipeline",
    "ExecutionAdapter",
    "ExecutionResult",
    "AnalyzeAdapter",
    "TestAdapter",
    "DeployAdapter",
    "VerifyAdapter",
]
