#!/usr/bin/env python3
"""
APEX Dynamic Sub-Agent Spawner
Production-ready system for spawning specialized sub-agents on demand.

Features:
- Dynamic agent spawning for specific skills
- Lifecycle management (spawn, track, terminate)
- Parallel execution support
- Cost budgeting and resource limits
- Integration with main orchestrator via events/callbacks
- Comprehensive logging and error handling

Usage:
    spawner = SubAgentSpawner()
    agent = await spawner.spawn(SubAgentType.SECURITY_AUDIT, task_context)
    result = await agent.execute()
"""

import asyncio
import hashlib
import json
import logging
import os
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from contextlib import asynccontextmanager
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SubAgentType(Enum):
    """Enumeration of specialized sub-agent types."""
    
    # Security & Compliance
    SECURITY_AUDIT = "security_audit"
    PAYSTACK_SECURITY = "paystack_security"
    FASTAPI_SECURITY = "fastapi_security"
    CAPACITOR_SECURITY = "capacitor_security"
    
    # AI & Optimization
    AI_ROUTER = "ai_router"
    AI_OPTIMIZER = "ai_optimizer"
    CODE_GENERATOR = "code_generator"
    
    # Database & Performance
    DB_OPTIMIZER = "db_optimizer"
    QUERY_OPTIMIZER = "query_optimizer"
    DB_MIGRATION = "db_migration"
    PERFORMANCE_PROFILER = "performance_profiler"
    CACHE_OPTIMIZER = "cache_optimizer"
    
    # Business Logic
    REWARD_CALCULATOR = "reward_calculator"
    REFERRAL_PROCESSOR = "referral_processor"
    PAYOUT_CALCULATOR = "payout_calculator"
    
    # Build & Deployment
    CAPACITOR_BUILD_EXPERT = "capacitor_build_expert"
    PLAY_STORE_DEPLOYER = "play_store_deployer"
    APP_STORE_DEPLOYER = "app_store_deployer"
    DOCKER_EXPERT = "docker_expert"
    K8S_EXPERT = "k8s_expert"
    
    # Testing & QA
    TEST_GENERATOR = "test_generator"
    E2E_TESTER = "e2e_tester"
    SECURITY_SCANNER = "security_scanner"
    
    # Route & Navigation
    ROUTE_OPTIMIZER = "route_optimizer"
    ETA_CALCULATOR = "eta_calculator"
    
    # Documentation & Analysis
    CODE_ANALYZER = "code_analyzer"
    DOC_GENERATOR = "doc_generator"
    BUSINESS_LOGIC_EXTRACTOR = "business_logic_extractor"


class AgentStatus(Enum):
    """Lifecycle states for sub-agents."""
    PENDING = "pending"
    SPAWNING = "spawning"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATING = "terminating"
    TERMINATED = "terminated"


@dataclass
class SubAgentConfig:
    """Configuration for a sub-agent type.
    
    Attributes:
        agent_type: The type of sub-agent
        required_skills: List of required skills/capabilities
        base_prompt: Base system prompt for the agent
        max_tokens: Maximum tokens for agent responses
        timeout: Maximum execution time in seconds
        cost_budget: Maximum cost budget for this agent (USD)
        max_parallel_tasks: Maximum parallel tasks this agent can handle
        retry_count: Number of retries on failure
        metadata: Additional configuration metadata
    """
    agent_type: SubAgentType
    required_skills: List[str] = field(default_factory=list)
    base_prompt: str = ""
    max_tokens: int = 4000
    timeout: int = 300  # 5 minutes default
    cost_budget: float = 1.0  # $1 USD default
    max_parallel_tasks: int = 1
    retry_count: int = 2
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.base_prompt:
            self.base_prompt = self._generate_default_prompt()
    
    def _generate_default_prompt(self) -> str:
        """Generate a default system prompt based on agent type."""
        return f"""You are a specialized {self.agent_type.value} sub-agent.
Your task is to execute the assigned work with precision and efficiency.
Required skills: {', '.join(self.required_skills)}

Guidelines:
- Focus on your specific domain expertise
- Provide clear, actionable outputs
- Report errors immediately with full context
- Respect the cost budget and timeout constraints
"""


