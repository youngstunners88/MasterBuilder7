#!/usr/bin/env python3
"""
YOLO Mode with Multi-AI Support
Deploys ChatGPT, Grok, Kimi, and all agents in parallel
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent))

from multi_ai_orchestrator import (
    MultiAIOrchestrator, 
    ParallelAgentSwarm, 
    AISystem, 
    TaskAssignment
)
from yolo_orchestrator import YOLOOrchestrator, BuildStage


class YOLOMultiAI(YOLOOrchestrator):
    """
    YOLO Mode with Multi-AI Orchestration
    Uses ChatGPT, Grok, Kimi, Claude simultaneously
    """
    
    def __init__(self, project_path: str, safety_threshold: float = 0.6):
        super().__init__(project_path, safety_threshold)
        self.multi_ai = MultiAIOrchestrator()
        self.swarm = ParallelAgentSwarm(self.multi_ai)
        
        # Register all available AIs
        self._register_ais()
        
    def _register_ais(self):
        """Register all AI systems"""
        # In production, check for API keys
        self.multi_ai.register_ai(AISystem.KIMI)
        self.multi_ai.register_ai(AISystem.CHATGPT) 
        self.multi_ai.register_ai(AISystem.GROK)
        self.multi_ai.register_ai(AISystem.CLAUDE)
        
        print("🎭 Multi-AI Orchestra Ready:")
        print("   🟢 Kimi (Code Generation)")
        print("   🟢 ChatGPT (Architecture & Reasoning)")
        print("   🟢 Grok (Real-time Data)")
        print("   🟢 Claude (Documentation & Analysis)")
    
    async def run_yolo_build_multi_ai(self) -> Dict[str, Any]:
        """
        YOLO build using ALL AIs in parallel
        Maximum effectiveness, not too many chefs!
        """
        print("\n" + "="*70)
        print("🔥 YOLO MODE: MULTI-AI ORCHESTRATION")
        print("="*70)
        print(f"Project: {self.project_path}")
        print(f"AIs: Kimi + ChatGPT + Grok + Claude")
        print(f"Max Parallel Agents: {self.swarm.max_parallel_agents}")
        print("="*70 + "\n")
        
        # Deploy FULL SWARM immediately
        print("🐝 Deploying FULL AGENT SWARM...")
        swarm_result = await self.swarm.deploy_full_swarm(self.project_path)
        
        # Continue with consensus verification
        print("\n🗳️ Running Multi-AI Consensus...")
        consensus_tasks = [
            ("architecture_design", "Verify architecture decisions"),
            ("security_audit", "Security consensus"),
            ("code_generation", "Code quality check"),
        ]
        
        consensus_results = []
        for task_type, description in consensus_tasks:
            result = await self.multi_ai.multi_ai_consensus(
                task_type, 
                description,
                min_ais=3
            )
            consensus_results.append({
                "task": description,
                "consensus": result['consensus_reached'],
                "confidence": result['confidence']
            })
        
        # Final result
        return {
            "build_id": self.build_id,
            "mode": "YOLO_MULTI_AI",
            "ais_used": ["kimi", "chatgpt", "grok", "claude"],
            "swarm_deployment": swarm_result,
            "consensus_checks": consensus_results,
            "total_agents": swarm_result['total_agents_deployed'],
            "parallel_efficiency": swarm_result['parallel_efficiency'],
            "status": "complete" if swarm_result['failed'] == 0 else "partial"
        }


async def main():
    """Run YOLO Multi-AI build"""
    import argparse
    
    parser = argparse.ArgumentParser(description="YOLO Multi-AI Build")
    parser.add_argument("project_path", help="Path to project")
    parser.add_argument("--safety", type=float, default=0.6)
    
    args = parser.parse_args()
    
    # Create orchestrator
    yolo = YOLOMultiAI(args.project_path, args.safety)
    
    # Initialize
    await yolo.initialize()
    
    # Run multi-AI build
    result = await yolo.run_yolo_build_multi_ai()
    
    # Print results
    print("\n" + "="*70)
    print("🏁 MULTI-AI BUILD COMPLETE")
    print("="*70)
    print(json.dumps(result, indent=2))
    
    return result


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result['status'] == 'complete' else 1)
