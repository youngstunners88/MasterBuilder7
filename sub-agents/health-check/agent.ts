#!/usr/bin/env bun
/**
 * HEALTH CHECK AGENT
 * Mission: Continuous monitoring of all endpoints
 */

import { serve } from 'bun';

const ENDPOINTS = [
  { name: 'Dashboard', url: 'http://localhost:3000/healthz', critical: true },
  { name: 'API', url: 'http://localhost:8000/api/v1/health', critical: true },
  { name: 'n8n', url: 'http://localhost:5678/healthz', critical: true },
  { name: 'PostgreSQL', url: 'internal', check: 'pg_isready', critical: true },
  { name: 'Redis', url: 'internal', check: 'redis-cli ping', critical: false },
  { name: 'Cost Guardian', url: 'http://localhost:7777/status', critical: false },
];

console.log('🏥 Health Check Agent Active');
console.log(`📊 Monitoring ${ENDPOINTS.length} endpoints\n`);

// Health check server
serve({
  port: 9999,
  async fetch(req) {
    const url = new URL(req.url);
    
    if (url.pathname === '/healthz') {
      // Overall health
      const checks = await Promise.all(ENDPOINTS.map(async (ep) => {
        try {
          if (ep.url === 'internal') {
            // Run command check
            return { name: ep.name, status: 'unknown', command: ep.check };
          }
          const resp = await fetch(ep.url, { signal: AbortSignal.timeout(5000) });
          return { 
            name: ep.name, 
            status: resp.ok ? 'healthy' : 'unhealthy',
            critical: ep.critical 
          };
        } catch (e) {
          return { 
            name: ep.name, 
            status: 'down', 
            critical: ep.critical,
            error: e.message 
          };
        }
      }));
      
      const allHealthy = checks.every(c => c.status === 'healthy' || !c.critical);
      
      return Response.json({
        status: allHealthy ? 'healthy' : 'degraded',
        timestamp: new Date().toISOString(),
        checks: checks
      }, { status: allHealthy ? 200 : 503 });
    }
    
    return new Response('Not found', { status: 404 });
  },
});

console.log('🏥 Health endpoint: http://localhost:9999/healthz');
console.log('   Ready for Render load balancer');
