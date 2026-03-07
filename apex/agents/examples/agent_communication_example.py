#!/usr/bin/env python3
"""
APEX Agent Communication Protocol - Usage Examples

This file demonstrates how to use the agent-to-agent communication protocol
for building collaborative multi-agent systems.
"""

import asyncio
from typing import Dict, Any
from datetime import datetime

# Import from the agent_protocol module
import sys
sys.path.insert(0, '/home/teacherchris37/MasterBuilder7')

from apex.agents.agent_protocol import (
    AgentBus,
    AgentCoordinator,
    AgentMessage,
    MessageType,
    MessagePriority,
    create_agent_bus,
    send_task_request,
    broadcast_task_completion,
)


# ============================================
# Example 1: Basic Message Passing
# ============================================

async def example_basic_messaging():
    """Example: Basic agent messaging."""
    print("\n" + "=" * 60)
    print("Example 1: Basic Message Passing")
    print("=" * 60)
    
    # Create and connect the message bus
    bus = await create_agent_bus(sqlite_path="/tmp/agent_example_1.db")
    
    # Define a message handler
    async def handle_message(message: AgentMessage):
        print(f"📨 Received: {message.message_type.value} from {message.sender}")
        print(f"   Payload: {message.payload}")
    
    # Subscribe agent-2 to receive messages
    await bus.subscribe("agent-2", handler=handle_message)
    
    # Send a direct message from agent-1 to agent-2
    message = await bus.send_direct(
        sender="agent-1",
        recipient="agent-2",
        payload={"greeting": "Hello!", "data": [1, 2, 3]},
        message_type=MessageType.DIRECT
    )
    
    print(f"📤 Sent message: {message.id}")
    
    # Give time for message to be processed
    await asyncio.sleep(0.1)
    
    # Cleanup
    await bus.disconnect()
    print("✓ Example 1 complete")


# ============================================
# Example 2: Task Request and Completion
# ============================================

async def example_task_workflow():
    """Example: Task request and completion workflow."""
    print("\n" + "=" * 60)
    print("Example 2: Task Request and Completion")
    print("=" * 60)
    
    bus = await create_agent_bus(sqlite_path="/tmp/agent_example_2.db")
    
    # Worker agent handler
    async def worker_handler(message: AgentMessage):
        if message.message_type == MessageType.TASK_REQUEST:
            print(f"🛠️  Worker received task: {message.payload.get('task_type')}")
            
            # Simulate work
            await asyncio.sleep(0.1)
            
            # Send completion
            completion = message.create_reply(
                payload={
                    "result": "Task completed successfully!",
                    "timestamp": datetime.utcnow().isoformat()
                },
                message_type=MessageType.TASK_COMPLETE
            )
            completion.sender = message.recipient
            await bus.send_message(completion)
            print(f"✅ Worker sent completion")
    
    # Subscribe worker
    await bus.subscribe("worker-agent", handler=worker_handler)
    
    # Send task request
    task_msg = AgentMessage(
        sender="orchestrator",
        recipient="worker-agent",
        message_type=MessageType.TASK_REQUEST,
        payload={
            "task_type": "process_data",
            "data": {"items": ["a", "b", "c"]}
        }
    )
    await bus.send_message(task_msg)
    print(f"📋 Orchestrator sent task: {task_msg.id}")
    
    # Wait for completion
    response = await bus.wait_for_response(task_msg.id, timeout_seconds=5.0)
    if response:
        print(f"✅ Orchestrator received result: {response.payload}")
    
    await bus.disconnect()
    print("✓ Example 2 complete")


# ============================================
# Example 3: Broadcast Pattern
# ============================================

