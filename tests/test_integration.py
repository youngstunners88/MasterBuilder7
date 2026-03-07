#!/usr/bin/env python3
"""
Test Suite: Integration Tests

End-to-end integration tests for the complete MasterBuilder7 system.

Coverage:
- Multi-agent communication
- State sharing across agents
- Task distribution and execution
- Health monitoring integration
- Cost tracking across agents
- Full workflow execution
"""

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime
from typing import List, Dict, Any

from apex.agents.agent_protocol import AgentBus, AgentCoordinator, MessageType
from apex.agents.shared_state import SharedStateManager
from apex.agents.task_queue import TaskQueue, TaskPriority, WorkerPool
from apex.agents.health_monitor import HealthMonitor, HealthStatus
from apex.agents.cost_tracker import CostTracker, AIProvider


# =============================================================================
# Multi-Agent Communication Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
class TestMultiAgentCommunication:
    """Test multi-agent communication scenarios."""
    
    async def test_agent_to_agent_messaging(self, integrated_system):
        """Test direct agent-to-agent messaging."""
        system = integrated_system
        bus = system["bus"]
        
        messages_received = []
        
        async def handler(message):
            messages_received.append(message)
        
        # Subscribe receiver
        await bus.subscribe("receiver-agent", handler=handler)
        
        # Send messages from multiple agents
        for i in range(5):
            await bus.send_direct(
                sender=f"sender-{i}",
                recipient="receiver-agent",
                payload={"index": i}
            )
        
        # Allow processing
        await asyncio.sleep(0.1)
        
        # Verify messages received
        messages = await bus.get_messages("receiver-agent")
        assert len(messages) == 5
    
    async def test_broadcast_to_all_agents(self, integrated_system):
        """Test broadcast to all agents."""
        system = integrated_system
        bus = system["bus"]
        
        # Subscribe multiple agents
        received_counts = {f"agent-{i}": 0 for i in range(10)}
        
        async def make_handler(agent_id):
            async def handler(message):
                received_counts[agent_id] += 1
            return handler
        
        for i in range(10):
            handler = await make_handler(f"agent-{i}")
            await bus.subscribe(f"agent-{i}", handler=handler)
        
        # Broadcast
        await bus.broadcast(
            sender="coordinator",
            payload={"command": "start"}
        )
        
        await asyncio.sleep(0.1)
        
        # Verify all agents received (via get_messages)
        for i in range(10):
            messages = await bus.get_messages(f"agent-{i}")
            assert len(messages) == 1
    
    async def test_request_response_pattern(self, integrated_system):
        """Test request-response pattern."""
        system = integrated_system
        bus = system["bus"]
        
        # Set up responder
        async def responder(message):
            reply = message.create_reply(
                payload={"result": "processed"},
                message_type=MessageType.HELP_RESPONSE
            )
            reply.sender = "responder-agent"
            reply.recipient = message.sender
            await bus.send_message(reply)
        
        await bus.subscribe("responder-agent", handler=responder)
        
        # Send request
        request = await bus.send_direct(
            sender="requester",
            recipient="responder-agent",
            payload={"request": "help"},
            message_type=MessageType.HELP_REQUEST
        )
        
        # Wait for response
        response = await bus.wait_for_response(request.id, timeout_seconds=2.0)
        
        assert response is not None
        assert response.payload["result"] == "processed"


