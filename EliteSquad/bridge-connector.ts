#!/usr/bin/env bun
/**
 * Bridge Connector
 * Syncs EliteSquad across 3-Zo network
 * 
 * FIXED VERSION - All bugs addressed
 */

import { KOFI_ZO, YOUNGSTUNNERS_ZO, KIMI_HOST } from './config.js';

interface SyncResult {
  node: string;
  status: 'success' | 'failed' | 'timeout';
  response?: unknown;
  error?: string;
  latency?: number;
}

interface BridgeMessage {
  type: string;
  from: string;
  timestamp: string;
  [key: string]: unknown;
}

async function sendWithRetry(
  url: string, 
  payload: BridgeMessage, 
  retries: number = 3,
  timeout: number = 10000
): Promise<SyncResult> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const start = Date.now();
      
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json"
        },
        body: JSON.stringify(payload),
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      const latency = Date.now() - start;
      
      if (!response.ok) {
        return {
          node: url,
          status: 'failed',
          error: `HTTP ${response.status}: ${response.statusText}`,
          latency
        };
      }
      
      const data = await response.json();
      return {
        node: url,
        status: 'success',
        response: data,
        latency
      };
      
    } catch (error) {
      if (attempt === retries) {
        clearTimeout(timeoutId);
        return {
          node: url,
          status: error instanceof Error && error.name === 'AbortError' ? 'timeout' : 'failed',
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
      // Exponential backoff
      await new Promise(r => setTimeout(r, Math.pow(2, attempt) * 100));
    }
  }
  
  return {
    node: url,
    status: 'failed',
    error: 'Max retries exceeded'
  };
}

async function syncAll(): Promise<void> {
  const timestamp = new Date().toISOString();
  console.log(`\n🔗 [${timestamp}] Syncing 3-Zo network...`);
  console.log("=".repeat(50));
  
  const payload: BridgeMessage = {
    type: "elitesquad-heartbeat",
    from: "youngstunners",
    agents: 8,
    projects: ["ihhashi", "nexus", "diamonds", "elitesquad"],
    status: "online",
    timestamp
  };
  
  // Send to all systems in parallel
  const results = await Promise.allSettled([
    sendWithRetry(`https://${KOFI_ZO}/api/kimi-bridge`, payload),
    sendWithRetry(`https://${YOUNGSTUNNERS_ZO}/api/elite-bridge`, payload),
    sendWithRetry(`http://${KIMI_HOST}/api/v1/health`, { ...payload, type: 'health-check' }, 1, 5000)
  ]);
  
  // Process results
  let successCount = 0;
  
  results.forEach((result, index) => {
    const nodes = ['Kofi Zo', 'Youngstunners Zo', 'Kimi CLI'];
    const node = nodes[index];
    
    if (result.status === 'fulfilled') {
      const syncResult = result.value;
      if (syncResult.status === 'success') {
        console.log(`✅ ${node}: synced (${syncResult.latency}ms)`);
        successCount++;
      } else if (syncResult.status === 'timeout') {
        console.log(`⏳ ${node}: timeout (offline/behind firewall)`);
      } else {
        console.log(`❌ ${node}: ${syncResult.error}`);
      }
    } else {
      console.log(`❌ ${node}: ${result.reason?.message || 'Unknown error'}`);
    }
  });
  
  console.log("=".repeat(50));
  console.log(`🤖 ${successCount}/3 nodes synced | 8 agents active | Next sync in 60s`);
}

// Graceful shutdown
let isRunning = true;

process.on('SIGINT', () => {
  console.log('\n\n🛑 Shutting down bridge connector...');
  isRunning = false;
  process.exit(0);
});

process.on('SIGTERM', () => {
  isRunning = false;
  process.exit(0);
});

// Initial sync
console.log("\n🚀 Elite Bridge Connector Started");
console.log("📍 youngstunners.zo.computer → kofi.zo.space → kimi-cli");
console.log("⏰ Sync interval: 60 seconds");
console.log("Press Ctrl+C to stop\n");

syncAll();

// Continuous sync
setInterval(() => {
  if (isRunning) {
    syncAll();
  }
}, 60000);
