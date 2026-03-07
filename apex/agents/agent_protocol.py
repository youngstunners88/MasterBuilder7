#!/usr/bin/env python3
"""
APEX Agent-to-Agent Communication Protocol

Pure agentic collaboration system enabling agents to:
- Send messages to each other
- Share state/context
- Request assistance from specialist agents
- Broadcast task completions
- Coordinate parallel work

Features:
- Async/await support for concurrent messaging
- Redis-backed pub/sub with SQLite fallback
- Message persistence and delivery guarantees
- Structured message types for common patterns
- Automatic retry and error handling
- Message routing and filtering

Author: APEX Infrastructure Team
Version: 1.0.0
"""

import asyncio
import json
import logging
import os
import sqlite3
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union, AsyncGenerator
from contextlib import asynccontextmanager
import hashlib
import threading
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger('AgentProtocol')

# Import existing Redis manager if available
try:
    from ..infrastructure.redis_manager import RedisManager, RedisConfig
    REDIS_MANAGER_AVAILABLE = True
except ImportError:
    REDIS_MANAGER_AVAILABLE = False
    logger.warning("RedisManager not available. Using SQLite-only mode.")

# Redis imports with graceful fallback
try:
    import redis.asyncio as aioredis
    from redis.asyncio import Redis
    from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis-py not available. Redis functionality disabled.")


class MessageType(Enum):
    """Standard message types for agent communication."""
    
    # Task Management
    TASK_REQUEST = "task_request"           # Request an agent to perform a task
    TASK_COMPLETE = "task_complete"         # Notify task completion
    TASK_FAILED = "task_failed"             # Notify task failure
    TASK_PROGRESS = "task_progress"         # Task progress update
    
    # Assistance
    HELP_REQUEST = "help_request"           # Request help from specialist
    HELP_RESPONSE = "help_response"         # Response to help request
    
    # State Management
    STATE_UPDATE = "state_update"           # Share state/context update
    STATE_REQUEST = "state_request"         # Request current state
    STATE_RESPONSE = "state_response"       # Respond with current state
    
    # Coordination
    BROADCAST = "broadcast"                 # Broadcast to all agents
    DIRECT = "direct"                       # Direct message to specific agent
    
    # Lifecycle
    AGENT_SPAWNED = "agent_spawned"         # New agent spawned
    AGENT_TERMINATING = "agent_terminating" # Agent shutting down
    HEARTBEAT = "heartbeat"                 # Keep-alive signal
    
    # Workflows
    WORKFLOW_START = "workflow_start"       # Start workflow
    WORKFLOW_STEP = "workflow_step"         # Workflow step update
    WORKFLOW_COMPLETE = "workflow_complete" # Workflow finished
    
    # Consensus
    CONSENSUS_REQUEST = "consensus_request" # Request consensus
    CONSENSUS_VOTE = "consensus_vote"       # Cast vote
    CONSENSUS_RESULT = "consensus_result"   # Consensus reached


class MessagePriority(Enum):
    """Message priority levels."""
    CRITICAL = 0    # Process immediately
    HIGH = 1        # Process soon
    NORMAL = 2      # Standard priority
    LOW = 3         # Process when convenient
    BACKGROUND = 4  # Background processing


class DeliveryStatus(Enum):
    """Message delivery status."""
    PENDING = "pending"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class AgentMessage:
    """
    Standard message format for agent-to-agent communication.
    
    Attributes:
        id: Unique message identifier
        message_type: Type of message
        sender: Sender agent ID
        recipient: Recipient agent ID (or "*" for broadcast)
        payload: Message payload/data
        timestamp: ISO format timestamp
        priority: Message priority
        ttl_seconds: Time-to-live for message
        correlation_id: ID to correlate related messages
        reply_to: Agent ID to reply to
        metadata: Additional metadata
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = MessageType.DIRECT
    sender: str = ""
    recipient: str = ""  # "*" or "broadcast" for all agents
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    priority: MessagePriority = MessagePriority.NORMAL
    ttl_seconds: int = 300  # 5 minutes default
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "id": self.id,
            "message_type": self.message_type.value,
            "sender": self.sender,
            "recipient": self.recipient,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "priority": self.priority.value,
            "ttl_seconds": self.ttl_seconds,
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        """Create message from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            message_type=MessageType(data.get("message_type", "direct")),
            sender=data.get("sender", ""),
            recipient=data.get("recipient", ""),
            payload=data.get("payload", {}),
            timestamp=data.get("timestamp", datetime.utcnow().isoformat()),
            priority=MessagePriority(data.get("priority", 2)),
            ttl_seconds=data.get("ttl_seconds", 300),
            correlation_id=data.get("correlation_id"),
            reply_to=data.get("reply_to"),
            metadata=data.get("metadata", {})
        )
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'AgentMessage':
        """Deserialize from JSON."""
        return cls.from_dict(json.loads(json_str))
    
    def is_expired(self) -> bool:
        """Check if message has expired."""
        try:
            timestamp = datetime.fromisoformat(self.timestamp)
            return datetime.utcnow() > timestamp + timedelta(seconds=self.ttl_seconds)
        except:
            return True
    
    def create_reply(self, payload: Dict[str, Any], message_type: Optional[MessageType] = None) -> 'AgentMessage':
        """Create a reply to this message."""
        return AgentMessage(
            message_type=message_type or MessageType.DIRECT,
            sender=self.recipient if self.recipient != "*" else "",
            recipient=self.sender,
            payload=payload,
            priority=self.priority,
            correlation_id=self.correlation_id or self.id,
            reply_to=self.sender
        )


