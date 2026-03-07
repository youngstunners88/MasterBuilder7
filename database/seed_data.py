"""Database seeding script for MasterBuilder7.

This script populates the database with initial data including:
- The 8 APEX specialist agents
- Sample project configurations
- Initial health check records

Usage:
    python seed_data.py
    
Environment Variables:
    DATABASE_URL: PostgreSQL connection URL (default: postgresql://masterbuilder:masterbuilder@localhost:5432/masterbuilder7)
"""

import os
import sys
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import (
    Base, Agent, Project, HealthMetric, Message,
    AgentType, AgentStatus, ProjectStatus, HealthStatus, MessageType
)

# Database URL from environment or default
def get_database_url() -> str:
    """Get database URL from environment variable or use default."""
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        # Handle Render.com and other platforms that use postgres://
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        return db_url
    return 'postgresql://masterbuilder:masterbuilder@localhost:5432/masterbuilder7'


# ============================================================================
# SEED DATA
# ============================================================================

AGENTS_DATA = [
    {
        "name": "Meta-Router",
        "agent_type": AgentType.META_ROUTER,
        "version": "1.0.0",
        "capabilities": [
            "stack_detection",
            "repository_analysis",
            "intelligent_routing",
            "dependency_resolution"
        ],
        "config": {
            "supported_stacks": [
                "react", "vue", "angular", "svelte",
                "fastapi", "django", "flask", "express",
                "capacitor", "expo", "flutter", "react_native"
            ],
            "analysis_timeout": 300,
            "max_file_size_mb": 10
        },
        "max_concurrent_tasks": 5,
        "memory_limit_mb": 2048,
        "cpu_limit_percent": 50,
    },
    {
        "name": "Planning-Agent",
        "agent_type": AgentType.PLANNING,
        "version": "1.0.0",
        "capabilities": [
            "architecture_design",
            "api_specification",
            "database_schema",
            "openapi_generation",
            "er_diagram_generation"
        ],
        "config": {
            "planning_depth": "detailed",
            "include_diagrams": True,
            "tech_stack_research": True
        },
        "max_concurrent_tasks": 3,
        "memory_limit_mb": 4096,
        "cpu_limit_percent": 60,
    },
    {
        "name": "Frontend-Agent",
        "agent_type": AgentType.FRONTEND,
        "version": "1.0.0",
        "capabilities": [
            "ui_development",
            "component_generation",
            "responsive_design",
            "accessibility_compliance",
            "state_management"
        ],
        "config": {
            "default_framework": "react",
            "css_framework": "tailwind",
            "include_storybook": True,
            "testing_library": "vitest"
        },
        "max_concurrent_tasks": 5,
        "memory_limit_mb": 3072,
        "cpu_limit_percent": 70,
    },
    {
        "name": "Backend-Agent",
        "agent_type": AgentType.BACKEND,
        "version": "1.0.0",
        "capabilities": [
            "api_development",
            "database_integration",
            "authentication",
            "security_hardening",
            "supabase_integration"
        ],
        "config": {
            "default_framework": "fastapi",
            "auth_method": "jwt",
            "include_openapi": True,
            "security_scan": True
        },
        "max_concurrent_tasks": 4,
        "memory_limit_mb": 4096,
        "cpu_limit_percent": 60,
    },
    {
        "name": "Testing-Agent",
        "agent_type": AgentType.TESTING,
        "version": "1.0.0",
        "capabilities": [
            "test_generation",
            "security_scanning",
            "coverage_analysis",
            "e2e_testing",
            "performance_testing"
        ],
        "config": {
            "min_coverage": 85,
            "test_types": ["unit", "integration", "e2e"],
            "security_tools": ["bandit", "semgrep", "safety"]
        },
        "max_concurrent_tasks": 5,
        "memory_limit_mb": 4096,
        "cpu_limit_percent": 80,
    },
    {
        "name": "DevOps-Agent",
        "agent_type": AgentType.DEVOPS,
        "version": "1.0.0",
        "capabilities": [
            "ci_cd_pipeline",
            "multi_platform_deploy",
            "mobile_builds",
            "infrastructure_as_code",
            "containerization"
        ],
        "config": {
            "platforms": ["netlify", "vercel", "railway", "render"],
            "mobile_platforms": ["ios", "android"],
            "include_docker": True
        },
        "max_concurrent_tasks": 3,
        "memory_limit_mb": 2048,
        "cpu_limit_percent": 50,
    },
    {
        "name": "Reliability-Agent",
        "agent_type": AgentType.RELIABILITY,
        "version": "1.0.0",
        "capabilities": [
            "health_monitoring",
            "rollback_capability",
            "consensus_verification",
            "fault_tolerance",
            "checkpoint_management"
        ],
        "config": {
            "verification_threshold": 3,
            "health_check_interval": 30,
            "auto_rollback": True
        },
        "max_concurrent_tasks": 10,
        "memory_limit_mb": 2048,
        "cpu_limit_percent": 40,
    },
    {
        "name": "Evolution-Agent",
        "agent_type": AgentType.EVOLUTION,
        "version": "1.0.0",
        "capabilities": [
            "pattern_recognition",
            "optimization_suggestions",
            "learning_extraction",
            "performance_tuning",
            "knowledge_base_updates"
        ],
        "config": {
            "learning_mode": "continuous",
            "pattern_retention": 1000,
            "feedback_loop": True
        },
        "max_concurrent_tasks": 2,
        "memory_limit_mb": 8192,
        "cpu_limit_percent": 50,
    },
]

