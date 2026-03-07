// Reputation and Incentive System for Sub-Atomic Agents
// Proof-of-work, proof-of-contribution, and reputation scoring

use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use serde::{Serialize, Deserialize};
use sha2::{Sha256, Digest};

/// Reputation score for a node
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Reputation {
    pub node_id: String,
    /// Base reputation score (0-100)
    pub score: u32,
    /// Tasks completed successfully
    pub tasks_completed: u64,
    /// Tasks failed
    pub tasks_failed: u64,
    /// Total work contributed (in compute units)
    pub work_contributed: u64,
    /// Uptime percentage (0-100)
    pub uptime_percent: f32,
    /// Peer endorsements
    pub endorsements: u32,
    /// Peer reports (negative)
    pub reports: u32,
    /// Join timestamp
    pub joined_at: u64,
    /// Last active timestamp
    pub last_active: u64,
    /// Verification level
    pub verification_level: VerificationLevel,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum VerificationLevel {
    Unverified = 0,
    Basic = 1,
    Verified = 2,
    Trusted = 3,
}

impl Default for Reputation {
    fn default() -> Self {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs();

        Self {
            node_id: String::new(),
            score: 50, // Start at neutral
            tasks_completed: 0,
            tasks_failed: 0,
            work_contributed: 0,
            uptime_percent: 0.0,
            endorsements: 0,
            reports: 0,
            joined_at: now,
            last_active: now,
            verification_level: VerificationLevel::Unverified,
        }
    }
}

impl Reputation {
    /// Calculate effective reputation
    pub fn effective_score(&self) -> u32 {
        let base = self.score;

        // Bonus for verification
        let verification_bonus = match self.verification_level {
            VerificationLevel::Unverified => 0,
            VerificationLevel::Basic => 10,
            VerificationLevel::Verified => 20,
            VerificationLevel::Trusted => 30,
        };

        // Penalty for high failure rate
        let total_tasks = self.tasks_completed + self.tasks_failed;
        let reliability_factor = if total_tasks > 0 {
            self.tasks_completed as f32 / total_tasks as f32
        } else {
            0.5
        };

        let adjusted = (base + verification_bonus) as f32 * reliability_factor;
        adjusted.min(100.0).max(0.0) as u32
    }

    /// Check if node can be trusted for critical tasks
    pub fn is_trusted(&self) -> bool {
        self.effective_score() >= 70 && self.verification_level as u8 >= VerificationLevel::Verified as u8
    }
}

/// Reputation system
pub struct ReputationSystem {
    reputations: Arc<RwLock<HashMap<String, Reputation>>>,
    /// Minimum reputation to participate
    min_reputation: u32,
    /// Reputation decay rate (per day)
    decay_rate: f32,
}

impl ReputationSystem {
    pub fn new(min_reputation: u32, decay_rate: f32) -> Self {
        Self {
            reputations: Arc::new(RwLock::new(HashMap::new())),
            min_reputation,
            decay_rate,
        }
    }

    /// Get or create reputation for a node
    pub async fn get_reputation(&self, node_id: &str) -> Reputation {
        let reputations = self.reputations.read().await;
        reputations.get(node_id).cloned().unwrap_or_else(|| {
            let mut rep = Reputation::default();
            rep.node_id = node_id.to_string();
            rep
        })
    }

    /// Update reputation for task completion
    pub async fn record_task_completion(&self, node_id: &str, success: bool, work_units: u64) {
        let mut reputations = self.reputations.write().await;
        let rep = reputations.entry(node_id.to_string()).or_insert_with(|| {
            let mut r = Reputation::default();
            r.node_id = node_id.to_string();
            r
        });

        if success {
            rep.tasks_completed += 1;
            rep.score = (rep.score + 1).min(100);
            rep.work_contributed += work_units;
        } else {
            rep.tasks_failed += 1;
            rep.score = rep.score.saturating_sub(5);
        }

        rep.last_active = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs();
    }

    /// Endorse a node (positive reputation)
    pub async fn endorse(&self, from_node: &str, to_node: &str) -> Result<(), ReputationError> {
        let from_rep = self.get_reputation(from_node).await;

        // Only trusted nodes can endorse
        if !from_rep.is_trusted() {
            return Err(ReputationError::InsufficientReputation);
        }

        let mut reputations = self.reputations.write().await;
        let rep = reputations.entry(to_node.to_string()).or_insert_with(|| {
            let mut r = Reputation::default();
            r.node_id = to_node.to_string();
            r
        });

        rep.endorsements += 1;
        rep.score = (rep.score + 2).min(100);

        Ok(())
    }

    /// Report a node (negative reputation)
    pub async fn report(&self, from_node: &str, to_node: &str, reason: &str) -> Result<(), ReputationError> {
        let from_rep = self.get_reputation(from_node).await;

        // Need some reputation to report
        if from_rep.effective_score() < 30 {
            return Err(ReputationError::InsufficientReputation);
        }

        let mut reputations = self.reputations.write().await;
        let rep = reputations.entry(to_node.to_string()).or_insert_with(|| {
            let mut r = Reputation::default();
            r.node_id = to_node.to_string();
            r
        });

        rep.reports += 1;
        rep.score = rep.score.saturating_sub(10);

        log::warn!("Node {} reported by {}: {}", to_node, from_node, reason);

        Ok(())
    }

    /// Get top nodes by reputation
    pub async fn get_top_nodes(&self, n: usize) -> Vec<Reputation> {
        let reputations = self.reputations.read().await;
        let mut reps: Vec<_> = reputations.values().cloned().collect();
        reps.sort_by(|a, b| b.effective_score().cmp(&a.effective_score()));
        reps.into_iter().take(n).collect()
    }

    /// Check if node meets minimum reputation
    pub async fn is_qualified(&self, node_id: &str) -> bool {
        let rep = self.get_reputation(node_id).await;
        rep.effective_score() >= self.min_reputation
    }
}

/// Reputation errors
#[derive(Debug, thiserror::Error)]
pub enum ReputationError {
    #[error("Insufficient reputation")]
    InsufficientReputation,

    #[error("Node not found")]
    NodeNotFound,
}

/// Lightweight proof-of-work for spam prevention
pub struct LightPoW {
    /// Difficulty level (number of leading zeros required)
    difficulty: u8,
}

impl LightPoW {
    pub fn new(difficulty: u8) -> Self {
        Self { difficulty }
    }

    /// Generate challenge
    pub fn generate_challenge(&self) -> Vec<u8> {
        let mut challenge = vec![0u8; 32];
        rand::fill(&mut challenge[..]);
        challenge
    }

    /// Solve challenge (find nonce)
    pub fn solve(&self, challenge: &[u8]) -> (u64, Vec<u8>) {
        let mut nonce: u64 = 0;

        loop {
            let hash = self.hash(challenge, nonce);

            if self.check_hash(&hash) {
                return (nonce, hash);
            }

            nonce += 1;
        }
    }

    /// Verify solution
    pub fn verify(&self, challenge: &[u8], nonce: u64, hash: &[u8]) -> bool {
        let expected = self.hash(challenge, nonce);
        expected == hash && self.check_hash(hash)
    }

    /// Hash challenge + nonce
    fn hash(&self, challenge: &[u8], nonce: u64) -> Vec<u8> {
        let mut hasher = Sha256::new();
        hasher.update(challenge);
        hasher.update(&nonce.to_le_bytes());
        hasher.finalize().to_vec()
    }

    /// Check if hash meets difficulty
    fn check_hash(&self, hash: &[u8]) -> bool {
        let required_zeros = (self.difficulty as usize + 7) / 8;

        if hash.len() < required_zeros {
            return false;
        }

        // Check full bytes
        for i in 0..(self.difficulty / 8) as usize {
            if hash[i] != 0 {
                return false;
            }
        }

        // Check partial byte
        let remaining = self.difficulty % 8;
        if remaining > 0 {
            let mask = 0xFFu8 << (8 - remaining);
            if hash[required_zeros - 1] & mask != 0 {
                return false;
            }
        }

        true
    }
}

/// Proof-of-contribution (for rewarding useful work)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContributionProof {
    pub node_id: String,
    pub task_id: String,
    pub task_type: String,
    pub work_units: u64,
    pub result_hash: String,
    pub timestamp: u64,
    pub signature: Vec<u8>,
}

