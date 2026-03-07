# 🔗 Elite Squad Integration

> **Kimi CLI (35.235.249.249) ↔ Elite Squad (100.127.121.51:4200)**

## Overview

Elite Squad runs on Zo Computer with 8 specialized agents. This bridge connects Kimi CLI to Elite Squad for tandem operation.

## The 8 Elite Squad Agents

| Agent | Role | Function |
|-------|------|----------|
| ⚓ **Captain** | Commander | Orchestration, safety validation |
| 🧭 **Meta-Router** | Pathfinder | Stack detection, intelligent routing |
| 📐 **Architect** | Planner | PRD generation, system design |
| 🎨 **Frontend** | UI/UX | React, Capacitor, Flutter builds |
| ⚙️ **Backend** | API/DB | FastAPI, Supabase development |
| 🛡️ **Guardian** | Quality | Testing, security scanning |
| 🚀 **DevOps** | Deployer | CI/CD, infrastructure |
| 📈 **Evolution** | Learner | Pattern extraction, improvement |

## Quick Start

```bash
# Check Elite Squad status
bun elite-bridge.ts status

# Deploy iHhashi through Elite Squad
bun elite-bridge.ts deploy https://github.com/youngstunners88/ihhashi capacitor 100

# Watch for updates
bun elite-bridge.ts watch &

# Sync completed tasks
bun elite-bridge.ts sync
```

## Workflow

```
Kimi CLI (You)
      │
      │ 1. Delegate task
      ▼
┌─────────────────┐
│ Elite Squad     │
│ Bridge          │
└────────┬────────┘
         │
         │ 2. Route to appropriate agent
         ▼
┌──────────────────────────────────┐
│         Elite Squad Flow         │
│  ⚓ Captain validates            │
│  🧭 Meta-Router decides path     │
│  📐 Architect creates plan       │
│  🎨 Frontend ←──parallel──→ ⚙️   │
│  🛡️ Guardian verifies            │
│  🚀 DevOps deploys               │
│  📈 Evolution learns             │
└────────┬─────────────────────────┘
         │
         │ 3. Return results
         ▼
Kimi CLI (Results)
```

## Command Reference

### `deploy <repo-url> [track] [budget]`

Deploy a repository through Elite Squad.

**Parameters:**
- `repo-url`: GitHub repository URL
- `track`: `capacitor`, `expo`, `flutter`, or `auto-detect`
- `budget`: Maximum USD to spend (default: 100)

**Example:**
```bash
bun elite-bridge.ts deploy https://github.com/youngstunners88/ihhashi capacitor 150
```

### `status`

Check status of all 8 Elite Squad agents.

**Example Output:**
```
╔════════════════════════════════════════════════╗
║           ELITE SQUAD STATUS                   ║
╠════════════════════════════════════════════════╣
║ ⚓ Captain       ✅ ready                     ║
║ 🧭 Meta-Router   ✅ ready                     ║
║ 📐 Architect     🔥 busy                      ║
║ 🎨 Frontend      ✅ ready                     ║
║ ⚙️  Backend       ✅ ready                     ║
║ 🛡️  Guardian      ✅ ready                     ║
║ 🚀 DevOps        ✅ ready                     ║
║ 📈 Evolution     ✅ ready                     ║
╠════════════════════════════════════════════════╣
║ Active Tasks: 1                                ║
║ Completed: 47                                  ║
╚════════════════════════════════════════════════╝
```

### `sync`

Check for completed tasks and update local state.

### `watch`

Continuous sync mode - checks every 10 seconds.

```bash
# Run in background
bun elite-bridge.ts watch &

# Stop watching
pkill -f "elite-bridge.ts watch"
```

### `message <text>`

Send a message directly to Elite Squad.

