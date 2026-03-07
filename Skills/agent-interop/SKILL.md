---
name: agent-interop
description: Research and implement agent interoperability protocols (MCP, A2A, ACP, SLIM, Agora, ANP, AG-UI)
trigger: "When user asks about agent protocols, MCP, A2A, interop, agent internet, or protocol comparisons"
metadata:
  author: youngstunners.zo.computer
---

# Agent Interoperability Skill

Research, implement, and compare agent communication protocols.

## Supported Protocols

| Protocol | Owner | Use Case | Triggers |
|----------|-------|----------|----------|
| MCP | Anthropic | LLM ↔ Tools | "MCP", "model context protocol" |
| A2A | Google | Agent ↔ Agent | "A2A", "agent to agent" |
| ACP | IBM | Persistent conversations | "ACP", "agent communication" |
| SLIM | Cisco | Real-time messaging | "SLIM", "low latency" |
| Agora | Oxford | NLP to protocols | "Agora", "natural language" |
| ANP | - | Decentralized discovery | "ANP", "agent network" |
| AG-UI | CopilotKit | Agent ↔ UI | "AG-UI", "agent UI" |

## Usage

```bash
# Check if a site supports MCP
agent-interop check-mcp <url>

# Get protocol details
agent-interop info <protocol>

# Compare protocols
agent-interop compare

# Find implementations
agent-interop find <protocol>
```

## Tools Used
- web_search: Research latest developments
- read_webpage: Check protocol documentation
- grep_search: Find implementations in code