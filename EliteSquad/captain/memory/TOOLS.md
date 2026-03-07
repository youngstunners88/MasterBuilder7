# Captain TOOLS.md
## MCP Tool Usage Conventions

### Primary Tools

**memory_search**
- Use: Before every command, search for relevant past deployments
- Query: `{ "query": "deployment pattern [stack]", "limit": 5 }`
- Store results: Brief note in working context

**file_read / file_write**
- Use: Reading/writing shared memory files
- Convention: Always append, never overwrite history
- Critical files: `../shared/memory/budget-tracker.md`, `deployment-history.md`

**bash / shell**
- Use: System commands, git operations
- Restriction: Never run without logging intent to memory first
- Audit: All commands logged to `memory/shell-commands.md`

**web_search / web_fetch**
- Use: External verification, documentation lookup
- Cache: Save relevant findings to `memory/research-cache.md`

### Secondary Tools (via MCP Party)

**Kimi VM Integration**
- Trigger: Complex reasoning tasks
- Handoff: Send context + request, await response
- Store: Kimi's reasoning to `memory/kimi-consultations.md`

**Claude Code MCP**
- Trigger: Code generation, refactoring
- Handoff: Clear spec + constraints, review output
- Store: Generated code patterns to `memory/code-patterns.md`

**Supabase MCP**
- Trigger: Database operations, schema changes
- Pre-check: Read current schema from `memory/db-schema.md`
- Post-action: Update schema file immediately

**Code Wiki MCP**
- Trigger: Need codebase understanding
- Query: Specific component or pattern
- Store: Learned patterns to `memory/codebase-patterns.md`

### Tool Orchestration Rules

**Parallel Execution:**
- Spawn up to 3 agents simultaneously
- Each with isolated memory context
- Merge results via Captain coordination

**Sequential Dependency:**
- Architect → Frontend/Backend → Guardian → DevOps
- Each stage gates the next
- Checkpoint written between each

**Never Do:**
- Use tool without search first
- Execute destructive command without confirmation log
- Spawn agents without budget check

---
*Tools are extensions of memory. Use them wisely.*
