#!/usr/bin/env python3
"""
Agent API - FastAPI service for AI agents
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid

app = FastAPI(title="MasterBuilder7 Agent API")

class DeployRequest(BaseModel):
    agent_id: str
    repo: str
    targets: list
    budget_limit: float = 50.0

@app.post("/agent/deploy")
async def agent_deploy(request: DeployRequest):
    # Import here to avoid circular dependency
    from orchestrator import MasterOrchestrator
    from budget_guardrail import BudgetGuardrail
    
    budget = BudgetGuardrail(
        daily_limit=request.budget_limit,
        monthly_limit=request.budget_limit * 30
    )
    
    orchestrator = MasterOrchestrator(
        daily_budget=request.budget_limit,
        monthly_budget=request.budget_limit * 30
    )
    
    result = orchestrator.deploy(
        repo=request.repo,
        targets=request.targets
    )
    
    return {
        "status": result["status"],
        "session_id": str(uuid.uuid4()),
        "deployments": result.get("deployments", {}),
        "cost": result.get("total_cost", 0),
        "autonomous": True
    }

@app.get("/agent/discover")
async def discover_tools(tool: str = None):
    tools = {
        "render": {
            "name": "render-deployer",
            "version": "1.0.0",
            "autonomous_capable": True,
            "required_setup": ["RENDER_API_KEY"]
        },
        "icp": {
            "name": "icp-deployer", 
            "version": "1.0.0",
            "autonomous_capable": True,
            "required_setup": ["DFX_IDENTITY"]
        }
    }
    if tool:
        return tools.get(tool, {"error": "Tool not found"})
    return tools

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
