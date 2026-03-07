# 🤖 RobeetsDay Agents

Agent definitions and configurations for the RobeetsDay ecosystem.

## Agent Overview

| Agent | Platform | Status | Purpose |
|-------|----------|--------|---------|
| **Nduna** | Telegram | ✅ Production | Customer support & routing |
| **Architect** | GitHub | 🚧 Beta | System design & reviews |
| **Implementer** | Kimi CLI | ✅ Production | Code generation |
| **Security** | CI/CD | ✅ Production | Security auditing |
| **Test Engineer** | Automated | 🚧 Beta | Test generation |
| **Sub-atomic** | Swarm | 🔬 Experimental | Micro-task agents |

## Directory Structure

```
agents/
├── README.md           # This file
├── nduna/             # Telegram bot
├── architect/         # GitHub agent
├── implementer/       # Kimi CLI agent
├── security/          # Security agent
├── test-engineer/     # Testing agent
└── subatomic/         # Sub-atomic templates
```

## Agent Communication

All agents communicate via:
- **Redis Pub/Sub** - Real-time events
- **MongoDB** - Persistent state
- **GitHub API** - Code collaboration
- **Telegram API** - User interaction

## Creating New Agents

1. Create directory: `mkdir agents/my-agent`
2. Add `SKILL.md` with capabilities
3. Add `config.yaml` with settings
4. Update `AGENTS.md` in root
5. Update this README

---

*See [AGENTS.md](../AGENTS.md) for detailed documentation.*
