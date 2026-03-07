"""
Deterministic Build Event Log - Append-only event sourcing
Part of Phase A: Truth Layer
"""

import json
import os
import sqlite3
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict


class BuildEventType(Enum):
    """Types of build events"""
    BUILD_STARTED = "build_started"
    STAGE_STARTED = "stage_started"
    STAGE_COMPLETED = "stage_completed"
    STAGE_FAILED = "stage_failed"
    ARTIFACT_CREATED = "artifact_created"
    RETRY_ATTEMPTED = "retry_attempted"
    BUILD_COMPLETED = "build_completed"
    BUILD_CANCELLED = "build_cancelled"


@dataclass
class BuildEvent:
    """
    Append-only event for build state transitions.
    Enables deterministic replay and audit.
    """
    event_id: str
    timestamp: str
    build_id: str
    event_type: str
    previous_state: Optional[str]
    new_state: str
    correlation_id: str
    actor: str
    payload: Dict[str, Any]
    
    @classmethod
    def create(
        cls,
        build_id: str,
        event_type: BuildEventType,
        new_state: str,
        actor: str,
        previous_state: Optional[str] = None,
        payload: Dict[str, Any] = None,
        correlation_id: str = None
    ) -> "BuildEvent":
        """Create a new build event"""
        return cls(
            event_id=f"evt-{uuid.uuid4().hex[:12]}",
            timestamp=datetime.utcnow().isoformat() + "Z",
            build_id=build_id,
            event_type=event_type.value,
            previous_state=previous_state,
            new_state=new_state,
            correlation_id=correlation_id or str(uuid.uuid4()),
            actor=actor,
            payload=payload or {}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class BuildEventLog:
    """
    Append-only event log for builds.
    Provides auditability and replay capability.
    """
    
    def __init__(self, db_path: str = None, log_dir: str = None):
        self.db_path = db_path or os.getenv("APEX_DB_PATH", "./orchestrator.db")
        self.log_dir = Path(log_dir or os.getenv("APEX_LOG_PATH", "./logs"))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS build_events (
                event_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                build_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                previous_state TEXT,
                new_state TEXT NOT NULL,
                correlation_id TEXT NOT NULL,
                actor TEXT NOT NULL,
                payload TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_build 
            ON build_events(build_id, timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_correlation 
            ON build_events(correlation_id)
        """)
        
        conn.commit()
        conn.close()
    
    def append(self, event: BuildEvent) -> str:
        """
        Append event to log (immutable operation).
        Returns event ID.
        """
        # Write to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO build_events 
            (event_id, timestamp, build_id, event_type, previous_state,
             new_state, correlation_id, actor, payload)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.event_id,
            event.timestamp,
            event.build_id,
            event.event_type,
            event.previous_state,
            event.new_state,
            event.correlation_id,
            event.actor,
            json.dumps(event.payload, default=str)
        ))
        
        conn.commit()
        conn.close()
        
        # Also append to file for easy replay
        log_file = self.log_dir / f"{event.build_id}.log"
        with open(log_file, 'a') as f:
            f.write(json.dumps(event.to_dict(), default=str) + "\n")
        
        return event.event_id
    
    def get_events(self, build_id: str) -> List[BuildEvent]:
        """Get all events for a build in chronological order"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT event_id, timestamp, build_id, event_type, previous_state,
                   new_state, correlation_id, actor, payload
            FROM build_events 
            WHERE build_id = ? 
            ORDER BY timestamp ASC
        """, (build_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            BuildEvent(
                event_id=row[0],
                timestamp=row[1],
                build_id=row[2],
                event_type=row[3],
                previous_state=row[4],
                new_state=row[5],
                correlation_id=row[6],
                actor=row[7],
                payload=json.loads(row[8])
            )
            for row in rows
        ]
    
    def replay_build(self, build_id: str) -> Dict[str, Any]:
        """
        Replay build from event log and reconstruct state.
        Returns final build state.
        """
        events = self.get_events(build_id)
        
        if not events:
            return {"error": f"No events found for build {build_id}"}
        
        # Reconstruct state
        state = {
            "build_id": build_id,
            "current_stage": None,
            "completed_stages": [],
            "artifacts": [],
            "errors": [],
            "retry_count": 0,
            "start_time": None,
            "end_time": None
        }
        
        for event in events:
            if event.event_type == BuildEventType.BUILD_STARTED.value:
                state["start_time"] = event.timestamp
                state["current_stage"] = "started"
            
            elif event.event_type == BuildEventType.STAGE_STARTED.value:
                state["current_stage"] = event.payload.get("stage")
            
            elif event.event_type == BuildEventType.STAGE_COMPLETED.value:
                stage = event.payload.get("stage")
                if stage:
                    state["completed_stages"].append(stage)
                state["current_stage"] = f"completed:{stage}"
            
            elif event.event_type == BuildEventType.STAGE_FAILED.value:
                state["errors"].append({
                    "stage": event.payload.get("stage"),
                    "error": event.payload.get("error"),
                    "timestamp": event.timestamp
                })
            
            elif event.event_type == BuildEventType.ARTIFACT_CREATED.value:
                state["artifacts"].append(event.payload.get("artifact_id"))
            
            elif event.event_type == BuildEventType.RETRY_ATTEMPTED.value:
                state["retry_count"] += 1
            
            elif event.event_type == BuildEventType.BUILD_COMPLETED.value:
                state["end_time"] = event.timestamp
                state["current_stage"] = "completed"
            
            elif event.event_type == BuildEventType.BUILD_CANCELLED.value:
                state["end_time"] = event.timestamp
                state["current_stage"] = "cancelled"
        
        return state
    
    def get_audit_trail(self, build_id: str) -> Dict[str, Any]:
        """Get full audit trail for a build"""
        events = self.get_events(build_id)
        
        return {
            "build_id": build_id,
            "event_count": len(events),
            "events": [e.to_dict() for e in events],
            "stages": list(set(
                e.payload.get("stage") 
                for e in events 
                if "stage" in e.payload
            )),
            "actors": list(set(e.actor for e in events)),
            "duration_seconds": self._calculate_duration(events)
        }
    
    def _calculate_duration(self, events: List[BuildEvent]) -> Optional[float]:
        """Calculate build duration from events"""
        if not events:
            return None
        
        start = None
        end = None
        
        for e in events:
            if e.event_type == BuildEventType.BUILD_STARTED.value:
                start = datetime.fromisoformat(e.timestamp.replace('Z', '+00:00'))
            elif e.event_type in [BuildEventType.BUILD_COMPLETED.value, BuildEventType.BUILD_CANCELLED.value]:
                end = datetime.fromisoformat(e.timestamp.replace('Z', '+00:00'))
        
        if start and end:
            return (end - start).total_seconds()
        return None
    
    def verify_determinism(self, build_id: str, replay_state: Dict[str, Any]) -> bool:
        """
        Verify that replay produces deterministic results.
        Compare replay state with actual outcome.
        """
        actual_events = self.get_events(build_id)
        
        # Re-replay and compare
        reconstructed = self.replay_build(build_id)
        
        # Key checks for determinism
        checks = [
            replay_state.get("completed_stages") == reconstructed.get("completed_stages"),
            replay_state.get("retry_count") == reconstructed.get("retry_count"),
            len(replay_state.get("artifacts", [])) == len(reconstructed.get("artifacts", []))
        ]
        
        return all(checks)
