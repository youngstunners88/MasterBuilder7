// Gossip Protocol - Epidemic Broadcast for P2P Communication
// Bandwidth target: <10KB/sec per node

use std::collections::{HashMap, HashSet, VecDeque};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::{mpsc, RwLock};
use serde::{Serialize, Deserialize};
use sha2::{Sha256, Digest};

/// Maximum message size (1KB to fit in small packets)
const MAX_MESSAGE_SIZE: usize = 1024;

/// Gossip interval - how often to gossip
const GOSSIP_INTERVAL_MS: u64 = 500;

/// Fanout - how many peers to gossip to each round
const GOSSIP_FANOUT: usize = 3;

/// Message TTL - how many hops before dying
const DEFAULT_TTL: u8 = 10;

/// Message ID for deduplication
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct MessageId(pub String);

impl MessageId {
    pub fn new(data: &[u8]) -> Self {
        let mut hasher = Sha256::new();
        hasher.update(data);
        let result = hasher.finalize();
        Self(hex::encode(&result[..8])) // First 8 bytes = 16 hex chars
    }
}

/// Gossip message envelope
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GossipMessage {
    pub id: MessageId,
    pub sender: String,
    pub timestamp: u64,
    pub ttl: u8,
    pub payload: MessagePayload,
}

impl GossipMessage {
    pub fn new(sender: String, payload: MessagePayload) -> Self {
        let timestamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs();

        let id = MessageId::new(&serde_json::to_vec(&payload).unwrap_or_default());

        Self {
            id,
            sender,
            timestamp,
            ttl: DEFAULT_TTL,
            payload,
        }
    }

    pub fn decrement_ttl(mut self) -> Option<Self> {
        if self.ttl > 0 {
            self.ttl -= 1;
            Some(self)
        } else {
            None
        }
    }
}

/// Message payload types
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", content = "data")]
pub enum MessagePayload {
    /// Heartbeat for peer discovery
    Heartbeat {
        node_id: String,
        capabilities: u32,
        agents_count: u32,
    },

    /// Task announcement
    TaskAnnounce {
        task_id: String,
        task_type: String,
        required_capabilities: u32,
        reward_credits: u32,
    },

    /// Task result
    TaskResult {
        task_id: String,
        executor: String,
        success: bool,
        result_hash: String,
    },

    /// CRDT operation
    CrdtOp {
        crdt_id: String,
        operation: Vec<u8>, // Serialized CRDT operation
    },

    /// Consensus vote
    ConsensusVote {
        proposal_id: String,
        voter: String,
        vote: bool,
    },

    /// Reputation update
    ReputationUpdate {
        node_id: String,
        delta: i32,
        reason: String,
    },

    /// Custom application message
    Custom {
        app_id: String,
        data: Vec<u8>,
    },
}

/// Peer information
#[derive(Debug, Clone)]
pub struct PeerInfo {
    pub node_id: String,
    pub address: String,
    pub capabilities: u32,
    pub last_seen: Instant,
    pub agents_count: u32,
    pub reputation: i32,
}

impl PeerInfo {
    pub fn is_alive(&self) -> bool {
        self.last_seen.elapsed() < Duration::from_secs(30)
    }
}

/// Gossip protocol handler
pub struct GossipProtocol {
    node_id: String,
    peers: Arc<RwLock<HashMap<String, PeerInfo>>>,
    seen_messages: Arc<RwLock<HashSet<MessageId>>>,
    message_queue: Arc<RwLock<VecDeque<GossipMessage>>>,
    tx: mpsc::Sender<GossipMessage>,
    rx: mpsc::Receiver<GossipMessage>,
    bytes_sent: Arc<RwLock<u64>>,
    bytes_received: Arc<RwLock<u64>>,
}

impl GossipProtocol {
    pub fn new(node_id: String) -> Self {
        let (tx, rx) = mpsc::channel(1000);

        Self {
            node_id,
            peers: Arc::new(RwLock::new(HashMap::new())),
            seen_messages: Arc::new(RwLock::new(HashSet::new())),
            message_queue: Arc::new(RwLock::new(VecDeque::new())),
            tx,
            rx,
            bytes_sent: Arc::new(RwLock::new(0)),
            bytes_received: Arc::new(RwLock::new(0)),
        }
    }

