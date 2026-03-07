# APEX Integration Layer

The main Integration Layer for MasterBuilder7 that ties together all infrastructure components (Redis, PostgreSQL, Git, Kimi API, n8n) with the agent layer.

## Overview

The `APEXIntegration` class serves as the **single entry point** for all APEX operations, providing:

- **Unified Component Management**: Initializes and manages Redis, PostgreSQL, Git, Kimi API, n8n, Pattern Database, and A/B Testing Framework
- **Three-Tier Checkpoint System**: Hot (Redis), Warm (PostgreSQL), Cold (Git)
- **Event-Driven Architecture**: Automatic event wiring between components
- **Circuit Breakers**: Resilient error handling with automatic recovery
- **Distributed Tracing**: Comprehensive metrics and observability
- **Graceful Degradation**: Services can fail without bringing down the entire system

## Quick Start

```python
import asyncio
from apex.integration import APEXIntegration, APEXConfig

async def main():
    # Load configuration from environment
    config = APEXConfig.from_env()
    
    # Or load from file
    # config = APEXConfig.from_file('/path/to/config.yaml')
    
    # Initialize integration
    apex = APEXIntegration(config)
    await apex.initialize()
    
    # Check health
    health = await apex.health_check()
    print(f"Status: {health['status']}")
    
    # Execute build
    result = await apex.execute_build(
        project_path='/path/to/project',
        config={'name': 'my-project'}
    )
    
    # Cleanup
    await apex.shutdown()

if __name__ == '__main__':
    asyncio.run(main())
```

## Configuration

### Environment Variables

```bash
# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=secret
REDIS_DB=0

# PostgreSQL
DATABASE_URL=postgresql://user:pass@localhost/apex
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=apex
POSTGRES_PASSWORD=apex
POSTGRES_DB=apex

# Git
CHECKPOINTS_REPO_PATH=/path/to/checkpoints
GIT_USER_NAME=APEX Integration
GIT_USER_EMAIL=apex@masterbuilder7.local
GIT_SIGNING_KEY=GPG_KEY_ID

# Kimi API
KIMI_API_KEY=your_api_key
KIMI_BASE_URL=https://api.moonshot.cn/v1
KIMI_TIMEOUT=120
KIMI_MAX_RETRIES=3

# n8n
N8N_BASE_URL=http://localhost:5678
N8N_API_KEY=your_n8n_key
WEBHOOK_SECRET=your_webhook_secret

# Feature Flags
APEX_MOCK_MODE=false  # Enable mock mode for testing
```

### Configuration File (YAML)

```yaml
# config.yaml
redis_host: localhost
redis_port: 6379
postgres_host: localhost
postgres_port: 5432
postgres_db: apex
git_repo_path: /tmp/apex_checkpoints
kimi_api_key: ${KIMI_API_KEY}  # Environment variable substitution
enable_redis: true
enable_postgres: true
enable_git: true
enable_mock_mode: false
```

## Core Methods

### Initialization & Health

```python
# Initialize all components
await apex.initialize()

# Check health status
health = await apex.health_check()
# Returns: {'status': 'healthy', 'components': {...}, 'summary': {...}}

# Get dashboard data
dashboard = await apex.get_dashboard_data()
```

### Unified Workflow Methods

```python
# End-to-end build execution
result = await apex.execute_build(
    project_path='/path/to/project',
    config={
        'name': 'my-project',
        'stack': 'react-fastapi',
        'auto_deploy': True
    }
)

# Process change through full stack
result = await apex.process_change_with_full_stack({
    'id': 'change-123',
    'description': 'Add user authentication',
    'files_affected': ['auth.py', 'Login.tsx'],
    'priority': 'high'
})

# Run security audit
audit = await apex.run_security_audit('/path/to/project')

# Optimize performance
optimized = await apex.optimize_performance(route_code="...")

# Verify rewards
verification = await apex.verify_rewards({
    'id': 'reward-123',
    'amount': 100,
    'user_id': 'user-456'
})
```

### Checkpoint Management

```python
# Create checkpoint across all 3 tiers
checkpoint = await apex.create_checkpoint(
    build_id='build-123',
    stage='frontend_complete',
    data={
        'files_created': ['App.tsx', 'Header.tsx'],
        'test_results': {'passed': 45, 'failed': 0}
    }
)
# Returns: CheckpointResult with tier1_success, tier2_success, tier3_success

# Rollback to checkpoint
result = await apex.rollback_to_checkpoint('checkpoint-id')
```

### A/B Testing

```python
# Create and run A/B test
test_result = await apex.run_ab_test({
    'name': 'Prompt Variation Test',
    'test_type': 'prompt_variation',
    'hypothesis': 'Shorter prompts improve response time',
    'primary_metric': 'execution_time',
    'variants': [
        {'name': 'control', 'traffic_percentage': 50, 'is_control': True},
        {'name': 'variant_b', 'traffic_percentage': 50}
    ],
    'min_sample_size': 100
})
```

### Pattern Database

```python
# Search patterns
patterns = await apex.search_patterns(
    query="authentication middleware",
    pattern_type="middleware",
    top_k=5
)
```

## Architecture

### Three-Tier Checkpoint System

