#!/usr/bin/env bun
/**
 * Cost Guardian
 * Hard budget enforcement with kill switch
 */

import { Client } from 'pg';
import Redis from 'ioredis';

interface BudgetConfig {
  limitUSD: number;
  alert1: number;  // 50%
  alert2: number;  // 80%
  kill: number;    // 95%
}

const CONFIG: BudgetConfig = {
  limitUSD: parseFloat(process.env.BUDGET_LIMIT_USD || '100'),
  alert1: 50,
  alert2: 80,
  kill: 95
};

class CostGuardian {
  private pg: Client;
  private redis: Redis;
  private currentSpend: number = 0;
  private isKilled: boolean = false;

  constructor() {
    this.pg = new Client({
      connectionString: process.env.POSTGRES_URL
    });
    this.redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');
  }

  async start(): Promise<void> {
    await this.pg.connect();
    await this.initializeTables();
    
    console.log('🛡️  Cost Guardian active');
    console.log(`   Budget: $${CONFIG.limitUSD} USD`);
    console.log(`   Kill at: ${CONFIG.kill}%`);

    // Start monitoring loop
    setInterval(() => this.checkBudget(), 30000); // Every 30s
    
    // Initial check
    await this.checkBudget();
  }

  private async initializeTables(): Promise<void> {
    await this.pg.query(`
      CREATE TABLE IF NOT EXISTS cost_tracking (
        id SERIAL PRIMARY KEY,
        workflow_id VARCHAR(255),
        category VARCHAR(100),
        amount_usd DECIMAL(10,4),
        description TEXT,
        timestamp TIMESTAMP DEFAULT NOW()
      );
      
      CREATE INDEX IF NOT EXISTS idx_cost_workflow 
        ON cost_tracking(workflow_id);
      CREATE INDEX IF NOT EXISTS idx_cost_timestamp 
        ON cost_tracking(timestamp);
    `);

    await this.pg.query(`
      CREATE TABLE IF NOT EXISTS budget_status (
        id SERIAL PRIMARY KEY,
        total_spend DECIMAL(10,4) DEFAULT 0,
        percentage_used DECIMAL(5,2) DEFAULT 0,
        status VARCHAR(50) DEFAULT 'ok',
        last_check TIMESTAMP DEFAULT NOW()
      );
    `);
  }

  async recordCost(
    workflowId: string,
    category: string,
    amount: number,
    description: string
  ): Promise<void> {
    await this.pg.query(
      `INSERT INTO cost_tracking (workflow_id, category, amount_usd, description)
       VALUES ($1, $2, $3, $4)`,
      [workflowId, category, amount, description]
    );

    // Update Redis for fast access
    await this.redis.hincrbyfloat(
      'mb7:cost:total',
      workflowId,
      amount
    );

    console.log(`💰 Cost recorded: $${amount.toFixed(4)} (${category})`);
  }

  private async checkBudget(): Promise<void> {
    const result = await this.pg.query(
      `SELECT COALESCE(SUM(amount_usd), 0) as total 
       FROM cost_tracking 
       WHERE timestamp > NOW() - INTERVAL '24 hours'`
    );

    this.currentSpend = parseFloat(result.rows[0].total);
    const percentage = (this.currentSpend / CONFIG.limitUSD) * 100;

    // Update status
    await this.pg.query(
      `INSERT INTO budget_status (total_spend, percentage_used, status)
       VALUES ($1, $2, $3)
       ON CONFLICT (id) DO UPDATE 
       SET total_spend = $1, percentage_used = $2, status = $3, last_check = NOW()`,
      [this.currentSpend, percentage, this.getStatus(percentage)]
    );

    // Publish to Redis
    await this.redis.publish('mb7:budget:update', JSON.stringify({
      spend: this.currentSpend,
      limit: CONFIG.limitUSD,
      percentage,
      timestamp: new Date().toISOString()
    }));

    // Check thresholds
    await this.handleThresholds(percentage);
  }

  private async handleThresholds(percentage: number): Promise<void> {
    if (percentage >= CONFIG.kill && !this.isKilled) {
      await this.killSwitch('budget_exceeded', percentage);
    } else if (percentage >= CONFIG.alert2) {
      await this.alert('critical', `Budget at ${percentage.toFixed(1)}%`);
    } else if (percentage >= CONFIG.alert1) {
      await this.alert('warning', `Budget at ${percentage.toFixed(1)}%`);
    }
  }

  private async killSwitch(reason: string, percentage: number): Promise<void> {
    this.isKilled = true;
    
    console.error(`🚨 KILL SWITCH ACTIVATED`);
    console.error(`   Reason: ${reason}`);
    console.error(`   Spend: $${this.currentSpend.toFixed(2)} / $${CONFIG.limitUSD}`);
    console.error(`   Percentage: ${percentage.toFixed(1)}%`);

    // Set kill flag in Redis
    await this.redis.set('mb7:system:killed', 'true');
    await this.redis.set('mb7:system:killed:reason', reason);
    await this.redis.set('mb7:system:killed:at', new Date().toISOString());

    // Publish kill event
    await this.redis.publish('mb7:system:kill', JSON.stringify({
      reason,
      percentage,
      spend: this.currentSpend,
      limit: CONFIG.limitUSD
    }));

    // Stop all agents
    const agents = await this.redis.keys('mb7:agent:*');
    for (const agent of agents) {
      await this.redis.del(agent);
    }

    console.error('✅ All systems stopped');
  }

  private async alert(level: string, message: string): Promise<void> {
    console.log(`⚠️  ${level.toUpperCase()}: ${message}`);
    
    await this.redis.publish('mb7:alert', JSON.stringify({
      level,
      message,
      timestamp: new Date().toISOString()
    }));

    // Send webhook if configured
    const webhook = process.env.SLACK_WEBHOOK_URL;
    if (webhook && level === 'critical') {
      await fetch(webhook, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: `🚨 MB7: ${message}` })
      });
    }
  }

  private getStatus(percentage: number): string {
    if (percentage >= CONFIG.kill) return 'killed';
    if (percentage >= CONFIG.alert2) return 'critical';
    if (percentage >= CONFIG.alert1) return 'warning';
    return 'ok';
  }

  async getStatus(): Promise<{
    spend: number;
    limit: number;
    percentage: number;
    status: string;
    remaining: number;
  }> {
    const percentage = (this.currentSpend / CONFIG.limitUSD) * 100;
    return {
      spend: this.currentSpend,
      limit: CONFIG.limitUSD,
      percentage,
      status: this.getStatus(percentage),
      remaining: CONFIG.limitUSD - this.currentSpend
    };
  }
}

// Start if run directly
if (require.main === module) {
  const guardian = new CostGuardian();
  guardian.start().catch(console.error);
}

export { CostGuardian };