-- ============================================================================
-- MasterBuilder7 PostgreSQL Database Schema
-- Production-Ready Schema with Proper Indexes, Foreign Keys, and Constraints
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- ENUM TYPES
-- ============================================================================

-- Agent Status Enum
CREATE TYPE agent_status AS ENUM (
    'idle',
    'busy',
    'offline',
    'error',
    'maintenance'
);

-- Agent Type Enum
CREATE TYPE agent_type AS ENUM (
    'meta_router',
    'planning',
    'frontend',
    'backend',
    'testing',
    'devops',
    'reliability',
    'evolution'
);

-- Build Status Enum
CREATE TYPE build_status AS ENUM (
    'pending',
    'running',
    'success',
    'failed',
    'cancelled',
    'rolling_back',
    'rolled_back'
);

-- Task Priority Enum
CREATE TYPE task_priority AS ENUM (
    'critical',
    'high',
    'medium',
    'low',
    'background'
);

-- Task Status Enum
CREATE TYPE task_status AS ENUM (
    'pending',
    'queued',
    'running',
    'completed',
    'failed',
    'cancelled',
    'retrying'
);

-- Checkpoint Tier Enum
CREATE TYPE checkpoint_tier AS ENUM (
    'tier_1',  -- Quick checkpoint (every 30s)
    'tier_2',  -- Standard checkpoint (on stage completion)
    'tier_3'   -- Deep checkpoint (on build success)
);

-- Consensus Status Enum
CREATE TYPE consensus_status AS ENUM (
    'pending',
    'approved',
    'rejected',
    'tie',
    'expired'
);

-- Message Type Enum
CREATE TYPE message_type AS ENUM (
    'command',
    'response',
    'broadcast',
    'heartbeat',
    'alert',
    'log'
);

-- Health Status Enum
CREATE TYPE health_status AS ENUM (
    'healthy',
    'degraded',
    'unhealthy',
    'unknown'
);

-- Project Status Enum
CREATE TYPE project_status AS ENUM (
    'active',
    'archived',
    'paused',
    'deleted'
);

-- ============================================================================
-- TABLES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. AGENTS - Agent registration and status
-- ----------------------------------------------------------------------------
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    agent_type agent_type NOT NULL,
    status agent_status NOT NULL DEFAULT 'idle',
    version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    
    -- Capabilities and configuration
    capabilities JSONB NOT NULL DEFAULT '[]',
    config JSONB NOT NULL DEFAULT '{}',
    
    -- Resource limits
    max_concurrent_tasks INTEGER NOT NULL DEFAULT 5,
    memory_limit_mb INTEGER,
    cpu_limit_percent INTEGER,
    
    -- Status tracking
    last_heartbeat TIMESTAMP WITH TIME ZONE,
    last_task_at TIMESTAMP WITH TIME ZONE,
    task_count INTEGER NOT NULL DEFAULT 0,
    success_rate DECIMAL(5,2) NOT NULL DEFAULT 100.00,
    
    -- Cost tracking
    total_cost_usd DECIMAL(10,4) NOT NULL DEFAULT 0.0000,
    cost_per_task_avg DECIMAL(8,4),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT agents_name_unique UNIQUE (name),
    CONSTRAINT agents_success_rate_check CHECK (success_rate >= 0 AND success_rate <= 100),
    CONSTRAINT agents_max_concurrent_check CHECK (max_concurrent_tasks > 0)
);

-- Comments
COMMENT ON TABLE agents IS 'Registered AI agents in the MasterBuilder7 system';
COMMENT ON COLUMN agents.capabilities IS 'JSON array of agent capabilities';
COMMENT ON COLUMN agents.config IS 'Agent-specific configuration';
COMMENT ON COLUMN agents.success_rate IS 'Percentage of successful tasks (0-100)';

