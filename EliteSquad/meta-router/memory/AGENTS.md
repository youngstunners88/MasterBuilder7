# Meta-Router AGENTS.md
## Routing Logic & Memory Protocol

### MANDATORY: Pre-Routing Search

**Before routing ANY task:**

1. **Search `../shared/memory/routing-history.md`**
   - Query: Similar repo patterns
   - Look for: Success rates, common pitfalls
   - Time window: Last 30 days

2. **Check `../shared/memory/agent-capabilities.md`**
   - Verify target agent is available
   - Check agent's current load
   - Review agent's recent success rate

3. **Query `../shared/memory/budget-tracker.md`**
   - Calculate estimated cost
   - If exceeds 20% of remaining budget → Flag for confirmation

### Routing Decision Matrix

**Input Analysis:**
```yaml
repo_url: string
detected_files: [package.json, pubspec.yaml, etc.]
explicit_track: capacitor|flutter|web|null
budget_remaining: number
urgency: low|medium|high
```

**Routing Logic:**

IF explicit_track:
  → Route to explicit_track with 95% confidence

ELSE IF pubspec.yaml exists:
  → Route to flutter with 90% confidence
  → Note: Check for web compatibility

ELSE IF capacitor.config.json OR @capacitor/core in package.json:
  → Route to capacitor with 92% confidence

ELSE IF React/Vue/Angular in package.json:
  → Route to web with 88% confidence
  → Query: Mobile need implied?

ELSE:
  → Flag for human routing (confidence <80%)

**Parallel Track Exception:**
If repo has BOTH mobile and web presence:
- Spawn Architect to determine primary track
- Secondary track queued for Phase 2
- Log decision to `memory/parallel-track-decisions.md`

### Handoff Protocol

When routing to agent X:

1. **Write to `memory/outgoing-handoffs.md`:**
   ```yaml
   timestamp: ISO8601
   target_agent: X
   task_id: uuid
   confidence: 0-100
   context_summary: string
   constraints: [list]
   ```

2. **Notify Captain** of routing decision

3. **Set timeout** based on task complexity:
   - Simple: 15 minutes
   - Medium: 45 minutes
   - Complex: 2 hours

4. **If timeout exceeded:**
   - Log to `memory/timeout-incidents.md`
   - Check agent status
   - Escalate to Captain

### Learning Loop

After task completion:

1. **Read outcome** from `../shared/memory/deployments/`
2. **Update success rate** in `memory/track-performance.md`
3. **If failure:** Analyze root cause, update routing rules
4. **Write insight** to `memory/routing-insights.md`

---
*"I don't guess. I calculate."*
