// Lightweight Raft Consensus for Distributed Agreement
// Optimized for <100MB RAM environments

use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::{mpsc, RwLock};
use serde::{Serialize, Deserialize};

/// Raft node states
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum RaftState {
    Follower,
    Candidate,
    Leader,
}

/// Raft configuration
#[derive(Debug, Clone)]
pub struct RaftConfig {
    /// Election timeout min (ms)
    pub election_timeout_min_ms: u64,
    /// Election timeout max (ms)
    pub election_timeout_max_ms: u64,
    /// Heartbeat interval (ms)
    pub heartbeat_interval_ms: u64,
    /// Max log entries per snapshot
    pub max_log_entries: usize,
}

impl Default for RaftConfig {
    fn default() -> Self {
        Self {
            election_timeout_min_ms: 150,
            election_timeout_max_ms: 300,
            heartbeat_interval_ms: 50,
            max_log_entries: 1000,
        }
    }
}

/// Log entry
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogEntry {
    pub term: u64,
    pub index: u64,
    pub command: Vec<u8>,
}

/// Raft RPC messages
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RaftMessage {
    /// Request vote
    RequestVote {
        term: u64,
        candidate_id: String,
        last_log_index: u64,
        last_log_term: u64,
    },

    /// Vote response
    RequestVoteResponse {
        term: u64,
        vote_granted: bool,
    },

    /// Append entries (heartbeat or log replication)
    AppendEntries {
        term: u64,
        leader_id: String,
        prev_log_index: u64,
        prev_log_term: u64,
        entries: Vec<LogEntry>,
        leader_commit: u64,
    },

    /// Append entries response
    AppendEntriesResponse {
        term: u64,
        success: bool,
        match_index: u64,
    },

    /// Client request
    ClientRequest {
        command: Vec<u8>,
    },

    /// Client response
    ClientResponse {
        success: bool,
        result: Option<Vec<u8>>,
    },
}

/// Raft node
pub struct RaftNode {
    /// Node ID
    id: String,
    /// Current state
    state: Arc<RwLock<RaftState>>,
    /// Current term
    current_term: Arc<RwLock<u64>>,
    /// Voted for in current term
    voted_for: Arc<RwLock<Option<String>>>,
    /// Log entries
    log: Arc<RwLock<Vec<LogEntry>>>,
    /// Commit index
    commit_index: Arc<RwLock<u64>>,
    /// Last applied
    last_applied: Arc<RwLock<u64>>,
    /// Next index for each peer (leader only)
    next_index: Arc<RwLock<HashMap<String, u64>>>,
    /// Match index for each peer (leader only)
    match_index: Arc<RwLock<HashMap<String, u64>>>,
    /// Peers in the cluster
    peers: Vec<String>,
    /// Configuration
    config: RaftConfig,
    /// Last heartbeat received
    last_heartbeat: Arc<RwLock<Instant>>,
    /// Message channels
    tx: mpsc::Sender<RaftMessage>,
    rx: mpsc::Receiver<RaftMessage>,
    /// State machine apply callback
    apply_callback: Box<dyn Fn(&[u8]) -> Vec<u8> + Send + Sync>,
}

impl RaftNode {
    pub fn new(
        id: String,
        peers: Vec<String>,
        config: RaftConfig,
        apply_callback: Box<dyn Fn(&[u8]) -> Vec<u8> + Send + Sync>,
    ) -> Self {
        let (tx, rx) = mpsc::channel(100);

        Self {
            id,
            state: Arc::new(RwLock::new(RaftState::Follower)),
            current_term: Arc::new(RwLock::new(0)),
            voted_for: Arc::new(RwLock::new(None)),
            log: Arc::new(RwLock::new(vec![])),
            commit_index: Arc::new(RwLock::new(0)),
            last_applied: Arc::new(RwLock::new(0)),
            next_index: Arc::new(RwLock::new(HashMap::new())),
            match_index: Arc::new(RwLock::new(HashMap::new())),
            peers,
            config,
            last_heartbeat: Arc::new(RwLock::new(Instant::now())),
            tx,
            rx,
            apply_callback,
        }
    }

