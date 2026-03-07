---
name: antfarm
description: Multi-agent development workflow orchestrator for software teams
metadata:
  author: youngstunners.zo.computer
---

## When to use this skill
- Run multi-agent development workflows (feature-dev, bug-fix, security-audit)
- Coordinate multiple AI agents working on same codebase
- Automate code review and testing
- Handle CI/CD pipeline tasks

## When NOT to use this skill
- For single-agent tasks (just do it directly)
- For simple file operations (use read_file/edit_file)
- For web searches (use web_search)
- When you need real-time interaction (use terminal directly)

## Inputs
- `workflow`: feature-dev, bug-fix, security-audit
- `task`: Description of what to build/fix
- `project_path`: Path to the codebase

## Outputs
- Generated code files
- PR descriptions
- Test results

## Usage
```bash
cd /path/to/project
antfarm workflow run feature-dev "Add user authentication"
antfarm workflow run bug-fix "Fix login redirect"
antfarm workflow run security-audit
```

## Negative examples
- Don't use for: one-off code edits (use edit_file_llm directly)
- Don't use for: reading files (use read_file)
- Don't use for: deploying sites (use publish_site or update_space_route)