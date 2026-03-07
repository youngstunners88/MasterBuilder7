// Sub-Atomic Agent - Core Agent Implementation
// Memory target: <50MB for worker agents

use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::{mpsc, RwLock};
use serde::{Serialize, Deserialize};
use uuid::Uuid;

/// Maximum memory target for worker agents (50MB)
const WORKER_MEMORY_TARGET_MB: usize = 50;

/// Maximum task execution time before forced termination
const MAX_TASK_DURATION: Duration = Duration::from_secs(60);

/// Agent types in the swarm
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AgentType {
    /// Execute single micro-tasks, ephemeral
    Worker,
    /// Route messages, maintain routing tables
    Router,
    /// Participate in consensus
    Consensus,
    /// Run local LLM inference
    Inference,
    /// Store CRDT data shards
    Storage,
}

/// Agent capabilities bitmask
#[derive(Debug, Clone, Copy, Default)]
pub struct Capabilities(u32);

impl Capabilities {
    const CAN_INFERENCE: u32 = 1 << 0;
    const CAN_STORAGE: u32 = 1 << 1;
    const CAN_CONSENSUS: u32 = 1 << 2;
    const CAN_ROUTE: u32 = 1 << 3;
    const HAS_INTERNET: u32 = 1 << 4;
    const HAS_LORA: u32 = 1 << 5;
    const HAS_BLUETOOTH: u32 = 1 << 6;

    pub fn new() -> Self {
        Self(0)
    }

    pub fn with_inference(mut self) -> Self {
        self.0 |= Self::CAN_INFERENCE;
        self
    }

    pub fn with_storage(mut self) -> Self {
        self.0 |= Self::CAN_STORAGE;
        self
    }

    pub fn with_internet(mut self) -> Self {
        self.0 |= Self::HAS_INTERNET;
        self
    }

    pub fn can_inference(&self) -> bool {
        self.0 & Self::CAN_INFERENCE != 0
    }

    pub fn has_internet(&self) -> bool {
        self.0 & Self::HAS_INTERNET != 0
    }
}

/// Unique agent identity
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct AgentId(pub String);

impl AgentId {
    pub fn new() -> Self {
        Self(Uuid::new_v4().to_string())
    }
}

impl Default for AgentId {
    fn default() -> Self {
        Self::new()
    }
}

/// Agent state
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AgentState {
    /// Just spawned, initializing
    Initializing,
    /// Ready to accept tasks
    Idle,
    /// Executing a task
    Executing,
    /// Shutting down
    Terminating,
    /// Dead, awaiting cleanup
    Dead,
}

/// Resource usage metrics
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ResourceMetrics {
    /// Memory usage in MB
    pub memory_mb: f32,
    /// CPU usage percentage
    pub cpu_percent: f32,
    /// Network bytes sent
    pub bytes_sent: u64,
    /// Network bytes received
    pub bytes_received: u64,
    /// Tasks executed
    pub tasks_executed: u32,
    /// Uptime in seconds
    pub uptime_secs: u64,
}

impl ResourceMetrics {
    /// Check if agent exceeds resource limits
    pub fn is_within_limits(&self) -> bool {
        self.memory_mb < WORKER_MEMORY_TARGET_MB as f32 && self.cpu_percent < 90.0
    }
}

/// Agent configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentConfig {
    pub agent_type: AgentType,
    pub mesh_id: String,
    pub bootstrap_peers: Vec<String>,
    pub max_tasks: u32,
    pub task_timeout_secs: u64,
    pub enable_metrics: bool,
}

impl Default for AgentConfig {
    fn default() -> Self {
        Self {
            agent_type: AgentType::Worker,
            mesh_id: "default".to_string(),
            bootstrap_peers: vec![],
            max_tasks: 1000,
            task_timeout_secs: 60,
            enable_metrics: true,
        }
    }
}

/// Task definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Task {
    pub id: String,
    pub task_type: String,
    pub payload: Vec<u8>,
    pub priority: u8,
    pub deadline: Option<u64>, // Unix timestamp
    pub required_capabilities: Capabilities,
}

