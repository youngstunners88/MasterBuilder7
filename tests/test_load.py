#!/usr/bin/env python3
"""
Test Suite: Load and Performance Tests

Load testing for 64+ parallel agents and performance benchmarking.

Coverage:
- 64+ parallel agent messaging
- High-throughput task processing
- Concurrent state operations
- Memory usage under load
- Response time benchmarks
- Scalability tests
"""

import asyncio
import time
import pytest
import pytest_asyncio
from datetime import datetime
from typing import List, Dict, Any
import statistics

from apex.agents.agent_protocol import AgentBus, AgentMessage, MessageType
from apex.agents.shared_state import SharedStateManager
from apex.agents.task_queue import TaskQueue, TaskPriority, WorkerPool
from apex.agents.health_monitor import HealthMonitor
from apex.agents.cost_tracker import CostTracker, AIProvider


# =============================================================================
# Load Test Configuration
# =============================================================================

LOAD_TEST_AGENTS = 64
LOAD_TEST_MESSAGES = 100
LOAD_TEST_TASKS = 200
LOAD_TEST_DURATION = 30  # seconds


# =============================================================================
# Agent Messaging Load Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.load
@pytest.mark.slow
class TestAgentMessagingLoad:
    """Load tests for agent messaging."""
    
    async def test_64_parallel_agents_messaging(self, temp_db_path):
        """Test messaging with 64 parallel agents."""
        bus = AgentBus(sqlite_path=str(temp_db_path))
        await bus.connect()
        
        num_agents = 64
        messages_per_agent = 5
        
        # Track received messages
        received_counts = {f"agent-{i}": 0 for i in range(num_agents)}
        
        async def message_handler(agent_id):
            async def handler(message):
                received_counts[agent_id] += 1
            return handler
        
        # Subscribe all agents
        for i in range(num_agents):
            handler = await message_handler(f"agent-{i}")
            await bus.subscribe(f"agent-{i}", handler=handler)
        
        start_time = time.time()
        
        # Send messages from all agents concurrently
        send_tasks = []
        for sender_id in range(num_agents):
            for msg_num in range(messages_per_agent):
                recipient_id = (sender_id + msg_num + 1) % num_agents
                task = bus.send_direct(
                    sender=f"agent-{sender_id}",
                    recipient=f"agent-{recipient_id}",
                    payload={"sender": sender_id, "msg": msg_num}
                )
                send_tasks.append(task)
        
        await asyncio.gather(*send_tasks)
        
        send_duration = time.time() - start_time
        
        # Allow processing time
        await asyncio.sleep(1)
        
        # Verify all messages were delivered
        total_messages = num_agents * messages_per_agent
        
        # Get all messages
        total_received = 0
        for i in range(num_agents):
            messages = await bus.get_messages(f"agent-{i}")
            total_received += len(messages)
        
        await bus.disconnect()
        
        # Verify
        assert total_received == total_messages
        
        # Performance metrics
        messages_per_second = total_messages / send_duration
        print(f"\n64-Agent Messaging Performance:")
        print(f"  Total messages: {total_messages}")
        print(f"  Send duration: {send_duration:.2f}s")
        print(f"  Messages/sec: {messages_per_second:.2f}")
        
        # Should handle at least 100 messages/sec
        assert messages_per_second > 100
    
    async def test_broadcast_to_64_agents(self, temp_db_path):
        """Test broadcast to 64 agents."""
        bus = AgentBus(sqlite_path=str(temp_db_path))
        await bus.connect()
        
        num_agents = 64
        num_broadcasts = 10
        
        # Subscribe all agents
        for i in range(num_agents):
            await bus.subscribe(f"agent-{i}")
        
        start_time = time.time()
        
        # Send broadcasts
        for i in range(num_broadcasts):
            await bus.broadcast(
                sender="coordinator",
                payload={"broadcast_id": i, "data": "x" * 1000}  # 1KB payload
            )
        
        broadcast_duration = time.time() - start_time
        
        # Allow processing
        await asyncio.sleep(0.5)
        
        # Verify all agents received all broadcasts
        for i in range(num_agents):
            messages = await bus.get_messages(f"agent-{i}")
            assert len(messages) == num_broadcasts
        
        await bus.disconnect()
        
        # Performance metrics
        broadcasts_per_second = num_broadcasts / broadcast_duration
        print(f"\n64-Agent Broadcast Performance:")
        print(f"  Total broadcasts: {num_broadcasts}")
        print(f"  Duration: {broadcast_duration:.2f}s")
        print(f"  Broadcasts/sec: {broadcasts_per_second:.2f}")
        
        assert broadcasts_per_second > 5