-- ----------------------------------------------------------------------------
-- 2. PROJECTS - Project configurations
-- ----------------------------------------------------------------------------
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Repository info
    repo_url VARCHAR(500),
    repo_branch VARCHAR(100) DEFAULT 'main',
    
    -- Stack information
    stack_detected JSONB,
    stack_config JSONB NOT NULL DEFAULT '{}',
    
    -- Build configuration
    build_config JSONB NOT NULL DEFAULT '{}',
    env_vars JSONB,
    
    -- Status
    status project_status NOT NULL DEFAULT 'active',
    
    -- Statistics
    total_builds INTEGER NOT NULL DEFAULT 0,
    successful_builds INTEGER NOT NULL DEFAULT 0,
    failed_builds INTEGER NOT NULL DEFAULT 0,
    
    -- Cost tracking
    total_cost_usd DECIMAL(12,4) NOT NULL DEFAULT 0.0000,
    budget_limit_usd DECIMAL(12,4),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_by UUID,
    
    -- Constraints
    CONSTRAINT projects_slug_unique UNIQUE (slug),
    CONSTRAINT projects_name_unique UNIQUE (name),
    CONSTRAINT projects_budget_check CHECK (budget_limit_usd IS NULL OR budget_limit_usd > 0)
);

-- Comments
COMMENT ON TABLE projects IS 'Software projects managed by MasterBuilder7';
COMMENT ON COLUMN projects.stack_detected IS 'Auto-detected tech stack';
COMMENT ON COLUMN projects.stack_config IS 'Stack-specific configuration';
COMMENT ON COLUMN projects.build_config IS 'Build pipeline configuration';

-- ----------------------------------------------------------------------------
-- 3. BUILDS - Build tracking
-- ----------------------------------------------------------------------------
CREATE TABLE builds (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL,
    
    -- Build info
    build_number INTEGER NOT NULL,
    git_commit VARCHAR(40),
    git_branch VARCHAR(100),
    git_tag VARCHAR(100),
    
    -- Status
    status build_status NOT NULL DEFAULT 'pending',
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    
    -- Pipeline stages
    stages JSONB NOT NULL DEFAULT '[]',
    current_stage VARCHAR(50),
    
    -- Outputs
    outputs JSONB,
    artifacts JSONB,
    
    -- Error handling
    error_message TEXT,
    error_details JSONB,
    retry_count INTEGER NOT NULL DEFAULT 0,
    parent_build_id UUID,
    
    -- Cost tracking
    estimated_cost_usd DECIMAL(8,4),
    actual_cost_usd DECIMAL(8,4),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    triggered_by UUID,
    
    -- Constraints
    CONSTRAINT builds_project_fk FOREIGN KEY (project_id) 
        REFERENCES projects(id) ON DELETE CASCADE,
    CONSTRAINT builds_parent_fk FOREIGN KEY (parent_build_id) 
        REFERENCES builds(id) ON DELETE SET NULL,
    CONSTRAINT builds_number_project_unique UNIQUE (project_id, build_number)
);

-- Comments
COMMENT ON TABLE builds IS 'Build executions tracked by the system';
COMMENT ON COLUMN builds.stages IS 'Pipeline stage results';
COMMENT ON COLUMN builds.outputs IS 'Build outputs (URLs, paths, etc.)';
COMMENT ON COLUMN builds.artifacts IS 'Generated artifacts information';

-- ----------------------------------------------------------------------------
-- 4. TASKS - Task queue persistence
-- ----------------------------------------------------------------------------
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    build_id UUID,
    agent_id UUID,
    
    -- Task info
    task_type VARCHAR(50) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    priority task_priority NOT NULL DEFAULT 'medium',
    
    -- Execution
    status task_status NOT NULL DEFAULT 'pending',
    input_data JSONB,
    output_data JSONB,
    result JSONB,
    
    -- Timing
    scheduled_at TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    
    -- Retry logic
    max_retries INTEGER NOT NULL DEFAULT 3,
    retry_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    
    -- Dependencies
    depends_on UUID[],
    
    -- Cost tracking
    estimated_cost_usd DECIMAL(8,4),
    actual_cost_usd DECIMAL(8,4),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT tasks_build_fk FOREIGN KEY (build_id) 
        REFERENCES builds(id) ON DELETE CASCADE,
    CONSTRAINT tasks_agent_fk FOREIGN KEY (agent_id) 
        REFERENCES agents(id) ON DELETE SET NULL
);

-- Comments
COMMENT ON TABLE tasks IS 'Task queue for distributed agent execution';
COMMENT ON COLUMN tasks.depends_on IS 'Array of task IDs this task depends on';

