---
name: agent-orchestrator
description: Parallel AI coding agents with GitHub integration (ao CLI)
metadata:
  author: youngstunners.zo.computer
---

## When to use this skill
- Spawn multiple AI agents in parallel for speed
- Coordinate agents on different tasks simultaneously
- Auto-handle CI failures and PR reviews
- Connect with GitHub for issue/PR management

## When NOT to use this skill
- For single sequential tasks (just do it yourself)
- For file operations (use read_file/edit_file)
- For deploying (use register_user_service or update_space_route)
- When you need simple CLI commands (use run_bash_command)

## Inputs
- `project`: Project name or path
- `issue`: Task/issue description
- `command`: init, start, spawn, status

## Outputs
- Agent sessions running in parallel
- PRs created on GitHub
- CI results

## Usage
```bash
cd /path/to/project
ao init --auto
ao start
ao spawn myproject "Fix the login bug"
```

## Negative examples
- Don't use for: simple one-line commands (use run_bash_command)
- Don't use for: single file edits (use edit_file_llm)
- Don't use for: website deployments (use update_space_route)