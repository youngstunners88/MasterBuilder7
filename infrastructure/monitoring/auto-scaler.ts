#!/usr/bin/env bun
/**
 * MasterBuilder7 Auto-Scaler
 * 24/7 monitoring with intelligent scaling
 * Max 12 agents active, idle = 3
 */

import Redis from 'ioredis';
import { Client } from 'pg';

interface ScalingConfig {
  minAgents: number;
  maxAgents: number;
  idleTimeoutMs: number;
  scaleUpThreshold: number;
  scaleDownThreshold: number;
}

const CONFIG: ScalingConfig = {
  minAgents: 3,        // Always keep 3 warm
  maxAgents: 12,     // Never exceed 12
  idleTimeoutMs: 300000,  // 5 min idle = scale down candidate
  scaleUpThreshold: 8,    // Scale up when queue > 8
  scaleDownThreshold: 3   // Scale down when idle agents > 3
};

class AutoScaler {
  private redis: Redis;
  private pg: Client;
  private agents: Map<string, any> = new Map();

  constructor() {
    this.redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');
    this.pg = new Client({
      connectionString: process.env.POSTGRES_URL
    });
  }

  async start(): Promise<void> {
    await this.pg.connect();
    
    console.log('🤖 Auto-Scaler started');
    console.log(`   Min: ${CONFIG.minAgents} | Max: ${CONFIG.maxAgents}`);
    console.log(`   Idle timeout: ${CONFIG.idleTimeoutMs}ms`);

    // Main control loop - every 10 seconds
    setInterval(() => this.evaluateScaling(), 10000);
    
    // Initial boot with min agents
    await this.ensureMinAgents();

    // Subscribe to task queue
    this.redis.subscribe('mb7:tasks:pending');
    this.redis.on('message', (channel, message) => {
      if (channel === 'mb7:tasks:pending') {
        this.handleNewTask(JSON.parse(message));
      }
    });
  }

  private async evaluateScaling(): Promise<void> {
    const metrics = await this.collectMetrics();
    
    console.log(`[${new Date().toISOString()}] Metrics:`, {
      active: metrics.activeCount,
      idle: metrics.idleCount,
      pending: metrics.pendingTasks,
      budget: metrics.budgetPercentage
    });

    // Check budget kill switch
    if (metrics.budgetPercentage >= 95) {
      console.error('🚨 Budget critical - preventing scale up');
      return;
    }

    // Scale up decision
    if (metrics.pendingTasks > CONFIG.scaleUpThreshold && 
        metrics.activeCount < CONFIG.maxAgents) {
      const needed = Math.min(
        metrics.pendingTasks - CONFIG.scaleUpThreshold,
        CONFIG.maxAgents - metrics.activeCount
      );
      await this.scaleUp(needed);
    }

    // Scale down decision
    if (metrics.idleCount > CONFIG.scaleDownThreshold && 
        metrics.activeCount > CONFIG.minAgents) {
      const excess = Math.min(
        metrics.idleCount - CONFIG.scaleDownThreshold,
        metrics.activeCount - CONFIG.minAgents
      );
      await this.scaleDown(excess);
    }

    // Ensure minimum always
    if (metrics.activeCount < CONFIG.minAgents) {
      await this.ensureMinAgents();
    }
  }

  private async collectMetrics(): Promise<any> {
    const [agents, pendingTasks, budget] = await Promise.all([
      this.getAgentStates(),
      this.redis.llen('mb7:tasks:pending'),
      this.getBudgetPercentage()
    ]);

    const activeCount = agents.filter(a => a.state === 'active').length;
    const idleCount = agents.filter(a => a.state === 'idle').length;

    return { activeCount, idleCount, pendingTasks, budgetPercentage: budget };
  }

  private async getAgentStates(): Promise<any[]> {
    const keys = await this.redis.keys('mb7:agent:*');
    const agents = [];
    
    for (const key of keys) {
      const data = await this.redis.hgetall(key);
      agents.push({
        id: key,
        ...data,
        idleTime: data.lastActivity 
          ? Date.now() - parseInt(data.lastActivity)
          : Infinity
      });
    }

    return agents;
  }

