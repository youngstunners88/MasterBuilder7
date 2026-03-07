---
name: agent-lightning
description: "RL training framework for AI agents. Use AgentLightningClient for experiment tracking, tracing, and training agent policies."
metadata:
  author: youngstunners.zo.computer
---

# Agent Lightning Skill

Reinforcement Learning training for AI agents.

## Features

- **AgentOpsTracer** - Trace prompts, tool calls, rewards
- **LightningStore** - Central hub for experiments
- **APO** - Advanced Policy Optimization
- **Algorithm** - Train and improve agent policies

## Usage

```python
from agentlightning import AgentLightningClient, AgentOpsTracer

# Initialize
client = AgentLightningClient()
tracer = AgentOpsTracer()

# Track an agent run
tracer.emit_prompt("user query")
tracer.emit_tool_call("search", {"query": "..."})
tracer.emit_reward(1.0)
```

## Docs
- PyPI: https://pypi.org/project/agentlightning/
- GitHub: https://github.com/agentlightning/agentlightning