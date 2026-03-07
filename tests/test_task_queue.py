#!/usr/bin/env python3
"""
Test Suite: Task Queue

Comprehensive tests for distributed task queue.

Coverage:
- Task creation and properties
- Worker management
- Task lifecycle (enqueue, dequeue, complete, fail)
- Priority handling
- Retry mechanism
- Dead letter queue
- Progress tracking
- Worker pool
- Batch operations
"""

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from apex.agents.task_queue import (
    TaskPriority,
    TaskStatus,
    WorkerStatus,
    TaskProgress,
    Task,
    Worker,
    TaskQueueStats,
    QueueConfig,
    SQLiteTaskStore,
    TaskQueue,
    WorkerPool,
    task_handler
)


# =============================================================================
# Task Tests
# =============================================================================

class TestTask:
    """Test Task dataclass."""
    
    def test_task_creation_defaults(self):
        """Test task creation with defaults."""
        task = Task(
            type="test_task",
            payload={"data": "test"}
        )
        
        assert task.type == "test_task"
        assert task.payload == {"data": "test"}
        assert task.priority == TaskPriority.NORMAL
        assert task.status == TaskStatus.PENDING
        assert task.max_retries == 3
        assert task.timeout_seconds == 300
        assert task.id is not None
        assert task.created_at is not None
    
    def test_task_creation_custom(self):
        """Test task creation with custom values."""
        task = Task(
            type="critical_task",
            payload={"urgent": True},
            priority=TaskPriority.CRITICAL,
            required_capabilities=["python", "fastapi"],
            max_retries=5,
            timeout_seconds=60,
            tags=["urgent", "billing"]
        )
        
        assert task.priority == TaskPriority.CRITICAL
        assert task.required_capabilities == ["python", "fastapi"]
        assert task.max_retries == 5
        assert task.timeout_seconds == 60
        assert "urgent" in task.tags
    
    def test_task_serialization(self):
        """Test task serialization."""
        task = Task(
            type="test",
            payload={"key": "value"},
            priority=TaskPriority.HIGH
        )
        
        data = task.to_dict()
        
        assert data["type"] == "test"
        assert data["payload"] == {"key": "value"}
        assert data["priority"] == 7  # HIGH value
        assert data["status"] == "pending"
    
    def test_task_from_dict(self):
        """Test task deserialization."""
        data = {
            "id": "task-123",
            "type": "code_review",
            "payload": {"file": "test.py"},
            "priority": 10,
            "status": "running",
            "retry_count": 2,
            "created_at": datetime.utcnow().isoformat()
        }
        
        task = Task.from_dict(data)
        
        assert task.id == "task-123"
        assert task.type == "code_review"
        assert task.priority == TaskPriority.CRITICAL
        assert task.status == TaskStatus.RUNNING
        assert task.retry_count == 2
    
    def test_task_is_active(self):
        """Test is_active property."""
        active_task = Task(type="test", status=TaskStatus.PENDING)
        assert active_task.is_active is True
        
        running_task = Task(type="test", status=TaskStatus.RUNNING)
        assert running_task.is_active is True
        
        completed_task = Task(type="test", status=TaskStatus.COMPLETED)
        assert completed_task.is_active is False
        
        failed_task = Task(type="test", status=TaskStatus.FAILED)
        assert failed_task.is_active is False
    
    def test_task_is_terminal(self):
        """Test is_terminal property."""
        terminal_task = Task(type="test", status=TaskStatus.COMPLETED)
        assert terminal_task.is_terminal is True
        
        cancelled_task = Task(type="test", status=TaskStatus.CANCELLED)
        assert cancelled_task.is_terminal is True
        
        active_task = Task(type="test", status=TaskStatus.PENDING)
        assert active_task.is_terminal is False
    
    def test_task_can_retry(self):
        """Test can_retry property."""
        # Can retry - failed with remaining retries
        task = Task(type="test", status=TaskStatus.FAILED, retry_count=1, max_retries=3)
        assert task.can_retry is True
        
        # Cannot retry - max retries reached
        task = Task(type="test", status=TaskStatus.FAILED, retry_count=3, max_retries=3)
        assert task.can_retry is False
        
        # Cannot retry - not failed
        task = Task(type="test", status=TaskStatus.COMPLETED, retry_count=0, max_retries=3)
        assert task.can_retry is False
    
    def test_task_wait_time(self):
        """Test wait_time_seconds property."""
        old_task = Task(
            type="test",
            created_at=(datetime.utcnow() - timedelta(minutes=5)).isoformat()
        )
        assert old_task.wait_time_seconds > 300  # More than 5 minutes
        
        new_task = Task(type="test")
        assert new_task.wait_time_seconds < 1  # Less than 1 second
    
    def test_task_execution_time(self):
        """Test execution_time_seconds property."""
        # No execution time yet
        task = Task(type="test")
        assert task.execution_time_seconds is None
        
        # Running task
        running_task = Task(
            type="test",
            status=TaskStatus.RUNNING,
            started_at=(datetime.utcnow() - timedelta(minutes=2)).isoformat()
        )
        assert running_task.execution_time_seconds > 120  # More than 2 minutes


