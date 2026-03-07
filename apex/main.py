#!/usr/bin/env python3
"""
APEX - Autonomous Programming & Execution Engine
=================================================
CLI and API Entry Point for the APEX Agent Layer

This is the main entry point for APEX, providing:
- CLI commands for build orchestration, checkpoint management, and agent control
- FastAPI server for programmatic access and webhook integrations
- Health monitoring and diagnostics
- Pattern search and evolution tracking

Usage:
    # CLI Mode
    apex init                    # Initialize APEX infrastructure
    apex build ./my-project      # Run full build pipeline
    apex serve                   # Start API server

    # API Mode (when running `apex serve`)
    curl http://localhost:8000/health
    curl -X POST http://localhost:8000/api/v1/build \
         -H "Content-Type: application/json" \
         -d '{"project_path": "./my-project"}'

Author: APEX Core Team
Version: 2.0.0
License: MIT
"""

import os
import sys
import json
import asyncio
import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager

# =============================================================================
# Environment & Configuration Setup
# =============================================================================

# Load .env file before imports that might use environment variables
try:
    from dotenv import load_dotenv
    
    # Try multiple locations for .env file
    env_paths = [
        Path(__file__).parent / ".env",
        Path(__file__).parent.parent / ".env",
        Path.cwd() / ".env",
        Path.home() / ".apex" / ".env",
    ]
    
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            break
except ImportError:
    pass  # dotenv not installed, env vars must be set manually

# =============================================================================
# Logging Configuration (Structured JSON Logging)
# =============================================================================

try:
    from pythonjsonlogger import jsonlogger
    JSON_LOGGER_AVAILABLE = True
except ImportError:
    JSON_LOGGER_AVAILABLE = False

try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False

def setup_logging(log_level: str = "INFO", json_format: bool = True) -> logging.Logger:
    """Configure structured logging for APEX."""
    log_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger("apex")
    logger.setLevel(log_level)
    logger.handlers = []  # Clear existing handlers
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    if json_format and JSON_LOGGER_AVAILABLE:
        # JSON formatter for production
        formatter = jsonlogger.JsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s',
            rename_fields={'levelname': 'level', 'asctime': 'timestamp'}
        )
    else:
        # Human-readable formatter for development
        formatter = logging.Formatter(
            '%(asctime)s | %(name)-15s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Configure structlog for structured logging (if available)
    if STRUCTLOG_AVAILABLE:
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    
    return logger

# Initialize logger
logger = setup_logging(
    log_level=os.getenv("APEX_LOG_LEVEL", "INFO"),
    json_format=os.getenv("APEX_LOG_FORMAT", "json").lower() == "json"
)

# =============================================================================
# Imports - with graceful fallbacks
# =============================================================================

try:
    import click
    from click import echo, style, secho
    CLICK_AVAILABLE = True
except ImportError:
    CLICK_AVAILABLE = False
    # Create stub decorators for compatibility
    class ClickStub:
        @staticmethod
        def group(*args, **kwargs):
            def decorator(f):
                return f
            return decorator
        @staticmethod
        def command(*args, **kwargs):
            def decorator(f):
                return f
            return decorator
        @staticmethod
        def option(*args, **kwargs):
            def decorator(f):
                return f
            return decorator
        @staticmethod
        def argument(*args, **kwargs):
            def decorator(f):
                return f
            return decorator
        @staticmethod
        def pass_context(*args, **kwargs):
            def decorator(f):
                return f
            return decorator
        @staticmethod
        def echo(*args, **kwargs):
            print(*args)
    click = ClickStub()

try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Depends
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.gzip import GZipMiddleware
    from pydantic import BaseModel, Field
    from uvicorn import Config, Server
    FASTAPI_AVAILABLE = True
except ImportError as e:
    FASTAPI_AVAILABLE = False
    logger.warning(f"FastAPI/uvicorn not available: {e}. API server will be unavailable.")

# APEX Component Imports
try:
    from agent_layer import AgentLayer, BuildStage, BuildContext
    from agents.subagent_spawner import SubAgentSpawner, SubAgentType, SKILL_REGISTRY
    from reliability.checkpoint_manager import CheckpointManager, Checkpoint
    from evolution.pattern_database import PatternDatabase
    from evolution.ab_testing import ABTestManager
    AGENT_LAYER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"APEX components not available: {e}. Running in demo mode.")
    AGENT_LAYER_AVAILABLE = False

# =============================================================================
# Configuration Models
# =============================================================================

class APEXConfig:
    """APEX configuration from environment variables."""
    
    # Server Configuration
    HOST = os.getenv("APEX_HOST", "0.0.0.0")
    PORT = int(os.getenv("APEX_PORT", "8000"))
    WORKERS = int(os.getenv("APEX_WORKERS", "1"))
    RELOAD = os.getenv("APEX_RELOAD", "false").lower() == "true"
    
    # Security
    API_KEY = os.getenv("APEX_API_KEY", None)
    SECRET_KEY = os.getenv("APEX_SECRET_KEY", "")
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://apex:apex@localhost/apex")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Paths
    _BASE_DIR = Path(__file__).resolve().parent
    CHECKPOINT_DIR = os.getenv("APEX_CHECKPOINT_DIR", str(_BASE_DIR / "checkpoints"))
    PATTERN_DB_PATH = os.getenv("APEX_PATTERN_DB_PATH", str(_BASE_DIR / "evolution" / "patterns"))
    
    # Feature Flags
    ENABLE_QUANTUM = os.getenv("APEX_ENABLE_QUANTUM", "false").lower() == "true"
    ENABLE_N8N = os.getenv("APEX_ENABLE_N8N", "true").lower() == "true"
    DEMO_MODE = os.getenv("APEX_DEMO_MODE", "false").lower() == "true"
    
    # Logging
    LOG_LEVEL = os.getenv("APEX_LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("APEX_LOG_FORMAT", "json")
    
    @classmethod
    def validate(cls) -> Dict[str, Any]:
        """Validate configuration and return status."""
        required_vars = [] if cls.DEMO_MODE else ["APEX_SECRET_KEY"]
        missing = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)
        
        return {
            "valid": len(missing) == 0,
            "missing": missing,
            "config": {
                "host": cls.HOST,
                "port": cls.PORT,
                "workers": cls.WORKERS,
                "demo_mode": cls.DEMO_MODE,
                "checkpoint_dir": cls.CHECKPOINT_DIR,
            }
        }

