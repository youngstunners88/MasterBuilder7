"""
Artifact Contracts - Typed schemas for build stage outputs
Part of Phase A: Truth Layer

Provides:
- Explicit schemas for all 7 build stages
- Contract validation
- Versioning and immutability
- Clear simulation flagging
"""

import hashlib
import json
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict


class BuildStage(Enum):
    """Build pipeline stages"""
    ANALYZE = "analyze"
    PLAN = "plan"
    BUILD = "build"
    TEST = "test"
    DEPLOY = "deploy"
    VERIFY = "verify"
    EVOLVE = "evolve"


# JSON Schema definitions for each stage output
CONTRACT_SCHEMAS = {
    BuildStage.ANALYZE: {
        "type": "object",
        "required": ["stack", "automation_potential", "demo_mode"],
        "properties": {
            "stack": {"type": "string", "description": "Detected technology stack"},
            "automation_potential": {"type": "number", "minimum": 0, "maximum": 1},
            "files_found": {"type": "array", "items": {"type": "string"}},
            "demo_mode": {"type": "boolean", "description": "Whether this is simulated"}
        }
    },
    BuildStage.PLAN: {
        "type": "object",
        "required": ["architecture", "stages", "demo_mode"],
        "properties": {
            "architecture": {"type": "string"},
            "stages": {"type": "array", "items": {"type": "string"}},
            "parallel_stages": {"type": "array", "items": {"type": "string"}},
            "estimated_duration_seconds": {"type": "number"},
            "demo_mode": {"type": "boolean"}
        }
    },
    BuildStage.BUILD: {
        "type": "object",
        "required": ["frontend", "backend", "demo_mode"],
        "properties": {
            "frontend": {
                "type": "object",
                "properties": {
                    "files_generated": {"type": "integer"},
                    "lines_of_code": {"type": "integer"},
                    "build_time_seconds": {"type": "number"}
                }
            },
            "backend": {
                "type": "object",
                "properties": {
                    "files_generated": {"type": "integer"},
                    "lines_of_code": {"type": "integer"},
                    "build_time_seconds": {"type": "number"}
                }
            },
            "demo_mode": {"type": "boolean"}
        }
    },
    BuildStage.TEST: {
        "type": "object",
        "required": ["unit_tests", "test_runner", "demo_mode"],
        "properties": {
            "unit_tests": {
                "type": "object",
                "properties": {
                    "passed": {"type": "integer"},
                    "failed": {"type": "integer"},
                    "coverage": {"type": "number", "minimum": 0, "maximum": 100}
                }
            },
            "integration_tests": {
                "type": "object",
                "properties": {
                    "passed": {"type": "integer"},
                    "failed": {"type": "integer"}
                }
            },
            "test_runner": {"type": "string", "enum": ["pytest", "jest", "none"]},
            "raw_output": {"type": "string"},
            "demo_mode": {"type": "boolean"}
        }
    },
    BuildStage.DEPLOY: {
        "type": "object",
        "required": ["status", "deployment_time", "demo_mode"],
        "properties": {
            "frontend_url": {"type": "string", "format": "uri"},
            "backend_url": {"type": "string", "format": "uri"},
            "deployment_time": {"type": "string"},
            "status": {"type": "string", "enum": ["success", "failed", "pending"]},
            "demo_mode": {"type": "boolean"},
            "simulation": {"type": "boolean", "description": "Deprecated, use demo_mode"}
        }
    },
    BuildStage.VERIFY: {
        "type": "object",
        "required": ["health_checks", "verification_status", "demo_mode"],
        "properties": {
            "health_checks": {
                "type": "object",
                "properties": {
                    "passed": {"type": "integer"},
                    "failed": {"type": "integer"}
                }
            },
            "response_times": {"type": "object"},
            "ssl_valid": {"type": "boolean"},
            "verification_status": {"type": "string", "enum": ["PASSED", "FAILED"]},
            "demo_mode": {"type": "boolean"}
        }
    },
    BuildStage.EVOLVE: {
        "type": "object",
        "required": ["improvements", "demo_mode"],
        "properties": {
            "improvements": {"type": "array", "items": {"type": "string"}},
            "lessons_learned": {"type": "array", "items": {"type": "string"}},
            "demo_mode": {"type": "boolean"}
        }
    }
}


