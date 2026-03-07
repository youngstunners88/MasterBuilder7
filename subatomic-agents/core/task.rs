// Task definitions and scheduling

use serde::{Serialize, Deserialize};
use std::collections::VecDeque;
use std::sync::Arc;
use tokio::sync::RwLock;

/// Task priority levels
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum TaskPriority {
    Critical = 0,
    High = 1,
    Normal = 2,
    Low = 3,
    Background = 4,
}

/// Task status
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TaskStatus {
    Pending,
    Assigned,
    Running,
    Completed,
    Failed,
    Cancelled,
}

/// Task requirements
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskRequirements {
    /// Minimum RAM required (MB)
    pub min_memory_mb: usize,
    /// Required capabilities (bitmask)
    pub capabilities: u32,
    /// Preferred agent type
    pub preferred_agent_type: Option<String>,
    /// Maximum execution time (seconds)
    pub max_duration_secs: u64,
}

impl Default for TaskRequirements {
    fn default() -> Self {
        Self {
            min_memory_mb: 50,
            capabilities: 0,
            preferred_agent_type: None,
            max_duration_secs: 60,
        }
    }
}

/// Task definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Task {
    /// Unique task ID
    pub id: String,
    /// Task type
    pub task_type: String,
    /// Task payload (binary data)
    pub payload: Vec<u8>,
    /// Task priority
    pub priority: TaskPriority,
    /// Task requirements
    pub requirements: TaskRequirements,
    /// Task status
    #[serde(skip)]
    pub status: TaskStatus,
    /// Created timestamp
    pub created_at: u64,
    /// Deadline timestamp (if any)
    pub deadline: Option<u64>,
}

impl Task {
    /// Create a new task
    pub fn new(task_type: &str, payload: Vec<u8>) -> Self {
        Self {
            id: uuid::Uuid::new_v4().to_string(),
            task_type: task_type.to_string(),
            payload,
            priority: TaskPriority::Normal,
            requirements: TaskRequirements::default(),
            status: TaskStatus::Pending,
            created_at: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
            deadline: None,
        }
    }

    /// Set priority
    pub fn with_priority(mut self, priority: TaskPriority) -> Self {
        self.priority = priority;
        self
    }

    /// Set requirements
    pub fn with_requirements(mut self, requirements: TaskRequirements) -> Self {
        self.requirements = requirements;
        self
    }

    /// Set deadline
    pub fn with_deadline(mut self, deadline_secs: u64) -> Self {
        self.deadline = Some(deadline_secs);
        self
    }

    /// Check if task is expired
    pub fn is_expired(&self) -> bool {
        if let Some(deadline) = self.deadline {
            let now = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs();
            now > deadline
        } else {
            false
        }
    }
}

/// Task result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskResult {
    /// Task ID
    pub task_id: String,
    /// Success flag
    pub success: bool,
    /// Result data (if successful)
    pub data: Option<Vec<u8>>,
    /// Error message (if failed)
    pub error: Option<String>,
    /// Execution time (milliseconds)
    pub execution_time_ms: u64,
    /// Agent that executed the task
    pub executed_by: Option<String>,
    /// Completed timestamp
    pub completed_at: u64,
}

impl TaskResult {
    /// Create successful result
    pub fn success(task_id: String, data: Vec<u8>, execution_time_ms: u64) -> Self {
        Self {
            task_id,
            success: true,
            data: Some(data),
            error: None,
            execution_time_ms,
            executed_by: None,
            completed_at: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
        }
    }

    /// Create failed result
    pub fn failure(task_id: String, error: String, execution_time_ms: u64) -> Self {
        Self {
            task_id,
            success: false,
            data: None,
            error: Some(error),
            execution_time_ms,
            executed_by: None,
            completed_at: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
        }
    }
}

/// Priority task queue
pub struct TaskQueue {
    /// Queue storage
    queues: Arc<RwLock<Vec<VecDeque<Task>>>>,
    /// Maximum queue size per priority
    max_size: usize,
}

impl TaskQueue {
    /// Create new task queue
    pub fn new(max_size: usize) -> Self {
        let queues: Vec<VecDeque<Task>> = (0..5).map(|_| VecDeque::new()).collect();

        Self {
            queues: Arc::new(RwLock::new(queues)),
            max_size,
        }
    }

    /// Push task to queue
    pub async fn push(&self, task: Task) -> Result<(), TaskQueueError> {
        let mut queues = self.queues.write().await;
        let priority_idx = task.priority as usize;

        if queues[priority_idx].len() >= self.max_size {
            return Err(TaskQueueError::QueueFull);
        }

        queues[priority_idx].push_back(task);
        Ok(())
    }