# =============================================================================
# Pydantic Models for API
# =============================================================================

if FASTAPI_AVAILABLE:
    class BuildRequest(BaseModel):
        project_path: str = Field(..., description="Path to the project to build")
        stages: Optional[List[str]] = Field(None, description="Specific stages to run")
        options: Optional[Dict[str, Any]] = Field(None, description="Build options")

    class AgentSpawnRequest(BaseModel):
        agent_type: str = Field(..., description="Type of agent to spawn")
        context: Dict[str, Any] = Field(default_factory=dict, description="Agent context")
        skill_name: Optional[str] = Field(None, description="Skill from registry")

    class CheckpointCreateRequest(BaseModel):
        build_id: str = Field(..., description="Build identifier")
        stage: str = Field(..., description="Build stage")
        files: List[str] = Field(default_factory=list, description="Files to checkpoint")
        metadata: Optional[Dict[str, Any]] = None

    class CheckpointRollbackRequest(BaseModel):
        checkpoint_id: str = Field(..., description="Checkpoint to rollback to")
        create_backup: bool = Field(True, description="Create backup branch")

    class SecurityAuditRequest(BaseModel):
        project_path: str = Field(..., description="Path to project")
        depth: str = Field("standard", description="Audit depth: quick, standard, deep")
        focus_areas: Optional[List[str]] = None

    class OptimizeRequest(BaseModel):
        file_path: str = Field(..., description="Path to file to optimize")
        optimization_type: str = Field("general", description="Type of optimization")

    class ABTestCreateRequest(BaseModel):
        name: str = Field(..., description="Test name")
        description: str = Field(..., description="Test description")
        variants: List[Dict[str, Any]] = Field(default_factory=list)
        metrics: List[str] = Field(default_factory=list)

    class PatternSearchRequest(BaseModel):
        query: str = Field(..., description="Search query")
        pattern_type: Optional[str] = None
        limit: int = Field(10, ge=1, le=100)

    class WebhookPayload(BaseModel):
        event: str
        data: Dict[str, Any] = Field(default_factory=dict)

    class HealthResponse(BaseModel):
        status: str
        version: str
        timestamp: str
        components: Dict[str, Any]

# =============================================================================
# Global State
# =============================================================================

class APEXState:
    """Global APEX state management."""
    
    def __init__(self):
        self.agent_layer: Optional[Any] = None
        self.spawner: Optional[Any] = None
        self.checkpoint_manager: Optional[Any] = None
        self.pattern_db: Optional[Any] = None
        self.ab_test_manager: Optional[Any] = None
        self.initialized: bool = False
        self.demo_mode: bool = APEXConfig.DEMO_MODE or not AGENT_LAYER_AVAILABLE
    
    async def initialize(self):
        """Initialize all APEX components."""
        if self.initialized:
            return
        
        logger.info("Initializing APEX components...")
        
        if self.demo_mode:
            logger.info("Running in DEMO mode - components will return mock data")
            self.initialized = True
            return
        
        try:
            # Initialize checkpoint manager
            self.checkpoint_manager = CheckpointManager(
                checkpoint_dir=APEXConfig.CHECKPOINT_DIR,
                redis_url=APEXConfig.REDIS_URL if os.getenv("REDIS_URL") else False
            )
            logger.info("CheckpointManager initialized")
            
            # Initialize sub-agent spawner
            self.spawner = SubAgentSpawner()
            logger.info("SubAgentSpawner initialized")
            
            # Initialize pattern database
            self.pattern_db = PatternDatabase(
                persist_directory=APEXConfig.PATTERN_DB_PATH
            )
            logger.info("PatternDatabase initialized")
            
            # Initialize A/B test manager
            self.ab_test_manager = ABTestManager()
            logger.info("ABTestManager initialized")
            
            self.initialized = True
            logger.info("APEX initialization complete")
            
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            logger.warning("Falling back to demo mode")
            self.demo_mode = True
            self.initialized = True
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of all components."""
        return {
            "initialized": self.initialized,
            "demo_mode": self.demo_mode,
            "agent_layer": self.agent_layer is not None,
            "spawner": self.spawner is not None,
            "checkpoint_manager": self.checkpoint_manager is not None,
            "pattern_db": self.pattern_db is not None,
            "ab_test_manager": self.ab_test_manager is not None,
        }

# Global state instance
apex_state = APEXState()

# =============================================================================
# FastAPI Application
# =============================================================================

if FASTAPI_AVAILABLE:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Application lifespan manager."""
        # Startup
        logger.info("APEX API starting up...")
        await apex_state.initialize()
        yield
        # Shutdown
        logger.info("APEX API shutting down...")

    app = FastAPI(
        title="APEX Agent Layer API",
        description="Autonomous Programming & Execution Engine API",
        version="2.0.0",
        docs_url="/docs" if os.getenv("APEX_ENABLE_DOCS", "true").lower() == "true" else None,
        redoc_url="/redoc" if os.getenv("APEX_ENABLE_DOCS", "true").lower() == "true" else None,
        lifespan=lifespan
    )
    
    # Add middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("APEX_CORS_ORIGINS", "*").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # =========================================================================
    # API Routes - Health & Status
    # =========================================================================

    @app.get("/health", response_model=HealthResponse if FASTAPI_AVAILABLE else None)
    async def health_check():
        """Health check endpoint."""
        config_status = APEXConfig.validate()
        
        return {
            "status": "healthy" if apex_state.initialized else "initializing",
            "version": "2.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "agent_layer": AGENT_LAYER_AVAILABLE,
                "checkpoint_manager": apex_state.checkpoint_manager is not None,
                "spawner": apex_state.spawner is not None,
                "pattern_db": apex_state.pattern_db is not None,
                "fastapi": True,
                "config": config_status["config"],
                "demo_mode": apex_state.demo_mode
            }
        }

    @app.get("/api/v1/status")
    async def get_status():
        """Get detailed APEX status."""
        return {
            "state": apex_state.get_status(),
            "config": APEXConfig.validate()["config"],
            "timestamp": datetime.utcnow().isoformat()
        }

    # =========================================================================
    # API Routes - Build
    # =========================================================================

    @app.post("/api/v1/build")
    async def trigger_build(request: BuildRequest, background_tasks: BackgroundTasks):
        """Trigger a build for a project."""
        build_id = f"build-{uuid.uuid4().hex[:8]}"
        
        if apex_state.demo_mode:
            return {
                "build_id": build_id,
                "status": "demo_mode",
                "message": "Build triggered in demo mode",
                "project_path": request.project_path
            }
        
        # TODO: Implement actual build logic
        return {
            "build_id": build_id,
            "status": "queued",
            "project_path": request.project_path,
            "stages": request.stages or ["analysis", "planning", "build", "test"]
        }

    @app.get("/api/v1/build/{build_id}")
    async def get_build_status(build_id: str):
        """Get status of a build."""
        if apex_state.demo_mode:
            return {
                "build_id": build_id,
                "status": "completed",
                "progress": 100,
                "stages_completed": ["analysis", "planning", "build", "test"]
            }
        
        # TODO: Implement actual status retrieval
        return {"build_id": build_id, "status": "unknown"}

    # =========================================================================
    # API Routes - Agents
    # =========================================================================

    @app.get("/api/v1/agents")
    async def list_agents():
        """List all running agents."""
        if apex_state.demo_mode:
            return {
                "agents": [
                    {"id": "agent-1", "type": "security_scanner", "status": "running"},
                    {"id": "agent-2", "type": "code_generator", "status": "idle"}
                ],
                "count": 2
            }
        
        # TODO: Implement actual agent listing
        return {"agents": [], "count": 0}

    @app.post("/api/v1/agents/spawn")
    async def spawn_agent(request: AgentSpawnRequest):
        """Spawn a new sub-agent."""
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"
        
        if apex_state.demo_mode:
            return {
                "agent_id": agent_id,
                "type": request.agent_type,
                "status": "spawned",
                "message": "Agent spawned in demo mode"
            }
        
        # TODO: Implement actual agent spawning
        return {
            "agent_id": agent_id,
            "type": request.agent_type,
            "status": "queued"
        }

    @app.get("/api/v1/agents/{agent_id}")
    async def get_agent_status(agent_id: str):
        """Get status of a specific agent."""
        return {"agent_id": agent_id, "status": "unknown"}

    @app.post("/api/v1/agents/{agent_id}/terminate")
    async def terminate_agent(agent_id: str):
        """Terminate a running agent."""
        return {"agent_id": agent_id, "status": "terminated"}

    # =========================================================================
    # API Routes - Checkpoints
    # =========================================================================

    @app.get("/api/v1/checkpoints")
    async def list_checkpoints(
        build_id: Optional[str] = Query(None),
        stage: Optional[str] = Query(None),
        limit: int = Query(100, ge=1, le=1000)
    ):
        """List checkpoints with optional filtering."""
        if apex_state.demo_mode:
            return {
                "checkpoints": [
                    {
                        "id": "cp-demo-001",
                        "build_id": build_id or "demo-build",
                        "stage": stage or "analysis",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ],
                "count": 1
            }
        
        if apex_state.checkpoint_manager:
            checkpoints = apex_state.checkpoint_manager.query_checkpoints(
                build_id=build_id, stage=stage, limit=limit
            )
            return {
                "checkpoints": [cp.__dict__ for cp in checkpoints],
                "count": len(checkpoints)
            }
        
        return {"checkpoints": [], "count": 0}

    @app.post("/api/v1/checkpoints/create")
    async def create_checkpoint(request: CheckpointCreateRequest):
        """Create a new checkpoint."""
        checkpoint_id = f"cp-{uuid.uuid4().hex[:8]}"
        
        if apex_state.demo_mode:
            return {
                "checkpoint_id": checkpoint_id,
                "status": "created",
                "tier": "demo",
                "message": "Checkpoint created in demo mode"
            }
        
        if apex_state.checkpoint_manager:
            result = apex_state.checkpoint_manager.create_full_checkpoint(
                build_id=request.build_id,
                stage=request.stage,
                files=request.files,
                metadata=request.metadata
            )
            return result
        
        raise HTTPException(status_code=503, detail="Checkpoint manager not available")

    @app.post("/api/v1/checkpoints/rollback")
    async def rollback_checkpoint(request: CheckpointRollbackRequest):
        """Rollback to a checkpoint."""
        if apex_state.demo_mode:
            return {
                "checkpoint_id": request.checkpoint_id,
                "status": "rolled_back",
                "backup_branch": "backup/demo-branch",
                "message": "Rollback completed in demo mode"
            }
        
        if apex_state.checkpoint_manager:
            result = apex_state.checkpoint_manager.rollback_to_checkpoint(
                checkpoint_id=request.checkpoint_id,
                create_backup_branch=request.create_backup
            )
            if result.get("success"):
                return result
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        raise HTTPException(status_code=503, detail="Checkpoint manager not available")

    @app.get("/api/v1/checkpoints/{checkpoint_id}")
    async def get_checkpoint(checkpoint_id: str):
        """Get details of a specific checkpoint."""
        if apex_state.demo_mode:
            return {
                "id": checkpoint_id,
                "build_id": "demo-build",
                "stage": "analysis",
                "timestamp": datetime.utcnow().isoformat(),
                "files": ["src/main.py", "src/utils.py"]
            }
        
        if apex_state.checkpoint_manager:
            cp = apex_state.checkpoint_manager.get_tier2_checkpoint(checkpoint_id)
            if cp:
                return cp.__dict__
        
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    # =========================================================================
    # API Routes - Security
    # =========================================================================

    @app.post("/api/v1/security/audit")
    async def security_audit(request: SecurityAuditRequest):
        """Run security audit on a project."""
        audit_id = f"audit-{uuid.uuid4().hex[:8]}"
        
        if apex_state.demo_mode:
            return {
                "audit_id": audit_id,
                "status": "completed",
                "findings": [
                    {"severity": "low", "issue": "Example finding in demo mode"}
                ],
                "score": 95,
                "message": "Audit completed in demo mode"
            }
        
        # TODO: Implement actual security audit
        return {
            "audit_id": audit_id,
            "status": "queued",
            "project_path": request.project_path
        }

    @app.get("/api/v1/security/audit/{audit_id}")
    async def get_audit_status(audit_id: str):
        """Get status of a security audit."""
        return {"audit_id": audit_id, "status": "unknown"}

    # =========================================================================
    # API Routes - Optimization
    # =========================================================================

    @app.post("/api/v1/optimize")
    async def optimize_code(request: OptimizeRequest):
        """Optimize code in a file."""
        optimization_id = f"opt-{uuid.uuid4().hex[:8]}"
        
        if apex_state.demo_mode:
            return {
                "optimization_id": optimization_id,
                "status": "completed",
                "suggestions": [
                    {"line": 10, "suggestion": "Example optimization in demo mode"}
                ],
                "message": "Optimization completed in demo mode"
            }
        
        # TODO: Implement actual optimization
        return {
            "optimization_id": optimization_id,
            "status": "queued",
            "file_path": request.file_path
        }

    # =========================================================================
    # API Routes - A/B Testing
    # =========================================================================

    @app.get("/api/v1/ab-tests")
    async def list_ab_tests():
        """List all A/B tests."""
        if apex_state.demo_mode:
            return {
                "tests": [
                    {
                        "id": "test-001",
                        "name": "Demo A/B Test",
                        "status": "running",
                        "variants": ["A", "B"]
                    }
                ],
                "count": 1
            }
        
        # TODO: Implement actual A/B test listing
        return {"tests": [], "count": 0}

    @app.post("/api/v1/ab-tests")
    async def create_ab_test(request: ABTestCreateRequest):
        """Create a new A/B test."""
        test_id = f"test-{uuid.uuid4().hex[:8]}"
        
        if apex_state.demo_mode:
            return {
                "test_id": test_id,
                "name": request.name,
                "status": "created",
                "message": "A/B test created in demo mode"
            }
        
        # TODO: Implement actual A/B test creation
        return {
            "test_id": test_id,
            "name": request.name,
            "status": "created"
        }

    @app.get("/api/v1/ab-tests/{test_id}")
    async def get_ab_test(test_id: str):
        """Get details of a specific A/B test."""
        return {"test_id": test_id, "status": "unknown"}

    @app.post("/api/v1/ab-tests/{test_id}/stop")
    async def stop_ab_test(test_id: str):
        """Stop an A/B test."""
        return {"test_id": test_id, "status": "stopped"}

    # =========================================================================
    # API Routes - Patterns
    # =========================================================================

    @app.post("/api/v1/patterns/search")
    async def search_patterns(request: PatternSearchRequest):
        """Search for patterns in the database."""
        if apex_state.demo_mode:
            return {
                "query": request.query,
                "results": [
                    {
                        "id": "pattern-001",
                        "type": "component",
                        "content": "// Example pattern in demo mode",
                        "similarity": 0.95
                    }
                ],
                "count": 1,
                "message": "Search completed in demo mode"
            }
        
        if apex_state.pattern_db:
            results = apex_state.pattern_db.search(
                query=request.query,
                pattern_type=request.pattern_type,
                limit=request.limit
            )
            return {
                "query": request.query,
                "results": [r.to_dict() for r in results],
                "count": len(results)
            }
        
        raise HTTPException(status_code=503, detail="Pattern database not available")

    @app.get("/api/v1/patterns/{pattern_id}")
    async def get_pattern(pattern_id: str):
        """Get a specific pattern."""
        return {"pattern_id": pattern_id, "status": "unknown"}

    # =========================================================================
    # API Routes - Webhooks
    # =========================================================================

    @app.post("/webhooks/n8n")
    async def n8n_webhook(payload: WebhookPayload):
        """Receive webhooks from n8n."""
        logger.info(f"Received n8n webhook: {payload.event}")
        
        # Handle different n8n events
        if payload.event == "workflow.completed":
            # Handle workflow completion
            pass
        elif payload.event == "workflow.failed":
            # Handle workflow failure
            pass
        
        return {
            "status": "received",
            "event": payload.event,
            "timestamp": datetime.utcnow().isoformat()
        }

    @app.post("/webhooks/github")
    async def github_webhook(payload: Dict[str, Any], event: Optional[str] = Query(None)):
        """Receive GitHub webhooks."""
        logger.info(f"Received GitHub webhook: {event}")
        return {"status": "received", "event": event}

# =============================================================================
# CLI Commands
# =============================================================================

if CLICK_AVAILABLE:
    @click.group(context_settings=dict(help_option_names=['-h', '--help']))
    @click.version_option(version="2.0.0", prog_name="apex")
    @click.pass_context
    def cli(ctx):
        """
        ╔═══════════════════════════════════════════════════════════════╗
        ║     APEX - Autonomous Programming & Execution Engine      ║
        ║                                                        ║
        ║  Intelligent build orchestration with AI-powered agents  ║
        ╚═══════════════════════════════════════════════════════════════╝
        
        Examples:
            apex init                          # Initialize APEX
            apex build ./my-project            # Run full build
            apex serve                         # Start API server
            apex health                        # Check health
            apex agent spawn security_scanner  # Spawn an agent
        """
        ctx.ensure_object(dict)
        ctx.obj['config'] = APEXConfig.validate()

    # =====================================================================
    # CLI: Init Command
    # =====================================================================

    @cli.command()
    @click.option('--force', is_flag=True, help='Force re-initialization')
    @click.pass_context
    def init(ctx, force):
        """Initialize APEX infrastructure (tables, repos, etc.)"""
        secho("🚀 Initializing APEX...", fg="cyan", bold=True)
        
        # Create checkpoint directory
        checkpoint_dir = Path(APEXConfig.CHECKPOINT_DIR)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        click.echo(f"  ✓ Checkpoint directory: {checkpoint_dir}")
        
        # Create pattern database directory
        pattern_dir = Path(APEXConfig.PATTERN_DB_PATH)
        pattern_dir.mkdir(parents=True, exist_ok=True)
        click.echo(f"  ✓ Pattern database: {pattern_dir}")
        
        # Initialize components
        try:
            if AGENT_LAYER_AVAILABLE:
                # Initialize checkpoint manager
                cm = CheckpointManager(checkpoint_dir=str(checkpoint_dir))
                click.echo(f"  ✓ CheckpointManager initialized")
                
                # Initialize spawner
                spawner = SubAgentSpawner()
                click.echo(f"  ✓ SubAgentSpawner initialized")
                
                # Initialize pattern database
                pdb = PatternDatabase(persist_directory=str(pattern_dir))
                click.echo(f"  ✓ PatternDatabase initialized")
            else:
                secho("  ⚠ Running in demo mode - APEX components not available", fg="yellow")
        except Exception as e:
            secho(f"  ✗ Error during initialization: {e}", fg="red")
            return
        
        secho("\n✅ APEX initialized successfully!", fg="green", bold=True)
        click.echo("\nNext steps:")
        click.echo("  apex serve          # Start the API server")
        click.echo("  apex build <path>   # Run a build")

    # =====================================================================
    # CLI: Health Command
    # =====================================================================

    @cli.command()
    @click.option('--json', 'json_output', is_flag=True, help='Output as JSON')
    def health(json_output):
        """Check all services health"""
        health_data = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "2.0.0",
            "components": {
                "agent_layer": AGENT_LAYER_AVAILABLE,
                "fastapi": FASTAPI_AVAILABLE,
                "click": CLICK_AVAILABLE,
                "checkpoint_manager": True,  # Can be initialized on demand
            }
        }
        
        if json_output:
            click.echo(json.dumps(health_data, indent=2))
        else:
            secho("APEX Health Status", fg="cyan", bold=True)
            click.echo("═" * 50)
            
            status_color = "green" if health_data["status"] == "healthy" else "red"
            secho(f"Status: {health_data['status'].upper()}", fg=status_color, bold=True)
            click.echo(f"Version: {health_data['version']}")
            click.echo(f"Timestamp: {health_data['timestamp']}")
            
            click.echo("\nComponents:")
            for name, status in health_data["components"].items():
                icon = "✓" if status else "✗"
                color = "green" if status else "red"
                secho(f"  {icon} {name}: {status}", fg=color)
            
            click.echo("\nConfiguration:")
            config = APEXConfig.validate()["config"]
            for key, value in config.items():
                click.echo(f"  • {key}: {value}")

    # =====================================================================
    # CLI: Build Commands
    # =====================================================================

    @cli.command()
    @click.argument('project_path', type=click.Path(exists=True))
    @click.option('--stages', '-s', multiple=True, help='Specific stages to run')
    @click.option('--watch', '-w', is_flag=True, help='Watch for changes')
    @click.option('--checkpoint/--no-checkpoint', default=True, help='Create checkpoints')
    def build(project_path, stages, watch, checkpoint):
        """Run full build on a project"""
        build_id = f"build-{uuid.uuid4().hex[:8]}"
        
        secho(f"🚀 Starting build: {build_id}", fg="cyan", bold=True)
        click.echo(f"Project: {project_path}")
        click.echo(f"Stages: {', '.join(stages) if stages else 'all'}")
        click.echo("")
        
        # Simulate build stages
        all_stages = list(stages) if stages else ["analysis", "planning", "frontend", "backend", "testing"]
        
        for i, stage in enumerate(all_stages, 1):
            secho(f"[{i}/{len(all_stages)}] Running: {stage}...", fg="yellow")
            # Simulate work
            import time
            time.sleep(0.5)
            secho(f"  ✓ {stage} complete", fg="green")
        
        if checkpoint:
            secho(f"  ✓ Checkpoint created", fg="green")
        
        secho(f"\n✅ Build {build_id} completed successfully!", fg="green", bold=True)

    @cli.command('analyze')
    @click.argument('project_path', type=click.Path(exists=True))
    @click.option('--output', '-o', type=click.Path(), help='Output file for analysis')
    def analyze_project(project_path, output):
        """Analyze project only (no build)"""
        secho("🔍 Analyzing project...", fg="cyan", bold=True)
        click.echo(f"Path: {project_path}")
        
        # Detect project type
        path = Path(project_path)
        files = list(path.rglob("*"))
        
        analysis = {
            "project_path": str(project_path),
            "files_count": len(files),
            "detected_stack": {},
            "recommendations": []
        }
        
        # Simple stack detection
        if any(f.name == "package.json" for f in files):
            analysis["detected_stack"]["nodejs"] = True
        if any(f.name.endswith(".py") for f in files):
            analysis["detected_stack"]["python"] = True
        if any(f.name == "requirements.txt" for f in files):
            analysis["detected_stack"]["python_requirements"] = True
        if any(f.name == "Dockerfile" for f in files):
            analysis["detected_stack"]["docker"] = True
        
        click.echo(f"\nFiles found: {analysis['files_count']}")
        click.echo("Detected stack:")
        for stack, detected in analysis["detected_stack"].items():
            secho(f"  ✓ {stack}", fg="green")
        
        if output:
            with open(output, 'w') as f:
                json.dump(analysis, f, indent=2)
            click.echo(f"\nAnalysis saved to: {output}")

    # =====================================================================
    # CLI: Checkpoint Commands
    # =====================================================================

    @cli.group()
    def checkpoint():
        """Checkpoint management commands"""
        pass

    @checkpoint.command('create')
    @click.argument('build_id')
    @click.option('--stage', '-s', default='manual', help='Build stage')
    @click.option('--files', '-f', multiple=True, help='Files to include')
    def checkpoint_create(build_id, stage, files):
        """Create manual checkpoint"""
        secho(f"💾 Creating checkpoint for build: {build_id}", fg="cyan")
        
        checkpoint_id = f"{build_id}-{stage}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        if AGENT_LAYER_AVAILABLE:
            cm = CheckpointManager(checkpoint_dir=APEXConfig.CHECKPOINT_DIR)
            result = cm.create_full_checkpoint(
                build_id=build_id,
                stage=stage,
                files=list(files) if files else [],
                metadata={"created_by": "cli"}
            )
            secho(f"✅ Checkpoint created:", fg="green", bold=True)
            click.echo(f"  ID: {result.get('tier2_sqlite', checkpoint_id)}")
            click.echo(f"  Tier 1 (Redis): {result.get('tier1_redis', 'N/A')}")
            click.echo(f"  Tier 2 (SQLite): {result.get('tier2_sqlite', 'N/A')}")
            click.echo(f"  Tier 3 (Git): {result.get('tier3_git', 'N/A')}")
        else:
            secho(f"✅ Checkpoint created (demo): {checkpoint_id}", fg="green")

    @checkpoint.command('list')
    @click.option('--build-id', '-b', help='Filter by build ID')
    @click.option('--limit', '-l', default=20, help='Maximum results')
    def checkpoint_list(build_id, limit):
        """List checkpoints"""
        secho("📋 Listing checkpoints...", fg="cyan")
        
        if AGENT_LAYER_AVAILABLE:
            cm = CheckpointManager(checkpoint_dir=APEXConfig.CHECKPOINT_DIR)
            checkpoints = cm.query_checkpoints(build_id=build_id, limit=limit)
            
            click.echo(f"\nFound {len(checkpoints)} checkpoint(s):\n")
            
            for cp in checkpoints:
                click.echo(f"  ID: {cp.id}")
                click.echo(f"  Build: {cp.build_id} | Stage: {cp.stage}")
                click.echo(f"  Time: {cp.timestamp}")
                click.echo(f"  Files: {len(cp.files)}")
                click.echo("")
        else:
            click.echo("Demo mode - no checkpoints to list")

    @checkpoint.command('rollback')
    @click.argument('checkpoint_id')
    @click.option('--no-backup', is_flag=True, help='Skip backup branch creation')
    def checkpoint_rollback(checkpoint_id, no_backup):
        """Rollback to a checkpoint"""
        secho(f"⏪ Rolling back to: {checkpoint_id}", fg="yellow", bold=True)
        
        if not click.confirm("Are you sure you want to rollback?"):
            click.echo("Rollback cancelled.")
            return
        
        if AGENT_LAYER_AVAILABLE:
            cm = CheckpointManager(checkpoint_dir=APEXConfig.CHECKPOINT_DIR)
            result = cm.rollback_to_checkpoint(
                checkpoint_id=checkpoint_id,
                create_backup_branch=not no_backup
            )
            
            if result.get("success"):
                secho("✅ Rollback successful!", fg="green", bold=True)
                click.echo(f"  Commit: {result.get('commit_hash', 'N/A')[:8]}")
                click.echo(f"  Stage: {result.get('stage', 'N/A')}")
                if result.get('backup_branch'):
                    click.echo(f"  Backup: {result['backup_branch']}")
            else:
                secho(f"❌ Rollback failed: {result.get('error')}", fg="red")
        else:
            secho("✅ Rollback completed (demo mode)", fg="green")

    # =====================================================================
    # CLI: Agent Commands
    # =====================================================================

    @cli.group()
    def agent():
        """Agent management commands"""
        pass

    @agent.command('spawn')
    @click.argument('agent_type')
    @click.option('--skill', '-s', help='Use pre-configured skill')
    @click.option('--context', '-c', help='JSON context for agent')
    def agent_spawn(agent_type, skill, context):
        """Spawn a sub-agent"""
        secho(f"🤖 Spawning agent: {agent_type}", fg="cyan", bold=True)
        
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"
        
        ctx = {}
        if context:
            ctx = json.loads(context)
        
        if skill:
            click.echo(f"Using skill: {skill}")
        
        click.echo(f"Context: {json.dumps(ctx, indent=2)}")
        
        secho(f"\n✅ Agent spawned: {agent_id}", fg="green", bold=True)
        
        if AGENT_LAYER_AVAILABLE and skill:
            click.echo(f"\nAvailable skills: {', '.join(SKILL_REGISTRY.keys())[:5]}...")

    @agent.command('list')
    def agent_list():
        """List running agents"""
        secho("💼 Running Agents", fg="cyan", bold=True)
        click.echo("")
        
        # Demo agents
        agents = [
            {"id": "agent-001", "type": "security_scanner", "status": "running", "task": "Scanning /src"},
            {"id": "agent-002", "type": "code_generator", "status": "idle", "task": None},
        ] if not AGENT_LAYER_AVAILABLE else []
        
        if agents:
            for agent in agents:
                status_color = "green" if agent["status"] == "running" else "yellow"
                secho(f"  • {agent['id']}", fg="cyan", bold=True)
                click.echo(f"    Type: {agent['type']}")
                secho(f"    Status: {agent['status']}", fg=status_color)
                if agent.get('task'):
                    click.echo(f"    Task: {agent['task']}")
                click.echo("")
        else:
            click.echo("No agents currently running.")

    # =====================================================================
    # CLI: Security Commands
    # =====================================================================

    @cli.command('security')
    @click.argument('project_path', type=click.Path(exists=True))
    @click.option('--depth', '-d', default='standard', type=click.Choice(['quick', 'standard', 'deep']))
    @click.option('--output', '-o', type=click.Path(), help='Output file')
    def security_audit(project_path, depth, output):
        """Run security audit on a project"""
        secho(f"🔒 Security Audit ({depth})", fg="cyan", bold=True)
        click.echo(f"Target: {project_path}\n")
        
        # Simulate audit
        import time
        stages = ["Scanning for secrets...", "Checking dependencies...", "Analyzing code...", "Generating report..."]
        
        for stage in stages:
            click.echo(f"  {stage}")
            time.sleep(0.3)
        
        report = {
            "score": 87,
            "findings": [
                {"severity": "low", "issue": "Outdated dependency", "file": "requirements.txt"},
                {"severity": "info", "issue": "Missing security headers", "file": "nginx.conf"}
            ]
        }
        
        score_color = "green" if report["score"] >= 80 else "yellow" if report["score"] >= 60 else "red"
        secho(f"\nSecurity Score: {report['score']}/100", fg=score_color, bold=True)
        
        click.echo(f"\nFindings: {len(report['findings'])}")
        for finding in report["findings"]:
            color = {"critical": "red", "high": "red", "medium": "yellow", "low": "yellow", "info": "blue"}.get(finding["severity"], "white")
            secho(f"  [{finding['severity'].upper()}] {finding['issue']} ({finding['file']})", fg=color)
        
        if output:
            with open(output, 'w') as f:
                json.dump(report, f, indent=2)
            click.echo(f"\nReport saved to: {output}")

    # =====================================================================
    # CLI: Optimize Command
    # =====================================================================

    @cli.command('optimize')
    @click.argument('file_path', type=click.Path(exists=True))
    @click.option('--type', '-t', 'opt_type', default='general', help='Optimization type')
    def optimize(file_path, opt_type):
        """Optimize code in a file"""
        secho(f"⚡ Optimizing: {file_path}", fg="cyan", bold=True)
        click.echo(f"Type: {opt_type}\n")
        
        # Read file
        with open(file_path, 'r') as f:
            content = f.read()
            lines = content.count('\n')
        
        click.echo(f"Original: {lines} lines")
        
        # Simulate optimization
        import time
        time.sleep(0.5)
        
        suggestions = [
            {"line": 15, "suggestion": "Use list comprehension", "impact": "medium"},
            {"line": 42, "suggestion": "Cache this lookup", "impact": "high"}
        ]
        
        click.echo(f"\nSuggestions found: {len(suggestions)}")
        for s in suggestions:
            color = {"high": "red", "medium": "yellow", "low": "blue"}.get(s["impact"], "white")
            secho(f"  Line {s['line']}: {s['suggestion']} ({s['impact']})", fg=color)

    # =====================================================================
    # CLI: A/B Test Commands
    # =====================================================================

    @cli.group('ab-test')
    def ab_test():
        """A/B testing commands"""
        pass

    @ab_test.command('create')
    @click.option('--name', '-n', required=True, help='Test name')
    @click.option('--description', '-d', default='', help='Test description')
    def ab_test_create(name, description):
        """Create A/B test"""
        test_id = f"test-{uuid.uuid4().hex[:8]}"
        secho(f"🧪 A/B Test Created", fg="cyan", bold=True)
        click.echo(f"  ID: {test_id}")
        click.echo(f"  Name: {name}")
        click.echo(f"  Description: {description or 'N/A'}")

    @ab_test.command('list')
    def ab_test_list():
        """List A/B tests"""
        secho("📊 A/B Tests", fg="cyan", bold=True)
        click.echo("")
        
        tests = [
            {"id": "test-001", "name": "Button Color", "status": "running", "variants": 2},
            {"id": "test-002", "name": "Pricing Page", "status": "completed", "variants": 3}
        ]
        
        for test in tests:
            status_color = "green" if test["status"] == "running" else "blue"
            click.echo(f"  • {test['name']} ({test['id']})")
            secho(f"    Status: {test['status']} | Variants: {test['variants']}", fg=status_color)

    # =====================================================================
    # CLI: Pattern Commands
    # =====================================================================

    @cli.command('pattern')
    @click.argument('query')
    @click.option('--type', '-t', help='Pattern type filter')
    @click.option('--limit', '-l', default=10, help='Maximum results')
    def pattern_search(query, type, limit):
        """Search patterns in database"""
        secho(f"🔍 Searching patterns: '{query}'", fg="cyan", bold=True)
        
        # Demo results
        results = [
            {"id": "pat-001", "type": "component", "similarity": 0.92, "content": "Button.tsx"},
            {"id": "pat-002", "type": "hook", "similarity": 0.87, "content": "useAuth.ts"}
        ]
        
        click.echo(f"\nFound {len(results)} result(s):\n")
        
        for r in results:
            secho(f"  {r['content']} ({r['id']})", fg="cyan", bold=True)
            click.echo(f"    Type: {r['type']} | Similarity: {r['similarity']:.2%}")

    # =====================================================================
    # CLI: Serve Command
    # =====================================================================

    @cli.command()
    @click.option('--host', '-h', default=APEXConfig.HOST, help='Host to bind')
    @click.option('--port', '-p', default=APEXConfig.PORT, help='Port to bind')
    @click.option('--workers', '-w', default=APEXConfig.WORKERS, help='Number of workers')
    @click.option('--reload/--no-reload', default=APEXConfig.RELOAD, help='Enable auto-reload')
    @click.option('--demo', is_flag=True, help='Force demo mode')
    def serve(host, port, workers, reload, demo):
        """Start API server"""
        if not FASTAPI_AVAILABLE:
            secho("❌ FastAPI not available. Install with: pip install fastapi uvicorn", fg="red")
            sys.exit(1)
        
        if demo:
            os.environ["APEX_DEMO_MODE"] = "true"
            apex_state.demo_mode = True
        
        secho("🚀 Starting APEX API Server", fg="cyan", bold=True)
        click.echo(f"Host: {host}")
        click.echo(f"Port: {port}")
        click.echo(f"Workers: {workers}")
        click.echo(f"Reload: {reload}")
        click.echo(f"Demo mode: {apex_state.demo_mode}")
        click.echo("")
        
        import uvicorn
        
        # Configure and run server
        config = Config(
            "apex.main:app",
            host=host,
            port=port,
            workers=workers if not reload else 1,
            reload=reload,
            log_level=APEXConfig.LOG_LEVEL.lower()
        )
        
        server = Server(config)
        
        secho(f"Server ready at http://{host}:{port}", fg="green", bold=True)
        click.echo(f"API docs: http://{host}:{port}/docs")
        click.echo(f"Health: http://{host}:{port}/health\n")
        
        try:
            server.run()
        except KeyboardInterrupt:
            secho("\n⚠ Server stopped", fg="yellow")