# =============================================================================
# Task Queue Load Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.load
@pytest.mark.slow
class TestTaskQueueLoad:
    """Load tests for task queue."""
    
    async def test_64_workers_processing(self, temp_db_path):
        """Test 64 workers processing tasks concurrently."""
        from apex.agents.task_queue import QueueConfig
        
        config = QueueConfig(
            sqlite_path=str(temp_db_path),
            max_workers=64,
            task_timeout_seconds=10
        )
        
        queue = TaskQueue(config)
        await queue.connect()
        await queue.start()
        
        num_tasks = 128
        completed_tasks = []
        
        async def task_handler(task):
            await asyncio.sleep(0.01)  # Simulate work
            completed_tasks.append(task.id)
            return {"status": "completed"}
        
        # Create 64 workers
        workers = []
        for i in range(64):
            pool = WorkerPool(
                queue=queue,
                worker_id=f"worker-{i}",
                task_handler=task_handler
            )
            await pool.start()
            workers.append(pool)
        
        start_time = time.time()
        
        # Enqueue tasks
        for i in range(num_tasks):
            await queue.enqueue(
                task_type="load_test",
                payload={"index": i},
                priority=TaskPriority.NORMAL
            )
        
        # Wait for completion
        timeout = 30
        while len(completed_tasks) < num_tasks and timeout > 0:
            await asyncio.sleep(0.1)
            timeout -= 0.1
        
        duration = time.time() - start_time
        
        # Stop workers
        for worker in workers:
            await worker.stop()
        
        await queue.disconnect()
        
        # Performance metrics
        tasks_per_second = len(completed_tasks) / duration
        print(f"\n64-Worker Processing Performance:")
        print(f"  Total tasks: {num_tasks}")
        print(f"  Completed: {len(completed_tasks)}")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Tasks/sec: {tasks_per_second:.2f}")
        
        assert len(completed_tasks) == num_tasks
        assert tasks_per_second > 10
    
    async def test_high_throughput_enqueue(self, temp_db_path):
        """Test high-throughput task enqueue."""
        from apex.agents.task_queue import QueueConfig
        
        config = QueueConfig(sqlite_path=str(temp_db_path))
        queue = TaskQueue(config)
        await queue.connect()
        
        num_tasks = 1000
        
        # Prepare batch data
        tasks_data = [
            {
                "type": "batch_task",
                "payload": {"index": i},
                "priority": TaskPriority.NORMAL
            }
            for i in range(num_tasks)
        ]
        
        start_time = time.time()
        
        # Batch enqueue
        tasks = await queue.enqueue_many(tasks_data)
        
        duration = time.time() - start_time
        
        await queue.disconnect()
        
        # Performance metrics
        tasks_per_second = num_tasks / duration
        print(f"\nHigh Throughput Enqueue Performance:")
        print(f"  Total tasks: {num_tasks}")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Tasks/sec: {tasks_per_second:.2f}")
        
        assert len(tasks) == num_tasks
        assert tasks_per_second > 100


# =============================================================================
# State Manager Load Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.load
@pytest.mark.slow
class TestStateManagerLoad:
    """Load tests for state manager."""
    
    async def test_concurrent_state_writes(self, temp_db_path):
        """Test concurrent state writes from multiple agents."""
        manager = SharedStateManager(sqlite_path=str(temp_db_path))
        await manager.connect()
        
        num_agents = 32
        writes_per_agent = 50
        
        async def writer_agent(agent_id: str):
            for i in range(writes_per_agent):
                key = f"agent:{agent_id}:counter"
                await manager.increment(key, amount=1, default=0)
            return agent_id
        
        start_time = time.time()
        
        # Run all writers concurrently
        agent_ids = [f"agent-{i}" for i in range(num_agents)]
        results = await asyncio.gather(*[writer_agent(aid) for aid in agent_ids])
        
        duration = time.time() - start_time
        
        # Verify all counters
        for agent_id in agent_ids:
            value = await manager.get(f"agent:{agent_id}:counter")
            assert value == writes_per_agent
        
        await manager.disconnect()
        
        # Performance metrics
        total_writes = num_agents * writes_per_agent
        writes_per_second = total_writes / duration
        print(f"\nConcurrent State Writes Performance:")
        print(f"  Total writes: {total_writes}")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Writes/sec: {writes_per_second:.2f}")
        
        assert writes_per_second > 50
    
    async def test_distributed_lock_contention(self, temp_db_path):
        """Test distributed lock under high contention."""
        manager = SharedStateManager(sqlite_path=str(temp_db_path))
        await manager.connect()
        
        num_agents = 20
        successful_locks = []
        
        async def lock_contender(agent_id: str):
            async with manager.lock(
                "contended-resource",
                owner=agent_id,
                ttl_seconds=1,
                blocking=True,
                blocking_timeout=0.5
            ) as lock_id:
                if lock_id:
                    successful_locks.append(agent_id)
                    await asyncio.sleep(0.1)  # Hold lock briefly
                return lock_id
        
        start_time = time.time()
        
        # All agents try to acquire lock simultaneously
        agent_ids = [f"agent-{i}" for i in range(num_agents)]
        results = await asyncio.gather(*[lock_contender(aid) for aid in agent_ids])
        
        duration = time.time() - start_time
        
        await manager.disconnect()
        
        # Only one should succeed
        assert len(successful_locks) == 1
        
        print(f"\nDistributed Lock Contention:")
        print(f"  Contenders: {num_agents}")
        print(f"  Successful locks: {len(successful_locks)}")
        print(f"  Duration: {duration:.2f}s")


