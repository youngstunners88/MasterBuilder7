// Lightweight proof-of-work for spam prevention

use sha2::{Sha256, Digest};

/// Light proof-of-work challenge
pub struct LightPoW {
    difficulty: u8,
}

impl LightPoW {
    /// Create new PoW with given difficulty (leading zero bits)
    pub fn new(difficulty: u8) -> Self {
        Self { difficulty }
    }

    /// Generate random challenge
    pub fn generate_challenge(&self) -> Vec<u8> {
        let mut challenge = vec![0u8; 32];
        rand::fill(&mut challenge[..]);
        challenge
    }

    /// Solve challenge
    pub fn solve(&self, challenge: &[u8]) -> (u64, Vec<u8>) {
        let mut nonce: u64 = 0;

        loop {
            let hash = self.hash(challenge, nonce);

            if self.verify_hash(&hash) {
                return (nonce, hash);
            }

            nonce += 1;
        }
    }

    /// Verify solution
    pub fn verify(&self, challenge: &[u8], nonce: u64, hash: &[u8]) -> bool {
        let expected = self.hash(challenge, nonce);
        expected == hash && self.verify_hash(hash)
    }

    /// Hash challenge + nonce
    fn hash(&self, challenge: &[u8], nonce: u64) -> Vec<u8> {
        let mut hasher = Sha256::new();
        hasher.update(challenge);
        hasher.update(&nonce.to_le_bytes());
        hasher.finalize().to_vec()
    }

    /// Check if hash meets difficulty
    fn verify_hash(&self, hash: &[u8]) -> bool {
        let full_bytes = (self.difficulty / 8) as usize;
        let remainder = self.difficulty % 8;

        // Check full zero bytes
        for i in 0..full_bytes {
            if hash.get(i) != Some(&0) {
                return false;
            }
        }

        // Check partial byte
        if remainder > 0 {
            let mask = 0xFFu8 << (8 - remainder);
            if let Some(&byte) = hash.get(full_bytes) {
                if byte & mask != 0 {
                    return false;
                }
            }
        }

        true
    }
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
        assert_eq!(hash[0], 0);
    }

    #[test]
    fn test_pow_difficulty() {
        // Higher difficulty should take more work
        let pow8 = LightPoW::new(8);
        let pow16 = LightPoW::new(16);

        let challenge = pow8.generate_challenge();

        let (_, hash8) = pow8.solve(&challenge);
        assert!(hash8[0] == 0);

        // Verify hash8 doesn't meet pow16 difficulty
        assert!(!pow16.verify_hash(&hash8) || hash8[1] == 0);
    }
}