    /// Pop highest priority task
    pub async fn pop(&self) -> Option<Task> {
        let mut queues = self.queues.write().await;

        for queue in queues.iter_mut() {
            // Remove expired tasks
            while let Some(front) = queue.front() {
                if front.is_expired() {
                    queue.pop_front();
                } else {
                    break;
                }
            }

            if let Some(task) = queue.pop_front() {
                if !task.is_expired() {
                    return Some(task);
                }
            }
        }

        None
    }

    /// Get queue size (all priorities)
    pub async fn size(&self) -> usize {
        let queues = self.queues.read().await;
        queues.iter().map(|q| q.len()).sum()
    }

    /// Get queue size by priority
    pub async fn size_by_priority(&self, priority: TaskPriority) -> usize {
        let queues = self.queues.read().await;
        queues[priority as usize].len()
    }

    /// Clear all queues
    pub async fn clear(&self) {
        let mut queues = self.queues.write().await;
        for queue in queues.iter_mut() {
            queue.clear();
        }
    }
}

/// Task queue errors
#[derive(Debug, thiserror::Error)]
pub enum TaskQueueError {
    #[error("Queue is full")]
    QueueFull,

    #[error("Task not found")]
    TaskNotFound,

    #[error("Invalid priority")]
    InvalidPriority,
}

/// Task scheduler
pub struct TaskScheduler {
    queue: TaskQueue,
    /// Scheduled tasks (for tracking)
    scheduled: Arc<RwLock<std::collections::HashMap<String, Task>>>,
}

impl TaskScheduler {
    /// Create new task scheduler
    pub fn new(max_queue_size: usize) -> Self {
        Self {
            queue: TaskQueue::new(max_queue_size),
            scheduled: Arc::new(RwLock::new(std::collections::HashMap::new())),
        }
    }

    /// Schedule a task
    pub async fn schedule(&self, task: Task) -> Result<(), TaskQueueError> {
        let task_id = task.id.clone();
        self.queue.push(task.clone()).await?;

        let mut scheduled = self.scheduled.write().await;
        scheduled.insert(task_id, task);

        Ok(())
    }

    /// Get next task to execute
    pub async fn next_task(&self) -> Option<Task> {
        let task = self.queue.pop().await?;

        // Update status
        let mut scheduled = self.scheduled.write().await;
        if let Some(t) = scheduled.get_mut(&task.id) {
            t.status = TaskStatus::Assigned;
        }

        Some(task)
    }

    /// Complete a task
    pub async fn complete(&self, task_id: &str, result: TaskResult) {
        let mut scheduled = self.scheduled.write().await;
        if let Some(task) = scheduled.get_mut(task_id) {
            task.status = if result.success {
                TaskStatus::Completed
            } else {
                TaskStatus::Failed
            };
        }
    }

    /// Get task status
    pub async fn get_status(&self, task_id: &str) -> Option<TaskStatus> {
        let scheduled = self.scheduled.read().await;
        scheduled.get(task_id).map(|t| t.status)
    }

    /// Get queue stats
    pub async fn stats(&self) -> SchedulerStats {
        SchedulerStats {
            queue_size: self.queue.size().await,
            scheduled_count: self.scheduled.read().await.len(),
        }
    }
}

/// Scheduler statistics
#[derive(Debug, Clone)]
pub struct SchedulerStats {
    pub queue_size: usize,
    pub scheduled_count: usize,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_task_queue() {
        let queue = TaskQueue::new(100);

        let task = Task::new("test", vec![1, 2, 3]);
        queue.push(task.clone()).await.unwrap();

        assert_eq!(queue.size().await, 1);

        let popped = queue.pop().await;
        assert!(popped.is_some());
        assert_eq!(popped.unwrap().id, task.id);
    }

    #[tokio::test]
    async fn test_task_priority() {
        let queue = TaskQueue::new(100);

        let low_task = Task::new("low", vec![]).with_priority(TaskPriority::Low);
        let high_task = Task::new("high", vec![]).with_priority(TaskPriority::High);

        queue.push(low_task).await.unwrap();
        queue.push(high_task).await.unwrap();

        // High priority should come first
        let popped = queue.pop().await.unwrap();
        assert_eq!(popped.task_type, "high");
    }

    #[tokio::test]
    async fn test_task_scheduler() {
        let scheduler = TaskScheduler::new(100);

        let task = Task::new("test", vec![1, 2, 3]);
        let task_id = task.id.clone();

        scheduler.schedule(task).await.unwrap();

        let next = scheduler.next_task().await;
        assert!(next.is_some());
        assert_eq!(next.unwrap().id, task_id);
    }
}
