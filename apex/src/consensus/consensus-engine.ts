/**
 * APEX Consensus Engine
 * 
 * Implements distributed consensus for agent decisions.
 * Uses 3-verifier protocol for quality control.
 * Handles conflicts and reaches agreement.
 */

import { Database } from "bun:sqlite";
import { EventEmitter } from "events";

interface Proposal {
  id: string;
  type: 'code_review' | 'architecture' | 'deployment' | 'rollback' | 'checkpoint';
  agentId: string;
  payload: any;
  timestamp: number;
  priority: number;
}

interface Vote {
  proposalId: string;
  agentId: string;
  agentType: string;
  vote: 'approve' | 'reject' | 'abstain';
  confidence: number; // 0-1
  reasoning: string;
  timestamp: number;
}

interface ConsensusResult {
  proposalId: string;
  status: 'approved' | 'rejected' | 'pending' | 'deadlocked';
  approvalRate: number;
  confidence: number;
  votes: Vote[];
  requiredVerifiers: number;
  actualVerifiers: number;
  timestamp: number;
  executed: boolean;
}

interface ConsensusConfig {
  threshold: number; // Minimum approval rate (0-1)
  minVerifiers: number; // Minimum verifiers required
  maxVerifiers: number; // Maximum verifiers to wait for
  timeoutMs: number; // Timeout for consensus
  conflictResolution: 'majority' | 'weighted' | 'hierarchical';
}

export class ConsensusEngine extends EventEmitter {
  private db: Database;
  private config: ConsensusConfig;
  private activeProposals: Map<string, Proposal>;
  private pendingVotes: Map<string, Vote[]>;
  private results: Map<string, ConsensusResult>;
  private verifierPool: string[];

  constructor(
    dbPath: string = "/data/fleet.db",
    config: Partial<ConsensusConfig> = {}
  ) {
    super();
    
    this.db = new Database(dbPath);
    this.config = {
      threshold: 0.80,
      minVerifiers: 3,
      maxVerifiers: 5,
      timeoutMs: 300000, // 5 minutes
      conflictResolution: 'weighted',
      ...config
    };

    this.activeProposals = new Map();
    this.pendingVotes = new Map();
    this.results = new Map();
    this.verifierPool = [];

    this.initDatabase();
    this.loadVerifierPool();
  }

  private initDatabase() {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS consensus_proposals (
        id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        agent_id TEXT NOT NULL,
        payload TEXT NOT NULL,
        timestamp INTEGER NOT NULL,
        priority INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending'
      );
      
      CREATE TABLE IF NOT EXISTS consensus_votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proposal_id TEXT NOT NULL,
        agent_id TEXT NOT NULL,
        agent_type TEXT NOT NULL,
        vote TEXT NOT NULL,
        confidence REAL NOT NULL,
        reasoning TEXT,
        timestamp INTEGER NOT NULL,
        UNIQUE(proposal_id, agent_id)
      );
      
      CREATE TABLE IF NOT EXISTS consensus_results (
        proposal_id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        approval_rate REAL NOT NULL,
        confidence REAL NOT NULL,
        required_verifiers INTEGER NOT NULL,
        actual_verifiers INTEGER NOT NULL,
        timestamp INTEGER NOT NULL,
        executed BOOLEAN DEFAULT 0
      );
      
      CREATE INDEX IF NOT EXISTS idx_proposals_status 
      ON consensus_proposals(status);
      
      CREATE INDEX IF NOT EXISTS idx_votes_proposal 
      ON consensus_votes(proposal_id);
    `);
  }

  private loadVerifierPool() {
    // Load eligible verifier agents from database
    const rows = this.db.query(
      `SELECT id FROM agents 
       WHERE type IN ('reliability', 'testing', 'auditor')
       AND status = 'running'`
    ).all() as { id: string }[];

    this.verifierPool = rows.map(r => r.id);
    console.log(`🎯 Loaded ${this.verifierPool.length} verifiers`);
  }

  async submitProposal(proposal: Omit<Proposal, 'id' | 'timestamp'>): Promise<string> {
    const id = `prop_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const fullProposal: Proposal = {
      ...proposal,
      id,
      timestamp: Date.now()
    };

    // Store in database
    this.db.run(
      `INSERT INTO consensus_proposals (id, type, agent_id, payload, timestamp, priority)
       VALUES (?, ?, ?, ?, ?, ?)`,
      [id, fullProposal.type, fullProposal.agentId, 
       JSON.stringify(fullProposal.payload), fullProposal.timestamp, fullProposal.priority]
    );

