#!/usr/bin/env bun
/**
 * APEX Fleet ↔ Zo Computer Connector
 * Enables tandem operation between Kimi CLI and Zo
 */

const ZO_ENDPOINT = "https://kofi.zo.computer/api/kimi-bridge";
const APEX_ID = "apex-fleet-35.235.249.249";

interface TaskDelegation {
  task_id: string;
  type: "frontend" | "backend" | "devops" | "testing" | "fullstack";
  description: string;
  repo_url?: string;
  priority: "low" | "medium" | "high" | "critical";
  deadline?: string;
  context: Record<string, any>;
}

interface ZoResponse {
  accepted: boolean;
  zo_agent_id: string;
  estimated_completion: string;
  message: string;
}

class ZoConnector {
  private pendingTasks: Map<string, TaskDelegation> = new Map();
  private completedTasks: Map<string, any> = new Map();

  async delegateTask(task: TaskDelegation): Promise<ZoResponse> {
    console.log(`🔄 Delegating task to Zo Computer: ${task.type}`);

    const payload = {
      from: APEX_ID,
      type: "task_delegation",
      task: task,
      timestamp: new Date().toISOString()
    };

    try {
      const response = await fetch(ZO_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`Zo rejected task: ${response.statusText}`);
      }

      const result: ZoResponse = await response.json();
      
      if (result.accepted) {
        console.log(`✅ Zo accepted task: ${result.zo_agent_id}`);
        this.pendingTasks.set(task.task_id, task);
      } else {
        console.log(`❌ Zo rejected task: ${result.message}`);
      }

      return result;
    } catch (error) {
      console.error("Delegation failed:", error.message);
      return {
        accepted: false,
        zo_agent_id: "",
        estimated_completion: "",
        message: error.message
      };
    }
  }

  async syncWithZo(): Promise<void> {
    console.log("🔄 Syncing with Zo Computer...");

    try {
      const response = await fetch(`${ZO_ENDPOINT}/sync?from=${APEX_ID}`, {
        method: "GET",
        headers: { "Accept": "application/json" }
      });

      const updates = await response.json();

      // Process completed tasks
      if (updates.completed_tasks) {
        for (const task of updates.completed_tasks) {
          if (this.pendingTasks.has(task.task_id)) {
            console.log(`✅ Task completed by Zo: ${task.task_id}`);
            this.completedTasks.set(task.task_id, task);
            this.pendingTasks.delete(task.task_id);
          }
        }
      }

      // Process new requests from Zo
      if (updates.requests) {
        for (const request of updates.requests) {
          console.log(`📨 Request from Zo: ${request.type}`);
          await this.handleZoRequest(request);
        }
      }

    } catch (error) {
      console.error("Sync failed:", error.message);
    }
  }

  private async handleZoRequest(request: any): Promise<void> {
    switch (request.type) {
      case "build_request":
        console.log(`🔨 Zo requested build for: ${request.repo}`);
        // Trigger APEX build agents
        break;
      
      case "status_check":
        console.log("📊 Zo requested fleet status");
        // Return current APEX status
        break;
      
      case "resource_allocation":
        console.log(`⚡ Zo requesting ${request.agents} agents`);
        // Coordinate agent allocation
        break;
    }
  }

  async shareContext(context: Record<string, any>): Promise<void> {
    await fetch(ZO_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        from: APEX_ID,
        type: "context_share",
        context: context,
        timestamp: new Date().toISOString()
      })
    });
  }

  getStatus(): { pending: number; completed: number } {
    return {
      pending: this.pendingTasks.size,
      completed: this.completedTasks.size
    };
  }
}

// Fleet Manager Integration
class TandemManager {
  private zo = new ZoConnector();
  private syncInterval: Timer | null = null;

  async startTandemMode(): Promise<void> {
    console.log("🚀 Starting APEX ↔ Zo Tandem Mode");

    // Initial handshake
    await this.zo.shareContext({
      fleet_size: 64,
      status: "operational",
      capabilities: [
        "frontend_react",
        "backend_fastapi",
        "devops_k8s",
        "testing_automated",
        "mobile_capacitor"
      ]
    });

    // Start continuous sync
    this.syncInterval = setInterval(() => {
      this.zo.syncWithZo();
    }, 10000); // Sync every 10 seconds

    console.log("✅ Tandem mode active. Syncing every 10 seconds.");
  }

  async stopTandemMode(): Promise<void> {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
      this.syncInterval = null;
    }
    console.log("🛑 Tandem mode stopped");
  }

  async delegateToZo(type: string, description: string): Promise<void> {
    const task: TaskDelegation = {
      task_id: crypto.randomUUID(),
      type: type as any,
      description: description,
      priority: "high",
      context: { source: "apex_fleet" }
    };

    await this.zo.delegateTask(task);
  }

  getStatus(): void {
    const status = this.zo.getStatus();
    console.log("\n📊 Tandem Status:");
    console.log(`   Pending tasks: ${status.pending}`);
    console.log(`   Completed: ${status.completed}`);
  }
}

// CLI
const manager = new TandemManager();
const command = process.argv[2];

switch (command) {
  case "start":
    await manager.startTandemMode();
    // Keep alive
    await new Promise(() => {});
    break;

  case "stop":
    await manager.stopTandemMode();
    break;

  case "delegate":
    const type = process.argv[3];
    const desc = process.argv.slice(4).join(" ");
    if (!type || !desc) {
      console.log("Usage: bun run zo-connector.ts delegate <type> <description>");
      process.exit(1);
    }
    await manager.delegateToZo(type, desc);
    break;

  case "status":
    manager.getStatus();
    break;

  case "sync":
    await manager.zo.syncWithZo();
    break;

  default:
    console.log(`
╔══════════════════════════════════════════════════════════════╗
║              APEX Fleet ↔ Zo Computer Connector               ║
║                     Tandem Operation Mode                      ║
╚══════════════════════════════════════════════════════════════╝

Commands:
  start                Begin continuous tandem operation
  stop                 Stop tandem mode
  delegate <t> <desc>  Delegate task to Zo (types: frontend, backend, devops, testing)
  status               Show pending/completed tasks
  sync                 Manual sync with Zo

Examples:
  bun run zo-connector.ts start &
  bun run zo-connector.ts delegate frontend "Build login page for iHhashi"
  bun run zo-connector.ts status

This enables APEX Fleet and Zo Computer to work together:
- APEX handles bulk parallel work (64 agents)
- Zo handles specialized deep work
- Continuous sync every 10 seconds
- Shared context and task delegation
`);
}
