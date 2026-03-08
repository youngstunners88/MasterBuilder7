#!/usr/bin/env python3
"""
Agent SDK - Client for agents to discover tools and execute deployments
"""

import requests
from typing import Dict, Optional


class AgentSDK:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    def discover(self, tool_name: str) -> Dict:
        """Discover tool metadata"""
        resp = requests.get(
            f"{self.base_url}/agent/discover",
            headers=self.headers,
            params={"tool": tool_name}
        )
        return resp.json()
    
    def validate(self, tool_name: str) -> Dict:
        """Check if tool is ready to use"""
        resp = requests.post(
            f"{self.base_url}/agent/validate",
            headers=self.headers,
            json={"tool": tool_name}
        )
        return resp.json()
    
    def estimate(self, tool_name: str, params: Dict) -> Dict:
        """Get cost/time estimate"""
        resp = requests.post(
            f"{self.base_url}/agent/estimate",
            headers=self.headers,
            json={"tool": tool_name, "params": params}
        )
        return resp.json()
    
    def deploy(self, targets: list, repo: str, budget_limit: float) -> Dict:
        """Execute deployment via orchestrator"""
        resp = requests.post(
            f"{self.base_url}/agent/deploy",
            headers=self.headers,
            json={
                "targets": targets,
                "repo": repo,
                "budget_limit": budget_limit
            }
        )
        return resp.json()