    /// Start the gossip protocol
    pub async fn start(&self) {
        // Spawn gossip ticker
        let node_id = self.node_id.clone();
        let peers = self.peers.clone();
        let tx = self.tx.clone();
        let bytes_sent = self.bytes_sent.clone();

        tokio::spawn(async move {
            let mut interval = tokio::time::interval(Duration::from_millis(GOSSIP_INTERVAL_MS));

            loop {
                interval.tick().await;

                // Send heartbeat
                let heartbeat = GossipMessage::new(
                    node_id.clone(),
                    MessagePayload::Heartbeat {
                        node_id: node_id.clone(),
                        capabilities: 0xFF, // All capabilities
                        agents_count: 1,
                    }
                );

                // Gossip to random peers
                Self::gossip_message(&peers, &tx, &bytes_sent, heartbeat).await;
            }
        });

        // Spawn message processor
        let mut rx = self.rx.resubscribe();
        let seen_messages = self.seen_messages.clone();
        let message_queue = self.message_queue.clone();
        let peers = self.peers.clone();
        let bytes_received = self.bytes_received.clone();

        tokio::spawn(async move {
            while let Some(msg) = rx.recv().await {
                // Track bytes received
                {
                    let mut bytes = bytes_received.write().await;
                    *bytes += serde_json::to_vec(&msg).unwrap_or_default().len() as u64;
                }

                // Deduplicate
                {
                    let mut seen = seen_messages.write().await;
                    if seen.contains(&msg.id) {
                        continue;
                    }
                    seen.insert(msg.id.clone());

                    // Limit seen set size (LRU eviction)
                    if seen.len() > 10000 {
                        seen.clear(); // Simple clear, could be smarter
                    }
                }

                // Process message
                Self::process_message(&peers, &msg).await;

                // Add to queue for forwarding
                {
                    let mut queue = message_queue.write().await;
                    if let Some(msg_with_ttl) = msg.decrement_ttl() {
                        queue.push_back(msg_with_ttl);
                    }
                }
            }
        });

        // Spawn message forwarder
        let peers = self.peers.clone();
        let tx = self.tx.clone();
        let message_queue = self.message_queue.clone();
        let bytes_sent = self.bytes_sent.clone();

        tokio::spawn(async move {
            let mut interval = tokio::time::interval(Duration::from_millis(100));

            loop {
                interval.tick().await;

                let msg = {
                    let mut queue = message_queue.write().await;
                    queue.pop_front()
                };

                if let Some(msg) = msg {
                    Self::gossip_message(&peers, &tx, &bytes_sent, msg).await;
                }
            }
        });
    }

    /// Gossip a message to random peers
    async fn gossip_message(
        peers: &Arc<RwLock<HashMap<String, PeerInfo>>>,
        tx: &mpsc::Sender<GossipMessage>,
        bytes_sent: &Arc<RwLock<u64>>,
        msg: GossipMessage,
    ) {
        let peers_guard = peers.read().await;
        let alive_peers: Vec<_> = peers_guard
            .values()
            .filter(|p| p.is_alive())
            .collect();

        if alive_peers.is_empty() {
            return;
        }

        // Select random peers (fanout)
        use rand::seq::SliceRandom;
        let mut rng = rand::thread_rng();
        let selected: Vec<_> = alive_peers
            .choose_multiple(&mut rng, GOSSIP_FANOUT)
            .collect();

        drop(peers_guard);

        // Send to selected peers (in real impl, would use actual transport)
        for _peer in selected {
            let _ = tx.send(msg.clone()).await;

            // Track bytes
            let msg_bytes = serde_json::to_vec(&msg).unwrap_or_default().len() as u64;
            let mut bytes = bytes_sent.write().await;
            *bytes += msg_bytes;
        }
    }

