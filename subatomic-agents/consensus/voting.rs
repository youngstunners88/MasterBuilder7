// Voting mechanisms for distributed consensus

use std::collections::HashMap;

/// Vote record
#[derive(Debug, Clone)]
pub struct Vote {
    pub voter: String,
    pub vote: bool,
    pub timestamp: u64,
    pub weight: u32,
}

/// Weighted voting
pub struct WeightedVoting {
    votes: HashMap<String, Vec<Vote>>,
}

impl WeightedVoting {
    /// Create new weighted voting
    pub fn new() -> Self {
        Self {
            votes: HashMap::new(),
        }
    }

    /// Cast a vote
    pub fn vote(&mut self, proposal_id: String, vote: Vote) {
        self.votes
            .entry(proposal_id)
            .or_insert_with(Vec::new)
            .push(vote);
    }

    /// Tally votes for a proposal
    pub fn tally(&self, proposal_id: &str, quorum: u32) -> Option<VoteResult> {
        let votes = self.votes.get(proposal_id)?;

        let (total_for, total_against): (u32, u32) = votes.iter().fold(
            (0, 0),
            |(for_sum, against_sum), vote| {
                if vote.vote {
                    (for_sum + vote.weight, against_sum)
                } else {
                    (for_sum, against_sum + vote.weight)
                }
            }
        );

        let total = total_for + total_against;

        if total_for >= quorum {
            Some(VoteResult {
                accepted: true,
                total_votes: total,
                votes_for: total_for,
                votes_against: total_against,
            })
        } else if total_against >= quorum {
            Some(VoteResult {
                accepted: false,
                total_votes: total,
                votes_for: total_for,
                votes_against: total_against,
            })
        } else {
            None // Undecided
        }
    }
}

/// Vote result
#[derive(Debug, Clone)]
pub struct VoteResult {
    pub accepted: bool,
    pub total_votes: u32,
    pub votes_for: u32,
    pub votes_against: u32,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_weighted_voting() {
        let mut voting = WeightedVoting::new();

        voting.vote("prop1".to_string(), Vote {
            voter: "node1".to_string(),
            vote: true,
            timestamp: 0,
            weight: 10,
        });

        voting.vote("prop1".to_string(), Vote {
            voter: "node2".to_string(),
            vote: true,
            timestamp: 0,
            weight: 10,
        });

        let result = voting.tally("prop1", 15);
        assert!(result.is_some());
        assert!(result.unwrap().accepted);
    }
}
