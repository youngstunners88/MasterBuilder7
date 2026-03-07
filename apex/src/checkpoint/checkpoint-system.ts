/**
 * APEX Checkpoint System
 * 
 * Saves and restores fleet state at regular intervals.
 * Enables rollback to known good states.
 * Provides crash recovery capabilities.
 */

import { Database } from "bun:sqlite";
import { mkdir, exists, readdir, copyFile } from "fs/promises";
import { join } from "path";

interface Checkpoint {
  id: string;
  timestamp: number;
  agentStates: Map<string, AgentState>;
  taskQueue: TaskState[];
  consensusState: ConsensusSnapshot;
  metadata: CheckpointMetadata;
}

interface AgentState {
  id: string;
  type: string;
  status: string;
  currentTask?: string;
  memory: Record<string, any>;
  lastHeartbeat: number;
}

interface TaskState {
  id: string;
  type: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  assignedTo?: string;
  payload: any;
  result?: any;
  createdAt: number;
  startedAt?: number;
  completedAt?: number;
}

interface ConsensusSnapshot {
  round: number;
  decisions: ConsensusDecision[];
  verifierVotes: Map<string, string[]>;
  timestamp: number;
}

interface ConsensusDecision {
  id: string;
  proposal: any;
  status: 'pending' | 'approved' | 'rejected';
  votes: { agentId: string; vote: 'yes' | 'no' }[];
  confidence: number;
}

interface CheckpointMetadata {
  version: string;
  agentCount: number;
  taskCount: number;
  consensusRound: number;
  diskUsage: number;
  reason: 'scheduled' | 'manual' | 'pre_migration' | 'emergency';
  tags: string[];
}

export class CheckpointSystem {
  private db: Database;
  private checkpointDir: string;
  private currentCheckpoint?: Checkpoint;
  private checkpointInterval: number;
  private maxCheckpoints: number;
  private checkpointTimer?: Timer;

  constructor(
    dbPath: string = "/data/fleet.db",
    checkpointDir: string = "/data/checkpoints",
    intervalMs: number = 300000, // 5 minutes
    maxCheckpoints: number = 50
  ) {
    this.db = new Database(dbPath);
    this.checkpointDir = checkpointDir;
    this.checkpointInterval = intervalMs;
    this.maxCheckpoints = maxCheckpoints;
    this.initDatabase();
  }