@dataclass
class SpawnedAgent:
    """Represents a spawned sub-agent instance.
    
    Attributes:
        id: Unique agent instance ID
        agent_type: Type of sub-agent
        config: Agent configuration
        status: Current lifecycle status
        created_at: Creation timestamp
        started_at: Execution start timestamp
        completed_at: Completion timestamp
        context: Task context/data
        result: Execution result
        error: Error information if failed
        cost_incurred: Actual cost incurred (USD)
        tokens_used: Total tokens consumed
        parent_task_id: ID of parent task if any
        callbacks: Registered event callbacks
    """
    id: str
    agent_type: SubAgentType
    config: SubAgentConfig
    status: AgentStatus = AgentStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    context: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    cost_incurred: float = 0.0
    tokens_used: int = 0
    parent_task_id: Optional[str] = None
    callbacks: Dict[str, List[Callable]] = field(default_factory=dict)
    _task: Optional[asyncio.Task] = field(default=None, repr=False)
    _semaphore: Optional[asyncio.Semaphore] = field(default=None, repr=False)
    
    def __post_init__(self):
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.config.max_parallel_tasks)
    
    async def execute(self, work_fn: Callable[..., Any], *args, **kwargs) -> Dict[str, Any]:
        """Execute work function with lifecycle management."""
        async with self._semaphore:
            self.status = AgentStatus.RUNNING
            self.started_at = datetime.now()
            
            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    work_fn(*args, **kwargs),
                    timeout=self.config.timeout
                )
                
                self.result = {
                    "status": "success",
                    "data": result,
                    "agent_id": self.id,
                    "agent_type": self.agent_type.value,
                    "execution_time": (datetime.now() - self.started_at).total_seconds()
                }
                self.status = AgentStatus.COMPLETED
                self._emit_event("completed", self.result)
                
            except asyncio.TimeoutError:
                self.error = f"Execution timed out after {self.config.timeout}s"
                self.status = AgentStatus.FAILED
                self.result = {"status": "failed", "error": self.error}
                self._emit_event("failed", {"error": self.error})
                
            except Exception as e:
                self.error = str(e)
                self.status = AgentStatus.FAILED
                self.result = {"status": "failed", "error": self.error, "traceback": traceback.format_exc()}
                self._emit_event("failed", {"error": self.error})
            
            finally:
                self.completed_at = datetime.now()
            
            return self.result
    
    def on_event(self, event_type: str, callback: Callable):
        """Register an event callback."""
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)
    
    def _emit_event(self, event_type: str, data: Dict):
        """Emit event to registered callbacks."""
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(self, data))
                    else:
                        callback(self, data)
                except Exception as e:
                    logger.error(f"Event callback error for {event_type}: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize agent state to dictionary."""
        return {
            "id": self.id,
            "agent_type": self.agent_type.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "cost_incurred": self.cost_incurred,
            "tokens_used": self.tokens_used,
            "parent_task_id": self.parent_task_id,
            "result": self.result,
            "error": self.error
        }


# =============================================================================
# SKILL REGISTRY - Pre-configured agent configurations for common tasks
# =============================================================================

SKILL_REGISTRY: Dict[str, SubAgentConfig] = {
    # Payment Security
    "paystack_security": SubAgentConfig(
        agent_type=SubAgentType.PAYSTACK_SECURITY,
        required_skills=["payment_security", "api_audit", "secret_scanning", "webhook_validation"],
        base_prompt="""You are a Paystack security audit specialist.
Your role is to thoroughly audit Paystack payment integrations for security vulnerabilities.

Key responsibilities:
1. Verify webhook signature validation is implemented correctly
2. Check that API keys are stored securely (environment variables, NOT in code)
3. Ensure payment callbacks validate transaction references
4. Verify amount tampering protection (check amounts match)
5. Check for proper error handling without leaking sensitive data
6. Verify HTTPS is enforced for all payment endpoints
7. Check rate limiting on payment endpoints
8. Audit for duplicate transaction prevention
9. Verify PCI compliance adherence (no card data logging)

Output format:
- Executive summary (PASS/FAIL with risk level)
- Detailed findings with line references
- Remediation code examples
- Testing recommendations""",
        max_tokens=8000,
        timeout=600,
        cost_budget=2.0,
        metadata={"domain": "payment", "priority": "critical"}
    ),
    
    # AI Route Optimization
    "ai_route_optimizer": SubAgentConfig(
        agent_type=SubAgentType.AI_ROUTER,
        required_skills=["routing", "optimization", "ml", "graph_theory"],
        base_prompt="""You are an AI route optimization specialist.
Your role is to optimize delivery routes and API routing decisions using AI/ML techniques.

Key responsibilities:
1. Analyze traffic patterns and historical delivery data
2. Optimize routes for minimum time/fuel consumption
3. Handle dynamic re-routing based on real-time conditions
4. Balance load across multiple delivery agents
5. Consider constraints (time windows, vehicle capacity, priority orders)
6. Apply machine learning for ETA prediction
7. Optimize API route handlers for performance

Algorithms you can apply:
- Dijkstra's / A* for shortest path
- Genetic algorithms for multi-stop optimization
- Reinforcement learning for dynamic routing
- Clustering for zone-based dispatch

Output format:
- Optimized route sequence
- Estimated metrics (time, distance, cost)
- Alternative routes with trade-offs
- Confidence score for recommendations""",
        max_tokens=6000,
        timeout=300,
        cost_budget=1.5,
        metadata={"domain": "routing", "ml_enabled": True}
    ),
    
    # Reward Calculation
    "reward_calculator": SubAgentConfig(
        agent_type=SubAgentType.REWARD_CALCULATOR,
        required_skills=["financial_calculation", "referral_tracking", "tier_logic"],
        base_prompt="""You are a reward calculation specialist for the iHhashi referral system.
Your role is to accurately calculate referral rewards, tier benefits, and payouts.

Key responsibilities:
1. Calculate iHhashi Coin earnings from referrals
2. Determine tier upgrades (Bronze → Silver → Gold → Platinum)
3. Calculate discount percentages based on tier
4. Track vendor referral bonus days (+2 days per referral)
5. Verify referral code validity and usage
6. Calculate weekly payout amounts for delivery servicemen
7. Handle edge cases (duplicate referrals, refunds, cancellations)

Rules:
- Customer referral: 50 coins (referrer), 25 coins (new customer)
- Vendor referral: +2 free days (max 90 extra days)
- Tiers: Bronze (1-5 refs, 5%), Silver (6-15, 10%), Gold (16-50, 15%), Platinum (51+, 20%)
- Coin value: 1 coin = R0.10 (10 cents)
- Payout day: Every Sunday at 11:11 AM SAST
- Minimum payout: R100

Output format:
- Detailed calculation breakdown
- Tier status and progress
- Coin balance and redemption value
- Next payout prediction""",
        max_tokens=4000,
        timeout=120,
        cost_budget=0.5,
        metadata={"domain": "finance", "currency": "ZAR"}
    ),
    
    # Database Query Optimizer
    "db_query_optimizer": SubAgentConfig(
        agent_type=SubAgentType.QUERY_OPTIMIZER,
        required_skills=["mongodb", "query_optimization", "indexing", "aggregation"],
        base_prompt="""You are a MongoDB query optimization specialist.
Your role is to analyze and optimize slow database queries for maximum performance.

Key responsibilities:
1. Analyze query execution plans (explain())
2. Identify missing or suboptimal indexes
3. Optimize aggregation pipelines
4. Reduce query complexity and document scans
5. Suggest schema improvements
6. Optimize for read-heavy vs write-heavy workloads
7. Handle large dataset pagination efficiently

Optimization techniques:
- Index creation (single, compound, text, geospatial)
- Query projection to limit returned fields
- Aggregation pipeline stage ordering
- Using covered queries
- Sharding strategies for scale
- Caching frequently accessed data

Output format:
- Original query analysis (execution stats)
- Optimized query with explanation
- Index recommendations with create commands
- Expected performance improvement
- Migration strategy for existing data""",
        max_tokens=6000,
        timeout=180,
        cost_budget=1.0,
        metadata={"database": "mongodb", "focus": "performance"}
    ),
    
    # Capacitor Build Expert
    "capacitor_build_expert": SubAgentConfig(
        agent_type=SubAgentType.CAPACITOR_BUILD_EXPERT,
        required_skills=["capacitor", "android", "ios", "gradle", "xcode", "cordova"],
        base_prompt="""You are a Capacitor build specialist for hybrid mobile apps.
Your role is to troubleshoot and optimize Capacitor builds for Android and iOS.

Key responsibilities:
1. Diagnose and fix Android Gradle build failures
2. Resolve iOS Xcode build issues
3. Optimize build configurations for faster builds
4. Handle native plugin integration issues
5. Manage signing and provisioning profiles
6. Optimize app bundle size
7. Ensure compatibility with latest OS versions

Common issues you solve:
- Gradle sync failures
- Missing native dependencies
- Plugin version conflicts
- Signing configuration errors
- ProGuard/R8 minification issues
- CocoaPods installation failures
- WebView rendering issues

Output format:
- Root cause analysis
- Step-by-step fix instructions
- Configuration changes with code
- Prevention recommendations
- Build optimization suggestions""",
        max_tokens=6000,
        timeout=300,
        cost_budget=1.0,
        metadata={"platform": "mobile", "framework": "capacitor"}
    ),
    
    # FastAPI Security
    "fastapi_security": SubAgentConfig(
        agent_type=SubAgentType.FASTAPI_SECURITY,
        required_skills=["fastapi", "security", "oauth2", "jwt", "input_validation"],
        base_prompt="""You are a FastAPI security specialist.
Your role is to audit and secure FastAPI applications against common vulnerabilities.

Key responsibilities:
1. Audit for OWASP Top 10 vulnerabilities
2. Verify authentication and authorization implementations
3. Check input validation and sanitization
4. Review CORS configuration
5. Verify rate limiting implementation
6. Check for SQL/NoSQL injection vulnerabilities
7. Audit dependency injection for security issues
8. Verify secure headers (HSTS, CSP, etc.)

Security checks:
- SQL/NoSQL injection in path/query/body params
- XSS in response templates
- CSRF protection
- JWT token security (expiration, algorithm, secret)
- OAuth2 flow implementation
- File upload security
- Dependency vulnerability scanning

Output format:
- Security score (0-100)
- Critical/High/Medium/Low findings
- Vulnerable code snippets
- Secure code replacements
- Testing recommendations""",
        max_tokens=8000,
        timeout=300,
        cost_budget=1.5,
        metadata={"framework": "fastapi", "domain": "security"}
    ),
    
    # Security Scanner
    "security_scanner": SubAgentConfig(
        agent_type=SubAgentType.SECURITY_SCANNER,
        required_skills=["vulnerability_scanning", "secrets_detection", "dependency_audit"],
        base_prompt="""You are a comprehensive security scanner specialist.
Your role is to perform deep security scans across the entire codebase.

Key responsibilities:
1. Scan for hardcoded secrets (API keys, passwords, tokens)
2. Detect vulnerable dependencies
3. Identify insecure configurations
4. Check for misconfigured CORS/CSP headers
5. Scan for exposed sensitive endpoints
6. Detect insecure logging that may leak data
7. Identify SSRF and injection vulnerabilities
8. Check for insecure deserialization

Tools and techniques:
- Pattern-based secret detection
- Dependency vulnerability database lookup
- Static Application Security Testing (SAST)
- Configuration file analysis
- Docker image scanning concepts

Output format:
- Executive summary with risk rating
- Detailed findings with severity
- Affected files and line numbers
- Remediation steps
- Compliance mapping (OWASP, CVE)""",
        max_tokens=8000,
        timeout=600,
        cost_budget=2.0,
        metadata={"scan_type": "full", "continuous": True}
    ),
    
    # Performance Profiler
    "performance_profiler": SubAgentConfig(
        agent_type=SubAgentType.PERFORMANCE_PROFILER,
        required_skills=["profiling", "optimization", "memory_analysis", "cpu_profiling"],
        base_prompt="""You are a performance profiling specialist.
Your role is to identify and resolve performance bottlenecks in applications.

Key responsibilities:
1. Analyze CPU usage patterns
2. Identify memory leaks and high allocation areas
3. Profile database query performance
4. Analyze API response times
5. Optimize frontend rendering performance
6. Review async/await usage for blocking operations
7. Suggest caching strategies

Profiling areas:
- Hot code paths
- N+1 query problems
- Unnecessary re-renders
- Memory allocations
- I/O bottlenecks
- Network request optimization

Output format:
- Performance metrics summary
- Bottleneck identification with flame graphs (text)
- Optimization recommendations ranked by impact
- Before/after performance predictions
- Implementation priority list""",
        max_tokens=6000,
        timeout=300,
        cost_budget=1.0,
        metadata={"focus": "performance", "tools": ["cProfile", "py-spy", "memory_profiler"]}
    ),
    
    # Code Generator
    "code_generator": SubAgentConfig(
        agent_type=SubAgentType.CODE_GENERATOR,
        required_skills=["code_generation", "templates", "multiple_languages"],
        base_prompt="""You are an intelligent code generation specialist.
Your role is to generate production-ready code from specifications.

Key responsibilities:
1. Generate code from natural language descriptions
2. Create boilerplate and scaffolding
3. Implement design patterns correctly
4. Generate API endpoints with proper validation
5. Create database models and migrations
6. Generate test cases for code
7. Follow language-specific best practices

Supported outputs:
- Python (FastAPI, Django, scripts)
- TypeScript/JavaScript (React, Node.js)
- SQL/NoSQL queries
- Shell scripts
- Configuration files
- Test files (pytest, jest)

Guidelines:
- Generate typed code where applicable
- Include proper error handling
- Add docstrings and comments
- Follow PEP 8 / ESLint standards
- Include input validation

Output format:
- Generated code files
- Explanation of key sections
- Usage examples
- Integration instructions""",
        max_tokens=8000,
        timeout=300,
        cost_budget=1.0,
        metadata={"languages": ["python", "typescript", "javascript", "sql"], "quality": "production"}
    ),
    
    # Documentation Generator
    "doc_generator": SubAgentConfig(
        agent_type=SubAgentType.DOC_GENERATOR,
        required_skills=["documentation", "technical_writing", "api_docs"],
        base_prompt="""You are a technical documentation specialist.
Your role is to generate comprehensive, clear documentation from code.

Key responsibilities:
1. Generate API documentation from code
2. Create README files with setup instructions
3. Document architecture and design decisions
4. Generate changelogs from commits
5. Create user guides and tutorials
6. Document deployment procedures
7. Maintain AGENTS.md files

Documentation types:
- API reference (OpenAPI/Swagger style)
- Architecture Decision Records (ADRs)
- Setup and installation guides
- Troubleshooting guides
- Code comments and docstrings
- README.md files

Output format:
- Markdown files
- Structured documentation
- Code examples
- Diagram descriptions (Mermaid)
- Cross-references between docs""",
        max_tokens=6000,
        timeout=180,
        cost_budget=0.75,
        metadata={"format": "markdown", "style": "technical"}
    ),
}


# =============================================================================
# MAIN SPAWNER CLASS
# =============================================================================

class SubAgentSpawner:
    """
    Dynamic sub-agent spawner for specialized task execution.
    
    Features:
    - Spawn specialized agents on-demand
    - Manage agent lifecycle (spawn, track, terminate)
    - Parallel execution support
    - Cost tracking and budgeting
    - Event-driven architecture for orchestrator integration
    - Persistent state in SQLite
    
    Example:
        spawner = SubAgentSpawner()
        
        # Spawn a single agent
        agent = await spawner.spawn_for_skill("paystack_security", {
            "repository": "/path/to/repo",
            "focus_areas": ["webhooks", "api_keys"]
        })
        
        # Execute work
        result = await agent.execute(my_audit_function)
        
        # Spawn multiple agents in parallel
        agents = await spawner.spawn_parallel([
            ("security_scanner", {"scope": "full"}),
            ("performance_profiler", {"target": "api"}),
            ("db_query_optimizer", {"slow_queries": [...]})
        ])
    """
    
    def __init__(
        self,
        db_path: str = "/home/teacherchris37/MasterBuilder7/apex/agents/subagent_registry.db",
        max_concurrent_agents: int = 64,
        global_cost_budget: float = 100.0,
        event_callbacks: Optional[Dict[str, List[Callable]]] = None
    ):
        """
        Initialize the sub-agent spawner.
        
        Args:
            db_path: Path to SQLite database for persistence
            max_concurrent_agents: Maximum agents allowed to run concurrently
            global_cost_budget: Total cost budget across all agents (USD)
            event_callbacks: Global event callbacks for orchestrator integration
        """
        self.db_path = db_path
        self.max_concurrent_agents = max_concurrent_agents
        self.global_cost_budget = global_cost_budget
        self.global_cost_incurred = 0.0
        
        # Agent tracking
        self.active_agents: Dict[str, SpawnedAgent] = {}
        self.agent_history: List[SpawnedAgent] = []
        self._agent_semaphore = asyncio.Semaphore(max_concurrent_agents)
        
        # Event system
        self.event_callbacks: Dict[str, List[Callable]] = event_callbacks or {}
        self._global_handlers: Dict[str, List[Callable]] = {
            "agent_spawned": [],
            "agent_completed": [],
            "agent_failed": [],
            "agent_terminated": [],
            "budget_warning": [],
        }
        
        # Initialize
        self._init_database()
        self._load_skill_registry()
        
        logger.info(f"SubAgentSpawner initialized (max_agents={max_concurrent_agents}, budget=${global_cost_budget})")
    
    def _init_database(self):
        """Initialize SQLite database for agent persistence."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main agents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS spawned_agents (
                id TEXT PRIMARY KEY,
                agent_type TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                context TEXT,
                result TEXT,
                error TEXT,
                cost_incurred REAL DEFAULT 0.0,
                tokens_used INTEGER DEFAULT 0,
                parent_task_id TEXT,
                config TEXT
            )
        ''')
        
        # Agent metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                metric_value REAL,
                recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES spawned_agents(id)
            )
        ''')
        
        # Skill usage stats
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS skill_usage (
                skill_name TEXT PRIMARY KEY,
                spawn_count INTEGER DEFAULT 0,
                total_cost REAL DEFAULT 0.0,
                avg_execution_time REAL DEFAULT 0.0,
                success_rate REAL DEFAULT 0.0,
                last_used TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.debug("Database initialized")
    
    def _load_skill_registry(self):
        """Load the skill registry with pre-configured agents."""
        self.skill_registry = SKILL_REGISTRY.copy()
        logger.debug(f"Loaded {len(self.skill_registry)} skills into registry")
    
    def register_skill(self, skill_name: str, config: SubAgentConfig):
        """Register a new skill dynamically."""
        self.skill_registry[skill_name] = config
        logger.info(f"Registered new skill: {skill_name}")
    
    # =========================================================================
    # SPAWNING METHODS
    # =========================================================================
    
    async def spawn(
        self,
        agent_type: SubAgentType,
        context: Dict[str, Any],
        config_overrides: Optional[Dict[str, Any]] = None,
        parent_task_id: Optional[str] = None
    ) -> SpawnedAgent:
        """
        Spawn a new sub-agent of the specified type.
        
        Args:
            agent_type: Type of agent to spawn
            context: Task context and input data
            config_overrides: Optional configuration overrides
            parent_task_id: ID of parent task if this is a child agent
            
        Returns:
            SpawnedAgent instance ready for execution
            
        Raises:
            BudgetExceededError: If global cost budget would be exceeded
            MaxAgentsError: If max concurrent agents reached
        """
        # Check budget
        if self.global_cost_incurred >= self.global_cost_budget:
            raise BudgetExceededError(
                f"Global cost budget exceeded: ${self.global_cost_incurred:.2f} / ${self.global_cost_budget:.2f}"
            )
        
        # Generate unique ID
        agent_id = self._generate_agent_id(agent_type, context)
        
        # Build config
        base_config = SubAgentConfig(agent_type=agent_type)
        if config_overrides:
            for key, value in config_overrides.items():
                if hasattr(base_config, key):
                    setattr(base_config, key, value)
        
        # Create agent instance
        agent = SpawnedAgent(
            id=agent_id,
            agent_type=agent_type,
            config=base_config,
            context=context,
            parent_task_id=parent_task_id,
            status=AgentStatus.SPAWNING
        )
        
        # Wire up event forwarding
        agent.on_event("completed", self._on_agent_completed)
        agent.on_event("failed", self._on_agent_failed)
        
        # Track agent
        async with self._agent_semaphore:
            self.active_agents[agent_id] = agent
        
        # Persist to database
        self._persist_agent(agent)
        
        # Emit global event
        self._emit_global_event("agent_spawned", {
            "agent_id": agent_id,
            "agent_type": agent_type.value,
            "parent_task_id": parent_task_id,
            "context_keys": list(context.keys())
        })
        
        agent.status = AgentStatus.READY
        logger.info(f"Spawned agent {agent_id} of type {agent_type.value}")
        
        return agent
    
    async def spawn_for_skill(
        self,
        skill_name: str,
        context: Dict[str, Any],
        parent_task_id: Optional[str] = None
    ) -> SpawnedAgent:
        """
        Spawn an agent using a pre-configured skill from the registry.
        
        Args:
            skill_name: Name of skill in registry (e.g., "paystack_security")
            context: Task context and input data
            parent_task_id: ID of parent task
            
        Returns:
            SpawnedAgent configured for the skill
            
        Raises:
            SkillNotFoundError: If skill not in registry
        """
        if skill_name not in self.skill_registry:
            raise SkillNotFoundError(f"Skill '{skill_name}' not found in registry. "
                                    f"Available: {list(self.skill_registry.keys())}")
        
        config = self.skill_registry[skill_name]
        
        # Add skill metadata to context
        context['_skill_name'] = skill_name
        context['_skill_metadata'] = config.metadata
        
        agent = await self.spawn(
            agent_type=config.agent_type,
            context=context,
            config_overrides={
                'required_skills': config.required_skills,
                'base_prompt': config.base_prompt,
                'max_tokens': config.max_tokens,
                'timeout': config.timeout,
                'cost_budget': config.cost_budget,
                'max_parallel_tasks': config.max_parallel_tasks,
                'retry_count': config.retry_count,
            },
            parent_task_id=parent_task_id
        )
        
        # Update skill usage stats
        self._update_skill_stats(skill_name, agent)
        
        return agent
    
    async def spawn_parallel(
        self,
        skill_tasks: List[Tuple[str, Dict[str, Any]]],
        parent_task_id: Optional[str] = None,
        max_parallel: Optional[int] = None
    ) -> List[SpawnedAgent]:
        """
        Spawn multiple agents in parallel for concurrent execution.
        
        Args:
            skill_tasks: List of (skill_name, context) tuples
            parent_task_id: ID of parent task
            max_parallel: Maximum concurrent spawns (default: unlimited)
            
        Returns:
            List of SpawnedAgent instances
        """
        semaphore = asyncio.Semaphore(max_parallel) if max_parallel else None
        
        async def spawn_with_limit(skill_name: str, context: Dict):
            if semaphore:
                async with semaphore:
                    return await self.spawn_for_skill(skill_name, context, parent_task_id)
            else:
                return await self.spawn_for_skill(skill_name, context, parent_task_id)
        
        tasks = [
            spawn_with_limit(skill_name, context)
            for skill_name, context in skill_tasks
        ]
        
        agents = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        successful_agents = []
        for i, agent in enumerate(agents):
            if isinstance(agent, Exception):
                logger.error(f"Failed to spawn agent for {skill_tasks[i][0]}: {agent}")
            else:
                successful_agents.append(agent)
        
        logger.info(f"Spawned {len(successful_agents)}/{len(skill_tasks)} agents in parallel")
        return successful_agents
    
    def get_specialized_agent(
        self,
        specialization: str,
        context: Dict[str, Any]
    ) -> Optional[SpawnedAgent]:
        """
        Get a pre-configured agent for common tasks (synchronous helper).
        Creates and returns immediately without async.
        
        Args:
            specialization: Common task name (e.g., "quick_security_scan")
            context: Task context
            
        Returns:
            SpawnedAgent or None if specialization unknown
        """
        specializations = {
            "quick_security_scan": ("security_scanner", {"depth": "quick"}),
            "deep_security_audit": ("paystack_security", {"depth": "full"}),
            "performance_check": ("performance_profiler", {"duration": "short"}),
            "db_health_check": ("db_query_optimizer", {"mode": "health_check"}),
            "build_fix": ("capacitor_build_expert", {"action": "diagnose"}),
            "route_optimization": ("ai_route_optimizer", {"priority": "balanced"}),
            "reward_calculation": ("reward_calculator", {"period": "current"}),
        }
        
        if specialization not in specializations:
            return None
        
        skill_name, default_context = specializations[specialization]
        merged_context = {**default_context, **context}
        
        # Create synchronous placeholder - actual spawn must use async spawn_for_skill
        config = self.skill_registry.get(skill_name)
        if not config:
            return None
        
        agent_id = self._generate_agent_id(config.agent_type, merged_context)
        return SpawnedAgent(
            id=agent_id,
            agent_type=config.agent_type,
            config=config,
            context=merged_context,
            status=AgentStatus.PENDING
        )
    
    # =========================================================================
    # LIFECYCLE MANAGEMENT
    # =========================================================================
    
    def track_agent(self, agent_id: str) -> Optional[SpawnedAgent]:
        """
        Get and monitor a spawned agent by ID.
        
        Args:
            agent_id: Agent instance ID
            
        Returns:
            SpawnedAgent if found, None otherwise
        """
        agent = self.active_agents.get(agent_id)
        if agent:
            logger.debug(f"Tracking agent {agent_id}: status={agent.status.value}")
        return agent
    
    async def terminate_agent(
        self,
        agent_id: str,
        force: bool = False,
        reason: str = "requested"
    ) -> bool:
        """
        Terminate a running agent gracefully or forcefully.
        
        Args:
            agent_id: Agent instance ID
            force: If True, cancel immediately without cleanup
            reason: Reason for termination
            
        Returns:
            True if termination successful, False otherwise
        """
        agent = self.active_agents.get(agent_id)
        if not agent:
            logger.warning(f"Cannot terminate: agent {agent_id} not found")
            return False
        
        agent.status = AgentStatus.TERMINATING
        logger.info(f"Terminating agent {agent_id} (force={force}, reason={reason})")
        
        try:
            if agent._task and not agent._task.done():
                if force:
                    agent._task.cancel()
                else:
                    # Give it a grace period to finish
                    try:
                        await asyncio.wait_for(agent._task, timeout=5.0)
                    except asyncio.TimeoutError:
                        agent._task.cancel()
            
            agent.status = AgentStatus.TERMINATED
            
            # Move to history
            self.agent_history.append(agent)
            del self.active_agents[agent_id]
            
            # Update database
            self._persist_agent(agent)
            
            # Emit event
            self._emit_global_event("agent_terminated", {
                "agent_id": agent_id,
                "reason": reason,
                "force": force,
                "final_status": agent.status.value
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error terminating agent {agent_id}: {e}")
            return False
    
    async def terminate_all(
        self,
        agent_type: Optional[SubAgentType] = None,
        force: bool = False
    ) -> int:
        """
        Terminate all active agents, optionally filtered by type.
        
        Args:
            agent_type: Optional filter by agent type
            force: Force termination flag
            
        Returns:
            Number of agents terminated
        """
        agents_to_terminate = []
        
        for agent_id, agent in list(self.active_agents.items()):
            if agent_type is None or agent.agent_type == agent_type:
                agents_to_terminate.append(agent_id)
        
        results = await asyncio.gather(*[
            self.terminate_agent(agent_id, force, "bulk_terminate")
            for agent_id in agents_to_terminate
        ])
        
        terminated_count = sum(1 for r in results if r)
        logger.info(f"Terminated {terminated_count}/{len(agents_to_terminate)} agents")
        return terminated_count
    
    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed status of a specific agent.
        
        Args:
            agent_id: Agent instance ID
            
        Returns:
            Status dictionary or None if not found
        """
        agent = self.active_agents.get(agent_id)
        if not agent:
            # Check history
            for hist_agent in self.agent_history:
                if hist_agent.id == agent_id:
                    return hist_agent.to_dict()
            return None
        
        status = agent.to_dict()
        status.update({
            "runtime_seconds": (datetime.now() - agent.started_at).total_seconds() 
                              if agent.started_at else None,
            "is_active": True,
            "has_result": agent.result is not None
        })
        return status
    
    # =========================================================================
    # STATUS & MONITORING
    # =========================================================================
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        active_by_type: Dict[str, int] = {}
        for agent in self.active_agents.values():
            type_name = agent.agent_type.value
            active_by_type[type_name] = active_by_type.get(type_name, 0) + 1
        
        return {
            "active_agents": len(self.active_agents),
            "historical_agents": len(self.agent_history),
            "max_concurrent": self.max_concurrent_agents,
            "global_cost": {
                "incurred": round(self.global_cost_incurred, 2),
                "budget": self.global_cost_budget,
                "remaining": round(self.global_cost_budget - self.global_cost_incurred, 2),
                "percentage": round((self.global_cost_incurred / self.global_cost_budget) * 100, 1)
            },
            "active_by_type": active_by_type,
            "available_slots": self.max_concurrent_agents - len(self.active_agents),
            "registered_skills": len(self.skill_registry)
        }
    
    def get_active_agents(
        self,
        agent_type: Optional[SubAgentType] = None,
        status: Optional[AgentStatus] = None
    ) -> List[SpawnedAgent]:
        """
        Get list of active agents with optional filtering.
        
        Args:
            agent_type: Filter by agent type
            status: Filter by status
            
        Returns:
            List of matching SpawnedAgent instances
        """
        results = []
        for agent in self.active_agents.values():
            if agent_type and agent.agent_type != agent_type:
                continue
            if status and agent.status != status:
                continue
            results.append(agent)
        return results
    
    # =========================================================================
    # EVENT & CALLBACK SYSTEM (Orchestrator Integration)
    # =========================================================================
    
    def on_event(self, event_type: str, callback: Callable):
        """
        Register a global event callback for orchestrator integration.
        
        Available events:
        - agent_spawned: When a new agent is spawned
        - agent_completed: When an agent completes successfully
        - agent_failed: When an agent fails
        - agent_terminated: When an agent is terminated
        - budget_warning: When approaching cost budget
        
        Args:
            event_type: Event name
            callback: Function to call (sync or async)
        """
        if event_type not in self._global_handlers:
            self._global_handlers[event_type] = []
        self._global_handlers[event_type].append(callback)
        logger.debug(f"Registered handler for event: {event_type}")
    
    def _emit_global_event(self, event_type: str, data: Dict[str, Any]):
        """Emit event to all registered handlers."""
        handlers = self._global_handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(data))
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Global event handler error: {e}")
    
    async def _on_agent_completed(self, agent: SpawnedAgent, data: Dict):
        """Handle agent completion."""
        self.global_cost_incurred += agent.cost_incurred
        self.agent_history.append(agent)
        
        if agent.id in self.active_agents:
            del self.active_agents[agent.id]
        
        self._persist_agent(agent)
        
        self._emit_global_event("agent_completed", {
            "agent_id": agent.id,
            "agent_type": agent.agent_type.value,
            "execution_time": data.get("execution_time"),
            "cost": agent.cost_incurred
        })
        
        # Budget warning check
        budget_pct = self.global_cost_incurred / self.global_cost_budget
        if budget_pct >= 0.8:
            self._emit_global_event("budget_warning", {
                "percentage": budget_pct * 100,
                "incurred": self.global_cost_incurred,
                "budget": self.global_cost_budget
            })
    
    async def _on_agent_failed(self, agent: SpawnedAgent, data: Dict):
        """Handle agent failure."""
        self.agent_history.append(agent)
        
        if agent.id in self.active_agents:
            del self.active_agents[agent.id]
        
        self._persist_agent(agent)
        
        self._emit_global_event("agent_failed", {
            "agent_id": agent.id,
            "agent_type": agent.agent_type.value,
            "error": data.get("error"),
            "retry_eligible": agent.config.retry_count > 0
        })
    
    # =========================================================================
    # DATABASE OPERATIONS
    # =========================================================================
    
    def _persist_agent(self, agent: SpawnedAgent):
        """Save agent state to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO spawned_agents 
                (id, agent_type, status, created_at, started_at, completed_at,
                 context, result, error, cost_incurred, tokens_used, parent_task_id, config)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                agent.id,
                agent.agent_type.value,
                agent.status.value,
                agent.created_at.isoformat(),
                agent.started_at.isoformat() if agent.started_at else None,
                agent.completed_at.isoformat() if agent.completed_at else None,
                json.dumps(agent.context),
                json.dumps(agent.result) if agent.result else None,
                agent.error,
                agent.cost_incurred,
                agent.tokens_used,
                agent.parent_task_id,
                json.dumps({
                    'required_skills': agent.config.required_skills,
                    'max_tokens': agent.config.max_tokens,
                    'timeout': agent.config.timeout,
                    'cost_budget': agent.config.cost_budget
                })
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to persist agent {agent.id}: {e}")
    
    def _update_skill_stats(self, skill_name: str, agent: SpawnedAgent):
        """Update skill usage statistics."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO skill_usage (skill_name, spawn_count, last_used)
                VALUES (?, 1, ?)
                ON CONFLICT(skill_name) DO UPDATE SET
                    spawn_count = spawn_count + 1,
                    last_used = excluded.last_used
            ''', (skill_name, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to update skill stats for {skill_name}: {e}")
    
    def get_skill_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get usage statistics for all skills."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM skill_usage')
            rows = cursor.fetchall()
            
            stats = {}
            for row in rows:
                stats[row[0]] = {
                    "spawn_count": row[1],
                    "total_cost": row[2],
                    "avg_execution_time": row[3],
                    "success_rate": row[4],
                    "last_used": row[5]
                }
            
            conn.close()
            return stats
        except Exception as e:
            logger.error(f"Failed to get skill stats: {e}")
            return {}
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def _generate_agent_id(
        self,
        agent_type: SubAgentType,
        context: Dict[str, Any]
    ) -> str:
        """Generate a unique agent ID."""
        timestamp = datetime.now().isoformat()
        unique_str = f"{agent_type.value}:{json.dumps(context, sort_keys=True)}:{timestamp}:{uuid.uuid4().hex[:8]}"
        hash_digest = hashlib.sha256(unique_str.encode()).hexdigest()[:16]
        return f"{agent_type.value[:3].upper()}-{hash_digest}"
    
    @asynccontextmanager
    async def managed_spawn(
        self,
        skill_name: str,
        context: Dict[str, Any],
        auto_terminate: bool = True
    ):
        """
        Context manager for automatic agent lifecycle management.
        
        Usage:
            async with spawner.managed_spawn("security_scanner", {"repo": "/path"}) as agent:
                result = await agent.execute(work_fn)
            # Agent automatically terminated on exit
        """
        agent = None
        try:
            agent = await self.spawn_for_skill(skill_name, context)
            yield agent
        finally:
            if agent and auto_terminate:
                await self.terminate_agent(agent.id, reason="context_exit")


# =============================================================================
# EXCEPTIONS
# =============================================================================

class BudgetExceededError(Exception):
    """Raised when cost budget is exceeded."""
    pass


class MaxAgentsError(Exception):
    """Raised when maximum concurrent agents reached."""
    pass


class SkillNotFoundError(Exception):
    """Raised when requested skill not in registry."""
    pass


# =============================================================================
# EXAMPLE USAGE & TESTING
# =============================================================================

async def example_usage():
    """Example demonstrating sub-agent spawner capabilities."""
    
    print("=" * 70)
    print("APEX Dynamic Sub-Agent Spawner - Example Usage")
    print("=" * 70)
    
    # Initialize spawner
    spawner = SubAgentSpawner(
        max_concurrent_agents=10,
        global_cost_budget=50.0
    )
    
    # Register orchestrator callbacks
    def on_agent_spawned(data):
        print(f"📢 Orchestrator notified: Agent {data['agent_id']} spawned")
    
    def on_agent_completed(data):
        print(f"✅ Orchestrator notified: Agent {data['agent_id']} completed in {data['execution_time']:.2f}s")
    
    spawner.on_event("agent_spawned", on_agent_spawned)
    spawner.on_event("agent_completed", on_agent_completed)
    
    print("\n--- Example 1: Spawn Single Agent ---")
    
    # Spawn a security audit agent
    security_agent = await spawner.spawn_for_skill(
        "paystack_security",
        context={
            "repository": "/home/teacherchris37/MasterBuilder7/projects/ihhashi",
            "focus_areas": ["webhooks", "api_keys", "transaction_validation"],
            "severity_threshold": "medium"
        }
    )
    
    print(f"Spawned: {security_agent.id}")
    print(f"Type: {security_agent.agent_type.value}")
    print(f"Status: {security_agent.status.value}")
    
    # Simulate work execution
    async def mock_security_audit():
        await asyncio.sleep(0.5)
        return {
            "findings": 3,
            "critical": 0,
            "high": 1,
            "medium": 2,
            "report_url": "/tmp/security_report.html"
        }
    
    result = await security_agent.execute(mock_security_audit)
    print(f"Result: {result}")
    
    print("\n--- Example 2: Spawn Multiple Agents in Parallel ---")
    
    # Spawn multiple agents for different tasks
    agents = await spawner.spawn_parallel([
        ("fastapi_security", {"scope": "api_routes", "auth_required": True}),
        ("db_query_optimizer", {"slow_query_threshold_ms": 100}),
        ("performance_profiler", {"target": "api_endpoints", "duration": "30s"})
    ])
    
    print(f"Spawned {len(agents)} agents in parallel:")
    for agent in agents:
        print(f"  - {agent.id} ({agent.agent_type.value})")
    
    print("\n--- Example 3: Get Specialized Agent ---")
    
    # Get a specialized agent for quick tasks
    quick_scan = spawner.get_specialized_agent(
        "quick_security_scan",
        {"repository": "/path/to/repo"}
    )
    if quick_scan:
        print(f"Specialized agent ready: {quick_scan.id}")
        print(f"Pre-configured for: {quick_scan.agent_type.value}")
    
    print("\n--- Example 4: System Status ---")
    
    status = spawner.get_system_status()
    print(f"Active agents: {status['active_agents']}")
    print(f"Cost: ${status['global_cost']['incurred']} / ${status['global_cost']['budget']}")
    print(f"Available slots: {status['available_slots']}")
    print(f"Registered skills: {status['registered_skills']}")
    
    print("\n--- Example 5: Lifecycle Management ---")
    
    # Spawn and track an agent
    agent = await spawner.spawn_for_skill(
        "reward_calculator",
        {"customer_id": "cust_12345", "calculate_for": "current_month"}
    )
    
    # Track the agent
    tracked = spawner.track_agent(agent.id)
    print(f"Tracking agent: {tracked.id if tracked else 'not found'}")
    
    # Get detailed status
    agent_status = spawner.get_agent_status(agent.id)
    print(f"Agent status: {agent_status['status']}")
    
    # Terminate gracefully
    terminated = await spawner.terminate_agent(agent.id, reason="example_complete")
    print(f"Terminated successfully: {terminated}")
    
    print("\n--- Example 6: Context Manager (Auto-cleanup) ---")
    
    async with spawner.managed_spawn(
        "capacitor_build_expert",
        {"platform": "android", "issue": "gradle_sync_failure"}
    ) as agent:
        print(f"Working with agent: {agent.id}")
        # Agent automatically terminated on exit
    print("Agent auto-terminated on context exit")
    
    print("\n--- Final System Status ---")
    final_status = spawner.get_system_status()
    print(json.dumps(final_status, indent=2))
    
    print("\n" + "=" * 70)
    print("Example complete!")
    print("=" * 70)
    
    return spawner


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())
