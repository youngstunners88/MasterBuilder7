# APEX Agent-to-Agent Communication Protocol

A production-ready protocol for pure agentic collaboration, enabling agents to communicate, coordinate, and work together seamlessly.

## Features

- **🚀 Async/Await Support**: Built on asyncio for concurrent messaging
- **💾 Redis-Backed**: High-performance pub/sub with Redis
- **🔄 SQLite Fallback**: Automatic fallback when Redis is unavailable
- **📨 Multiple Message Types**: Standard patterns for common use cases
- **🎯 Priority Messaging**: Critical messages processed first
- **📊 Delivery Tracking**: Know when messages are delivered and read
- **🔒 Type-Safe**: Full type hints for better IDE support
- **🧪 Well-Tested**: Comprehensive examples and demo code

## Quick Start

```python
import asyncio
from apex.agents.agent_protocol import (
    AgentBus, AgentMessage, MessageType, create_agent_bus
)

async def main():
    # Create and connect the message bus
    bus = await create_agent_bus()
    
    # Subscribe to messages
    async def handle_message(message: AgentMessage):
        print(f"Received: {message.payload}")
    
    await bus.subscribe("my-agent", handler=handle_message)
    
    # Send a message
    await bus.send_direct(
        sender="sender-agent",
        recipient="my-agent",
        payload={"hello": "world"},
        message_type=MessageType.DIRECT
    )
    
    await bus.disconnect()

asyncio.run(main())
```

## Core Components

### AgentMessage

The standard message format for all agent communication:

```python
from apex.agents.agent_protocol import AgentMessage, MessageType, MessagePriority

message = AgentMessage(
    sender="agent-1",
    recipient="agent-2",  # Use "*" for broadcast
    message_type=MessageType.TASK_REQUEST,
    payload={"task": "process_data", "data": [...]},
    priority=MessagePriority.HIGH,
    ttl_seconds=300,  # Message expires after 5 minutes
    correlation_id="task-123",  # Link related messages
)
```

### Message Types

| Type | Purpose |
|------|---------|
| `TASK_REQUEST` | Request an agent to perform a task |
| `TASK_COMPLETE` | Notify task completion |
| `TASK_FAILED` | Notify task failure |
| `TASK_PROGRESS` | Task progress update |
| `HELP_REQUEST` | Request help from specialist |
| `HELP_RESPONSE` | Response to help request |
| `STATE_UPDATE` | Share state/context update |
| `BROADCAST` | Broadcast to all agents |
| `DIRECT` | Direct message to specific agent |
| `CONSENSUS_REQUEST` | Request consensus vote |
| `CONSENSUS_VOTE` | Cast consensus vote |
| `WORKFLOW_START` | Start coordinated workflow |

### AgentBus

The pub/sub message bus for all communication:

```python
from apex.agents.agent_protocol import AgentBus

# Create with custom configuration
bus = AgentBus(
    redis_url="redis://localhost:6379",
    sqlite_path="/tmp/agent_messages.db",
    message_ttl=86400
)

await bus.connect()
```

#### Methods

- `send_message(message)` - Send a message
- `send_direct(sender, recipient, payload, ...)` - Send direct message (convenience)
- `broadcast(sender, payload, ...)` - Broadcast to all agents
- `subscribe(agent_id, message_type, handler)` - Subscribe to messages
- `get_messages(recipient, ...)` - Get pending messages
- `request_help(...)` - Request specialist assistance
- `share_state(...)` - Share agent state
- `get_agent_state(agent_id)` - Get agent state

### AgentCoordinator

High-level coordinator for complex patterns:

```python
from apex.agents.agent_protocol import AgentCoordinator

coordinator = AgentCoordinator(bus)

# Distribute tasks
results = await coordinator.distribute_task(
    task_id="task-001",
    task_type="process_chunk",
    agents=["worker-1", "worker-2", "worker-3"],
    payload={"data": [...]},
    strategy="all"  # or "any", "race"
)

# Build consensus
result = await coordinator.build_consensus(
    proposal_id="deploy-v2",
    agents=["agent-1", "agent-2", "agent-3"],
    proposal={"action": "deploy", "version": "2.0"},
    timeout_seconds=60
)
```

## Usage Patterns

### 1. Task Request/Response

```python
# Worker subscribes to tasks
async def worker_handler(message: AgentMessage):
    if message.message_type == MessageType.TASK_REQUEST:
        # Do work...
        result = process_task(message.payload)
        
        # Send completion
        completion = message.create_reply(
            payload={"result": result},
            message_type=MessageType.TASK_COMPLETE
        )
        completion.sender = "worker-agent"
        await bus.send_message(completion)

await bus.subscribe("worker-agent", handler=worker_handler)

# Client sends task
response = await send_task_request(
    bus=bus,
    sender="client-agent",
    recipient="worker-agent",
    task_type="analyze",
    task_data={"file": "data.csv"},
    timeout_seconds=60
)
```

### 2. Broadcast Pattern

```python
# Subscribe multiple agents
for agent_id in ["agent-1", "agent-2", "agent-3"]:
    await bus.subscribe(agent_id, handler=handle_broadcast)

# Broadcast to all
await bus.broadcast(
    sender="coordinator",
    payload={"announcement": "Maintenance window starting"},
    message_type=MessageType.BROADCAST
)
```

### 3. Help Request Pattern

```python
# Request help from security specialist
help_response = await bus.request_help(
    requester="developer-agent",
    specialist_type="security",
    task_description="Audit auth module",
    context={"files": ["auth.py"]},
    timeout_seconds=300
)

if help_response:
    recommendations = help_response.payload.get("recommendations")
```

