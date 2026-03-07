"""
Phase A Hardening Tests
Validates:
1. Artifact contracts and validation
2. Build event log replay
3. Demo mode flagging
4. Deterministic behavior
"""

import asyncio
import json
import os
import tempfile
import pytest
from pathlib import Path

# Add parent to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.workflow.artifact_contracts import (
    BuildStage, StageArtifact, ArtifactStore, CONTRACT_SCHEMAS
)
from core.workflow.build_event_log import BuildEvent, BuildEventLog, BuildEventType
from core.workflow.build_pipeline_hardened import (
    HardenedBuildPipeline, AnalyzeAdapter, TestAdapter
)


class TestArtifactContracts:
    """Test artifact contract system"""
    
    def test_artifact_creation(self):
        """Test creating a valid artifact"""
        artifact = StageArtifact.create(
            stage=BuildStage.ANALYZE,
            build_id="build-001",
            producer_agent="analyze-agent",
            payload={
                "stack": "react-vite-web",
                "automation_potential": 0.85,
                "files_found": ["package.json", "src/"],
                "demo_mode": False
            },
            simulation=False
        )
        
        assert artifact.stage == "analyze"
        assert artifact.build_id == "build-001"
        assert artifact.simulation == False
        assert artifact.signature.startswith("sha256:")
        assert artifact.verify()  # Signature should be valid
    
    def test_artifact_validation(self):
        """Test contract validation"""
        # Valid artifact
        artifact = StageArtifact.create(
            stage=BuildStage.ANALYZE,
            build_id="build-001",
            producer_agent="analyze-agent",
            payload={
                "stack": "react-vite-web",
                "automation_potential": 0.85,
                "demo_mode": False
            },
            simulation=False
        )
        
        errors = artifact.validate_contract()
        assert len(errors) == 0, f"Unexpected errors: {errors}"
        
        # Invalid - missing demo_mode
        artifact_invalid = StageArtifact.create(
            stage=BuildStage.ANALYZE,
            build_id="build-001",
            producer_agent="analyze-agent",
            payload={
                "stack": "react-vite-web",
                "automation_potential": 0.85
                # Missing demo_mode
            },
            simulation=False
        )
        
        errors = artifact_invalid.validate_contract()
        assert any("demo_mode" in e for e in errors)
    
    def test_simulation_flag_explicit(self):
        """Ensure simulation flag is always explicit"""
        # Artifact with simulation=True
        artifact_sim = StageArtifact.create(
            stage=BuildStage.DEPLOY,
            build_id="build-001",
            producer_agent="deploy-agent",
            payload={
                "frontend_url": "https://demo.example.com",
                "status": "success",
                "deployment_time": "0.5s",
                "demo_mode": True
            },
            simulation=True
        )
        
        assert artifact_sim.simulation == True
        assert artifact_sim.payload["demo_mode"] == True
        
        # Verify JSON output includes simulation flags
        json_str = artifact_sim.to_json()
        data = json.loads(json_str)
        assert data["simulation"] == True
        assert data["payload"]["demo_mode"] == True
    
    def test_artifact_store(self, tmp_path):
        """Test artifact persistence"""
        store = ArtifactStore(str(tmp_path / "artifacts"))
        
        artifact = StageArtifact.create(
            stage=BuildStage.TEST,
            build_id="build-test",
            producer_agent="test-agent",
            payload={
                "unit_tests": {"passed": 10, "failed": 0, "coverage": 85},
                "test_runner": "pytest",
                "demo_mode": False
            },
            simulation=False
        )
        
        # Save
        file_path = store.save(artifact)
        assert Path(file_path).exists()
        
        # Load
        loaded = store.load("build-test", "test")
        assert loaded is not None
        assert loaded.artifact_id == artifact.artifact_id
        assert loaded.verify()  # Signature should still be valid


