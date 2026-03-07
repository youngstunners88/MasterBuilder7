#!/usr/bin/env bun
/**
 * 3-TIER CHECKPOINT SYSTEM
 * Redis (hot) → PostgreSQL (warm) → Git (cold)
 */

import { Redis } from 'ioredis';
import { execSync } from 'child_process';
import { mkdirSync, writeFileSync } from 'fs';
import { join } from 'path';

const redis = new Redis();

class ThreeTierCheckpoint {
  private db: any; // PostgreSQL pool (would be asyncpg in Python)
  private gitRepo: string;

  constructor(gitRepoPath: string = './checkpoints') {
    this.gitRepo = gitRepoPath;
  }

  async createCheckpoint(projectId: string, agentOutputs: Record<string, any>): Promise<string> {
    const checkpointId = `fleet_${projectId}_${Date.now()}`;
    const timestamp = new Date().toISOString();
    
    console.log(`💾 Creating checkpoint: ${checkpointId}`);
    
    // TIER 1: Redis (hot) - 2 minute TTL for fast recovery
    await this.saveToRedis(checkpointId, projectId, agentOutputs, timestamp);
    
    // TIER 2: PostgreSQL (warm) - persistent storage
    await this.saveToDatabase(checkpointId, projectId, agentOutputs, timestamp);
    
    // TIER 3: Git (cold) - code snapshot
    await this.saveToGit(checkpointId, projectId, agentOutputs, timestamp);
    
    // Update checkpoint index
    await redis.lpush(`apex:project:${projectId}:checkpoints`, checkpointId);
    await redis.set(`apex:checkpoint:${checkpointId}:meta`, JSON.stringify({
      projectId,
      timestamp,
      agentCount: Object.keys(agentOutputs).length
    }));
    
    console.log(`✅ Checkpoint saved: ${checkpointId}`);
    return checkpointId;
  }

  private async saveToRedis(
    checkpointId: string, 
    projectId: string,
    agentOutputs: Record<string, any>, 
    timestamp: string
  ): Promise<void> {
    const pipeline = redis.pipeline();
    
    for (const [agentId, output] of Object.entries(agentOutputs)) {
      const hash = Bun.hash(output).toString(16).slice(0, 16);
      
      pipeline.hset(`apex:agent:${agentId}:checkpoint`, {
        checkpointId,
        projectId,
        outputHash: hash,
        timestamp,
        status: 'checkpointed'
      });
      
      // 2 minute TTL for hot recovery
      pipeline.expire(`apex:agent:${agentId}:checkpoint`, 120);
    }
    
    await pipeline.exec();
    console.log('   → Redis (hot): 120s TTL');
  }

  private async saveToDatabase(
    checkpointId: string,
    projectId: string, 
    agentOutputs: Record<string, any>,
    timestamp: string
  ): Promise<void> {
    // Store in SQLite for now (PostgreSQL would be in production)
    const dbPath = join(this.gitRepo, 'checkpoints.db');
    
    // Use Bun's built-in SQLite support
    const db = new Bun.SQLite(dbPath);
    
    db.run(`
      CREATE TABLE IF NOT EXISTS checkpoints (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        agent_outputs TEXT NOT NULL,
        created_at TEXT NOT NULL
      )
    `);
    
    db.run(`
      INSERT INTO checkpoints (id, project_id, agent_outputs, created_at)
      VALUES (?, ?, ?, ?)
    `, [checkpointId, projectId, JSON.stringify(agentOutputs), timestamp]);
    
    db.close();
    console.log('   → SQLite (warm): persistent');
  }

