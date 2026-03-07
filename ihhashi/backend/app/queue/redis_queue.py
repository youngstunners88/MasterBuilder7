"""
Redis-based message queue for async processing
Supports:
- Reliable message delivery
- Dead letter queue for failed messages
- Priority queues
- Delayed message scheduling
"""
import json
import asyncio
import logging
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)


class MessagePriority(int, Enum):
    """Message priority levels"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


@dataclass
class QueueMessage:
    """Message structure for queue"""
    id: str
    type: str
    payload: Dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    created_at: datetime = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def to_json(self) -> str:
        data = asdict(self)
        data['priority'] = self.priority.value
        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'QueueMessage':
        data = json.loads(json_str)
        data['priority'] = MessagePriority(data.get('priority', 3))
        if data.get('created_at'):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


class RedisQueue:
    """
    Redis-based reliable message queue.
    
    Features:
    - Priority-based message ordering
    - Automatic retry with exponential backoff
    - Dead letter queue for failed messages
    - Message acknowledgment
    """
    
    def __init__(
        self,
        queue_name: str,
        max_retries: int = 3,
        visibility_timeout: int = 300,  # 5 minutes
    ):
        self.queue_name = queue_name
        self.max_retries = max_retries
        self.visibility_timeout = visibility_timeout
        
        # Redis keys
        self.main_queue = f"queue:{queue_name}"
        self.processing_queue = f"queue:{queue_name}:processing"
        self.dlq_queue = f"queue:{queue_name}:dlq"
        self.delayed_queue = f"queue:{queue_name}:delayed"
    
    async def enqueue(
        self,
        message_type: str,
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        delay_seconds: int = 0
    ) -> str:
        """
        Add a message to the queue.
        
        Args:
            message_type: Type of message (e.g., 'order.created', 'payment.process')
            payload: Message data
            priority: Message priority
            delay_seconds: Delay before message becomes visible
            
        Returns:
            Message ID
        """
        import uuid
        
        message = QueueMessage(
            id=str(uuid.uuid4()),
            type=message_type,
            payload=payload,
            priority=priority,
            max_retries=self.max_retries
        )
        
        redis = get_redis()
        if not redis:
            logger.error("Redis not available for queue")
            raise RuntimeError("Redis not available")
        
        if delay_seconds > 0:
            # Add to delayed queue with score = current time + delay
            score = (datetime.utcnow() + timedelta(seconds=delay_seconds)).timestamp()
            await redis.zadd(self.delayed_queue, {message.to_json(): score})
            logger.debug(f"Message {message.id} scheduled for delayed processing")
        else:
            # Add to main queue with priority
            # Use priority as score (lower = higher priority)
            await redis.zadd(self.main_queue, {message.to_json(): priority.value})
            logger.debug(f"Message {message.id} added to queue {self.queue_name}")
        
        return message.id
    
    async def dequeue(self, timeout: int = 5) -> Optional[QueueMessage]:
        """
        Get a message from the queue.
        Moves message to processing queue for visibility timeout.
        
        Args:
            timeout: Blocking timeout in seconds
            
        Returns:
            Message or None if queue is empty
        """
        redis = get_redis()
        if not redis:
            return None
        
        # First, check delayed queue for messages that should be moved to main queue
        await self._process_delayed_messages()
        
        # Get message from main queue (lowest score = highest priority)
        result = await redis.bzpopmin(self.main_queue, timeout=timeout)
        
        if not result:
            return None
        
        # result is [queue_name, message_data, score]
        message_data = result[1]
        message = QueueMessage.from_json(message_data)
        
        # Add to processing queue with visibility timeout
        processing_data = {
            "message": message_data,
            "started_at": datetime.utcnow().isoformat(),
            "visible_at": (datetime.utcnow() + timedelta(seconds=self.visibility_timeout)).isoformat()
        }
        await redis.hset(self.processing_queue, message.id, json.dumps(processing_data))
        
        logger.debug(f"Message {message.id} dequeued for processing")
        return message
    
    async def acknowledge(self, message_id: str) -> bool:
        """
        Acknowledge message processing is complete.
        Removes message from processing queue.
        
        Args:
            message_id: Message ID to acknowledge
            
        Returns:
            True if acknowledged
        """
        redis = get_redis()
        if not redis:
            return False
        
        result = await redis.hdel(self.processing_queue, message_id)
        if result:
            logger.debug(f"Message {message_id} acknowledged")
        return result > 0
    
    async def reject(self, message_id: str, requeue: bool = True) -> bool:
        """
        Reject a message (processing failed).
        Either requeue for retry or move to DLQ.
        
        Args:
            message_id: Message ID to reject
            requeue: Whether to requeue for retry
            
        Returns:
            True if handled
        """
        redis = get_redis()
        if not redis:
            return False
        
        # Get message from processing queue
        processing_data = await redis.hget(self.processing_queue, message_id)
        if not processing_data:
            logger.warning(f"Message {message_id} not found in processing queue")
            return False
        
        data = json.loads(processing_data)
        message = QueueMessage.from_json(data["message"])
        
        # Remove from processing queue
        await redis.hdel(self.processing_queue, message_id)
        
        if requeue and message.retry_count < message.max_retries:
            # Requeue with incremented retry count
            message.retry_count += 1
            # Add exponential backoff
            delay = 2 ** message.retry_count
            score = (datetime.utcnow() + timedelta(seconds=delay)).timestamp()
            await redis.zadd(self.main_queue, {message.to_json(): message.priority.value})
            logger.info(f"Message {message_id} requeued for retry {message.retry_count}")
        else:
            # Move to DLQ
            dlq_entry = {
                "message": message.to_json(),
                "failed_at": datetime.utcnow().isoformat(),
                "retry_count": message.retry_count
            }
            await redis.lpush(self.dlq_queue, json.dumps(dlq_entry))
            logger.warning(f"Message {message_id} moved to DLQ after {message.retry_count} retries")
        
        return True
    
    async def _process_delayed_messages(self):
        """Move delayed messages that are ready to the main queue"""
        redis = get_redis()
        if not redis:
            return
        
        now = datetime.utcnow().timestamp()
        
        # Get messages with score <= now
        messages = await redis.zrangebyscore(self.delayed_queue, 0, now)
        
        for message_data in messages:
            # Remove from delayed queue
            await redis.zrem(self.delayed_queue, message_data)
            
            # Add to main queue
            message = QueueMessage.from_json(message_data)
            await redis.zadd(self.main_queue, {message_data: message.priority.value})
            logger.debug(f"Delayed message {message.id} moved to main queue")
    
    async def get_queue_stats(self) -> Dict[str, int]:
        """Get queue statistics"""
        redis = get_redis()
        if not redis:
            return {"error": "Redis not available"}
        
        return {
            "main": await redis.zcard(self.main_queue),
            "processing": await redis.hlen(self.processing_queue),
            "dlq": await redis.llen(self.dlq_queue),
            "delayed": await redis.zcard(self.delayed_queue)
        }
    
    async def purge_dlq(self) -> int:
        """Purge dead letter queue. Returns number of messages removed."""
        redis = get_redis()
        if not redis:
            return 0
        
        count = await redis.llen(self.dlq_queue)
        await redis.delete(self.dlq_queue)
        logger.info(f"Purged {count} messages from DLQ")
        return count


class QueueWorker:
    """
    Worker that processes messages from a queue.
    
    Features:
    - Concurrent message processing
    - Graceful shutdown
    - Error handling and retry
    - Metrics collection
    """
    
    def __init__(
        self,
        queue: RedisQueue,
        handler: Callable[[QueueMessage], Any],
        max_workers: int = 5,
        poll_interval: float = 1.0
    ):
        self.queue = queue
        self.handler = handler
        self.max_workers = max_workers
        self.poll_interval = poll_interval
        
        self._running = False
        self._workers: List[asyncio.Task] = []
        self._metrics = {
            "processed": 0,
            "failed": 0,
            "started_at": None
        }
    
    async def start(self):
        """Start the worker"""
        self._running = True
        self._metrics["started_at"] = datetime.utcnow().isoformat()
        
        # Start worker tasks
        for i in range(self.max_workers):
            task = asyncio.create_task(self._worker_loop(), name=f"worker_{i}")
            self._workers.append(task)
        
        logger.info(f"QueueWorker started with {self.max_workers} workers for queue {self.queue.queue_name}")
    
    async def stop(self):
        """Stop the worker gracefully"""
        self._running = False
        
        # Cancel all worker tasks
        for task in self._workers:
            task.cancel()
        
        # Wait for tasks to complete
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        
        logger.info(f"QueueWorker stopped for queue {self.queue.queue_name}")
    
    async def _worker_loop(self):
        """Main worker loop"""
        while self._running:
            try:
                # Get message from queue
                message = await self.queue.dequeue(timeout=1)
                
                if message:
                    try:
                        # Process message
                        await self.handler(message)
                        
                        # Acknowledge success
                        await self.queue.acknowledge(message.id)
                        self._metrics["processed"] += 1
                    
                    except Exception as e:
                        logger.error(f"Error processing message {message.id}: {e}")
                        
                        # Reject message (will retry or move to DLQ)
                        await self.queue.reject(message.id, requeue=True)
                        self._metrics["failed"] += 1
                else:
                    # No message, wait before polling again
                    await asyncio.sleep(self.poll_interval)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(self.poll_interval)
    
    def get_metrics(self) -> Dict:
        """Get worker metrics"""
        return {
            **self._metrics,
            "running": self._running,
            "active_workers": len([w for w in self._workers if not w.done()])
        }


# Global queues
order_queue = RedisQueue("orders")
payment_queue = RedisQueue("payments")
notification_queue = RedisQueue("notifications", max_retries=5)