  private async getBudgetPercentage(): Promise<number> {
    const result = await this.pg.query(
      `SELECT percentage_used FROM budget_status ORDER BY last_check DESC LIMIT 1`
    );
    return result.rows[0]?.percentage_used || 0;
  }

  private async handleNewTask(task: any): Promise<void> {
    const agents = await this.getAgentStates();
    const activeCount = agents.filter(a => a.state === 'active').length;

    // If no idle agents and under max, scale up immediately
    if (activeCount >= CONFIG.maxAgents) {
      console.log('⏳ Queue full, task waiting...');
      return;
    }

    const idleAgent = agents.find(a => a.state === 'idle');
    if (idleAgent) {
      await this.assignTask(idleAgent.id, task);
    } else {
      await this.scaleUp(1);
      await this.assignTask(`mb7:agent:new-${Date.now()}`, task);
    }
  }

  private async scaleUp(count: number): Promise<void> {
    console.log(`📈 Scaling up: +${count} agents`);

    for (let i = 0; i < count; i++) {
      const agentId = `mb7:agent:${Date.now()}-${i}`;
      
      // Register agent
      await this.redis.hset(agentId, {
        state: 'starting',
        type: 'general',
        startedAt: Date.now().toString(),
        lastActivity: Date.now().toString()
      });

      // Start actual agent process
      await this.spawnAgent(agentId);

      // Log scaling event
      await this.pg.query(
        `INSERT INTO scaling_events (action, agent_id, reason)
         VALUES ('scale_up', $1, 'queue_pressure')`,
        [agentId]
      );
    }
  }

  private async scaleDown(count: number): Promise<void> {
    console.log(`📉 Scaling down: -${count} agents`);

    const agents = await this.getAgentStates();
    const idleAgents = agents
      .filter(a => a.state === 'idle' && a.idleTime > CONFIG.idleTimeoutMs)
      .sort((a, b) => b.idleTime - a.idleTime) // Oldest idle first
      .slice(0, count);

    for (const agent of idleAgents) {
      await this.terminateAgent(agent.id);
      
      await this.pg.query(
        `INSERT INTO scaling_events (action, agent_id, reason)
         VALUES ('scale_down', $1, 'idle_timeout')`,
        [agent.id]
      );
    }
  }

  private async ensureMinAgents(): Promise<void> {
    const agents = await this.getAgentStates();
    const activeCount = agents.length;

    if (activeCount < CONFIG.minAgents) {
      const needed = CONFIG.minAgents - activeCount;
      console.log(`🔥 Booting ${needed} warm agents`);
      await this.scaleUp(needed);
    }
  }

  private async assignTask(agentId: string, task: any): Promise<void> {
    await this.redis.hset(agentId, {
      state: 'active',
      task: JSON.stringify(task),
      lastActivity: Date.now().toString()
    });

    await this.redis.publish('mb7:agent:assign', JSON.stringify({
      agentId,
      task
    }));
  }

  private async spawnAgent(agentId: string): Promise<void> {
    // In production, this would spawn actual process/container
    // For now, simulate agent start
    await this.redis.hset(agentId, {
      state: 'idle',
      pid: `sim-${Date.now()}`,
      lastActivity: Date.now().toString()
    });

    // Publish agent start
    await this.redis.publish('mb7:agent:spawned', JSON.stringify({
      agentId,
      timestamp: new Date().toISOString()
    }));
  }

  private async terminateAgent(agentId: string): Promise<void> {
    await this.redis.del(agentId);
    
    await this.redis.publish('mb7:agent:terminated', JSON.stringify({
      agentId,
      reason: 'idle_timeout'
    }));
  }
}

// Database setup for scaling events
async function setupDatabase(pg: Client): Promise<void> {
  await pg.query(`
    CREATE TABLE IF NOT EXISTS scaling_events (
      id SERIAL PRIMARY KEY,
      action VARCHAR(50) NOT NULL,
      agent_id VARCHAR(255),
      reason TEXT,
      timestamp TIMESTAMP DEFAULT NOW()
    );
    
    CREATE INDEX IF NOT EXISTS idx_scaling_timestamp 
      ON scaling_events(timestamp);
  `);
}

if (require.main === module) {
  const scaler = new AutoScaler();
  scaler.start().catch(console.error);
}

export { AutoScaler };