    /// Start the Raft node
    pub async fn start(&mut self) {
        // Start election timer
        self.start_election_timer().await;

        // Start message processor
        self.start_message_processor().await;

        // Start heartbeat sender (if leader)
        self.start_heartbeat_sender().await;

        // Start log applier
        self.start_log_applier().await;
    }

    /// Start election timer
    async fn start_election_timer(&self) {
        let state = self.state.clone();
        let current_term = self.current_term.clone();
        let voted_for = self.voted_for.clone();
        let id = self.id.clone();
        let peers = self.peers.clone();
        let tx = self.tx.clone();
        let last_heartbeat = self.last_heartbeat.clone();
        let config = self.config.clone();
        let log = self.log.clone();

        tokio::spawn(async move {
            use rand::Rng;
            let mut rng = rand::thread_rng();

            loop {
                let timeout = rng.gen_range(
                    config.election_timeout_min_ms..config.election_timeout_max_ms
                );

                tokio::time::sleep(Duration::from_millis(timeout)).await;

                let state_guard = state.read().await;
                if *state_guard != RaftState::Leader {
                    // Check if heartbeat received
                    let last = last_heartbeat.read().await;
                    if last.elapsed().as_millis() as u64 > timeout {
                        drop(state_guard);
                        drop(last);

                        // Start election
                        start_election(
                            &id, &peers, &state, &current_term, &voted_for, &tx, &log
                        ).await;
                    }
                }
            }
        });
    }

    /// Start message processor
    async fn start_message_processor(&mut self) {
        let mut rx = self.rx.resubscribe();
        let id = self.id.clone();
        let state = self.state.clone();
        let current_term = self.current_term.clone();
        let voted_for = self.voted_for.clone();
        let log = self.log.clone();
        let commit_index = self.commit_index.clone();
        let last_heartbeat = self.last_heartbeat.clone();
        let next_index = self.next_index.clone();
        let match_index = self.match_index.clone();
        let peers = self.peers.clone();
        let tx = self.tx.clone();

        tokio::spawn(async move {
            while let Some(msg) = rx.recv().await {
                match msg {
                    RaftMessage::RequestVote { term, candidate_id, last_log_index, last_log_term } => {
                        let mut current_term_guard = current_term.write().await;
                        let mut state_guard = state.write().await;
                        let mut voted_for_guard = voted_for.write().await;

                        if term > *current_term_guard {
                            *current_term_guard = term;
                            *state_guard = RaftState::Follower;
                            *voted_for_guard = None;
                        }

                        let mut vote_granted = false;
                        if term >= *current_term_guard {
                            let can_vote = voted_for_guard.is_none() ||
                                          voted_for_guard.as_ref() == Some(&candidate_id);

                            if can_vote {
                                let log_guard = log.read().await;
                                let my_last_index = log_guard.len() as u64;
                                let my_last_term = log_guard.last()
                                    .map(|e| e.term)
                                    .unwrap_or(0);

                                let log_ok = last_log_term > my_last_term ||
                                    (last_log_term == my_last_term &&
                                     last_log_index >= my_last_index);

                                if log_ok {
                                    vote_granted = true;
                                    *voted_for_guard = Some(candidate_id.clone());
                                }
                            }
                        }

                        let response = RaftMessage::RequestVoteResponse {
                            term: *current_term_guard,
                            vote_granted,
                        };

                        // Send response (in real impl, would use transport)
                        log::debug!("Vote for {}: {}", candidate_id, vote_granted);
                    }

                    RaftMessage::RequestVoteResponse { term, vote_granted } => {
                        let mut current_term_guard = current_term.write().await;
                        let mut state_guard = state.write().await;

                        if term > *current_term_guard {
                            *current_term_guard = term;
                            *state_guard = RaftState::Follower;
                        } else if *state_guard == RaftState::Candidate && vote_granted {
                            // Count votes
                            log::debug!("Received vote for term {}", term);
                        }
                    }

                    RaftMessage::AppendEntries { term, leader_id, prev_log_index, prev_log_term, entries, leader_commit } => {
                        let mut current_term_guard = current_term.write().await;
                        let mut state_guard = state.write().await;
                        let mut last_heartbeat_guard = last_heartbeat.write().await;

                        *last_heartbeat_guard = Instant::now();

                        if term >= *current_term_guard {
                            *current_term_guard = term;
                            *state_guard = RaftState::Follower;

                            // Append entries logic
                            let mut log_guard = log.write().await;
                            // ... (full log replication logic)

                            let mut commit_guard = commit_index.write().await;
                            if leader_commit > *commit_guard {
                                *commit_guard = leader_commit.min(log_guard.len() as u64);
                            }
                        }
                    }

                    _ => {}
                }
            }
        });
    }

    /// Start heartbeat sender
    async fn start_heartbeat_sender(&self) {
        let state = self.state.clone();
        let id = self.id.clone();
        let tx = self.tx.clone();
        let config = self.config.clone();
        let current_term = self.current_term.clone();
        let log = self.log.clone();

        tokio::spawn(async move {
            let mut interval = tokio::time::interval(
                Duration::from_millis(config.heartbeat_interval_ms)
            );

            loop {
                interval.tick().await;

                let state_guard = state.read().await;
                if *state_guard == RaftState::Leader {
                    let term = *current_term.read().await;
                    let log_guard = log.read().await;
                    let last_index = log_guard.len() as u64;
                    let last_term = log_guard.last().map(|e| e.term).unwrap_or(0);

                    let heartbeat = RaftMessage::AppendEntries {
                        term,
                        leader_id: id.clone(),
                        prev_log_index: last_index,
                        prev_log_term: last_term,
                        entries: vec![], // Empty for heartbeat
                        leader_commit: 0,
                    };

                    // Send to all peers (in real impl)
                    log::debug!("Sending heartbeat for term {}", term);
                }
            }
        });
    }

    /// Start log applier
    async fn start_log_applier(&self) {
        let last_applied = self.last_applied.clone();
        let commit_index = self.commit_index.clone();
        let log = self.log.clone();
        let apply_callback = self.apply_callback.clone();

        tokio::spawn(async move {
            let mut interval = tokio::time::interval(Duration::from_millis(10));

            loop {
                interval.tick().await;

                let mut last_applied_guard = last_applied.write().await;
                let commit_guard = commit_index.read().await;
                let log_guard = log.read().await;

                while *last_applied_guard < *commit_guard {
                    *last_applied_guard += 1;
                    let index = *last_applied_guard as usize - 1;

                    if index < log_guard.len() {
                        let entry = &log_guard[index];
                        let _result = apply_callback(&entry.command);
                        log::debug!("Applied log entry {} (term {})", entry.index, entry.term);
                    }
                }
            }
        });
    }

    /// Propose a command (client interface)
    pub async fn propose(&self, command: Vec<u8>) -> Result<Vec<u8>, RaftError> {
        let state = self.state.read().await;
        if *state != RaftState::Leader {
            return Err(RaftError::NotLeader);
        }
        drop(state);

        // Add to log
        let mut log_guard = self.log.write().await;
        let term = *self.current_term.read().await;
        let index = log_guard.len() as u64 + 1;

        let entry = LogEntry {
            term,
            index,
            command,
        };

        log_guard.push(entry);
        log::debug!("Proposed entry at index {} (term {})", index, term);

        // Wait for commit (in real impl, would use oneshot channel)
        Ok(vec![])
    }

    /// Get current state
    pub async fn get_state(&self) -> RaftState {
        *self.state.read().await
    }

    /// Get current term
    pub async fn get_term(&self) -> u64 {
        *self.current_term.read().await
    }
}

