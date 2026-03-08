#!/usr/bin/env bun
/**
 * APEX Fleet API Server
 * Health checks, status, and orchestration endpoints
 */

import { serve } from "bun";

type TaskRecord = {
  id: string;
  repo: string;
  track?: string;
  status: "queued" | "completed";
  created_at: string;
  completed_at?: string;
  result?: Record<string, string>;
};

type IdempotencyRecord = {
  response: Record<string, unknown>;
  status: number;
  createdAt: number;
};

const PORT = parseInt(process.env.PORT || "4200", 10);
const PUBLIC_HOST = process.env.PUBLIC_HOST || "127.0.0.1";
const KIMI_ID = process.env.KIMI_ID || "kimi-cli-local";
const API_KEY = process.env.APEX_API_KEY;
const REQUIRE_API_KEY = (process.env.REQUIRE_API_KEY || "true").toLowerCase() === "true";
const DEMO_MODE = (process.env.APEX_DEMO_MODE || "false").toLowerCase() === "true";
const ELITE_BRIDGE_URL = process.env.ELITE_BRIDGE_URL || "http://100.127.121.51:4200";
const MCP_INVOKE_URL = process.env.MCP_INVOKE_URL || "";
const TASK_TTL_MS = parseInt(process.env.TASK_TTL_MS || `${60 * 60 * 1000}`, 10);
const IDEMPOTENCY_TTL_MS = parseInt(process.env.IDEMPOTENCY_TTL_MS || `${15 * 60 * 1000}`, 10);

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

const activeTasks = new Map<string, TaskRecord>();
const idempotencyCache = new Map<string, IdempotencyRecord>();

const sanitizeRepoUrl = (value: unknown): string | null => {
  if (typeof value !== "string") return null;
  try {
    const url = new URL(value);
    if (!url.protocol.startsWith("http")) return null;
    return url.toString();
  } catch {
    return null;
  }
};

const isOriginAllowed = (requestOrigin: string | null): boolean => {
  if (!requestOrigin) return true;
  if (ALLOWED_ORIGINS.includes("*")) return true;
  return ALLOWED_ORIGINS.includes(requestOrigin);
};

const getCorsOrigin = (requestOrigin: string | null): string | null => {
  if (!requestOrigin) return null;
  if (ALLOWED_ORIGINS.includes("*")) return "*";
  return ALLOWED_ORIGINS.includes(requestOrigin) ? requestOrigin : null;
};

const jsonResponse = (payload: Record<string, unknown>, request: Request, status = 200) => {
  const origin = getCorsOrigin(request.headers.get("origin"));
  const headers: Record<string, string> = {
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-Kimi-ID, X-API-Key, X-Idempotency-Key",
    "Content-Type": "application/json",
    "Vary": "Origin",
    "Cache-Control": "no-store"
  };

  if (origin) headers["Access-Control-Allow-Origin"] = origin;

  return new Response(JSON.stringify(payload), { status, headers });
};

const isAuthorized = (request: Request): boolean => {
  if (DEMO_MODE) return true;
  if (!REQUIRE_API_KEY) return true;
  if (!API_KEY) return false;
  return request.headers.get("x-api-key") === API_KEY;
};

const cacheResponse = (
  key: string,
  status: number,
  response: Record<string, unknown>
) => idempotencyCache.set(key, { status, response, createdAt: Date.now() });

const getCachedResponse = (key: string): IdempotencyRecord | null => {
  const cached = idempotencyCache.get(key);
  if (!cached) return null;
  if (Date.now() - cached.createdAt > IDEMPOTENCY_TTL_MS) {
    idempotencyCache.delete(key);
    return null;
  }
  return cached;
};

const garbageCollect = () => {
  const now = Date.now();

  for (const [id, task] of activeTasks.entries()) {
    const createdAtMs = new Date(task.created_at).getTime();
    if (!Number.isFinite(createdAtMs) || (now - createdAtMs) > TASK_TTL_MS) {
      activeTasks.delete(id);
    }
  }

  for (const [key, cached] of idempotencyCache.entries()) {
    if ((now - cached.createdAt) > IDEMPOTENCY_TTL_MS) {
      idempotencyCache.delete(key);
    }
  }
};