@dataclass
class MessageDelivery:
    """Tracks message delivery status."""
    message_id: str
    status: DeliveryStatus = DeliveryStatus.PENDING
    delivered_at: Optional[str] = None
    read_at: Optional[str] = None
    attempts: int = 0
    last_error: Optional[str] = None
    
    def mark_delivered(self):
        """Mark as delivered."""
        self.status = DeliveryStatus.DELIVERED
        self.delivered_at = datetime.utcnow().isoformat()
    
    def mark_read(self):
        """Mark as read."""
        self.status = DeliveryStatus.READ
        self.read_at = datetime.utcnow().isoformat()
    
    def mark_failed(self, error: str):
        """Mark as failed."""
        self.status = DeliveryStatus.FAILED
        self.last_error = error


class SQLiteMessageStore:
    """SQLite-based message store for fallback and persistence."""
    
    def __init__(self, db_path: str = "/tmp/agent_messages.db"):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    def _init_db(self):
        """Initialize SQLite database."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                message_type TEXT NOT NULL,
                sender TEXT NOT NULL,
                recipient TEXT NOT NULL,
                payload TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                priority INTEGER DEFAULT 2,
                ttl_seconds INTEGER DEFAULT 300,
                correlation_id TEXT,
                reply_to TEXT,
                metadata TEXT,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Delivery tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS delivery_tracking (
                message_id TEXT PRIMARY KEY,
                status TEXT DEFAULT 'pending',
                delivered_at TIMESTAMP,
                read_at TIMESTAMP,
                attempts INTEGER DEFAULT 0,
                last_error TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (message_id) REFERENCES messages(id)
            )
        """)
        
        # Subscriptions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                agent_id TEXT NOT NULL,
                message_type TEXT NOT NULL,
                pattern TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (agent_id, message_type)
            )
        """)
        
        # Agent state table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_state (
                agent_id TEXT PRIMARY KEY,
                state_data TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)
        
        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_recipient ON messages(recipient)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_correlation ON messages(correlation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_expires ON messages(expires_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_type ON messages(message_type)")
        
        conn.commit()
        logger.info(f"SQLite message store initialized: {self.db_path}")
    
    def store_message(self, message: AgentMessage) -> bool:
        """Store a message."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            expires_at = (datetime.utcnow() + timedelta(seconds=message.ttl_seconds)).isoformat()
            
            cursor.execute("""
                INSERT INTO messages 
                (id, message_type, sender, recipient, payload, timestamp, priority, 
                 ttl_seconds, correlation_id, reply_to, metadata, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                message.id, message.message_type.value, message.sender, message.recipient,
                json.dumps(message.payload), message.timestamp, message.priority.value,
                message.ttl_seconds, message.correlation_id, message.reply_to,
                json.dumps(message.metadata), expires_at
            ))
            
            # Initialize delivery tracking
            cursor.execute("""
                INSERT OR REPLACE INTO delivery_tracking (message_id, status, attempts)
                VALUES (?, 'pending', 0)
            """, (message.id,))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to store message: {e}")
            return False
    
    def get_messages_for_recipient(self, recipient: str, 
                                    message_type: Optional[MessageType] = None,
                                    since: Optional[str] = None,
                                    limit: int = 100) -> List[AgentMessage]:
        """Get messages for a recipient."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            now = datetime.utcnow().isoformat()
            
            query = """
                SELECT * FROM messages 
                WHERE (recipient = ? OR recipient = '*' OR recipient = 'broadcast')
                AND expires_at > ?
            """
            params = [recipient, now]
            
            if message_type:
                query += " AND message_type = ?"
                params.append(message_type.value)
            
            if since:
                query += " AND timestamp > ?"
                params.append(since)
            
            query += " ORDER BY priority ASC, timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            messages = []
            for row in rows:
                msg = AgentMessage(
                    id=row['id'],
                    message_type=MessageType(row['message_type']),
                    sender=row['sender'],
                    recipient=row['recipient'],
                    payload=json.loads(row['payload']),
                    timestamp=row['timestamp'],
                    priority=MessagePriority(row['priority']),
                    ttl_seconds=row['ttl_seconds'],
                    correlation_id=row['correlation_id'],
                    reply_to=row['reply_to'],
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                )
                messages.append(msg)
            
            return messages
        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            return []
    
    def update_delivery_status(self, message_id: str, status: DeliveryStatus, 
                                error: Optional[str] = None):
        """Update delivery status."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if status == DeliveryStatus.DELIVERED:
                cursor.execute("""
                    UPDATE delivery_tracking 
                    SET status = ?, delivered_at = ?, attempts = attempts + 1
                    WHERE message_id = ?
                """, (status.value, datetime.utcnow().isoformat(), message_id))
            elif status == DeliveryStatus.READ:
                cursor.execute("""
                    UPDATE delivery_tracking 
                    SET status = ?, read_at = ?, attempts = attempts + 1
                    WHERE message_id = ?
                """, (status.value, datetime.utcnow().isoformat(), message_id))
            elif status == DeliveryStatus.FAILED:
                cursor.execute("""
                    UPDATE delivery_tracking 
                    SET status = ?, last_error = ?, attempts = attempts + 1
                    WHERE message_id = ?
                """, (status.value, error, message_id))
            else:
                cursor.execute("""
                    UPDATE delivery_tracking 
                    SET status = ?, attempts = attempts + 1
                    WHERE message_id = ?
                """, (status.value, message_id))
            
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to update delivery status: {e}")
    
    def get_delivery_status(self, message_id: str) -> Optional[MessageDelivery]:
        """Get delivery status for a message."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM delivery_tracking WHERE message_id = ?
            """, (message_id,))
            
            row = cursor.fetchone()
            if row:
                return MessageDelivery(
                    message_id=row['message_id'],
                    status=DeliveryStatus(row['status']),
                    delivered_at=row['delivered_at'],
                    read_at=row['read_at'],
                    attempts=row['attempts'],
                    last_error=row['last_error']
                )
            return None
        except Exception as e:
            logger.error(f"Failed to get delivery status: {e}")
            return None
    
    def cleanup_expired(self):
        """Remove expired messages."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            now = datetime.utcnow().isoformat()
            
            cursor.execute("DELETE FROM messages WHERE expires_at < ?", (now,))
            cursor.execute("DELETE FROM agent_state WHERE expires_at < ?", (now,))
            
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to cleanup expired messages: {e}")
    
    def store_agent_state(self, agent_id: str, state: Dict[str, Any], 
                          ttl_seconds: int = 3600) -> bool:
        """Store agent state."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            expires_at = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()
            
            cursor.execute("""
                INSERT OR REPLACE INTO agent_state (agent_id, state_data, expires_at)
                VALUES (?, ?, ?)
            """, (agent_id, json.dumps(state), expires_at))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to store agent state: {e}")
            return False
    
    def get_agent_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent state."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            now = datetime.utcnow().isoformat()
            
            cursor.execute("""
                SELECT state_data FROM agent_state 
                WHERE agent_id = ? AND expires_at > ?
            """, (agent_id, now))
            
            row = cursor.fetchone()
            if row:
                return json.loads(row['state_data'])
            return None
        except Exception as e:
            logger.error(f"Failed to get agent state: {e}")
            return None


class AgentBus:
    """
    Pub/Sub message bus for agent-to-agent communication.
    
    Features:
    - Async message publishing and subscription
    - Redis-backed with SQLite fallback
    - Automatic retry and error handling
    - Message filtering and routing
    - Delivery tracking
    
    Usage:
        bus = AgentBus()
        await bus.connect()
        
        # Subscribe to messages
        await bus.subscribe("my-agent", MessageType.TASK_REQUEST, handler)
        
        # Send message
        await bus.send_message(AgentMessage(...))
        
        # Broadcast
        await bus.broadcast(MessageType.BROADCAST, {"data": "hello"})
    """
    
    # Redis key prefixes
    PREFIX_MESSAGE = "apex:agent:msg:"
    PREFIX_CHANNEL = "apex:agent:channel:"
    PREFIX_STATE = "apex:agent:state:"
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_password: Optional[str] = None,
        sqlite_path: str = "/tmp/agent_messages.db",
        message_ttl: int = 86400,  # 24 hours
        max_retries: int = 3
    ):
        """
        Initialize AgentBus.
        
        Args:
            redis_url: Redis URL (overrides host/port/password)
            redis_host: Redis host
            redis_port: Redis port
            redis_password: Redis password
            sqlite_path: Path to SQLite fallback database
            message_ttl: Default message TTL in seconds
            max_retries: Max retry attempts for failed operations
        """
        self.redis_url = redis_url
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_password = redis_password
        self.message_ttl = message_ttl
        self.max_retries = max_retries
        
        # Redis client
        self._redis: Optional[Redis] = None
        self._pubsub = None
        self._pubsub_task: Optional[asyncio.Task] = None
        
        # SQLite fallback
        self._sqlite = SQLiteMessageStore(sqlite_path)
        
        # Subscriptions
        self._subscriptions: Dict[str, List[Tuple[Optional[MessageType], Callable]]] = defaultdict(list)
        self._broadcast_handlers: List[Callable] = []
        
        # Connection state
        self._connected = False
        self._lock = asyncio.Lock()
        
        # Message queue for local buffering
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._delivery_tracking: Dict[str, MessageDelivery] = {}
        
        logger.info("AgentBus initialized")
    
    async def connect(self) -> bool:
        """
        Connect to Redis (with SQLite fallback).
        
        Returns:
            True if connected to Redis, False if using SQLite
        """
        async with self._lock:
            if self._connected:
                return True
            
            if not REDIS_AVAILABLE:
                logger.warning("Redis not available, using SQLite fallback")
                return False
            
            try:
                if self.redis_url:
                    self._redis = aioredis.from_url(
                        self.redis_url,
                        decode_responses=True,
                        socket_connect_timeout=5,
                        socket_timeout=5
                    )
                else:
                    self._redis = aioredis.Redis(
                        host=self.redis_host,
                        port=self.redis_port,
                        password=self.redis_password,
                        decode_responses=True,
                        socket_connect_timeout=5,
                        socket_timeout=5
                    )
                
                # Test connection
                await self._redis.ping()
                self._connected = True
                
                # Start message processor
                self._processor_task = asyncio.create_task(self._message_processor())
                
                logger.info("AgentBus connected to Redis")
                return True
                
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Using SQLite fallback.")
                self._redis = None
                self._connected = False
                return False
    
    async def disconnect(self):
        """Disconnect from Redis."""
        async with self._lock:
            if self._pubsub_task:
                self._pubsub_task.cancel()
                try:
                    await self._pubsub_task
                except asyncio.CancelledError:
                    pass
            
            if self._redis:
                await self._redis.close()
                self._redis = None
            
            self._connected = False
            logger.info("AgentBus disconnected")
    
    async def send_message(self, message: AgentMessage) -> bool:
        """
        Send a message to an agent.
        
        Args:
            message: The message to send
            
        Returns:
            True if sent successfully
        """
        # Store in SQLite for persistence
        self._sqlite.store_message(message)
        
        if self._connected and self._redis:
            try:
                # Publish to Redis
                channel = f"{self.PREFIX_CHANNEL}{message.recipient}"
                await self._redis.publish(channel, message.to_json())
                
                # Also store for later retrieval
                key = f"{self.PREFIX_MESSAGE}{message.id}"
                await self._redis.setex(key, message.ttl_seconds, message.to_json())
                
                self._sqlite.update_delivery_status(message.id, DeliveryStatus.DELIVERED)
                return True
                
            except Exception as e:
                logger.error(f"Failed to send via Redis: {e}")
                # Will be picked up from SQLite
                return False
        else:
            # SQLite only mode - message already stored
            logger.debug(f"Message stored in SQLite: {message.id}")
            return True
    
    async def send_direct(
        self,
        sender: str,
        recipient: str,
        payload: Dict[str, Any],
        message_type: MessageType = MessageType.DIRECT,
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str] = None
    ) -> AgentMessage:
        """
        Send a direct message (convenience method).
        
        Args:
            sender: Sender agent ID
            recipient: Recipient agent ID
            payload: Message payload
            message_type: Type of message
            priority: Message priority
            correlation_id: Correlation ID for related messages
            
        Returns:
            The sent message
        """
        message = AgentMessage(
            sender=sender,
            recipient=recipient,
            message_type=message_type,
            payload=payload,
            priority=priority,
            correlation_id=correlation_id
        )
        await self.send_message(message)
        return message
    
    async def broadcast(
        self,
        sender: str,
        payload: Dict[str, Any],
        message_type: MessageType = MessageType.BROADCAST,
        exclude: Optional[List[str]] = None
    ) -> AgentMessage:
        """
        Broadcast a message to all agents.
        
        Args:
            sender: Sender agent ID
            payload: Message payload
            message_type: Broadcast type
            exclude: List of agent IDs to exclude
            
        Returns:
            The broadcast message
        """
        message = AgentMessage(
            sender=sender,
            recipient="*",
            message_type=message_type,
            payload=payload,
            priority=MessagePriority.NORMAL,
            metadata={"exclude": exclude or []}
        )
        
        if self._connected and self._redis:
            try:
                await self._redis.publish(
                    f"{self.PREFIX_CHANNEL}broadcast",
                    message.to_json()
                )
            except Exception as e:
                logger.error(f"Broadcast failed: {e}")
        
        # Always store in SQLite
        self._sqlite.store_message(message)
        
        return message
    
    async def subscribe(
        self,
        agent_id: str,
        message_type: Optional[MessageType] = None,
        handler: Optional[Callable[[AgentMessage], Any]] = None
    ) -> bool:
        """
        Subscribe to messages.
        
        Args:
            agent_id: Agent ID to subscribe for
            message_type: Specific message type to filter (None for all)
            handler: Callback function(message) for received messages
            
        Returns:
            True if subscribed successfully
        """
        if handler:
            self._subscriptions[agent_id].append((message_type, handler))
        
        if self._connected and self._redis and handler:
            # Start pub/sub listener if not already running
            if not self._pubsub_task or self._pubsub_task.done():
                self._pubsub_task = asyncio.create_task(self._pubsub_listener())
        
        return True
    
    async def unsubscribe(self, agent_id: str, handler: Optional[Callable] = None):
        """
        Unsubscribe from messages.
        
        Args:
            agent_id: Agent ID to unsubscribe
            handler: Specific handler to remove (None for all)
        """
        if handler:
            self._subscriptions[agent_id] = [
                (mt, h) for mt, h in self._subscriptions[agent_id] if h != handler
            ]
        else:
            self._subscriptions.pop(agent_id, None)
    
    async def get_messages(
        self,
        recipient: str,
        message_type: Optional[MessageType] = None,
        since: Optional[str] = None,
        mark_delivered: bool = True
    ) -> List[AgentMessage]:
        """
        Get pending messages for an agent.
        
        Args:
            recipient: Recipient agent ID
            message_type: Filter by message type
            since: Get messages since timestamp
            mark_delivered: Mark messages as delivered
            
        Returns:
            List of messages
        """
        messages = self._sqlite.get_messages_for_recipient(recipient, message_type, since)
        
        if mark_delivered:
            for msg in messages:
                self._sqlite.update_delivery_status(msg.id, DeliveryStatus.DELIVERED)
        
        return messages
    
    async def request_help(
        self,
        requester: str,
        specialist_type: str,
        task_description: str,
        context: Dict[str, Any],
        timeout_seconds: int = 300
    ) -> Optional[AgentMessage]:
        """
        Request help from a specialist agent.
        
        Args:
            requester: Requesting agent ID
            specialist_type: Type of specialist needed
            task_description: Description of the task
            context: Task context/data
            timeout_seconds: Timeout for response
            
        Returns:
            Response message or None if timeout
        """
        request = AgentMessage(
            sender=requester,
            recipient=f"specialist:{specialist_type}",
            message_type=MessageType.HELP_REQUEST,
            payload={
                "task_description": task_description,
                "context": context,
                "timeout_seconds": timeout_seconds
            },
            priority=MessagePriority.HIGH,
            ttl_seconds=timeout_seconds
        )
        
        await self.send_message(request)
        
        # Wait for response
        return await self._wait_for_response(request.id, timeout_seconds)
    
    async def share_state(
        self,
        agent_id: str,
        state: Dict[str, Any],
        recipients: Optional[List[str]] = None,
        ttl_seconds: int = 3600
    ) -> bool:
        """
        Share state with other agents.
        
        Args:
            agent_id: Agent sharing state
            state: State data to share
            recipients: Specific recipients (None for all)
            ttl_seconds: State TTL
            
        Returns:
            True if shared successfully
        """
        # Store in SQLite
        self._sqlite.store_agent_state(agent_id, state, ttl_seconds)
        
        if recipients:
            for recipient in recipients:
                message = AgentMessage(
                    sender=agent_id,
                    recipient=recipient,
                    message_type=MessageType.STATE_UPDATE,
                    payload={"state": state, "agent_id": agent_id},
                    ttl_seconds=ttl_seconds
                )
                await self.send_message(message)
        else:
            # Broadcast state update
            await self.broadcast(
                sender=agent_id,
                payload={"state": state, "agent_id": agent_id},
                message_type=MessageType.STATE_UPDATE
            )
        
        # Also store in Redis if available
        if self._connected and self._redis:
            try:
                key = f"{self.PREFIX_STATE}{agent_id}"
                await self._redis.setex(key, ttl_seconds, json.dumps(state))
            except Exception as e:
                logger.error(f"Failed to store state in Redis: {e}")
        
        return True
    
    async def get_agent_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current state of an agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent state or None
        """
        # Try Redis first
        if self._connected and self._redis:
            try:
                key = f"{self.PREFIX_STATE}{agent_id}"
                data = await self._redis.get(key)
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.error(f"Failed to get state from Redis: {e}")
        
        # Fall back to SQLite
        return self._sqlite.get_agent_state(agent_id)
    
    async def get_delivery_status(self, message_id: str) -> Optional[MessageDelivery]:
        """Get delivery status for a message."""
        return self._sqlite.get_delivery_status(message_id)
    
    async def wait_for_response(
        self,
        correlation_id: str,
        timeout_seconds: float = 30.0
    ) -> Optional[AgentMessage]:
        """
        Wait for a response message.
        
        Args:
            correlation_id: Correlation ID to wait for
            timeout_seconds: Maximum wait time
            
        Returns:
            Response message or None if timeout
        """
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout_seconds:
            # Check SQLite for responses
            messages = self._sqlite.get_messages_for_recipient("*")
            for msg in messages:
                if msg.correlation_id == correlation_id:
                    if msg.message_type in [
                        MessageType.HELP_RESPONSE,
                        MessageType.TASK_COMPLETE,
                        MessageType.STATE_RESPONSE
                    ]:
                        return msg
            
            await asyncio.sleep(0.1)
        
        return None
    
    async def _pubsub_listener(self):
        """Background task for Redis pub/sub listening."""
        try:
            self._pubsub = self._redis.pubsub()
            
            # Subscribe to all relevant channels
            channels = set()
            for agent_id, handlers in self._subscriptions.items():
                channels.add(f"{self.PREFIX_CHANNEL}{agent_id}")
            channels.add(f"{self.PREFIX_CHANNEL}broadcast")
            
            if channels:
                await self._pubsub.subscribe(*channels)
                logger.info(f"Subscribed to channels: {channels}")
            
            async for message in self._pubsub.listen():
                if message['type'] == 'message':
                    try:
                        msg_data = json.loads(message['data'])
                        agent_message = AgentMessage.from_dict(msg_data)
                        
                        # Route to handlers
                        await self._route_message(agent_message)
                        
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in pub/sub message")
                    except Exception as e:
                        logger.error(f"Error processing pub/sub message: {e}")
                        
        except asyncio.CancelledError:
            logger.info("Pub/Sub listener cancelled")
            raise
        except Exception as e:
            logger.error(f"Pub/Sub listener error: {e}")
    
    async def _message_processor(self):
        """Background task for processing queued messages."""
        while True:
            try:
                message = await self._message_queue.get()
                await self._route_message(message)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Message processor error: {e}")
    
    async def _route_message(self, message: AgentMessage):
        """Route message to appropriate handlers."""
        # Find matching handlers
        handlers_to_call = []
        
        for agent_id, handlers in self._subscriptions.items():
            if message.recipient in [agent_id, "*", "broadcast"]:
                for msg_type, handler in handlers:
                    if msg_type is None or msg_type == message.message_type:
                        handlers_to_call.append(handler)
        
        # Call handlers
        for handler in handlers_to_call:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(message))
                else:
                    handler(message)
            except Exception as e:
                logger.error(f"Handler error: {e}")
        
        # Mark as delivered
        self._sqlite.update_delivery_status(message.id, DeliveryStatus.DELIVERED)
    
    async def _wait_for_response(
        self,
        request_id: str,
        timeout_seconds: int
    ) -> Optional[AgentMessage]:
        """Wait for a response to a request."""
        return await self.wait_for_response(request_id, timeout_seconds)
    
    async def cleanup(self):
        """Clean up expired messages and states."""
        self._sqlite.cleanup_expired()


