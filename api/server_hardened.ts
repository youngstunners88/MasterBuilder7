/**
 * APEX API Server - Production Hardened
 * 
 * Phase A: Security & Integrity
 * - Proper CORS with allowed origins
 * - Idempotency keys for mutating requests
 * - Request validation
 * - Security headers
 * - Rate limiting (prepared)
 */

import { serve } from "bun";

// Configuration with strict security defaults
const PORT = parseInt(process.env.APEX_PORT || "3000");
const NODE_ENV = process.env.NODE_ENV || "development";
const API_SECRET = process.env.APEX_API_SECRET || "change-me-in-production";

// CORS configuration - NO WILDCARD in production
const ALLOWED_ORIGINS = process.env.APEX_ALLOWED_ORIGINS
  ? process.env.APEX_ALLOWED_ORIGINS.split(",")
  : NODE_ENV === "production"
    ? [] // Empty in production means CORS will block all origins
    : ["http://localhost:3000", "http://localhost:5173", "http://localhost:4173"];

// Health check - no CORS restriction needed
async function handleHealth(): Promise<Response> {
  return new Response(JSON.stringify({
    status: "ok",
    version: "2.0.0-hardened",
    phase: "A-Truth-Layer",
    timestamp: new Date().toISOString()
  }), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
      ...getSecurityHeaders()
    }
  });
}

// Agent status - simulation clearly labeled
async function handleStatus(): Promise<Response> {
  const status = {
    meta_router: { status: "ready", tasks_completed: 47, simulation: true },
    planning: { status: "ready", tasks_completed: 23, simulation: true },
    frontend: { status: "ready", tasks_completed: 31, simulation: true },
    backend: { status: "ready", tasks_completed: 28, simulation: true },
    testing: { status: "ready", tasks_completed: 19, simulation: true },
    devops: { status: "ready", tasks_completed: 15, simulation: true },
    reliability: { status: "ready", tasks_completed: 12, simulation: true },
    evolution: { status: "ready", tasks_completed: 8, simulation: true },
    _meta: {
      simulation: true,
      note: "These values are simulated for development",
      phase: "A-Truth-Layer"
    }
  };
  
  return new Response(JSON.stringify(status), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
      ...getSecurityHeaders()
    }
  });
}

// Build deploy endpoint with idempotency
async function handleDeploy(req: Request): Promise<Response> {
  // Validate idempotency key for mutating operation
  const idempotencyKey = req.headers.get("Idempotency-Key");
  if (!idempotencyKey) {
    return new Response(JSON.stringify({
      error: "Missing Idempotency-Key header",
      message: "Mutating requests must include Idempotency-Key header for replay protection"
    }), {
      status: 400,
      headers: {
        "Content-Type": "application/json",
        ...getSecurityHeaders()
      }
    });
  }
  
  // Validate idempotency key format
  if (!isValidIdempotencyKey(idempotencyKey)) {
    return new Response(JSON.stringify({
      error: "Invalid Idempotency-Key",
      message: "Idempotency key must be a valid UUID v4"
    }), {
      status: 400,
      headers: {
        "Content-Type": "application/json",
        ...getSecurityHeaders()
      }
    });
  }
  
  try {
    const body = await req.json();
    const projectName = body.project_name || "unnamed-project";
    const repoPath = body.repo_path || ".";
    
    console.log(`[Deploy] Idempotency-Key: ${idempotencyKey}`);
    console.log(`[Deploy] Project: ${projectName}, Path: ${repoPath}`);
    
    // In hardened version, we would:
    // 1. Check if idempotency key already exists (return cached result)
    // 2. Create build record with idempotency key
    // 3. Execute hardened build pipeline
    // 4. Store result with idempotency key
    
    return new Response(JSON.stringify({
      success: true,
      message: "Build queued",
      idempotency_key: idempotencyKey,
      project_name: projectName,
      status: "accepted",
      build_id: `build-${Date.now()}`,
      note: "This is Phase A hardened endpoint",
      simulation: true
    }), {
      status: 202,
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": idempotencyKey,
        ...getSecurityHeaders()
      }
    });
    
  } catch (error) {
    return new Response(JSON.stringify({
      error: "Invalid request body",
      details: String(error)
    }), {
      status: 400,
      headers: {
        "Content-Type": "application/json",
        ...getSecurityHeaders()
      }
    });
  }
}