-- ----------------------------------------------------------------------------
-- 5. CHECKPOINTS - 3-tier checkpoint data
-- ----------------------------------------------------------------------------
CREATE TABLE checkpoints (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    build_id UUID NOT NULL,
    task_id UUID,
    
    -- Checkpoint info
    tier checkpoint_tier NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    
    -- Snapshot data
    snapshot_data JSONB NOT NULL,
    file_manifest JSONB,
    
    -- Storage
    storage_path VARCHAR(500),
    storage_size_bytes BIGINT,
    checksum VARCHAR(64),
    
    -- Restoration
    can_rollback BOOLEAN NOT NULL DEFAULT true,
    rolled_back_at TIMESTAMP WITH TIME ZONE,
    rolled_back_to UUID,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_by_agent UUID,
    
    -- Constraints
    CONSTRAINT checkpoints_build_fk FOREIGN KEY (build_id) 
        REFERENCES builds(id) ON DELETE CASCADE,
    CONSTRAINT checkpoints_task_fk FOREIGN KEY (task_id) 
        REFERENCES tasks(id) ON DELETE SET NULL,
    CONSTRAINT checkpoints_agent_fk FOREIGN KEY (created_by_agent) 
        REFERENCES agents(id) ON DELETE SET NULL,
    CONSTRAINT checkpoints_rollback_fk FOREIGN KEY (rolled_back_to) 
        REFERENCES checkpoints(id) ON DELETE SET NULL
);

-- Comments
COMMENT ON TABLE checkpoints IS '3-tier checkpoint system for build recovery';
COMMENT ON COLUMN checkpoints.snapshot_data IS 'Complete state snapshot';
COMMENT ON COLUMN checkpoints.file_manifest IS 'List of files in checkpoint';

-- ----------------------------------------------------------------------------
-- 6. AGENT_STATES - Agent state snapshots
-- ----------------------------------------------------------------------------
CREATE TABLE agent_states (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL,
    task_id UUID,
    checkpoint_id UUID,
    
    -- State data
    state_type VARCHAR(50) NOT NULL,
    state_data JSONB NOT NULL,
    memory_state JSONB,
    context_window JSONB,
    
    -- Performance
    tokens_used INTEGER,
    tokens_input INTEGER,
    tokens_output INTEGER,
    
    -- Cost
    cost_usd DECIMAL(8,4),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT agent_states_agent_fk FOREIGN KEY (agent_id) 
        REFERENCES agents(id) ON DELETE CASCADE,
    CONSTRAINT agent_states_task_fk FOREIGN KEY (task_id) 
        REFERENCES tasks(id) ON DELETE SET NULL,
    CONSTRAINT agent_states_checkpoint_fk FOREIGN KEY (checkpoint_id) 
        REFERENCES checkpoints(id) ON DELETE SET NULL
);

-- Comments
COMMENT ON TABLE agent_states IS 'Agent memory and context state snapshots';
COMMENT ON COLUMN agent_states.context_window IS 'Conversation/message context';

-- ----------------------------------------------------------------------------
-- 7. CONSENSUS_RECORDS - Consensus voting records
-- ----------------------------------------------------------------------------
CREATE TABLE consensus_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL,
    build_id UUID,
    
    -- Consensus info
    decision_type VARCHAR(50) NOT NULL,
    subject TEXT NOT NULL,
    
    -- Voting
    required_votes INTEGER NOT NULL DEFAULT 3,
    votes_received INTEGER NOT NULL DEFAULT 0,
    status consensus_status NOT NULL DEFAULT 'pending',
    
    -- Results
    votes JSONB NOT NULL DEFAULT '[]',
    final_decision BOOLEAN,
    confidence_score DECIMAL(5,2),
    
    -- Resolution
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT,
    
    -- Timing
    timeout_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT consensus_task_fk FOREIGN KEY (task_id) 
        REFERENCES tasks(id) ON DELETE CASCADE,
    CONSTRAINT consensus_build_fk FOREIGN KEY (build_id) 
        REFERENCES builds(id) ON DELETE SET NULL,
    CONSTRAINT consensus_required_votes_check CHECK (required_votes >= 2),
    CONSTRAINT consensus_confidence_check CHECK (
        confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 100)
    )
);

-- Comments
COMMENT ON TABLE consensus_records IS '3-verifier consensus voting system';
COMMENT ON COLUMN consensus_records.votes IS 'Array of vote objects with agent_id, decision, reason';

