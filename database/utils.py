"""Database utility functions for MasterBuilder7.

This module provides helper functions for common database operations.
"""

import os
from contextlib import contextmanager
from typing import Generator, Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from sqlalchemy import create_engine, func, desc, and_
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from models import (
    Agent, Project, Build, Task, Checkpoint, AgentState,
    ConsensusRecord, CostTracking, HealthMetric, Message,
    AgentType, AgentStatus, BuildStatus, TaskStatus, TaskPriority,
    CheckpointTier, ConsensusStatus, HealthStatus, ProjectStatus
)


def get_database_url() -> str:
    """Get database URL from environment variable or use default."""
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        return db_url
    return 'postgresql://masterbuilder:masterbuilder@localhost:5432/masterbuilder7'


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Get a database session as a context manager.
    
    Usage:
        with get_db_session() as session:
            agents = session.query(Agent).all()
    """
    engine = create_engine(get_database_url())
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        yield session
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        raise e
    finally:
        session.close()


# ============================================================================
# AGENT OPERATIONS
# ============================================================================

def get_agent_by_name(session: Session, name: str) -> Optional[Agent]:
    """Get an agent by name."""
    return session.query(Agent).filter_by(name=name).first()


def get_agent_by_type(session: Session, agent_type: AgentType) -> Optional[Agent]:
    """Get an agent by type."""
    return session.query(Agent).filter_by(agent_type=agent_type).first()


def get_available_agents(session: Session) -> List[Agent]:
    """Get all available (idle) agents."""
    return session.query(Agent).filter_by(status=AgentStatus.IDLE).all()


def update_agent_heartbeat(session: Session, agent_id: str) -> None:
    """Update agent heartbeat timestamp."""
    agent = session.query(Agent).get(agent_id)
    if agent:
        agent.last_heartbeat = datetime.now(timezone.utc)


def get_agent_stats(session: Session, agent_id: str) -> Dict[str, Any]:
    """Get comprehensive agent statistics."""
    agent = session.query(Agent).get(agent_id)
    if not agent:
        return {}
    
    # Get task counts
    total_tasks = session.query(Task).filter_by(agent_id=agent_id).count()
    completed_tasks = session.query(Task).filter_by(
        agent_id=agent_id, status=TaskStatus.COMPLETED
    ).count()
    failed_tasks = session.query(Task).filter_by(
        agent_id=agent_id, status=TaskStatus.FAILED
    ).count()
    
    # Get recent costs
    recent_cost = session.query(func.sum(CostTracking.total_cost_usd)).filter_by(
        agent_id=agent_id
    ).scalar() or Decimal('0')
    
    return {
        "agent": agent,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "failed_tasks": failed_tasks,
        "success_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
        "total_cost_usd": recent_cost,
        "is_healthy": agent.status != AgentStatus.ERROR,
    }


# ============================================================================
# PROJECT OPERATIONS
# ============================================================================

def get_project_by_slug(session: Session, slug: str) -> Optional[Project]:
    """Get a project by slug."""
    return session.query(Project).filter_by(slug=slug).first()


def get_active_projects(session: Session) -> List[Project]:
    """Get all active projects."""
    return session.query(Project).filter_by(status=ProjectStatus.ACTIVE).all()


def create_project(
    session: Session,
    name: str,
    slug: str,
    repo_url: Optional[str] = None,
    description: Optional[str] = None,
    budget_limit: Optional[Decimal] = None
) -> Project:
    """Create a new project."""
    project = Project(
        name=name,
        slug=slug,
        repo_url=repo_url,
        description=description,
        budget_limit_usd=budget_limit,
        status=ProjectStatus.ACTIVE
    )
    session.add(project)
    session.flush()
    return project


# ============================================================================
# BUILD OPERATIONS
# ============================================================================

def create_build(
    session: Session,
    project_id: str,
    git_commit: Optional[str] = None,
    git_branch: Optional[str] = None,
    triggered_by: Optional[str] = None
) -> Build:
    """Create a new build for a project."""
    build = Build(
        project_id=project_id,
        git_commit=git_commit,
        git_branch=git_branch,
        triggered_by=triggered_by,
        status=BuildStatus.PENDING
    )
    session.add(build)
    session.flush()
    return build


def start_build(session: Session, build_id: str) -> None:
    """Mark a build as started."""
    build = session.query(Build).get(build_id)
    if build:
        build.status = BuildStatus.RUNNING
        build.started_at = datetime.now(timezone.utc)


def complete_build(session: Session, build_id: str, success: bool = True) -> None:
    """Mark a build as completed."""
    build = session.query(Build).get(build_id)
    if build:
        build.status = BuildStatus.SUCCESS if success else BuildStatus.FAILED
        build.completed_at = datetime.now(timezone.utc)


def get_recent_builds(session: Session, project_id: str, limit: int = 10) -> List[Build]:
    """Get recent builds for a project."""
    return session.query(Build).filter_by(
        project_id=project_id
    ).order_by(desc(Build.created_at)).limit(limit).all()


# ============================================================================
# TASK OPERATIONS
# ============================================================================

def create_task(
    session: Session,
    name: str,
    task_type: str,
    build_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    priority: TaskPriority = TaskPriority.MEDIUM,
    input_data: Optional[Dict] = None,
    depends_on: Optional[List[str]] = None
) -> Task:
    """Create a new task."""
    task = Task(
        name=name,
        task_type=task_type,
        build_id=build_id,
        agent_id=agent_id,
        priority=priority,
        input_data=input_data,
        depends_on=depends_on or [],
        status=TaskStatus.PENDING
    )
    session.add(task)
    session.flush()
    return task


def assign_task_to_agent(session: Session, task_id: str, agent_id: str) -> None:
    """Assign a task to an agent."""
    task = session.query(Task).get(task_id)
    if task:
        task.agent_id = agent_id
        task.status = TaskStatus.QUEUED


def start_task(session: Session, task_id: str) -> None:
    """Mark a task as started."""
    task = session.query(Task).get(task_id)
    if task:
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(timezone.utc)
        
        # Update agent status
        if task.agent_id:
            agent = session.query(Agent).get(task.agent_id)
            if agent:
                agent.status = AgentStatus.BUSY


def complete_task(
    session: Session,
    task_id: str,
    success: bool = True,
    output_data: Optional[Dict] = None,
    result: Optional[Dict] = None
) -> None:
    """Mark a task as completed."""
    task = session.query(Task).get(task_id)
    if task:
        task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
        task.completed_at = datetime.now(timezone.utc)
        task.output_data = output_data
        task.result = result
        
        # Update agent status
        if task.agent_id:
            agent = session.query(Agent).get(task.agent_id)
            if agent:
                agent.status = AgentStatus.IDLE
                agent.last_task_at = datetime.now(timezone.utc)
                agent.task_count += 1


def get_pending_tasks(session: Session) -> List[Task]:
    """Get all pending tasks."""
    return session.query(Task).filter_by(
        status=TaskStatus.PENDING
    ).order_by(
        Task.priority,
        Task.created_at
    ).all()


# ============================================================================
# CHECKPOINT OPERATIONS
# ============================================================================

def create_checkpoint(
    session: Session,
    build_id: str,
    tier: CheckpointTier,
    name: str,
    snapshot_data: Dict[str, Any],
    agent_id: Optional[str] = None,
    task_id: Optional[str] = None,
    storage_path: Optional[str] = None
) -> Checkpoint:
    """Create a new checkpoint."""
    checkpoint = Checkpoint(
        build_id=build_id,
        task_id=task_id,
        tier=tier,
        name=name,
        snapshot_data=snapshot_data,
        created_by_agent=agent_id,
        storage_path=storage_path,
        can_rollback=True
    )
    session.add(checkpoint)
    session.flush()
    return checkpoint


def get_latest_checkpoint(session: Session, build_id: str, tier: Optional[CheckpointTier] = None) -> Optional[Checkpoint]:
    """Get the latest checkpoint for a build."""
    query = session.query(Checkpoint).filter_by(build_id=build_id)
    if tier:
        query = query.filter_by(tier=tier)
    return query.order_by(desc(Checkpoint.created_at)).first()


def rollback_to_checkpoint(session: Session, checkpoint_id: str) -> Optional[Checkpoint]:
    """Mark a checkpoint as rolled back."""
    checkpoint = session.query(Checkpoint).get(checkpoint_id)
    if checkpoint and checkpoint.can_rollback:
        checkpoint.rolled_back_at = datetime.now(timezone.utc)
        return checkpoint
    return None


# ============================================================================
# CONSENSUS OPERATIONS
# ============================================================================

def create_consensus(
    session: Session,
    task_id: str,
    decision_type: str,
    subject: str,
    required_votes: int = 3,
    timeout_minutes: int = 30
) -> ConsensusRecord:
    """Create a new consensus record."""
    consensus = ConsensusRecord(
        task_id=task_id,
        decision_type=decision_type,
        subject=subject,
        required_votes=required_votes,
        timeout_at=datetime.now(timezone.utc) + timedelta(minutes=timeout_minutes)
    )
    session.add(consensus)
    session.flush()
    return consensus


def cast_vote(
    session: Session,
    consensus_id: str,
    agent_id: str,
    decision: bool,
    reason: Optional[str] = None
) -> None:
    """Cast a vote for a consensus."""
    consensus = session.query(ConsensusRecord).get(consensus_id)
    if not consensus:
        return
    
    # Add vote
    vote = {
        "agent_id": agent_id,
        "decision": decision,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    votes = list(consensus.votes) if consensus.votes else []
    votes.append(vote)
    consensus.votes = votes
    consensus.votes_received = len(votes)
    
    # Check if consensus is reached
    if len(votes) >= consensus.required_votes:
        approve_count = sum(1 for v in votes if v.get("decision"))
        reject_count = len(votes) - approve_count
        
        if approve_count > reject_count:
            consensus.status = ConsensusStatus.APPROVED
            consensus.final_decision = True
        elif reject_count > approve_count:
            consensus.status = ConsensusStatus.REJECTED
            consensus.final_decision = False
        else:
            consensus.status = ConsensusStatus.TIE
        
        consensus.resolved_at = datetime.now(timezone.utc)
        consensus.confidence_score = Decimal(max(approve_count, reject_count)) / len(votes) * 100


# ============================================================================
# COST TRACKING OPERATIONS
# ============================================================================

def track_cost(
    session: Session,
    agent_id: str,
    ai_provider: str,
    ai_model: str,
    tokens_input: int,
    tokens_output: int,
    input_cost_per_1k: Decimal,
    output_cost_per_1k: Decimal,
    task_id: Optional[str] = None,
    build_id: Optional[str] = None,
    duration_seconds: Optional[int] = None
) -> CostTracking:
    """Track costs for an AI operation."""
    input_cost = (tokens_input / 1000) * input_cost_per_1k
    output_cost = (tokens_output / 1000) * output_cost_per_1k
    total_cost = input_cost + output_cost
    
    cost = CostTracking(
        agent_id=agent_id,
        task_id=task_id,
        build_id=build_id,
        ai_provider=ai_provider,
        ai_model=ai_model,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        tokens_total=tokens_input + tokens_output,
        input_cost_per_1k=input_cost_per_1k,
        output_cost_per_1k=output_cost_per_1k,
        input_cost_usd=input_cost,
        output_cost_usd=output_cost,
        total_cost_usd=total_cost,
        duration_seconds=duration_seconds
    )
    session.add(cost)
    
    # Update agent total cost
    agent = session.query(Agent).get(agent_id)
    if agent:
        agent.total_cost_usd = (agent.total_cost_usd or Decimal('0')) + total_cost
    
    session.flush()
    return cost


def get_cost_summary(session: Session, days: int = 30) -> Dict[str, Any]:
    """Get cost summary for the last N days."""
    from_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    total_cost = session.query(func.sum(CostTracking.total_cost_usd)).filter(
        CostTracking.created_at >= from_date
    ).scalar() or Decimal('0')
    
    total_tokens = session.query(func.sum(CostTracking.tokens_total)).filter(
        CostTracking.created_at >= from_date
    ).scalar() or 0
    
    # By provider
    provider_costs = session.query(
        CostTracking.ai_provider,
        func.sum(CostTracking.total_cost_usd)
    ).filter(
        CostTracking.created_at >= from_date
    ).group_by(CostTracking.ai_provider).all()
    
    return {
        "total_cost_usd": total_cost,
        "total_tokens": total_tokens,
        "period_days": days,
        "by_provider": {p[0]: p[1] for p in provider_costs}
    }


# ============================================================================
# HEALTH METRICS OPERATIONS
# ============================================================================

def record_health_check(
    session: Session,
    service_name: str,
    status: HealthStatus,
    check_type: str = "custom",
    agent_id: Optional[str] = None,
    response_time_ms: Optional[int] = None,
    cpu_percent: Optional[Decimal] = None,
    memory_percent: Optional[Decimal] = None,
    message: Optional[str] = None,
    metrics: Optional[Dict] = None
) -> HealthMetric:
    """Record a health check."""
    health = HealthMetric(
        agent_id=agent_id,
        service_name=service_name,
        status=status,
        check_type=check_type,
        response_time_ms=response_time_ms,
        cpu_percent=cpu_percent,
        memory_percent=memory_percent,
        message=message,
        metrics=metrics or {}
    )
    session.add(health)
    session.flush()
    return health


def get_unhealthy_services(session: Session) -> List[HealthMetric]:
    """Get all unhealthy services (latest check per service)."""
    subquery = session.query(
        HealthMetric.service_name,
        func.max(HealthMetric.checked_at).label('max_checked')
    ).group_by(HealthMetric.service_name).subquery()
    
    return session.query(HealthMetric).join(
        subquery,
        and_(
            HealthMetric.service_name == subquery.c.service_name,
            HealthMetric.checked_at == subquery.c.max_checked
        )
    ).filter(HealthMetric.status != HealthStatus.HEALTHY).all()


# ============================================================================
# MESSAGE OPERATIONS
# ============================================================================

def send_message(
    session: Session,
    content: str,
    message_type: MessageType = MessageType.LOG,
    sender_id: Optional[str] = None,
    sender_type: str = "system",
    recipient_id: Optional[str] = None,
    recipient_type: str = "broadcast",
    subject: Optional[str] = None,
    payload: Optional[Dict] = None,
    priority: int = 5,
    thread_id: Optional[str] = None
) -> Message:
    """Send a message between agents/system."""
    message = Message(
        sender_id=sender_id,
        sender_type=sender_type,
        recipient_id=recipient_id,
        recipient_type=recipient_type,
        message_type=message_type,
        subject=subject,
        content=content,
        payload=payload,
        priority=priority,
        thread_id=thread_id
    )
    session.add(message)
    session.flush()
    return message


def get_unread_messages(session: Session, recipient_id: str) -> List[Message]:
    """Get unread messages for a recipient."""
    return session.query(Message).filter_by(
        recipient_id=recipient_id,
        is_read=False
    ).order_by(desc(Message.priority), desc(Message.created_at)).all()


def mark_message_read(session: Session, message_id: str) -> None:
    """Mark a message as read."""
    message = session.query(Message).get(message_id)
    if message and not message.is_read:
        message.is_read = True
        message.read_at = datetime.now(timezone.utc)
