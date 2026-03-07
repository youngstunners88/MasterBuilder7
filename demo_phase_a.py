#!/usr/bin/env python3
"""
Phase A Hardening Demo
Shows the truth layer in action with explicit simulation flags.
"""

import asyncio
import sys
import tempfile
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.workflow.build_pipeline_hardened import HardenedBuildPipeline
from core.workflow.build_event_log import BuildEventLog
from core.workflow.artifact_contracts import ArtifactStore


async def demo_artifact_contracts():
    """Demonstrate artifact contracts with simulation flags"""
    print("\n" + "="*60)
    print("DEMO 1: Artifact Contracts with Explicit Simulation Flags")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create pipeline in demo mode
        pipeline = HardenedBuildPipeline(demo_mode=True)
        
        print("\n🎭 Running in DEMO MODE")
        print("   All artifacts will have simulation=True")
        
        # Execute build
        result = await pipeline.execute_build(
            project_name="demo-app",
            repo_path="."
        )
        
        print(f"\n✅ Build completed: {result['build_id']}")
        print(f"   Status: {result['status']}")
        print(f"   Demo Mode: {result['demo_mode']}")
        
        # Show artifacts
        print("\n📦 Artifacts Created:")
        for stage, artifact_id in result['artifacts'].items():
            print(f"   - {stage}: {artifact_id}")
        
        # Load and verify one artifact
        artifact_id = result['artifacts']['analysis']
        print(f"\n🔍 Inspecting artifact: {artifact_id}")
        
        # Load from store
        store = ArtifactStore()
        build_id = result['build_id']
        artifact = store.load(build_id, "analyze")
        
        if artifact:
            print(f"   Artifact ID: {artifact.artifact_id}")
            print(f"   Simulation: {artifact.simulation}")
            print(f"   Signature Valid: {artifact.verify()}")
            print(f"   Payload keys: {list(artifact.payload.keys())}")
            
            if 'demo_mode' in artifact.payload:
                print(f"   Payload demo_mode: {artifact.payload['demo_mode']}")


async def demo_event_logging():
    """Demonstrate build event logging"""
    print("\n" + "="*60)
    print("DEMO 2: Deterministic Event Logging")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        pipeline = HardenedBuildPipeline(demo_mode=True)
        
        print("\n📝 Executing build with full event logging...")
        
        result = await pipeline.execute_build(
            project_name="event-demo",
            repo_path="."
        )
        
        build_id = result['build_id']
        
        # Get event log
        event_log = BuildEventLog()
        events = event_log.get_events(build_id)
        
        print(f"\n📊 Event Log Summary for {build_id}:")
        print(f"   Total events: {len(events)}")
        
        print("\n   Event Timeline:")
        for event in events:
            emoji = {
                'build_started': '🚀',
                'stage_started': '▶️',
                'stage_completed': '✅',
                'stage_failed': '❌',
                'artifact_created': '📦',
                'build_completed': '🏁'
            }.get(event.event_type, '•')
            
            payload_info = ""
            if event.payload:
                if 'stage' in event.payload:
                    payload_info = f" (stage: {event.payload['stage']})"
                elif 'artifact_id' in event.payload:
                    payload_info = f" (artifact: {event.payload['artifact_id'][:20]}...)"
            
            print(f"   {emoji} {event.timestamp.split('T')[1][:8]} {event.event_type}{payload_info}")
        
        # Replay build
        print(f"\n🔄 Replaying build from event log...")
        state = event_log.replay_build(build_id)
        
        print(f"   Reconstructed state:")
        print(f"   - Current stage: {state['current_stage']}")
        print(f"   - Completed stages: {state['completed_stages']}")
        print(f"   - Artifacts: {len(state['artifacts'])}")
        print(f"   - Errors: {len(state['errors'])}")
        
        # Verify determinism
        print(f"\n✓ Replay verified: {event_log.verify_determinism(build_id, state)}")


async def demo_security_headers():
    """Show security headers and CORS configuration"""
    print("\n" + "="*60)
    print("DEMO 3: Security Hardening")
    print("="*60)
    
    print("\n🔒 Security Features:")
    print("   ✓ No wildcard CORS in production")
    print("   ✓ Explicit origin whitelist")
    print("   ✓ Idempotency-Key required for mutations")
    print("   ✓ Security headers (X-Frame-Options, HSTS)")
    
    print("\n🛡️ Required Headers for API Calls:")
    print("   POST /build")
    print("   Content-Type: application/json")
    print("   Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000")
    
    print("\n📋 Environment Variables:")
    print("   APEX_DEMO_MODE=false       # Disable simulation")
    print("   APEX_ALLOWED_ORIGINS=https://app.example.com")
    print("   APEX_API_SECRET=your-secret")


async def demo_comparison():
    """Compare simulated vs hardened"""
    print("\n" + "="*60)
    print("DEMO 4: Simulated vs Hardened Comparison")
    print("="*60)
    
    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│ BEFORE (Simulated)          │ AFTER (Hardened Phase A)      │")
    print("├─────────────────────────────────────────────────────────────┤")
    print("│ asyncio.sleep(0.5)          │ Real repo inspection          │")
    print("│ Hardcoded stack values      │ Actual file detection         │")
    print("│ Fake URLs (no flag)         │ Explicit simulation flag      │")
    print("│ No artifact schema          │ Typed artifact contracts      │")
    print("│ No event log                │ Append-only event log         │")
    print("│ No replay capability        │ Deterministic replay          │")
    print("│ CORS: * (insecure)          │ Origin whitelist              │")
    print("│ No idempotency              │ UUID idempotency keys         │")
    print("└─────────────────────────────────────────────────────────────┘")


async def main():
    """Run all demos"""
    print("\n")
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║     APEX Build Pipeline - Phase A: Truth Layer Demo           ║")
    print("║     Production-Grade Execution Integrity                      ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    
    await demo_artifact_contracts()
    await demo_event_logging()
    await demo_security_headers()
    await demo_comparison()
    
    print("\n" + "="*60)
    print("Demo Complete!")
    print("="*60)
    print("\nNext Steps:")
    print("  1. Review docs/EXECUTION_HARDENING.md")
    print("  2. Run tests: python tests/test_phase_a_hardening.py")
    print("  3. Start hardened API: bun api/server_hardened.ts")
    print("  4. Implement Phase B: Real deployment adapters")
    print()


if __name__ == "__main__":
    asyncio.run(main())
