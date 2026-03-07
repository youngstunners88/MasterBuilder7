#!/usr/bin/env bun
/**
 * EMERGENCY KILL SWITCH
 * Global halt for all fleet operations
 */

import { Redis } from 'ioredis';

const redis = new Redis({
  host: process.env.REDIS_HOST || 'localhost',
  port: parseInt(process.env.REDIS_PORT || '6379')
});

class EmergencyKillSwitch {
  async globalKill(reason: string): Promise<any> {
    console.log(`🛑 EMERGENCY KILL ACTIVATED: ${reason}`);
    
    // 1. Set global kill flag
    await redis.set('apex:global:killswitch', 'TRIGGERED', 'EX', 86400);
    
    // 2. Stop all queues
    const queues = ['frontend', 'backend', 'testing', 'devops', 'stress', 'audit', 'security'];
    for (const queue of queues) {
      await redis.lpush(`apex:queue:${queue}:control`, 'EMERGENCY_HALT');
      await redis.expire(`apex:queue:${queue}:control`, 3600);
    }
    
    // 3. Get current burn rate
    const stats = await this.getBurnRate();
    
    // 4. Log the kill
    await redis.lpush('apex:emergency:log', JSON.stringify({
      timestamp: new Date().toISOString(),
      reason,
      estimatedCost: stats.estimatedTotalCost,
      agentsHalted: stats.activeAgents
    }));
    
    return {
      status: 'KILLED',
      reason,
      estimatedCostToDate: stats.estimatedTotalCost,
      agentsHalted: stats.activeAgents,
      timestamp: new Date().toISOString()
    };
  }
  
  async getBurnRate(): Promise<any> {
    const tasksCompleted = parseInt(await redis.get('apex:metrics:tasks_completed') || '0');
    const activeAgents = parseInt(await redis.get('apex:fleet:active_count') || '0');
    const uptimeMinutes = parseInt(await redis.get('apex:fleet:uptime_minutes') || '0');
    
    // Zo Computer rates (approximate)
    const costPerTask = 0.05;  // $0.05 per task
    const costPerAgentMinute = 0.10;  // $0.10 per agent per minute
    
    const taskCost = tasksCompleted * costPerTask;
    const computeCost = activeAgents * uptimeMinutes * costPerAgentMinute;
    const totalCost = taskCost + computeCost;
    
    const projectedDaily = activeAgents * 24 * 60 * costPerAgentMinute;
    
    return {
      tasksCompleted,
      activeAgents,
      uptimeMinutes,
      estimatedTotalCost: totalCost.toFixed(2),
      projectedDailyBurn: projectedDaily.toFixed(2),
      recommendation: projectedDaily > 500 ? '⚠️  DAILY BURN EXCEEDS $500 - IMPLEMENT SPEND CAP' : '✓ Burn rate acceptable'
    };
  }
  
  async verifyConsensus(): Promise<any> {
    const consensusKeys = await redis.keys('apex:consensus:*');
    const checkpointKeys = await redis.keys('apex:checkpoint:*');
    
    return {
      consensusActive: consensusKeys.length > 10,
      consensusEvents: consensusKeys.length,
      checkpoints: checkpointKeys.length,
      status: consensusKeys.length < 10 ? '❌ CONSENSUS NOT DETECTED - QUALITY UNVERIFIED' : '✓ Consensus engine active'
    };
  }
  
  async checkHealth(): Promise<any> {
    const killswitch = await redis.get('apex:global:killswitch');
    const activeAgents = await redis.keys('apex:agent:*:heartbeat');
    const failedAgents = await redis.keys('apex:agent:*:failed');
    
    return {
      killswitchActive: killswitch === 'TRIGGERED',
      activeAgents: activeAgents.length,
      failedAgents: failedAgents.length,
      status: killswitch === 'TRIGGERED' ? '🔴 KILLED' : activeAgents.length > 0 ? '🟢 RUNNING' : '🟡 IDLE'
    };
  }
}

// CLI execution
const killSwitch = new EmergencyKillSwitch();

const command = process.argv[2];

switch (command) {
  case 'kill':
    const reason = process.argv[3] || 'Manual emergency stop';
    killSwitch.globalKill(reason).then(result => {
      console.log('\n' + '='.repeat(50));
      console.log('KILL SWITCH ACTIVATED');
      console.log('='.repeat(50));
      console.log(JSON.stringify(result, null, 2));
      process.exit(0);
    });
    break;
    
  case 'status':
    Promise.all([
      killSwitch.getBurnRate(),
      killSwitch.verifyConsensus(),
      killSwitch.checkHealth()
    ]).then(([burn, consensus, health]) => {
      console.log('\n' + '='.repeat(50));
      console.log('FLEET STATUS');
      console.log('='.repeat(50));
      console.log('\n💰 BURN RATE:');
      console.log(JSON.stringify(burn, null, 2));
      console.log('\n🎲 CONSENSUS:');
      console.log(JSON.stringify(consensus, null, 2));
      console.log('\n🏥 HEALTH:');
      console.log(JSON.stringify(health, null, 2));
      process.exit(0);
    });
    break;
    
  default:
    console.log(`
Usage:
  bun run emergency-kill-switch.ts kill [reason]   - Emergency stop all agents
  bun run emergency-kill-switch.ts status          - Check fleet status
    `);
    process.exit(1);
}
