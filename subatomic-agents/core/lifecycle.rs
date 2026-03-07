// Agent Lifecycle Management
// Handles spawn, execute, and death of ephemeral agents

use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::process::Command;
use tokio::sync::Semaphore;

/// Agent lifecycle states
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LifecycleState {
    /// Agent is being spawned
    Spawning,
    /// Agent is running and ready
    Running,
    /// Agent is executing a task
    Executing,
    /// Agent is shutting down
    ShuttingDown,
    /// Agent has died
    Dead,
}

/// Lifecycle manager for agent pools
pub struct LifecycleManager {
    /// Maximum concurrent agents
    max_concurrent: usize,
    /// Current active agents
    active_count: Arc<tokio::sync::RwLock<usize>>,
    /// Semaphore for controlling concurrency
    semaphore: Arc<Semaphore>,
    /// Agent spawn timeout
    spawn_timeout: Duration,
    /// Task execution timeout
    task_timeout: Duration,
}

impl LifecycleManager {
    /// Create new lifecycle manager
    pub fn new(max_concurrent: usize, task_timeout_secs: u64) -> Self {
        Self {
            max_concurrent,
            active_count: Arc::new(tokio::sync::RwLock::new(0)),
            semaphore: Arc::new(Semaphore::new(max_concurrent)),
            spawn_timeout: Duration::from_secs(5),
            task_timeout: Duration::from_secs(task_timeout_secs),
        }
    }

    /// Check if we can spawn a new agent
    pub async fn can_spawn(&self) -> bool {
        let active = *self.active_count.read().await;
        active < self.max_concurrent
    }

    /// Get current active agent count
    pub async fn active_count(&self) -> usize {
        *self.active_count.read().await
    }

    /// Acquire spawn permit
    pub async fn acquire_permit(&self) -> Option<tokio::sync::OwnedSemaphorePermit> {
        match self.semaphore.clone().acquire_owned().await {
            Ok(permit) => Some(permit),
            Err(_) => None,
        }
    }
}

/// Ephemeral agent handle
pub struct EphemeralAgent {
    /// Unique agent ID
    pub id: String,
    /// Process handle (if spawned as external process)
    pub process: Option<tokio::process::Child>,
    /// Spawn time
    pub spawned_at: Instant,
    /// Lifecycle state
    pub state: LifecycleState,
}

impl EphemeralAgent {
    /// Spawn a new ephemeral agent
    pub async fn spawn(id: String, binary_path: &str) -> Result<Self, LifecycleError> {
        let spawned_at = Instant::now();

        // Spawn external process (for isolation)
        let process = Command::new(binary_path)
            .arg(&id)
            .spawn()
            .map_err(|e| LifecycleError::SpawnFailed(e.to_string()))?;

        Ok(Self {
            id,
            process: Some(process),
            spawned_at,
            state: LifecycleState::Spawning,
        })
    }

    /// Spawn in-process agent (for embedded use)
    pub async fn spawn_in_process(id: String) -> Self {
        Self {
            id,
            process: None,
            spawned_at: Instant::now(),
            state: LifecycleState::Running,
        }
    }

    /// Check if agent is still alive
    pub async fn is_alive(&mut self) -> bool {
        if let Some(ref mut process) = self.process {
            match process.try_wait() {
                Ok(None) => true,  // Still running
                Ok(Some(_)) => false, // Exited
                Err(_) => false,
            }
        } else {
            self.state != LifecycleState::Dead
        }
    }

    /// Kill agent
    pub async fn kill(&mut self) -> Result<(), LifecycleError> {
        self.state = LifecycleState::ShuttingDown;

        if let Some(ref mut process) = self.process {
            process.kill().await
                .map_err(|e| LifecycleError::KillFailed(e.to_string()))?;
        }

        self.state = LifecycleState::Dead;
        Ok(())
    }

    /// Get uptime
    pub fn uptime(&self) -> Duration {
        self.spawned_at.elapsed()
    }
}

/// Lifecycle errors
#[derive(Debug, thiserror::Error)]
pub enum LifecycleError {
    #[error("Failed to spawn agent: {0}")]
    SpawnFailed(String),

    #[error("Failed to kill agent: {0}")]
    KillFailed(String),

    #[error("Agent timeout")]
    Timeout,

    #[error("Resource limit exceeded")]
    ResourceLimit,
}

/// Agent pool for managing multiple ephemeral agents
pub struct AgentPool {
    lifecycle: LifecycleManager,
    agents: Arc<tokio::sync::RwLock<Vec<EphemeralAgent>>>,
}

impl AgentPool {
    pub fn new(max_concurrent: usize, task_timeout_secs: u64) -> Self {
        Self {
            lifecycle: LifecycleManager::new(max_concurrent, task_timeout_secs),
            agents: Arc::new(tokio::sync::RwLock::new(Vec::new())),
        }
    }

    /// Spawn a new agent in the pool
    pub async fn spawn(&self, binary_path: &str) -> Result<String, LifecycleError> {
        // Check if we can spawn
        if !self.lifecycle.can_spawn().await {
            return Err(LifecycleError::ResourceLimit);
        }

        let id = uuid::Uuid::new_v4().to_string();
        let mut agent = EphemeralAgent::spawn(id.clone(), binary_path).await?;

        // Add to pool
        let mut agents = self.agents.write().await;
        agents.push(agent);

        Ok(id)
    }

    /// Clean up dead agents
    pub async fn cleanup(&self) {
        let mut agents = self.agents.write().await;
        agents.retain_mut(|agent| {
            let alive = futures::executor::block_on(agent.is_alive());
            if !alive {
                log::debug!("Cleaning up dead agent: {}", agent.id);
            }
            alive
        });
    }

    /// Get pool statistics
    pub async fn stats(&self) -> PoolStats {
        let agents = self.agents.read().await;
        let active = agents.len();

        PoolStats {
            total_agents: active,
            max_agents: self.lifecycle.max_concurrent,
            utilization_percent: (active as f32 / self.lifecycle.max_concurrent as f32) * 100.0,
        }
    }
}

/// Pool statistics
#[derive(Debug, Clone)]
pub struct PoolStats {
    pub total_agents: usize,
    pub max_agents: usize,
    pub utilization_percent: f32,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_lifecycle_manager() {
        let manager = LifecycleManager::new(10, 60);
        assert!(manager.can_spawn().await);
        assert_eq!(manager.active_count().await, 0);
    }

    #[tokio::test]
    async fn test_agent_pool() {
        let pool = AgentPool::new(5, 60);
        let stats = pool.stats().await;
        assert_eq!(stats.total_agents, 0);
        assert_eq!(stats.max_agents, 5);
    }
}
