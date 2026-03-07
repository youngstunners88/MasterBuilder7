# MasterBuilder7 Database

Production-ready PostgreSQL database schema with Alembic migrations for the MasterBuilder7 agent orchestration system.

## 📁 Structure

```
database/
├── alembic/
│   ├── versions/           # Migration files
│   │   └── 001_initial_schema.py
│   ├── env.py             # Alembic environment config
│   └── script.py.mako     # Migration template
├── alembic.ini            # Alembic configuration
├── schema.sql             # Raw SQL schema (for reference)
├── models.py              # SQLAlchemy ORM models
├── seed_data.py           # Database seeding script
├── requirements.txt       # Python dependencies
├── .env.example           # Environment template
└── README.md              # This file
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd /home/teacherchris37/MasterBuilder7/database
pip install -r requirements.txt
```

### 2. Setup PostgreSQL

```bash
# Create database
createdb masterbuilder7

# Or with specific user
psql -U postgres -c "CREATE DATABASE masterbuilder7;"
psql -U postgres -c "CREATE USER masterbuilder WITH PASSWORD 'masterbuilder';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE masterbuilder7 TO masterbuilder;"
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your database credentials
```

### 4. Run Migrations

```bash
# Initialize Alembic (if not already done)
alembic init alembic

# Run all migrations
alembic upgrade head
```

### 5. Seed Data

```bash
python seed_data.py
```

## 📊 Schema Overview

### Tables

| Table | Purpose |
|-------|---------|
| `agents` | 8 APEX specialist agent registration |
| `projects` | Software project configurations |
| `builds` | Build execution tracking |
| `tasks` | Task queue persistence |
| `checkpoints` | 3-tier checkpoint system |
| `agent_states` | Agent memory/context snapshots |
| `consensus_records` | 3-verifier consensus voting |
| `cost_tracking` | Per-agent/AI cost tracking |
| `health_metrics` | Health check data |
| `messages` | Agent communication log |

### Enums

- **Agent Types**: `meta_router`, `planning`, `frontend`, `backend`, `testing`, `devops`, `reliability`, `evolution`
- **Build Status**: `pending`, `running`, `success`, `failed`, `cancelled`, `rolling_back`, `rolled_back`
- **Task Priority**: `critical`, `high`, `medium`, `low`, `background`
- **Checkpoint Tiers**: `tier_1`, `tier_2`, `tier_3`
- **Consensus Status**: `pending`, `approved`, `rejected`, `tie`, `expired`

## 🔧 Migration Commands

```bash
# Create new migration
alembic revision -m "description_of_change"

# Auto-generate from models
alembic revision --autogenerate -m "auto_migration"

# Upgrade to latest
alembic upgrade head

# Upgrade specific revision
alembic upgrade 001

# Downgrade one revision
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade 001

# Current version
alembic current

# History
alembic history
```

## 💻 Using Models

```python
from database import (
    Agent, Project, Build, Task,
    AgentType, BuildStatus, get_session
)
from sqlalchemy import create_engine

# Connect to database
engine = create_engine('postgresql://user:pass@localhost/masterbuilder7')
session = get_session(engine)

# Query all agents
agents = session.query(Agent).all()
for agent in agents:
    print(f"{agent.name}: {agent.status}")

# Create new project
project = Project(
    name="My New App",
    slug="my-new-app",
    repo_url="https://github.com/user/repo"
)
session.add(project)
session.commit()

# Query builds for project
builds = session.query(Build).filter_by(
    project_id=project.id,
    status=BuildStatus.SUCCESS
).all()
```

## 🌱 Seeding

```bash
# Default database
python seed_data.py

# Custom database URL
DATABASE_URL=postgresql://user:pass@host/db python seed_data.py
```

## 🔐 Row Level Security

RLS policies are created but set to allow all. To customize:

```sql
-- Example: Users can only see their own projects
CREATE POLICY projects_user_isolation ON projects
    FOR ALL
    USING (created_by = current_setting('app.current_user_id')::UUID);
```

## 📈 Performance

### Indexes Created

- `agents`: status, type, heartbeat
- `projects`: status, slug
- `builds`: project_id, status, created_at
- `tasks`: build_id, agent_id, status, priority
- `checkpoints`: build_id, tier
- `cost_tracking`: agent_id, build_id, created_at
- `health_metrics`: agent_id, status, checked_at
- `messages`: sender_id, recipient_id, type, created_at

### Views

- `agent_performance_summary`: Aggregated agent metrics
- `project_build_stats`: Build statistics per project
- `daily_cost_summary`: Daily cost breakdown
- `active_tasks_with_deps`: Currently active tasks

## 🔍 Troubleshooting

### Connection Issues

```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1;"

# Check PostgreSQL is running
pg_isready
```

### Migration Issues

```bash
# Reset (careful - drops all data!)
alembic downgrade base
alembic upgrade head

# Mark as specific version without running
alembic stamp 001
```

## 📚 Additional Resources

- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)
- [Alembic Docs](https://alembic.sqlalchemy.org/)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)