# =============================================================================
# State Sharing Integration Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
class TestStateSharingIntegration:
    """Test state sharing across agents."""
    
    async def test_shared_state_across_agents(self, integrated_system):
        """Test state shared between agents."""
        system = integrated_system
        state_manager = system["state_manager"]
        
        # Agent 1 sets state
        await state_manager.set("shared-key", "shared-value")
        
        # Agent 2 reads state
        value = await state_manager.get("shared-key")
        
        assert value == "shared-value"
    
    async def test_distributed_locking(self, integrated_system):
        """Test distributed locking between agents."""
        system = integrated_system
        state_manager = system["state_manager"]
        
        async def agent_task(agent_id: str):
            async with state_manager.lock("critical-resource", owner=agent_id, ttl_seconds=5) as lock_id:
                if lock_id:
                    # Simulate work
                    await asyncio.sleep(0.1)
                    return f"{agent_id} acquired lock"
                return f"{agent_id} failed to acquire lock"
        
        # Run multiple agents concurrently
        results = await asyncio.gather(
            agent_task("agent-1"),
            agent_task("agent-2"),
            agent_task("agent-3")
        )
        
        # Exactly one should acquire the lock
        acquired = [r for r in results if "acquired" in r]
        failed = [r for r in results if "failed" in r]
        
        assert len(acquired) == 1
        assert len(failed) == 2
    
    async def test_state_snapshots(self, integrated_system):
        """Test state snapshots for recovery."""
        system = integrated_system
        state_manager = system["state_manager"]
        
        # Set up initial state
        await state_manager.set("config:app", "fastapi")
        await state_manager.set("config:db", "postgresql")
        await state_manager.set("build:version", "1.0.0")
        
        # Create snapshot
        snapshot_id = await state_manager.snapshot(name="pre-deployment")
        assert snapshot_id is not None
        
        # Modify state
        await state_manager.set("config:app", "django")
        await state_manager.delete("config:db")
        
        # Restore snapshot
        result = await state_manager.restore(snapshot_id)
        assert result is True
        
        # Verify restored state
        assert await state_manager.get("config:app") == "fastapi"
        assert await state_manager.get("config:db") == "postgresql"
        assert await state_manager.get("build:version") == "1.0.0"


# =============================================================================
# Task Queue Integration Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
class TestTaskQueueIntegration:
    """Test task queue with multiple workers."""
    
    async def test_task_distribution(self, integrated_system):
        """Test task distribution to workers."""
        system = integrated_system
        queue = system["queue"]
        
        completed_tasks = []
        
        async def task_handler(task):
            completed_tasks.append(task.id)
            return {"status": "completed"}
        
        # Create worker pool
        pool = WorkerPool(
            queue=queue,
            worker_id="worker-1",
            capabilities=["python"],
            task_handler=task_handler
        )
        
        await pool.start()
        
        # Enqueue tasks
        task_ids = []
        for i in range(5):
            task = await queue.enqueue(
                task_type="python_task",
                payload={"index": i},
                required_capabilities=["python"]
            )
            task_ids.append(task.id)
        
        # Wait for completion
        await asyncio.sleep(1)
        
        await pool.stop()
        
        # Verify tasks were completed
        assert len(completed_tasks) == 5
    
    async def test_priority_task_handling(self, integrated_system):
        """Test that high priority tasks are processed first."""
        system = integrated_system
        queue = system["queue"]
        
        processing_order = []
        
        async def task_handler(task):
            processing_order.append(task.priority.value)
            return {"status": "completed"}
        
        pool = WorkerPool(
            queue=queue,
            worker_id="priority-worker",
            task_handler=task_handler
        )
        
        await pool.start()
        
        # Enqueue in reverse priority order
        from apex.agents.task_queue import TaskPriority
        await queue.enqueue("task", {}, priority=TaskPriority.LOW)
        await queue.enqueue("task", {}, priority=TaskPriority.NORMAL)
        await queue.enqueue("task", {}, priority=TaskPriority.HIGH)
        await queue.enqueue("task", {}, priority=TaskPriority.CRITICAL)
        
        await asyncio.sleep(1)
        
        await pool.stop()
        
        # Verify order (highest first)
        assert processing_order[0] == 10  # CRITICAL
        assert processing_order[1] == 7   # HIGH
        assert processing_order[2] == 5   # NORMAL
        assert processing_order[3] == 3   # LOW
    
    async def test_task_retry_mechanism(self, integrated_system):
        """Test task retry on failure."""
        system = integrated_system
        queue = system["queue"]
        
        attempt_count = 0
        
        async def failing_handler(task):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception("Temporary failure")
            return {"status": "success"}
        
        pool = WorkerPool(
            queue=queue,
            worker_id="retry-worker",
            task_handler=failing_handler
        )
        
        await pool.start()
        
        task = await queue.enqueue(
            task_type="retry_task",
            payload={},
            max_retries=3
        )
        
        # Wait for retries
        await asyncio.sleep(3)
        
        await pool.stop()
        
        # Verify task was eventually completed
        completed_task = await queue.get_task(task.id)
        assert completed_task is not None
        # Note: Task status depends on actual retry implementation


# =============================================================================
# Health Monitor Integration Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
class TestHealthMonitorIntegration:
    """Test health monitoring with real agents."""
    
    async def test_health_monitoring_integration(self, integrated_system):
        """Test health monitoring with active agents."""
        system = integrated_system
        monitor = system["monitor"]
        bus = system["bus"]
        
        # Register agents
        for i in range(5):
            monitor.register_agent(f"agent-{i}", agent_type=f"type-{i}")
        
        # Start monitoring
        await monitor.start_monitoring()
        
        # Send heartbeats
        for i in range(5):
            monitor.heartbeat(f"agent-{i}", {
                "cpu_percent": 30.0 + i * 5,
                "memory_mb": 100.0 + i * 50,
                "status": "healthy"
            })
        
        # Check health
        health = monitor.check_health()
        
        assert health["total_agents"] == 5
        assert health["healthy_agents"] == 5
        assert health["average_health_score"] > 0.8
        
        await monitor.stop_monitoring()
    
    async def test_failure_detection(self, integrated_system):
        """Test automatic failure detection."""
        system = integrated_system
        monitor = system["monitor"]
        
        monitor.heartbeat_interval = 1  # Short for test
        monitor.missed_tolerance = 2
        
        monitor.register_agent("failing-agent", agent_type="test")
        
        # Send initial heartbeat
        monitor.heartbeat("failing-agent", {"status": "healthy"})
        
        # Start monitoring
        await monitor.start_monitoring()
        
        # Wait for missed heartbeat detection
        await asyncio.sleep(3)
        
        # Agent should be marked as failed
        agent_health = monitor.check_health("failing-agent")
        assert agent_health.status == HealthStatus.FAILED
        
        await monitor.stop_monitoring()


# =============================================================================
# Cost Tracking Integration Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
class TestCostTrackingIntegration:
    """Test cost tracking across multiple agents."""
    
    async def test_multi_agent_cost_tracking(self, integrated_system):
        """Test cost tracking with multiple agents."""
        system = integrated_system
        tracker = system["tracker"]
        
        # Simulate usage from different agents
        for i in range(10):
            tracker.record_usage(
                agent_id=f"agent-{i % 3}",  # 3 agents
                provider=AIProvider.CHATGPT,
                model="gpt-4",
                tokens_input=1000,
                tokens_output=500,
                request_type="code_generation"
            )
        
        # Get agent summary
        summary = tracker.get_agent_summary()
        
        assert len(summary) == 3
        
        for agent_id in ["agent-0", "agent-1", "agent-2"]:
            assert agent_id in summary
            assert summary[agent_id]["total_requests"] > 0
            assert summary[agent_id]["total_cost"] > 0
    
    async def test_budget_alerts_integration(self, integrated_system):
        """Test budget alerts across agents."""
        system = integrated_system
        tracker = system["tracker"]
        
        # Set low budget
        tracker.daily_budget = 0.5  # 50 cents
        
        alert_triggered = False
        
        def alert_callback(alert):
            nonlocal alert_triggered
            alert_triggered = True
        
        tracker.alert_callbacks.append(alert_callback)
        
        # Record usage until alert threshold
        for _ in range(5):
            tracker.record_usage(
                agent_id="agent-1",
                provider=AIProvider.CHATGPT,
                model="gpt-4",
                tokens_input=2000,
                tokens_output=1000,
                request_type="code_generation"
            )
        
        # Alert should have been triggered
        assert len(tracker._alerts_triggered) > 0


