#!/usr/bin/env bun
/**
 * Bridge Monitor - 3-Zo Network Health Monitor
 * 
 * Usage:
 *   bun monitor.ts check     - Single health check
 *   bun monitor.ts daemon    - Continuous monitoring
 *   bun monitor.ts status    - Detailed status
 *   bun monitor.ts heartbeat - Send heartbeat to all nodes
 */

interface NodeStatus {
  name: string;
  endpoint: string;
  online: boolean;
  latency: number | null;
  agents: number | null;
  pendingMessages: number | null;
  lastCheck: string;
  error?: string;
}

const NODES = [
  {
    name: "youngstunners",
    endpoint: "https://youngstunners.zo.space/api/elite-bridge",
    role: "coordinator",
  },
  {
    name: "kofi",
    endpoint: "https://kofi.zo.space/api/kimi-bridge",
    role: "review-deploy",
  },
  {
    name: "kimi-cli",
    endpoint: "http://35.235.249.249:4200/api/v1/health",
    role: "builder",
  },
];

class BridgeMonitor {
  private consecutiveFailures: Map<string, number> = new Map();

  async checkNode(node: typeof NODES[0]): Promise<NodeStatus> {
    const start = Date.now();
    
    try {
      const response = await fetch(node.endpoint, {
        method: "GET",
        signal: AbortSignal.timeout(5000),
      });
      
      const latency = Date.now() - start;
      
      if (response.ok) {
        const data = await response.json().catch(() => ({}));
        this.consecutiveFailures.set(node.name, 0);
        
        return {
          name: node.name,
          endpoint: node.endpoint,
          online: true,
          latency,
          agents: data.agents || data.capabilities?.agents || null,
          pendingMessages: data.pendingMessages || data.messages?.length || null,
          lastCheck: new Date().toISOString(),
        };
      } else {
        return this.recordFailure(node, `HTTP ${response.status}`);
      }
    } catch (error) {
      return this.recordFailure(node, error instanceof Error ? error.message : "Unknown error");
    }
  }

  private recordFailure(node: typeof NODES[0], error: string): NodeStatus {
    const failures = (this.consecutiveFailures.get(node.name) || 0) + 1;
    this.consecutiveFailures.set(node.name, failures);
    
    if (failures >= 3) {
      this.sendAlert(node.name, error, failures);
    }
    
    return {
      name: node.name,
      endpoint: node.endpoint,
      online: false,
      latency: null,
      agents: null,
      pendingMessages: null,
      lastCheck: new Date().toISOString(),
      error,
    };
  }

  private sendAlert(node: string, error: string, failures: number): void {
    console.log(`\n🚨 ALERT: ${node} has been offline for ${failures} consecutive checks`);
    console.log(`   Error: ${error}`);
  }

  async checkAll(): Promise<NodeStatus[]> {
    return Promise.all(NODES.map(n => this.checkNode(n)));
  }

  printStatus(statuses: NodeStatus[]): void {
    const timestamp = new Date().toISOString();
    const online = statuses.filter(s => s.online).length;
    const total = statuses.length;
    const health = Math.round((online / total) * 100);

    console.log("\n═".repeat(65));
    console.log(`🌉 BRIDGE NETWORK STATUS - ${timestamp}`);
    console.log("═".repeat(65));
    console.log();
    console.log("  NODE            STATUS      LATENCY    AGENTS    MESSAGES");
    console.log("  ────────────── ─────────── ────────── ───────── ──────────");

    for (const s of statuses) {
      const status = s.online ? "✅ ONLINE " : "❌ OFFLINE";
      const latency = s.latency ? `${s.latency}ms`.padEnd(8) : "--".padEnd(8);
      const agents = s.agents !== null ? String(s.agents).padEnd(8) : "--".padEnd(8);
      const messages = s.pendingMessages !== null ? String(s.pendingMessages).padEnd(8) : "--".padEnd(8);
      
      console.log(`  ${s.name.padEnd(14)} ${status}    ${latency}  ${agents}  ${messages}`);
    }

    console.log();
    console.log(`  NETWORK HEALTH: ${health}% (${online}/${total} nodes)`);
    
    if (health < 100) {
      const offline = statuses.filter(s => !s.online);
      console.log(`\n  ⚠️  Offline nodes: ${offline.map(s => s.name).join(", ")}`);
    }
    
    console.log("═".repeat(65));
  }

  async daemon(intervalMs: number = 60000): Promise<void> {
    console.log("🌉 Bridge Monitor Daemon Started");
    console.log(`   Checking every ${intervalMs / 1000}s`);
    console.log("   Press Ctrl+C to stop\n");

    const check = async () => {
      const statuses = await this.checkAll();
      this.printStatus(statuses);
    };

    await check();
    setInterval(check, intervalMs);
  }

  async sendHeartbeat(): Promise<void> {
    console.log("💓 Sending heartbeat to all nodes...\n");
    
    for (const node of NODES) {
      try {
        const response = await fetch(node.endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            type: "heartbeat",
            from: "youngstunners.zo.computer",
            timestamp: new Date().toISOString(),
          }),
        });
        
        if (response.ok) {
          console.log(`  ✅ ${node.name}: Heartbeat received`);
        } else {
          console.log(`  ❌ ${node.name}: HTTP ${response.status}`);
        }
      } catch (error) {
        console.log(`  ❌ ${node.name}: ${error instanceof Error ? error.message : "Failed"}`);
      }
    }
  }
}

// CLI
const command = process.argv[2] || "check";

async function main() {
  const monitor = new BridgeMonitor();

  switch (command) {
    case "check":
      const statuses = await monitor.checkAll();
      monitor.printStatus(statuses);
      break;

    case "daemon":
      const interval = parseInt(process.argv[3]) || 60000;
      await monitor.daemon(interval);
      break;

    case "status":
      const detailed = await monitor.checkAll();
      monitor.printStatus(detailed);
      console.log("\n📊 Detailed Info:");
      for (const s of detailed) {
        console.log(`\n${s.name}:`);
        console.log(`  Endpoint: ${s.endpoint}`);
        console.log(`  Online: ${s.online}`);
        console.log(`  Latency: ${s.latency}ms`);
        console.log(`  Last Check: ${s.lastCheck}`);
        if (s.error) console.log(`  Error: ${s.error}`);
      }
      break;

    case "heartbeat":
      await monitor.sendHeartbeat();
      break;

    default:
      console.log("Usage: bun monitor.ts [check|daemon|status|heartbeat]");
  }
}

main();