    // Add to active proposals
    this.activeProposals.set(id, fullProposal);
    this.pendingVotes.set(id, []);

    console.log(`📨 Proposal submitted: ${id}`);
    console.log(`   Type: ${fullProposal.type}`);
    console.log(`   From: ${fullProposal.agentId}`);

    // Start consensus process
    this.startConsensusRound(id);

    return id;
  }

  private async startConsensusRound(proposalId: string) {
    const proposal = this.activeProposals.get(proposalId);
    if (!proposal) return;

    // Select verifiers
    const verifiers = this.selectVerifiers(proposal);
    console.log(`🎲 Selected ${verifiers.length} verifiers for ${proposalId}`);

    // Request votes
    for (const verifierId of verifiers) {
      this.requestVote(proposalId, verifierId);
    }

    // Set timeout
    setTimeout(() => {
      this.finalizeConsensus(proposalId);
    }, this.config.timeoutMs);
  }

  private selectVerifiers(proposal: Proposal): string[] {
    // Filter out the proposing agent
    const eligible = this.verifierPool.filter(v => v !== proposal.agentId);
    
    // Shuffle and select
    const shuffled = eligible.sort(() => Math.random() - 0.5);
    return shuffled.slice(0, this.config.maxVerifiers);
  }

  private requestVote(proposalId: string, verifierId: string) {
    // Emit event for agent to handle
    this.emit('voteRequested', {
      proposalId,
      verifierId,
      proposal: this.activeProposals.get(proposalId)
    });

    console.log(`🗳️  Vote requested from ${verifierId} for ${proposalId}`);
  }

  async submitVote(vote: Omit<Vote, 'timestamp'>): Promise<boolean> {
    const fullVote: Vote = {
      ...vote,
      timestamp: Date.now()
    };

    // Validate proposal exists
    if (!this.activeProposals.has(vote.proposalId)) {
      console.error(`❌ Proposal not found: ${vote.proposalId}`);
      return false;
    }

    // Check for duplicate vote
    const existingVotes = this.pendingVotes.get(vote.proposalId) || [];
    if (existingVotes.some(v => v.agentId === vote.agentId)) {
      console.warn(`⚠️  Duplicate vote from ${vote.agentId}`);
      return false;
    }

    // Store vote
    existingVotes.push(fullVote);
    this.pendingVotes.set(vote.proposalId, existingVotes);

    this.db.run(
      `INSERT INTO consensus_votes 
       (proposal_id, agent_id, agent_type, vote, confidence, reasoning, timestamp)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [vote.proposalId, vote.agentId, vote.agentType, vote.vote, 
       vote.confidence, vote.reasoning, fullVote.timestamp]
    );

    console.log(`✅ Vote recorded: ${vote.agentId} -> ${vote.vote}`);

    // Check if consensus reached
    await this.checkConsensus(vote.proposalId);

    return true;
  }

  private async checkConsensus(proposalId: string) {
    const votes = this.pendingVotes.get(proposalId) || [];
    
    // Wait for minimum verifiers
    if (votes.length < this.config.minVerifiers) {
      return;
    }

    // Calculate approval rate
    const approvals = votes.filter(v => v.vote === 'approve').length;
    const rejections = votes.filter(v => v.vote === 'reject').length;
    const total = votes.filter(v => v.vote !== 'abstain').length;

    if (total === 0) return;

    const approvalRate = approvals / total;

    // Check threshold
    if (approvalRate >= this.config.threshold) {
      await this.finalizeConsensus(proposalId, 'approved');
    } else if (rejections / total > (1 - this.config.threshold)) {
      await this.finalizeConsensus(proposalId, 'rejected');
    } else if (votes.length >= this.config.maxVerifiers) {
      // Max verifiers reached but no consensus
      await this.finalizeConsensus(proposalId, 'deadlocked');
    }
  }

  private async finalizeConsensus(
    proposalId: string, 
    forcedStatus?: 'approved' | 'rejected' | 'deadlocked'
  ) {
    const proposal = this.activeProposals.get(proposalId);
    const votes = this.pendingVotes.get(proposalId) || [];

    if (!proposal) return;

    // Calculate final result
    const approvals = votes.filter(v => v.vote === 'approve');
    const total = votes.filter(v => v.vote !== 'abstain').length;
    const approvalRate = total > 0 ? approvals.length / total : 0;
    
    // Calculate weighted confidence
    const avgConfidence = votes.length > 0
      ? votes.reduce((sum, v) => sum + v.confidence, 0) / votes.length
      : 0;

    // Determine status
    let status: ConsensusResult['status'];
    if (forcedStatus) {
      status = forcedStatus;
    } else if (approvalRate >= this.config.threshold) {
      status = 'approved';
    } else {
      status = 'rejected';
    }

    const result: ConsensusResult = {
      proposalId,
      status,
      approvalRate,
      confidence: avgConfidence,
      votes,
      requiredVerifiers: this.config.minVerifiers,
      actualVerifiers: votes.length,
      timestamp: Date.now(),
      executed: false
    };

    // Store result
    this.results.set(proposalId, result);
    this.db.run(
      `INSERT INTO consensus_results 
       (proposal_id, status, approval_rate, confidence, required_verifiers, actual_verifiers, timestamp)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [proposalId, status, approvalRate, avgConfidence, 
       this.config.minVerifiers, votes.length, result.timestamp]
    );

    // Update proposal status
    this.db.run(
      "UPDATE consensus_proposals SET status = ? WHERE id = ?",
      [status, proposalId]
    );

    // Clean up
    this.activeProposals.delete(proposalId);
    this.pendingVotes.delete(proposalId);

    console.log(`🏁 Consensus finalized: ${proposalId}`);
    console.log(`   Status: ${status.toUpperCase()}`);
    console.log(`   Approval: ${(approvalRate * 100).toFixed(1)}%`);
    console.log(`   Confidence: ${(avgConfidence * 100).toFixed(1)}%`);

    // Emit result
    this.emit('consensusReached', result);

    // Auto-execute if approved
    if (status === 'approved') {
      this.executeProposal(proposalId, result);
    }
  }

  private async executeProposal(proposalId: string, result: ConsensusResult) {
    console.log(`🚀 Executing proposal: ${proposalId}`);

    // Mark as executed
    result.executed = true;
    this.db.run(
      "UPDATE consensus_results SET executed = 1 WHERE proposal_id = ?",
      [proposalId]
    );

    // Emit for execution
    this.emit('executeProposal', result);
  }

  getResult(proposalId: string): ConsensusResult | undefined {
    return this.results.get(proposalId);
  }

  getPendingProposals(): Proposal[] {
    return Array.from(this.activeProposals.values());
  }

  getStats(): {
    totalProposals: number;
    approved: number;
    rejected: number;
    deadlocked: number;
    pending: number;
    averageApprovalRate: number;
  } {
    const allResults = Array.from(this.results.values());
    
    return {
      totalProposals: allResults.length + this.activeProposals.size,
      approved: allResults.filter(r => r.status === 'approved').length,
      rejected: allResults.filter(r => r.status === 'rejected').length,
      deadlocked: allResults.filter(r => r.status === 'deadlocked').length,
      pending: this.activeProposals.size,
      averageApprovalRate: allResults.length > 0
        ? allResults.reduce((sum, r) => sum + r.approvalRate, 0) / allResults.length
        : 0
    };
  }

  // Conflict resolution strategies
  resolveConflict(proposals: Proposal[]): Proposal | null {
    switch (this.config.conflictResolution) {
      case 'majority':
        return this.resolveByMajority(proposals);
      case 'weighted':
        return this.resolveByWeight(proposals);
      case 'hierarchical':
        return this.resolveByHierarchy(proposals);
      default:
        return proposals[0];
    }
  }

  private resolveByMajority(proposals: Proposal[]): Proposal | null {
    // Simple: return the first (or could count votes)
    return proposals[0] || null;
  }

  private resolveByWeight(proposals: Proposal[]): Proposal | null {
    // Weight by agent reliability score
    const weighted = proposals.map(p => ({
      proposal: p,
      weight: this.getAgentReliability(p.agentId)
    }));

    weighted.sort((a, b) => b.weight - a.weight);
    return weighted[0]?.proposal || null;
  }

  private resolveByHierarchy(proposals: Proposal[]): Proposal | null {
    // Hierarchy: reliability > testing > devops > backend > frontend > planning
    const hierarchy = ['reliability', 'testing', 'devops', 'backend', 'frontend', 'planning'];
    
    const sorted = proposals.sort((a, b) => {
      const aRank = hierarchy.indexOf(a.type) ?? 999;
      const bRank = hierarchy.indexOf(b.type) ?? 999;
      return aRank - bRank;
    });

    return sorted[0] || null;
  }

  private getAgentReliability(agentId: string): number {
    // Query agent's historical performance
    const row = this.db.query(
      `SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved
       FROM consensus_proposals
       WHERE agent_id = ?`
    ).get(agentId) as { total: number; approved: number } | undefined;

    if (!row || row.total === 0) return 0.5;
    return row.approved / row.total;
  }
}

// Export singleton
export const consensusEngine = new ConsensusEngine();