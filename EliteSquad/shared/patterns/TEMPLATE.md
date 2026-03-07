# Pattern Template
## Use this format for all extracted patterns

```yaml
pattern_id: "[category]-[name]-v[version]"
extracted_date: ISO8601
source_deployment: "uuid"
extracted_by: "Evolution"

# Context
context: "When to use this pattern"
problem: "What problem it solves"
solution: "How it solves it"
tradeoffs: "What you give up"

# Implementation
code_example: |
  ```typescript
  // Working example
  ```
tests: |
  ```typescript
  // Test coverage
  ```

# Metadata
success_rate: 0.0-1.0
usage_count: integer
last_used: ISO8601
tags: [list]

# Agents that should know this
relevant_to: [frontend, backend, architect]
```

---
*Patterns are the squad's collective wisdom*
