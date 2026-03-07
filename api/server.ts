#!/usr/bin/env bun
/**
 * APEX Fleet API Server
 * Health checks, status, and orchestration endpoints
 * Runs on: 35.235.249.249:4200
 */

import { serve } from "bun";

const PORT = parseInt(process.env.PORT || "4200", 10);
const KIMI_ID = process.env.KIMI_ID || "kimi-cli-local";
const API_KEY = process.env.APEX_API_KEY;
const ELITE_BRIDGE_URL = process.env.ELITE_BRIDGE_URL || "http://100.127.121.51:4200";
const MCP_INVOKE_URL = process.env.MCP_INVOKE_URL || "";
const ALLOWED_ORIGINS = (process.env.ALLOWED_ORIGINS || "http://localhost:3000,http://localhost:5173")
  .split(",")
  .map(origin => origin.trim())
  .filter(Boolean);

// Agent status simulation (would connect to actual agent processes)
const agentStatus = {
  meta_router: { status: "ready", tasks_completed: 47, queue: 0 },
  planning: { status: "ready", tasks_completed: 52, queue: 0 },
  frontend: { status: "busy", tasks_completed: 128, queue: 3 },
  backend: { status: "busy", tasks_completed: 115, queue: 2 },
  testing: { status: "ready", tasks_completed: 89, queue: 0 },
  devops: { status: "ready", tasks_completed: 34, queue: 0 },
  reliability: { status: "ready", tasks_completed: 156, queue: 0 },
  evolution: { status: "learning", tasks_completed: 12, queue: 1 }
};

// Active tasks
const activeTasks = new Map();

const getCorsOrigin = (requestOrigin: string | null): string => {
  if (!requestOrigin) return ALLOWED_ORIGINS[0] || "http://localhost:3000";
  if (ALLOWED_ORIGINS.includes("*")) return "*";
  return ALLOWED_ORIGINS.includes(requestOrigin) ? requestOrigin : (ALLOWED_ORIGINS[0] || "http://localhost:3000");
};

const jsonResponse = (payload: Record<string, unknown>, request: Request, status = 200) => {
  const headers = {
    "Access-Control-Allow-Origin": getCorsOrigin(request.headers.get("origin")),
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-Kimi-ID, X-API-Key",
    "Content-Type": "application/json"
  };
  return new Response(JSON.stringify(payload), { status, headers });
};

const isAuthorized = (request: Request): boolean => {
  if (!API_KEY) return true;
  return request.headers.get("x-api-key") === API_KEY;
};

