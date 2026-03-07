# MCP Connection Guide for ChatGPT & Grok

## 🔌 MCP Server Endpoint

**Your MCP Server is running at:**

```
http://YOUR_IP:8000
```

**Replace `YOUR_IP` with your actual IP address or domain.**

### To find your IP:
```bash
curl ifconfig.me
# or
hostname -I
```

---

## 🤖 For ChatGPT (OpenAI GPTs)

### Method 1: Custom GPT Actions

1. Go to [chat.openai.com/gpts](https://chat.openai.com/gpts)
2. Create a new GPT
3. Go to "Configure" → "Add Actions"
4. Enter this schema:

```yaml
openapi: 3.1.0
info:
  title: MasterBuilder7 MCP
  version: 1.1.0
  description: Multi-AI orchestration for software builds
servers:
  - url: http://YOUR_IP:8000
    description: MasterBuilder7 MCP Server

paths:
  /mcp/invoke:
    post:
      operationId: invokeTool
      summary: Invoke an MCP tool
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                tool:
                  type: string
                  enum: [analyze_project, execute_build, spawn_agent, create_checkpoint, run_security_audit, optimize_performance, verify_rewards, get_build_status, yolo_mode_enable, rollback, deploy_agents_parallel, get_ai_orchestra_status]
                params:
                  type: object
                ai_source:
                  type: string
                  default: chatgpt
      responses:
        200:
          description: Tool execution result
          content:
            application/json:
              schema:
                type: object
                properties:
                  request_id:
                    type: string
                  status:
                    type: string
                  result:
                    type: object
                  error:
                    type: string

  /mcp/tools:
    get:
      operationId: listTools
      summary: List available tools
      responses:
        200:
          description: List of tools

  /mcp/status:
    get:
      operationId: getStatus
      summary: Get server status
      responses:
        200:
          description: Server status
```

5. **Privacy Policy:** `http://YOUR_IP:8000/privacy`
6. Save and test!

### Method 2: ChatGPT API with MCP

```python
import openai
import requests

# Your MCP server endpoint
MCP_SERVER = "http://YOUR_IP:8000/mcp/invoke"

def chatgpt_with_mcp(user_message):
    # First, let ChatGPT decide what to do
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an AI orchestrator. Use MCP tools when needed."},
            {"role": "user", "content": user_message}
        ],
        functions=[
            {
                "name": "mcp_invoke",
                "description": "Invoke MasterBuilder7 MCP tool",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tool": {"type": "string"},
                        "params": {"type": "object"}
                    }
                }
            }
        ]
    )
    
    # If ChatGPT wants to use MCP
    if response.choices[0].finish_reason == "function_call":
        tool_call = response.choices[0].message.function_call
        
        # Call MCP server
        mcp_response = requests.post(MCP_SERVER, json={
            "tool": tool_call.arguments["tool"],
            "params": tool_call.arguments["params"],
            "ai_source": "chatgpt"
        })
        
        return mcp_response.json()
    
    return response.choices[0].message.content
```

---

## 🐦 For Grok (xAI)

### Method 1: Direct API Calls

```python
import requests

# Your MCP server
MCP_ENDPOINT = "http://YOUR_IP:8000"

class GrokMCPClient:
    def __init__(self):
        self.endpoint = MCP_ENDPOINT
        self.ai_name = "grok"
        
    def connect(self):
        """Register Grok with MCP server"""
        response = requests.post(f"{self.endpoint}/mcp/connect", json={
            "ai_name": self.ai_name,
            "info": {
                "provider": "xAI",
                "strengths": ["real-time", "trends", "research"]
            }
        })
        return response.json()
    
    def invoke(self, tool: str, params: dict):
        """Invoke an MCP tool"""
        response = requests.post(f"{self.endpoint}/mcp/invoke", json={
            "tool": tool,
            "params": params,
            "ai_source": self.ai_name,
            "request_id": f"grok-{int(time.time())}"
        })
        return response.json()
    
    def get_tools(self):
        """List available tools"""
        response = requests.get(f"{self.endpoint}/mcp/tools")
        return response.json()

# Usage
client = GrokMCPClient()
client.connect()

# Invoke tools
result = client.invoke("analyze_project", {
    "project_path": "/home/user/my-app"
})
print(result)
```

### Method 2: Grok with Real-time Data + MCP

```python
# Grok's specialty: Real-time data + MCP orchestration

def grok_build_with_trends(project_path):
    """
    Grok researches current trends, then orchestrates build
    """
    # Step 1: Grok researches (its specialty)
    trends = grok.research(f"Latest trends for {project_path}")
    
    # Step 2: Grok invokes MCP to start build
    mcp_response = requests.post("http://YOUR_IP:8000/mcp/invoke", json={
        "tool": "deploy_agents_parallel",
        "params": {
            "project_path": project_path,
            "ai_sources": ["grok", "kimi", "chatgpt"],
            "max_parallel": 64
        },
        "ai_source": "grok"
    })
    
    return {
        "trends": trends,
        "build": mcp_response.json()
    }
```

---

## 🔗 Universal MCP Client (Works with ALL AIs)

```python
import requests
import json
from typing import Dict, Any

class MasterBuilder7MCPClient:
    """
    Universal MCP client for ChatGPT, Grok, Kimi, Claude
    """
    
    def __init__(self, server_url: str, ai_name: str):
        self.server_url = server_url.rstrip('/')
        self.ai_name = ai_name
        self.connected = False
        
    def connect(self, ai_info: dict = None):
        """Connect to MCP server"""
        response = requests.post(
            f"{self.server_url}/mcp/connect",
            json={
                "ai_name": self.ai_name,
                "info": ai_info or {"name": self.ai_name}
            }
        )
        self.connected = response.status_code == 200
        return response.json()
    
    def invoke(self, tool: str, params: Dict[str, Any]) -> Dict:
        """Invoke an MCP tool"""
        if not self.connected:
            raise Exception("Not connected. Call connect() first.")
            
        response = requests.post(
            f"{self.server_url}/mcp/invoke",
            json={
                "tool": tool,
                "params": params,
                "ai_source": self.ai_name
            }
        )
        return response.json()
    
    def analyze_project(self, project_path: str):
        return self.invoke("analyze_project", {"project_path": project_path})
    
    def execute_build(self, project_path: str, yolo_mode: bool = True):
        return self.invoke("execute_build", {
            "project_path": project_path,
            "yolo_mode": yolo_mode
        })
    
    def yolo_mode(self, project_path: str, safety: float = 0.6):
        return self.invoke("yolo_mode_enable", {
            "project_path": project_path,
            "safety_threshold": safety
        })
    
    def deploy_parallel(self, project_path: str, ais: list = None):
        return self.invoke("deploy_agents_parallel", {
            "project_path": project_path,
            "ai_sources": ais or ["kimi", "chatgpt", "grok"],
            "max_parallel": 64
        })

# Usage Examples:

# ChatGPT connection
chatgpt = MasterBuilder7MCPClient("http://YOUR_IP:8000", "chatgpt")
chatgpt.connect({"provider": "OpenAI", "model": "GPT-4"})
chatgpt.yolo_mode("/path/to/project")

# Grok connection  
grok = MasterBuilder7MCPClient("http://YOUR_IP:8000", "grok")
grok.connect({"provider": "xAI", "specialty": "real-time"})
grok.deploy_parallel("/path/to/project", ["grok", "kimi"])

# Kimi connection
kimi = MasterBuilder7MCPClient("http://YOUR_IP:8000", "kimi")
kimi.connect({"provider": "Moonshot", "specialty": "code"})
kimi.execute_build("/path/to/project", yolo_mode=True)
```

---

## 📡 Available MCP Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Server info |
| `/mcp/tools` | GET | List all tools |
| `/mcp/invoke` | POST | Invoke a tool |
| `/mcp/connect` | POST | Register AI connection |
| `/mcp/status` | GET | Server status |
| `/mcp/sse` | GET | Real-time updates (SSE) |
| `/health` | GET | Health check |
| `/docs` | GET | API documentation |

---

## 🔧 Quick Start

### 1. Start MCP Server

```bash
cd /home/teacherchris37/MasterBuilder7
source .venv/bin/activate

# Start HTTP MCP server
python3 mcp_http_server.py

# Or with custom host/port
MCP_HOST=0.0.0.0 MCP_PORT=8000 python3 mcp_http_server.py
```

### 2. Test Connection

```bash
# Test health
curl http://YOUR_IP:8000/health

# List tools
curl http://YOUR_IP:8000/mcp/tools

# Connect ChatGPT
curl -X POST http://YOUR_IP:8000/mcp/connect \
  -H "Content-Type: application/json" \
  -d '{"ai_name": "chatgpt", "info": {"provider": "OpenAI"}}'

# Invoke tool
curl -X POST http://YOUR_IP:8000/mcp/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "yolo_mode_enable",
    "params": {"project_path": "/tmp/test", "safety_threshold": 0.6},
    "ai_source": "chatgpt"
  }'
```

---

## 🔐 Security Note

For production, add authentication:

```python
# Add to mcp_http_server.py headers check
API_KEY = os.getenv("MCP_API_KEY")

@app.middleware("http")
async def auth_middleware(request, call_next):
    if request.headers.get("X-API-Key") != API_KEY:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    return await call_next(request)
```

Then provide API key to ChatGPT/Grok:
```bash
curl -H "X-API-Key: your-secret-key" http://YOUR_IP:8000/mcp/invoke ...
```

---

## 🎯 Summary

**Give ChatGPT & Grok this endpoint:**
```
http://YOUR_IP:8000/mcp/invoke
```

**They can then:**
- ✅ Invoke any MCP tool
- ✅ Start YOLO builds
- ✅ Deploy parallel agents
- ✅ Check build status
- ✅ Coordinate with other AIs

**All AIs work together through the MCP server!** 🎭