impl Task {
    pub fn new(task_type: &str, payload: Vec<u8>) -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            task_type: task_type.to_string(),
            payload,
            priority: 5,
            deadline: None,
            required_capabilities: Capabilities::new(),
        }
    }
}

/// Task result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskResult {
    pub task_id: String,
    pub success: bool,
    pub result: Option<Vec<u8>>,
    pub error: Option<String>,
    pub execution_time_ms: u64,
}

/// Core agent trait - all agents implement this
#[async_trait::async_trait]
pub trait Agent: Send + Sync {
    /// Get agent ID
    fn id(&self) -> &AgentId;

    /// Get agent type
    fn agent_type(&self) -> AgentType;

    /// Get current state
    fn state(&self) -> AgentState;

    /// Get capabilities
    fn capabilities(&self) -> Capabilities;

    /// Initialize the agent
    async fn initialize(&mut self) -> Result<(), AgentError>;

    /// Execute a single task
    async fn execute_task(&mut self, task: Task) -> Result<TaskResult, AgentError>;

    /// Graceful shutdown
    async fn shutdown(&mut self) -> Result<(), AgentError>;

    /// Get current metrics
    fn metrics(&self) -> ResourceMetrics;
}

/// Agent errors
#[derive(Debug, thiserror::Error)]
pub enum AgentError {
    #[error("Initialization failed: {0}")]
    InitializationFailed(String),

    #[error("Task execution failed: {0}")]
    TaskExecutionFailed(String),

    #[error("Resource limit exceeded: {0}")]
    ResourceLimitExceeded(String),

    #[error("Network error: {0}")]
    NetworkError(String),

    #[error("Consensus failed: {0}")]
    ConsensusFailed(String),

    #[error("Timeout")]
    Timeout,

    #[error("Invalid task: {0}")]
    InvalidTask(String),
}

/// Worker agent implementation - ephemeral, single-task
pub struct WorkerAgent {
    id: AgentId,
    state: Arc<RwLock<AgentState>>,
    config: AgentConfig,
    metrics: Arc<RwLock<ResourceMetrics>>,
    start_time: Instant,
}

impl WorkerAgent {
    pub fn new(config: AgentConfig) -> Self {
        Self {
            id: AgentId::new(),
            state: Arc::new(RwLock::new(AgentState::Initializing)),
            config,
            metrics: Arc::new(RwLock::new(ResourceMetrics::default())),
            start_time: Instant::now(),
        }
    }

    /// Check if this agent can handle a task
    pub fn can_handle(&self, task: &Task) -> bool {
        // Check capabilities
        let caps = self.capabilities();
        let required = &task.required_capabilities;

        // Check deadline
        if let Some(deadline) = task.deadline {
            let now = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs();
            if now > deadline {
                return false;
            }
        }

        true
    }

    /// Update metrics
    async fn update_metrics(&self) {
        let mut metrics = self.metrics.write().await;
        metrics.uptime_secs = self.start_time.elapsed().as_secs();

        // Get memory usage (Linux-specific, works on Pi)
        #[cfg(target_os = "linux")]
        {
            if let Ok(status) = std::fs::read_to_string("/proc/self/status") {
                for line in status.lines() {
                    if line.starts_with("VmRSS:") {
                        let parts: Vec<&str> = line.split_whitespace().collect();
                        if parts.len() >= 2 {
                            if let Ok(kb) = parts[1].parse::<f32>() {
                                metrics.memory_mb = kb / 1024.0;
                            }
                        }
                        break;
                    }
                }
            }
        }
    }
}

#[async_trait::async_trait]
impl Agent for WorkerAgent {
    fn id(&self) -> &AgentId {
        &self.id
    }

    fn agent_type(&self) -> AgentType {
        AgentType::Worker
    }

    fn state(&self) -> AgentState {
        // Read lock - this is quick
        if let Ok(state) = self.state.try_read() {
            *state
        } else {
            AgentState::Executing // Likely executing if locked
        }
    }

    fn capabilities(&self) -> Capabilities {
        Capabilities::new().with_internet() // Assume internet for now
    }

    async fn initialize(&mut self) -> Result<(), AgentError> {
        let mut state = self.state.write().await;
        *state = AgentState::Idle;
        Ok(())
    }

