#!/usr/bin/env python3
"""
Universal MCP Client for MasterBuilder7
Use this to connect ChatGPT, Grok, Kimi, Claude, or any AI
"""

import requests
import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class MCPConfig:
    """Configuration for MCP connection"""
    server_url: str = "http://localhost:8000"
    ai_name: str = "unknown"
    api_key: Optional[str] = None
    timeout: int = 30


class MasterBuilder7MCP:
    """
    Universal MCP Client
    
    Usage:
        # For ChatGPT
        mcp = MasterBuilder7MCP("http://YOUR_IP:8000", "chatgpt")
        mcp.connect()
        result = mcp.yolo_mode("/path/to/project")
        
        # For Grok
        mcp = MasterBuilder7MCP("http://YOUR_IP:8000", "grok")
        mcp.connect()
        result = mcp.deploy_agents_parallel("/path/to/project")
    """
    
    def __init__(self, server_url: str, ai_name: str, api_key: str = None):
        self.config = MCPConfig(
            server_url=server_url,
            ai_name=ai_name,
            api_key=api_key
        )
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"X-API-Key": api_key})
        
    def connect(self, ai_info: dict = None) -> dict:
        """
        Connect to MCP server
        
        Call this first before using other methods!
        """
        response = self.session.post(
            f"{self.config.server_url}/mcp/connect",
            json={
                "ai_name": self.config.ai_name,
                "info": ai_info or {
                    "name": self.config.ai_name,
                    "connected_at": time.time()
                }
            },
            timeout=self.config.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def _invoke(self, tool: str, params: dict) -> dict:
        """Internal: invoke an MCP tool"""
        response = self.session.post(
            f"{self.config.server_url}/mcp/invoke",
            json={
                "tool": tool,
                "params": params,
                "ai_source": self.config.ai_name,
                "request_id": f"{self.config.ai_name}-{int(time.time())}"
            },
            timeout=self.config.timeout
        )
        response.raise_for_status()
        return response.json()
    
    # === HIGH-LEVEL METHODS ===
    
    def analyze_project(self, project_path: str) -> dict:
        """
        Analyze project structure and detect stack
        
        Returns:
            {
                "project_path": str,
                "stack_detected": str,
                "automation_potential": float,
                "agents_needed": list
            }
        """
        return self._invoke("analyze_project", {
            "project_path": project_path,
            "project_name": "project"
        })
    
    def execute_build(self, project_path: str, yolo_mode: bool = True, 
                      max_agents: int = 64) -> dict:
        """
        Execute full build
        
        Args:
            project_path: Path to project
            yolo_mode: Enable YOLO mode (default: True)
            max_agents: Max parallel agents (default: 64)
        
        Returns:
            {
                "build_id": str,
                "status": str,
                "message": str
            }
        """
        return self._invoke("execute_build", {
            "project_path": project_path,
            "yolo_mode": yolo_mode,
            "max_agents": max_agents
        })
    
    def yolo_mode(self, project_path: str, safety_threshold: float = 0.6) -> dict:
        """
        Enable YOLO mode - full autonomous build
        
        Args:
            project_path: Path to project
            safety_threshold: Safety threshold 0.0-1.0 (default: 0.6)
        
        Returns:
            {
                "yolo_mode": "ENGAGED",
                "zo1": "ONLINE",
                "zo2": "ONLINE"
            }
        """
        return self._invoke("yolo_mode_enable", {
            "project_path": project_path,
            "safety_threshold": safety_threshold
        })
    
    def spawn_agent(self, agent_type: str, task: str, 
                    context: dict = None) -> dict:
        """
        Spawn a specialized sub-agent
        
        Args:
            agent_type: Type of agent (e.g., "paystack_security")
            task: Task description
            context: Optional context
        
        Returns:
            {
                "agent_id": str,
                "type": str,
                "status": str
            }
        """
        return self._invoke("spawn_agent", {
            "agent_type": agent_type,
            "task": task,
            "context": context or {}
        })
    
    def create_checkpoint(self, build_id: str, stage: str, 
                          data: dict = None) -> dict:
        """
        Create a 3-tier checkpoint
        
        Returns:
            {
                "checkpoint_id": str,
                "tier_1_redis": "✓",
                "tier_2_postgres": "✓",
                "tier_3_git": "✓"
            }
        """
        return self._invoke("create_checkpoint", {
            "build_id": build_id,
            "stage": stage,
            "data": data or {}
        })
    
    def run_security_audit(self, project_path: str, 
                           auto_fix: bool = False) -> dict:
        """
        Run Paystack security audit
        
        Returns:
            {
                "overall_score": int,
                "findings": int,
                "critical": int,
                "high": int
            }
        """
        return self._invoke("run_security_audit", {
            "project_path": project_path,
            "auto_fix": auto_fix
        })
    
    def optimize_performance(self, route_code: str, 
                             use_quantum: bool = False) -> dict:
        """
        Optimize API route performance
        
        Returns:
            {
                "optimization_score": int,
                "latency_improvement": str,
                "bottlenecks_found": int
            }
        """
        return self._invoke("optimize_performance", {
            "route_code": route_code,
            "use_quantum": use_quantum
        })
    
    def verify_rewards(self, reward_data: dict, 
                       check_fraud: bool = True) -> dict:
        """
        Verify iHhashi reward calculations
        
        Returns:
            {
                "status": str,
                "compliance": str,
                "coin_balance": str
            }
        """
        return self._invoke("verify_rewards", {
            "reward_data": reward_data,
            "check_fraud": check_fraud
        })
    
    def get_build_status(self) -> dict:
        """
        Get current build status
        
        Returns:
            {
                "status": str,
                "active_agents": int,
                "completed_tasks": int,
                "checkpoints": int
            }
        """
        return self._invoke("get_build_status", {})
    
    def rollback(self, checkpoint_id: str) -> dict:
        """
        Rollback to checkpoint
        
        Returns:
            {
                "rollback_to": str,
                "status": str,
                "restored_files": int
            }
        """
        return self._invoke("rollback", {
            "checkpoint_id": checkpoint_id
        })
    
    def deploy_agents_parallel(self, project_path: str,
                                ai_sources: List[str] = None,
                                max_parallel: int = 64) -> dict:
        """
        Deploy ALL agents in parallel (Multi-AI mode)
        
        Args:
            project_path: Path to project
            ai_sources: List of AIs to use ["kimi", "chatgpt", "grok"]
            max_parallel: Max parallel agents
        
        Returns:
            {
                "deployment": "PARALLEL_SWARM",
                "agents_deployed": int,
                "estimated_completion": str
            }
        """
        return self._invoke("deploy_agents_parallel", {
            "project_path": project_path,
            "ai_sources": ai_sources or ["kimi", "chatgpt", "grok"],
            "max_parallel": max_parallel
        })
    
    def get_ai_orchestra_status(self) -> dict:
        """
        Get status of all connected AIs
        
        Returns:
            {
                "connected_ais": list,
                "orchestra": {
                    "kimi": {...},
                    "chatgpt": {...},
                    "grok": {...}
                }
            }
        """
        return self._invoke("get_ai_orchestra_status", {})
    
    # === UTILITY METHODS ===
    
    def get_tools(self) -> list:
        """List all available MCP tools"""
        response = self.session.get(
            f"{self.config.server_url}/mcp/tools",
            timeout=self.config.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def health_check(self) -> dict:
        """Check server health"""
        response = self.session.get(
            f"{self.config.server_url}/health",
            timeout=self.config.timeout
        )
        response.raise_for_status()
        return response.json()


# === EXAMPLE USAGE ===

def example_chatgpt_usage():
    """Example: How ChatGPT would use this"""
    print("=" * 60)
    print("ChatGPT Example Usage")
    print("=" * 60)
    
    # Connect
    mcp = MasterBuilder7MCP(
        server_url="http://localhost:8000",
        ai_name="chatgpt"
    )
    
    print("\n1. Connect to MCP server...")
    result = mcp.connect({
        "provider": "OpenAI",
        "model": "GPT-4",
        "specialty": "architecture"
    })
    print(f"   Status: {result.get('status')}")
    
    print("\n2. Analyze project...")
    result = mcp.analyze_project("/home/user/my-app")
    print(f"   Stack: {result.get('stack_detected')}")
    
    print("\n3. Enable YOLO mode...")
    result = mcp.yolo_mode("/home/user/my-app", safety_threshold=0.6)
    print(f"   Status: {result.get('yolo_mode')}")
    print(f"   ZO1: {result.get('zo1')}")
    print(f"   ZO2: {result.get('zo2')}")


def example_grok_usage():
    """Example: How Grok would use this"""
    print("\n" + "=" * 60)
    print("Grok Example Usage")
    print("=" * 60)
    
    mcp = MasterBuilder7MCP(
        server_url="http://localhost:8000",
        ai_name="grok"
    )
    
    print("\n1. Connect...")
    mcp.connect({"provider": "xAI", "specialty": "real-time"})
    
    print("\n2. Deploy parallel agents...")
    result = mcp.deploy_agents_parallel(
        "/home/user/my-app",
        ai_sources=["grok", "kimi", "chatgpt"],
        max_parallel=64
    )
    print(f"   Agents deployed: {result.get('agents_deployed')}")
    print(f"   Mode: {result.get('deployment')}")
    print(f"   ETA: {result.get('estimated_completion')}")


def example_kimi_usage():
    """Example: How Kimi would use this"""
    print("\n" + "=" * 60)
    print("Kimi Example Usage")
    print("=" * 60)
    
    mcp = MasterBuilder7MCP(
        server_url="http://localhost:8000",
        ai_name="kimi"
    )
    
    print("\n1. Connect...")
    mcp.connect({"provider": "Moonshot", "specialty": "code"})
    
    print("\n2. Execute full build...")
    result = mcp.execute_build(
        "/home/user/my-app",
        yolo_mode=True,
        max_agents=64
    )
    print(f"   Build ID: {result.get('build_id')}")
    print(f"   Status: {result.get('status')}")
    print(f"   Message: {result.get('message')}")


if __name__ == "__main__":
    # Run examples
    example_chatgpt_usage()
    example_grok_usage()
    example_kimi_usage()
    
    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)
