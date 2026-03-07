---
name: context-audit
description: Audit all context files loaded each message (AGENTS.md, TOOLS.md, USER.md, MEMORY.md, HEARTBEAT.md, SOUL.md) to identify: (1) what should be a skill instead, (2) what's outdated/redundant, (3) what's verbose. Output current size, projected size, and token savings.
metadata:
  author: youngstunners.zo.computer
---

# Context Audit Skill

## Purpose
Audit every file that loads into context each message to optimize token usage and reduce always-loaded context bloat.

## Context Files to Audit
- AGENTS.md - Workspace instructions and memory
- TOOLS.md - Tool definitions and rules
- USER.md - User preferences and profile
- MEMORY.md - Session memory
- HEARTBEAT.md - Background task state
- SOUL.md - Agent personality

## Audit Criteria

### 1. What Should Be a Skill?
Identify content that:
- Is a reusable procedure (not one-off instructions)
- Has clear inputs/outputs
- Could be invoked conditionally
- Contains multi-step workflows

### 2. What's Outdated or Redundant?
- Old instructions that no longer apply
- Duplicate info across files
- Deprecated workflows
- Fixed issues that still have "TODO" markers

### 3. What's Verbose?
- Long explanations where short would do
- Repeated examples
- Over-detailed edge cases
- Redundant disclaimers

## Output Format
```
FILE: 
Current size: <X> tokens
Issues: <list>
Projected: <Y> tokens
Savings: <X-Y> tokens (<%> reduction)
```

## Action Items
For each issue found:
1. Move to skill if procedural
2. Delete if outdated
3. Condense if verbose
4. Create cleanup script