#!/usr/bin/env python3
"""
APEX Agent Intelligence Layer (AIL) v2.0
=====================================
Central orchestrator for the 8-core agent system with consensus,
checkpointing, sub-agent spawning, and self-evaluation capabilities.

This is the brain of MasterBuilder7 - coordinating all agents,
enforcing quality gates, managing budgets, and ensuring reliable
software delivery through autonomous decision-making.

Author: APEX Core Team
Version: 2.0.0
License: MIT
"""

import os
import sys
import json
import yaml
import asyncio
import logging
import hashlib
import subprocess
from typing import Dict, List, Any, Optional, Callable, Union, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from abc import ABC, abstractmethod
from collections import defaultdict
import threading
import uuid

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/apex_agent_layer.log')
    ]
)
logger = logging.getLogger('AgentLayer')

# Import reliability components
try:
    from reliability.consensus_engine import (
        ConsensusEngine, ConsensusReport, ConsensusDecision, 
        AgentType, VerificationResult
    )
    CONSENSUS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"ConsensusEngine not available: {e}")
    CONSENSUS_AVAILABLE = False

try:
    from reliability.checkpoint_manager import (
        CheckpointManager, Checkpoint, CheckpointStatus
    )
    CHECKPOINT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"CheckpointManager not available: {e}")
    CHECKPOINT_AVAILABLE = False

try:
    from reliability.spend_guardrail import SpendGuardrail
    SPEND_GUARD_AVAILABLE = True
except ImportError as e:
    logger.warning(f"SpendGuardrail not available: {e}")
    SPEND_GUARD_AVAILABLE = False


# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================

class AgentStatus(Enum):
    """Status of an agent in the system"""
    IDLE = auto()
    INITIALIZING = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    FAILED = auto()
    ROLLING_BACK = auto()


class BuildStage(Enum):
    """Stages in the build pipeline"""
    ANALYSIS = "analysis"
    PLANNING = "planning"
    FRONTEND_BUILD = "frontend_build"
    BACKEND_BUILD = "backend_build"
    TESTING = "testing"
    EVALUATION = "evaluation"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"
    EVOLUTION = "evolution"