impl ContributionProof {
    pub fn new(
        node_id: String,
        task_id: String,
        task_type: String,
        work_units: u64,
        result_hash: String,
    ) -> Self {
        let timestamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs();

        Self {
            node_id,
            task_id,
            task_type,
            work_units,
            result_hash,
            timestamp,
            signature: vec![], // Would be signed with node's key
        }
    }

    pub fn verify(&self) -> bool {
        // Verify signature
        // In production, would use ed25519 or similar
        !self.signature.is_empty()
    }
}

/// Reward system
pub struct RewardSystem {
    /// Credits per work unit
    credit_per_unit: f64,
    /// Total credits distributed
    total_distributed: Arc<RwLock<f64>>,
    /// Node balances
    balances: Arc<RwLock<HashMap<String, f64>>>,
}

impl RewardSystem {
    pub fn new(credit_per_unit: f64) -> Self {
        Self {
            credit_per_unit,
            total_distributed: Arc::new(RwLock::new(0.0)),
            balances: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Reward a node for contribution
    pub async fn reward(&self, proof: &ContributionProof, reputation: &Reputation) -> f64 {
        // Base reward
        let base_reward = proof.work_units as f64 * self.credit_per_unit;

        // Reputation multiplier
        let multiplier = 0.5 + (reputation.effective_score() as f64 / 100.0);

        // Verification bonus
        let verification_bonus = match reputation.verification_level {
            VerificationLevel::Unverified => 0.0,
            VerificationLevel::Basic => 0.1,
            VerificationLevel::Verified => 0.2,
            VerificationLevel::Trusted => 0.3,
        };

        let total_reward = base_reward * multiplier * (1.0 + verification_bonus);

        // Update balance
        let mut balances = self.balances.write().await;
        let balance = balances.entry(proof.node_id.clone()).or_insert(0.0);
        *balance += total_reward;

        // Update total distributed
        let mut total = self.total_distributed.write().await;
        *total += total_reward;

        total_reward
    }

    /// Get node balance
    pub async fn get_balance(&self, node_id: &str) -> f64 {
        let balances = self.balances.read().await;
        *balances.get(node_id).unwrap_or(&0.0)
    }

    /// Get total distributed
    pub async fn get_total_distributed(&self) -> f64 {
        *self.total_distributed.read().await
    }
}

/// iHhashi-specific: Rider reputation for delivery
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiderReputation {
    pub rider_id: String,
    pub deliveries_completed: u32,
    pub on_time_rate: f32,
    pub customer_rating: f32,
    pub earnings_zar: f64,
    pub badges: Vec<String>,
}

/// iHhashi-specific: Merchant reputation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MerchantReputation {
    pub merchant_id: String,
    pub orders_fulfilled: u32,
    pub avg_prep_time_minutes: f32,
    pub food_quality_score: f32,
    pub hygiene_rating: f32,
    pub blue_horse_verified: bool,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_light_pow() {
        let pow = LightPoW::new(8); // 1 leading zero byte

        let challenge = pow.generate_challenge();
        let (nonce, hash) = pow.solve(&challenge);

        assert!(pow.verify(&challenge, nonce, &hash));
        assert!(hash[0] == 0);
    }

    #[tokio::test]
    async fn test_reputation_system() {
        let system = ReputationSystem::new(30, 0.01);

        // Record some tasks
        system.record_task_completion("node1", true, 100).await;
        system.record_task_completion("node1", true, 100).await;
        system.record_task_completion("node1", false, 50).await;

        let rep = system.get_reputation("node1").await;
        assert_eq!(rep.tasks_completed, 2);
        assert_eq!(rep.tasks_failed, 1);

        // Check effective score
        let score = rep.effective_score();
        assert!(score > 0 && score <= 100);
    }

    #[tokio::test]
    async fn test_reward_system() {
        let rewards = RewardSystem::new(0.001);

        let reputation = Reputation {
            node_id: "node1".to_string(),
            score: 80,
            tasks_completed: 100,
            tasks_failed: 5,
            work_contributed: 10000,
            uptime_percent: 95.0,
            endorsements: 10,
            reports: 0,
            joined_at: 0,
            last_active: 0,
            verification_level: VerificationLevel::Verified,
        };

        let proof = ContributionProof::new(
            "node1".to_string(),
            "task1".to_string(),
            "compute".to_string(),
            1000,
            "abc123".to_string(),
        );

        let reward = rewards.reward(&proof, &reputation).await;
        assert!(reward > 0.0);

        let balance = rewards.get_balance("node1").await;
        assert_eq!(balance, reward);
    }
}
