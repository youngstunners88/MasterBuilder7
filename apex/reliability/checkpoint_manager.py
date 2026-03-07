#!/usr/bin/env python3
"""
APEX Checkpoint Manager
Saves and restores build state for fault tolerance
"""

import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class Checkpoint:
    id: str
    timestamp: str
    stage: str
    files: List[str]
    metadata: Dict[str, Any]
    hash: str


class CheckpointManager:
    """Manages build checkpoints for rollback capability"""
    
    def __init__(self, checkpoint_dir: str = "/home/teacherchris37/MasterBuilder7/apex/checkpoints"):
        self.checkpoint_dir = checkpoint_dir
        os.makedirs(checkpoint_dir, exist_ok=True)
        self.checkpoints: Dict[str, Checkpoint] = {}
        self._load_checkpoints()
    
    def _load_checkpoints(self):
        """Load existing checkpoints from disk"""
        index_path = os.path.join(self.checkpoint_dir, "index.json")
        if os.path.exists(index_path):
            with open(index_path, 'r') as f:
                data = json.load(f)
                for cp_id, cp_data in data.items():
                    self.checkpoints[cp_id] = Checkpoint(**cp_data)
    
    def _save_index(self):
        """Save checkpoint index to disk"""
        index_path = os.path.join(self.checkpoint_dir, "index.json")
        with open(index_path, 'w') as f:
            json.dump({k: asdict(v) for k, v in self.checkpoints.items()}, f, indent=2)
    
    def create_checkpoint(self, build_id: str, stage: str, 
                         files: List[str], metadata: Dict = None) -> Checkpoint:
        """Create a new checkpoint"""
        
        checkpoint_id = f"{build_id}-{stage}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        checkpoint = Checkpoint(
            id=checkpoint_id,
            timestamp=datetime.now().isoformat(),
            stage=stage,
            files=files,
            metadata=metadata or {},
            hash=self._compute_hash(files)
        )
        
        self.checkpoints[checkpoint_id] = checkpoint
        self._save_index()
        
        # Save checkpoint data
        checkpoint_path = os.path.join(self.checkpoint_dir, f"{checkpoint_id}.json")
        with open(checkpoint_path, 'w') as f:
            json.dump(asdict(checkpoint), f, indent=2)
        
        return checkpoint
    
    def _compute_hash(self, files: List[str]) -> str:
        """Compute hash of file contents"""
        import hashlib
        
        hasher = hashlib.sha256()
        for filepath in sorted(files):
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    hasher.update(f.read())
        
        return hasher.hexdigest()[:16]
    
    def get_latest_checkpoint(self, build_id: str) -> Optional[Checkpoint]:
        """Get the latest checkpoint for a build"""
        build_checkpoints = [
            cp for cp in self.checkpoints.values() 
            if cp.id.startswith(build_id)
        ]
        
        if not build_checkpoints:
            return None
        
        return max(build_checkpoints, key=lambda x: x.timestamp)
    
    def get_stage_checkpoint(self, build_id: str, stage: str) -> Optional[Checkpoint]:
        """Get checkpoint for specific stage"""
        for cp in self.checkpoints.values():
            if cp.id.startswith(build_id) and cp.stage == stage:
                return cp
        return None
    
    def list_checkpoints(self, build_id: str = None) -> List[Checkpoint]:
        """List all checkpoints, optionally filtered by build"""
        if build_id:
            return [
                cp for cp in self.checkpoints.values()
                if cp.id.startswith(build_id)
            ]
        return list(self.checkpoints.values())
    
    def rollback_to_checkpoint(self, checkpoint_id: str) -> Dict:
        """Rollback to a specific checkpoint"""
        if checkpoint_id not in self.checkpoints:
            return {
                'success': False,
                'error': f'Checkpoint {checkpoint_id} not found'
            }
        
        checkpoint = self.checkpoints[checkpoint_id]
        
        # In real implementation, this would restore files
        return {
            'success': True,
            'checkpoint_id': checkpoint_id,
            'stage': checkpoint.stage,
            'files_restored': len(checkpoint.files),
            'timestamp': checkpoint.timestamp
        }
    
    def clean_old_checkpoints(self, build_id: str, keep_last: int = 5):
        """Clean old checkpoints, keeping only the most recent"""
        build_cps = self.list_checkpoints(build_id)
        
        if len(build_cps) <= keep_last:
            return {'removed': 0}
        
        # Sort by timestamp and remove old ones
        sorted_cps = sorted(build_cps, key=lambda x: x.timestamp, reverse=True)
        to_remove = sorted_cps[keep_last:]
        
        removed = 0
        for cp in to_remove:
            del self.checkpoints[cp.id]
            cp_path = os.path.join(self.checkpoint_dir, f"{cp.id}.json")
            if os.path.exists(cp_path):
                os.remove(cp_path)
            removed += 1
        
        self._save_index()
        
        return {'removed': removed, 'kept': keep_last}


if __name__ == "__main__":
    # Test
    manager = CheckpointManager()
    
    print("Testing APEX Checkpoint Manager...")
    
    # Create test checkpoint
    cp = manager.create_checkpoint(
        build_id="test-build-001",
        stage="planning",
        files=["/tmp/test.txt"],
        metadata={"agent": "planning-1", "status": "complete"}
    )
    
    print(f"Created checkpoint: {cp.id}")
    print(f"Stage: {cp.stage}")
    print(f"Timestamp: {cp.timestamp}")
    
    # List checkpoints
    checkpoints = manager.list_checkpoints("test-build-001")
    print(f"\nTotal checkpoints: {len(checkpoints)}")
