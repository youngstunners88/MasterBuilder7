---
name: memory-sync
description: Cross-Zo memory synchronisation. Keeps shared memory consistent across youngstunners, kofi, and Kimi CLI.
trigger: "When user asks to sync memory, share context, or update shared state"
metadata:
  author: youngstunners.zo.computer
  version: 1.0.0
---

# Memory Sync Skill

Synchronises shared memory across the 3-Zo network.

## Memory Structure

```
shared/
├── memory/
│   ├── deployment-history.md
│   ├── budget-tracker.md
│   ├── system-health.md
│   ├── agent-activity-log.md
│   └── agents/
│       ├── captain-state.md
│       ├── meta-router-state.md
│       └── ... (8 agents)
└── patterns/
    └── TEMPLATE.md
```

## Usage

```bash
# Full sync to all nodes
bun /home/workspace/Skills/memory-sync/scripts/sync.ts push

# Pull from a specific node
bun /home/workspace/Skills/memory-sync/scripts/sync.ts pull kofi

# Watch for changes (daemon)
bun /home/workspace/Skills/memory-sync/scripts/sync.ts watch

# Show sync status
bun /home/workspace/Skills/memory-sync/scripts/sync.ts status
```

## Sync Rules

| File Type | Direction | Conflict Resolution |
|-----------|-----------|---------------------|
| deployment-history.md | Append-only | Merge both |
| budget-tracker.md | Latest wins | Compare timestamps |
| agent-state.md | Owner writes | Agent owns its state |
| system-health.md | Broadcast | All nodes update |

## Locking

Uses optimistic locking with timestamps:
- Each update includes `lastModified` timestamp
- Conflicts resolved by latest timestamp
- Critical sections use advisory locks

---

*Memory Sync: One mind, many bodies*
