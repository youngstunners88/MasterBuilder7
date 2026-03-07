#!/usr/bin/env python3
"""
APEX Consensus Engine
Ensures quality through multi-agent verification
"""

import hashlib
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Verification:
    agent_id: str
    result: Any
    confidence: float
    timestamp: datetime
    hash: str


class ConsensusEngine:
    """3-Verifier consensus protocol for APEX"""
    
    def __init__(self, threshold: float = 0.80):
        self.threshold = threshold
        self.verifications: Dict[str, List[Verification]] = {}
        self.cache: Dict[str, Any] = {}
        
    def submit_verification(self, task_id: str, agent_id: str, 
                           result: Any, confidence: float) -> Dict:
        """Submit a verification result from an agent"""
        
        # Create hash of result for comparison
        result_hash = self._hash_result(result)
        
        verification = Verification(
            agent_id=agent_id,
            result=result,
            confidence=confidence,
            timestamp=datetime.now(),
            hash=result_hash
        )
        
        if task_id not in self.verifications:
            self.verifications[task_id] = []
        
        self.verifications[task_id].append(verification)
        
        # Check if we have consensus
        consensus = self._check_consensus(task_id)
        
        return {
            'task_id': task_id,
            'verifications_count': len(self.verifications[task_id]),
            'consensus_reached': consensus['reached'],
            'consensus_confidence': consensus['confidence'],
            'agreement_percentage': consensus['agreement']
        }
    
    def _hash_result(self, result: Any) -> str:
        """Create hash of result for comparison"""
        result_str = json.dumps(result, sort_keys=True, default=str)
        return hashlib.sha256(result_str.encode()).hexdigest()[:16]
    
    def _check_consensus(self, task_id: str) -> Dict:
        """Check if consensus is reached for a task"""
        verifications = self.verifications.get(task_id, [])
        
        if len(verifications) < 3:
            return {
                'reached': False,
                'confidence': 0.0,
                'agreement': 0.0,
                'reason': 'insufficient_verifiers'
            }
        
        # Count hash matches
        hash_counts = {}
        for v in verifications:
            hash_counts[v.hash] = hash_counts.get(v.hash, 0) + 1
        
        # Find majority hash
        majority_hash = max(hash_counts, key=hash_counts.get)
        majority_count = hash_counts[majority_hash]
        
        agreement = majority_count / len(verifications)
        
        # Calculate average confidence of majority
        majority_verifications = [v for v in verifications if v.hash == majority_hash]
        avg_confidence = sum(v.confidence for v in majority_verifications) / len(majority_verifications)
        
        # Consensus requires 80% agreement AND average confidence >= threshold
        reached = agreement >= 0.80 and avg_confidence >= self.threshold
        
        return {
            'reached': reached,
            'confidence': avg_confidence,
            'agreement': agreement,
            'majority_hash': majority_hash,
            'verifiers': [v.agent_id for v in majority_verifications]
        }
    
    def get_consensus_result(self, task_id: str) -> Optional[Dict]:
        """Get the consensus result for a task"""
        consensus = self._check_consensus(task_id)
        
        if not consensus['reached']:
            return None
        
        # Return the majority result
        verifications = self.verifications.get(task_id, [])
        majority_result = next(
            v.result for v in verifications 
            if v.hash == consensus['majority_hash']
        )
        
        return {
            'result': majority_result,
            'confidence': consensus['confidence'],
            'agreement': consensus['agreement'],
            'verifiers': consensus['verifiers']
        }
    
    def require_revote(self, task_id: str) -> Dict:
        """Trigger a revote if consensus not reached"""
        # Clear verifications for fresh consensus
        if task_id in self.verifications:
            del self.verifications[task_id]
        
        return {
            'task_id': task_id,
            'action': 'revote_triggered',
            'message': 'New verifiers assigned for fresh consensus'
        }


if __name__ == "__main__":
    # Test
    engine = ConsensusEngine()
    
    # Simulate verifications
    task_id = "test-task-001"
    
    print("Testing APEX Consensus Engine...")
    
    # Three agents with same result
    result1 = {"status": "success", "code": 200}
    result2 = {"status": "success", "code": 200}
    result3 = {"status": "success", "code": 200}
    
    engine.submit_verification(task_id, "agent-1", result1, 0.95)
    engine.submit_verification(task_id, "agent-2", result2, 0.90)
    engine.submit_verification(task_id, "agent-3", result3, 0.92)
    
    consensus = engine._check_consensus(task_id)
    print(f"Consensus reached: {consensus['reached']}")
    print(f"Agreement: {consensus['agreement']:.0%}")
    print(f"Confidence: {consensus['confidence']:.2f}")