    /// Process incoming message
    async fn process_message(
        peers: &Arc<RwLock<HashMap<String, PeerInfo>>>,
        msg: &GossipMessage,
    ) {
        match &msg.payload {
            MessagePayload::Heartbeat { node_id, capabilities, agents_count } => {
                let mut peers_guard = peers.write().await;
                peers_guard.insert(
                    node_id.clone(),
                    PeerInfo {
                        node_id: node_id.clone(),
                        address: "unknown".to_string(), // Would be from transport
                        capabilities: *capabilities,
                        last_seen: Instant::now(),
                        agents_count: *agents_count,
                        reputation: 0,
                    }
                );
            }
            MessagePayload::TaskAnnounce { task_id, task_type, required_capabilities, reward_credits } => {
                // Task announced - check if we can execute
                log::info!("Task announced: {} (type: {}, reward: {} credits)",
                    task_id, task_type, reward_credits);
            }
            MessagePayload::TaskResult { task_id, executor, success, result_hash } => {
                log::info!("Task result: {} by {} (success: {}, hash: {})",
                    task_id, executor, success, result_hash);
            }
            MessagePayload::CrdtOp { crdt_id, operation } => {
                // Forward to CRDT handler
                log::debug!("CRDT op for {}", crdt_id);
            }
            MessagePayload::ConsensusVote { proposal_id, voter, vote } => {
                log::debug!("Consensus vote: {} by {} = {}", proposal_id, voter, vote);
            }
            MessagePayload::ReputationUpdate { node_id, delta, reason } => {
                log::info!("Reputation update: {} delta {} ({})", node_id, delta, reason);
            }
            MessagePayload::Custom { app_id, data } => {
                log::debug!("Custom message for app {} ({} bytes)", app_id, data.len());
            }
        }
    }

    /// Broadcast a message to the network
    pub async fn broadcast(&self, payload: MessagePayload) -> Result<(), GossipError> {
        let msg = GossipMessage::new(self.node_id.clone(), payload);

        // Add to our seen set
        {
            let mut seen = self.seen_messages.write().await;
            seen.insert(msg.id.clone());
        }

        // Add to queue for forwarding
        {
            let mut queue = self.message_queue.write().await;
            queue.push_back(msg);
        }

        Ok(())
    }

    /// Get current peers
    pub async fn get_peers(&self) -> Vec<PeerInfo> {
        let peers = self.peers.read().await;
        peers.values().cloned().collect()
    }

    /// Get network statistics
    pub async fn get_stats(&self) -> NetworkStats {
        NetworkStats {
            peers_count: self.peers.read().await.len(),
            messages_seen: self.seen_messages.read().await.len(),
            bytes_sent: *self.bytes_sent.read().await,
            bytes_received: *self.bytes_received.read().await,
        }
    }
}

/// Network statistics
#[derive(Debug, Clone)]
pub struct NetworkStats {
    pub peers_count: usize,
    pub messages_seen: usize,
    pub bytes_sent: u64,
    pub bytes_received: u64,
}

/// Gossip errors
#[derive(Debug, thiserror::Error)]
pub enum GossipError {
    #[error("Broadcast failed: {0}")]
    BroadcastFailed(String),

    #[error("Invalid message: {0}")]
    InvalidMessage(String),
}

/// Plumtree - optimized gossip for large messages
/// Uses gossip for small metadata, direct transfer for large payloads
pub struct PlumtreeProtocol {
    gossip: GossipProtocol,
    // ... additional state for eager/lazy push
}

impl PlumtreeProtocol {
    /// Send large payload efficiently
    pub async fn send_large_payload(&self, _payload: &[u8], _recipients: &[String]) {
        // Announce via gossip (small)
        // Deliver via direct transfer (large)
        unimplemented!()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_message_id() {
        let data = b"test message";
        let id1 = MessageId::new(data);
        let id2 = MessageId::new(data);
        assert_eq!(id1, id2);
    }

    #[tokio::test]
    async fn test_gossip_broadcast() {
        let protocol = GossipProtocol::new("node1".to_string());
        protocol.start().await;

        let payload = MessagePayload::Heartbeat {
            node_id: "node1".to_string(),
            capabilities: 0xFF,
            agents_count: 1,
        };

        protocol.broadcast(payload).await.unwrap();

        let stats = protocol.get_stats().await;
        assert_eq!(stats.messages_seen, 1);
    }
}
