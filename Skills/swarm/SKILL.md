---
name: swarm
description: Autonomous agent swarm for high-volume task execution
metadata:
  author: youngstunners.zo.computer
---

## When to use this skill
- Run thousands of parallel tasks
- Coordinate multiple agent workers
- Execute batch operations at scale
- Build production pipelines

## When NOT to use this skill
- For small single tasks (do it directly)
- For sequential workflows (use normal tool calls)
- For simple searches (use web_search)
- For file operations (use read_file/edit_file)

## Inputs
- `task_type`: build, test, deploy, research
- `count`: Number of parallel agents
- `description`: What to accomplish

## Outputs
- Multiple completed tasks
- Aggregated results
- Performance metrics

## Usage
```bash
# Uses ao (agent-orchestrator) for parallel execution
# Uses antfarm for multi-agent dev workflows
# Coordinates via API calls to zo/ask endpoint
```

## Integration
- Combines: ao CLI + antfarm + zo/ask API
- Max concurrency: ~20 parallel requests
- For larger scale, process in batches

## Negative examples
- Don't use for: one-off tasks (just do it)
- Don't use for: simple queries (use web_search)
- Don't use for: single file edits (use edit_file_llm)