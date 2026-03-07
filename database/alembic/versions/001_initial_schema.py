"""Initial MasterBuilder7 database schema.

Creates all core tables with indexes, constraints, and triggers.

Revision ID: 001
Revises: 
Create Date: 2026-03-07 17:00:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Create enum types
    agent_status = postgresql.ENUM(
        'idle', 'busy', 'offline', 'error', 'maintenance',
        name='agent_status'
    )
    agent_status.create(op.get_bind())
    
    agent_type = postgresql.ENUM(
        'meta_router', 'planning', 'frontend', 'backend', 
        'testing', 'devops', 'reliability', 'evolution',
        name='agent_type'
    )
    agent_type.create(op.get_bind())
    
    build_status = postgresql.ENUM(
        'pending', 'running', 'success', 'failed', 
        'cancelled', 'rolling_back', 'rolled_back',
        name='build_status'
    )
    build_status.create(op.get_bind())
    
    task_priority = postgresql.ENUM(
        'critical', 'high', 'medium', 'low', 'background',
        name='task_priority'
    )
    task_priority.create(op.get_bind())
    
    task_status = postgresql.ENUM(
        'pending', 'queued', 'running', 'completed', 
        'failed', 'cancelled', 'retrying',
        name='task_status'
    )
    task_status.create(op.get_bind())
    
    checkpoint_tier = postgresql.ENUM(
        'tier_1', 'tier_2', 'tier_3',
        name='checkpoint_tier'
    )
    checkpoint_tier.create(op.get_bind())
    
    consensus_status = postgresql.ENUM(
        'pending', 'approved', 'rejected', 'tie', 'expired',
        name='consensus_status'
    )
    consensus_status.create(op.get_bind())
    
    message_type = postgresql.ENUM(
        'command', 'response', 'broadcast', 'heartbeat', 'alert', 'log',
        name='message_type'
    )
    message_type.create(op.get_bind())
    
    health_status = postgresql.ENUM(
        'healthy', 'degraded', 'unhealthy', 'unknown',
        name='health_status'
    )
    health_status.create(op.get_bind())
    
    project_status = postgresql.ENUM(
        'active', 'archived', 'paused', 'deleted',
        name='project_status'
    )
    project_status.create(op.get_bind())
    
    # Create agents table
    op.create_table(
        'agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('agent_type', agent_type, nullable=False),
        sa.Column('status', agent_status, nullable=False, server_default='idle'),
        sa.Column('version', sa.String(20), nullable=False, server_default='1.0.0'),
        sa.Column('capabilities', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('config', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('max_concurrent_tasks', sa.Integer, nullable=False, server_default='5'),
        sa.Column('memory_limit_mb', sa.Integer, nullable=True),
        sa.Column('cpu_limit_percent', sa.Integer, nullable=True),
        sa.Column('last_heartbeat', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_task_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('task_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('success_rate', sa.Numeric(5, 2), nullable=False, server_default='100.00'),
        sa.Column('total_cost_usd', sa.Numeric(10, 4), nullable=False, server_default='0.0000'),
        sa.Column('cost_per_task_avg', sa.Numeric(8, 4), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.CheckConstraint('success_rate >= 0 AND success_rate <= 100'),
        sa.CheckConstraint('max_concurrent_tasks > 0')
    )
    
    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('repo_url', sa.String(500), nullable=True),
        sa.Column('repo_branch', sa.String(100), nullable=False, server_default='main'),
        sa.Column('stack_detected', postgresql.JSONB, nullable=True),
        sa.Column('stack_config', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('build_config', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('env_vars', postgresql.JSONB, nullable=True),
        sa.Column('status', project_status, nullable=False, server_default='active'),
        sa.Column('total_builds', sa.Integer, nullable=False, server_default='0'),
        sa.Column('successful_builds', sa.Integer, nullable=False, server_default='0'),
        sa.Column('failed_builds', sa.Integer, nullable=False, server_default='0'),
        sa.Column('total_cost_usd', sa.Numeric(12, 4), nullable=False, server_default='0.0000'),
        sa.Column('budget_limit_usd', sa.Numeric(12, 4), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
        sa.UniqueConstraint('name'),
        sa.CheckConstraint('budget_limit_usd IS NULL OR budget_limit_usd > 0')
    )
    
    # Create builds table
    op.create_table(
        'builds',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('build_number', sa.Integer, nullable=False),
        sa.Column('git_commit', sa.String(40), nullable=True),
        sa.Column('git_branch', sa.String(100), nullable=True),
        sa.Column('git_tag', sa.String(100), nullable=True),
        sa.Column('status', build_status, nullable=False, server_default='pending'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer, nullable=True),
        sa.Column('stages', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('current_stage', sa.String(50), nullable=True),
        sa.Column('outputs', postgresql.JSONB, nullable=True),
        sa.Column('artifacts', postgresql.JSONB, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('error_details', postgresql.JSONB, nullable=True),
        sa.Column('retry_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('parent_build_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('estimated_cost_usd', sa.Numeric(8, 4), nullable=True),
        sa.Column('actual_cost_usd', sa.Numeric(8, 4), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('triggered_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_build_id'], ['builds.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'build_number')
    )
    
    # Create tasks table
    op.create_table(
        'tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('build_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('task_type', sa.String(50), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('priority', task_priority, nullable=False, server_default='medium'),
        sa.Column('status', task_status, nullable=False, server_default='pending'),
        sa.Column('input_data', postgresql.JSONB, nullable=True),
        sa.Column('output_data', postgresql.JSONB, nullable=True),
        sa.Column('result', postgresql.JSONB, nullable=True),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer, nullable=True),
        sa.Column('max_retries', sa.Integer, nullable=False, server_default='3'),
        sa.Column('retry_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text, nullable=True),
        sa.Column('depends_on', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('estimated_cost_usd', sa.Numeric(8, 4), nullable=True),
        sa.Column('actual_cost_usd', sa.Numeric(8, 4), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['build_id'], ['builds.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create checkpoints table
    op.create_table(
        'checkpoints',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('build_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('tier', checkpoint_tier, nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('snapshot_data', postgresql.JSONB, nullable=False),
        sa.Column('file_manifest', postgresql.JSONB, nullable=True),
        sa.Column('storage_path', sa.String(500), nullable=True),
        sa.Column('storage_size_bytes', sa.BigInteger, nullable=True),
        sa.Column('checksum', sa.String(64), nullable=True),
        sa.Column('can_rollback', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('rolled_back_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rolled_back_to', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('created_by_agent', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['build_id'], ['builds.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_agent'], ['agents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['rolled_back_to'], ['checkpoints.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create agent_states table
    op.create_table(
        'agent_states',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('checkpoint_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('state_type', sa.String(50), nullable=False),
        sa.Column('state_data', postgresql.JSONB, nullable=False),
        sa.Column('memory_state', postgresql.JSONB, nullable=True),
        sa.Column('context_window', postgresql.JSONB, nullable=True),
        sa.Column('tokens_used', sa.Integer, nullable=True),
        sa.Column('tokens_input', sa.Integer, nullable=True),
        sa.Column('tokens_output', sa.Integer, nullable=True),
        sa.Column('cost_usd', sa.Numeric(8, 4), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['checkpoint_id'], ['checkpoints.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create consensus_records table
    op.create_table(
        'consensus_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('build_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('decision_type', sa.String(50), nullable=False),
        sa.Column('subject', sa.Text, nullable=False),
        sa.Column('required_votes', sa.Integer, nullable=False, server_default='3'),
        sa.Column('votes_received', sa.Integer, nullable=False, server_default='0'),
        sa.Column('status', consensus_status, nullable=False, server_default='pending'),
        sa.Column('votes', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('final_decision', sa.Boolean, nullable=True),
        sa.Column('confidence_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_notes', sa.Text, nullable=True),
        sa.Column('timeout_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['build_id'], ['builds.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('required_votes >= 2'),
        sa.CheckConstraint('confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 100)')
    )
    
    # Create cost_tracking table
    op.create_table(
        'cost_tracking',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('build_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ai_provider', sa.String(50), nullable=False),
        sa.Column('ai_model', sa.String(100), nullable=False),
        sa.Column('tokens_input', sa.Integer, nullable=False, server_default='0'),
        sa.Column('tokens_output', sa.Integer, nullable=False, server_default='0'),
        sa.Column('tokens_total', sa.Integer, nullable=False, server_default='0'),
        sa.Column('input_cost_per_1k', sa.Numeric(8, 6), nullable=False),
        sa.Column('output_cost_per_1k', sa.Numeric(8, 6), nullable=False),
        sa.Column('input_cost_usd', sa.Numeric(10, 6), nullable=False),
        sa.Column('output_cost_usd', sa.Numeric(10, 6), nullable=False),
        sa.Column('total_cost_usd', sa.Numeric(10, 6), nullable=False),
        sa.Column('api_cost_usd', sa.Numeric(10, 6), nullable=False, server_default='0'),
        sa.Column('storage_cost_usd', sa.Numeric(10, 6), nullable=False, server_default='0'),
        sa.Column('compute_cost_usd', sa.Numeric(10, 6), nullable=False, server_default='0'),
        sa.Column('duration_seconds', sa.Integer, nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['build_id'], ['builds.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create health_metrics table
    op.create_table(
        'health_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('service_name', sa.String(100), nullable=False),
        sa.Column('status', health_status, nullable=False),
        sa.Column('check_type', sa.String(50), nullable=False),
        sa.Column('response_time_ms', sa.Integer, nullable=True),
        sa.Column('cpu_percent', sa.Numeric(5, 2), nullable=True),
        sa.Column('memory_percent', sa.Numeric(5, 2), nullable=True),
        sa.Column('disk_percent', sa.Numeric(5, 2), nullable=True),
        sa.Column('metrics', postgresql.JSONB, nullable=True),
        sa.Column('message', sa.Text, nullable=True),
        sa.Column('details', postgresql.JSONB, nullable=True),
        sa.Column('alert_level', sa.String(20), nullable=True),
        sa.Column('alert_sent', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('checked_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('(cpu_percent IS NULL OR (cpu_percent >= 0 AND cpu_percent <= 100)) AND (memory_percent IS NULL OR (memory_percent >= 0 AND memory_percent <= 100)) AND (disk_percent IS NULL OR (disk_percent >= 0 AND disk_percent <= 100))')
    )
    
    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('sender_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('sender_type', sa.String(20), nullable=False),
        sa.Column('recipient_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('recipient_type', sa.String(20), nullable=False),
        sa.Column('message_type', message_type, nullable=False),
        sa.Column('channel', sa.String(50), nullable=True),
        sa.Column('priority', sa.Integer, nullable=False, server_default='5'),
        sa.Column('subject', sa.String(200), nullable=True),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('payload', postgresql.JSONB, nullable=True),
        sa.Column('is_read', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('thread_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reply_to', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('context', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['sender_id'], ['agents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['recipient_id'], ['agents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['thread_id'], ['messages.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reply_to'], ['messages.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('priority >= 1 AND priority <= 10')
    )
    
    # Create indexes
    # Agents indexes
    op.create_index('idx_agents_status', 'agents', ['status'])
    op.create_index('idx_agents_type', 'agents', ['agent_type'])
    op.create_index('idx_agents_heartbeat', 'agents', ['last_heartbeat'])
    
    # Projects indexes
    op.create_index('idx_projects_status', 'projects', ['status'])
    op.create_index('idx_projects_slug', 'projects', ['slug'])
    
    # Builds indexes
    op.create_index('idx_builds_project', 'builds', ['project_id'])
    op.create_index('idx_builds_status', 'builds', ['status'])
    op.create_index('idx_builds_created_at', 'builds', [sa.text('created_at DESC')])
    op.create_index('idx_builds_status_created', 'builds', ['status', sa.text('created_at DESC')])
    
    # Tasks indexes
    op.create_index('idx_tasks_build', 'tasks', ['build_id'])
    op.create_index('idx_tasks_agent', 'tasks', ['agent_id'])
    op.create_index('idx_tasks_status', 'tasks', ['status'])
    op.create_index('idx_tasks_priority', 'tasks', ['priority'])
    op.create_index('idx_tasks_scheduled', 'tasks', ['scheduled_at'])
    op.create_index('idx_tasks_status_priority', 'tasks', ['status', 'priority'])
    
    # Checkpoints indexes
    op.create_index('idx_checkpoints_build', 'checkpoints', ['build_id'])
    op.create_index('idx_checkpoints_tier', 'checkpoints', ['tier'])
    op.create_index('idx_checkpoints_can_rollback', 'checkpoints', ['can_rollback'], postgresql_where=sa.text('can_rollback = true'))
    
    # Agent states indexes
    op.create_index('idx_agent_states_agent', 'agent_states', ['agent_id'])
    op.create_index('idx_agent_states_created', 'agent_states', [sa.text('created_at DESC')])
    
    # Consensus indexes
    op.create_index('idx_consensus_task', 'consensus_records', ['task_id'])
    op.create_index('idx_consensus_status', 'consensus_records', ['status'])
    op.create_index('idx_consensus_timeout', 'consensus_records', ['timeout_at'])
    
    # Cost tracking indexes
    op.create_index('idx_cost_tracking_agent', 'cost_tracking', ['agent_id'])
    op.create_index('idx_cost_tracking_build', 'cost_tracking', ['build_id'])
    op.create_index('idx_cost_tracking_created', 'cost_tracking', ['created_at'])
    op.create_index('idx_cost_tracking_provider', 'cost_tracking', ['ai_provider'])
    
    # Health metrics indexes
    op.create_index('idx_health_metrics_agent', 'health_metrics', ['agent_id'])
    op.create_index('idx_health_metrics_status', 'health_metrics', ['status'])
    op.create_index('idx_health_metrics_checked', 'health_metrics', [sa.text('checked_at DESC')])
    op.create_index('idx_health_metrics_service', 'health_metrics', ['service_name'])
    
    # Messages indexes
    op.create_index('idx_messages_sender', 'messages', ['sender_id'])
    op.create_index('idx_messages_recipient', 'messages', ['recipient_id'])
    op.create_index('idx_messages_type', 'messages', ['message_type'])
    op.create_index('idx_messages_created', 'messages', [sa.text('created_at DESC')])
    op.create_index('idx_messages_thread', 'messages', ['thread_id'])
    op.create_index('idx_messages_unread', 'messages', ['recipient_id', 'is_read'], postgresql_where=sa.text('is_read = false'))
    
    # Create triggers
    op.execute('''
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    ''')
    
    op.execute('''
        CREATE TRIGGER update_agents_updated_at
            BEFORE UPDATE ON agents
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    ''')
    
    op.execute('''
        CREATE TRIGGER update_projects_updated_at
            BEFORE UPDATE ON projects
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    ''')
    
    op.execute('''
        CREATE TRIGGER update_builds_updated_at
            BEFORE UPDATE ON builds
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    ''')
    
    op.execute('''
        CREATE TRIGGER update_tasks_updated_at
            BEFORE UPDATE ON tasks
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    ''')
    
    # Duration calculation triggers
    op.execute('''
        CREATE OR REPLACE FUNCTION calculate_build_duration()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.completed_at IS NOT NULL AND NEW.started_at IS NOT NULL THEN
                NEW.duration_seconds = EXTRACT(EPOCH FROM (NEW.completed_at - NEW.started_at))::INTEGER;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    ''')
    
    op.execute('''
        CREATE TRIGGER calculate_build_duration_trigger
            BEFORE UPDATE ON builds
            FOR EACH ROW EXECUTE FUNCTION calculate_build_duration();
    ''')
    
    op.execute('''
        CREATE OR REPLACE FUNCTION calculate_task_duration()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.completed_at IS NOT NULL AND NEW.started_at IS NOT NULL THEN
                NEW.duration_seconds = EXTRACT(EPOCH FROM (NEW.completed_at - NEW.started_at))::INTEGER;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    ''')
    
    op.execute('''
        CREATE TRIGGER calculate_task_duration_trigger
            BEFORE UPDATE ON tasks
            FOR EACH ROW EXECUTE FUNCTION calculate_task_duration();
    ''')
    
    # Build number auto-increment
    op.execute('''
        CREATE OR REPLACE FUNCTION set_build_number()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.build_number IS NULL THEN
                SELECT COALESCE(MAX(build_number), 0) + 1
                INTO NEW.build_number
                FROM builds
                WHERE project_id = NEW.project_id;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    ''')
    
    op.execute('''
        CREATE TRIGGER set_build_number_trigger
            BEFORE INSERT ON builds
            FOR EACH ROW EXECUTE FUNCTION set_build_number();
    ''')
    
    # Project build count triggers
    op.execute('''
        CREATE OR REPLACE FUNCTION update_project_build_counts()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                UPDATE projects 
                SET total_builds = total_builds + 1,
                    updated_at = NOW()
                WHERE id = NEW.project_id;
            ELSIF TG_OP = 'UPDATE' THEN
                IF NEW.status = 'success' AND OLD.status != 'success' THEN
                    UPDATE projects 
                    SET successful_builds = successful_builds + 1,
                        updated_at = NOW()
                    WHERE id = NEW.project_id;
                ELSIF NEW.status = 'failed' AND OLD.status != 'failed' THEN
                    UPDATE projects 
                    SET failed_builds = failed_builds + 1,
                        updated_at = NOW()
                    WHERE id = NEW.project_id;
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    ''')
    
    op.execute('''
        CREATE TRIGGER update_project_build_counts_trigger
            AFTER INSERT OR UPDATE ON builds
            FOR EACH ROW EXECUTE FUNCTION update_project_build_counts();
    ''')
    
    # Enable RLS
    op.execute('ALTER TABLE agents ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE projects ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE builds ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE tasks ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE checkpoints ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE agent_states ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE consensus_records ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE cost_tracking ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE health_metrics ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE messages ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    # Drop triggers
    op.execute('DROP TRIGGER IF EXISTS update_project_build_counts_trigger ON builds')
    op.execute('DROP TRIGGER IF EXISTS set_build_number_trigger ON builds')
    op.execute('DROP TRIGGER IF EXISTS calculate_task_duration_trigger ON tasks')
    op.execute('DROP TRIGGER IF EXISTS calculate_build_duration_trigger ON builds')
    op.execute('DROP TRIGGER IF EXISTS update_tasks_updated_at ON tasks')
    op.execute('DROP TRIGGER IF EXISTS update_builds_updated_at ON builds')
    op.execute('DROP TRIGGER IF EXISTS update_projects_updated_at ON projects')
    op.execute('DROP TRIGGER IF EXISTS update_agents_updated_at ON agents')
    
    # Drop functions
    op.execute('DROP FUNCTION IF EXISTS update_project_build_counts()')
    op.execute('DROP FUNCTION IF EXISTS set_build_number()')
    op.execute('DROP FUNCTION IF EXISTS calculate_task_duration()')
    op.execute('DROP FUNCTION IF EXISTS calculate_build_duration()')
    op.execute('DROP FUNCTION IF EXISTS update_updated_at_column()')
    
    # Drop tables (cascade to drop indexes)
    op.drop_table('messages')
    op.drop_table('health_metrics')
    op.drop_table('cost_tracking')
    op.drop_table('consensus_records')
    op.drop_table('agent_states')
    op.drop_table('checkpoints')
    op.drop_table('tasks')
    op.drop_table('builds')
    op.drop_table('projects')
    op.drop_table('agents')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS project_status')
    op.execute('DROP TYPE IF EXISTS health_status')
    op.execute('DROP TYPE IF EXISTS message_type')
    op.execute('DROP TYPE IF EXISTS consensus_status')
    op.execute('DROP TYPE IF EXISTS checkpoint_tier')
    op.execute('DROP TYPE IF EXISTS task_status')
    op.execute('DROP TYPE IF EXISTS task_priority')
    op.execute('DROP TYPE IF EXISTS build_status')
    op.execute('DROP TYPE IF EXISTS agent_type')
    op.execute('DROP TYPE IF EXISTS agent_status')