class TestBuildEventLog:
    """Test event log system"""
    
    def test_event_creation(self):
        """Test creating build events"""
        event = BuildEvent.create(
            build_id="build-001",
            event_type=BuildEventType.BUILD_STARTED,
            new_state="started",
            actor="test-pipeline",
            payload={"project_name": "test-app"}
        )
        
        assert event.build_id == "build-001"
        assert event.event_type == "build_started"
        assert event.new_state == "started"
        assert event.event_id.startswith("evt-")
    
    def test_event_logging(self, tmp_path):
        """Test append-only logging"""
        db_path = str(tmp_path / "test.db")
        log_dir = str(tmp_path / "logs")
        
        event_log = BuildEventLog(db_path, log_dir)
        
        # Append events
        event1 = BuildEvent.create(
            build_id="build-002",
            event_type=BuildEventType.BUILD_STARTED,
            new_state="started",
            actor="pipeline"
        )
        
        event2 = BuildEvent.create(
            build_id="build-002",
            event_type=BuildEventType.STAGE_STARTED,
            new_state="analyze_running",
            actor="pipeline",
            previous_state="started",
            payload={"stage": "analyze"}
        )
        
        event_log.append(event1)
        event_log.append(event2)
        
        # Retrieve
        events = event_log.get_events("build-002")
        assert len(events) == 2
        assert events[0].event_type == "build_started"
        assert events[1].event_type == "stage_started"
    
    def test_build_replay(self, tmp_path):
        """Test deterministic replay"""
        db_path = str(tmp_path / "test.db")
        log_dir = str(tmp_path / "logs")
        
        event_log = BuildEventLog(db_path, log_dir)
        
        # Simulate a build
        events = [
            BuildEvent.create("build-003", BuildEventType.BUILD_STARTED, "started", "pipeline"),
            BuildEvent.create("build-003", BuildEventType.STAGE_STARTED, "analyze_running", "pipeline", 
                            previous_state="started", payload={"stage": "analyze"}),
            BuildEvent.create("build-003", BuildEventType.STAGE_COMPLETED, "analyze_completed", "pipeline",
                            previous_state="analyze_running", payload={"stage": "analyze"}),
            BuildEvent.create("build-003", BuildEventType.STAGE_STARTED, "test_running", "pipeline",
                            previous_state="analyze_completed", payload={"stage": "test"}),
            BuildEvent.create("build-003", BuildEventType.STAGE_COMPLETED, "test_completed", "pipeline",
                            previous_state="test_running", payload={"stage": "test"}),
            BuildEvent.create("build-003", BuildEventType.BUILD_COMPLETED, "completed", "pipeline",
                            previous_state="test_completed"),
        ]
        
        for e in events:
            event_log.append(e)
        
        # Replay
        state = event_log.replay_build("build-003")
        
        assert state["build_id"] == "build-003"
        assert state["current_stage"] == "completed"
        assert "analyze" in state["completed_stages"]
        assert "test" in state["completed_stages"]


class TestAnalyzeAdapter:
    """Test real execution adapters"""
    
    @pytest.mark.asyncio
    async def test_real_repo_detection(self, tmp_path):
        """Test actual repository analysis"""
        # Create a mock React project
        (tmp_path / "package.json").write_text(json.dumps({
            "name": "test-app",
            "dependencies": {"react": "^18.0.0"}
        }))
        (tmp_path / "vite.config.ts").write_text("")
        
        adapter = AnalyzeAdapter(demo_mode=False)
        result = await adapter.execute({"repo_path": str(tmp_path)})
        
        assert result.success == True
        assert result.payload["stack"] == "react-vite-web"
        assert result.payload["demo_mode"] == False
        assert "vite.config.ts" in result.payload["files_found"]
    
    @pytest.mark.asyncio
    async def test_nonexistent_repo(self, tmp_path):
        """Test handling of non-existent repo"""
        adapter = AnalyzeAdapter(demo_mode=False)
        result = await adapter.execute({"repo_path": str(tmp_path / "nonexistent")})
        
        assert result.success == False
        assert "does not exist" in result.error


class TestDeterminism:
    """Test deterministic behavior"""
    
    def test_replay_determinism(self, tmp_path):
        """Verify replay produces same results"""
        db_path = str(tmp_path / "test.db")
        log_dir = str(tmp_path / "logs")
        
        event_log = BuildEventLog(db_path, log_dir)
        
        # Create a complete build log
        build_id = "build-det"
        for event in [
            BuildEvent.create(build_id, BuildEventType.BUILD_STARTED, "started", "p"),
            BuildEvent.create(build_id, BuildEventType.ARTIFACT_CREATED, "art1", "p", 
                            payload={"artifact_id": "a1", "stage": "analyze"}),
            BuildEvent.create(build_id, BuildEventType.STAGE_COMPLETED, "analyze_done", "p",
                            payload={"stage": "analyze"}),
            BuildEvent.create(build_id, BuildEventType.BUILD_COMPLETED, "done", "p"),
        ]:
            event_log.append(event)
        
        # Replay multiple times
        state1 = event_log.replay_build(build_id)
        state2 = event_log.replay_build(build_id)
        
        assert state1 == state2  # Deterministic!
        
        # Verify with helper
        assert event_log.verify_determinism(build_id, state1)


def run_tests():
    """Run all tests with pytest"""
    import subprocess
    result = subprocess.run(
        ["python", "-m", "pytest", __file__, "-v"],
        capture_output=False
    )
    return result.returncode


if __name__ == "__main__":
    exit(run_tests())
