// Gossip-based consensus (for simple agreement without full Raft)

use std::collections::HashMap;

/// Gossip consensus state
#[derive(Debug, Clone, Default)]
pub struct GossipConsensus {
    /// Current proposals
    proposals: HashMap<String, ProposalState>,
}

/// Proposal state
#[derive(Debug, Clone)]
pub struct ProposalState {
    pub id: String,
    pub value: Vec<u8>,
    pub votes_for: u32,
    pub votes_against: u32,
    pub decided: bool,
    pub accepted: bool,
}

impl GossipConsensus {
    /// Create new gossip consensus
    pub fn new() -> Self {
        Self {
            proposals: HashMap::new(),
        }
    }

    /// Propose a value
    pub fn propose(&mut self, id: String, value: Vec<u8>) {
        self.proposals.insert(id.clone(), ProposalState {
            id,
            value,
            votes_for: 0,
            votes_against: 0,
            decided: false,
            accepted: false,
        });
    }

    /// Vote on a proposal
    pub fn vote(&mut self, id: &str, accept: bool, quorum: u32) -> Option<bool> {
        if let Some(proposal) = self.proposals.get_mut(id) {
            if accept {
                proposal.votes_for += 1;
            } else {
                proposal.votes_against += 1;
            }

            // Check if decided
            if proposal.votes_for >= quorum {
                proposal.decided = true;
                proposal.accepted = true;
                return Some(true);
            } else if proposal.votes_against >= quorum {
                proposal.decided = true;
                proposal.accepted = false;
                return Some(false);
            }
        }

        None // Undecided
    }

    /// Get proposal status
    pub fn get_status(&self, id: &str) -> Option<&ProposalState> {
        self.proposals.get(id)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_gossip_consensus() {
        let mut consensus = GossipConsensus::new();

        consensus.propose("prop1".to_string(), b"value1".to_vec());

        // Vote
        assert!(consensus.vote("prop1", true, 3).is_none());
        assert!(consensus.vote("prop1", true, 3).is_none());
        assert_eq!(consensus.vote("prop1", true, 3), Some(true));

        let status = consensus.get_status("prop1").unwrap();
        assert!(status.decided);
        assert!(status.accepted);
    }
}