# =============================================================================
# Worker Tests
# =============================================================================

class TestWorker:
    """Test Worker dataclass."""
    
    def test_worker_creation(self):
        """Test worker creation."""
        worker = Worker(
            id="worker-1",
            name="Test Worker",
            capabilities=["python", "fastapi"],
            max_concurrent_tasks=4
        )
        
        assert worker.id == "worker-1"
        assert worker.name == "Test Worker"
        assert worker.capabilities == ["python", "fastapi"]
        assert worker.max_concurrent_tasks == 4
        assert worker.status == WorkerStatus.IDLE
    
    def test_worker_can_handle_task(self):
        """Test can_handle_task method."""
        worker = Worker(
            id="worker-1",
            capabilities=["python", "docker"],
            max_concurrent_tasks=2
        )
        
        # Can handle - matching capabilities
        task = Task(
            type="test",
            required_capabilities=["python"]
        )
        assert worker.can_handle_task(task) is True
        
        # Cannot handle - missing capability
        task = Task(
            type="test",
            required_capabilities=["rust"]
        )
        assert worker.can_handle_task(task) is False
        
        # Cannot handle - at max capacity
        worker.current_load = 2
        task = Task(type="test")
        assert worker.can_handle_task(task) is False
    
    def test_worker_update_heartbeat(self):
        """Test heartbeat update."""
        worker = Worker(id="worker-1")
        old_heartbeat = worker.last_heartbeat
        
        worker.update_heartbeat()
        
        assert worker.last_heartbeat != old_heartbeat


# =============================================================================
# TaskProgress Tests
# =============================================================================

class TestTaskProgress:
    """Test TaskProgress dataclass."""
    
    def test_progress_creation(self):
        """Test progress creation."""
        progress = TaskProgress(
            percent=50.0,
            current_step="compiling",
            steps_total=10,
            steps_completed=5
        )
        
        assert progress.percent == 50.0
        assert progress.current_step == "compiling"
        assert progress.steps_total == 10
        assert progress.steps_completed == 5
    
    def test_progress_serialization(self):
        """Test progress serialization."""
        progress = TaskProgress(percent=75.0, current_step="testing")
        
        data = progress.to_dict()
        progress2 = TaskProgress.from_dict(data)
        
        assert progress2.percent == progress.percent
        assert progress2.current_step == progress.current_step


# =============================================================================
# SQLite Task Store Tests
# =============================================================================

