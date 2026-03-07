//! Sub-Atomic Agent Swarm
//! 
//! Enterprise-grade automation on ultra-low resources.
//! Runs 1000+ tiny agents on $5 Raspberry Pi Zeros and old smartphones.
//! 
//! # Architecture
//! 
//! ```text
//! ┌─────────────────────────────────────────────────────────────┐
//! │                    SUB-ATOMIC AGENT SWARM                    │
//! ├─────────────────────────────────────────────────────────────┤
//! │  Worker Agents (W)    Router Agents (R)    Storage (S)      │
//! │  ┌─────────────┐      ┌─────────────┐     ┌─────────────┐   │
//! │  │ Pi Zero     │◄────►│ Pi Zero     │◄───►│ Pi Zero     │   │
//! │  │ 512MB RAM   │      │ 512MB RAM   │     │ + SD Card   │   │
//! │  └─────────────┘      └─────────────┘     └─────────────┘   │
//! │         ▲                    ▲                    ▲         │
//! │         │   Gossip Protocol  │   CRDT Sync        │         │
//! │         ▼                    ▼                    ▼         │
//! │  ┌───────────────────────────────────────────────────────┐  │
//! │  │                    Mesh Network                        │  │
//! │  │    WiFi Direct ◄──► Bluetooth LE ◄──► LoRa           │  │
//! │  └───────────────────────────────────────────────────────┘  │
//! │                              │                              │
//! │                              ▼                              │
//! │  ┌───────────────────────────────────────────────────────┐  │
//! │  │              Gateway Nodes (Internet)                  │  │
//! │  │    Raspberry Pi 4 / Old Laptop / Cloud VM             │  │
//! │  └───────────────────────────────────────────────────────┘  │
//! │                              │                              │
//! │                              ▼                              │
//! │  ┌───────────────────────────────────────────────────────┐  │
//! │  │              iHhashi Food Delivery API                 │  │
//! │  └───────────────────────────────────────────────────────┘  │
//! └─────────────────────────────────────────────────────────────┘
//! ```
//! 
//! # Quick Start
//! 
//! ```rust,no_run
//! use subatomic_agents::core::agent::{WorkerAgent, AgentConfig, Task};
//! use subatomic_agents::protocols::gossip::GossipProtocol;
//! 
//! #[tokio::main]
//! async fn main() -> Result<(), Box<dyn std::error::Error>> {
//!     // Create worker agent
//!     let config = AgentConfig::default();
//!     let mut agent = WorkerAgent::new(config);
//!     
//!     // Initialize
//!     agent.initialize().await?;
//!     
//!     // Execute task
//!     let task = Task::new("echo", b"hello".to_vec());
//!     let result = agent.execute_task(task).await?;
//!     
//!     println!("Task result: {:?}", result);
//!     
//!     Ok(())
//! }
//! ```

#![warn(missing_docs)]
#![deny(unsafe_code)]

pub mod core {
    //! Core agent implementation
    
    pub mod agent;
    pub mod lifecycle;
    pub mod task;
    pub mod swarm;
}

pub mod protocols {
    //! Communication protocols
    
    pub mod gossip;
    pub mod crdt;
    pub mod message;
    pub mod routing;
}

pub mod networking {
    //! P2P networking layer
    
    pub mod mesh;
    pub mod transport;
    pub mod wifi_direct;
    pub mod bluetooth;
}

pub mod consensus {
    //! Distributed consensus
    
    pub mod raft;
    pub mod gossip_consensus;
    pub mod voting;
}

pub mod inference {
    //! Local LLM inference
    
    pub mod runtime;
    pub mod models;
    pub mod tasks;
}

pub mod incentives {
    //! Reputation and reward systems
    
    pub mod reputation;
    pub mod rewards;
    pub mod proof_of_work;
}

pub mod integration {
    //! Platform integrations
    
    pub mod ihhashi;
}

// Re-export commonly used types
pub use core::agent::{Agent, WorkerAgent, AgentConfig, AgentType, Task, TaskResult};
pub use protocols::gossip::GossipProtocol;
pub use networking::mesh::MeshNetwork;

/// Version of the subatomic-agents crate
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Minimum supported Rust version
pub const MIN_RUST_VERSION: &str = "1.70";

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_version() {
        assert!(!VERSION.is_empty());
    }
}