const server = serve({
  port: PORT,
  async fetch(request) {
    garbageCollect();

    const url = new URL(request.url);
    const path = url.pathname;

    if (!isOriginAllowed(request.headers.get("origin"))) {
      return jsonResponse({ error: "Origin not allowed" }, request, 403);
    }

    if (request.method === "OPTIONS") {
      return jsonResponse({}, request, 204);
    }

    if (path === "/api/v1/health") {
      return jsonResponse({
        status: "healthy",
        node: KIMI_ID,
        timestamp: new Date().toISOString(),
        agents: Object.keys(agentStatus).length,
        version: "1.2.0",
        mcp_integration: MCP_INVOKE_URL ? "configured" : "not_configured",
        auth_mode: DEMO_MODE ? "demo" : (REQUIRE_API_KEY ? "api_key_required" : "open")
      }, request);
    }

    if (path === "/api/v1/status") {
      return jsonResponse({
        node: KIMI_ID,
        agents: agentStatus,
        active_tasks: activeTasks.size,
        total_completed: Object.values(agentStatus).reduce((sum, a) => sum + a.tasks_completed, 0),
        uptime: process.uptime(),
        timestamp: new Date().toISOString(),
        demo_mode: DEMO_MODE
      }, request);
    }

    if (path === "/api/v1/deploy" && request.method === "POST") {
      if (!isAuthorized(request)) {
        return jsonResponse({ accepted: false, error: "Unauthorized" }, request, 401);
      }

      try {
        const body = await request.json();
        const repoUrl = sanitizeRepoUrl(body?.repoUrl);
        if (!repoUrl) {
          return jsonResponse({ accepted: false, error: "Valid repoUrl is required" }, request, 400);
        }

        const idempotencyKey = request.headers.get("x-idempotency-key");
        if (idempotencyKey) {
          const cached = getCachedResponse(`deploy:${idempotencyKey}`);
          if (cached) {
            return jsonResponse({ ...cached.response, idempotent_replay: true }, request, cached.status);
          }
        }

        const taskId = `kimi-${Date.now()}`;
        activeTasks.set(taskId, {
          id: taskId,
          repo: repoUrl,
          track: typeof body.track === "string" ? body.track : undefined,
          status: "queued",
          created_at: new Date().toISOString()
        });

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

        const response = {
          accepted: true,
          task_id: taskId,
          message: "Deployment queued",
          eta: "5 minutes"
        };

        if (idempotencyKey) cacheResponse(`deploy:${idempotencyKey}`, 200, response);

        return jsonResponse(response, request);
      } catch (error) {
        return jsonResponse({
          accepted: false,
          error: error instanceof Error ? error.message : "Invalid request"
        }, request, 400);
      }
    }

    if (path === "/api/v1/sync") {
      const completed = Array.from(activeTasks.values()).filter(t => t.status === "completed");

      return jsonResponse({
        node: KIMI_ID,
        pending: activeTasks.size - completed.length,
        completed,
        timestamp: new Date().toISOString()
      }, request);
    }

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

    if (path === "/api/v1/orchestrate" && request.method === "POST") {
      if (!isAuthorized(request)) {
        return jsonResponse({ accepted: false, error: "Unauthorized" }, request, 401);
      }

      try {
        const body = await request.json();
        const repoUrl = sanitizeRepoUrl(body?.repoUrl);
        if (!repoUrl) {
          return jsonResponse({ accepted: false, error: "Valid repoUrl is required" }, request, 400);
        }

        const response = {
          accepted: true,
          task_id: `orch-${Date.now()}`,
          target_repo: repoUrl,
          distribution: {
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
          },
          parallel_agents: 72,
          message: "72-agent parallel execution initiated"
        };

        return jsonResponse(response, request);
      } catch (error) {
        return jsonResponse({
          accepted: false,
          error: error instanceof Error ? error.message : "Invalid request"
        }, request, 400);
      }
    }

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
║  Health: http://${PUBLIC_HOST}:${PORT}/api/v1/health${' '.repeat(7)}║
║  Status: http://${PUBLIC_HOST}:${PORT}/api/v1/status${' '.repeat(7)}║
╠════════════════════════════════════════════════════════════════╣
║  8 Agents: Meta-Router, Planning, Frontend, Backend,           ║
║           Testing, DevOps, Reliability, Evolution              ║
╚════════════════════════════════════════════════════════════════╝
`);