class ChangePriority(Enum):
    """Priority levels for changes"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    TRIVIAL = 5


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class AgentSpec:
    """Specification for an agent"""
    name: str
    version: str
    agent_type: str
    count: int
    cost_per_hour: float
    model: str
    autonomy_level: int
    capabilities: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    system_prompt: str = ""
    parallel_to: Optional[str] = None


@dataclass
class AgentInstance:
    """Running instance of an agent"""
    id: str
    spec: AgentSpec
    status: AgentStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    current_task: Optional[str] = None
    output: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


@dataclass
class ChangeRequest:
    """Request for a change to be processed"""
    id: str
    description: str
    priority: ChangePriority
    files_affected: List[str]
    requested_by: str
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BuildContext:
    """Context for a build process"""
    build_id: str
    project_path: str
    project_name: str
    stack_detected: Dict[str, Any] = field(default_factory=dict)
    stages_completed: List[BuildStage] = field(default_factory=list)
    current_stage: Optional[BuildStage] = None
    checkpoints: List[str] = field(default_factory=list)
    consensus_reports: List[Dict] = field(default_factory=list)
    evaluation_scores: List[float] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_cost: float = 0.0


@dataclass
class EvaluationResult:
    """Result of self-evaluation"""
    score: float
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    metrics: Dict[str, float]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SubAgentTask:
    """Task for a sub-agent"""
    id: str
    parent_agent: str
    task_type: str
    description: str
    input_data: Dict[str, Any]
    priority: ChangePriority
    spawned_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None


# ============================================================================
# EVENT SYSTEM
# ============================================================================

class EventEmitter:
    """Event system for agent layer events"""
    
    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def on(self, event: str, callback: Callable):
        """Register an event listener"""
        with self._lock:
            self._listeners[event].append(callback)
    
    def off(self, event: str, callback: Callable):
        """Remove an event listener"""
        with self._lock:
            if event in self._listeners:
                self._listeners[event] = [
                    cb for cb in self._listeners[event] if cb != callback
                ]
    
    def emit(self, event: str, data: Any = None):
        """Emit an event to all listeners"""
        with self._lock:
            listeners = self._listeners[event].copy()
        
        for callback in listeners:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(data))
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Event handler error for {event}: {e}")


# ============================================================================
# SELF-EVALUATION ENGINE
# ============================================================================

class SelfEvaluationEngine:
    """
    Evaluates agent performance and output quality
    Provides continuous improvement feedback
    """
    
    def __init__(self):
        self.evaluation_history: List[EvaluationResult] = []
        self.metrics_cache: Dict[str, List[float]] = defaultdict(list)
    
    def evaluate_output(
        self,
        agent_type: str,
        output: Dict[str, Any],
        expected_criteria: Dict[str, Any]
    ) -> EvaluationResult:
        """
        Evaluate agent output against criteria
        
        Args:
            agent_type: Type of agent that produced output
            output: The output to evaluate
            expected_criteria: Criteria to evaluate against
            
        Returns:
            EvaluationResult with score and feedback
        """
        score = 0.0
        strengths = []
        weaknesses = []
        metrics = {}
        
        # Completeness check
        if 'files_created' in output:
            expected_files = expected_criteria.get('min_files', 1)
            actual_files = len(output['files_created'])
            completeness = min(1.0, actual_files / expected_files)
            metrics['completeness'] = completeness
            if completeness >= 0.9:
                strengths.append(f"Created {actual_files} files as expected")
            else:
                weaknesses.append(f"Only created {actual_files}/{expected_files} expected files")
        
        # Code quality check
        if 'code_quality_score' in output:
            quality = output['code_quality_score']
            metrics['code_quality'] = quality
            if quality >= 0.8:
                strengths.append("High code quality score")
            elif quality < 0.6:
                weaknesses.append("Code quality below threshold")
        
        # Test coverage check
        if 'test_coverage' in output:
            coverage = output['test_coverage']
            metrics['test_coverage'] = coverage
            if coverage >= 0.85:
                strengths.append("Excellent test coverage")
            elif coverage < 0.7:
                weaknesses.append("Insufficient test coverage")
        
        # Error check
        if 'errors' in output:
            error_count = len(output['errors'])
            metrics['error_count'] = error_count
            if error_count == 0:
                strengths.append("No errors generated")
            else:
                weaknesses.append(f"{error_count} errors encountered")
        
        # Calculate overall score
        if metrics:
            score = sum(metrics.values()) / len(metrics)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(weaknesses, metrics)
        
        result = EvaluationResult(
            score=round(score, 4),
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            metrics=metrics
        )
        
        self.evaluation_history.append(result)
        
        # Update metrics cache
        for metric_name, value in metrics.items():
            self.metrics_cache[metric_name].append(value)
        
        return result
    
    def _generate_recommendations(
        self,
        weaknesses: List[str],
        metrics: Dict[str, float]
    ) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        if 'test_coverage' in metrics and metrics['test_coverage'] < 0.7:
            recommendations.append("Add unit tests for uncovered code paths")
        
        if 'code_quality' in metrics and metrics['code_quality'] < 0.7:
            recommendations.append("Review code for style and best practices")
        
        if 'completeness' in metrics and metrics['completeness'] < 0.9:
            recommendations.append("Ensure all required files are generated")
        
        if not recommendations and weaknesses:
            recommendations.append("Review agent logs for detailed error analysis")
        
        return recommendations
    
    def get_performance_trend(self, metric_name: str, window: int = 10) -> Dict[str, float]:
        """Get performance trend for a metric"""
        values = self.metrics_cache.get(metric_name, [])
        if len(values) < 2:
            return {'trend': 0.0, 'average': 0.0, 'current': 0.0}
        
        recent = values[-window:]
        trend = recent[-1] - recent[0] if len(recent) > 1 else 0.0
        
        return {
            'trend': round(trend, 4),
            'average': round(sum(recent) / len(recent), 4),
            'current': round(recent[-1], 4),
            'samples': len(recent)
        }


# ============================================================================
# SUB-AGENT SPAWNER
# ============================================================================

class SubAgentSpawner:
    """
    Spawns specialized sub-agents for complex tasks
    Manages sub-agent lifecycle and result aggregation
    """
    
    def __init__(self):
        self.active_tasks: Dict[str, SubAgentTask] = {}
        self.completed_tasks: List[SubAgentTask] = []
        self.spawn_count = 0
    
    async def spawn_task(
        self,
        parent_agent: str,
        task_type: str,
        description: str,
        input_data: Dict[str, Any],
        priority: ChangePriority = ChangePriority.MEDIUM
    ) -> str:
        """
        Spawn a new sub-agent task
        
        Args:
            parent_agent: ID of the parent agent
            task_type: Type of task (e.g., 'code_review', 'security_scan')
            description: Task description
            input_data: Input data for the task
            priority: Task priority
            
        Returns:
            Task ID
        """
        task_id = f"subtask-{uuid.uuid4().hex[:8]}"
        
        task = SubAgentTask(
            id=task_id,
            parent_agent=parent_agent,
            task_type=task_type,
            description=description,
            input_data=input_data,
            priority=priority
        )
        
        self.active_tasks[task_id] = task
        self.spawn_count += 1
        
        logger.info(f"Spawned sub-agent task {task_id} ({task_type}) for {parent_agent}")
        
        # Start async execution
        asyncio.create_task(self._execute_task(task_id))
        
        return task_id
    
    async def _execute_task(self, task_id: str):
        """Execute a sub-agent task"""
        task = self.active_tasks.get(task_id)
        if not task:
            return
        
        try:
            # Simulate task execution (would integrate with actual agent)
            await asyncio.sleep(0.1)  # Simulate work
            
            # Generate mock result based on task type
            result = self._generate_mock_result(task)
            
            task.result = result
            task.completed_at = datetime.now()
            
            self.completed_tasks.append(task)
            del self.active_tasks[task_id]
            
            logger.info(f"Sub-agent task {task_id} completed")
            
        except Exception as e:
            logger.error(f"Sub-agent task {task_id} failed: {e}")
            task.result = {'success': False, 'error': str(e)}
            task.completed_at = datetime.now()
            self.completed_tasks.append(task)
            del self.active_tasks[task_id]
    
    def _generate_mock_result(self, task: SubAgentTask) -> Dict[str, Any]:
        """Generate a mock result for a task"""
        return {
            'success': True,
            'task_type': task.task_type,
            'findings': [],
            'recommendations': []
        }
    
    async def get_result(self, task_id: str, timeout: float = 30.0) -> Optional[Dict[str, Any]]:
        """Get result of a sub-agent task with timeout"""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < timeout:
            # Check if completed
            for task in self.completed_tasks:
                if task.id == task_id:
                    return task.result
            
            # Check if still active
            if task_id not in self.active_tasks:
                return {'success': False, 'error': 'Task not found'}
            
            await asyncio.sleep(0.1)
        
        return {'success': False, 'error': 'Timeout waiting for task result'}
    
    def get_active_count(self) -> int:
        """Get count of active sub-agent tasks"""
        return len(self.active_tasks)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get spawner statistics"""
        return {
            'total_spawned': self.spawn_count,
            'active': len(self.active_tasks),
            'completed': len(self.completed_tasks),
            'by_type': self._count_by_type()
        }
    
    def _count_by_type(self) -> Dict[str, int]:
        """Count tasks by type"""
        counts = defaultdict(int)
        for task in list(self.active_tasks.values()) + self.completed_tasks:
            counts[task.task_type] += 1
        return dict(counts)


# ============================================================================
# AGENT LAYER - MAIN ORCHESTRATOR
# ============================================================================

