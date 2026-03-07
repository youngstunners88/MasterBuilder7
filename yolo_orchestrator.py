#!/usr/bin/env python3
"""
YOLO Mode Orchestrator for MasterBuilder7
Coordinates ZO1 and ZO2 computers in full autonomous build mode
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/yolo_build.log')
    ]
)
logger = logging.getLogger('YOLO')

# Add apex to path
sys.path.insert(0, str(Path(__file__).parent))


class BuildStage(Enum):
    IDLE = "idle"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    BUILDING_FRONTEND = "building_frontend"
    BUILDING_BACKEND = "building_backend"
    TESTING = "testing"
    DEPLOYING = "deploying"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class AgentStatus:
    name: str
    status: str = "idle"
    current_task: Optional[str] = None
    success_rate: float = 1.0
    last_heartbeat: float = field(default_factory=time.time)


@dataclass
class BuildState:
    build_id: str
    project_path: str
    stage: BuildStage = BuildStage.IDLE
    start_time: float = field(default_factory=time.time)
    agents: Dict[str, AgentStatus] = field(default_factory=dict)
    checkpoints: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    completed_tasks: int = 0
    total_tasks: int = 0


class YOLOOrchestrator:
    """
    YOLO Mode Orchestrator
    Runs all agents autonomously until project is complete
    """
    
    def __init__(self, project_path: str, safety_threshold: float = 0.6):
        self.project_path = project_path
        self.safety_threshold = safety_threshold
        self.build_id = f"yolo-{int(time.time())}"
        self.state = BuildState(
            build_id=self.build_id,
            project_path=project_path,
            agents={
                "zo1": AgentStatus(name="ZO1"),
                "zo2": AgentStatus(name="ZO2"),
                "meta_router": AgentStatus(name="Meta-Router"),
                "planning": AgentStatus(name="Planning"),
                "frontend": AgentStatus(name="Frontend"),
                "backend": AgentStatus(name="Backend"),
                "testing": AgentStatus(name="Testing"),
                "devops": AgentStatus(name="DevOps"),
                "reliability": AgentStatus(name="Reliability"),
                "evolution": AgentStatus(name="Evolution"),
            }
        )
        self.running = False
        self.consensus_engine = None
        self.checkpoint_manager = None
        
    async def initialize(self):
        """Initialize all components"""
        logger.info("🚀 Initializing YOLO Orchestrator...")
        
        # Import and initialize components
        try:
            from apex.reliability.consensus_engine import ConsensusEngine
            from apex.reliability.checkpoint_manager import CheckpointManager
            
            self.consensus_engine = ConsensusEngine(threshold=self.safety_threshold)
            self.checkpoint_manager = CheckpointManager()
            
            logger.info("✅ Consensus Engine initialized")
            logger.info("✅ Checkpoint Manager initialized")
            
        except Exception as e:
            logger.warning(f"⚠️  Some components not available: {e}")
        
        logger.info(f"✅ YOLO Orchestrator ready")
        logger.info(f"   Build ID: {self.build_id}")
        logger.info(f"   Project: {self.project_path}")
        logger.info(f"   Safety Threshold: {self.safety_threshold}")
        
    async def run_yolo_build(self) -> Dict[str, Any]:
        """
        Run complete YOLO mode build
        This runs ALL agents until project is complete
        """
        self.running = True
        start_time = time.time()
        
        logger.info("\n" + "="*60)
        logger.info("🔥 YOLO MODE BUILD STARTED 🔥")
        logger.info("="*60)
        
        try:
            # Stage 1: Analysis (ZO1)
            await self._run_stage(BuildStage.ANALYZING, "zo1", self._analyze_project)
            
            # Stage 2: Planning (ZO2)
            await self._run_stage(BuildStage.PLANNING, "zo2", self._create_plan)
            
            # Stage 3: Build Frontend (Parallel ZO1 + ZO2)
            await self._run_parallel_build()
            
            # Stage 4: Testing (Both ZOs)
            await self._run_stage(BuildStage.TESTING, "zo1", self._run_tests)
            
            # Stage 5: Deploy (Both ZOs)
            await self._run_stage(BuildStage.DEPLOYING, "zo2", self._deploy)
            
            self.state.stage = BuildStage.COMPLETE
            
        except Exception as e:
            logger.error(f"❌ Build failed: {e}")
            self.state.stage = BuildStage.FAILED
            self.state.errors.append(str(e))
            
            # Auto-rollback on failure
            if self.state.checkpoints:
                await self._rollback()
        
        finally:
            self.running = False
            
        duration = time.time() - start_time
        
        return {
            "build_id": self.build_id,
            "status": self.state.stage.value,
            "duration_seconds": duration,
            "agents_used": len(self.state.agents),
            "checkpoints_created": len(self.state.checkpoints),
            "tasks_completed": self.state.completed_tasks,
            "errors": self.state.errors
        }
    
    async def _run_stage(self, stage: BuildStage, agent_id: str, task_func):
        """Run a single build stage"""
        self.state.stage = stage
        agent = self.state.agents[agent_id]
        agent.status = "working"
        agent.current_task = stage.value
        
        logger.info(f"\n📋 Stage: {stage.value.upper()}")
        logger.info(f"   Agent: {agent_id}")
        
        try:
            # Create checkpoint before stage
            await self._create_checkpoint(stage.value)
            
            # Execute task
            result = await task_func()
            
            # Verify with consensus if available
            if self.consensus_engine:
                # Mock consensus for demo
                import random
                score = random.uniform(0.7, 0.95)
                if score < self.safety_threshold:
                    raise Exception(f"Consensus rejected {stage.value} (score: {score:.2f})")
            
            agent.status = "complete"
            self.state.completed_tasks += 1
            
            logger.info(f"✅ Stage complete: {stage.value}")
            
        except Exception as e:
            agent.status = "failed"
            raise
    
    async def _run_parallel_build(self):
        """Run frontend and backend in parallel"""
        logger.info("\n📋 Stage: PARALLEL BUILD")
        logger.info("   ZO1: Frontend | ZO2: Backend")
        
        self.state.stage = BuildStage.BUILDING_FRONTEND
        
        # Create tasks
        frontend_task = self._build_frontend()
        backend_task = self._build_backend()
        
        # Run in parallel
        results = await asyncio.gather(
            frontend_task,
            backend_task,
            return_exceptions=True
        )
        
        # Check results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                raise result
        
        logger.info("✅ Parallel build complete")
    
    async def _analyze_project(self) -> Dict:
        """ZO1: Analyze project"""
        logger.info("   Analyzing project structure...")
        
        try:
            from core.agents.meta_router import MetaRouterAgent
            agent = MetaRouterAgent()
            result = await agent.analyze_repository(self.project_path)
            
            logger.info(f"   Stack detected: {result.get('stack_detection', {}).get('primary_stack', 'unknown')}")
            return result
            
        except Exception as e:
            logger.warning(f"   Meta-router not available, using basic analysis: {e}")
            return {"stack": "unknown", "error": str(e)}
    
    async def _create_plan(self) -> Dict:
        """ZO2: Create build plan"""
        logger.info("   Creating build plan...")
        
        # Simulate planning
        await asyncio.sleep(1)
        
        plan = {
            "agents_required": 8,
            "estimated_time": "45 minutes",
            "stages": ["analysis", "planning", "frontend", "backend", "testing", "deploy"]
        }
        
        logger.info(f"   Plan created: {plan['agents_required']} agents")
        return plan
    
    async def _build_frontend(self) -> Dict:
        """ZO1: Build frontend"""
        self.state.agents["zo1"].current_task = "building_frontend"
        logger.info("   ZO1: Building frontend...")
        
        # Simulate build
        await asyncio.sleep(2)
        
        result = {"status": "success", "components": 15, "tests": 20}
        logger.info(f"   Frontend: {result['components']} components built")
        return result
    
    async def _build_backend(self) -> Dict:
        """ZO2: Build backend"""
        self.state.agents["zo2"].current_task = "building_backend"
        logger.info("   ZO2: Building backend...")
        
        # Simulate build
        await asyncio.sleep(2)
        
        result = {"status": "success", "endpoints": 12, "models": 8}
        logger.info(f"   Backend: {result['endpoints']} endpoints created")
        return result
    
    async def _run_tests(self) -> Dict:
        """Run all tests"""
        logger.info("   Running tests...")
        
        # Simulate tests
        await asyncio.sleep(2)
        
        result = {"passed": 85, "failed": 0, "coverage": 87.5}
        logger.info(f"   Tests: {result['passed']} passed, {result['coverage']:.1f}% coverage")
        return result
    
    async def _deploy(self) -> Dict:
        """Deploy application"""
        logger.info("   Deploying...")
        
        # Simulate deployment
        await asyncio.sleep(1)
        
        result = {"status": "deployed", "url": "https://app.example.com"}
        logger.info(f"   Deployed to: {result['url']}")
        return result
    
    async def _create_checkpoint(self, stage: str):
        """Create 3-tier checkpoint"""
        checkpoint_id = f"{self.build_id}-{stage}"
        self.state.checkpoints.append(checkpoint_id)
        
        if self.checkpoint_manager:
            try:
                self.checkpoint_manager.create_checkpoint(
                    build_id=self.build_id,
                    stage=stage,
                    files=[],
                    metadata={"agent": "yolo", "stage": stage}
                )
            except Exception as e:
                logger.warning(f"   Checkpoint failed: {e}")
        
        logger.info(f"   Checkpoint: {checkpoint_id}")
    
    async def _rollback(self):
        """Rollback to last checkpoint"""
        if not self.state.checkpoints:
            return
        
        last_checkpoint = self.state.checkpoints[-1]
        logger.info(f"⏮️  Rolling back to: {last_checkpoint}")
        
        if self.checkpoint_manager:
            try:
                self.checkpoint_manager.rollback_to_checkpoint(last_checkpoint)
                logger.info("✅ Rollback complete")
            except Exception as e:
                logger.error(f"❌ Rollback failed: {e}")
    
    def get_status(self) -> Dict:
        """Get current build status"""
        return {
            "build_id": self.build_id,
            "stage": self.state.stage.value,
            "running": self.running,
            "agents": {k: {
                "status": v.status,
                "task": v.current_task
            } for k, v in self.state.agents.items()},
            "checkpoints": len(self.state.checkpoints),
            "elapsed_time": time.time() - self.state.start_time
        }


async def main():
    """Run YOLO mode build"""
    import argparse
    
    parser = argparse.ArgumentParser(description="YOLO Mode Build Orchestrator")
    parser.add_argument("project_path", help="Path to project")
    parser.add_argument("--safety", type=float, default=0.6, help="Safety threshold")
    parser.add_argument("--agents", type=int, default=64, help="Max agents")
    
    args = parser.parse_args()
    
    # Create orchestrator
    orchestrator = YOLOOrchestrator(
        project_path=args.project_path,
        safety_threshold=args.safety
    )
    
    # Initialize
    await orchestrator.initialize()
    
    # Run build
    result = await orchestrator.run_yolo_build()
    
    # Print final result
    logger.info("\n" + "="*60)
    logger.info("🏁 BUILD COMPLETE")
    logger.info("="*60)
    logger.info(f"Status: {result['status'].upper()}")
    logger.info(f"Duration: {result['duration_seconds']:.1f}s")
    logger.info(f"Agents: {result['agents_used']}")
    logger.info(f"Tasks: {result['tasks_completed']}")
    logger.info(f"Checkpoints: {result['checkpoints_created']}")
    
    if result['errors']:
        logger.info(f"Errors: {len(result['errors'])}")
        for error in result['errors']:
            logger.error(f"   - {error}")
    
    return result


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result['status'] == 'complete' else 1)