    async fn execute_task(&mut self, task: Task) -> Result<TaskResult, AgentError> {
        // Set state to executing
        {
            let mut state = self.state.write().await;
            *state = AgentState::Executing;
        }

        let start = Instant::now();

        // Check resource limits before starting
        self.update_metrics().await;
        let metrics = self.metrics.read().await;
        if !metrics.is_within_limits() {
            return Err(AgentError::ResourceLimitExceeded(
                format!("Memory: {:.1}MB", metrics.memory_mb)
            ));
        }
        drop(metrics);

        // Execute with timeout
        let result = tokio::time::timeout(
            Duration::from_secs(self.config.task_timeout_secs),
            execute_task_internal(&task)
        ).await;

        let execution_time_ms = start.elapsed().as_millis() as u64;

        // Update metrics
        {
            let mut metrics = self.metrics.write().await;
            metrics.tasks_executed += 1;
        }

        // Set state back to idle or dead
        {
            let mut state = self.state.write().await;
            *state = AgentState::Dead; // Workers die after one task
        }

        match result {
            Ok(Ok(output)) => Ok(TaskResult {
                task_id: task.id,
                success: true,
                result: Some(output),
                error: None,
                execution_time_ms,
            }),
            Ok(Err(e)) => Ok(TaskResult {
                task_id: task.id,
                success: false,
                result: None,
                error: Some(e.to_string()),
                execution_time_ms,
            }),
            Err(_) => Ok(TaskResult {
                task_id: task.id,
                success: false,
                result: None,
                error: Some("Task timeout".to_string()),
                execution_time_ms,
                }),
        }
    }

    async fn shutdown(&mut self) -> Result<(), AgentError> {
        let mut state = self.state.write().await;
        *state = AgentState::Terminating;
        // Worker agents just die immediately
        *state = AgentState::Dead;
        Ok(())
    }

    fn metrics(&self) -> ResourceMetrics {
        if let Ok(metrics) = self.metrics.try_read() {
            metrics.clone()
        } else {
            ResourceMetrics::default()
        }
    }
}

/// Internal task execution - replace with actual task handlers
async fn execute_task_internal(task: &Task) -> Result<Vec<u8>, AgentError> {
    match task.task_type.as_str() {
        "echo" => {
            // Simple echo task for testing
            Ok(task.payload.clone())
        }
        "validate_order" => {
            // Validate order structure
            validate_order(&task.payload).await
        }
        "calculate_eta" => {
            // Calculate ETA using route memory
            calculate_eta(&task.payload).await
        }
        "check_inventory" => {
            // Check if items are in stock
            check_inventory(&task.payload).await
        }
        _ => Err(AgentError::InvalidTask(
            format!("Unknown task type: {}", task.task_type)
        )),
    }
}

// Placeholder task handlers - implement actual logic
async fn validate_order(payload: &[u8]) -> Result<Vec<u8>, AgentError> {
    // Deserialize order, validate, return result
    Ok(vec![1]) // Success
}

async fn calculate_eta(payload: &[u8]) -> Result<Vec<u8>, AgentError> {
    // Use route memory to calculate ETA
    Ok(vec![15, 0, 0, 0]) // 15 minutes as u32
}

async fn check_inventory(payload: &[u8]) -> Result<Vec<u8>, AgentError> {
    // Check inventory CRDT
    Ok(vec![1]) // In stock
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_worker_agent_lifecycle() {
        let config = AgentConfig::default();
        let mut agent = WorkerAgent::new(config);

        assert_eq!(agent.state(), AgentState::Initializing);

        agent.initialize().await.unwrap();
        assert_eq!(agent.state(), AgentState::Idle);

        let task = Task::new("echo", b"hello".to_vec());
        let result = agent.execute_task(task).await.unwrap();

        assert!(result.success);
        assert_eq!(result.result, Some(b"hello".to_vec()));
        assert_eq!(agent.state(), AgentState::Dead);
    }

    #[test]
    fn test_capabilities() {
        let caps = Capabilities::new()
            .with_inference()
            .with_internet();

        assert!(caps.can_inference());
        assert!(caps.has_internet());
    }
}