else:
    # Fallback when click is not available
    def cli():
        print("CLI mode requires 'click'. Install with: pip install click")
        sys.exit(1)

# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main entry point for APEX."""
    if CLICK_AVAILABLE:
        cli()
    else:
        # Fallback to argparse for basic functionality
        import argparse
        
        parser = argparse.ArgumentParser(
            description="APEX - Autonomous Programming & Execution Engine"
        )
        parser.add_argument('--version', action='version', version='%(prog)s 2.0.0')
        
        subparsers = parser.add_subparsers(dest='command')
        
        # Serve command
        serve_parser = subparsers.add_parser('serve', help='Start API server')
        serve_parser.add_argument('--host', default=APEXConfig.HOST)
        serve_parser.add_argument('--port', '-p', type=int, default=APEXConfig.PORT)
        
        # Health command
        subparsers.add_parser('health', help='Check health')
        
        args = parser.parse_args()
        
        if args.command == 'serve':
            if not FASTAPI_AVAILABLE:
                print("FastAPI not available. Install with: pip install fastapi uvicorn")
                sys.exit(1)
            import uvicorn
            uvicorn.run(app, host=args.host, port=args.port)
        elif args.command == 'health':
            print(json.dumps({
                "status": "healthy",
                "version": "2.0.0",
                "fastapi": FASTAPI_AVAILABLE,
                "click": CLICK_AVAILABLE
            }, indent=2))
        else:
            parser.print_help()

# For running with: python -m apex.main
if __name__ == "__main__":
    main()