async def example_broadcast():
    """Example: Broadcasting to all agents."""
    print("\n" + "=" * 60)
    print("Example 3: Broadcast Pattern")
    print("=" * 60)
    
    bus = await create_agent_bus(sqlite_path="/tmp/agent_example_3.db")
    
    received_count = 0
    
    async def broadcast_handler(message: AgentMessage):
        nonlocal received_count
        if message.message_type == MessageType.BROADCAST:
            received_count += 1
            print(f"📢 {message.recipient} received broadcast from {message.sender}")
    
    # Subscribe multiple agents
    for i in range(5):
        await bus.subscribe(f"agent-{i}", handler=broadcast_handler)
    
    # Broadcast message
    broadcast_msg = await bus.broadcast(
        sender="coordinator",
        payload={"announcement": "System maintenance in 5 minutes"},
        message_type=MessageType.BROADCAST
    )
    
    await asyncio.sleep(0.1)
    print(f"✅ Broadcast reached {received_count} agents")
    
    await bus.disconnect()
    print("✓ Example 3 complete")


# ============================================
# Example 4: Help Request Pattern
# ============================================

async def example_help_request():
    """Example: Requesting help from specialist."""
    print("\n" + "=" * 60)
    print("Example 4: Help Request Pattern")
    print("=" * 60)
    
    bus = await create_agent_bus(sqlite_path="/tmp/agent_example_4.db")
    
    # Specialist agent
    async def security_specialist(message: AgentMessage):
        if message.message_type == MessageType.HELP_REQUEST:
            print(f"🔒 Security specialist helping {message.sender}")
            
            # Send help response
            response = message.create_reply(
                payload={
                    "recommendations": [
                        "Enable rate limiting",
                        "Update dependencies",
                        "Add input validation"
                    ],
                    "risk_level": "medium"
                },
                message_type=MessageType.HELP_RESPONSE
            )
            response.sender = "specialist:security"
            await bus.send_message(response)
    
    await bus.subscribe("specialist:security", handler=security_specialist)
    
    # Request help
    help_response = await bus.request_help(
        requester="developer-agent",
        specialist_type="security",
        task_description="Security audit needed for auth module",
        context={"files": ["auth.py", "middleware.py"]},
        timeout_seconds=5
    )
    
    if help_response:
        print(f"✅ Help received: {help_response.payload}")
    else:
        print("❌ Help request timed out")
    
    await bus.disconnect()
    print("✓ Example 4 complete")


# ============================================
# Example 5: State Sharing
# ============================================

async def example_state_sharing():
    """Example: Sharing state between agents."""
    print("\n" + "=" * 60)
    print("Example 5: State Sharing")
    print("=" * 60)
    
    bus = await create_agent_bus(sqlite_path="/tmp/agent_example_5.db")
    
    # Share state
    await bus.share_state(
        agent_id="data-processor",
        state={
            "status": "processing",
            "progress": 0.75,
            "items_processed": 750,
            "items_total": 1000,
            "estimated_completion": "2024-01-15T10:30:00Z"
        },
        recipients=["monitoring-agent", "orchestrator"]
    )
    print("📊 State shared by data-processor")
    
    # Retrieve state
    state = await bus.get_agent_state("data-processor")
    if state:
        print(f"✅ Retrieved state: {state.get('progress')*100:.0f}% complete")
    
    await bus.disconnect()
    print("✓ Example 5 complete")


# ============================================
# Example 6: Coordinator - Parallel Tasks
# ============================================

async def example_parallel_tasks():
    """Example: Distributing tasks to multiple agents."""
    print("\n" + "=" * 60)
    print("Example 6: Coordinator - Parallel Tasks")
    print("=" * 60)
    
    bus = await create_agent_bus(sqlite_path="/tmp/agent_example_6.db")
    coordinator = AgentCoordinator(bus)
    
    # Set up worker agents
    async def worker_handler(message: AgentMessage):
        if message.message_type == MessageType.TASK_REQUEST:
            # Simulate work
            await asyncio.sleep(0.05)
            
            completion = message.create_reply(
                payload={"processed_by": message.recipient, "status": "done"},
                message_type=MessageType.TASK_COMPLETE
            )
            completion.sender = message.recipient
            await bus.send_message(completion)
    
    for i in range(3):
        await bus.subscribe(f"worker-{i}", handler=worker_handler)
    
    # Distribute task
    print("🔄 Distributing task to 3 workers...")
    results = await coordinator.distribute_task(
        task_id="parallel-task-001",
        task_type="data_chunk_processing",
        agents=["worker-0", "worker-1", "worker-2"],
        payload={"chunk_size": 100},
        strategy="all"  # Wait for all agents
    )
    
    print(f"✅ Results from {len(results)} workers: {list(results.keys())}")
    
    await bus.disconnect()
    print("✓ Example 6 complete")


# ============================================
# Example 7: Coordinator - Consensus
# ============================================

async def example_consensus():
    """Example: Building consensus among agents."""
    print("\n" + "=" * 60)
    print("Example 7: Coordinator - Consensus Building")
    print("=" * 60)
    
    bus = await create_agent_bus(sqlite_path="/tmp/agent_example_7.db")
    coordinator = AgentCoordinator(bus)
    
    # Set up voting agents
    votes = {"agent-0": "yes", "agent-1": "yes", "agent-2": "no"}
    
    async def voter_handler(message: AgentMessage):
        if message.message_type == MessageType.CONSENSUS_REQUEST:
            proposal_id = message.payload.get("proposal_id")
            
            # Cast vote
            vote = votes.get(message.recipient, "abstain")
            vote_msg = AgentMessage(
                sender=message.recipient,
                recipient="coordinator",
                message_type=MessageType.CONSENSUS_VOTE,
                payload={"proposal_id": proposal_id, "vote": vote},
                correlation_id=proposal_id
            )
            await bus.send_message(vote_msg)
            print(f"🗳️  {message.recipient} voted: {vote}")
    
    for agent_id in votes.keys():
        await bus.subscribe(agent_id, handler=voter_handler)
    
    # Build consensus
    print("🗳️  Building consensus for deployment proposal...")
    result = await coordinator.build_consensus(
        proposal_id="deploy-v2.0",
        agents=list(votes.keys()),
        proposal={"action": "deploy", "version": "2.0.0", "canary": True},
        timeout_seconds=5
    )
    
    print(f"✅ Consensus result: {'PASSED' if result['passed'] else 'REJECTED'}")
    print(f"   Votes: Yes={result['yes']}, No={result['no']}, Abstain={result['abstain']}")
    
    await bus.disconnect()
    print("✓ Example 7 complete")


# ============================================
# Example 8: Priority Messaging
# ============================================

async def example_priority_messaging():
    """Example: Priority-based messaging."""
    print("\n" + "=" * 60)
    print("Example 8: Priority Messaging")
    print("=" * 60)
    
    bus = await create_agent_bus(sqlite_path="/tmp/agent_example_8.db")
    
    received_order = []
    
    async def priority_handler(message: AgentMessage):
        received_order.append((message.priority.name, message.payload.get("msg")))
    
    await bus.subscribe("priority-agent", handler=priority_handler)
    
    # Send messages with different priorities
    priorities = [
        (MessagePriority.LOW, "Low priority message"),
        (MessagePriority.CRITICAL, "Critical alert!"),
        (MessagePriority.NORMAL, "Normal message"),
        (MessagePriority.HIGH, "High priority message"),
        (MessagePriority.BACKGROUND, "Background task"),
    ]
    
    for priority, msg_text in priorities:
        await bus.send_direct(
            sender="sender",
            recipient="priority-agent",
            payload={"msg": msg_text},
            priority=priority
        )
    
    await asyncio.sleep(0.1)
    
    print("📨 Messages received in priority order:")
    for priority, msg in received_order:
        print(f"   [{priority}] {msg}")
    
    await bus.disconnect()
    print("✓ Example 8 complete")


# ============================================
# Main
# ============================================

async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("APEX Agent Communication Protocol - Examples")
    print("=" * 60)
    
    examples = [
        example_basic_messaging,
        example_task_workflow,
        example_broadcast,
        example_help_request,
        example_state_sharing,
        example_parallel_tasks,
        example_consensus,
        example_priority_messaging,
    ]
    
    for example in examples:
        try:
            await example()
        except Exception as e:
            print(f"❌ Example failed: {e}")
    
    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