class AgentCoordinator:
    """
    High-level coordinator for agent collaboration.
    
    Provides patterns for:
    - Task distribution
    - Parallel execution coordination
    - Consensus building
    - Workflow orchestration
    """
    
    def __init__(self, bus: AgentBus):
        """
        Initialize coordinator.
        
        Args:
            bus: AgentBus instance
        """
        self.bus = bus
        self._workflows: Dict[str, Dict[str, Any]] = {}
        self._task_futures: Dict[str, asyncio.Future] = {}
    
    async def distribute_task(
        self,
        task_id: str,
        task_type: str,
        agents: List[str],
        payload: Dict[str, Any],
        strategy: str = "any"  # "any", "all", "race"
    ) -> Dict[str, Any]:
        """
        Distribute a task to multiple agents.
        
        Args:
            task_id: Unique task identifier
            task_type: Type of task
            agents: List of agent IDs to distribute to
            payload: Task payload
            strategy: Distribution strategy
            
        Returns:
            Task results
        """
        results = {}
        
        if strategy == "race":
            # First to complete wins
            futures = []
            for agent in agents:
                future = self._send_task_and_wait(agent, task_id, task_type, payload)
                futures.append(future)
            
            done, pending = await asyncio.wait(
                futures,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel pending
            for p in pending:
                p.cancel()
            
            # Return first result
            if done:
                return await list(done)[0]
                
        elif strategy == "all":
            # Wait for all agents
            tasks = [
                self._send_task_and_wait(agent, task_id, task_type, payload)
                for agent in agents
            ]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for agent, response in zip(agents, responses):
                if not isinstance(response, Exception):
                    results[agent] = response
                    
        else:  # "any"
            # Send to all, return first success
            for agent in agents:
                try:
                    result = await self._send_task_and_wait(
                        agent, task_id, task_type, payload, timeout=30
                    )
                    if result:
                        results[agent] = result
                        break
                except asyncio.TimeoutError:
                    continue
        
        return results
    
    async def _send_task_and_wait(
        self,
        agent: str,
        task_id: str,
        task_type: str,
        payload: Dict[str, Any],
        timeout: float = 60.0
    ) -> Dict[str, Any]:
        """Send task to agent and wait for completion."""
        message = await self.bus.send_direct(
            sender="coordinator",
            recipient=agent,
            payload={
                "task_id": task_id,
                "task_type": task_type,
                "data": payload
            },
            message_type=MessageType.TASK_REQUEST
        )
        
        # Wait for completion
        start = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start) < timeout:
            messages = await self.bus.get_messages("coordinator", since=message.timestamp)
            for msg in messages:
                if (msg.correlation_id == message.id and 
                    msg.message_type in [MessageType.TASK_COMPLETE, MessageType.TASK_FAILED]):
                    return msg.payload
            await asyncio.sleep(0.1)
        
        raise asyncio.TimeoutError(f"Task {task_id} timed out")
    
    async def build_consensus(
        self,
        proposal_id: str,
        agents: List[str],
        proposal: Dict[str, Any],
        timeout_seconds: int = 60
    ) -> Dict[str, Any]:
        """
        Build consensus among agents.
        
        Args:
            proposal_id: Unique proposal ID
            agents: List of agents to vote
            proposal: Proposal details
            timeout_seconds: Voting timeout
            
        Returns:
            Consensus results
        """
        # Send consensus request
        request = AgentMessage(
            sender="coordinator",
            recipient="*",
            message_type=MessageType.CONSENSUS_REQUEST,
            payload={
                "proposal_id": proposal_id,
                "proposal": proposal,
                "voters": agents
            },
            correlation_id=proposal_id
        )
        await self.bus.send_message(request)
        
        # Collect votes
        votes = {}
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout_seconds:
            messages = await self.bus.get_messages("coordinator")
            for msg in messages:
                if (msg.correlation_id == proposal_id and 
                    msg.message_type == MessageType.CONSENSUS_VOTE):
                    votes[msg.sender] = msg.payload.get("vote", "abstain")
            
            if len(votes) >= len(agents):
                break
                
            await asyncio.sleep(0.1)
        
        # Calculate result
        yes_votes = sum(1 for v in votes.values() if v == "yes")
        no_votes = sum(1 for v in votes.values() if v == "no")
        
        result = {
            "proposal_id": proposal_id,
            "total_votes": len(votes),
            "yes": yes_votes,
            "no": no_votes,
            "abstain": len(votes) - yes_votes - no_votes,
            "passed": yes_votes > no_votes,
            "votes": votes
        }
        
        # Broadcast result
        await self.bus.broadcast(
            sender="coordinator",
            payload=result,
            message_type=MessageType.CONSENSUS_RESULT
        )
        
        return result
    
    async def start_workflow(
        self,
        workflow_id: str,
        steps: List[Dict[str, Any]],
        agents: List[str]
    ) -> str:
        """
        Start a coordinated workflow.
        
        Args:
            workflow_id: Unique workflow ID
            steps: List of workflow steps
            agents: Agents participating
            
        Returns:
            Workflow ID
        """
        self._workflows[workflow_id] = {
            "id": workflow_id,
            "steps": steps,
            "agents": agents,
            "current_step": 0,
            "status": "running",
            "results": []
        }
        
        # Broadcast workflow start
        await self.bus.broadcast(
            sender="coordinator",
            payload={
                "workflow_id": workflow_id,
                "steps": steps,
                "agents": agents
            },
            message_type=MessageType.WORKFLOW_START
        )
        
        return workflow_id
    
    async def execute_workflow_step(
        self,
        workflow_id: str,
        step_index: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a workflow step.
        
        Args:
            workflow_id: Workflow ID
            step_index: Step index (None for current)
            
        Returns:
            Step results
        """
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        if step_index is None:
            step_index = workflow["current_step"]
        
        if step_index >= len(workflow["steps"]):
            workflow["status"] = "completed"
            await self.bus.broadcast(
                sender="coordinator",
                payload={"workflow_id": workflow_id, "status": "completed"},
                message_type=MessageType.WORKFLOW_COMPLETE
            )
            return {"status": "completed"}
        
        step = workflow["steps"][step_index]
        
        # Broadcast step start
        await self.bus.broadcast(
            sender="coordinator",
            payload={
                "workflow_id": workflow_id,
                "step_index": step_index,
                "step": step
            },
            message_type=MessageType.WORKFLOW_STEP
        )
        
        # Execute step
        results = await self.distribute_task(
            task_id=f"{workflow_id}-step-{step_index}",
            task_type=step["type"],
            agents=workflow["agents"],
            payload=step.get("payload", {}),
            strategy=step.get("strategy", "any")
        )
        
        workflow["results"].append(results)
        workflow["current_step"] = step_index + 1
        
        return results


# ==================== Convenience Functions ====================

async def create_agent_bus(
    redis_url: Optional[str] = None,
    sqlite_path: str = "/tmp/agent_messages.db"
) -> AgentBus:
    """
    Factory function to create and connect AgentBus.
    
    Args:
        redis_url: Redis URL
        sqlite_path: SQLite database path
        
    Returns:
        Connected AgentBus instance
    """
    bus = AgentBus(redis_url=redis_url, sqlite_path=sqlite_path)
    await bus.connect()
    return bus


async def send_task_request(
    bus: AgentBus,
    sender: str,
    recipient: str,
    task_type: str,
    task_data: Dict[str, Any],
    timeout_seconds: int = 300
) -> Optional[AgentMessage]:
    """
    Send a task request and wait for completion.
    
    Args:
        bus: AgentBus instance
        sender: Sender agent ID
        recipient: Recipient agent ID
        task_type: Type of task
        task_data: Task data
        timeout_seconds: Timeout
        
    Returns:
        Response message or None
    """
    message = AgentMessage(
        sender=sender,
        recipient=recipient,
        message_type=MessageType.TASK_REQUEST,
        payload={
            "task_type": task_type,
            "data": task_data
        }
    )
    
    await bus.send_message(message)
    return await bus.wait_for_response(message.id, timeout_seconds)


async def broadcast_task_completion(
    bus: AgentBus,
    agent_id: str,
    task_id: str,
    result: Dict[str, Any],
    success: bool = True
) -> AgentMessage:
    """
    Broadcast task completion.
    
    Args:
        bus: AgentBus instance
        agent_id: Agent ID
        task_id: Task ID
        result: Task result
        success: Whether task succeeded
        
    Returns:
        Broadcast message
    """
    message_type = MessageType.TASK_COMPLETE if success else MessageType.TASK_FAILED
    
    return await bus.broadcast(
        sender=agent_id,
        payload={
            "task_id": task_id,
            "result": result,
            "success": success,
            "completed_at": datetime.utcnow().isoformat()
        },
        message_type=message_type
    )


# ==================== Demo Code ====================

async def demo_agent_protocol():
    """Demonstrate agent protocol functionality."""
    print("=" * 70)
    print("APEX Agent-to-Agent Communication Protocol - Demo")
    print("=" * 70)
    
    # Create bus
    bus = await create_agent_bus(sqlite_path="/tmp/agent_protocol_demo.db")
    
    # Message tracking for demo
    received_messages = []
    
    async def message_handler(message: AgentMessage):
        """Demo message handler."""
        received_messages.append(message)
        print(f"   📨 [{message.recipient}] Received {message.message_type.value} from {message.sender}")
    
    # Subscribe agents
    print("\n1. Subscribing agents...")
    await bus.subscribe("agent-1", handler=message_handler)
    await bus.subscribe("agent-2", handler=message_handler)
    await bus.subscribe("agent-3", handler=message_handler)
    print("   ✓ 3 agents subscribed")
    
    # Send direct message
    print("\n2. Sending direct message...")
    msg1 = await bus.send_direct(
        sender="agent-1",
        recipient="agent-2",
        payload={"greeting": "Hello from agent-1!", "data": [1, 2, 3]},
        message_type=MessageType.DIRECT
    )
    print(f"   ✓ Sent: {msg1.id[:8]}...")
    
    # Wait a bit for delivery
    await asyncio.sleep(0.2)
    
    # Get messages
    messages = await bus.get_messages("agent-2")
    print(f"   ✓ agent-2 has {len(messages)} messages")
    
    # Broadcast
    print("\n3. Broadcasting message...")
    broadcast_msg = await bus.broadcast(
        sender="agent-1",
        payload={"announcement": "All agents report in!"},
        message_type=MessageType.BROADCAST
    )
    print(f"   ✓ Broadcast: {broadcast_msg.id[:8]}...")
    
    await asyncio.sleep(0.2)
    
    # Task request
    print("\n4. Task request workflow...")
    task_msg = AgentMessage(
        sender="agent-1",
        recipient="agent-2",
        message_type=MessageType.TASK_REQUEST,
        payload={
            "task_type": "analyze_code",
            "files": ["main.py", "utils.py"]
        },
        priority=MessagePriority.HIGH
    )
    await bus.send_message(task_msg)
    print(f"   ✓ Task request sent: {task_msg.id[:8]}...")
    
    # Simulate task completion
    completion = task_msg.create_reply({
        "task_id": task_msg.id,
        "status": "completed",
        "findings": ["Issue #1", "Issue #2"]
    }, MessageType.TASK_COMPLETE)
    completion.sender = "agent-2"
    completion.recipient = "agent-1"
    await bus.send_message(completion)
    print(f"   ✓ Task completion sent: {completion.id[:8]}...")
    
    # State sharing
    print("\n5. State sharing...")
    await bus.share_state(
        agent_id="agent-1",
        state={
            "status": "idle",
            "capabilities": ["code_review", "testing"],
            "current_load": 0.3
        },
        recipients=["agent-2", "agent-3"]
    )
    print("   ✓ State shared with agent-2 and agent-3")
    
    # Get agent state
    state = await bus.get_agent_state("agent-1")
    if state:
        print(f"   ✓ Retrieved state: {state.get('status')}")
    
    # Coordinator demo
    print("\n6. Coordinator - Consensus building...")
    coordinator = AgentCoordinator(bus)
    
    consensus_result = await coordinator.build_consensus(
        proposal_id="proposal-001",
        agents=["agent-1", "agent-2", "agent-3"],
        proposal={"action": "deploy", "version": "1.0.0"},
        timeout_seconds=5
    )
    print(f"   ✓ Consensus: {consensus_result.get('passed', False)}")
    print(f"   ✓ Votes: {consensus_result.get('votes', {})}")
    
    # Workflow demo
    print("\n7. Coordinator - Workflow...")
    workflow_id = await coordinator.start_workflow(
        workflow_id="workflow-001",
        steps=[
            {"type": "validate", "payload": {"schema": "v1"}},
            {"type": "build", "payload": {"target": "production"}},
            {"type": "test", "payload": {"suite": "full"}}
        ],
        agents=["agent-1", "agent-2"]
    )
    print(f"   ✓ Workflow started: {workflow_id}")
    
    # Delivery tracking
    print("\n8. Delivery tracking...")
    status = await bus.get_delivery_status(msg1.id)
    if status:
        print(f"   ✓ Message {msg1.id[:8]}... status: {status.status.value}")
    
    # Cleanup
    print("\n9. Cleanup...")
    await bus.cleanup()
    print("   ✓ Expired messages cleaned up")
    
    await bus.disconnect()
    print("   ✓ Bus disconnected")
    
    print("\n" + "=" * 70)
    print("Demo completed successfully!")
    print("=" * 70)
    
    return True


if __name__ == "__main__":
    try:
        asyncio.run(demo_agent_protocol())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise
