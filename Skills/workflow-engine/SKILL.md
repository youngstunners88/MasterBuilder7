---
name: workflow-engine
description: Implement the AI workflow rules from the workflow orchestration system
metadata:
  author: youngstunners.zo.computer
  source: workflow-rules- attachment

## Principles
- Simplicity First
- No Laziness  
- Minimal Impact

## Workflow Orchestration
1. **Plan Node Default** - Always plan before executing
2. **Subagent Strategy** - Split complex tasks to parallel agents
3. **Swarm Strategy** - Coordinate multiple agents for scale
4. **Sequential Strategy** - Chain tasks that depend on each other

## Task Management
1. **Plan First** - Always create a plan before code
2. **Execute Next** - Then execute the plan
3. **Capture Lessons** - Document what worked/didn't
4. **Iterate** - Improve based on results
5. **Verify** - Test the output
6. **Ship** - Deploy when ready

## Usage
```bash
# Run workflow
workflow-engine plan "build english learning game"
workflow-engine execute
workflow-engine verify
```

## Implementation
- Use edit_file_llm for text changes
- Use update_space_route for web apps
- Use run_bash_command for terminal tasks
- Use grep_search before modifying files
- Always create_or_rewrite_file new files, edit_file_llm existing