// Build pipeline execution
async function handleBuild(req: Request): Promise<Response> {
  const idempotencyKey = req.headers.get("Idempotency-Key");
  if (!idempotencyKey) {
    return new Response(JSON.stringify({
      error: "Missing Idempotency-Key header"
    }), {
      status: 400,
      headers: {
        "Content-Type": "application/json",
        ...getSecurityHeaders()
      }
    });
  }
  
  try {
    const body = await req.json();
    const projectName = body.project_name || "unnamed-project";
    const repoPath = body.repo_path || ".";
    
    console.log(`[Build] Idempotency-Key: ${idempotencyKey}`);
    console.log(`[Build] Starting hardened pipeline for: ${projectName}`);
    
    // Response indicates this is hardened endpoint
    return new Response(JSON.stringify({
      success: true,
      message: "Build pipeline started (hardened)",
      idempotency_key: idempotencyKey,
      project_name: projectName,
      build_id: `build-${Date.now()}`,
      phase: "A-Truth-Layer",
      features: [
        "Artifact contracts",
        "Build event log",
        "Demo mode labeling",
        "Idempotency keys"
      ],
      simulation: true,
      note: "Phase B (Real Execution) coming next"
    }), {
      status: 202,
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": idempotencyKey,
        ...getSecurityHeaders()
      }
    });
    
  } catch (error) {
    return new Response(JSON.stringify({
      error: "Invalid request body"
    }), {
      status: 400,
      headers: {
        "Content-Type": "application/json",
        ...getSecurityHeaders()
      }
    });
  }
}

// CORS validation
function isOriginAllowed(origin: string | null): boolean {
  if (!origin) return false;
  if (NODE_ENV !== "production") return true; // Allow all in dev
  if (ALLOWED_ORIGINS.length === 0) return false; // Block all if none configured
  return ALLOWED_ORIGINS.includes(origin);
}

function getCorsHeaders(req: Request): Record<string, string> {
  const origin = req.headers.get("Origin");
  
  if (isOriginAllowed(origin)) {
    return {
      "Access-Control-Allow-Origin": origin || "",
      "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Idempotency-Key, Authorization",
      "Access-Control-Max-Age": "86400"
    };
  }
  
  return {};
}

function getSecurityHeaders(): Record<string, string> {
  return {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Referrer-Policy": "strict-origin-when-cross-origin"
  };
}

function isValidIdempotencyKey(key: string): boolean {
  // UUID v4 validation
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  return uuidRegex.test(key);
}

// Main server
console.log(`🚀 APEX API Server (Hardened Phase A)`);
console.log(`   Port: ${PORT}`);
console.log(`   Environment: ${NODE_ENV}`);
console.log(`   Allowed Origins: ${ALLOWED_ORIGINS.join(", ") || "none (CORS disabled)"}`);
console.log("=".repeat(50));

serve({
  port: PORT,
  async fetch(req: Request) {
    const url = new URL(req.url);
    const corsHeaders = getCorsHeaders(req);
    
    // Handle preflight
    if (req.method === "OPTIONS") {
      if (Object.keys(corsHeaders).length > 0) {
        return new Response(null, { 
          status: 204, 
          headers: { ...corsHeaders, ...getSecurityHeaders() } 
        });
      }
      return new Response(null, { status: 403 });
    }
    
    // Check CORS for actual requests
    if (!isOriginAllowed(req.headers.get("Origin"))) {
      return new Response(JSON.stringify({
        error: "CORS error",
        message: "Origin not allowed"
      }), {
        status: 403,
        headers: {
          "Content-Type": "application/json",
          ...getSecurityHeaders()
        }
      });
    }
    
    // Route handlers
    let response: Response;
    
    switch (url.pathname) {
      case "/health":
        response = await handleHealth();
        break;
        
      case "/status":
        response = await handleStatus();
        break;
        
      case "/deploy":
        response = await handleDeploy(req);
        break;
        
      case "/build":
        response = await handleBuild(req);
        break;
        
      default:
        response = new Response(JSON.stringify({ error: "Not found" }), {
          status: 404,
          headers: {
            "Content-Type": "application/json",
            ...getSecurityHeaders()
          }
        });
    }
    
    // Add CORS headers to response
    if (Object.keys(corsHeaders).length > 0) {
      Object.entries(corsHeaders).forEach(([key, value]) => {
        response.headers.set(key, value);
      });
    }
    
    return response;
  }
});

console.log("\n✅ Hardened API server running");
console.log("   Endpoints:");
console.log("   - GET  /health   (no auth required)");
console.log("   - GET  /status   (simulation flags added)");
console.log("   - POST /deploy   (requires Idempotency-Key)");
console.log("   - POST /build    (requires Idempotency-Key)");
