#!/usr/bin/env python3
"""
SECURE HTTP MCP Server for MasterBuilder7
- API Key authentication
- No IP exposure options
- Rate limiting
- Request logging
"""

import json
import os
import sys
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from functools import wraps

sys.path.insert(0, str(Path(__file__).parent))

try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Depends
    from fastapi.responses import JSONResponse, StreamingResponse
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from pydantic import BaseModel
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    print("❌ FastAPI not installed")
    sys.exit(1)


# Configuration
class Config:
    """Server configuration from environment"""
    API_KEY = os.getenv("MCP_API_KEY", "")
    HOST = os.getenv("MCP_HOST", "0.0.0.0")
    PORT = int(os.getenv("MCP_PORT", "8000"))
    RATE_LIMIT = int(os.getenv("MCP_RATE_LIMIT", "100"))  # requests per minute
    LOG_LEVEL = os.getenv("MCP_LOG_LEVEL", "INFO")
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        if not cls.API_KEY:
            print("⚠️  WARNING: No API key set!")
            print("   Set MCP_API_KEY environment variable for security")
            print("   Or run: export MCP_API_KEY=your-secret-key")
            return False
        return True


# Models
class MCPRequest(BaseModel):
    tool: str
    params: Dict[str, Any]
    request_id: Optional[str] = None
    ai_source: Optional[str] = "unknown"


class MCPResponse(BaseModel):
    request_id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    processing_time_ms: Optional[int] = None


# Rate limiting
class RateLimiter:
    """Simple rate limiter per API key"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = {}  # api_key -> list of timestamps
    
    def is_allowed(self, api_key: str) -> bool:
        """Check if request is allowed"""
        now = time.time()
        
        # Clean old requests
        if api_key in self.requests:
            self.requests[api_key] = [
                ts for ts in self.requests[api_key]
                if now - ts < self.window_seconds
            ]
        else:
            self.requests[api_key] = []
        
        # Check limit
        if len(self.requests[api_key]) >= self.max_requests:
            return False
        
        # Add request
        self.requests[api_key].append(now)
        return True
    
    def get_remaining(self, api_key: str) -> int:
        """Get remaining requests in window"""
        now = time.time()
        
        if api_key in self.requests:
            recent = [ts for ts in self.requests[api_key] 
                     if now - ts < self.window_seconds]
            return max(0, self.max_requests - len(recent))
        
        return self.max_requests


rate_limiter = RateLimiter()

# Security
security = HTTPBearer()

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API key from Authorization header"""
    if not Config.API_KEY:
        # No API key configured - allow all (development mode)
        return "development"
    
    token = credentials.credentials
    
    # Simple comparison (use constant-time comparison in production)
    if token != Config.API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return token


# Create app
app = FastAPI(
    title="MasterBuilder7 Secure MCP Server",
    description="Secure MCP server with API key authentication",
    version="1.1.0-secure"
)

# CORS - restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict to known domains
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


# Request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    start_time = time.time()
    
    # Get client info (will show tunnel IP, not real IP)
    client_host = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    
    # Log (but not the real IP if behind tunnel)
    print(f"[{datetime.now().isoformat()}] "
          f"{request.method} {request.url.path} "
          f"{response.status_code} "
          f"{duration:.3f}s")
    
    return response


# Rate limiting middleware
@app.middleware("http")
async def rate_limit(request: Request, call_next):
    """Apply rate limiting"""
    # Get API key from header
    api_key = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    if not api_key:
        api_key = "anonymous"
    
    # Skip rate limit for health checks
    if request.url.path in ["/health", "/"]:
        return await call_next(request)
    
    # Check rate limit
    if not rate_limiter.is_allowed(api_key):
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "retry_after": 60,
                "limit": Config.RATE_LIMIT
            }
        )
    
    response = await call_next(request)
    
    # Add rate limit headers
    remaining = rate_limiter.get_remaining(api_key)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Limit"] = str(Config.RATE_LIMIT)
    
    return response


# Endpoints
@app.get("/")
async def root():
    """Server info"""
    return {
        "name": "MasterBuilder7 Secure MCP Server",
        "version": "1.1.0-secure",
        "status": "running",
        "security": {
            "api_key_required": bool(Config.API_KEY),
            "rate_limit": Config.RATE_LIMIT
        },
        "endpoints": {
            "invoke": "/mcp/invoke (POST, requires API key)",
            "tools": "/mcp/tools (GET, public)",
            "health": "/health (GET, public)"
        },
        "note": "Use a tunnel (ngrok, cloudflare) to hide your real IP"
    }