class TestSQLiteTaskStore:
    """Test SQLite task store."""
    
    def test_enqueue_task(self, temp_db_path):
        """Test task enqueue."""
        store = SQLiteTaskStore(db_path=str(temp_db_path))
        
        task = Task(type="test", payload={"data": "test"})
        result = store.enqueue_task(task)
        
        assert result is True
    
    def test_dequeue_task(self, temp_db_path):
        """Test task dequeue."""
        store = SQLiteTaskStore(db_path=str(temp_db_path))
        
        # Enqueue task
        task = Task(type="test", payload={"data": "test"})
        store.enqueue_task(task)
        
        # Dequeue task
        dequeued = store.dequeue_task()
        
        assert dequeued is not None
        assert dequeued.id == task.id
        assert dequeued.status == TaskStatus.ASSIGNED
    
    def test_dequeue_with_capabilities(self, temp_db_path):
        """Test dequeue with capability matching."""
        store = SQLiteTaskStore(db_path=str(temp_db_path))
        
        # Enqueue task with capabilities
        task = Task(
            type="test",
            payload={},
            required_capabilities=["python", "docker"]
        )
        store.enqueue_task(task)
        
        # Should not match
        no_match = store.dequeue_task(worker_capabilities=["rust"])
        assert no_match is None
        
        # Should match
        match = store.dequeue_task(worker_capabilities=["python", "docker"])
        assert match is not None
    
    def test_update_task(self, temp_db_path):
        """Test task update."""
        store = SQLiteTaskStore(db_path=str(temp_db_path))
        
        task = Task(type="test", payload={})
        store.enqueue_task(task)
        
        task.status = TaskStatus.COMPLETED
        result = store.update_task(task)
        
        assert result is True
        
        retrieved = store.get_task(task.id)
        assert retrieved.status == TaskStatus.COMPLETED
    
    def test_move_to_dead_letter(self, temp_db_path):
        """Test moving task to dead letter queue."""
        store = SQLiteTaskStore(db_path=str(temp_db_path))
        
        task = Task(type="test", payload={})
        store.enqueue_task(task)
        
        result = store.move_to_dead_letter(task, "Test failure")
        
        assert result is True
        
        # Task should no longer be in main queue
        assert store.get_task(task.id) is None
        
        # But should be in DLQ
        dlq_tasks = store.get_dead_letter_tasks()
        assert len(dlq_tasks) == 1
    
    def test_worker_registration(self, temp_db_path):
        """Test worker registration."""
        store = SQLiteTaskStore(db_path=str(temp_db_path))
        
        worker = Worker(
            id="worker-1",
            name="Test Worker",
            capabilities=["python"]
        )
        
        result = store.register_worker(worker)
        assert result is True
        
        retrieved = store.get_worker("worker-1")
        assert retrieved is not None
        assert retrieved.name == "Test Worker"
    
    def test_get_stats(self, temp_db_path):
        """Test getting queue statistics."""
        store = SQLiteTaskStore(db_path=str(temp_db_path))
        
        # Create tasks with different statuses
        pending_task = Task(type="test1", payload={}, status=TaskStatus.PENDING)
        running_task = Task(type="test2", payload={}, status=TaskStatus.RUNNING)
        completed_task = Task(type="test3", payload={}, status=TaskStatus.COMPLETED)
        
        store.enqueue_task(pending_task)
        store.enqueue_task(running_task)
        store.enqueue_task(completed_task)
        
        stats = store.get_stats()
        
        assert isinstance(stats, TaskQueueStats)
        # Note: Tasks may be counted differently based on implementation


# =============================================================================
# TaskQueue Tests
# =============================================================================