```bash
bun elite-bridge.ts message "Priority: Fix production bug in auth"
```

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    KIMI CLI (35.235.249.249)                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  elite-bridge.ts                                    │   │
│  │  • Task delegation                                  │   │
│  │  • Status monitoring                                │   │
│  │  • Result sync                                      │   │
│  └────────────────┬────────────────────────────────────┘   │
│                   │ HTTPS/Tailscale                         │
└───────────────────┼─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│              ZO COMPUTER (100.127.121.51:4200)              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  OpenFang + Elite Squad                             │   │
│  │                                                     │   │
│  │  ⚓ Captain       - Safety & orchestration         │   │
│  │  🧭 Meta-Router   - Stack detection               │   │
│  │  📐 Architect     - Planning & specs              │   │
│  │  🎨 Frontend      - UI development                │   │
│  │  ⚙️  Backend       - API development                │   │
│  │  🛡️  Guardian      - Testing & security            │   │
│  │  🚀 DevOps        - Deployment                    │   │
│  │  📈 Evolution     - Learning & patterns           │   │
│  │                                                     │   │
│  │  Shared Memory: /home/workspace/EliteSquad        │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Environment Variables

```bash
# Elite Squad endpoint (via Tailscale)
export ELITE_SQUAD_URL="http://100.127.121.51:4200"

# Kimi CLI identifier
export KIMI_ID="kimi-cli-35.235.249.249"

# Default budget
export ELITE_BUDGET="100"
```

## Use Cases

### 1. Deploy iHhashi

```bash
# Full deployment through Elite Squad
bun elite-bridge.ts deploy \
  https://github.com/youngstunners88/ihhashi \
  capacitor \
  200

# Watch progress
bun elite-bridge.ts watch
```

### 2. Tandem Development

```bash
# Terminal 1: Kimi CLI working on local code
vim src/components/Login.tsx

# Terminal 2: Elite Squad handling deployment
bun elite-bridge.ts watch &

# When ready to deploy
bun elite-bridge.ts deploy . capacitor 100
```

### 3. Parallel Work

```bash
# Kimi CLI: Work on complex algorithm
# Elite Squad: Handle frontend polish simultaneously

# Delegate frontend work
bun elite-bridge.ts message "Frontend: Improve mobile responsiveness"

# Continue working on backend
# Results sync automatically
```

## Troubleshooting

### Cannot Connect to Elite Squad

```bash
# Check if Zo Computer is reachable
ping 100.127.121.51

# Check Tailscale connection
tailscale status

# Verify OpenFang is running
curl http://100.127.121.51:4200/health
```

### Tasks Not Completing

```bash
# Force sync
bun elite-bridge.ts sync

# Check detailed status
bun elite-bridge.ts status

# View Elite Squad logs (on Zo Computer)
ssh zo-computer "tail -f /var/log/elite-squad.log"
```

## Best Practices

1. **Start with status**: Always check Elite Squad status before deploying
2. **Use watch mode**: Enable continuous sync for long-running tasks
3. **Set budgets**: Always specify budget to prevent runaway costs
4. **Sync regularly**: Check for completed tasks frequently
5. **Share context**: Use messages to share important context

## Advanced: Direct API Access

```typescript
// Direct fetch to Elite Squad
const response = await fetch("http://100.127.121.51:4200/api/elite/deploy", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-Kimi-ID": "kimi-cli-35.235.249.249"
  },
  body: JSON.stringify({
    repoUrl: "https://github.com/user/repo",
    track: "capacitor",
    budget: 100
  })
});
```

## Comparison: Solo vs Tandem

| Approach | Time | Quality | Cost |
|----------|------|---------|------|
| Kimi CLI Solo | 2-3 hours | Good | ~$5 |
| Elite Squad Solo | 1-2 hours | Excellent | ~$10 |
| **Tandem** | **30-60 min** | **Superior** | **~$8** |

**Tandem advantages:**
- Parallel work streams
- Specialized expertise
- Quality gates (Guardian)
- Automatic learning (Evolution)

---

**8 Agents. Two Systems. One Goal.** ⚡🦀🔗
