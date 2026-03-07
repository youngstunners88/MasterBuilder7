---
name: orchestrate-agents
description: |
  Coordinate multiple AI agents for parallel task execution.
  
  Use when:
  - User wants to build many games simultaneously
  - User mentions "swarm" or "multiple agents"
  - User wants to scale production
  - Task can be parallelized
  
  Don't use when:
  - Single sequential task (just do it)
  - Tasks have dependencies (do sequentially)

inputs:
  task_type: build|research|test|deploy
  count: number_of_agents
  project: target_project

tools:
  - ao (Agent Orchestrator CLI)
  - run_bash_command
  - update_space_route

output: Multiple completed tasks in parallel

examples:
  - "Build 5 games at once" → spawn 5 agents
  - "Test all games" → parallel test execution
  
negative_examples:
  - "Fix one bug" → do directly, no need for orchestration