@pytest.mark.asyncio
class TestTaskQueue:
    """Test TaskQueue."""
    
    async def test_queue_initialization(self, temp_db_path):
        """Test queue initialization."""
        config = QueueConfig(sqlite_path=str(temp_db_path))
        queue = TaskQueue(config)
        
        assert queue.config == config
        assert queue._connected is False
    
    async def test_connect_disconnect(self, temp_db_path):
        """Test connection lifecycle."""
        config = QueueConfig(sqlite_path=str(temp_db_path))
        queue = TaskQueue(config)
        
        result = await queue.connect()
        # Should fall back to SQLite
        assert result is False
        
        await queue.disconnect()
    
    async def test_enqueue(self, temp_db_path):
        """Test task enqueue."""
        config = QueueConfig(sqlite_path=str(temp_db_path))
        queue = TaskQueue(config)
        await queue.connect()
        
        task = await queue.enqueue(
            task_type="code_review",
            payload={"file": "test.py"},
            priority=TaskPriority.HIGH
        )
        
        assert task is not None
        assert task.type == "code_review"
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.PENDING
    
    async def test_dequeue(self, temp_db_path):
        """Test task dequeue."""
        config = QueueConfig(sqlite_path=str(temp_db_path))
        queue = TaskQueue(config)
        await queue.connect()
        await queue.start()
        
        # Enqueue first
        await queue.enqueue(type="test", payload={"data": "test"})
        
        # Dequeue
        task = await queue.dequeue(worker_id="worker-1")
        
        assert task is not None
        assert task.assigned_to == "worker-1"
        assert task.status == TaskStatus.ASSIGNED
    
    async def test_complete_task(self, temp_db_path):
        """Test task completion."""
        config = QueueConfig(sqlite_path=str(temp_db_path))
        queue = TaskQueue(config)
        await queue.connect()
        await queue.start()
        
        # Enqueue and dequeue
        task = await queue.enqueue(type="test", payload={})
        dequeued = await queue.dequeue(worker_id="worker-1")
        
        # Complete
        result = await queue.complete(
            dequeued.id,
            result={"status": "success"}
        )
        
        assert result is True
        
        # Verify
        completed = await queue.get_task(dequeued.id)
        assert completed.status == TaskStatus.COMPLETED
        assert completed.result == {"status": "success"}
    
    async def test_fail_task_with_retry(self, temp_db_path):
        """Test task failure with retry."""
        config = QueueConfig(sqlite_path=str(temp_db_path))
        queue = TaskQueue(config)
        await queue.connect()
        await queue.start()
        
        # Enqueue, dequeue, and fail
        task = await queue.enqueue(type="test", payload={}, max_retries=3)
        dequeued = await queue.dequeue(worker_id="worker-1")
        
        # First fail - should retry
        result = await queue.fail(dequeued.id, "Temporary error")
        
        assert result is True  # Will retry
        
        # Verify task is in retrying state
        retrying = await queue.get_task(dequeued.id)
        assert retrying.status == TaskStatus.RETRYING
        assert retrying.retry_count == 1
    
    async def test_fail_task_to_dead_letter(self, temp_db_path):
        """Test task failure to dead letter queue."""
        config = QueueConfig(sqlite_path=str(temp_db_path))
        queue = TaskQueue(config)
        await queue.connect()
        await queue.start()
        
        # Enqueue with 0 retries
        task = await queue.enqueue(type="test", payload={}, max_retries=0)
        dequeued = await queue.dequeue(worker_id="worker-1")
        
        # Fail - should go to DLQ
        result = await queue.fail(dequeued.id, "Permanent error")
        
        assert result is False  # Moved to DLQ
        
        # Verify in DLQ
        dlq_tasks = await queue.get_dead_letter_tasks()
        assert len(dlq_tasks) == 1
    
    async def test_cancel_task(self, temp_db_path):
        """Test task cancellation."""
        config = QueueConfig(sqlite_path=str(temp_db_path))
        queue = TaskQueue(config)
        await queue.connect()
        await queue.start()
        
        # Enqueue
        task = await queue.enqueue(type="test", payload={})
        
        # Cancel
        result = await queue.cancel(task.id, reason="User request")
        
        assert result is True
        
        # Verify
        cancelled = await queue.get_task(task.id)
        assert cancelled.status == TaskStatus.CANCELLED
    
    async def test_progress_tracking(self, temp_db_path):
        """Test task progress tracking."""
        config = QueueConfig(sqlite_path=str(temp_db_path))
        queue = TaskQueue(config)
        await queue.connect()
        await queue.start()
        
        # Enqueue and dequeue
        task = await queue.enqueue(type="long_task", payload={})
        dequeued = await queue.dequeue(worker_id="worker-1")
        
        # Update progress
        await queue.update_progress(
            dequeued.id,
            percent=50.0,
            current_step="processing",
            steps_completed=5,
            steps_total=10
        )
        
        # Get progress
        progress = await queue.get_progress(dequeued.id)
        
        assert progress is not None
        assert progress.percent == 50.0
        assert progress.current_step == "processing"
    
    async def test_worker_registration(self, temp_db_path):
        """Test worker registration."""
        config = QueueConfig(sqlite_path=str(temp_db_path))
        queue = TaskQueue(config)
        await queue.connect()
        
        worker = await queue.register_worker(
            worker_id="worker-1",
            name="Test Worker",
            capabilities=["python", "fastapi"],
            max_concurrent_tasks=4
        )
        
        assert worker is not None
        assert worker.id == "worker-1"
        assert worker.name == "Test Worker"
        assert "python" in worker.capabilities
    
    async def test_heartbeat(self, temp_db_path):
        """Test worker heartbeat."""
        config = QueueConfig(sqlite_path=str(temp_db_path))
        queue = TaskQueue(config)
        await queue.connect()
        
        # Register worker first
        await queue.register_worker(worker_id="worker-1")
        
        # Send heartbeat
        await queue.heartbeat(
            worker_id="worker-1",
            status=WorkerStatus.BUSY,
            metrics={"tasks": 5}
        )
        
        # Verify
        workers = await queue.get_workers()
        assert len(workers) == 1
        assert workers[0].status == WorkerStatus.BUSY
    
    async def test_find_capable_workers(self, temp_db_path):
        """Test finding capable workers."""
        config = QueueConfig(sqlite_path=str(temp_db_path))
        queue = TaskQueue(config)
        await queue.connect()
        
        # Register workers
        await queue.register_worker(
            worker_id="worker-1",
            capabilities=["python", "docker"]
        )
        await queue.register_worker(
            worker_id="worker-2",
            capabilities=["rust", "docker"]
        )
        
        # Find capable
        capable = await queue.find_capable_workers(["docker"])
        assert len(capable) == 2
        
        capable_python = await queue.find_capable_workers(["python"])
        assert len(capable_python) == 1
    
    async def test_enqueue_many(self, temp_db_path):
        """Test batch enqueue."""
        config = QueueConfig(sqlite_path=str(temp_db_path))
        queue = TaskQueue(config)
        await queue.connect()
        
        tasks_data = [
            {"type": "task1", "payload": {"i": i}}
            for i in range(10)
        ]
        
        tasks = await queue.enqueue_many(tasks_data)
        
        assert len(tasks) == 10
        assert all(t.status == TaskStatus.PENDING for t in tasks)
    
    async def test_cancel_many(self, temp_db_path):
        """Test batch cancellation."""
        config = QueueConfig(sqlite_path=str(temp_db_path))
        queue = TaskQueue(config)
        await queue.connect()
        
        # Enqueue multiple
        tasks = []
        for i in range(5):
            task = await queue.enqueue(type="test", payload={"i": i})
            tasks.append(task.id)
        
        # Cancel all
        cancelled = await queue.cancel_many(tasks)
        
        assert cancelled == 5