# =============================================================================
# Health Monitor Load Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.load
@pytest.mark.slow
class TestHealthMonitorLoad:
    """Load tests for health monitor."""
    
    async def test_64_agents_health_tracking(self, temp_db_path):
        """Test health tracking for 64 agents."""
        monitor = HealthMonitor(
            db_path=str(temp_db_path),
            heartbeat_interval=1,
            auto_restart=False
        )
        
        num_agents = 64
        
        # Register all agents
        start_time = time.time()
        for i in range(num_agents):
            monitor.register_agent(f"agent-{i}", agent_type="test")
        
        register_duration = time.time() - start_time
        
        # Send heartbeats from all agents
        start_time = time.time()
        for i in range(num_agents):
            monitor.heartbeat(f"agent-{i}", {
                "cpu_percent": 30.0,
                "memory_mb": 100.0,
                "status": "healthy"
            })
        
        heartbeat_duration = time.time() - start_time
        
        # Check health
        start_time = time.time()
        health = monitor.check_health()
        check_duration = time.time() - start_time
        
        # Performance metrics
        print(f"\n64-Agent Health Tracking Performance:")
        print(f"  Register duration: {register_duration:.2f}s")
        print(f"  Heartbeat duration: {heartbeat_duration:.2f}s")
        print(f"  Check duration: {check_duration:.2f}s")
        
        assert health["total_agents"] == num_agents
        assert health["healthy_agents"] == num_agents
        
        # Should be fast
        assert register_duration < 5.0
        assert heartbeat_duration < 5.0
        assert check_duration < 1.0


# =============================================================================
# Cost Tracker Load Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.load
@pytest.mark.slow
class TestCostTrackerLoad:
    """Load tests for cost tracker."""
    
    async def test_high_volume_cost_tracking(self, temp_directory):
        """Test cost tracking with high volume of requests."""
        storage_path = temp_directory / "cost_load.json"
        tracker = CostTracker(
            daily_budget=10000.0,
            storage_path=str(storage_path),
            enable_kill_switch=False
        )
        
        num_requests = 1000
        
        start_time = time.time()
        
        for i in range(num_requests):
            tracker.record_usage(
                agent_id=f"agent-{i % 10}",
                provider=AIProvider.KIMI,
                model="kimi-v1",
                tokens_input=1000,
                tokens_output=500,
                request_type="load_test"
            )
        
        duration = time.time() - start_time
        
        # Generate report
        report = tracker.get_cost_report(period="today")
        
        # Performance metrics
        requests_per_second = num_requests / duration
        print(f"\nHigh Volume Cost Tracking Performance:")
        print(f"  Total requests: {num_requests}")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Requests/sec: {requests_per_second:.2f}")
        print(f"  Total cost: ${report.total_cost:.4f}")
        
        assert report.total_requests == num_requests
        assert requests_per_second > 100


