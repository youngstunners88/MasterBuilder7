#!/usr/bin/env python3
"""
Agentic Build Master - Pure Agentic Collaboration System
Coordinates all agents (ZO1, ZO2, Kimi, ChatGPT, Grok, Claude) to build autonomously
"""

import asyncio
import json
import time
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

sys.path.insert(0, str(Path(__file__).parent))

# Import all agentic infrastructure
from agents.agent_protocol import AgentBus, AgentMessage, MessageType, create_agent_bus
from agents.shared_state import SharedStateManager, StateType
from agents.task_queue import TaskQueue, TaskPriority, TaskStatus
from agents.health_monitor import HealthMonitor, HealthStatus
from agents.cost_tracker import CostTracker, AIProvider, get_tracker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger('AGENTIC_BUILD')


@dataclass
class BuildComponent:
    """A component to be built by agents"""
    id: str
    name: str
    description: str
    assigned_agents: List[str]
    dependencies: List[str]
    status: str = "pending"
    priority: int = 5
    ai_specialty: str = "kimi"  # Which AI is best for this


class AgenticBuildMaster:
    """
    Master orchestrator for pure agentic collaboration
    All agents work together autonomously
    """
    
    def __init__(self, project_path: str, build_id: str = None):
        self.project_path = project_path
        self.build_id = build_id or f"agentic-{int(time.time())}"
        
        # Core infrastructure
        self.agent_bus: Optional[AgentBus] = None
        self.state_manager: Optional[SharedStateManager] = None
        self.task_queue: Optional[TaskQueue] = None
        self.health_monitor: Optional[HealthMonitor] = None
        self.cost_tracker: Optional[CostTracker] = None
        
        # Active agents
        self.agents: Dict[str, dict] = {
            "zo1": {"type": "frontend", "status": "idle", "ai": "kimi"},
            "zo2": {"type": "backend", "status": "idle", "ai": "kimi"},
            "kimi": {"type": "code_gen", "status": "idle", "ai": "kimi"},
            "chatgpt": {"type": "architecture", "status": "idle", "ai": "chatgpt"},
            "grok": {"type": "research", "status": "idle", "ai": "grok"},
            "claude": {"type": "docs", "status": "idle", "ai": "claude"},
        }
        
        # Build components
        self.components: Dict[str, BuildComponent] = {}
        
        self.running = False
        
    async def initialize(self):
        """Initialize all agentic infrastructure"""
        logger.info("🚀 Initializing Agentic Build Master...")
        
        # 1. Initialize agent bus (communication)
        logger.info("   📡 Initializing Agent Bus...")
        self.agent_bus = await create_agent_bus()
        await self.agent_bus.connect()
        
        # 2. Initialize shared state
        logger.info("   💾 Initializing Shared State...")
        self.state_manager = SharedStateManager()
        await self.state_manager.connect()
        
        # 3. Initialize task queue
        logger.info("   📋 Initializing Task Queue...")
        self.task_queue = TaskQueue()
        await self.task_queue.connect()
        
        # 4. Initialize health monitor
        logger.info("   ❤️  Initializing Health Monitor...")
        self.health_monitor = HealthMonitor()
        await self.health_monitor.initialize()
        
        # 5. Initialize cost tracker
        logger.info("   💰 Initializing Cost Tracker...")
        self.cost_tracker = get_tracker(daily_budget=500.0)
        
        # Register all agents
        for agent_id, agent_info in self.agents.items():
            await self.health_monitor.register_agent(
                agent_id=agent_id,
                agent_type=agent_info["type"],
                capabilities=[agent_info["type"]],
                metadata={"ai": agent_info["ai"]}
            )
        
        # Subscribe to agent messages
        await self.agent_bus.subscribe("build-master", self._handle_agent_message)
        await self.agent_bus.subscribe("#", self._broadcast_handler)  # All messages
        
        # Set initial state
        await self.state_manager.set(
            f"build:{self.build_id}:status",
            "initializing",
            StateType.STRING
        )
        
        logger.info("✅ Agentic infrastructure initialized")
        logger.info(f"   Build ID: {self.build_id}")
        logger.info(f"   Agents: {len(self.agents)}")
        
    async def _handle_agent_message(self, message: AgentMessage):
        """Handle messages from agents"""
        logger.info(f"📨 Message from {message.sender}: {message.message_type}")
        
        if message.message_type == MessageType.TASK_COMPLETE:
            await self._handle_task_complete(message)
        elif message.message_type == MessageType.HELP_REQUEST:
            await self._handle_help_request(message)
        elif message.message_type == MessageType.STATE_UPDATE:
            await self._handle_state_update(message)
            
    async def _broadcast_handler(self, message: AgentMessage):
        """Handle broadcast messages"""
        # Update heartbeat
        if message.sender in self.agents:
            await self.health_monitor.heartbeat(
                agent_id=message.sender,
                status="healthy"
            )
    
    async def _handle_task_complete(self, message: AgentMessage):
        """Handle task completion"""
        component_id = message.payload.get("component_id")
        if component_id and component_id in self.components:
            self.components[component_id].status = "completed"
            logger.info(f"✅ Component completed: {component_id}")
            
            # Record cost
            self.cost_tracker.record_usage(
                agent_id=message.sender,
                provider=AIProvider.KIMI,
                model="kimi-k2-5",
                tokens_input=message.payload.get("tokens_in", 1000),
                tokens_output=message.payload.get("tokens_out", 500),
                request_type="component_build"
            )
    
    async def _handle_help_request(self, message: AgentMessage):
        """Handle help requests from agents"""
        # Find best agent to help
        help_type = message.payload.get("help_type")
        best_helper = self._find_best_agent(help_type)
        
        if best_helper:
            await self.agent_bus.send_direct(
                sender="build-master",
                recipient=best_helper,
                message_type=MessageType.HELP_REQUEST,
                payload={
                    "original_sender": message.sender,
                    "help_type": help_type,
                    "context": message.payload
                }
            )
    
    async def _handle_state_update(self, message: AgentMessage):
        """Handle state updates"""
        # Broadcast to all interested agents
        pass
    
    def _find_best_agent(self, task_type: str) -> Optional[str]:
        """Find best agent for a task type"""
        agent_specialties = {
            "code": "kimi",
            "architecture": "chatgpt",
            "research": "grok",
            "docs": "claude",
            "frontend": "zo1",
            "backend": "zo2",
        }
        
        specialty = agent_specialties.get(task_type, "kimi")
        for agent_id, info in self.agents.items():
            if info["ai"] == specialty and info["status"] == "idle":
                return agent_id
        
        # Fallback to any idle agent
        for agent_id, info in self.agents.items():
            if info["status"] == "idle":
                return agent_id
        
        return None
    
    def define_build_components(self):
        """Define all components to build"""
        self.components = {
            "api_endpoints": BuildComponent(
                id="api_endpoints",
                name="API Endpoints",
                description="RESTful API endpoints for agent communication",
                assigned_agents=["zo2", "kimi"],
                dependencies=[],
                priority=10,
                ai_specialty="kimi"
            ),
            "database_schema": BuildComponent(
                id="database_schema",
                name="Database Schema",
                description="PostgreSQL schema with migrations",
                assigned_agents=["claude", "kimi"],
                dependencies=[],
                priority=9,
                ai_specialty="claude"
            ),
            "frontend_ui": BuildComponent(
                id="frontend_ui",
                name="Frontend UI",
                description="React dashboard for monitoring",
                assigned_agents=["zo1", "kimi"],
                dependencies=["api_endpoints"],
                priority=8,
                ai_specialty="kimi"
            ),
            "agent_workers": BuildComponent(
                id="agent_workers",
                name="Agent Workers",
                description="Worker processes for parallel execution",
                assigned_agents=["zo1", "zo2", "kimi"],
                dependencies=["api_endpoints", "database_schema"],
                priority=10,
                ai_specialty="kimi"
            ),
            "monitoring_dashboard": BuildComponent(
                id="monitoring_dashboard",
                name="Monitoring Dashboard",
                description="Real-time monitoring and metrics",
                assigned_agents=["claude", "zo1"],
                dependencies=["frontend_ui"],
                priority=7,
                ai_specialty="claude"
            ),
            "ci_cd_pipeline": BuildComponent(
                id="ci_cd_pipeline",
                name="CI/CD Pipeline",
                description="GitHub Actions for automated builds",
                assigned_agents=["zo2", "chatgpt"],
                dependencies=[],
                priority=6,
                ai_specialty="chatgpt"
            ),
            "security_audit": BuildComponent(
                id="security_audit",
                name="Security Audit",
                description="Automated security scanning",
                assigned_agents=["kimi", "chatgpt"],
                dependencies=["api_endpoints", "agent_workers"],
                priority=9,
                ai_specialty="kimi"
            ),
            "documentation": BuildComponent(
                id="documentation",
                name="Documentation",
                description="Complete API and user docs",
                assigned_agents=["claude"],
                dependencies=[],
                priority=5,
                ai_specialty="claude"
            ),
            "tests": BuildComponent(
                id="tests",
                name="Test Suite",
                description="Unit and integration tests",
                assigned_agents=["kimi", "zo1"],
                dependencies=["agent_workers"],
                priority=8,
                ai_specialty="kimi"
            ),
            "deployment_config": BuildComponent(
                id="deployment_config",
                name="Deployment Config",
                description="Docker, K8s, and deployment scripts",
                assigned_agents=["zo2", "chatgpt"],
                dependencies=["ci_cd_pipeline"],
                priority=7,
                ai_specialty="chatgpt"
            ),
        }
    
    async def start_agentic_build(self):
        """Start the pure agentic build process"""
        logger.info("\n" + "="*70)
        logger.info("🔥 STARTING AGENTIC BUILD - ALL AGENTS COLLABORATING")
        logger.info("="*70)
        
        self.running = True
        
        # Define components
        self.define_build_components()
        
        # Update state
        await self.state_manager.set(
            f"build:{self.build_id}:status",
            "building",
            StateType.STRING
        )
        
        # Broadcast start
        await self.agent_bus.broadcast(
            sender="build-master",
            message_type=MessageType.WORKFLOW_START,
            payload={
                "build_id": self.build_id,
                "component_count": len(self.components),
                "agents": list(self.agents.keys())
            }
        )
        
        # Start build loop
        while self.running:
            # Find ready components (dependencies met)
            ready_components = self._get_ready_components()
            
            if not ready_components and self._all_complete():
                logger.info("✅ All components built!")
                break
            
            # Assign components to agents
            for component in ready_components:
                await self._assign_component(component)
            
            # Check health
            await self._check_system_health()
            
            # Check budget
            budget_status = self.cost_tracker.check_budget()
            if budget_status["status"] == "exceeded":
                logger.error("❌ Budget exceeded! Stopping build.")
                await self._emergency_stop()
                break
            
            # Progress report
            await self._report_progress()
            
            await asyncio.sleep(5)
        
        await self._finalize_build()
    
    def _get_ready_components(self) -> List[BuildComponent]:
        """Get components ready to build (dependencies met)"""
        ready = []
        for comp in self.components.values():
            if comp.status != "pending":
                continue
            
            # Check dependencies
            deps_met = all(
                self.components.get(dep, BuildComponent("", "", "", [], [])).status == "completed"
                for dep in comp.dependencies
            )
            
            if deps_met:
                ready.append(comp)
        
        # Sort by priority
        ready.sort(key=lambda c: c.priority, reverse=True)
        return ready
    
    def _all_complete(self) -> bool:
        """Check if all components are complete"""
        return all(
            comp.status == "completed"
            for comp in self.components.values()
        )
    
    async def _assign_component(self, component: BuildComponent):
        """Assign a component to agents"""
        component.status = "building"
        
        # Find best agent
        best_agent = self._find_best_agent(component.ai_specialty)
        
        if not best_agent:
            logger.warning(f"⚠️ No agent available for {component.id}")
            component.status = "pending"
            return
        
        # Mark agent as busy
        self.agents[best_agent]["status"] = "busy"
        
        # Send task
        await self.agent_bus.send_direct(
            sender="build-master",
            recipient=best_agent,
            message_type=MessageType.TASK_REQUEST,
            payload={
                "component_id": component.id,
                "component_name": component.name,
                "description": component.description,
                "project_path": self.project_path
            },
            priority=component.priority
        )
        
        logger.info(f"📋 Assigned {component.id} to {best_agent}")
    
    async def _check_system_health(self):
        """Check health of all components"""
        health = await self.health_monitor.check_health()
        
        if health["overall"] == HealthStatus.FAILED:
            logger.error("❌ System health check failed!")
            await self._restart_failed_agents()
    
    async def _restart_failed_agents(self):
        """Restart any failed agents"""
        restarted = await self.health_monitor.restart_failed_agents()
        if restarted:
            logger.info(f"🔄 Restarted {len(restarted)} agents")
    
    async def _report_progress(self):
        """Report build progress"""
        completed = sum(1 for c in self.components.values() if c.status == "completed")
        total = len(self.components)
        percent = (completed / total * 100) if total > 0 else 0
        
        cost_report = self.cost_tracker.get_cost_report(period="today")
        
        logger.info(f"📊 Progress: {completed}/{total} ({percent:.1f}%) | "
                   f"Cost: ${cost_report.summary().get('total_cost', 0):.2f}")
        
        # Update shared state
        await self.state_manager.track_build_progress(
            build_id=self.build_id,
            stage="agentic_build",
            progress_percent=percent,
            status="running"
        )
    
    async def _emergency_stop(self):
        """Emergency stop all agents"""
        logger.error("🛑 EMERGENCY STOP")
        
        await self.agent_bus.broadcast(
            sender="build-master",
            message_type=MessageType.BROADCAST,
            payload={"command": "STOP", "reason": "budget_exceeded"}
        )
        
        self.running = False
    
    async def _finalize_build(self):
        """Finalize the build"""
        logger.info("\n" + "="*70)
        logger.info("🏁 AGENTIC BUILD COMPLETE")
        logger.info("="*70)
        
        # Update state
        await self.state_manager.set(
            f"build:{self.build_id}:status",
            "completed",
            StateType.STRING
        )
        
        # Final broadcast
        completed = sum(1 for c in self.components.values() if c.status == "completed")
        
        await self.agent_bus.broadcast(
            sender="build-master",
            message_type=MessageType.WORKFLOW_COMPLETE,
            payload={
                "build_id": self.build_id,
                "components_completed": completed,
                "total_components": len(self.components)
            }
        )
        
        # Final cost report
        cost_report = self.cost_tracker.get_cost_report(period="today")
        logger.info(f"💰 Total cost: ${cost_report.summary().get('total_cost', 0):.2f}")
        
        # Cleanup
        await self.agent_bus.disconnect()
        await self.state_manager.disconnect()
        await self.task_queue.disconnect()


async def main():
    """Run agentic build"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agentic Build Master")
    parser.add_argument("project_path", help="Path to project")
    parser.add_argument("--build-id", help="Build ID (optional)")
    
    args = parser.parse_args()
    
    # Create and initialize
    master = AgenticBuildMaster(args.project_path, args.build_id)
    await master.initialize()
    
    # Start build
    await master.start_agentic_build()


if __name__ == "__main__":
    asyncio.run(main())