SAMPLE_PROJECTS = [
    {
        "name": "Sample React Application",
        "slug": "sample-react-app",
        "description": "A sample React application demonstrating MasterBuilder7 capabilities",
        "repo_url": "https://github.com/example/sample-react-app",
        "repo_branch": "main",
        "stack_detected": {
            "frontend": "react",
            "build_tool": "vite",
            "styling": "tailwindcss",
            "state_management": "zustand"
        },
        "stack_config": {
            "typescript": True,
            "testing": "vitest",
            "linting": "eslint"
        },
        "build_config": {
            "parallel_builds": True,
            "enable_tests": True,
            "deployment_target": "netlify"
        },
        "budget_limit_usd": Decimal("100.00"),
    },
    {
        "name": "FastAPI Backend Service",
        "slug": "fastapi-backend",
        "description": "Sample FastAPI backend with PostgreSQL integration",
        "repo_url": "https://github.com/example/fastapi-backend",
        "repo_branch": "develop",
        "stack_detected": {
            "backend": "fastapi",
            "database": "postgresql",
            "auth": "jwt",
            "deployment": "docker"
        },
        "stack_config": {
            "async_support": True,
            "orm": "sqlalchemy",
            "migrations": "alembic"
        },
        "build_config": {
            "include_tests": True,
            "security_scan": True,
            "deployment_target": "railway"
        },
        "budget_limit_usd": Decimal("150.00"),
    },
    {
        "name": "Mobile App Prototype",
        "slug": "mobile-app-prototype",
        "description": "Cross-platform mobile application prototype",
        "repo_url": "https://github.com/example/mobile-app",
        "stack_detected": {
            "framework": "react_native",
            "platforms": ["ios", "android"],
            "navigation": "react_navigation"
        },
        "stack_config": {
            "expo": True,
            "typescript": True,
            "styling": "styled_components"
        },
        "build_config": {
            "generate_apk": True,
            "generate_ipa": False,
            "deployment_target": "app_store"
        },
        "budget_limit_usd": Decimal("200.00"),
    },
]


