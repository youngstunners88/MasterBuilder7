#!/usr/bin/env python3
"""
APEX Task Queue - Usage Examples

This file demonstrates how to use the distributed task queue system.
"""

import asyncio
from datetime import datetime, timedelta
from apex.agents.task_queue import (
    TaskQueue, Task, Worker, TaskPriority, TaskStatus,
    create_task_queue, create_worker_pool, task_handler
)


# Example 1: Basic Task Queue Usage
async def example_basic_usage():
    """Demonstrate basic task queue operations."""
    print("=" * 60)
    print("Example 1: Basic Task Queue Usage")
    print("=" * 60)
    
    # Create queue
    queue = await create_task_queue(
        redis_host="localhost",
        redis_port=6379,
        sqlite_path="/tmp/example_task_queue.db"
    )
    
    # Register a worker
    worker = await queue.register_worker(
        name="my-worker",
        capabilities=["python", "fastapi"],
        max_concurrent_tasks=4
    )
    print(f"✓ Registered worker: {worker.name}")
    
    # Enqueue a task
    task = await queue.enqueue(
        task_type="code_review",
        payload={"file": "app.py", "lines": 150},
        priority=TaskPriority.HIGH,
        required_capabilities=["python"],
        tags=["review", "api"]
    )
    print(f"✓ Enqueued task: {task.id}")
    
    # Dequeue and process
    assigned_task = await queue.dequeue(worker.id, worker.capabilities)
    if assigned_task:
        print(f"✓ Assigned to worker: {assigned_task.id}")
        
        # Simulate processing
        await queue.update_progress(
            assigned_task.id,
            percent=50,
            current_step="analyzing_code"
        )
        
        # Mark complete
        await queue.complete(assigned_task.id, {
            "issues_found": 2,
            "suggestions": ["Add type hints", "Improve error handling"]
        })
        print("✓ Task completed")
    
    # Get statistics
    stats = await queue.get_stats()
    print(f"\nQueue Stats:")
    print(f"  Pending: {stats.total_pending}")
    print(f"  Completed: {stats.total_completed}")
    
    await queue.disconnect()


# Example 2: Priority-Based Scheduling
async def example_priority_scheduling():
    """Demonstrate priority-based task scheduling."""
    print("\n" + "=" * 60)
    print("Example 2: Priority-Based Scheduling")
    print("=" * 60)
    
    queue = await create_task_queue(sqlite_path="/tmp/example_priority.db")
    
    # Enqueue tasks with different priorities
    tasks = []
    for priority in [TaskPriority.LOW, TaskPriority.CRITICAL, TaskPriority.NORMAL, TaskPriority.HIGH]:
        task = await queue.enqueue(
            task_type="process_data",
            payload={"priority": priority.name},
            priority=priority
        )
        tasks.append(task)
        print(f"✓ Enqueued {priority.name} task: {task.id[:8]}...")
    
    # Workers will receive tasks in priority order (CRITICAL > HIGH > NORMAL > LOW)
    print("\nTasks will be processed in priority order: CRITICAL > HIGH > NORMAL > LOW")
    
    await queue.disconnect()


# Example 3: Capability-Based Assignment
async def example_capability_assignment():
    """Demonstrate capability-based task assignment."""
    print("\n" + "=" * 60)
    print("Example 3: Capability-Based Assignment")
    print("=" * 60)
    
    queue = await create_task_queue(sqlite_path="/tmp/example_capabilities.db")
    
    # Register specialized workers
    python_worker = await queue.register_worker(
        name="python-expert",
        capabilities=["python", "fastapi", "django", "sqlalchemy"]
    )
    
    js_worker = await queue.register_worker(
        name="js-expert",
        capabilities=["javascript", "nodejs", "react", "vue"]
    )
    
    ml_worker = await queue.register_worker(
        name="ml-expert",
        capabilities=["python", "tensorflow", "pytorch", "sklearn"]
    )
    
    print("✓ Registered specialized workers")
    
    # Enqueue tasks requiring specific capabilities
    python_task = await queue.enqueue(
        task_type="api_development",
        payload={"endpoint": "/users"},
        required_capabilities=["python", "fastapi"]
    )
    print(f"✓ Python task: {python_task.id[:8]}...")
    
    js_task = await queue.enqueue(
        task_type="frontend_fix",
        payload={"component": "UserProfile"},
        required_capabilities=["javascript", "react"]
    )
    print(f"✓ JS task: {js_task.id[:8]}...")
    
    ml_task = await queue.enqueue(
        task_type="model_training",
        payload={"model": "sentiment_analysis"},
        required_capabilities=["python", "tensorflow"]
    )
    print(f"✓ ML task: {ml_task.id[:8]}...")
    
    # Tasks will only be assigned to workers with matching capabilities
    print("\nTasks will only be assigned to workers with matching capabilities")
    
    await queue.disconnect()


