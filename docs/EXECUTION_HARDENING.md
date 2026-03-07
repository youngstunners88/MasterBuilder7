# MasterBuilder7 - Execution Hardening Guide

## Overview

This document details the conversion from **simulated prototype** to **production-grade execution integrity** for the APEX (Automated Production EXecution) system.

## Phase A: Truth Layer ✅ COMPLETE

### Goals
1. **Explicit demo_mode labeling** - No hidden simulations
2. **Artifact contracts** - Typed schemas for all stage outputs
3. **Deterministic event log** - Append-only log for replay and audit
4. **Security hardening** - No wildcard CORS, idempotency keys

### Files Created/Modified

#### 1. Core Workflow (`core/workflow/`)

**`artifact_contracts.py`** - NEW
- Typed schemas for all 7 build stages (analyze, plan, build, test, deploy, verify, evolve)
- `StageArtifact` dataclass with explicit `simulation` flag
- `ArtifactStore` for saving/loading artifacts with versioning
- JSON Schema validation for each stage output

**`build_event_log.py`** - NEW
- `BuildEvent` - Immutable event records
- `BuildEventLog` - Append-only SQLite + file logging
- Event types: BUILD_STARTED, STAGE_STARTED, STAGE_COMPLETED, STAGE_FAILED, ARTIFACT_CREATED, RETRY_ATTEMPTED, BUILD_COMPLETED, BUILD_CANCELLED
- `replay_build()` - Reconstruct build state from events
- `verify_determinism()` - Validate replay produces same results

**`build_pipeline_hardened.py`** - NEW
- `HardenedBuildPipeline` class
- Real execution adapters (no `asyncio.sleep()`):
  - `AnalyzeAdapter` - Real repo inspection for stack detection
  - `TestAdapter` - Actual test execution (pytest, jest)
  - `DeployAdapter` - Real deployment or explicit simulation
  - `VerifyAdapter` - Real health check probes
- All artifacts include `simulation` flag
- Full event logging

**`__init__.py`** - UPDATED
- Exports all new hardened components

#### 2. API Server (`api/`)

**`server_hardened.ts`** - NEW
- CORS with explicit allowed origins (NO wildcard in production)
- Idempotency-Key required for mutating requests (POST /deploy, POST /build)
- UUID v4 validation for idempotency keys
- Security headers (X-Frame-Options, X-Content-Type-Options, HSTS)
- Clear simulation flags in all responses

### Migration from Simulated to Hardened

#### Before (Simulated)
```python
# build_pipeline.py - SIMULATED
await asyncio.sleep(0.5)  # Fake delay
context.stack_analysis = {
    "stack": "capacitor-react-fastapi",  # HARDCODED
    "automation_potential": 0.70,
}
```

#### After (Hardened)
```python
# build_pipeline_hardened.py - REAL
class AnalyzeAdapter(ExecutionAdapter):
    async def execute(self, context: Dict[str, Any]) -> ExecutionResult:
        # Real file system inspection
        path = Path(repo_path)
        files = list(path.iterdir())
        stack_detected = self._detect_stack(files)  # ACTUAL detection
        
        return ExecutionResult(
            success=True,
            payload={
                "stack": stack_detected,
                "automation_potential": calculate_potential(stack_detected),
                "demo_mode": self.demo_mode  # EXPLICIT flag
            },
            ...
        )
```

### Security Changes

#### CORS Configuration

**Before (Insecure):**
```typescript
const headers = {
  "Access-Control-Allow-Origin": "*",  // DANGEROUS
};
```

**After (Hardened):**
```typescript
const ALLOWED_ORIGINS = process.env.APEX_ALLOWED_ORIGINS
  ? process.env.APEX_ALLOWED_ORIGINS.split(",")
  : NODE_ENV === "production"
    ? []  // Block all if not configured
    : ["http://localhost:3000", "http://localhost:5173"];

function isOriginAllowed(origin: string | null): boolean {
  if (NODE_ENV !== "production") return true;
  if (ALLOWED_ORIGINS.length === 0) return false;
  return ALLOWED_ORIGINS.includes(origin);
}
```

#### Idempotency Keys

All mutating endpoints now require `Idempotency-Key` header:

```bash
# Valid request
curl -X POST http://localhost:3000/build \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000" \
  -d '{"project_name": "my-app", "repo_path": "."}'

# Invalid - missing idempotency key
curl -X POST http://localhost:3000/build \
  -H "Content-Type: application/json" \
  -d '{"project_name": "my-app"}'
# Response: 400 Bad Request
# { "error": "Missing Idempotency-Key header" }
```

### Artifact Schema Example

```json
{
  "artifact_id": "art-analyze-550e8400-e29b",
  "stage": "analyze",
  "build_id": "build-20250307-121530",
  "version": 1,
  "timestamp": "2026-03-07T12:15:30.123456Z",
  "producer_agent": "analyze",
  "payload": {
    "stack": "react-vite-web",
    "files_found": ["package.json", "vite.config.ts", "src/"],
    "automation_potential": 0.85
  },
  "simulation": false,
  "signature": "sha256:abc123...",
  "contract_version": "1.0"
}
```

### Event Log Example

```json
{"event_id": "evt-550e8400-e29b", "timestamp": "2026-03-07T12:15:30Z", "build_id": "build-20250307-121530", "event_type": "build_started", "previous_state": null, "new_state": "started", "correlation_id": "corr-abc123", "actor": "build-pipeline", "payload": {"project_name": "my-app", "demo_mode": false}}
{"event_id": "evt-661f9511-f3ac", "timestamp": "2026-03-07T12:15:31Z", "build_id": "build-20250307-121530", "event_type": "stage_started", "previous_state": "started", "new_state": "analyze_running", "correlation_id": "corr-abc123", "actor": "build-pipeline", "payload": {"stage": "analyze"}}
{"event_id": "evt-772g0622-g4bd", "timestamp": "2026-03-07T12:15:32Z", "build_id": "build-20250307-121530", "event_type": "artifact_created", "previous_state": "analyze_running", "new_state": "analyze_artifact_created", "correlation_id": "corr-abc123", "actor": "build-pipeline", "payload": {"artifact_id": "art-analyze-550e8400-e29b", "stage": "analyze"}}
{"event_id": "evt-883h1733-h5ce", "timestamp": "2026-03-07T12:15:33Z", "build_id": "build-20250307-121530", "event_type": "stage_completed", "previous_state": "analyze_artifact_created", "new_state": "analyze_completed", "correlation_id": "corr-abc123", "actor": "build-pipeline", "payload": {"stage": "analyze", "duration": 1.234, "artifact_id": "art-analyze-550e8400-e29b"}}
```

## Phase B: Real Execution (PLANNED)

### Goals
1. Replace remaining simulated adapters with real implementations
2. Real repository inspection (done in Phase A)
3. Real test execution (done in Phase A)
4. Real deployment integration (AWS, GCP, Azure, Netlify, Vercel)
5. Real health check probes

### Adapters to Implement

#### BuildAdapter
- Execute actual build commands (npm build, cargo build, etc.)
- Capture real build artifacts
- Stream build logs

#### DeployAdapter Extensions
- AWS (ECS, Lambda, S3)
- GCP (Cloud Run, App Engine)
- Netlify API integration
- Vercel API integration

### Integration Points

```python
# Example: AWS deployment
class AWSDeployAdapter(ExecutionAdapter):
    async def execute(self, context: Dict) -> ExecutionResult:
        # Real AWS SDK calls
        # Create ECS task definition
        # Deploy to Fargate
        # Return actual deployment URL
        pass

# Example: Netlify deployment  
class NetlifyDeployAdapter(ExecutionAdapter):
    async def execute(self, context: Dict) -> ExecutionResult:
        # Netlify API calls
        # Upload build artifacts
        # Return live URL
        pass
```

## Phase C: Reliability (PLANNED)

### Goals
1. Exponential backoff with jitter
2. Dead-letter queues for failed builds
3. Comprehensive metrics and SLOs
4. Circuit breakers
5. Graceful degradation

### Components

#### RetryManager
```python
class RetryManager:
    def __init__(self, max_retries=3, base_delay=1.0, max_delay=60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    async def execute_with_retry(self, operation: Callable) -> Any:
        for attempt in range(self.max_retries):
            try:
                return await operation()
            except RetryableError as e:
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                delay += random.uniform(0, delay * 0.1)  # Jitter
                await asyncio.sleep(delay)
        raise MaxRetriesExceeded()
```

#### MetricsCollector
```python
class MetricsCollector:
    def record_stage_duration(self, stage: BuildStage, duration: float):
        # Prometheus metrics
        pass
    
    def record_build_outcome(self, success: bool, error_type: str = None):
        pass
    
    def record_retry(self, stage: BuildStage, attempt: int):
        pass
```

#### DeadLetterQueue
```python
class DeadLetterQueue:
    async def enqueue(self, build_id: str, error: Exception, context: Dict):
        # Store failed builds for manual review
        pass
    
    async def reprocess(self, build_id: str):
        # Retry failed build
        pass
```

## Testing

### Unit Tests

```bash
# Run tests for new modules
python -m pytest tests/test_artifact_contracts.py -v
python -m pytest tests/test_build_event_log.py -v
python -m pytest tests/test_build_pipeline_hardened.py -v
```

### Integration Tests

```bash
# Test hardened API server
cd api && bun test server_hardened.test.ts

# Test end-to-end build pipeline
python -m pytest tests/integration/test_hardened_pipeline.py -v
```

### Determinism Verification

```python
# Verify replay produces same results
events = event_log.get_events(build_id)
original_state = pipeline.get_final_state(build_id)
replayed_state = event_log.replay_build(build_id)
assert event_log.verify_determinism(build_id, original_state)
```

## Environment Variables

### Phase A

```bash
# Demo mode (defaults to false in production)
export APEX_DEMO_MODE=false

# CORS allowed origins (comma-separated)
export APEX_ALLOWED_ORIGINS="https://app.example.com,https://admin.example.com"

# Database and log paths
export APEX_DB_PATH="./orchestrator.db"
export APEX_LOG_PATH="./logs"

# API security
export APEX_API_SECRET="your-secret-key"
```

### Phase B

```bash
# AWS credentials (if using AWS deployment)
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_REGION="us-east-1"

# Netlify token
export NETLIFY_TOKEN="..."

# Vercel token
export VERCEL_TOKEN="..."
```

### Phase C

```bash
# Retry configuration
export APEX_MAX_RETRIES=3
export APEX_RETRY_BASE_DELAY=1.0
export APEX_RETRY_MAX_DELAY=60.0

# Metrics
export APEX_METRICS_ENABLED=true
export APEX_METRICS_PORT=9090
```

## Migration Checklist

### From Old Pipeline to Hardened

- [ ] Replace `build_pipeline.py` imports with `build_pipeline_hardened`
- [ ] Add `demo_mode` parameter or env var
- [ ] Update API server to use `server_hardened.ts`
- [ ] Configure `APEX_ALLOWED_ORIGINS` for production
- [ ] Ensure all clients send `Idempotency-Key` header
- [ ] Run determinism tests
- [ ] Verify artifact schemas
- [ ] Check event log replay

## Summary

| Aspect | Before | After (Phase A) | After (Phase B) | After (Phase C) |
|--------|--------|-----------------|-----------------|-----------------|
| **Simulation** | Hidden | Explicit `demo_mode` flag | Real execution | Real execution |
| **Artifacts** | None | Typed schemas + validation | Real build outputs | Real outputs |
| **Event Log** | None | Append-only SQLite + file | Same + metrics | Same + DLQ |
| **CORS** | Wildcard `*` | Origin whitelist | Origin whitelist | Origin whitelist |
| **Idempotency** | None | Required UUID keys | Required + caching | Required + caching |
| **Retry** | None | None | Basic retry | Exponential backoff |
| **Monitoring** | None | None | Prometheus metrics | Full SLO tracking |

## Next Steps

1. **Deploy Phase A** to staging
2. **Update clients** to send Idempotency-Key headers
3. **Configure CORS** allowed origins
4. **Implement Phase B** real deployment adapters
5. **Implement Phase C** reliability features
6. **Load test** hardened pipeline
7. **Production rollout**

---

**Version:** 2.0.0-hardened-phase-a  
**Date:** 2026-03-07  
**Status:** Phase A Complete ✅