```
┌─────────────────────────────────────────────────────────────┐
│                    APEX Integration                         │
├─────────────────────────────────────────────────────────────┤
│  Tier 1 (Hot)  │  Tier 2 (Warm)   │  Tier 3 (Cold)         │
│  ───────────   │  ─────────────   │  ─────────────         │
│  Redis         │  PostgreSQL      │  Git                   │
│  - Sub-10ms    │  - Persistent    │  - Immutable           │
│  - TTL: 5min   │  - Indexed       │  - Versioned           │
│  - Fallback:   │  - Fallback:     │  - GPG Signed          │
│    SQLite      │    SQLite        │                        │
└─────────────────────────────────────────────────────────────┘
```

### Component Interactions

```
┌─────────────────────────────────────────────────────────────┐
│  Agent Layer Events                                         │
│  ├── checkpoint_created ────┐                              │
│  ├── consensus_reached ─────┼──► n8n Webhooks               │
│  └── evaluation_complete ───┘                              │
├─────────────────────────────────────────────────────────────┤
│  Consensus Results ─────────► Pattern Database              │
├─────────────────────────────────────────────────────────────┤
│  Evaluation Results ────────► A/B Testing Framework         │
└─────────────────────────────────────────────────────────────┘
```

### Event Flow

```
Agent Layer Event
       │
       ▼
┌─────────────┐
│  Event Bus  │
└──────┬──────┘
       │
       ├──► n8n Webhook
       ├──► Pattern Database (on consensus approve)
       └──► A/B Testing (on evaluation complete)
```

## Error Handling

### Circuit Breakers

Each external service has a circuit breaker that:
- Opens after 5 consecutive failures
- Attempts recovery after 30 seconds
- Allows 3 test calls in half-open state

```python
# Circuit breaker states are tracked
health = await apex.health_check()
if health['components']['redis']['status'] == 'degraded':
    print("Redis using fallback (SQLite)")
```

### Retry Logic

- **Exponential backoff**: Base 2.0, max 60s delay
- **Jitter**: Prevents thundering herd
- **Max retries**: Configurable (default 3)

### Fallback Chains

- Redis → SQLite
- ChromaDB → SQLite
- PostgreSQL → SQLite

## Monitoring & Observability

### Metrics Collected

```python
metrics = apex.metrics.get_summary()
# Returns:
# {
#     'total_requests': 100,
#     'success_rate': 0.95,
#     'average_latency_ms': 45.2,
#     'cache_hit_rate': 0.78,
#     'checkpoint_count': 25,
#     'agent_executions': 50,
#     'workflow_triggers': 10,
#     'p99_latency_ms': 120.5
# }
```

### Health Dashboard Data

```python
dashboard = await apex.get_dashboard_data()
# Returns:
# {
#     'health': {...},          # Component health statuses
#     'metrics': {...},         # Aggregated metrics
#     'recent_checkpoints': [...],  # Last 10 checkpoints
#     'timestamp': '...'
# }
```

## Testing

### Run Integration Tests

```python
from apex.integration import run_integration_test
import asyncio

asyncio.run(run_integration_test())
```

### Run Performance Benchmarks

```python
from apex.integration import run_performance_benchmark
import asyncio

asyncio.run(run_performance_benchmark())
```

### Mock Mode

For testing without external services:

```python
config = APEXConfig(enable_mock_mode=True)
apex = APEXIntegration(config)
await apex.initialize()
```

## API Reference

### APEXIntegration

| Method | Description |
|--------|-------------|
| `initialize()` | Initialize all components |
| `shutdown()` | Gracefully shutdown all components |
| `health_check()` | Check health of all services |
| `execute_build(project_path, config)` | End-to-end build execution |
| `process_change_with_full_stack(change)` | Process change through all agents |
| `run_security_audit(project_path)` | Run Paystack Security Agent |
| `optimize_performance(route_code)` | Optimize code using AI Route Optimizer |
| `verify_rewards(reward_data)` | Verify rewards |
| `create_checkpoint(build_id, stage, data)` | Create 3-tier checkpoint |
| `rollback_to_checkpoint(checkpoint_id)` | Rollback to checkpoint |
| `run_ab_test(test_config)` | Create and run A/B test |
| `search_patterns(query, type, top_k)` | Search pattern database |
| `get_dashboard_data()` | Get dashboard data |

### APEXConfig

| Class Method | Description |
|--------------|-------------|
| `from_env()` | Load from environment variables |
| `from_file(filepath)` | Load from JSON/YAML file |

## Environment Setup

### Development

```bash
# Install dependencies
pip install httpx asyncpg aioredis redis gitpython chromadb

# Or use the provided requirements
pip install -r requirements.txt
```

### Production

```bash
# Set environment variables
export KIMI_API_KEY="your_key"
export DATABASE_URL="postgresql://..."
export REDIS_URL="redis://..."

# Run health check
python -c "from apex.integration import APEXIntegration; 
import asyncio; 
async def check(): 
    apex = APEXIntegration(); 
    await apex.initialize(); 
    print(await apex.health_check()); 
    await apex.shutdown()
asyncio.run(check())"
```

## Troubleshooting

### Component Not Available

```
WARNING: RedisManager not available: No module named 'redis'
```

**Solution**: Install the missing dependency or the component will use its fallback.

### Circuit Breaker Open

```
Circuit redis OPEN (5 failures)
```

**Solution**: Check the Redis connection. The circuit will automatically try recovery after 30 seconds.

### Git Repository Not Found

```
RepositoryNotFoundError: Repository not found at /path/to/checkpoints
```

**Solution**: The integration will automatically initialize the repository on first use.

## License

MIT License - See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## Support

For issues and questions, please use the GitHub issue tracker or contact the APEX Core Team.
