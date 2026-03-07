// Swarm coordination and orchestration

use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use serde::{Serialize, Deserialize};

/// Swarm role
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum SwarmRole {
    /// Regular worker
    Worker,
    /// Coordinator (elected)
    Coordinator,
    /// Gateway to external systems
    Gateway,
    /// Bootstrap node
    Bootstrap,
}

/// Node information in the swarm
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SwarmNode {
    /// Node ID
    pub id: String,
    /// Node role
    pub role: SwarmRole,
    /// Node capabilities
    pub capabilities: u32,
    /// Last seen timestamp
    pub last_seen: u64,
    /// Load factor (0-100)
    pub load: u8,
    /// Tasks completed
    pub tasks_completed: u64,
    /// Reputation score
    pub reputation: u32,
}

/// Swarm topology
#[derive(Debug, Clone, Default)]
pub struct SwarmTopology {
    /// Nodes in the swarm
    pub nodes: HashMap<String, SwarmNode>,
    /// Swarm age (seconds)
    pub age_secs: u64,
    /// Total tasks completed
    pub total_tasks: u64,
    /// Average load
    pub avg_load: f32,
}

/// Swarm coordinator
pub struct SwarmCoordinator {
    node_id: String,
    topology: Arc<RwLock<SwarmTopology>>,
    role: Arc<RwLock<SwarmRole>>,
}

impl SwarmCoordinator {
    /// Create new swarm coordinator
    pub fn new(node_id: String) -> Self {
        Self {
            node_id,
            topology: Arc::new(RwLock::new(SwarmTopology::default())),
            role: Arc::new(RwLock::new(SwarmRole::Worker)),
        }
    }

    /// Join the swarm
    pub async fn join(&self, bootstrap: Option<String>) -> Result<(), SwarmError> {
        // Register with bootstrap or discover peers
        if let Some(bootstrap_addr) = bootstrap {
            log::info!("Joining swarm via bootstrap: {}", bootstrap_addr);
            // Connect to bootstrap
        } else {
            log::info!("Starting new swarm as bootstrap");
            // Become bootstrap node
            let mut role = self.role.write().await;
            *role = SwarmRole::Bootstrap;
        }

        Ok(())
    }

    /// Update node info
    pub async fn update_node(&self, node: SwarmNode) {
        let mut topology = self.topology.write().await;
        topology.nodes.insert(node.id.clone(), node);

        // Clean up stale nodes
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs();

        topology.nodes.retain(|_, n| now - n.last_seen < 300); // 5 min timeout
    }

    /// Get optimal node for task
    pub async fn get_optimal_node(&self, required_capabilities: u32) -> Option<String> {
        let topology = self.topology.read().await;

        topology.nodes
            .values()
            .filter(|n| n.capabilities & required_capabilities == required_capabilities)
            .filter(|n| n.load < 80) // Not overloaded
            .min_by_key(|n| n.load)
            .map(|n| n.id.clone())
    }

    /// Get swarm statistics
    pub async fn stats(&self) -> SwarmStats {
        let topology = self.topology.read().await;

        SwarmStats {
            total_nodes: topology.nodes.len(),
            workers: topology.nodes.values().filter(|n| n.role == SwarmRole::Worker).count(),
            gateways: topology.nodes.values().filter(|n| n.role == SwarmRole::Gateway).count(),
            coordinators: topology.nodes.values().filter(|n| n.role == SwarmRole::Coordinator).count(),
            total_tasks: topology.total_tasks,
            avg_load: topology.avg_load,
        }
    }
}

/// Swarm statistics
#[derive(Debug, Clone)]
pub struct SwarmStats {
    pub total_nodes: usize,
    pub workers: usize,
    pub gateways: usize,
    pub coordinators: usize,
    pub total_tasks: u64,
    pub avg_load: f32,
}

/// Swarm errors
#[derive(Debug, thiserror::Error)]
pub enum SwarmError {
    #[error("Failed to join swarm: {0}")]
    JoinFailed(String),

    #[error("No coordinator available")]
    NoCoordinator,

    #[error("Topology error: {0}")]
    TopologyError(String),
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_swarm_coordinator() {
        let coordinator = SwarmCoordinator::new("node1".to_string());

        // Add nodes
        coordinator.update_node(SwarmNode {
            id: "node2".to_string(),
            role: SwarmRole::Worker,
            capabilities: 0xFF,
            last_seen: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
            load: 50,
            tasks_completed: 100,
            reputation: 80,
        }).await;

        let stats = coordinator.stats().await;
        assert_eq!(stats.total_nodes, 1);
        assert_eq!(stats.workers, 1);
    }
}
