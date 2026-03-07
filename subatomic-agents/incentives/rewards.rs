// Reward distribution system

use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;

/// Reward configuration
#[derive(Debug, Clone)]
pub struct RewardConfig {
    /// Credits per work unit
    pub credits_per_unit: f64,
    /// Minimum payout threshold
    pub min_payout: f64,
    /// Payout interval (seconds)
    pub payout_interval: u64,
}

impl Default for RewardConfig {
    fn default() -> Self {
        Self {
            credits_per_unit: 0.001,
            min_payout: 10.0,
            payout_interval: 86400, // 24 hours
        }
    }
}

/// Reward system
pub struct RewardSystem {
    config: RewardConfig,
    balances: Arc<RwLock<HashMap<String, f64>>>,
    total_distributed: Arc<RwLock<f64>>,
}

impl RewardSystem {
    /// Create new reward system
    pub fn new(config: RewardConfig) -> Self {
        Self {
            config,
            balances: Arc::new(RwLock::new(HashMap::new())),
            total_distributed: Arc::new(RwLock::new(0.0)),
        }
    }

    /// Award credits to a node
    pub async fn award(&self, node_id: &str, work_units: u64) -> f64 {
        let credits = work_units as f64 * self.config.credits_per_unit;

        let mut balances = self.balances.write().await;
        let balance = balances.entry(node_id.to_string()).or_insert(0.0);
        *balance += credits;

        let mut total = self.total_distributed.write().await;
        *total += credits;

        credits
    }

    /// Get node balance
    pub async fn get_balance(&self, node_id: &str) -> f64 {
        let balances = self.balances.read().await;
        *balances.get(node_id).unwrap_or(&0.0)
    }

    /// Process payouts (call periodically)
    pub async fn process_payouts(&self) -> Vec<Payout> {
        let mut balances = self.balances.write().await;
        let mut payouts = vec![];

        for (node_id, balance) in balances.iter_mut() {
            if *balance >= self.config.min_payout {
                payouts.push(Payout {
                    node_id: node_id.clone(),
                    amount: *balance,
                    timestamp: std::time::SystemTime::now()
                        .duration_since(std::time::UNIX_EPOCH)
                        .unwrap()
                        .as_secs(),
                });
                *balance = 0.0;
            }
        }

        payouts
    }

    /// Get total distributed
    pub async fn get_total_distributed(&self) -> f64 {
        *self.total_distributed.read().await
    }
}

/// Payout record
#[derive(Debug, Clone)]
pub struct Payout {
    pub node_id: String,
    pub amount: f64,
    pub timestamp: u64,
}
