---
name: agent-leadership
description: Lead and develop a team of autonomous agents to execute opportunities. Manages agent orchestration, task delegation, quality control, and continuous improvement of the agent swarm.
metadata:
  author: youngstunners.zo.computer
---

# Agent Leadership Skill

## Purpose
Lead the opportunity team of agents - orchestrate multiple AI agents to work together on complex tasks, ensuring quality output and continuous improvement.

## Core Capabilities

### 1. Agent Orchestration
- **Task Decomposition**: Break complex opportunities into agent-sized tasks
- **Agent Selection**: Match agents to tasks based on capabilities
- **Coordination**: Manage parallel execution and dependencies
- **Quality Gates**: Verify output at each stage

### 2. Opportunity Management
- **Discovery**: Identify opportunities in data/conversations
- **Prioritization**: Rank by impact, feasibility, resources
- **Execution Plans**: Create actionable agent workflows
- **Tracking**: Monitor progress and outcomes

### 3. Agent Development
- **Skill Assessment**: Evaluate agent capabilities
- **Training**: Create new skills from successful patterns
- **Optimization**: Refine prompts and workflows
- **Documentation**: Capture learnings for future agents

### 4. Quality Control
- **Review**: Check agent outputs for accuracy
- **Testing**: Validate before delivery
- **Feedback**: Loop corrections back to agents
- **Metrics**: Track success rates and improvements

## Usage
```python
from agent_leadership import AgentLeader

leader = AgentLeader()
leader.assess_opportunity(user_request)
leader.assign_agents(task_breakdown)
leader.coordinate_execution()
leader.verify_quality(output)
```

## Integration with Agent Orchestrator
Use `ao` CLI for execution:
```bash
ao init --auto
ao spawn <project> <issue>
```