### 4. State Sharing

```python
# Share current state
await bus.share_state(
    agent_id="data-processor",
    state={
        "status": "processing",
        "progress": 0.75,
        "items_processed": 750
    },
    recipients=["monitoring-agent", "orchestrator"]
)

# Get agent state elsewhere
state = await bus.get_agent_state("data-processor")
print(f"Progress: {state['progress']*100}%")
```

### 5. Parallel Task Distribution

```python
# Distribute to all workers and wait for all
coordinator = AgentCoordinator(bus)

results = await coordinator.distribute_task(
    task_id="parallel-process",
    task_type="process_chunk",
    agents=["worker-1", "worker-2", "worker-3"],
    payload={"chunk_size": 1000},
    strategy="all"  # Wait for all, "race" for first, "any" for first success
)

for worker_id, result in results.items():
    print(f"{worker_id}: {result}")
```

### 6. Consensus Building

```python
# Build consensus for deployment
coordinator = AgentCoordinator(bus)

result = await coordinator.build_consensus(
    proposal_id="deploy-v2.0",
    agents=["dev-1", "dev-2", "dev-3", "ops-1"],
    proposal={"version": "2.0.0", "canary": True},
    timeout_seconds=300
)

if result["passed"]:
    print(f"Consensus reached! Yes: {result['yes']}, No: {result['no']}")
    await proceed_with_deployment()
else:
    print("Consensus not reached")
```

## Configuration

### Environment Variables

```bash
# Redis configuration
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_password

# Or use SQLite only (no Redis)
AGENT_PROTOCOL_MODE=sqlite
```

### Programmatic Configuration

```python
from apex.agents.agent_protocol import AgentBus

bus = AgentBus(
    redis_url="redis://localhost:6379",
    redis_host="localhost",      # Fallback if no URL
    redis_port=6379,
    redis_password=None,
    sqlite_path="/data/agent_messages.db",
    message_ttl=86400,           # 24 hours
    max_retries=3
)
```

## Priority Levels

Messages are processed in priority order:

1. `CRITICAL` (0) - Process immediately (alerts, failures)
2. `HIGH` (1) - Process soon (urgent tasks)
3. `NORMAL` (2) - Standard priority (default)
4. `LOW` (3) - Process when convenient (batch jobs)
5. `BACKGROUND` (4) - Background processing (analytics)

```python
from apex.agents.agent_protocol import MessagePriority

await bus.send_direct(
    sender="monitor",
    recipient="ops-team",
    payload={"alert": "Service down!"},
    priority=MessagePriority.CRITICAL
)
```

## Delivery Tracking

Track message delivery status:

```python
# Send message
message = await bus.send_direct(...)

# Check status
status = await bus.get_delivery_status(message.id)
print(f"Status: {status.status}")  # PENDING, DELIVERED, READ, FAILED
```

## Error Handling

```python
from apex.agents.agent_protocol import MessageType

try:
    response = await bus.request_help(
        requester="agent-1",
        specialist_type="security",
        task_description="Audit needed",
        context={},
        timeout_seconds=30
    )
    
    if response is None:
        print("Help request timed out")
    elif response.message_type == MessageType.TASK_FAILED:
        print(f"Help request failed: {response.payload.get('error')}")
    else:
        print(f"Help received: {response.payload}")
        
except Exception as e:
    print(f"Error: {e}")
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Agent 1   │◄───►│   AgentBus  │◄───►│   Agent 2   │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
       ┌──────▼──────┐          ┌──────▼──────┐
       │    Redis    │◄────────►│    SQLite   │
       │   (Pub/Sub) │  Fallback│   (Persist) │
       └─────────────┘          └─────────────┘
```

## Testing

Run the demo to see all features:

```bash
cd /home/teacherchris37/MasterBuilder7
python3 -m apex.agents.agent_protocol
```

Run examples:

```bash
cd /home/teacherchris37/MasterBuilder7
python3 apex/agents/examples/agent_communication_example.py
```

## API Reference

### AgentMessage

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | str | Unique message ID |
| `message_type` | MessageType | Type of message |
| `sender` | str | Sender agent ID |
| `recipient` | str | Recipient agent ID ("*" for broadcast) |
| `payload` | dict | Message data |
| `timestamp` | str | ISO format timestamp |
| `priority` | MessagePriority | Message priority |
| `ttl_seconds` | int | Time-to-live |
| `correlation_id` | str | Link related messages |
| `reply_to` | str | Reply-to agent ID |

### AgentBus

| Method | Returns | Description |
|--------|---------|-------------|
| `connect()` | bool | Connect to Redis/SQLite |
| `disconnect()` | None | Disconnect |
| `send_message(msg)` | bool | Send a message |
| `send_direct(...)` | AgentMessage | Send direct message |
| `broadcast(...)` | AgentMessage | Broadcast to all |
| `subscribe(...)` | bool | Subscribe to messages |
| `get_messages(...)` | List[AgentMessage] | Get pending messages |
| `request_help(...)` | AgentMessage | Request specialist help |
| `share_state(...)` | bool | Share agent state |
| `get_agent_state(...)` | dict | Get agent state |

### AgentCoordinator

| Method | Returns | Description |
|--------|---------|-------------|
| `distribute_task(...)` | dict | Distribute task to agents |
| `build_consensus(...)` | dict | Build consensus |
| `start_workflow(...)` | str | Start workflow |
| `execute_workflow_step(...)` | dict | Execute workflow step |

## License

Part of the APEX Agent System - MasterBuilder7
