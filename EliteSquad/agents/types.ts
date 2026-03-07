/**
 * EliteSquad Type Definitions
 * Core types for all agents and operations
 */

// ============================================
// Core Agent Types
// ============================================

export interface SOUL {
  name: string;
  role: string;
  essence: string;
  personality: string[];
  coreBeliefs: string[];
  speechPatterns: string[];
  memoryAnchors: Record<string, unknown>;
  loaded: boolean;
}

export interface AgentConfig {
  id: string;
  name: string;
  role: AgentRole;
}

export type AgentRole = 
  | 'command' 
  | 'orchestration' 
  | 'planning' 
  | 'ui' 
  | 'api' 
  | 'qa' 
  | 'deploy' 
  | 'learn';

export interface AgentState {
  id: string;
  status: AgentStatus;
  memoryLoaded: boolean;
  lastActivity: string;
  tasksCompleted: number;
  errorCount: number;
}

export type AgentStatus = 'idle' | 'active' | 'busy' | 'error' | 'offline';

// ============================================
// Deployment Types
// ============================================

export interface DeploymentConfig {
  repoUrl: string;
  track: DeploymentTrack;
  budget: number;
  environment?: 'development' | 'staging' | 'production';
}

export type DeploymentTrack = 
  | 'auto-detect' 
  | 'capacitor' 
  | 'flutter' 
  | 'web' 
  | 'api' 
  | 'fullstack';

export interface DeploymentResult {
  success: boolean;
  url?: string;
  version?: string;
  error?: string;
  metrics: DeploymentMetrics;
}

export interface DeploymentMetrics {
  buildTime: number;
  testCoverage: number;
  securityScore: number;
  performanceScore: number;
}

// ============================================
// Validation Types
// ============================================

export interface ValidationResult {
  ok: boolean;
  reason?: string;
  warnings?: string[];
  score?: number;
}

export interface RouteDecision {
  track: DeploymentTrack;
  confidence: number;
  alternatives?: DeploymentTrack[];
  reasoning?: string;
}

export interface BuildPlan {
  estimate: number;
  frontend: BuildSpec;
  backend: BuildSpec;
  tests: TestSpec[];
  dependencies: string[];
}

export interface BuildSpec {
  framework: string;
  components: string[];
  apis: string[];
  features: string[];
}

export interface TestSpec {
  type: 'unit' | 'integration' | 'e2e' | 'security';
  coverage: number;
  priority: 'high' | 'medium' | 'low';
}

// ============================================
// Guardian Types
// ============================================

export interface VerificationResult {
  decision: 'GO' | 'NO-GO' | 'REVIEW';
  score: number;
  syntax: number;
  logic: number;
  security: number;
  issues: Issue[];
}

export interface Issue {
  severity: 'critical' | 'high' | 'medium' | 'low';
  category: 'syntax' | 'logic' | 'security' | 'performance';
  message: string;
  location?: string;
  suggestion?: string;
}

// ============================================
// Bridge Types
// ============================================

export interface BridgeMessage {
  id: string;
  type: BridgeMessageType;
  from: string;
  to?: string;
  timestamp: string;
  payload: Record<string, unknown>;
}

export type BridgeMessageType = 
  | 'handshake' 
  | 'heartbeat' 
  | 'task' 
  | 'result' 
  | 'error' 
  | 'status';

export interface BridgeStatus {
  bridge_id: string;
  handle: string;
  zo_url: string;
  space_url: string;
  model: string;
  status: AgentStatus;
  connected_nodes: string[];
  capabilities: Record<string, boolean>;
  projects: string[];
  last_heartbeat: string;
}

// ============================================
// Memory Types
// ============================================

export interface MemoryEntry {
  id: string;
  agent: string;
  type: 'pattern' | 'decision' | 'error' | 'success';
  timestamp: string;
  content: string;
  metadata?: Record<string, unknown>;
}

export interface DeploymentHistory {
  id: string;
  repoUrl: string;
  track: DeploymentTrack;
  status: 'success' | 'failed' | 'rolled-back';
  timestamp: string;
  duration: number;
  agentStates: AgentState[];
  lessons: string[];
}

// ============================================
// Error Types
// ============================================

export class EliteSquadError extends Error {
  constructor(
    message: string,
    public code: string,
    public agent?: string,
    public recoverable: boolean = true
  ) {
    super(message);
    this.name = 'EliteSquadError';
  }
}

export class ValidationError extends EliteSquadError {
  constructor(message: string, agent?: string) {
    super(message, 'VALIDATION_ERROR', agent, true);
    this.name = 'ValidationError';
  }
}

export class BudgetExceededError extends EliteSquadError {
  constructor(current: number, limit: number) {
    super(
      `Budget exceeded: ${current}/${limit}`,
      'BUDGET_EXCEEDED',
      'captain',
      false
    );
    this.name = 'BudgetExceededError';
  }
}

export class BridgeConnectionError extends EliteSquadError {
  constructor(endpoint: string, reason: string) {
    super(
      `Bridge connection failed: ${endpoint} - ${reason}`,
      'BRIDGE_CONNECTION_ERROR',
      'bridge',
      true
    );
    this.name = 'BridgeConnectionError';
  }
}
