# MasterBuilder7 Database Schema Summary

## 📁 Files Created

```
MasterBuilder7/database/
├── alembic/
│   ├── versions/
│   │   └── 001_initial_schema.py    # 602 lines - Initial migration
│   ├── env.py                        # 75 lines - Alembic environment
│   └── script.py.mako                # 21 lines - Migration template
├── alembic.ini                       # Alembic configuration
├── schema.sql                        # 862 lines - Raw SQL schema
├── models.py                         # 665 lines - SQLAlchemy ORM models
├── seed_data.py                      # 589 lines - Database seeding
├── utils.py                          # 571 lines - Database utilities
├── requirements.txt                  # Dependencies
├── .env.example                      # Environment template
├── __init__.py                       # Package exports
├── README.md                         # Documentation
└── SCHEMA_SUMMARY.md                 # This file
```

**Total Lines of Code: ~3,289 lines**

## 📊 Schema Overview

### 10 Core Tables

| # | Table | Purpose | Key Features |
|---|-------|---------|--------------|
| 1 | **agents** | Agent registration | 8 specialist agents, status tracking, cost tracking |
| 2 | **projects** | Project configs | Stack detection, build config, budget limits |
| 3 | **builds** | Build tracking | Auto-increment numbers, stage tracking, rollback support |
| 4 | **tasks** | Task queue | Priority levels, dependency chains, retry logic |
| 5 | **checkpoints** | 3-tier checkpoints | Tier 1/2/3, rollback capability, file manifests |
| 6 | **agent_states** | State snapshots | Memory, context window, token tracking |
| 7 | **consensus_records** | Consensus voting | 3-verifier system, voting records, timeout handling |
| 8 | **cost_tracking** | Cost per AI | Token usage, per-provider pricing, detailed breakdown |
| 9 | **health_metrics** | Health checks | CPU/Memory/Disk, custom metrics, alerting |
| 10 | **messages** | Agent comms | Threading, priorities, broadcast/unicast |

### 10 Enum Types

```
agent_status     : idle, busy, offline, error, maintenance
agent_type       : meta_router, planning, frontend, backend, testing, devops, reliability, evolution
build_status     : pending, running, success, failed, cancelled, rolling_back, rolled_back
task_priority    : critical, high, medium, low, background
task_status      : pending, queued, running, completed, failed, cancelled, retrying
checkpoint_tier  : tier_1, tier_2, tier_3
consensus_status : pending, approved, rejected, tie, expired
message_type     : command, response, broadcast, heartbeat, alert, log
health_status    : healthy, degraded, unhealthy, unknown
project_status   : active, archived, paused, deleted
```

## 🔑 Key Features

### Constraints & Validation
- ✅ 30+ Check constraints (success rates 0-100%, positive integers, etc.)
- ✅ 25+ Foreign key relationships with proper CASCADE/SET NULL
- ✅ 20+ Unique constraints
- ✅ NOT NULL constraints on critical fields

### Indexes (35+)
```sql
-- High-performance indexes for common queries
idx_agents_status, idx_agents_type, idx_agents_heartbeat
idx_builds_project, idx_builds_status, idx_builds_created_at
idx_tasks_status_priority, idx_tasks_scheduled
idx_cost_tracking_agent, idx_cost_tracking_created
idx_messages_unread (partial index)
```

### Triggers (8)
```sql
update_updated_at_column()      -- Auto-update timestamps
calculate_build_duration()      -- Auto-calc build duration
calculate_task_duration()       -- Auto-calc task duration
set_build_number()              -- Auto-increment build numbers
update_project_build_counts()   -- Auto-update project stats
```

### Views (4)
```sql
agent_performance_summary   -- Aggregated agent metrics
project_build_stats         -- Build statistics per project
daily_cost_summary          -- Daily cost breakdown
active_tasks_with_deps      -- Active tasks with pending dependencies
```

### Row Level Security
- ✅ RLS enabled on all tables
- ✅ Placeholder policies (customize per auth requirements)

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Setup database
createdb masterbuilder7

# 3. Run migrations
alembic upgrade head

# 4. Seed data
python seed_data.py
```

## 📈 Sample Queries

### Agent Performance
```sql
SELECT * FROM agent_performance_summary 
WHERE status = 'idle' 
ORDER BY success_rate DESC;
```

### Recent Builds
```sql
SELECT * FROM builds 
WHERE project_id = '...' 
ORDER BY created_at DESC 
LIMIT 10;
```

### Cost Analysis
```sql
SELECT * FROM daily_cost_summary 
WHERE date >= NOW() - INTERVAL '7 days';
```

### Pending Tasks
```sql
SELECT * FROM active_tasks_with_deps 
WHERE pending_deps = 0 
ORDER BY priority, created_at;
```

## 🔧 Migration Examples

```bash
# Create new migration
alembic revision -m "add_agent_capabilities"

# Auto-generate from model changes
alembic revision --autogenerate -m "update_models"

# Upgrade
alembic upgrade head

# Downgrade
alembic downgrade -1
```

## 💰 Cost Tracking Example

```python
from database import track_cost, get_cost_summary

# Track an AI operation
track_cost(
    session=session,
    agent_id=agent.id,
    ai_provider="openai",
    ai_model="gpt-4",
    tokens_input=1000,
    tokens_output=500,
    input_cost_per_1k=Decimal("0.03"),
    output_cost_per_1k=Decimal("0.06"),
    task_id=task.id
)

# Get summary
summary = get_cost_summary(session, days=7)
print(f"Total cost: ${summary['total_cost_usd']}")
```

## 🏥 Health Check Example

```python
from database import record_health_check, HealthStatus

# Record health check
record_health_check(
    session=session,
    service_name="Meta-Router",
    status=HealthStatus.HEALTHY,
    response_time_ms=45,
    cpu_percent=Decimal("25.5"),
    message="All systems operational"
)
```

## 📝 Task Management Example

```python
from database import create_task, assign_task_to_agent, start_task, complete_task

# Create task
task = create_task(
    session=session,
    name="Analyze repository",
    task_type="analysis",
    build_id=build.id,
    priority=TaskPriority.HIGH
)

# Assign to agent
assign_task_to_agent(session, task.id, agent.id)

# Start task
start_task(session, task.id)

# Complete task
complete_task(
    session=session,
    task_id=task.id,
    success=True,
    result={"files_analyzed": 42}
)
```

## 🔒 Production Checklist

- [ ] Update `DATABASE_URL` environment variable
- [ ] Configure Row Level Security policies
- [ ] Set up database backups
- [ ] Configure connection pooling
- [ ] Enable query logging (optional)
- [ ] Set up monitoring for health_metrics
- [ ] Configure cost alerts
- [ ] Enable SSL for database connections
