#!/usr/bin/env python3
"""
MCP HTTP Server: /deploy endpoint with approval gate
MASTER-RECOVERY-vFINAL: Sovereign deployment engine
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
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()
API_KEYS = [k.strip() for k in os.getenv("MCP_API_KEYS", "").split(",") if k.strip()]
if not API_KEYS:
    API_KEYS = ["dev-key-change-in-production"]  # Default for development
    logger.warning("Using default API key - CHANGE IN PRODUCTION")

# Approval queue for production deployments
approval_queue: Dict[str, dict] = {}
deployment_history: list = []

# Pydantic models
class DeployRequest(BaseModel):
    repo: str
    platform: str  # "android", "ios", "icp", "web"
    track: str = "internal"  # internal, alpha, beta, production
    version_code: int = 1
    version_name: str = "1.0.0"
    require_approval: bool = True  # Kill switch: must approve for production
    aab_path: Optional[str] = None  # For Android
    ipa_path: Optional[str] = None  # For iOS
    canister_id: Optional[str] = None  # For ICP

class ApprovalRequest(BaseModel):
    deployment_id: str
    approved: bool
    reason: str = ""

class ApprovalResponse(BaseModel):
    deployment_id: str
    status: str
    message: str

# FastAPI app
app = FastAPI(
    title="MasterBuilder7 MCP Server",
    description="Sovereign deployment engine for app stores",
    version="vFINAL"
)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API key"""
    if credentials.credentials not in API_KEYS:
        logger.warning(f"Invalid API key attempt: {credentials.credentials[:10]}...")
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials

@app.get("/health")
async def health_check():
    """Health check for load balancers"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "vFINAL",
        "service": "MasterBuilder7-MCP"
    }

@app.get("/status")
async def get_status():
    """Full system status"""
    # Import here to check configuration
    deployer_available = False
    try:
        from deploy.store_deploy import MasterDeployer
        deployer = MasterDeployer()
        deployer_available = deployer.gp_deployer is not None or deployer.ios_deployer is not None
    except Exception as e:
        logger.debug(f"Deployer check: {e}")
    
    return {
        "pending_approvals": len(approval_queue),
        "total_deployments": len(deployment_history),
        "recent_deployments": deployment_history[-5:] if deployment_history else [],
        "deployer_available": deployer_available,
        "configured": {
            "google_play": bool(os.getenv("GOOGLE_PLAY_SERVICE_ACCOUNT")),
            "apple": all([
                os.getenv("APPLE_ISSUER_ID"),
                os.getenv("APPLE_KEY_ID")
            ]),
            "icp": bool(os.getenv("DFX_IDENTITY")),
            "render": bool(os.getenv("RENDER_API_KEY"))
        },
        "timestamp": datetime.now().isoformat()
    }

@app.post("/deploy")
async def deploy(
    request: DeployRequest,
    background_tasks: BackgroundTasks,
    token: str = Depends(verify_token)
):
    """
    Deploy to app stores with approval gate for production.
    
    - Internal/Alpha/Beta: Auto-approved
    - Production: Requires manual approval (kill switch)
    """
    deployment_id = f"deploy-{datetime.now().strftime(\'%Y%m%d-%H%M%S\')}-{request.platform}"
    
    # Kill switch: production requires approval
    if request.track == "production" and request.require_approval:
        approval_queue[deployment_id] = {
            "request": request.dict(),
            "status": "pending_approval",
            "requested_at": datetime.now().isoformat(),
            "token": token,
            "deployment_id": deployment_id
        }
        
        logger.warning(f"Production deployment {deployment_id} queued for approval")
        
        return {
            "deployment_id": deployment_id,
            "status": "pending_approval",
            "message": "Production deployment requires approval. Use /approve endpoint.",
            "approval_endpoint": f"/approve/{deployment_id}",
            "approve_command": f"curl -X POST http://localhost:8000/approve/{deployment_id} -H \"Authorization: Bearer {token}\" -d \"{{\"approved\": true}}\""
        }
    
    # Non-production: execute immediately
    logger.info(f"Auto-approving {request.track} deployment {deployment_id}")
    
    try:
        result = await execute_deployment(request, deployment_id)
        deployment_history.append({
            "deployment_id": deployment_id,
            "platform": request.platform,
            "track": request.track,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "deployment_id": deployment_id,
            "status": "completed" if result.get("success") else "failed",
            "result": result
        }
    
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        return {
            "deployment_id": deployment_id,
            "status": "failed",
            "error": str(e)
        }

@app.post("/approve/{deployment_id}")
async def approve_deployment(
    deployment_id: str,
    request: ApprovalRequest,
    token: str = Depends(verify_token)
):
    """Approve or reject a pending production deployment"""
    if deployment_id not in approval_queue:
        raise HTTPException(status_code=404, detail="Deployment not found in approval queue")
    
    pending = approval_queue[deployment_id]
    
    if not request.approved:
        pending["status"] = "rejected"
        pending["rejected_at"] = datetime.now().isoformat()
        pending["reason"] = request.reason
        logger.info(f"Deployment {deployment_id} rejected: {request.reason}")
        return {"deployment_id": deployment_id, "status": "rejected", "reason": request.reason}
    
    # Execute approved deployment
    pending["status"] = "approved"
    pending["approved_at"] = datetime.now().isoformat()
    
    try:
        deploy_request = DeployRequest(**pending["request"])
        result = await execute_deployment(deploy_request, deployment_id)
        
        deployment_history.append({
            "deployment_id": deployment_id,
            "platform": deploy_request.platform,
            "track": deploy_request.track,
            "result": result,
            "timestamp": datetime.now().isoformat(),
            "approved_by": token[:10] + "..."
        })
        
        # Remove from queue
        del approval_queue[deployment_id]
        
        return {
            "deployment_id": deployment_id,
            "status": "completed" if result.get("success") else "failed",
            "result": result
        }
    
    except Exception as e:
        logger.error(f"Approved deployment failed: {e}")
        return {
            "deployment_id": deployment_id,
            "status": "failed",
            "error": str(e)
        }

@app.get("/approvals/pending")
async def list_pending_approvals(token: str = Depends(verify_token)):
    """List all pending approvals (for dashboard)"""
    return {
        "count": len(approval_queue),
        "approvals": list(approval_queue.values())
    }

async def execute_deployment(request: DeployRequest, deployment_id: str) -> Dict:
    """Execute the actual deployment"""
    from deploy.store_deploy import MasterDeployer, DeploymentConfig
    
    deployer = MasterDeployer()
    
    if request.platform == "android":
        if not request.aab_path:
            return {"success": False, "error": "AAB path required for Android"}
        
        # Extract package name from repo or use provided
        package = request.repo.replace("https://github.com/", "").replace("/", ".")
        
        config = DeploymentConfig(
            repo_path=".",
            package_name=package,
            version_code=request.version_code,
            version_name=request.version_name,
            track=request.track,
            aab_path=request.aab_path
        )
        
        return deployer.deploy_android(config)
    
    elif request.platform == "ios":
        if not request.ipa_path:
            return {"success": False, "error": "IPA path required for iOS"}
        
        return deployer.deploy_ios(request.ipa_path, request.repo)
    
    elif request.platform == "icp":
        # ICP deployment
        from icp_deployer import ICPDeployer
        icp = ICPDeployer()
        return icp.deploy_from_repo(request.repo, network="ic")
    
    elif request.platform == "web":
        # Render deployment
        from render_deployer import RenderDeployer
        render = RenderDeployer()
        return render.deploy_web(request.repo, service_name=request.repo.split("/")[-1])
    
    else:
        return {"success": False, "error": f"Unknown platform: {request.platform}"}

# Dashboard HTML
dashboard_html = """
<!DOCTYPE html>
<html>
<head>
    <title>MasterBuilder7 Dashboard</title>
    <style>
        body { font-family: system-ui; max-width: 1200px; margin: 0 auto; padding: 20px; }
        .card { border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin: 10px 0; }
        .status-ok { color: green; }
        .status-warn { color: orange; }
        .status-error { color: red; }
        .approval { background: #fff3cd; padding: 15px; border-radius: 5px; margin: 10px 0; }
        button { padding: 10px 20px; cursor: pointer; }
        .approve { background: green; color: white; }
        .reject { background: red; color: white; }
    </style>
</head>
<body>
    <h1>🚀 MasterBuilder7 Deployment Dashboard</h1>
    <div id="status" class="card">Loading...</div>
    <div id="approvals" class="card">Loading...</div>
    
    <script>
        async function loadStatus() {
            const resp = await fetch("/status", {headers: {"Authorization": "Bearer dev-key-change-in-production"}});
            const data = await resp.json();
            document.getElementById("status").innerHTML = `
                <h2>System Status</h2>
                <p>Pending Approvals: <strong>${data.pending_approvals}</strong></p>
                <p>Total Deployments: ${data.total_deployments}</p>
                <p>Google Play: ${data.configured.google_play ? "✅" : "❌"}</p>
                <p>Apple: ${data.configured.apple ? "✅" : "❌"}</p>
                <p>ICP: ${data.configured.icp ? "✅" : "❌"}</p>
            `;
        }
        
        async function loadApprovals() {
            const resp = await fetch("/approvals/pending", {headers: {"Authorization": "Bearer dev-key-change-in-production"}});
            const data = await resp.json();
            let html = "<h2>Pending Approvals</h2>";
            if (data.count === 0) {
                html += "<p>No pending approvals</p>";
            } else {
                data.approvals.forEach(a => {
                    html += `<div class="approval">
                        <p><strong>${a.deployment_id}</strong></p>
                        <p>Platform: ${a.request.platform} | Track: ${a.request.track}</p>
                        <button class="approve" onclick="approve(\'${a.deployment_id}\', true)">Approve</button>
                        <button class="reject" onclick="approve(\'${a.deployment_id}\', false)">Reject</button>
                    </div>`;
                });
            }
            document.getElementById("approvals").innerHTML = html;
        }
        
        async function approve(id, approved) {
            await fetch(`/approve/${id}`, {
                method: "POST",
                headers: {
                    "Authorization": "Bearer dev-key-change-in-production",
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({approved, reason: approved ? "Approved via dashboard" : "Rejected via dashboard"})
            });
            loadStatus();
            loadApprovals();
        }
        
        loadStatus();
        loadApprovals();
        setInterval(() => { loadStatus(); loadApprovals(); }, 5000);
    </script>
</body>
</html>
"""

@app.get("/dashboard")
async def dashboard():
    """Serve dashboard HTML"""
    return JSONResponse(content={"html": dashboard_html})

if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════════╗
║           🚀 MasterBuilder7 MCP Server - vFINAL                ║
╠════════════════════════════════════════════════════════════════╣
║  Endpoints:                                                    ║
║    GET  /health          - Health check                        ║
║    GET  /status          - Full system status                  ║
║    POST /deploy          - Deploy to stores (with approval)    ║
║    POST /approve/{id}    - Approve production deployment       ║
║    GET  /approvals/pending - List pending approvals            ║
╠════════════════════════════════════════════════════════════════╣
║  Environment:                                                  ║
║    MCP_API_KEYS          - Comma-separated API keys            ║
║    GOOGLE_PLAY_SERVICE_ACCOUNT - JSON service account          ║
║    APPLE_ISSUER_ID, APPLE_KEY_ID, APPLE_PRIVATE_KEY - Apple   ║
╚════════════════════════════════════════════════════════════════╝
    """)
    uvicorn.run(app, host="0.0.0.0", port=8000)