-- ----------------------------------------------------------------------------
-- 8. COST_TRACKING - Cost per agent/AI
-- ----------------------------------------------------------------------------
CREATE TABLE cost_tracking (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL,
    task_id UUID,
    build_id UUID,
    
    -- Cost breakdown
    ai_provider VARCHAR(50) NOT NULL,  -- openai, anthropic, google, etc.
    ai_model VARCHAR(100) NOT NULL,    -- gpt-4, claude-3, etc.
    
    -- Token usage
    tokens_input INTEGER NOT NULL DEFAULT 0,
    tokens_output INTEGER NOT NULL DEFAULT 0,
    tokens_total INTEGER NOT NULL DEFAULT 0,
    
    -- Pricing
    input_cost_per_1k DECIMAL(8,6) NOT NULL,
    output_cost_per_1k DECIMAL(8,6) NOT NULL,
    
    -- Calculated costs
    input_cost_usd DECIMAL(10,6) NOT NULL,
    output_cost_usd DECIMAL(10,6) NOT NULL,
    total_cost_usd DECIMAL(10,6) NOT NULL,
    
    -- Additional costs
    api_cost_usd DECIMAL(10,6) DEFAULT 0,
    storage_cost_usd DECIMAL(10,6) DEFAULT 0,
    compute_cost_usd DECIMAL(10,6) DEFAULT 0,
    
    -- Time tracking
    duration_seconds INTEGER,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT cost_tracking_agent_fk FOREIGN KEY (agent_id) 
        REFERENCES agents(id) ON DELETE CASCADE,
    CONSTRAINT cost_tracking_task_fk FOREIGN KEY (task_id) 
        REFERENCES tasks(id) ON DELETE SET NULL,
    CONSTRAINT cost_tracking_build_fk FOREIGN KEY (build_id) 
        REFERENCES builds(id) ON DELETE SET NULL
);

-- Comments
COMMENT ON TABLE cost_tracking IS 'Detailed cost tracking for all AI operations';
COMMENT ON COLUMN cost_tracking.ai_provider IS 'AI service provider name';

-- ----------------------------------------------------------------------------
-- 9. HEALTH_METRICS - Health check data
-- ----------------------------------------------------------------------------
CREATE TABLE health_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID,
    service_name VARCHAR(100) NOT NULL,
    
    -- Health status
    status health_status NOT NULL,
    check_type VARCHAR(50) NOT NULL,  -- heartbeat, resource, dependency, custom
    
    -- Metrics
    response_time_ms INTEGER,
    cpu_percent DECIMAL(5,2),
    memory_percent DECIMAL(5,2),
    disk_percent DECIMAL(5,2),
    
    -- Custom metrics
    metrics JSONB,
    
    -- Details
    message TEXT,
    details JSONB,
    
    -- Alerting
    alert_level VARCHAR(20),  -- info, warning, critical
    alert_sent BOOLEAN DEFAULT false,
    
    -- Metadata
    checked_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT health_metrics_agent_fk FOREIGN KEY (agent_id) 
        REFERENCES agents(id) ON DELETE CASCADE,
    CONSTRAINT health_metrics_percent_check CHECK (
        (cpu_percent IS NULL OR (cpu_percent >= 0 AND cpu_percent <= 100)) AND
        (memory_percent IS NULL OR (memory_percent >= 0 AND memory_percent <= 100)) AND
        (disk_percent IS NULL OR (disk_percent >= 0 AND disk_percent <= 100))
    )
);

-- Comments
COMMENT ON TABLE health_metrics IS 'System and agent health monitoring data';
COMMENT ON COLUMN health_metrics.metrics IS 'Custom health metrics as JSON';

-- ----------------------------------------------------------------------------
-- 10. MESSAGES - Agent communication log
-- ----------------------------------------------------------------------------
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Sender/Receiver
    sender_id UUID,
    sender_type VARCHAR(20) NOT NULL,  -- agent, system, user, external
    recipient_id UUID,
    recipient_type VARCHAR(20) NOT NULL,  -- agent, system, broadcast, external
    
    -- Message content
    message_type message_type NOT NULL,
    channel VARCHAR(50),  -- internal, websocket, webhook, queue
    priority INTEGER DEFAULT 5,  -- 1-10, lower is higher priority
    
    -- Content
    subject VARCHAR(200),
    content TEXT NOT NULL,
    payload JSONB,
    
    -- Status
    is_read BOOLEAN DEFAULT false,
    read_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    
    -- Threading
    thread_id UUID,
    reply_to UUID,
    
    -- Context
    context JSONB,  -- build_id, task_id, etc.
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT messages_sender_fk FOREIGN KEY (sender_id) 
        REFERENCES agents(id) ON DELETE SET NULL,
    CONSTRAINT messages_recipient_fk FOREIGN KEY (recipient_id) 
        REFERENCES agents(id) ON DELETE SET NULL,
    CONSTRAINT messages_thread_fk FOREIGN KEY (thread_id) 
        REFERENCES messages(id) ON DELETE SET NULL,
    CONSTRAINT messages_reply_fk FOREIGN KEY (reply_to) 
        REFERENCES messages(id) ON DELETE SET NULL,
    CONSTRAINT messages_priority_check CHECK (priority >= 1 AND priority <= 10)
);