def seed_agents(session) -> list[Agent]:
    """Seed the 8 APEX specialist agents.
    
    Args:
        session: Database session
        
    Returns:
        List of created Agent objects
    """
    print("🤖 Seeding agents...")
    agents = []
    
    for agent_data in AGENTS_DATA:
        # Check if agent already exists
        existing = session.query(Agent).filter_by(name=agent_data["name"]).first()
        if existing:
            print(f"   ⚠️  Agent '{agent_data['name']}' already exists, skipping")
            agents.append(existing)
            continue
            
        agent = Agent(
            name=agent_data["name"],
            agent_type=agent_data["agent_type"],
            version=agent_data["version"],
            capabilities=agent_data["capabilities"],
            config=agent_data["config"],
            max_concurrent_tasks=agent_data["max_concurrent_tasks"],
            memory_limit_mb=agent_data.get("memory_limit_mb"),
            cpu_limit_percent=agent_data.get("cpu_limit_percent"),
            status=AgentStatus.IDLE,
            last_heartbeat=datetime.now(timezone.utc),
        )
        session.add(agent)
        agents.append(agent)
        print(f"   ✅ Created agent: {agent.name} ({agent.agent_type.value})")
    
    session.commit()
    print(f"✅ Seeded {len(agents)} agents\n")
    return agents


def seed_projects(session) -> list[Project]:
    """Seed sample projects.
    
    Args:
        session: Database session
        
    Returns:
        List of created Project objects
    """
    print("📁 Seeding projects...")
    projects = []
    
    for project_data in SAMPLE_PROJECTS:
        # Check if project already exists
        existing = session.query(Project).filter_by(slug=project_data["slug"]).first()
        if existing:
            print(f"   ⚠️  Project '{project_data['name']}' already exists, skipping")
            projects.append(existing)
            continue
            
        project = Project(
            name=project_data["name"],
            slug=project_data["slug"],
            description=project_data["description"],
            repo_url=project_data.get("repo_url"),
            repo_branch=project_data.get("repo_branch", "main"),
            stack_detected=project_data.get("stack_detected"),
            stack_config=project_data.get("stack_config", {}),
            build_config=project_data.get("build_config", {}),
            budget_limit_usd=project_data.get("budget_limit_usd"),
            status=ProjectStatus.ACTIVE,
        )
        session.add(project)
        projects.append(project)
        print(f"   ✅ Created project: {project.name}")
    
    session.commit()
    print(f"✅ Seeded {len(projects)} projects\n")
    return projects


def seed_health_metrics(session, agents: list[Agent]) -> None:
    """Seed initial health check records for agents.
    
    Args:
        session: Database session
        agents: List of Agent objects
    """
    print("💓 Seeding health metrics...")
    
    for agent in agents:
        # Check if health metric already exists for this agent
        existing = session.query(HealthMetric).filter_by(
            agent_id=agent.id,
            service_name=f"{agent.name}-health"
        ).first()
        
        if existing:
            print(f"   ⚠️  Health metric for '{agent.name}' already exists, skipping")
            continue
            
        metric = HealthMetric(
            agent_id=agent.id,
            service_name=f"{agent.name}-health",
            status=HealthStatus.HEALTHY,
            check_type="heartbeat",
            response_time_ms=45,
            cpu_percent=Decimal("25.5"),
            memory_percent=Decimal("40.2"),
            metrics={
                "tasks_completed": 0,
                "tasks_failed": 0,
                "avg_response_time": 45
            },
            message=f"Agent {agent.name} is healthy and ready",
            alert_sent=False,
        )
        session.add(metric)
        print(f"   ✅ Created health metric for: {agent.name}")
    
    # Add system health metric
    existing_system = session.query(HealthMetric).filter_by(
        service_name="masterbuilder7-system"
    ).first()
    
    if not existing_system:
        system_metric = HealthMetric(
            service_name="masterbuilder7-system",
            status=HealthStatus.HEALTHY,
            check_type="system",
            response_time_ms=12,
            cpu_percent=Decimal("15.0"),
            memory_percent=Decimal("30.5"),
            disk_percent=Decimal("45.0"),
            metrics={
                "database_status": "connected",
                "queue_status": "operational",
                "api_status": "healthy"
            },
            message="MasterBuilder7 system is operational",
            alert_sent=False,
        )
        session.add(system_metric)
        print(f"   ✅ Created system health metric")
    
    session.commit()
    print(f"✅ Seeded health metrics\n")


