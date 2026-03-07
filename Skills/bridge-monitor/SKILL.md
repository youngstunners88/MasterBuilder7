---
name: bridge-monitor
description: Real-time 3-Zo network health monitoring. Monitors youngstunners, kofi, and Kimi CLI connections with alerts.
trigger: "When user asks about network status, bridge health, or connection status"
metadata:
  author: youngstunners.zo.computer
  version: 1.0.0
---

# Bridge Monitor Skill

Real-time monitoring for the 3-Zo network (youngstunners ↔ kofi ↔ Kimi CLI).

## Nodes

| Node | Endpoint | Role |
|------|----------|------|
| **youngstunners** | https://youngstunners.zo.space/api/elite-bridge | Coordinator |
| **kofi** | https://kofi.zo.space/api/kimi-bridge | Review/Deploy |
| **Kimi CLI** | http://35.235.249.249:4200/api/v1/health | Builder |

## Usage

```bash
# Check all nodes
bun /home/workspace/Skills/bridge-monitor/scripts/monitor.ts check

# Continuous monitoring (daemon)
bun /home/workspace/Skills/bridge-monitor/scripts/monitor.ts daemon

# Get detailed status
bun /home/workspace/Skills/bridge-monitor/scripts/monitor.ts status

# Send heartbeat to all nodes
bun /home/workspace/Skills/bridge-monitor/scripts/monitor.ts heartbeat
```

## Health Checks

- **HTTP Status**: Is the endpoint responding?
- **Latency**: Response time in ms
- **Bridge State**: Are messages flowing?
- **Agent Count**: How many agents active?

## Alerting

Automatic alerts when:
- Node goes offline (3 consecutive failures)
- Latency > 5000ms
- Bridge queue > 100 pending messages
- Memory/CPU threshold exceeded

## Output

```
═══════════════════════════════════════════════════════════
🌉 BRIDGE NETWORK STATUS - 2026-03-07T17:40:00Z
═══════════════════════════════════════════════════════════

  NODE            STATUS    LATENCY    AGENTS    MESSAGES
  ────────────── ───────── ────────── ───────── ──────────
  youngstunners   ✅ ONLINE    45ms       8         0
  kofi            ✅ ONLINE   120ms       8        15
  kimi-cli        ❌ OFFLINE    --        --        --

  NETWORK HEALTH: 66% (2/3 nodes)
```

## Integration

Used by:
- EliteSquad deployment pipeline
- Memory sync operations
- Agent coordination

---

*Bridge Monitor: Keeping the network alive*
