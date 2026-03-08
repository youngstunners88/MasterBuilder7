#!/usr/bin/env python3
"""
MCP HTTP Server: /deploy endpoint with approval gate
Sovereign deployment engine for MasterBuilder7
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import uvicorn

from deploy.store_deploy import MasterDeployer, DeploymentConfig

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()
API_KEYS = os.getenv('MCP_API_KEYS', '').split(',')

# Approval queue
approval_queue = {}
deployment_history = []


class DeployRequest(BaseModel):
    repo: str
    platform: str  # "android", "ios", "all"
    track: str = "internal"  # internal, alpha, beta, production
    version_code: int
    version_name: str
    require_approval: bool = True  # Kill switch: must approve for production


class ApprovalRequest(BaseModel):
    deployment_id: str
    approved: bool
    reason: str = ""


app = FastAPI(title="MasterBuilder7 MCP Server")


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API key"""
    if credentials.credentials not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials


@app.get("/health")
async def health_check():
    """Health check for load balancers"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "vFINAL"
    }


@app.get("/status")
async def get_status():
    """Full system status"""
    return {
        "pending_approvals": len(approval_queue),
        "total_deployments": len(deployment_history),
        "recent_deployments": deployment_history[-5:],
        "configured": {
            "google_play": bool(os.getenv('GOOGLE_PLAY_SERVICE_ACCOUNT')),
            "apple": all([
                os.getenv('APPLE_ISSUER_ID'),
                os.getenv('APPLE_KEY_ID'),
                os.getenv('APPLE_PRIVATE_KEY')
            ])
        }
    }


@app.post("/deploy")
async def deploy(
    request: DeployRequest,
    background_tasks: BackgroundTasks,
    token: str = Depends(verify_token)
):
    """
    Deploy to app stores
    
    For production track: requires manual approval (kill switch)
    """
    deployment_id = f"deploy-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{request.platform}"
    
    # Kill switch: production requires approval
    if request.track == "production" and request.require_approval:
        approval_queue[deployment_id] = {
            "request": request.dict(),
            "status": "pending_approval",
            "requested_at": datetime.now().isoformat(),
            "token": token
        }
        
        logger.warning(f"Production deployment {deployment_id} queued for approval")
        
        return {
            "deployment_id": deployment_id,
            "status": "pending_approval",
            "message": "Production deployment requires approval. Use /approve endpoint.",
            "approval_endpoint": f"/approve/{deployment_id}"
        }
    
    # Auto-approve non-production
    background_tasks.add_task(execute_deployment, deployment_id, request)
    
    return {
        "deployment_id": deployment_id,
        "status": "in_progress",
        "message": f"Deploying to {request.platform} on {request.track} track",
        "check_status": f"/status/{deployment_id}"
    }


@app.post("/approve/{deployment_id}")
async def approve_deployment(
    deployment_id: str,
    approval: ApprovalRequest,
    token: str = Depends(verify_token)
):
    """Approve a pending production deployment"""
    if deployment_id not in approval_queue:
        raise HTTPException(status_code=404, detail="Deployment not found or already processed")
    
    queued = approval_queue[deployment_id]
    
    if not approval.approved:
        approval_queue[deployment_id]["status"] = "rejected"
        approval_queue[deployment_id]["reason"] = approval.reason
        
        logger.warning(f"Deployment {deployment_id} rejected: {approval.reason}")
        return {"status": "rejected", "reason": approval.reason}
    
    # Execute approved deployment
    request = DeployRequest(**queued["request"])
    asyncio.create_task(execute_deployment(deployment_id, request))
    
    approval_queue[deployment_id]["status"] = "approved"
    approval_queue[deployment_id]["approved_at"] = datetime.now().isoformat()
    approval_queue[deployment_id]["approved_by"] = token[:8]  # Partial key for audit
    
    logger.info(f"Deployment {deployment_id} approved and executing")
    
    return {
        "status": "approved",
        "deployment_id": deployment_id,
        "message": "Deployment approved and in progress"
    }


async def execute_deployment(deployment_id: str, request: DeployRequest):
    """Execute the actual deployment"""
    logger.info(f"Starting deployment {deployment_id}")
    
    try:
        deployer = MasterDeployer()
        
        # Build first (if needed)
        if request.platform in ["android", "all"]:
            config = DeploymentConfig(
                repo_path=f"/home/workspace/{request.repo}",
                package_name=f"com.{request.repo.lower()}.app",
                version_code=request.version_code,
                version_name=request.version_name,
                track=request.track
            )
            
            result = deployer.deploy_android(config)
            
            deployment_history.append({
                "deployment_id": deployment_id,
                "platform": "android",
                "timestamp": datetime.now().isoformat(),
                "result": result
            })
        
        logger.info(f"Deployment {deployment_id} completed")
        
    except Exception as e:
        logger.error(f"Deployment {deployment_id} failed: {e}")
        deployment_history.append({
            "deployment_id": deployment_id,
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })


@app.get("/status/{deployment_id}")
async def get_deployment_status(deployment_id: str):
    """Get deployment status"""
    # Check approval queue
    if deployment_id in approval_queue:
        return approval_queue[deployment_id]
    
    # Check history
    for dep in deployment_history:
        if dep.get("deployment_id") == deployment_id:
            return dep
    
    raise HTTPException(status_code=404, detail="Deployment not found")


@app.get("/deploy")
async def list_deployments():
    """List all deployments"""
    return {
        "pending": list(approval_queue.values()),
        "history": deployment_history[-20:]
    }


if __name__ == "__main__":
    # Load API keys from env
    if not API_KEYS or API_KEYS == ['']:
        print("WARNING: No MCP_API_KEYS set. Server will reject all requests.")
        print("Set MCP_API_KEYS=key1,key2,key3")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv('MCP_PORT', '8000')),
        log_level="info"
    )