def seed_messages(session, agents: list[Agent]) -> None:
    """Seed initial system messages.
    
    Args:
        session: Database session
        agents: List of Agent objects
    """
    print("💬 Seeding messages...")
    
    # System initialization message
    existing = session.query(Message).filter_by(
        subject="System Initialization"
    ).first()
    
    if not existing:
        init_message = Message(
            sender_type="system",
            recipient_type="broadcast",
            message_type=MessageType.BROADCAST,
            channel="internal",
            priority=1,
            subject="System Initialization",
            content="MasterBuilder7 system has been initialized. All 8 APEX specialist agents are ready.",
            payload={
                "agents_registered": len(agents),
                "version": "1.0.0",
                "startup_time": datetime.now(timezone.utc).isoformat()
            },
            is_read=False,
        )
        session.add(init_message)
        print(f"   ✅ Created initialization message")
    
    # Agent registration messages
    for agent in agents:
        existing = session.query(Message).filter_by(
            sender_id=agent.id,
            subject="Agent Registration"
        ).first()
        
        if existing:
            continue
            
        message = Message(
            sender_id=agent.id,
            sender_type="agent",
            recipient_type="system",
            message_type=MessageType.LOG,
            channel="internal",
            priority=5,
            subject="Agent Registration",
            content=f"Agent {agent.name} has registered with capabilities: {', '.join(agent.capabilities)}",
            payload={
                "agent_type": agent.agent_type.value,
                "capabilities": agent.capabilities,
                "version": agent.version
            },
            is_read=True,
            read_at=datetime.now(timezone.utc),
        )
        session.add(message)
        print(f"   ✅ Created registration message for: {agent.name}")
    
    session.commit()
    print(f"✅ Seeded messages\n")


def verify_seed_data(session) -> None:
    """Verify that seed data was inserted correctly.
    
    Args:
        session: Database session
    """
    print("🔍 Verifying seed data...")
    
    # Count records
    agent_count = session.query(Agent).count()
    project_count = session.query(Project).count()
    health_count = session.query(HealthMetric).count()
    message_count = session.query(Message).count()
    
    print(f"   📊 Database Statistics:")
    print(f"      - Agents: {agent_count}")
    print(f"      - Projects: {project_count}")
    print(f"      - Health Metrics: {health_count}")
    print(f"      - Messages: {message_count}")
    
    # Verify agent types
    agent_types = session.query(Agent.agent_type).distinct().all()
    print(f"   🎯 Agent Types: {', '.join([a[0].value for a in agent_types])}")
    
    # Verify all agents are idle
    idle_count = session.query(Agent).filter_by(status=AgentStatus.IDLE).count()
    print(f"   ✅ {idle_count}/{agent_count} agents are idle and ready")
    
    print("\n✅ Seed data verification complete!")


def main():
    """Main entry point for database seeding."""
    print("=" * 60)
    print("🚀 MasterBuilder7 Database Seeding")
    print("=" * 60)
    print()
    
    # Get database URL
    database_url = get_database_url()
    print(f"📡 Database URL: {database_url.replace('://', '://***:***@')}")
    print()
    
    # Create engine and session
    try:
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # Test connection
        session.execute("SELECT 1")
        print("✅ Database connection successful\n")
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\nPlease ensure:")
        print("  1. PostgreSQL is running")
        print("  2. Database 'masterbuilder7' exists")
        print("  3. Credentials are correct")
        print("\nYou can set DATABASE_URL environment variable to customize connection.")
        sys.exit(1)
    
    try:
        # Seed data
        agents = seed_agents(session)
        projects = seed_projects(session)
        seed_health_metrics(session, agents)
        seed_messages(session, agents)
        
        # Verify
        verify_seed_data(session)
        
        print()
        print("=" * 60)
        print("✅ Database seeding completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Seeding failed: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