  private async saveToGit(
    checkpointId: string,
    projectId: string,
    agentOutputs: Record<string, any>,
    timestamp: string
  ): Promise<void> {
    const checkpointDir = join(this.gitRepo, checkpointId);
    
    // Create directory
    mkdirSync(checkpointDir, { recursive: true });
    
    // Write each agent output
    for (const [agentId, output] of Object.entries(agentOutputs)) {
      const filePath = join(checkpointDir, `${agentId}.json`);
      writeFileSync(filePath, JSON.stringify(output, null, 2));
    }
    
    // Write metadata
    writeFileSync(
      join(checkpointDir, 'meta.json'),
      JSON.stringify({ checkpointId, projectId, timestamp }, null, 2)
    );
    
    // Git commit (if git repo initialized)
    try {
      execSync('git add .', { cwd: this.gitRepo, stdio: 'ignore' });
      execSync(
        `git commit -m "Checkpoint ${checkpointId}: ${Object.keys(agentOutputs).length} agents"`,
        { cwd: this.gitRepo, stdio: 'ignore' }
      );
      console.log('   → Git (cold): committed');
    } catch (e) {
      console.log('   → Git (cold): files saved, commit skipped');
    }
  }

  async recoverFailedAgents(projectId: string, failedAgentIds: string[]): Promise<any> {
    console.log(`🔄 Recovering ${failedAgentIds.length} failed agents...`);
    
    // Get last checkpoint from Redis (fastest)
    const checkpointIds = await redis.lrange(`apex:project:${projectId}:checkpoints`, 0, 0);
    
    if (checkpointIds.length === 0) {
      throw new Error('No checkpoints found - full restart required');
    }
    
    const lastCheckpointId = checkpointIds[0];
    const metaRaw = await redis.get(`apex:checkpoint:${lastCheckpointId}:meta`);
    
    if (!metaRaw) {
      throw new Error('Checkpoint metadata missing');
    }
    
    const meta = JSON.parse(metaRaw);
    
    // Recover each failed agent
    const recovered: any[] = [];
    
    for (const agentId of failedAgentIds) {
      const checkpointData = await redis.hgetall(`apex:agent:${agentId}:checkpoint`);
      
      if (checkpointData && checkpointData.checkpointId === lastCheckpointId) {
        recovered.push({
          agentId,
          fromCheckpoint: lastCheckpointId,
          context: checkpointData,
          status: 'recovered'
        });
        
        console.log(`   → ${agentId}: recovered from ${lastCheckpointId}`);
      } else {
        // Try SQLite
        console.log(`   → ${agentId}: checkpoint expired, checking database...`);
        // Would query SQLite here
      }
    }
    
    return {
      projectId,
      recoveredCount: recovered.length,
      failedCount: failedAgentIds.length - recovered.length,
      fromCheckpoint: lastCheckpointId,
      agents: recovered
    };
  }

  async listCheckpoints(projectId: string): Promise<any[]> {
    const checkpointIds = await redis.lrange(`apex:project:${projectId}:checkpoints`, 0, 20);
    
    const checkpoints = [];
    for (const id of checkpointIds) {
      const metaRaw = await redis.get(`apex:checkpoint:${id}:meta`);
      if (metaRaw) {
        checkpoints.push(JSON.parse(metaRaw));
      }
    }
    
    return checkpoints;
  }
}

// Export
export { ThreeTierCheckpoint };

// CLI
if (import.meta.main) {
  const checkpoint = new ThreeTierCheckpoint();
  
  switch (process.argv[2]) {
    case 'create':
      const projectId = process.argv[3] || 'test-project';
      const mockOutputs = {
        'frontend-1': { code: 'console.log("frontend")', status: 'done' },
        'backend-1': { code: 'console.log("backend")', status: 'done' },
        'testing-1': { tests: 42, passed: 40, failed: 2 }
      };
      
      await checkpoint.createCheckpoint(projectId, mockOutputs);
      break;
      
    case 'list':
      const pid = process.argv[3] || 'test-project';
      const checkpoints = await checkpoint.listCheckpoints(pid);
      console.log(JSON.stringify(checkpoints, null, 2));
      break;
      
    case 'recover':
      const recPid = process.argv[3] || 'test-project';
      const failedAgents = (process.argv[4] || 'frontend-1,backend-1').split(',');
      const result = await checkpoint.recoverFailedAgents(recPid, failedAgents);
      console.log(JSON.stringify(result, null, 2));
      break;
      
    default:
      console.log(`
Usage:
  bun run checkpoint-system.ts create [projectId]    - Create checkpoint
  bun run checkpoint-system.ts list [projectId]       - List checkpoints
  bun run checkpoint-system.ts recover [projectId] [agent1,agent2]  - Recover agents
      `);
  }
}
