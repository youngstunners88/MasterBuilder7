# EliteSquad Shared Memory

This directory contains the shared memory for all 8 agents.

## Structure

```
memory/
├── deployment-history.md    # All deployments
├── budget-tracker.md        # Budget usage
├── system-health.md         # System status
├── agent-activity-log.md    # Agent actions
├── deployments/             # Per-deployment details
├── agents/                  # Per-agent state
└── telemetry/               # Metrics and logs
```

## Memory Protocol

All agents MUST:
1. Read relevant memory before any operation
2. Write results after completion
3. Append to logs (never overwrite)
4. Respect shared locks

## Current State

- **Status:** Initialized
- **Last Updated:** 2026-03-07
- **Active Agents:** 8
