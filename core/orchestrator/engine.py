#!/usr/bin/env python3
"""
APEX Core Orchestrator - 8 Specialist Agent Engine
Surpasses Emergent.sh through intelligence, not brute force
"""

import asyncio
import json
import hashlib
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import sqlite3
import os


class AgentType(Enum):
    META_ROUTER = "meta_router"      # Stack detection, routing
    PLANNING = "planning"            # Architecture, specs
    FRONTEND = "frontend"            # React/Vite/Capacitor
    BACKEND = "backend"              # FastAPI/Supabase
    TESTING = "testing"              # QA, security scans
    DEVOPS = "devops"                # CI/CD, deployment
    RELIABILITY = "reliability"      # Consensus, checkpoints
    EVOLUTION = "evolution"          # Learning, optimization


@dataclass
class Task:
    id: str
    type: str
    agent_type: AgentType
    input_data: Dict
    status: str = "pending"  # pending, running, completed, failed
    priority: int = 5        # 1-10, 10 = highest
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict] = None
    error: Optional[str] = None
    parent_task_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)


@dataclass
class Agent:
    id: str
    type: AgentType
    name: str
    status: str = "idle"  # idle, busy, error
    current_task: Optional[str] = None
    capabilities: List[str] = field(default_factory=list)
    success_rate: float = 1.0
    total_tasks: int = 0
    failed_tasks: int = 0


DEFAULT_DB_PATH = os.getenv(
    "APEX_ORCHESTRATOR_DB_PATH",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "orchestrator.db")
)


