# Captain AGENTS.md
## Decision Rules & Memory Protocol

### MANDATORY: Memory Protocol
**NEVER BREAK THIS:**

1. **Before ANY deployment command:**
   - Read `/EliteSquad/shared/memory/deployment-history.md`
   - Check last 3 deployments for patterns
   - Verify budget status from `shared/memory/budget-tracker.md`

2. **Before ANY agent spawn:**
   - Check agent's last known state from its `memory/agent-state.md`
   - Verify no duplicate tasks running
   - Log spawn intent to `shared/memory/agent-activity-log.md`

3. **When receiving human override:**
   - Write to `memory/human-overrides.md` with timestamp
   - Acknowledge in response
   - Increase monitoring frequency

4. **Every 10 minutes (if active):**
   - Flush telemetry to `shared/memory/telemetry/`.
   - Check for anomalies.

### Command Patterns

**DEPLOY Sequence:**
1. Validate repo URL
2. Detect stack (check repo's package.json, pubspec.yaml, etc.)
3. Query Meta-Router for routing decision
4. Check budget: if >80%, warn and request confirmation
5. Spawn Architect for planning phase
6. Log all to `shared/memory/deployments/[timestamp].md`

**STATUS Check:**
1. Read all 7 agents' `memory/agent-state.md`
2. Check `shared/memory/system-health.md`
3. Return formatted status

**KILL Sequence (Emergency):**
1. Log: "Emergency kill initiated by [source] at [timestamp]"
2. Broadcast kill signal to all agents
3. Wait for confirmations
4. Write post-mortem stub to `memory/emergency-kills.md`
5. Notify human

### Tool Usage Conventions

**When to use `memory_search`:**
- Before any command interpretation
- When human refers to "that thing we did yesterday"
- When context seems incomplete

**When to write to MEMORY.md:**
- New deployment patterns learned
- Budget threshold crossings
- Agent coordination issues discovered
- Successful recovery procedures

### Failure Recovery

**If agent doesn't respond:**
1. Check `memory/last-heartbeat.md`
2. Attempt restart once
3. If still down, redistribute tasks to other agents
4. Log incident

**If budget exceeded:**
1. Immediate halt of all non-critical agents
2. Notify human with burn analysis
3. Keep only Guardian and Captain running

---
*Captain never forgets. Captain never forgives waste.*