  private initDatabase() {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS checkpoints (
        id TEXT PRIMARY KEY,
        timestamp INTEGER NOT NULL,
        metadata TEXT NOT NULL,
        file_path TEXT NOT NULL,
        size_bytes INTEGER NOT NULL,
        restored_from BOOLEAN DEFAULT 0
      );
      
      CREATE INDEX IF NOT EXISTS idx_checkpoints_time 
      ON checkpoints(timestamp DESC);
      
      CREATE TABLE IF NOT EXISTS checkpoint_agents (
        checkpoint_id TEXT,
        agent_id TEXT,
        agent_type TEXT,
        status TEXT,
        current_task TEXT,
        memory TEXT,
        last_heartbeat INTEGER,
        PRIMARY KEY (checkpoint_id, agent_id),
        FOREIGN KEY (checkpoint_id) REFERENCES checkpoints(id)
      );
      
      CREATE TABLE IF NOT EXISTS checkpoint_tasks (
        checkpoint_id TEXT,
        task_id TEXT,
        task_type TEXT,
        status TEXT,
        assigned_to TEXT,
        payload TEXT,
        result TEXT,
        created_at INTEGER,
        started_at INTEGER,
        completed_at INTEGER,
        PRIMARY KEY (checkpoint_id, task_id),
        FOREIGN KEY (checkpoint_id) REFERENCES checkpoints(id)
      );
    `);
  }

  async start(): Promise<void> {
    await mkdir(this.checkpointDir, { recursive: true });
    
    // Ensure checkpoint directory exists
    const dirExists = await exists(this.checkpointDir);
    if (!dirExists) {
      throw new Error(`Failed to create checkpoint directory: ${this.checkpointDir}`);
    }

    // Start scheduled checkpoints
    this.checkpointTimer = setInterval(
      () => this.createCheckpoint('scheduled'),
      this.checkpointInterval
    );

    console.log(`✅ Checkpoint system started`);
    console.log(`   Directory: ${this.checkpointDir}`);
    console.log(`   Interval: ${this.checkpointInterval / 1000}s`);
    console.log(`   Max checkpoints: ${this.maxCheckpoints}`);

    // Create initial checkpoint
    await this.createCheckpoint('manual', ['initial', 'startup']);
  }

  stop(): void {
    if (this.checkpointTimer) {
      clearInterval(this.checkpointTimer);
      this.checkpointTimer = undefined;
    }
    console.log('⏹️  Checkpoint system stopped');
  }

  async createCheckpoint(
    reason: CheckpointMetadata['reason'] = 'scheduled',
    tags: string[] = []
  ): Promise<Checkpoint> {
    const checkpointId = `chk_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const timestamp = Date.now();

    // Gather current state
    const agentStates = await this.captureAgentStates();
    const taskQueue = await this.captureTaskQueue();
    const consensusState = await this.captureConsensusState();

    // Calculate disk usage
    const checkpoint: Checkpoint = {
      id: checkpointId,
      timestamp,
      agentStates,
      taskQueue,
      consensusState,
      metadata: {
        version: '2.0.0',
        agentCount: agentStates.size,
        taskCount: taskQueue.length,
        consensusRound: consensusState.round,
        diskUsage: 0, // Will be updated after save
        reason,
        tags
      }
    };

    // Save to disk
    const filePath = await this.saveCheckpointFile(checkpoint);
    const stats = await Bun.file(filePath).stat();
    checkpoint.metadata.diskUsage = stats?.size || 0;

    // Record in database
    this.db.run(
      `INSERT INTO checkpoints (id, timestamp, metadata, file_path, size_bytes)
       VALUES (?, ?, ?, ?, ?)`,
      [
        checkpointId,
        timestamp,
        JSON.stringify(checkpoint.metadata),
        filePath,
        checkpoint.metadata.diskUsage
      ]
    );

    // Save agent states
    for (const [agentId, state] of agentStates) {
      this.db.run(
        `INSERT INTO checkpoint_agents 
         (checkpoint_id, agent_id, agent_type, status, current_task, memory, last_heartbeat)
         VALUES (?, ?, ?, ?, ?, ?, ?)`,
        [
          checkpointId,
          agentId,
          state.type,
          state.status,
          state.currentTask || null,
          JSON.stringify(state.memory),
          state.lastHeartbeat
        ]
      );
    }

    // Save task states
    for (const task of taskQueue) {
      this.db.run(
        `INSERT INTO checkpoint_tasks
         (checkpoint_id, task_id, task_type, status, assigned_to, payload, result,
          created_at, started_at, completed_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [
          checkpointId,
          task.id,
          task.type,
          task.status,
          task.assignedTo || null,
          JSON.stringify(task.payload),
          task.result ? JSON.stringify(task.result) : null,
          task.createdAt,
          task.startedAt || null,
          task.completedAt || null
        ]
      );
    }

    this.currentCheckpoint = checkpoint;

    // Cleanup old checkpoints
    await this.cleanupOldCheckpoints();

    console.log(`💾 Checkpoint created: ${checkpointId}`);
    console.log(`   Agents: ${checkpoint.metadata.agentCount}`);
    console.log(`   Tasks: ${checkpoint.metadata.taskCount}`);
    console.log(`   Size: ${(checkpoint.metadata.diskUsage / 1024).toFixed(2)} KB`);

    return checkpoint;
  }

  private async captureAgentStates(): Promise<Map<string, AgentState>> {
    const states = new Map<string, AgentState>();
    
    const rows = this.db.query(
      "SELECT id, type, status, current_task, memory, last_heartbeat FROM agents"
    ).all() as any[];

    for (const row of rows) {
      states.set(row.id, {
        id: row.id,
        type: row.type,
        status: row.status,
        currentTask: row.current_task,
        memory: JSON.parse(row.memory || '{}'),
        lastHeartbeat: row.last_heartbeat
      });
    }

    return states;
  }

  private async captureTaskQueue(): Promise<TaskState[]> {
    const tasks: TaskState[] = [];
    
    const rows = this.db.query(
      `SELECT id, type, status, assigned_to, payload, result,
              created_at, started_at, completed_at
       FROM tasks WHERE status IN ('pending', 'running')`
    ).all() as any[];

    for (const row of rows) {
      tasks.push({
        id: row.id,
        type: row.type,
        status: row.status,
        assignedTo: row.assigned_to,
        payload: JSON.parse(row.payload || '{}'),
        result: row.result ? JSON.parse(row.result) : undefined,
        createdAt: row.created_at,
        startedAt: row.started_at,
        completedAt: row.completed_at
      });
    }

    return tasks;
  }

  private async captureConsensusState(): Promise<ConsensusSnapshot> {
    // This would integrate with the consensus engine
    // For now, return a placeholder
    return {
      round: 0,
      decisions: [],
      verifierVotes: new Map(),
      timestamp: Date.now()
    };
  }

  private async saveCheckpointFile(checkpoint: Checkpoint): Promise<string> {
    const fileName = `${checkpoint.id}.json`;
    const filePath = join(this.checkpointDir, fileName);
    
    const checkpointData = {
      ...checkpoint,
      agentStates: Array.from(checkpoint.agentStates.entries()),
      consensusState: {
        ...checkpoint.consensusState,
        verifierVotes: Array.from(checkpoint.consensusState.verifierVotes.entries())
      }
    };

    await Bun.write(filePath, JSON.stringify(checkpointData, null, 2));
    return filePath;
  }

  async restoreCheckpoint(checkpointId: string): Promise<boolean> {
    console.log(`🔄 Restoring checkpoint: ${checkpointId}`);

    // Load checkpoint from database
    const row = this.db.query(
      "SELECT file_path FROM checkpoints WHERE id = ?"
    ).get(checkpointId) as { file_path: string } | undefined;

    if (!row) {
      console.error(`❌ Checkpoint not found: ${checkpointId}`);
      return false;
    }

    // Load checkpoint file
    const file = Bun.file(row.file_path);
    if (!(await file.exists())) {
      console.error(`❌ Checkpoint file not found: ${row.file_path}`);
      return false;
    }

    const data = await file.json();
    
    // Restore agent states
    const agentStates = new Map(data.agentStates);
    for (const [agentId, state] of agentStates) {
      this.db.run(
        `UPDATE agents SET 
         status = ?, current_task = ?, memory = ?, last_heartbeat = ?
         WHERE id = ?`,
        [state.status, state.currentTask, JSON.stringify(state.memory), state.lastHeartbeat, agentId]
      );
    }

    // Mark as restored
    this.db.run(
      "UPDATE checkpoints SET restored_from = 1 WHERE id = ?",
      [checkpointId]
    );

    console.log(`✅ Restored checkpoint: ${checkpointId}`);
    console.log(`   Agents restored: ${agentStates.size}`);

    return true;
  }

  async listCheckpoints(limit: number = 10): Promise<CheckpointMetadata[]> {
    const rows = this.db.query(
      `SELECT id, timestamp, metadata, size_bytes, restored_from
       FROM checkpoints
       ORDER BY timestamp DESC
       LIMIT ?`
    ).all(limit) as any[];

    return rows.map(row => ({
      ...JSON.parse(row.metadata),
      id: row.id,
      timestamp: row.timestamp,
      diskUsage: row.size_bytes,
      restored: !!row.restored_from
    }));
  }

  private async cleanupOldCheckpoints(): Promise<void> {
    // Count total checkpoints
    const count = this.db.query(
      "SELECT COUNT(*) as count FROM checkpoints"
    ).get() as { count: number };

    if (count.count <= this.maxCheckpoints) {
      return;
    }

    // Get old checkpoints to delete
    const oldCheckpoints = this.db.query(
      `SELECT id, file_path FROM checkpoints
       WHERE restored_from = 0
       ORDER BY timestamp ASC
       LIMIT ?`
    ).all(count.count - this.maxCheckpoints) as { id: string; file_path: string }[];

    for (const chk of oldCheckpoints) {
      // Delete file
      try {
        await Bun.file(chk.file_path).delete();
      } catch (e) {
        console.warn(`Failed to delete checkpoint file: ${chk.file_path}`);
      }

      // Delete from database
      this.db.run("DELETE FROM checkpoint_agents WHERE checkpoint_id = ?", [chk.id]);
      this.db.run("DELETE FROM checkpoint_tasks WHERE checkpoint_id = ?", [chk.id]);
      this.db.run("DELETE FROM checkpoints WHERE id = ?", [chk.id]);
    }

    console.log(`🧹 Cleaned up ${oldCheckpoints.length} old checkpoints`);
  }

  async getCheckpointStats(): Promise<{
    totalCheckpoints: number;
    totalSize: number;
    oldestCheckpoint: number;
    latestCheckpoint: number;
  }> {
    const stats = this.db.query(
      `SELECT 
        COUNT(*) as total,
        SUM(size_bytes) as total_size,
        MIN(timestamp) as oldest,
        MAX(timestamp) as latest
       FROM checkpoints`
    ).get() as any;

    return {
      totalCheckpoints: stats.total || 0,
      totalSize: stats.total_size || 0,
      oldestCheckpoint: stats.oldest || 0,
      latestCheckpoint: stats.latest || 0
    };
  }
}

// Export singleton instance
export const checkpointSystem = new CheckpointSystem();