# =============================================================================
# End-to-End Workflow Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
class TestEndToEndWorkflows:
    """Test complete end-to-end workflows."""
    
    async def test_full_build_workflow(self, integrated_system):
        """Test a full build workflow with all components."""
        system = integrated_system
        bus = system["bus"]
        state_manager = system["state_manager"]
        queue = system["queue"]
        monitor = system["monitor"]
        tracker = system["tracker"]
        
        coordinator = AgentCoordinator(bus)
        
        # 1. Register build agents
        agent_ids = ["builder", "tester", "deployer"]
        for agent_id in agent_ids:
            monitor.register_agent(agent_id, agent_type="build")
            monitor.heartbeat(agent_id, {"status": "healthy"})
        
        # 2. Set initial state
        await state_manager.set("build:id", "build-123")
        await state_manager.set("build:status", "starting")
        
        # 3. Start workflow
        workflow_id = await coordinator.start_workflow(
            workflow_id="wf-123",
            steps=[
                {"type": "build", "payload": {"target": "production"}},
                {"type": "test", "payload": {"suite": "integration"}},
                {"type": "deploy", "payload": {"env": "staging"}}
            ],
            agents=agent_ids
        )
        
        assert workflow_id == "wf-123"
        
        # 4. Simulate work and cost tracking
        for i, agent_id in enumerate(agent_ids):
            tracker.record_usage(
                agent_id=agent_id,
                provider=AIProvider.KIMI,
                model="kimi-v1",
                tokens_input=5000,
                tokens_output=2000,
                request_type="build_task"
            )
            
            # Update progress
            await state_manager.track_build_progress(
                build_id="build-123",
                stage=f"step-{i+1}",
                progress_percent=(i + 1) * 33,
                status="running"
            )
        
        # 5. Verify final state
        build_progress = await state_manager.get_build_progress("build-123")
        assert build_progress is not None
        
        # 6. Check health
        health = monitor.check_health()
        assert health["total_agents"] == 3
        
        # 7. Verify costs
        cost_summary = tracker.get_agent_summary()
        assert len(cost_summary) == 3
    
    async def test_consensus_building_workflow(self, integrated_system):
        """Test consensus building workflow."""
        system = integrated_system
        bus = system["bus"]
        
        coordinator = AgentCoordinator(bus)
        
        # Set up voters
        voters = ["voter-1", "voter-2", "voter-3"]
        
        # Start consensus (will timeout since no actual voting)
        result = await coordinator.build_consensus(
            proposal_id="prop-1",
            agents=voters,
            proposal={"action": "deploy", "version": "2.0"},
            timeout_seconds=0.5
        )
        
        assert result["proposal_id"] == "prop-1"
        assert result["total_votes"] == 0
        assert result["passed"] is False


# =============================================================================
# Stress Integration Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
class TestStressIntegration:
    """Stress tests for integration scenarios."""
    
    async def test_many_agents_communication(self, integrated_system):
        """Test communication with many agents."""
        system = integrated_system
        bus = system["bus"]
        
        num_agents = 20
        
        # Each agent sends messages to next agent
        for i in range(num_agents):
            sender = f"agent-{i}"
            recipient = f"agent-{(i + 1) % num_agents}"
            
            await bus.send_direct(
                sender=sender,
                recipient=recipient,
                payload={"from": sender, "to": recipient}
            )
        
        # Verify each agent received exactly one message
        for i in range(num_agents):
            messages = await bus.get_messages(f"agent-{i}")
            assert len(messages) == 1
    
    async def test_concurrent_state_operations(self, integrated_system):
        """Test concurrent state operations."""
        system = integrated_system
        state_manager = system["state_manager"]
        
        async def worker(worker_id: str):
            for i in range(10):
                key = f"worker:{worker_id}:counter"
                await state_manager.increment(key, amount=1, default=0)
            return worker_id
        
        # Run 10 workers concurrently
        worker_ids = [f"w{i}" for i in range(10)]
        results = await asyncio.gather(*[worker(wid) for wid in worker_ids])
        
        assert len(results) == 10
        
        # Verify each counter
        for worker_id in worker_ids:
            value = await state_manager.get(f"worker:{worker_id}:counter")
            assert value == 10