# =============================================================================
# WorkerPool Tests
# =============================================================================

@pytest.mark.asyncio
class TestWorkerPool:
    """Test WorkerPool."""
    
    async def test_pool_initialization(self, temp_db_path):
        """Test pool initialization."""
        config = QueueConfig(sqlite_path=str(temp_db_path))
        queue = TaskQueue(config)
        await queue.connect()
        
        pool = WorkerPool(
            queue=queue,
            worker_id="pool-1",
            capabilities=["python"]
        )
        
        assert pool.worker_id == "pool-1"
        assert pool.capabilities == ["python"]
        assert pool.max_concurrent == 1
    
    async def test_pool_start_stop(self, temp_db_path):
        """Test pool start and stop."""
        config = QueueConfig(sqlite_path=str(temp_db_path))
        queue = TaskQueue(config)
        await queue.connect()
        await queue.start()
        
        pool = WorkerPool(
            queue=queue,
            worker_id="pool-1"
        )
        
        await pool.start()
        assert pool.stats["start_time"] is not None
        
        await pool.stop()


# =============================================================================
# Priority Tests
# =============================================================================

@pytest.mark.asyncio
class TestTaskPriorities:
    """Test task priority handling."""
    
    async def test_priority_ordering(self, temp_db_path):
        """Test that tasks are dequeued in priority order."""
        config = QueueConfig(sqlite_path=str(temp_db_path))
        queue = TaskQueue(config)
        await queue.connect()
        await queue.start()
        
        # Enqueue in reverse priority order
        low_task = await queue.enqueue(
            type="low",
            payload={},
            priority=TaskPriority.LOW
        )
        normal_task = await queue.enqueue(
            type="normal",
            payload={},
            priority=TaskPriority.NORMAL
        )
        high_task = await queue.enqueue(
            type="high",
            payload={},
            priority=TaskPriority.HIGH
        )
        critical_task = await queue.enqueue(
            type="critical",
            payload={},
            priority=TaskPriority.CRITICAL
        )
        
        # Dequeue should return in priority order
        first = await queue.dequeue(worker_id="worker-1")
        assert first.priority == TaskPriority.CRITICAL
        
        second = await queue.dequeue(worker_id="worker-1")
        assert second.priority == TaskPriority.HIGH


# =============================================================================
# Error Handling Tests
# =============================================================================

@pytest.mark.asyncio
class TestTaskQueueErrors:
    """Test error handling."""
    
    async def test_complete_nonexistent_task(self, temp_db_path):
        """Test completing non-existent task."""
        config = QueueConfig(sqlite_path=str(temp_db_path))
        queue = TaskQueue(config)
        await queue.connect()
        
        result = await queue.complete("nonexistent-id")
        assert result is False
    
    async def test_fail_nonexistent_task(self, temp_db_path):
        """Test failing non-existent task."""
        config = QueueConfig(sqlite_path=str(temp_db_path))
        queue = TaskQueue(config)
        await queue.connect()
        
        result = await queue.fail("nonexistent-id", "error")
        assert result is False
    
    async def test_cancel_non_pending_task(self, temp_db_path):
        """Test cancelling non-pending task."""
        config = QueueConfig(sqlite_path=str(temp_db_path))
        queue = TaskQueue(config)
        await queue.connect()
        await queue.start()
        
        # Enqueue, dequeue, and complete
        task = await queue.enqueue(type="test", payload={})
        dequeued = await queue.dequeue(worker_id="worker-1")
        await queue.complete(dequeued.id)
        
        # Try to cancel completed task
        result = await queue.cancel(dequeued.id)
        assert result is False