-- Comments
COMMENT ON TABLE messages IS 'Inter-agent communication and logging';
COMMENT ON COLUMN messages.payload IS 'Structured message data';
COMMENT ON COLUMN messages.context IS 'Reference to builds, tasks, etc.';

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Agents indexes
CREATE INDEX idx_agents_status ON agents(status);
CREATE INDEX idx_agents_type ON agents(agent_type);
CREATE INDEX idx_agents_heartbeat ON agents(last_heartbeat);

-- Projects indexes
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_slug ON projects(slug);

-- Builds indexes
CREATE INDEX idx_builds_project ON builds(project_id);
CREATE INDEX idx_builds_status ON builds(status);
CREATE INDEX idx_builds_created_at ON builds(created_at DESC);
CREATE INDEX idx_builds_status_created ON builds(status, created_at DESC);

-- Tasks indexes
CREATE INDEX idx_tasks_build ON tasks(build_id);
CREATE INDEX idx_tasks_agent ON tasks(agent_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_tasks_scheduled ON tasks(scheduled_at);
CREATE INDEX idx_tasks_status_priority ON tasks(status, priority);

-- Checkpoints indexes
CREATE INDEX idx_checkpoints_build ON checkpoints(build_id);
CREATE INDEX idx_checkpoints_tier ON checkpoints(tier);
CREATE INDEX idx_checkpoints_can_rollback ON checkpoints(can_rollback) WHERE can_rollback = true;

-- Agent states indexes
CREATE INDEX idx_agent_states_agent ON agent_states(agent_id);
CREATE INDEX idx_agent_states_created ON agent_states(created_at DESC);

-- Consensus indexes
CREATE INDEX idx_consensus_task ON consensus_records(task_id);
CREATE INDEX idx_consensus_status ON consensus_records(status);
CREATE INDEX idx_consensus_timeout ON consensus_records(timeout_at);

-- Cost tracking indexes
CREATE INDEX idx_cost_tracking_agent ON cost_tracking(agent_id);
CREATE INDEX idx_cost_tracking_build ON cost_tracking(build_id);
CREATE INDEX idx_cost_tracking_created ON cost_tracking(created_at);
CREATE INDEX idx_cost_tracking_provider ON cost_tracking(ai_provider);

-- Health metrics indexes
CREATE INDEX idx_health_metrics_agent ON health_metrics(agent_id);
CREATE INDEX idx_health_metrics_status ON health_metrics(status);
CREATE INDEX idx_health_metrics_checked ON health_metrics(checked_at DESC);
CREATE INDEX idx_health_metrics_service ON health_metrics(service_name);

-- Messages indexes
CREATE INDEX idx_messages_sender ON messages(sender_id);
CREATE INDEX idx_messages_recipient ON messages(recipient_id);
CREATE INDEX idx_messages_type ON messages(message_type);
CREATE INDEX idx_messages_created ON messages(created_at DESC);
CREATE INDEX idx_messages_thread ON messages(thread_id);
CREATE INDEX idx_messages_unread ON messages(recipient_id, is_read) WHERE is_read = false;

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Agent performance summary
CREATE VIEW agent_performance_summary AS
SELECT 
    a.id,
    a.name,
    a.agent_type,
    a.status,
    a.task_count,
    a.success_rate,
    COUNT(t.id) FILTER (WHERE t.status = 'completed') as completed_tasks,
    COUNT(t.id) FILTER (WHERE t.status = 'failed') as failed_tasks,
    AVG(t.duration_seconds) FILTER (WHERE t.status = 'completed') as avg_task_duration,
    SUM(ct.total_cost_usd) as total_cost,
    a.last_heartbeat
FROM agents a
LEFT JOIN tasks t ON a.id = t.agent_id
LEFT JOIN cost_tracking ct ON a.id = ct.agent_id
GROUP BY a.id, a.name, a.agent_type, a.status, a.task_count, a.success_rate, a.last_heartbeat;

-- Build statistics by project
CREATE VIEW project_build_stats AS
SELECT 
    p.id,
    p.name,
    p.status,
    COUNT(b.id) as total_builds,
    COUNT(b.id) FILTER (WHERE b.status = 'success') as successful_builds,
    COUNT(b.id) FILTER (WHERE b.status = 'failed') as failed_builds,
    AVG(b.duration_seconds) FILTER (WHERE b.status = 'success') as avg_build_duration,
    SUM(b.actual_cost_usd) as total_cost,
    MAX(b.created_at) as last_build_at
FROM projects p
LEFT JOIN builds b ON p.id = b.project_id
GROUP BY p.id, p.name, p.status;

-- Daily cost summary
CREATE VIEW daily_cost_summary AS
SELECT 
    DATE_TRUNC('day', created_at) as date,
    ai_provider,
    ai_model,
    COUNT(*) as operation_count,
    SUM(tokens_input) as total_input_tokens,
    SUM(tokens_output) as total_output_tokens,
    SUM(total_cost_usd) as total_cost,
    AVG(total_cost_usd) as avg_cost_per_operation
FROM cost_tracking
GROUP BY DATE_TRUNC('day', created_at), ai_provider, ai_model;

-- Active tasks with dependencies
CREATE VIEW active_tasks_with_deps AS
SELECT 
    t.*,
    b.project_id,
    a.name as agent_name,
    (SELECT COUNT(*) FROM tasks t2 WHERE t2.id = ANY(t.depends_on) AND t2.status != 'completed') as pending_deps
FROM tasks t
LEFT JOIN builds b ON t.build_id = b.id
LEFT JOIN agents a ON t.agent_id = a.id
WHERE t.status IN ('pending', 'queued', 'running', 'retrying');

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to all tables
CREATE TRIGGER update_agents_updated_at
    BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_builds_updated_at
    BEFORE UPDATE ON builds
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Calculate build duration trigger
CREATE OR REPLACE FUNCTION calculate_build_duration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.completed_at IS NOT NULL AND NEW.started_at IS NOT NULL THEN
        NEW.duration_seconds = EXTRACT(EPOCH FROM (NEW.completed_at - NEW.started_at))::INTEGER;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER calculate_build_duration_trigger
    BEFORE UPDATE ON builds
    FOR EACH ROW EXECUTE FUNCTION calculate_build_duration();

-- Calculate task duration trigger
CREATE OR REPLACE FUNCTION calculate_task_duration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.completed_at IS NOT NULL AND NEW.started_at IS NOT NULL THEN
        NEW.duration_seconds = EXTRACT(EPOCH FROM (NEW.completed_at - NEW.started_at))::INTEGER;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER calculate_task_duration_trigger
    BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION calculate_task_duration();

-- Auto-increment build number trigger
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

CREATE TRIGGER set_build_number_trigger
    BEFORE INSERT ON builds
    FOR EACH ROW EXECUTE FUNCTION set_build_number();

-- Update project build counts trigger
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

CREATE TRIGGER update_project_build_counts_trigger
    AFTER INSERT OR UPDATE ON builds
    FOR EACH ROW EXECUTE FUNCTION update_project_build_counts();

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE builds ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE checkpoints ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE consensus_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE cost_tracking ENABLE ROW LEVEL SECURITY;
ALTER TABLE health_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Create policies (placeholder - customize based on auth requirements)
CREATE POLICY agents_all ON agents FOR ALL TO PUBLIC USING (true);
CREATE POLICY projects_all ON projects FOR ALL TO PUBLIC USING (true);
CREATE POLICY builds_all ON builds FOR ALL TO PUBLIC USING (true);
CREATE POLICY tasks_all ON tasks FOR ALL TO PUBLIC USING (true);
CREATE POLICY checkpoints_all ON checkpoints FOR ALL TO PUBLIC USING (true);
CREATE POLICY agent_states_all ON agent_states FOR ALL TO PUBLIC USING (true);
CREATE POLICY consensus_all ON consensus_records FOR ALL TO PUBLIC USING (true);
CREATE POLICY cost_tracking_all ON cost_tracking FOR ALL TO PUBLIC USING (true);
CREATE POLICY health_metrics_all ON health_metrics FOR ALL TO PUBLIC USING (true);
CREATE POLICY messages_all ON messages FOR ALL TO PUBLIC USING (true);