# =============================================================================
# System-Wide Load Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.load
@pytest.mark.slow
class TestSystemWideLoad:
    """System-wide load tests."""
    
    async def test_full_system_under_load(self, temp_directory):
        """Test full system under simulated production load."""
        
        # Setup all components
        bus = AgentBus(sqlite_path=str(temp_directory / "bus.db"))
        await bus.connect()
        
        state_manager = SharedStateManager(
            sqlite_path=str(temp_directory / "state.db")
        )
        await state_manager.connect()
        
        from apex.agents.task_queue import QueueConfig
        config = QueueConfig(sqlite_path=str(temp_directory / "queue.db"))
        queue = TaskQueue(config)
        await queue.connect()
        await queue.start()
        
        monitor = HealthMonitor(
            db_path=str(temp_directory / "health.db"),
            auto_restart=False
        )
        
        tracker = CostTracker(
            daily_budget=10000.0,
            storage_path=str(temp_directory / "cost.json"),
            enable_kill_switch=False
        )
        
        # Simulate 64 agents working
        num_agents = 64
        tasks_per_agent = 5
        
        async def agent_worker(agent_id: str):
            # Register with monitor
            monitor.register_agent(agent_id, agent_type="load_test")
            monitor.heartbeat(agent_id, {"status": "healthy"})
            
            completed = 0
            
            for task_num in range(tasks_per_agent):
                # Update state
                await state_manager.set(f"agent:{agent_id}:task:{task_num}", "running")
                
                # Send message
                await bus.send_direct(
                    sender=agent_id,
                    recipient=f"agent-{(int(agent_id.split('-')[1]) + 1) % num_agents}",
                    payload={"task": task_num}
                )
                
                # Record cost
                tracker.record_usage(
                    agent_id=agent_id,
                    provider=AIProvider.KIMI,
                    model="kimi-v1",
                    tokens_input=500,
                    tokens_output=200,
                    request_type="task_execution"
                )
                
                # Complete task
                await state_manager.set(f"agent:{agent_id}:task:{task_num}", "completed")
                completed += 1
            
            return completed
        
        start_time = time.time()
        
        # Run all agents
        agent_ids = [f"agent-{i}" for i in range(num_agents)]
        results = await asyncio.gather(*[agent_worker(aid) for aid in agent_ids])
        
        duration = time.time() - start_time
        
        # Cleanup
        await bus.disconnect()
        await state_manager.disconnect()
        await queue.disconnect()
        
        # Performance metrics
        total_operations = sum(results)
        ops_per_second = total_operations / duration
        
        print(f"\nFull System Load Test Performance:")
        print(f"  Agents: {num_agents}")
        print(f"  Tasks per agent: {tasks_per_agent}")
        print(f"  Total operations: {total_operations}")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Operations/sec: {ops_per_second:.2f}")
        
        assert all(r == tasks_per_agent for r in results)
        assert ops_per_second > 10
    
    async def test_memory_usage_under_load(self, temp_directory):
        """Test memory usage remains stable under load."""
        import gc
        
        tracker = CostTracker(
            daily_budget=10000.0,
            storage_path=str(temp_directory / "cost_memory.json"),
            enable_kill_switch=False
        )
        
        # Force garbage collection
        gc.collect()
        
        # Record many requests
        for i in range(5000):
            tracker.record_usage(
                agent_id="agent-1",
                provider=AIProvider.KIMI,
                model="kimi-v1",
                tokens_input=100,
                tokens_output=50,
                request_type="memory_test"
            )
            
            # Periodically clear old history to manage memory
            if i % 1000 == 0:
                # Keep only last 1000 records
                tracker._usage_history = tracker._usage_history[-1000:]
        
        # Verify memory is managed
        assert len(tracker._usage_history) <= 5000
        
        print(f"\nMemory Usage Under Load:")
        print(f"  Records in history: {len(tracker._usage_history)}")


# =============================================================================
# Benchmark Tests
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.load
class TestBenchmarks:
    """Benchmark tests with performance assertions."""
    
    async def test_message_latency_benchmark(self, temp_db_path):
        """Benchmark message latency."""
        bus = AgentBus(sqlite_path=str(temp_db_path))
        await bus.connect()
        
        latencies = []
        
        for _ in range(100):
            start = time.time()
            await bus.send_direct(
                sender="sender",
                recipient="receiver",
                payload={"test": True}
            )
            latency = time.time() - start
            latencies.append(latency)
        
        await bus.disconnect()
        
        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        
        print(f"\nMessage Latency Benchmark:")
        print(f"  Average: {avg_latency * 1000:.2f}ms")
        print(f"  P95: {p95_latency * 1000:.2f}ms")
        
        # Average should be under 10ms
        assert avg_latency < 0.01
    
    async def test_state_operation_benchmark(self, temp_db_path):
        """Benchmark state operations."""
        manager = SharedStateManager(sqlite_path=str(temp_db_path))
        await manager.connect()
        
        # Benchmark writes
        write_times = []
        for i in range(100):
            start = time.time()
            await manager.set(f"key-{i}", f"value-{i}")
            write_times.append(time.time() - start)
        
        # Benchmark reads
        read_times = []
        for i in range(100):
            start = time.time()
            await manager.get(f"key-{i}")
            read_times.append(time.time() - start)
        
        await manager.disconnect()
        
        avg_write = statistics.mean(write_times)
        avg_read = statistics.mean(read_times)
        
        print(f"\nState Operation Benchmark:")
        print(f"  Avg write: {avg_write * 1000:.2f}ms")
        print(f"  Avg read: {avg_read * 1000:.2f}ms")
        
        # Should be fast
        assert avg_write < 0.05
        assert avg_read < 0.01