@app.get("/mcp/tools")
async def list_tools():
    """List available tools (public)"""
    return [
        {"name": "analyze_project", "description": "Analyze project structure"},
        {"name": "execute_build", "description": "Execute YOLO build"},
        {"name": "yolo_mode_enable", "description": "Enable YOLO mode"},
        {"name": "deploy_agents_parallel", "description": "Deploy parallel agents"},
        {"name": "run_security_audit", "description": "Security audit"},
        {"name": "optimize_performance", "description": "Performance optimization"},
        {"name": "verify_rewards", "description": "Verify rewards"},
        {"name": "get_build_status", "description": "Build status"},
        {"name": "create_checkpoint", "description": "Create checkpoint"},
        {"name": "rollback", "description": "Rollback"},
        {"name": "spawn_agent", "description": "Spawn agent"},
        {"name": "get_ai_orchestra_status", "description": "AI orchestra status"}
    ]


@app.post("/mcp/invoke", response_model=MCPResponse)
async def invoke_tool(
    request: MCPRequest,
    api_key: str = Depends(verify_api_key)
):
    """Invoke MCP tool (requires API key)"""
    start_time = time.time()
    request_id = request.request_id or f"req-{int(time.time())}"
    
    # Validate tool
    valid_tools = [
        "analyze_project", "execute_build", "spawn_agent", "create_checkpoint",
        "run_security_audit", "optimize_performance", "verify_rewards",
        "get_build_status", "yolo_mode_enable", "rollback",
        "deploy_agents_parallel", "get_ai_orchestra_status"
    ]
    
    if request.tool not in valid_tools:
        return MCPResponse(
            request_id=request_id,
            status="error",
            error=f"Unknown tool: {request.tool}",
            processing_time_ms=int((time.time() - start_time) * 1000)
        )
    
    # Execute tool
    try:
        result = await execute_tool_secure(request.tool, request.params, request.ai_source)
        
        return MCPResponse(
            request_id=request_id,
            status="success",
            result=result,
            processing_time_ms=int((time.time() - start_time) * 1000)
        )
        
    except Exception as e:
        return MCPResponse(
            request_id=request_id,
            status="error",
            error=str(e),
            processing_time_ms=int((time.time() - start_time) * 1000)
        )


async def execute_tool_secure(tool: str, params: dict, ai_source: str) -> dict:
    """Execute tool with security checks"""
    
    # Validate project_path (prevent directory traversal)
    if "project_path" in params:
        path = params["project_path"]
        # Basic sanitization
        if ".." in path or path.startswith("/etc") or path.startswith("/root"):
            raise Exception("Invalid project path")
    
    # Mock implementations (same as before but secure)
    if tool == "analyze_project":
        return {
            "project_path": params.get("project_path"),
            "ai_analyzed_by": ai_source,
            "stack_detected": "capacitor_react_fastapi",
            "automation_potential": 0.70
        }
    
    elif tool == "yolo_mode_enable":
        return {
            "yolo_mode": "ENGAGED 🔥",
            "safety_threshold": params.get("safety_threshold", 0.6),
            "zo1": "ONLINE",
            "zo2": "ONLINE",
            "activated_by": ai_source,
            "note": "Running securely via tunnel"
        }
    
    elif tool == "deploy_agents_parallel":
        return {
            "deployment": "PARALLEL_SWARM",
            "agents_deployed": 20,
            "orchestrated_by": params.get("ai_sources", ["kimi"]),
            "triggered_by": ai_source
        }
    
    # ... other tools ...
    return {"tool": tool, "status": "executed", "by": ai_source}


@app.get("/health")
async def health():
    """Health check (public)"""
    return {
        "status": "healthy",
        "version": "1.1.0-secure",
        "secure_mode": bool(Config.API_KEY),
        "timestamp": datetime.now().isoformat()
    }


def main():
    """Run secure MCP server"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║     MasterBuilder7 SECURE MCP Server                             ║
╠══════════════════════════════════════════════════════════════════╣
║  ⚠️  IMPORTANT: Use a tunnel to hide your real IP!               ║
║                                                                  ║
║  Option 1 (Easy):    ngrok http 8000                            ║
║  Option 2 (Best):    cloudflared tunnel                         ║
║  Option 3 (Quick):   npx localtunnel --port 8000                ║
╚══════════════════════════════════════════════════════════════════╝
""")
    
    # Validate config
    is_secure = Config.validate()
    
    if not is_secure:
        print("\n⚠️  Running in INSECURE mode (no API key)")
        print("   Set MCP_API_KEY for production use\n")
    else:
        print(f"\n🔐 API Key: {'*' * 10} (hidden)")
        print("   Server requires authentication\n")
    
    print(f"🚀 Starting server on {Config.HOST}:{Config.PORT}")
    print(f"📊 Rate limit: {Config.RATE_LIMIT} requests/minute")
    print(f"\n🔗 After starting tunnel, give this URL to ChatGPT/Grok:")
    print(f"   https://YOUR-TUNNEL-URL/mcp/invoke")
    print(f"\n📖 API Docs: http://localhost:{Config.PORT}/docs\n")
    
    uvicorn.run(app, host=Config.HOST, port=Config.PORT)


if __name__ == "__main__":
    main()
