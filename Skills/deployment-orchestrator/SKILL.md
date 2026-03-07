---
name: deployment-orchestrator
description: Multi-agent deployment coordination. Orchestrates parallel deployments across the 3-Zo network with budget tracking.
trigger: "When user asks to deploy, orchestrate, or coordinate multi-agent deployments"
metadata:
  author: youngstunners.zo.computer
  version: 1.0.0
---

# Deployment Orchestrator Skill

Coordinates deployments across youngstunners, kofi, and Kimi CLI.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Deployment Orchestrator                │
├─────────────────────────────────────────────────────────┤
│  ┌─────────┐    ┌─────────┐    ┌─────────┐             │
│  │ Captain │───▶│ Router  │───▶│Architect│             │
│  └────┬────┘    └─────────┘    └────┬────┘             │
│       │                              │                   │
│       │         ┌────────────────────┼───────────────┐   │
│       │         ▼                    ▼               ▼   │
│       │    ┌──────────┐       ┌──────────┐   ┌─────────┐│
│       │    │ Frontend │       │ Backend  │   │ Guardian││
│       │    └────┬─────┘       └────┬─────┘   └────┬────┘│
│       │         └─────────┬────────┘              │      │
│       │                   ▼                       │      │
│       │            ┌───────────┐                  │      │
│       └───────────▶│  DevOps   │◀─────────────────┘      │
│                    └─────┬─────┘                         │
│                          ▼                               │
│                    ┌───────────┐                         │
│                    │ Evolution │                         │
│                    └───────────┘                         │
└─────────────────────────────────────────────────────────┘
```

## Usage

```bash
# Deploy a repository
bun /home/workspace/Skills/deployment-orchestrator/scripts/deploy.ts launch <repo> <track> <budget>

# Check deployment status
bun /home/workspace/Skills/deployment-orchestrator/scripts/deploy.ts status <deployment-id>

# List all deployments
bun /home/workspace/Skills/deployment-orchestrator/scripts/deploy.ts list

# Cancel deployment
bun /home/workspace/Skills/deployment-orchestrator/scripts/deploy.ts cancel <deployment-id>
```

## Tracks

| Track | Agents | Avg Time | Cost |
|-------|--------|----------|------|
| `web` | 4 | 3 min | $12 |
| `capacitor` | 6 | 5 min | $25 |
| `flutter` | 6 | 7 min | $30 |
| `auto` | varies | varies | varies |

## Budget Management

- Hard limit enforcement
- Warning at 80%
- Auto-cancel at 100%
- Cost tracking per agent

## Consensus

3-verifier consensus required:
- Syntax check (DevOps)
- Logic check (Guardian)
- Security check (Guardian)

---

*Deployment Orchestrator: Ship it safe*