# Example 4: Task Retry with Exponential Backoff
async def example_retry_mechanism():
    """Demonstrate task retry with exponential backoff."""
    print("\n" + "=" * 60)
    print("Example 4: Task Retry with Exponential Backoff")
    print("=" * 60)
    
    queue = await create_task_queue(sqlite_path="/tmp/example_retry.db")
    
    # Create a task that will fail
    task = await queue.enqueue(
        task_type="unreliable_operation",
        payload={"should_fail": True},
        max_retries=3  # Will retry 3 times
    )
    print(f"✓ Created task with max_retries=3: {task.id[:8]}...")
    
    # Simulate failure
    await queue.fail(task.id, "Connection timeout")
    
    # Check task status
    updated = await queue.get_task(task.id)
    print(f"  Status after fail: {updated.status.value}")
    print(f"  Retry count: {updated.retry_count}/{updated.max_retries}")
    print(f"  Scheduled for retry at: {updated.scheduled_at}")
    
    print("\nRetry delays:")
    print("  Retry 1: 1 second (base_delay * 2^0)")
    print("  Retry 2: 2 seconds (base_delay * 2^1)")
    print("  Retry 3: 4 seconds (base_delay * 2^2)")
    
    await queue.disconnect()


# Example 5: Worker Pool
async def example_worker_pool():
    """Demonstrate using a worker pool to process tasks."""
    print("\n" + "=" * 60)
    print("Example 5: Worker Pool")
    print("=" * 60)
    
    queue = await create_task_queue(sqlite_path="/tmp/example_pool.db")
    
    # Define a task handler
    async def my_task_handler(task: Task) -> dict:
        """Process a task."""
        print(f"  Processing task {task.id[:8]}... (type={task.type})")
        await asyncio.sleep(0.1)  # Simulate work
        return {"processed": True, "task_type": task.type}
    
    # Create worker pool
    pool = await create_worker_pool(
        queue=queue,
        name="my-worker-pool",
        capabilities=["python", "general"],
        max_concurrent=4,
        task_handler=my_task_handler
    )
    print(f"✓ Started worker pool: {pool.worker_id}")
    
    # Enqueue some tasks
    for i in range(5):
        await queue.enqueue(
            task_type="batch_process",
            payload={"item_id": i},
            required_capabilities=["python"]
        )
    print(f"✓ Enqueued 5 tasks")
    
    # Let workers process
    await asyncio.sleep(2)
    
    # Show stats
    print(f"\n  Tasks processed: {pool.stats['tasks_processed']}")
    print(f"  Tasks succeeded: {pool.stats['tasks_succeeded']}")
    print(f"  Tasks failed: {pool.stats['tasks_failed']}")
    
    await pool.stop()
    await queue.disconnect()


# Example 6: Batch Operations
async def example_batch_operations():
    """Demonstrate batch task operations."""
    print("\n" + "=" * 60)
    print("Example 6: Batch Operations")
    print("=" * 60)
    
    queue = await create_task_queue(sqlite_path="/tmp/example_batch.db")
    
    # Batch enqueue
    tasks_data = [
        {
            'type': 'data_processing',
            'payload': {'batch_id': i, 'data': f'item_{i}'},
            'priority': TaskPriority.NORMAL,
            'required_capabilities': ['python']
        }
        for i in range(100)
    ]
    
    tasks = await queue.enqueue_many(tasks_data)
    print(f"✓ Batch enqueued {len(tasks)} tasks")
    
    # Get stats
    stats = await queue.get_stats()
    print(f"  Total pending: {stats.total_pending}")
    print(f"  Priority breakdown: {stats.priority_breakdown}")
    
    await queue.disconnect()


# Example 7: Task Progress Tracking
async def example_progress_tracking():
    """Demonstrate task progress tracking."""
    print("\n" + "=" * 60)
    print("Example 7: Progress Tracking")
    print("=" * 60)
    
    queue = await create_task_queue(sqlite_path="/tmp/example_progress.db")
    
    # Create a long-running task
    task = await queue.enqueue(
        task_type="large_file_processing",
        payload={"file": "data.csv", "rows": 10000},
        timeout_seconds=3600
    )
    print(f"✓ Created task: {task.id[:8]}...")
    
    # Simulate progress updates
    for i in range(0, 101, 20):
        await queue.update_progress(
            task.id,
            percent=i,
            current_step=f"processing_chunk_{i//20}",
            steps_completed=i//20,
            steps_total=5,
            metadata={"rows_processed": i * 100}
        )
        progress = await queue.get_progress(task.id)
        print(f"  Progress: {progress.percent}%, Step: {progress.current_step}")
    
    await queue.disconnect()


# Example 8: Callbacks and Events
async def example_callbacks():
    """Demonstrate task event callbacks."""
    print("\n" + "=" * 60)
    print("Example 8: Callbacks and Events")
    print("=" * 60)
    
    queue = await create_task_queue(sqlite_path="/tmp/example_callbacks.db")
    
    # Register callbacks
    def on_task_created(task):
        print(f"  [EVENT] Task created: {task.id[:8]}...")
    
    def on_task_completed(task):
        print(f"  [EVENT] Task completed: {task.id[:8]}...")
    
    queue.on('created', on_task_created)
    queue.on('completed', on_task_completed)
    
    # Register worker
    worker = await queue.register_worker(
        name="callback-demo-worker",
        capabilities=["general"]
    )
    
    # Create and process task
    task = await queue.enqueue(
        task_type="demo_task",
        payload={"test": True}
    )
    
    # Dequeue and complete
    assigned = await queue.dequeue(worker.id, worker.capabilities)
    if assigned:
        await queue.complete(assigned.id, {"result": "ok"})
    
    await queue.disconnect()


# Run all examples
async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("APEX Distributed Task Queue - Usage Examples")
    print("=" * 60)
    
    await example_basic_usage()
    await example_priority_scheduling()
    await example_capability_assignment()
    await example_retry_mechanism()
    await example_worker_pool()
    await example_batch_operations()
    await example_progress_tracking()
    await example_callbacks()
    
    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
