---
name: elite-sweep
description: Automated code audit & fix engine. Scans codebases for bugs, missing files, type errors, and auto-fixes with verification.
trigger: "When user asks to audit, sweep, fix bugs, or check code quality"
metadata:
  author: youngstunners.zo.computer
  version: 1.0.0
---

# Elite Sweep Skill

Automated code quality engine for deep audits and fixes.

## Capabilities

- **Bug Detection**: Finds runtime errors, type mismatches, null references
- **Missing File Detection**: Identifies imports that don't resolve
- **Type Audit**: TypeScript type coverage analysis
- **Auto-Fix**: Applies safe fixes automatically
- **Verification**: Runs tests after fixes to ensure correctness

## Usage

```bash
# Full audit
bun /home/workspace/Skills/elite-sweep/scripts/sweep.ts audit /path/to/project

# Quick scan (just errors)
bun /home/workspace/Skills/elite-sweep/scripts/sweep.ts scan /path/to/project

# Auto-fix mode
bun /home/workspace/Skills/elite-sweep/scripts/sweep.ts fix /path/to/project

# Generate report
bun /home/workspace/Skills/elite-sweep/scripts/sweep.ts report /path/to/project
```

## Audit Categories

| Category | Checks |
|----------|--------|
| **Imports** | Missing files, circular dependencies |
| **Types** | Any types, missing generics, type assertions |
| **Runtime** | Null/undefined access, unhandled promises |
| **Security** | Hardcoded secrets, SQL injection risks |
| **Structure** | Missing package.json, tsconfig.json |

## Output Format

```json
{
  "project": "path/to/project",
  "timestamp": "ISO-8601",
  "summary": {
    "totalIssues": 0,
    "critical": 0,
    "warnings": 0,
    "fixed": 0
  },
  "issues": [...],
  "recommendations": [...]
}
```

## Integration

Called automatically when:
- User says "audit this code"
- User says "sweep for bugs"
- User says "fix all issues"
- Before any deployment (optional)

---

*Elite Sweep: Zero tolerance for bugs*