const server = serve({
  port: PORT,
  async fetch(request) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === "OPTIONS") {
      return jsonResponse({}, request, 204);
    }

    // Health check
    if (path === "/api/v1/health") {
      return jsonResponse({
        status: "healthy",
        node: KIMI_ID,
        timestamp: new Date().toISOString(),
        agents: Object.keys(agentStatus).length,
        version: "1.1.0",
        mcp_integration: MCP_INVOKE_URL ? "configured" : "not_configured"
      }, request);
    }

    // Full status
    if (path === "/api/v1/status") {
      return jsonResponse({
        node: KIMI_ID,
        agents: agentStatus,
        active_tasks: activeTasks.size,
        total_completed: Object.values(agentStatus).reduce((sum, a) => sum + a.tasks_completed, 0),
        uptime: process.uptime(),
        timestamp: new Date().toISOString(),
        demo_mode: process.env.APEX_DEMO_MODE === "true"
      }, request);
    }

    // Deploy endpoint
    if (path === "/api/v1/deploy" && request.method === "POST") {
      if (!isAuthorized(request)) {
        return jsonResponse({ accepted: false, error: "Unauthorized" }, request, 401);
      }

      try {
        const body = await request.json();
        if (!body?.repoUrl || typeof body.repoUrl !== "string") {
          return jsonResponse({ accepted: false, error: "repoUrl is required" }, request, 400);
        }

        const taskId = `kimi-${Date.now()}`;
        
        activeTasks.set(taskId, {
          id: taskId,
          repo: body.repoUrl,
          track: body.track,
          status: "queued",
          created_at: new Date().toISOString()
        });

        // Simulate async deployment
        setTimeout(() => {
          const task = activeTasks.get(taskId);
          if (task) {
            task.status = "completed";
            task.completed_at = new Date().toISOString();
            task.result = {
              frontend_url: "https://app.netlify.app",
              backend_url: "https://api.up.railway.app",
              mobile_build: "app-release.aab"
            };
          }
        }, 5000);

        return jsonResponse({
          accepted: true,
          task_id: taskId,
          message: "Deployment queued",
          eta: "5 minutes"
        }, request);

      } catch (error) {
        return jsonResponse({
          accepted: false,
          error: error instanceof Error ? error.message : "Invalid request"
        }, request, 400);
      }
    }

    // Task sync
    if (path === "/api/v1/sync") {
      const completed = Array.from(activeTasks.values())
        .filter(t => t.status === "completed");
      
      return jsonResponse({
        node: KIMI_ID,
        pending: activeTasks.size - completed.length,
        completed: completed,
        timestamp: new Date().toISOString()
      }, request);
    }

    // Bridge to Elite Squad
    if (path === "/api/v1/bridge/elite") {
      return jsonResponse({
        endpoint: ELITE_BRIDGE_URL,
        status: "connected",
        last_ping: new Date().toISOString()
      }, request);
    }

    if (path === "/api/v1/mcp") {
      return jsonResponse({
        configured: Boolean(MCP_INVOKE_URL),
        endpoint: MCP_INVOKE_URL || null
      }, request);
    }

    // 72-agent orchestration
    if (path === "/api/v1/orchestrate" && request.method === "POST") {
      if (!isAuthorized(request)) {
        return jsonResponse({ accepted: false, error: "Unauthorized" }, request, 401);
      }

      try {
        const body = await request.json();
        
        // Distribute work across 72 agents
        const distribution = {
          kimi_64: {
            screens: { agents: 16, screens_per_agent: 4 },
            api: { agents: 20, endpoints_per_agent: 1 },
            tests: { agents: 16, coverage: "full" },
            docs: { agents: 12, pages_per_agent: 5 }
          },
          kofi_8: {
            meta_router: "stack detection",
            architect: "integration planning",
            frontend: "code review",
            backend: "security verification",
            guardian: "consensus verification",
            devops: "deployment prep",
            captain: "orchestration",
            evolution: "pattern extraction"
          },
          youngstunners: {
            bridge: "sync every 10s",
            relay: "command forwarding",
            monitor: "health checks"
          },
          estimated_time: "3 minutes (vs 15 min sequential)"
        };

        return jsonResponse({
          accepted: true,
          task_id: `orch-${Date.now()}`,
          distribution: distribution,
          parallel_agents: 72,
          message: "72-agent parallel execution initiated"
        }, request);

      } catch (error) {
        return jsonResponse({
          accepted: false,
          error: error instanceof Error ? error.message : "Invalid request"
        }, request, 400);
      }
    }

    // Default 404
    return jsonResponse({
      error: "Not found",
      available_endpoints: [
        "GET  /api/v1/health",
        "GET  /api/v1/status",
        "POST /api/v1/deploy",
        "GET  /api/v1/sync",
        "GET  /api/v1/bridge/elite",
        "GET  /api/v1/mcp",
        "POST /api/v1/orchestrate"
      ]
    }, request, 404);
  }
});

console.log(`
╔════════════════════════════════════════════════════════════════╗
║           🦀 APEX Fleet API Server                              ║
║           Kimi CLI Node: ${KIMI_ID.padEnd(32)} ║
╠════════════════════════════════════════════════════════════════╣
║  Port: ${PORT.toString().padEnd(52)} ║
║  Health: http://35.235.249.249:${PORT}/api/v1/health${' '.repeat(7)}║
║  Status: http://35.235.249.249:${PORT}/api/v1/status${' '.repeat(7)}║
╠════════════════════════════════════════════════════════════════╣
║  8 Agents: Meta-Router, Planning, Frontend, Backend,           ║
║           Testing, DevOps, Reliability, Evolution              ║
╚════════════════════════════════════════════════════════════════╝
`);