/// Start election
async fn start_election(
    id: &str,
    peers: &[String],
    state: &Arc<RwLock<RaftState>>,
    current_term: &Arc<RwLock<u64>>,
    voted_for: &Arc<RwLock<Option<String>>>,
    tx: &mpsc::Sender<RaftMessage>,
    log: &Arc<RwLock<Vec<LogEntry>>>,
) {
    let mut state_guard = state.write().await;
    *state_guard = RaftState::Candidate;

    let mut current_term_guard = current_term.write().await;
    *current_term_guard += 1;

    let mut voted_for_guard = voted_for.write().await;
    *voted_for_guard = Some(id.to_string());

    let term = *current_term_guard;

    let log_guard = log.read().await;
    let last_log_index = log_guard.len() as u64;
    let last_log_term = log_guard.last().map(|e| e.term).unwrap_or(0);

    log::info!("Starting election for term {}", term);

    // Send RequestVote to all peers
    for peer in peers {
        let vote_request = RaftMessage::RequestVote {
            term,
            candidate_id: id.to_string(),
            last_log_index,
            last_log_term,
        };

        let _ = tx.send(vote_request).await;
    }
}

/// Raft errors
#[derive(Debug, thiserror::Error)]
pub enum RaftError {
    #[error("Not the leader")]
    NotLeader,

    #[error("Proposal failed: {0}")]
    ProposalFailed(String),

    #[error("Timeout")]
    Timeout,
}

/// Lightweight consensus for simple agreement
/// Uses gossip-based voting for efficiency
pub struct GossipConsensus {
    node_id: String,
    proposals: Arc<RwLock<HashMap<String, Proposal>>>,
    quorum: usize,
}

#[derive(Debug, Clone)]
struct Proposal {
    id: String,
    value: Vec<u8>,
    votes_for: HashMap<String, bool>,
    decided: bool,
}

impl GossipConsensus {
    pub fn new(node_id: String, quorum: usize) -> Self {
        Self {
            node_id,
            proposals: Arc::new(RwLock::new(HashMap::new())),
            quorum,
        }
    }

    /// Propose a value
    pub async fn propose(&self, proposal_id: String, value: Vec<u8>) {
        let mut proposals = self.proposals.write().await;
        proposals.insert(proposal_id.clone(), Proposal {
            id: proposal_id,
            value,
            votes_for: HashMap::new(),
            decided: false,
        });
    }

    /// Vote on a proposal
    pub async fn vote(&self, proposal_id: &str, voter: String, vote: bool) -> Option<bool> {
        let mut proposals = self.proposals.write().await;

        if let Some(proposal) = proposals.get_mut(proposal_id) {
            proposal.votes_for.insert(voter, vote);

            // Check if decided
            let votes_for = proposal.votes_for.values().filter(|&&v| v).count();
            let total_votes = proposal.votes_for.len();

            if votes_for >= self.quorum {
                proposal.decided = true;
                return Some(true);
            } else if total_votes - votes_for > self.quorum {
                // Too many no votes to reach quorum
                proposal.decided = true;
                return Some(false);
            }
        }

        None // Undecided
    }

    /// Get proposal status
    pub async fn get_status(&self, proposal_id: &str) -> Option<(bool, usize, usize)> {
        let proposals = self.proposals.read().await;
        proposals.get(proposal_id).map(|p| {
            let votes_for = p.votes_for.values().filter(|&&v| v).count();
            let total = p.votes_for.len();
            (p.decided, votes_for, total)
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_gossip_consensus() {
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            let consensus = GossipConsensus::new("node1".to_string(), 3);

            consensus.propose("prop1".to_string(), b"value1".to_vec()).await;

            // Vote
            let result = consensus.vote("prop1", "node1".to_string(), true).await;
            assert!(result.is_none()); // Not decided yet

            let result = consensus.vote("prop1", "node2".to_string(), true).await;
            assert!(result.is_none());

            let result = consensus.vote("prop1", "node3".to_string(), true).await;
            assert_eq!(result, Some(true)); // Decided!
        });
    }
}