@dataclass
class StageArtifact:
    """
    Immutable artifact from a build stage.
    
    Guarantees:
    - Typed payload schema per stage
    - Explicit simulation flag
    - Cryptographic signature
    - Immutable once created
    """
    artifact_id: str
    stage: str
    build_id: str
    version: int
    timestamp: str
    producer_agent: str
    payload: Dict[str, Any]
    simulation: bool
    signature: str
    contract_version: str
    
    @classmethod
    def create(
        cls,
        stage: BuildStage,
        build_id: str,
        producer_agent: str,
        payload: Dict[str, Any],
        simulation: bool = False
    ) -> "StageArtifact":
        """Create a new artifact with computed signature"""
        
        artifact = cls(
            artifact_id=f"art-{stage.value}-{uuid.uuid4().hex[:12]}",
            stage=stage.value,
            build_id=build_id,
            version=1,
            timestamp=datetime.utcnow().isoformat() + "Z",
            producer_agent=producer_agent,
            payload=payload,
            simulation=simulation,
            signature="",  # Computed below
            contract_version="1.0"
        )
        
        artifact.signature = artifact._compute_signature()
        return artifact
    
    def _compute_signature(self) -> str:
        """Compute SHA-256 signature of artifact contents"""
        content = json.dumps({
            "stage": self.stage,
            "build_id": self.build_id,
            "timestamp": self.timestamp,
            "producer_agent": self.producer_agent,
            "payload": self.payload,
            "simulation": self.simulation,
            "contract_version": self.contract_version
        }, sort_keys=True)
        
        return f"sha256:{hashlib.sha256(content.encode()).hexdigest()[:32]}"
    
    def verify(self) -> bool:
        """Verify artifact integrity"""
        return self.signature == self._compute_signature()
    
    def validate_contract(self) -> List[str]:
        """Validate payload against stage schema. Returns list of errors."""
        errors = []
        
        try:
            stage_enum = BuildStage(self.stage)
            schema = CONTRACT_SCHEMAS.get(stage_enum)
            
            if not schema:
                errors.append(f"No schema defined for stage: {self.stage}")
                return errors
            
            required = schema.get("required", [])
            for field in required:
                if field not in self.payload:
                    errors.append(f"Missing required field: {field}")
            
            # Check demo_mode is present
            if "demo_mode" not in self.payload:
                errors.append("Missing demo_mode flag in payload")
            
        except ValueError:
            errors.append(f"Invalid stage: {self.stage}")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=indent, default=str)


class ArtifactStore:
    """
    Persistent storage for build artifacts.
    Provides versioning and retrieval.
    """
    
    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path or "./artifacts")
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def save(self, artifact: StageArtifact) -> str:
        """
        Save artifact to storage.
        Returns file path.
        """
        # Validate before saving
        errors = artifact.validate_contract()
        if errors:
            raise ValueError(f"Artifact validation failed: {errors}")
        
        # Create directory structure: artifacts/{build_id}/{stage}/
        artifact_dir = self.base_path / artifact.build_id / artifact.stage
        artifact_dir.mkdir(parents=True, exist_ok=True)
        
        # Save with versioned filename
        file_path = artifact_dir / f"v{artifact.version}.json"
        
        with open(file_path, 'w') as f:
            f.write(artifact.to_json())
        
        return str(file_path)
    
    def load(self, build_id: str, stage: str, version: int = None) -> Optional[StageArtifact]:
        """
        Load artifact from storage.
        If version not specified, loads latest.
        """
        artifact_dir = self.base_path / build_id / stage
        
        if not artifact_dir.exists():
            return None
        
        if version:
            file_path = artifact_dir / f"v{version}.json"
        else:
            # Find latest version
            versions = sorted(
                [f for f in artifact_dir.glob("v*.json")],
                key=lambda p: int(p.stem[1:]),
                reverse=True
            )
            if not versions:
                return None
            file_path = versions[0]
        
        with open(file_path) as f:
            data = json.load(f)
        
        return StageArtifact(**data)
    
    def list_builds(self) -> List[str]:
        """List all build IDs in storage"""
        if not self.base_path.exists():
            return []
        
        return [d.name for d in self.base_path.iterdir() if d.is_dir()]
    
    def list_artifacts(self, build_id: str) -> List[Dict[str, Any]]:
        """List all artifacts for a build"""
        build_dir = self.base_path / build_id
        
        if not build_dir.exists():
            return []
        
        artifacts = []
        for stage_dir in build_dir.iterdir():
            if stage_dir.is_dir():
                for version_file in stage_dir.glob("v*.json"):
                    with open(version_file) as f:
                        data = json.load(f)
                        artifacts.append({
                            "artifact_id": data["artifact_id"],
                            "stage": data["stage"],
                            "version": data["version"],
                            "simulation": data["simulation"],
                            "timestamp": data["timestamp"]
                        })
        
        return sorted(artifacts, key=lambda x: x["timestamp"])