class AgentOrchestrator:
    """
    Central orchestrator for 8 specialist agents
    Features that surpass Emergent.sh:
    - Intelligent task routing (not random)
    - Dependency-aware parallel execution
    - Self-healing on failure
    - Real-time consensus
    - Continuous evolution
    """
    
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.agents: Dict[str, Agent] = {}
        self.task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.running_tasks: Dict[str, Task] = {}
        self.completed_tasks: Dict[str, Task] = {}
        self.event_handlers: Dict[str, List[Callable]] = {}
        self._init_db()
        self._init_agents()
        
    def _init_db(self):
        """Initialize SQLite database for persistence"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                type TEXT,
                agent_type TEXT,
                input_data TEXT,
                status TEXT,
                priority INTEGER,
                created_at TEXT,
                started_at TEXT,
                completed_at TEXT,
                result TEXT,
                error TEXT,
                parent_task_id TEXT,
                dependencies TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_stats (
                agent_id TEXT PRIMARY KEY,
                type TEXT,
                total_tasks INTEGER,
                failed_tasks INTEGER,
                success_rate REAL,
                avg_execution_time REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _init_agents(self):
        """Initialize the 8 specialist agents"""
        agent_configs = [
            (AgentType.META_ROUTER, "Meta-Router", ["repo_analysis", "stack_detection", "routing"]),
            (AgentType.PLANNING, "Planning", ["architecture", "specs", "risk_assessment"]),
            (AgentType.FRONTEND, "Frontend", ["react", "vite", "capacitor", "tailwind"]),
            (AgentType.BACKEND, "Backend", ["fastapi", "supabase", "postgresql", "api_design"]),
            (AgentType.TESTING, "Testing", ["jest", "pytest", "security_scan", "e2e"]),
            (AgentType.DEVOPS, "DevOps", ["docker", "k8s", "ci_cd", "deploy"]),
            (AgentType.RELIABILITY, "Reliability", ["consensus", "checkpoint", "rollback"]),
            (AgentType.EVOLUTION, "Evolution", ["pattern_extraction", "optimization", "learning"]),
        ]
        
        for agent_type, name, capabilities in agent_configs:
            agent_id = f"{agent_type.value}-001"
            self.agents[agent_id] = Agent(
                id=agent_id,
                type=agent_type,
                name=name,
                capabilities=capabilities
            )
    
    async def submit_task(self, task_type: str, agent_type: AgentType, 
                         input_data: Dict, priority: int = 5,
                         dependencies: List[str] = None) -> str:
        """Submit a task to the orchestrator"""
        
        task_id = self._generate_task_id(task_type, input_data)
        
        task = Task(
            id=task_id,
            type=task_type,
            agent_type=agent_type,
            input_data=input_data,
            priority=priority,
            dependencies=dependencies or []
        )
        
        # Store in database
        self._persist_task(task)
        
        # Add to queue (priority queue uses negative priority for highest first)
        await self.task_queue.put((-priority, task))
        
        self._emit_event("task_submitted", {"task_id": task_id, "type": task_type})
        
        return task_id
    
    def _generate_task_id(self, task_type: str, input_data: Dict) -> str:
        """Generate unique task ID"""
        data_str = json.dumps(input_data, sort_keys=True)
        hash_input = f"{task_type}:{data_str}:{datetime.now().isoformat()}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def _persist_task(self, task: Task):
        """Save task to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO tasks 
            (id, type, agent_type, input_data, status, priority, created_at, dependencies)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task.id, task.type, task.agent_type.value,
            json.dumps(task.input_data), task.status, task.priority,
            task.created_at.isoformat(), json.dumps(task.dependencies)
        ))
        
        conn.commit()
        conn.close()
    
    async def process_tasks(self):
        """Main task processing loop"""
        while True:
            try:
                # Get highest priority task
                priority, task = await asyncio.wait_for(
                    self.task_queue.get(), timeout=1.0
                )
                
                # Check dependencies
                if not self._dependencies_satisfied(task):
                    # Re-queue with slightly lower priority
                    await self.task_queue.put((priority + 0.1, task))
                    continue
                
                # Find best agent for this task
                agent = self._select_agent(task.agent_type)
                
                if agent:
                    await self._execute_task(agent, task)
                else:
                    # No agent available, re-queue
                    await self.task_queue.put((priority, task))
                    await asyncio.sleep(0.5)
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Orchestrator error: {e}")
    
    def _dependencies_satisfied(self, task: Task) -> bool:
        """Check if all dependencies are completed"""
        for dep_id in task.dependencies:
            if dep_id not in self.completed_tasks:
                return False
        return True
    
    def _select_agent(self, agent_type: AgentType) -> Optional[Agent]:
        """Select best available agent for task type"""
        available = [
            a for a in self.agents.values()
            if a.type == agent_type and a.status == "idle"
        ]
        
        if not available:
            return None
        
        # Sort by success rate (highest first)
        available.sort(key=lambda a: a.success_rate, reverse=True)
        return available[0]
    
    async def _execute_task(self, agent: Agent, task: Task):
        """Execute task on selected agent"""
        agent.status = "busy"
        agent.current_task = task.id
        task.status = "running"
        task.started_at = datetime.now()
        
        self.running_tasks[task.id] = task
        
        self._emit_event("task_started", {
            "task_id": task.id,
            "agent_id": agent.id
        })
        
        try:
            # Simulate task execution (replace with actual agent execution)
            result = await self._run_agent_task(agent, task)
            
            task.result = result
            task.status = "completed"
            task.completed_at = datetime.now()
            
            agent.total_tasks += 1
            agent.success_rate = (agent.total_tasks - agent.failed_tasks) / agent.total_tasks
            
            self.completed_tasks[task.id] = task
            del self.running_tasks[task.id]
            
            self._emit_event("task_completed", {
                "task_id": task.id,
                "agent_id": agent.id,
                "result": result
            })
            
        except Exception as e:
            task.error = str(e)
            task.status = "failed"
            task.completed_at = datetime.now()
            
            agent.failed_tasks += 1
            agent.total_tasks += 1
            agent.success_rate = (agent.total_tasks - agent.failed_tasks) / agent.total_tasks
            
            # Trigger self-healing
            await self._self_heal(agent, task, e)
            
        finally:
            agent.status = "idle"
            agent.current_task = None
            self._persist_task(task)
    
    async def _run_agent_task(self, agent: Agent, task: Task) -> Dict:
        """Run actual agent task - this would call the AI model"""
        # Placeholder - actual implementation would call Kimi/Zo API
        await asyncio.sleep(0.1)  # Simulate work
        
        return {
            "agent_type": agent.type.value,
            "task_type": task.type,
            "executed_at": datetime.now().isoformat(),
            "output": f"Task {task.id} completed by {agent.name}"
        }
    
    async def _self_heal(self, agent: Agent, task: Task, error: Exception):
        """Self-healing mechanism when task fails"""
        print(f"🩹 Self-healing triggered for task {task.id}: {error}")
        
        # Try with different agent of same type
        other_agents = [
            a for a in self.agents.values()
            if a.type == agent.type and a.id != agent.id
        ]
        
        if other_agents:
            new_agent = other_agents[0]
            print(f"🔄 Retrying with agent {new_agent.id}")
            await self._execute_task(new_agent, task)
        else:
            # Escalate to Evolution agent for analysis
            await self.submit_task(
                "failure_analysis",
                AgentType.EVOLUTION,
                {"failed_task": task.id, "error": str(error)},
                priority=10
            )
    
    def _emit_event(self, event_type: str, data: Dict):
        """Emit event to registered handlers"""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    handler(data)
                except Exception as e:
                    print(f"Event handler error: {e}")
    
    def on_event(self, event_type: str, handler: Callable):
        """Register event handler"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    def get_status(self) -> Dict:
        """Get current orchestrator status"""
        return {
            "agents": {
                agent_id: {
                    "type": agent.type.value,
                    "status": agent.status,
                    "success_rate": agent.success_rate,
                    "total_tasks": agent.total_tasks
                }
                for agent_id, agent in self.agents.items()
            },
            "queue_size": self.task_queue.qsize(),
            "running_tasks": len(self.running_tasks),
            "completed_tasks": len(self.completed_tasks)
        }


# Singleton instance
_orchestrator: Optional[AgentOrchestrator] = None


def get_orchestrator() -> AgentOrchestrator:
    """Get or create orchestrator singleton"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator


if __name__ == "__main__":
    # Test the orchestrator
    async def test():
        orch = get_orchestrator()
        
        # Print initial status
        print("Initial Status:")
        print(json.dumps(orch.get_status(), indent=2))
        
        # Start processing loop in background
        asyncio.create_task(orch.process_tasks())
        
        # Submit some test tasks
        print("\nSubmitting tasks...")
        
        task1 = await orch.submit_task(
            "analyze_repo",
            AgentType.META_ROUTER,
            {"repo_url": "https://github.com/example/app"},
            priority=8
        )
        print(f"Submitted: {task1}")
        
        task2 = await orch.submit_task(
            "design_architecture",
            AgentType.PLANNING,
            {"requirements": ["auth", "payments"]},
            priority=7,
            dependencies=[task1]
        )
        print(f"Submitted: {task2}")
        
        # Wait a bit
        await asyncio.sleep(2)
        
        print("\nFinal Status:")
        print(json.dumps(orch.get_status(), indent=2))
    
    asyncio.run(test())