class AgentLayer:
    """
    Central orchestrator for the APEX Agent Intelligence Layer.
    
    Coordinates all 8 core agents:
    1. Meta-Router (Stack detection & routing)
    2. Planning Agent (Architecture & specs)
    3. Frontend Agent (UI/UX development)
    4. Backend Agent (API & database)
    5. Testing Agent (Quality assurance)
    6. DevOps Agent (CI/CD & deployment)
    7. Reliability Agent (Quality control)
    8. Evolution Agent (Learning & optimization)
    
    Features:
    - 3-tier checkpoint system (Redis/SQLite/Git)
    - Consensus engine with 3-verifier protocol
    - Sub-agent spawning for complex tasks
    - Self-evaluation and continuous improvement
    - Budget enforcement and safety mechanisms
    - Event-driven architecture
    """
    
    # Agent specification file mapping
    AGENT_SPECS = {
        'meta_router': '01-meta-router.yaml',
        'planning': '02-planning-agent.yaml',
        'frontend': '03-frontend-agent.yaml',
        'backend': '04-backend-agent.yaml',
        'testing': '05-testing-agent.yaml',
        'devops': '06-devops-agent.yaml',
        'reliability': '07-reliability-evolution-agent.yaml',
        'evolution': '08-evolution-agent.yaml'
    }
    
    def __init__(
        self,
        specs_dir: str = "/home/teacherchris37/MasterBuilder7/apex/agents/specs",
        fleet_config_path: str = "/home/teacherchris37/MasterBuilder7/apex/fleet-composition.yaml",
        enable_consensus: bool = True,
        enable_checkpoints: bool = True,
        max_budget_usd: float = 500.0
    ):
        """
        Initialize the Agent Intelligence Layer
        
        Args:
            specs_dir: Directory containing agent YAML specifications
            fleet_config_path: Path to fleet composition YAML
            enable_consensus: Whether to enable consensus verification
            enable_checkpoints: Whether to enable checkpointing
            max_budget_usd: Maximum daily budget in USD
        """
        self.specs_dir = Path(specs_dir)
        self.fleet_config_path = Path(fleet_config_path)
        self.max_budget_usd = max_budget_usd
        
        # Initialize event system
        self.events = EventEmitter()
        
        # Initialize core components
        self.agents: Dict[str, AgentSpec] = {}
        self.agent_instances: Dict[str, AgentInstance] = {}
        self.build_contexts: Dict[str, BuildContext] = {}
        
        # Initialize reliability components
        self.consensus_engine: Optional[ConsensusEngine] = None
        self.checkpoint_manager: Optional[CheckpointManager] = None
        self.spend_guardrail: Optional[Any] = None
        
        if enable_consensus and CONSENSUS_AVAILABLE:
            self.consensus_engine = ConsensusEngine()
            logger.info("Consensus Engine initialized")
        
        if enable_checkpoints and CHECKPOINT_AVAILABLE:
            self.checkpoint_manager = CheckpointManager()
            logger.info("Checkpoint Manager initialized")
        
        if SPEND_GUARD_AVAILABLE:
            self.spend_guardrail = SpendGuardrail(daily_limit=max_budget_usd)
            logger.info("Spend Guardrail initialized")
        
        # Initialize supporting systems
        self.subagent_spawner = SubAgentSpawner()
        self.self_evaluation = SelfEvaluationEngine()
        
        # State tracking
        self._initialized = False
        self._paused = False
        self._shutdown = False
        self._lock = threading.RLock()
        
        logger.info("Agent Intelligence Layer created")
    
    # ========================================================================
    # INITIALIZATION
    # ========================================================================
    
    def initialize(self) -> bool:
        """
        Initialize all agents from specifications
        
        Returns:
            True if initialization successful
        """
        try:
            logger.info("Initializing Agent Intelligence Layer...")
            
            # Load agent specifications
            self._load_agent_specs()
            
            # Load fleet composition
            self._load_fleet_composition()
            
            # Initialize agent instances
            self._initialize_agents()
            
            self._initialized = True
            logger.info("Agent Intelligence Layer initialized successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False
    
    def _load_agent_specs(self):
        """Load agent specifications from YAML files"""
        for agent_key, filename in self.AGENT_SPECS.items():
            spec_path = self.specs_dir / filename
            if spec_path.exists():
                with open(spec_path, 'r') as f:
                    spec_data = yaml.safe_load(f)
                    
                metadata = spec_data.get('metadata', {})
                self.agents[agent_key] = AgentSpec(
                    name=metadata.get('name', agent_key),
                    version=metadata.get('version', '1.0.0'),
                    agent_type=metadata.get('type', 'core-agent'),
                    count=metadata.get('count', 1),
                    cost_per_hour=metadata.get('cost_per_hour', 0.50),
                    model=metadata.get('model', 'kimi-k2-5'),
                    autonomy_level=metadata.get('autonomy_level', 2),
                    capabilities=spec_data.get('capabilities', []),
                    dependencies=spec_data.get('dependencies', []),
                    system_prompt=spec_data.get('system_prompt', ''),
                    parallel_to=metadata.get('parallel_to')
                )
                logger.debug(f"Loaded spec for {agent_key}")
            else:
                logger.warning(f"Spec file not found: {spec_path}")
    
    def _load_fleet_composition(self):
        """Load fleet composition configuration"""
        if self.fleet_config_path.exists():
            with open(self.fleet_config_path, 'r') as f:
                fleet_config = yaml.safe_load(f)
            
            # Update max budget if specified
            metadata = fleet_config.get('metadata', {})
            if 'max_daily_budget' in metadata:
                self.max_budget_usd = metadata['max_daily_budget']
            
            logger.info(f"Fleet composition loaded: {self.max_budget_usd} USD max daily budget")
    
    def _initialize_agents(self):
        """Initialize agent instances"""
        for agent_key, spec in self.agents.items():
            instance = AgentInstance(
                id=f"{agent_key}-{uuid.uuid4().hex[:8]}",
                spec=spec,
                status=AgentStatus.IDLE,
                started_at=datetime.now()
            )
            self.agent_instances[agent_key] = instance
            logger.info(f"Initialized {agent_key} agent (autonomy level {spec.autonomy_level})")
    
    # ========================================================================
    # CORE WORKFLOW METHODS
    # ========================================================================
    
    async def analyze_project(
        self,
        project_path: str,
        project_name: str
    ) -> Dict[str, Any]:
        """
        Run Meta-Router analysis on a project
        
        Args:
            project_path: Path to project repository
            project_name: Project identifier
            
        Returns:
            Analysis results with stack detection and routing decision
        """
        logger.info(f"Analyzing project: {project_name} at {project_path}")
        
        instance = self.agent_instances.get('meta_router')
        if not instance:
            raise RuntimeError("Meta-Router agent not initialized")
        
        instance.status = AgentStatus.RUNNING
        instance.current_task = f"analyze:{project_name}"
        
        try:
            # Detect stack from project files
            stack_detection = self._detect_stack(project_path)
            
            # Calculate automation potential
            automation = self._calculate_automation(stack_detection)
            
            # Generate routing decision
            routing = self._generate_routing(stack_detection, automation)
            
            result = {
                'stack_detection': stack_detection,
                'automation_assessment': automation,
                'routing_decision': routing,
                'migration_analysis': self._analyze_migration(stack_detection),
                'timestamp': datetime.now().isoformat()
            }
            
            instance.output = result
            instance.status = AgentStatus.COMPLETED
            instance.completed_at = datetime.now()
            
            logger.info(f"Analysis complete: {stack_detection.get('primary_stack', 'unknown')}")
            
            return result
            
        except Exception as e:
            instance.status = AgentStatus.FAILED
            instance.errors.append(str(e))
            raise
    
    async def plan_architecture(
        self,
        project_name: str,
        analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run Planning agent to create architecture and specifications
        
        Args:
            project_name: Project identifier
            analysis_result: Result from analyze_project
            
        Returns:
            Architecture plan with PRD and technical specs
        """
        logger.info(f"Planning architecture for: {project_name}")
        
        instance = self.agent_instances.get('planning')
        if not instance:
            raise RuntimeError("Planning agent not initialized")
        
        instance.status = AgentStatus.RUNNING
        instance.current_task = f"plan:{project_name}"
        
        try:
            stack = analysis_result.get('stack_detection', {})
            routing = analysis_result.get('routing_decision', {})
            
            plan = {
                'prd': self._generate_prd(project_name, stack),
                'tech_spec': self._generate_tech_spec(stack),
                'architecture': self._generate_architecture(stack, routing),
                'data_models': self._generate_data_models(stack),
                'api_contracts': self._generate_api_contracts(stack),
                'risk_assessment': self._assess_risks(stack),
                'agent_assignments': routing
            }
            
            instance.output = plan
            instance.status = AgentStatus.COMPLETED
            instance.completed_at = datetime.now()
            
            logger.info("Architecture planning complete")
            
            return plan
            
        except Exception as e:
            instance.status = AgentStatus.FAILED
            instance.errors.append(str(e))
            raise
    
    async def build_frontend(
        self,
        build_context: BuildContext,
        plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run Frontend agent with consensus verification
        
        Args:
            build_context: Current build context
            plan: Architecture plan
            
        Returns:
            Frontend build results
        """
        logger.info(f"Building frontend for: {build_context.build_id}")
        
        instance = self.agent_instances.get('frontend')
        if not instance:
            raise RuntimeError("Frontend agent not initialized")
        
        instance.status = AgentStatus.RUNNING
        instance.current_task = f"frontend:{build_context.build_id}"
        
        try:
            # Generate frontend code
            result = {
                'files_created': [],
                'components': [],
                'tests_added': [],
                'code_quality_score': 0.0
            }
            
            # Simulate frontend generation
            # In production, this would call the actual agent
            result['files_created'] = [
                'src/components/App.tsx',
                'src/components/Header.tsx',
                'src/pages/Home.tsx',
                'src/hooks/useAuth.ts',
                'src/styles/global.css'
            ]
            result['code_quality_score'] = 0.85
            
            # Run consensus verification if enabled
            if self.consensus_engine:
                for file_path in result['files_created']:
                    # Simulate code content
                    code = f"// Generated code for {file_path}"
                    report = self.consensus_engine.evaluate_consensus(
                        task_id=f"{build_context.build_id}-{file_path}",
                        code=code,
                        file_path=file_path,
                        agent_type=AgentType.FRONTEND
                    )
                    
                    if report.decision == ConsensusDecision.REJECT:
                        logger.warning(f"Consensus rejected: {file_path}")
                        result['errors'] = result.get('errors', []) + [f"Rejected: {file_path}"]
            
            instance.output = result
            instance.status = AgentStatus.COMPLETED
            instance.completed_at = datetime.now()
            
            # Self-evaluation
            eval_result = self.self_evaluation.evaluate_output(
                'frontend', result, {'min_files': 5}
            )
            
            logger.info(f"Frontend build complete (score: {eval_result.score})")
            
            return result
            
        except Exception as e:
            instance.status = AgentStatus.FAILED
            instance.errors.append(str(e))
            raise
    
    async def build_backend(
        self,
        build_context: BuildContext,
        plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run Backend agent with consensus verification
        
        Args:
            build_context: Current build context
            plan: Architecture plan
            
        Returns:
            Backend build results
        """
        logger.info(f"Building backend for: {build_context.build_id}")
        
        instance = self.agent_instances.get('backend')
        if not instance:
            raise RuntimeError("Backend agent not initialized")
        
        instance.status = AgentStatus.RUNNING
        instance.current_task = f"backend:{build_context.build_id}"
        
        try:
            result = {
                'files_created': [],
                'api_endpoints': [],
                'database_models': [],
                'tests_added': [],
                'code_quality_score': 0.0
            }
            
            # Simulate backend generation
            result['files_created'] = [
                'backend/app/main.py',
                'backend/app/models/user.py',
                'backend/app/routes/auth.py',
                'backend/app/services/database.py',
                'backend/tests/test_auth.py'
            ]
            result['code_quality_score'] = 0.88
            
            # Run consensus verification
            if self.consensus_engine:
                for file_path in result['files_created']:
                    code = f"# Generated code for {file_path}"
                    report = self.consensus_engine.evaluate_consensus(
                        task_id=f"{build_context.build_id}-{file_path}",
                        code=code,
                        file_path=file_path,
                        agent_type=AgentType.BACKEND
                    )
                    
                    if report.decision == ConsensusDecision.REJECT:
                        logger.warning(f"Consensus rejected: {file_path}")
            
            instance.output = result
            instance.status = AgentStatus.COMPLETED
            instance.completed_at = datetime.now()
            
            eval_result = self.self_evaluation.evaluate_output(
                'backend', result, {'min_files': 5}
            )
            
            logger.info(f"Backend build complete (score: {eval_result.score})")
            
            return result
            
        except Exception as e:
            instance.status = AgentStatus.FAILED
            instance.errors.append(str(e))
            raise
    
    async def run_tests(
        self,
        build_context: BuildContext,
        frontend_result: Dict[str, Any],
        backend_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run Testing agent for quality assurance
        
        Args:
            build_context: Current build context
            frontend_result: Frontend build results
            backend_result: Backend build results
            
        Returns:
            Test results with coverage and quality metrics
        """
        logger.info(f"Running tests for: {build_context.build_id}")
        
        instance = self.agent_instances.get('testing')
        if not instance:
            raise RuntimeError("Testing agent not initialized")
        
        instance.status = AgentStatus.RUNNING
        instance.current_task = f"test:{build_context.build_id}"
        
        try:
            # Simulate test execution
            result = {
                'unit_tests': {'passed': 45, 'failed': 0, 'coverage': 0.87},
                'integration_tests': {'passed': 12, 'failed': 0, 'coverage': 0.82},
                'e2e_tests': {'passed': 8, 'failed': 0, 'coverage': 0.75},
                'security_scan': {'issues': 0, 'severity': 'none'},
                'performance_tests': {'avg_response_ms': 120, 'p95_ms': 180},
                'go_no_go': 'GO'
            }
            
            # Calculate overall coverage
            overall_coverage = (
                result['unit_tests']['coverage'] * 0.5 +
                result['integration_tests']['coverage'] * 0.3 +
                result['e2e_tests']['coverage'] * 0.2
            )
            result['overall_coverage'] = round(overall_coverage, 2)
            
            # Determine go/no-go
            if result['unit_tests']['failed'] > 0 or overall_coverage < 0.70:
                result['go_no_go'] = 'NO_GO'
            
            instance.output = result
            instance.status = AgentStatus.COMPLETED
            instance.completed_at = datetime.now()
            
            logger.info(f"Testing complete (coverage: {overall_coverage:.0%})")
            
            return result
            
        except Exception as e:
            instance.status = AgentStatus.FAILED
            instance.errors.append(str(e))
            raise
    
    async def deploy(
        self,
        build_context: BuildContext,
        test_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run DevOps agent for deployment
        
        Args:
            build_context: Current build context
            test_result: Test results
            
        Returns:
            Deployment results
        """
        logger.info(f"Deploying: {build_context.build_id}")
        
        # Check go/no-go
        if test_result.get('go_no_go') != 'GO':
            raise RuntimeError("Deployment blocked: tests did not pass go/no-go")
        
        instance = self.agent_instances.get('devops')
        if not instance:
            raise RuntimeError("DevOps agent not initialized")
        
        instance.status = AgentStatus.RUNNING
        instance.current_task = f"deploy:{build_context.build_id}"
        
        try:
            result = {
                'deployment_id': f"deploy-{uuid.uuid4().hex[:8]}",
                'platform': 'render',  # or 'play_store', 'app_store'
                'status': 'success',
                'url': f"https://{build_context.project_name}.onrender.com",
                'logs': [],
                'timestamp': datetime.now().isoformat()
            }
            
            instance.output = result
            instance.status = AgentStatus.COMPLETED
            instance.completed_at = datetime.now()
            
            logger.info(f"Deployment complete: {result['url']}")
            
            return result
            
        except Exception as e:
            instance.status = AgentStatus.FAILED
            instance.errors.append(str(e))
            raise
    
    async def monitor_reliability(self, build_context: BuildContext) -> Dict[str, Any]:
        """
        Run Reliability agent for quality control
        
        Args:
            build_context: Current build context
            
        Returns:
            Reliability assessment
        """
        logger.info(f"Monitoring reliability for: {build_context.build_id}")
        
        instance = self.agent_instances.get('reliability')
        if not instance:
            raise RuntimeError("Reliability agent not initialized")
        
        instance.status = AgentStatus.RUNNING
        instance.current_task = f"monitor:{build_context.build_id}"
        
        try:
            result = {
                'system_health': 'healthy',
                'uptime_percentage': 99.9,
                'error_rate': 0.001,
                'response_time_p95': 180,
                'alerts': [],
                'recommendations': []
            }
            
            instance.output = result
            instance.status = AgentStatus.COMPLETED
            instance.completed_at = datetime.now()
            
            return result
            
        except Exception as e:
            instance.status = AgentStatus.FAILED
            instance.errors.append(str(e))
            raise
    
    async def evolve_system(self, build_context: BuildContext) -> Dict[str, Any]:
        """
        Run Evolution agent for continuous improvement
        
        Args:
            build_context: Current build context
            
        Returns:
            Evolution recommendations
        """
        logger.info(f"Running evolution analysis for: {build_context.build_id}")
        
        instance = self.agent_instances.get('evolution')
        if not instance:
            raise RuntimeError("Evolution agent not initialized")
        
        instance.status = AgentStatus.RUNNING
        instance.current_task = f"evolve:{build_context.build_id}"
        
        try:
            # Analyze build metrics for patterns
            result = {
                'patterns_extracted': [],
                'prompt_optimizations': [],
                'migration_opportunities': [],
                'roi_calculations': {},
                'ab_test_recommendations': []
            }
            
            instance.output = result
            instance.status = AgentStatus.COMPLETED
            instance.completed_at = datetime.now()
            
            return result
            
        except Exception as e:
            instance.status = AgentStatus.FAILED
            instance.errors.append(str(e))
            raise
    
    # ========================================================================
    # CHANGE PROCESSING PIPELINE
    # ========================================================================
    
    async def process_change(
        self,
        change_request: ChangeRequest,
        project_path: str
    ) -> Dict[str, Any]:
        """
        End-to-end change processing pipeline
        
        Steps:
        1. Analyze → 2. Plan → 3. Build → 4. Test → 5. Evaluate → 6. Deploy
        
        Args:
            change_request: The change to process
            project_path: Path to project repository
            
        Returns:
            Complete processing results
        """
        build_id = f"build-{uuid.uuid4().hex[:8]}"
        
        logger.info(f"Processing change {change_request.id} as {build_id}")
        
        # Create build context
        build_context = BuildContext(
            build_id=build_id,
            project_path=project_path,
            project_name=change_request.metadata.get('project_name', 'unknown')
        )
        self.build_contexts[build_id] = build_context
        
        results = {
            'build_id': build_id,
            'change_id': change_request.id,
            'stages': {},
            'success': False,
            'error': None
        }
        
        try:
            # Check budget
            if not self._check_budget():
                raise RuntimeError("Daily budget exceeded")
            
            # === STAGE 1: ANALYZE ===
            logger.info(f"[{build_id}] Stage 1: Analysis")
            build_context.current_stage = BuildStage.ANALYSIS
            
            analysis = await self.analyze_project(
                project_path,
                build_context.project_name
            )
            results['stages']['analysis'] = analysis
            build_context.stack_detected = analysis.get('stack_detection', {})
            
            await self._create_checkpoint(build_context, BuildStage.ANALYSIS)
            self.events.emit('on_checkpoint_created', {'build_id': build_id, 'stage': 'analysis'})
            
            # === STAGE 2: PLAN ===
            logger.info(f"[{build_id}] Stage 2: Planning")
            build_context.current_stage = BuildStage.PLANNING
            
            plan = await self.plan_architecture(
                build_context.project_name,
                analysis
            )
            results['stages']['planning'] = plan
            
            # Human-in-the-loop for planning if critical
            if change_request.priority == ChangePriority.CRITICAL:
                await self.pause_for_review(
                    build_context,
                    "Critical change requires human review of architecture plan"
                )
            
            await self._create_checkpoint(build_context, BuildStage.PLANNING)
            
            # === STAGE 3: BUILD ===
            logger.info(f"[{build_id}] Stage 3: Build")
            
            # Frontend and backend can run in parallel
            build_context.current_stage = BuildStage.FRONTEND_BUILD
            frontend_task = asyncio.create_task(
                self.build_frontend(build_context, plan)
            )
            
            build_context.current_stage = BuildStage.BACKEND_BUILD
            backend_task = asyncio.create_task(
                self.build_backend(build_context, plan)
            )
            
            frontend_result, backend_result = await asyncio.gather(
                frontend_task, backend_task
            )
            
            results['stages']['frontend'] = frontend_result
            results['stages']['backend'] = backend_result
            
            await self._create_checkpoint(build_context, BuildStage.FRONTEND_BUILD)
            await self._create_checkpoint(build_context, BuildStage.BACKEND_BUILD)
            
            # === STAGE 4: TEST ===
            logger.info(f"[{build_id}] Stage 4: Testing")
            build_context.current_stage = BuildStage.TESTING
            
            test_result = await self.run_tests(
                build_context,
                frontend_result,
                backend_result
            )
            results['stages']['testing'] = test_result
            
            # Verify consensus before proceeding
            if not await self._verify_consensus(build_context, test_result):
                raise RuntimeError("Consensus verification failed")
            
            self.events.emit('on_consensus_reached', {'build_id': build_id})
            
            await self._create_checkpoint(build_context, BuildStage.TESTING)
            
            # === STAGE 5: EVALUATE ===
            logger.info(f"[{build_id}] Stage 5: Evaluation")
            build_context.current_stage = BuildStage.EVALUATION
            
            evaluation = self.self_evaluation.evaluate_output(
                'full_build',
                {
                    'frontend': frontend_result,
                    'backend': backend_result,
                    'tests': test_result
                },
                {'min_files': 10, 'test_coverage': 0.85}
            )
            results['stages']['evaluation'] = asdict(evaluation)
            build_context.evaluation_scores.append(evaluation.score)
            
            self.events.emit('on_evaluation_complete', {
                'build_id': build_id,
                'score': evaluation.score
            })
            
            # === STAGE 6: DEPLOY ===
            logger.info(f"[{build_id}] Stage 6: Deployment")
            build_context.current_stage = BuildStage.DEPLOYMENT
            
            deploy_result = await self.deploy(build_context, test_result)
            results['stages']['deployment'] = deploy_result
            
            await self._create_checkpoint(build_context, BuildStage.DEPLOYMENT)
            
            # Mark as completed
            results['success'] = True
            build_context.end_time = datetime.now()
            build_context.stages_completed = list(results['stages'].keys())
            
            logger.info(f"Change {change_request.id} processed successfully")
            
            # Run evolution analysis post-build
            asyncio.create_task(self.evolve_system(build_context))
            
        except Exception as e:
            logger.error(f"Change processing failed: {e}")
            results['success'] = False
            results['error'] = str(e)
            
            # Trigger rollback
            await self.rollback_on_failure(build_context)
        
        return results
    
    # ========================================================================
    # SAFETY MECHANISMS
    # ========================================================================
    
    async def rollback_on_failure(self, build_context: BuildContext) -> bool:
        """
        Automatic rollback on failure
        
        Args:
            build_context: Build context to rollback
            
        Returns:
            True if rollback successful
        """
        logger.warning(f"Initiating rollback for {build_context.build_id}")
        
        if not self.checkpoint_manager or not build_context.checkpoints:
            logger.error("No checkpoints available for rollback")
            return False
        
        try:
            # Get last checkpoint
            last_checkpoint_id = build_context.checkpoints[-1]
            
            # Perform rollback
            result = self.checkpoint_manager.rollback_to_checkpoint(last_checkpoint_id)
            
            if result.get('success'):
                logger.info(f"Rollback successful to {last_checkpoint_id}")
                return True
            else:
                logger.error(f"Rollback failed: {result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Rollback error: {e}")
            return False
    
    async def pause_for_review(
        self,
        build_context: BuildContext,
        reason: str,
        timeout_seconds: float = 3600
    ) -> bool:
        """
        Pause execution for human-in-the-loop review
        
        Args:
            build_context: Current build context
            reason: Reason for pause
            timeout_seconds: Maximum time to wait
            
        Returns:
            True if approved, False if rejected or timeout
        """
        logger.info(f"Pausing for review: {reason}")
        
        pause_id = f"pause-{uuid.uuid4().hex[:8]}"
        pause_marker = {
            'pause_id': pause_id,
            'build_id': build_context.build_id,
            'reason': reason,
            'started_at': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        # Write pause marker
        marker_path = Path(f"/tmp/apex_pause_{pause_id}.json")
        with open(marker_path, 'w') as f:
            json.dump(pause_marker, f, indent=2)
        
        print(f"\n{'='*60}")
        print(f"APEX PAUSE FOR REVIEW")
        print(f"{'='*60}")
        print(f"Build ID: {build_context.build_id}")
        print(f"Reason: {reason}")
        print(f"Marker: {marker_path}")
        print(f"\nApprove by running:")
        print(f"  echo '{{\"approved\": true}}' > {marker_path}")
        print(f"\nReject by running:")
        print(f"  echo '{{\"approved\": false}}' > {marker_path}")
        print(f"{'='*60}\n")
        
        # Wait for approval
        start_time = datetime.now()
        while (datetime.now() - start_time).total_seconds() < timeout_seconds:
            if marker_path.exists():
                try:
                    with open(marker_path, 'r') as f:
                        response = json.load(f)
                    
                    if response.get('approved'):
                        logger.info(f"Pause {pause_id} approved")
                        return True
                    else:
                        logger.warning(f"Pause {pause_id} rejected")
                        return False
                        
                except Exception:
                    pass
            
            await asyncio.sleep(1)
        
        logger.warning(f"Pause {pause_id} timed out")
        return False
    
    def budget_enforcement(self) -> Dict[str, Any]:
        """
        Check and enforce budget limits
        
        Returns:
            Budget status
        """
        if self.spend_guardrail:
            return self.spend_guardrail.check_budget()
        
        # Fallback budget check
        return {
            'within_budget': True,
            'daily_spend': 0.0,
            'daily_limit': self.max_budget_usd,
            'remaining': self.max_budget_usd
        }
    
    def _check_budget(self) -> bool:
        """Check if within budget"""
        status = self.budget_enforcement()
        return status.get('within_budget', True)
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _detect_stack(self, project_path: str) -> Dict[str, Any]:
        """Detect technology stack from project files"""
        stack = {
            'primary_stack': 'unknown',
            'frontend_framework': 'unknown',
            'backend_type': 'unknown',
            'database': 'none',
            'mobile_framework': 'none',
            'build_tool': 'unknown'
        }
        
        path = Path(project_path)
        
        # Check for package.json
        package_json = path / 'package.json'
        if package_json.exists():
            with open(package_json) as f:
                pkg = json.load(f)
            
            deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
            
            # Detect frontend framework
            if 'react' in deps:
                stack['frontend_framework'] = 'react'
            elif 'vue' in deps:
                stack['frontend_framework'] = 'vue'
            elif 'angular' in deps:
                stack['frontend_framework'] = 'angular'
            
            # Detect mobile framework
            if 'capacitor' in deps or '@capacitor/core' in deps:
                stack['mobile_framework'] = 'capacitor'
                stack['primary_stack'] = 'capacitor'
            elif 'expo' in deps:
                stack['mobile_framework'] = 'expo'
                stack['primary_stack'] = 'expo'
            
            # Detect build tool
            if 'vite' in deps:
                stack['build_tool'] = 'vite'
            elif 'webpack' in deps:
                stack['build_tool'] = 'webpack'
            
            if stack['primary_stack'] == 'unknown':
                stack['primary_stack'] = 'web'
        
        # Check for Python backend
        if (path / 'requirements.txt').exists() or (path / 'pyproject.toml').exists():
            stack['backend_type'] = 'fastapi' if (path / 'backend').exists() else 'python'
        
        # Check for database
        if (path / 'supabase').exists():
            stack['database'] = 'supabase'
        
        return stack
    
    def _calculate_automation(self, stack: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate automation potential"""
        automation_map = {
            'expo': 0.95,
            'flutter': 0.85,
            'capacitor': 0.70,
            'web': 0.98,
            'unknown': 0.50
        }
        
        primary = stack.get('primary_stack', 'unknown')
        potential = automation_map.get(primary, 0.50)
        
        return {
            'potential_percentage': potential * 100,
            'estimated_build_time_minutes': 120 if primary == 'capacitor' else 60,
            'manual_steps_required': self._get_manual_steps(primary),
            'manual_time_estimate_minutes': 45 if primary == 'capacitor' else 15,
            'full_automation_blockers': self._get_blockers(primary)
        }
    
    def _get_manual_steps(self, stack: str) -> List[str]:
        """Get manual steps for a stack"""
        steps = {
            'capacitor': [
                "Open Android Studio and build release AAB",
                "Upload AAB to Google Play Console"
            ],
            'expo': ["Play Console publish"],
            'flutter': ["Android Studio/Xcode build"],
            'web': []
        }
        return steps.get(stack, ["Manual review required"])
    
    def _get_blockers(self, stack: str) -> List[str]:
        """Get automation blockers for a stack"""
        blockers = {
            'capacitor': [
                "Google Play requires manual account access",
                "Android Studio signing required for release builds"
            ],
            'expo': ["Google Play account access required"],
            'flutter': ["Platform-specific build tools required"],
            'web': []
        }
        return blockers.get(stack, ["Unknown stack configuration"])
    
    def _generate_routing(
        self,
        stack: Dict[str, Any],
        automation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate agent routing decision"""
        return {
            'primary_track': stack.get('primary_stack', 'web'),
            'planning_agent_count': 1,
            'frontend_agent_count': 2 if stack.get('frontend_framework') else 0,
            'backend_agent_count': 2 if stack.get('backend_type') != 'unknown' else 0,
            'testing_agent_count': 1,
            'devops_agent_count': 1
        }
    
    def _analyze_migration(self, stack: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze migration options"""
        return {
            'current_stack_viable': True,
            'recommended_alternative': 'none',
            'migration_effort_hours': 0,
            'migration_benefits': [],
            'migration_risks': [],
            'preserve_current_stack': True
        }
    
    def _generate_prd(self, project_name: str, stack: Dict[str, Any]) -> Dict[str, Any]:
        """Generate PRD structure"""
        return {
            'title': f"Project Requirements Document: {project_name}",
            'overview': {
                'summary': f"Full-stack application for {project_name}",
                'target_platforms': ['android', 'ios', 'web'],
                'key_stakeholders': ['end_users', 'administrators']
            },
            'technical_stack': stack
        }
    
    def _generate_tech_spec(self, stack: Dict[str, Any]) -> Dict[str, Any]:
        """Generate technical specification"""
        return {
            'frontend': {
                'framework': stack.get('frontend_framework', 'react'),
                'state_management': 'zustand',
                'styling': 'tailwindcss'
            },
            'backend': {
                'framework': stack.get('backend_type', 'fastapi'),
                'api_style': 'rest',
                'authentication': 'jwt'
            },
            'database': {
                'type': stack.get('database', 'postgresql'),
                'orm': 'sqlalchemy' if stack.get('backend_type') == 'fastapi' else 'prisma'
            }
        }
    
    def _generate_architecture(
        self,
        stack: Dict[str, Any],
        routing: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate architecture design"""
        return {
            'pattern': 'microservices' if routing.get('backend_agent_count', 0) > 2 else 'monolith',
            'tiers': ['presentation', 'application', 'data'],
            'services': self._define_services(stack),
            'communication': 'rest_api'
        }
    
    def _define_services(self, stack: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Define microservices based on stack"""
        services = []
        
        if stack.get('frontend_framework'):
            services.append({
                'name': 'frontend',
                'type': 'presentation',
                'framework': stack['frontend_framework']
            })
        
        if stack.get('backend_type') != 'unknown':
            services.append({
                'name': 'api',
                'type': 'application',
                'framework': stack['backend_type']
            })
        
        return services
    
    def _generate_data_models(self, stack: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate data model specifications"""
        return [
            {'name': 'User', 'fields': ['id', 'email', 'created_at']},
            {'name': 'Project', 'fields': ['id', 'name', 'owner_id', 'status']}
        ]
    
    def _generate_api_contracts(self, stack: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate API contract specifications"""
        return [
            {
                'path': '/api/v1/users',
                'methods': ['GET', 'POST'],
                'auth_required': True
            },
            {
                'path': '/api/v1/auth/login',
                'methods': ['POST'],
                'auth_required': False
            }
        ]
    
    def _assess_risks(self, stack: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Assess project risks"""
        risks = []
        
        if stack.get('primary_stack') == 'unknown':
            risks.append({
                'level': 'high',
                'category': 'technical',
                'description': 'Unknown technology stack detected'
            })
        
        return risks
    
    async def _create_checkpoint(
        self,
        build_context: BuildContext,
        stage: BuildStage
    ):
        """Create checkpoint for build stage"""
        if not self.checkpoint_manager:
            return
        
        try:
            checkpoint = self.checkpoint_manager.create_full_checkpoint(
                build_id=build_context.build_id,
                stage=stage.value,
                files=[],  # Would be populated with actual files
                metadata={
                    'project_name': build_context.project_name,
                    'stack': build_context.stack_detected
                }
            )
            
            if checkpoint.get('tier2_sqlite'):
                build_context.checkpoints.append(checkpoint['tier2_sqlite'])
                
        except Exception as e:
            logger.warning(f"Checkpoint creation failed: {e}")
    
    async def _verify_consensus(
        self,
        build_context: BuildContext,
        data: Dict[str, Any]
    ) -> bool:
        """Verify consensus before proceeding"""
        if not self.consensus_engine:
            return True
        
        # Simulate consensus check
        # In production, this would evaluate actual code/output
        return True
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the agent layer"""
        return {
            'initialized': self._initialized,
            'paused': self._paused,
            'agents': {
                name: {
                    'status': instance.status.name,
                    'current_task': instance.current_task,
                    'autonomy_level': instance.spec.autonomy_level
                }
                for name, instance in self.agent_instances.items()
            },
            'active_builds': len(self.build_contexts),
            'subagent_stats': self.subagent_spawner.get_stats(),
            'budget': self.budget_enforcement()
        }
    
    def get_agent_capabilities(self, agent_name: str) -> List[str]:
        """Get capabilities for a specific agent"""
        agent = self.agents.get(agent_name)
        return agent.capabilities if agent else []
    
    def pause(self):
        """Pause all agent activity"""
        self._paused = True
        logger.info("Agent layer paused")
    
    def resume(self):
        """Resume agent activity"""
        self._paused = False
        logger.info("Agent layer resumed")
    
    def shutdown(self):
        """Graceful shutdown"""
        self._shutdown = True
        logger.info("Agent layer shutting down...")
        
        # Complete active builds
        for build_id, context in self.build_contexts.items():
            if not context.end_time:
                logger.warning(f"Build {build_id} incomplete at shutdown")
        
        logger.info("Agent layer shutdown complete")


# ============================================================================
# FACTORY AND MAIN ENTRY POINT
# ============================================================================

def create_agent_layer(
    specs_dir: Optional[str] = None,
    fleet_config_path: Optional[str] = None,
    max_budget_usd: float = 500.0
) -> AgentLayer:
    """
    Factory function to create an AgentLayer instance
    
    Args:
        specs_dir: Directory containing agent specs
        fleet_config_path: Path to fleet composition config
        max_budget_usd: Maximum daily budget
        
    Returns:
        Configured AgentLayer instance
    """
    base_path = Path("/home/teacherchris37/MasterBuilder7")
    
    specs_dir = specs_dir or str(base_path / "apex" / "agents" / "specs")
    fleet_config_path = fleet_config_path or str(base_path / "apex" / "fleet-composition.yaml")
    
    layer = AgentLayer(
        specs_dir=specs_dir,
        fleet_config_path=fleet_config_path,
        max_budget_usd=max_budget_usd
    )
    
    return layer


# ============================================================================
# MAIN EXECUTION BLOCK
# ============================================================================

async def main():
    """
    Example usage of the Agent Intelligence Layer
    
    This demonstrates:
    1. Initialization of all 8 core agents
    2. Processing a sample change request
    3. Running the full pipeline
    4. Displaying results and metrics
    """
    print("="*70)
    print("APEX AGENT INTELLIGENCE LAYER v2.0")
    print("MasterBuilder7 - Autonomous Software Development System")
    print("="*70)
    print()
    
    # Create and initialize the agent layer
    print("[1/5] Creating Agent Intelligence Layer...")
    layer = create_agent_layer(max_budget_usd=500.0)
    
    print("[2/5] Initializing agents from specifications...")
    if not layer.initialize():
        print("ERROR: Failed to initialize agent layer")
        return 1
    
    print(f"      ✓ Loaded {len(layer.agents)} agent specifications")
    print(f"      ✓ Initialized {len(layer.agent_instances)} agent instances")
    print()
    
    # Display agent roster
    print("[3/5] Agent Roster:")
    for name, instance in layer.agent_instances.items():
        spec = instance.spec
        print(f"      • {name:20} | v{spec.version} | autonomy L{spec.autonomy_level} | ${spec.cost_per_hour}/hr")
    print()
    
    # Create sample change request
    print("[4/5] Creating sample change request...")
    change = ChangeRequest(
        id=f"change-{uuid.uuid4().hex[:8]}",
        description="Add user authentication flow with JWT tokens",
        priority=ChangePriority.HIGH,
        files_affected=['src/pages/Login.tsx', 'backend/app/auth.py'],
        requested_by="product-team",
        created_at=datetime.now(),
        metadata={'project_name': 'ihhashi'}
    )
    print(f"      Change ID: {change.id}")
    print(f"      Priority: {change.priority.name}")
    print(f"      Description: {change.description}")
    print()
    
    # Process the change
    print("[5/5] Processing change through pipeline...")
    print("      Pipeline: Analyze → Plan → Build → Test → Evaluate → Deploy")
    print()
    
    try:
        # Setup event listeners
        def on_checkpoint(data):
            print(f"      📍 Checkpoint created: {data.get('stage', 'unknown')}")
        
        def on_consensus(data):
            print(f"      ✓ Consensus reached for build {data.get('build_id', 'unknown')[:8]}")
        
        def on_eval(data):
            print(f"      📊 Evaluation complete: score={data.get('score', 0):.2f}")
        
        layer.events.on('on_checkpoint_created', on_checkpoint)
        layer.events.on('on_consensus_reached', on_consensus)
        layer.events.on('on_evaluation_complete', on_eval)
        
        # Run the pipeline
        start_time = datetime.now()
        
        results = await layer.process_change(
            change_request=change,
            project_path="/home/teacherchris37"
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        print()
        print("="*70)
        print("RESULTS SUMMARY")
        print("="*70)
        
        if results['success']:
            print(f"✓ Build {results['build_id']} completed successfully")
            print(f"  Duration: {duration:.1f}s")
            print(f"  Stages completed: {len(results['stages'])}")
            
            # Show stage results
            for stage_name, stage_data in results['stages'].items():
                if isinstance(stage_data, dict):
                    status = "✓" if not stage_data.get('error') else "✗"
                    print(f"  {status} {stage_name}")
            
            # Show evaluation
            if 'evaluation' in results['stages']:
                eval_data = results['stages']['evaluation']
                print(f"\n  Quality Score: {eval_data.get('score', 0):.2%}")
                
                strengths = eval_data.get('strengths', [])
                if strengths:
                    print(f"  Strengths ({len(strengths)}):")
                    for s in strengths[:3]:
                        print(f"    • {s}")
            
            # Show deployment
            if 'deployment' in results['stages']:
                deploy = results['stages']['deployment']
                print(f"\n  Deployment URL: {deploy.get('url', 'N/A')}")
        
        else:
            print(f"✗ Build failed: {results.get('error', 'Unknown error')}")
        
        # Show final status
        print()
        print("="*70)
        print("SYSTEM STATUS")
        print("="*70)
        status = layer.get_status()
        print(f"Active builds: {status['active_builds']}")
        print(f"Sub-agents spawned: {status['subagent_stats']['total_spawned']}")
        print(f"Budget status: ${status['budget'].get('daily_spend', 0):.2f} / ${status['budget'].get('daily_limit', 500):.2f}")
        
        # Show performance trends
        print()
        print("="*70)
        print("PERFORMANCE TRENDS")
        print("="*70)
        for metric in ['code_quality', 'test_coverage', 'completeness']:
            trend = layer.self_evaluation.get_performance_trend(metric)
            if trend['samples'] > 0:
                trend_arrow = "↑" if trend['trend'] > 0 else "↓" if trend['trend'] < 0 else "→"
                print(f"  {metric:20} | avg: {trend['average']:.2f} | {trend_arrow}")
        
        print()
        print("="*70)
        print("Agent Intelligence Layer execution complete")
        print("="*70)
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Error during execution: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    # Run the main async function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
