#!/usr/bin/env bun
/**
 * SPEND GUARDRAIL
 * Hard limits with auto-kill
 */

import { Redis } from 'ioredis';

const redis = new Redis();

const CONFIG = {
  HARD_LIMIT_USD: 500,        // $500/day max
  WARNING_THRESHOLD: 80,       // 80% warning
  CRITICAL_THRESHOLD: 95,      // 95% pause
  KILL_THRESHOLD: 100,        // 100% kill
  CHECK_INTERVAL_MS: 30000     // Check every 30 seconds
};

class SpendGuardrail {
  private currentSpend = 0;
  private percentageUsed = 0;

  async initialize(): Promise<void> {
    // Reset daily spend tracking
    const today = new Date().toISOString().split('T')[0];
    await redis.set(`apex:spend:daily:${today}`, '0', 'EX', 86400);
    await redis.set('apex:spend:limit', CONFIG.HARD_LIMIT_USD.toString());
    await redis.set('apex:spend:initialized', new Date().toISOString());
    
    console.log(`✅ Spend guardrail initialized: $${CONFIG.HARD_LIMIT_USD}/day limit`);
  }

  async recordCost(costUsd: number, category: string): Promise<void> {
    const today = new Date().toISOString().split('T')[0];
    const current = parseFloat(await redis.get(`apex:spend:daily:${today}`) || '0');
    const newTotal = current + costUsd;
    
    await redis.set(`apex:spend:daily:${today}`, newTotal.toString(), 'EX', 86400);
    await redis.incrbyfloat('apex:spend:total', costUsd);
    
    this.currentSpend = newTotal;
    this.percentageUsed = (newTotal / CONFIG.HARD_LIMIT_USD) * 100;
    
    // Log spend event
    await redis.lpush('apex:spend:log', JSON.stringify({
      timestamp: new Date().toISOString(),
      amount: costUsd,
      category,
      total: newTotal,
      percentage: this.percentageUsed
    }));
    
    // Check thresholds
    await this.checkThresholds();
  }

  private async checkThresholds(): Promise<void> {
    if (this.percentageUsed >= CONFIG.KILL_THRESHOLD) {
      console.error(`💀 SPEND LIMIT EXCEEDED: $${this.currentSpend.toFixed(2)}/${CONFIG.HARD_LIMIT_USD}`);
      await this.globalKill('Spend limit exceeded');
      return;
    }
    
    if (this.percentageUsed >= CONFIG.CRITICAL_THRESHOLD) {
      console.warn(`🛑 CRITICAL: ${this.percentageUsed.toFixed(1)}% budget used`);
      await redis.set('apex:fleet:paused', 'true', 'EX', 3600);
      await this.sendAlert('CRITICAL', `Budget at ${this.percentageUsed.toFixed(1)}% - fleet paused`);
      return;
    }
    
    if (this.percentageUsed >= CONFIG.WARNING_THRESHOLD) {
      console.warn(`⚠️  WARNING: ${this.percentageUsed.toFixed(1)}% budget used`);
      await this.sendAlert('WARNING', `Budget at ${this.percentageUsed.toFixed(1)}%`);
    }
  }

  private async globalKill(reason: string): Promise<void> {
    // Import and use kill switch
    await redis.set('apex:global:killswitch', 'SPEND_LIMIT_KILL', 'EX', 86400);
    
    // Stop all queues
    const queues = ['frontend', 'backend', 'testing', 'devops'];
    for (const queue of queues) {
      await redis.lpush(`apex:queue:${queue}:control`, 'SPEND_KILL');
    }
    
    // Log
    await redis.lpush('apex:emergency:log', JSON.stringify({
      timestamp: new Date().toISOString(),
      type: 'SPEND_KILL',
      reason,
      finalSpend: this.currentSpend
    }));
    
    console.error('💀 GLOBAL KILL: Spend limit exceeded');
    process.exit(1); // Kill the process
  }

  private async sendAlert(level: string, message: string): Promise<void> {
    await redis.lpush('apex:alerts', JSON.stringify({
      timestamp: new Date().toISOString(),
      level,
      message,
      spend: this.currentSpend,
      percentage: this.percentageUsed
    }));
  }

  async getStatus(): Promise<any> {
    const today = new Date().toISOString().split('T')[0];
    const spend = parseFloat(await redis.get(`apex:spend:daily:${today}`) || '0');
    const percentage = (spend / CONFIG.HARD_LIMIT_USD) * 100;
    const remaining = CONFIG.HARD_LIMIT_USD - spend;
    
    return {
      limit: CONFIG.HARD_LIMIT_USD,
      spent: spend.toFixed(2),
      remaining: remaining.toFixed(2),
      percentage: percentage.toFixed(1),
      status: percentage >= 100 ? 'EXCEEDED' : 
              percentage >= 95 ? 'CRITICAL' :
              percentage >= 80 ? 'WARNING' : 'NORMAL',
      projectedDailyBurn: (percentage * 3).toFixed(1) // Rough projection
    };
  }

  startMonitoring(): void {
    setInterval(async () => {
      const status = await this.getStatus();
      await redis.set('apex:spend:status', JSON.stringify(status));
      
      if (parseFloat(status.percentage) >= CONFIG.WARNING_THRESHOLD) {
        console.warn(`💰 Budget check: ${status.percentage}% used ($${status.spent}/$${CONFIG.HARD_LIMIT_USD})`);
      }
    }, CONFIG.CHECK_INTERVAL_MS);
    
    console.log('🔍 Spend monitoring active (30s intervals)');
  }
}

// Export for use
export { SpendGuardrail, CONFIG };

// CLI
if (import.meta.main) {
  const guardrail = new SpendGuardrail();
  
  switch (process.argv[2]) {
    case 'init':
      await guardrail.initialize();
      guardrail.startMonitoring();
      break;
      
    case 'status':
      const status = await guardrail.getStatus();
      console.log(JSON.stringify(status, null, 2));
      break;
      
    case 'test':
      // Test recording costs
      await guardrail.initialize();
      console.log('Testing cost recording...');
      await guardrail.recordCost(50, 'api_calls');
      await guardrail.recordCost(200, 'compute');
      console.log(await guardrail.getStatus());
      break;
      
    default:
      console.log(`
Usage:
  bun run spend-guardrail.ts init     - Initialize with hard limits
  bun run spend-guardrail.ts status  - Check current spend
  bun run spend-guardrail.ts test    - Test cost recording
      `);
  }
}
