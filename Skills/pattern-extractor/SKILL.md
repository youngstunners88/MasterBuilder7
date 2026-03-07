---
name: pattern-extractor
description: Extracts patterns from codebases automatically. Identifies code patterns, architecture patterns, and anti-patterns.
trigger: "When user asks to extract patterns, learn from code, or analyze codebase patterns"
metadata:
  author: youngstunners.zo.computer
  version: 1.0.0
---

# Pattern Extractor Skill

Automatically extracts and codifies patterns from codebases.

## Pattern Types

| Type | Description | Example |
|------|-------------|---------|
| **Code** | Reusable code snippets | Error handling patterns |
| **Architecture** | System design patterns | Microservice patterns |
| **Process** | Workflow patterns | CI/CD patterns |
| **Anti-pattern** | What to avoid | God objects, circular deps |

## Usage

```bash
# Extract patterns from a project
bun /home/workspace/Skills/pattern-extractor/scripts/extract.ts analyze <project-path>

# Extract specific pattern type
bun /home/workspace/Skills/pattern-extractor/scripts/extract.ts code <project-path>
bun /home/workspace/Skills/pattern-extractor/scripts/extract.ts architecture <project-path>

# Find anti-patterns
bun /home/workspace/Skills/pattern-extractor/scripts/extract.ts anti-patterns <project-path>

# Export patterns to knowledge base
bun /home/workspace/Skills/pattern-extractor/scripts/extract.ts export <project-path> <output-dir>
```

## Output

```json
{
  "project": "EliteSquad",
  "patterns": [
    {
      "type": "code",
      "name": "Agent SOUL Loader",
      "description": "Loads agent identity from SOUL.md",
      "occurrences": 8,
      "files": ["captain/...", "backend/..."],
      "template": "..."
    }
  ],
  "antiPatterns": [
    {
      "type": "anti-pattern",
      "name": "Missing Error Handling",
      "description": "Async functions without try-catch",
      "severity": "medium",
      "files": ["..."]
    }
  ]
}
```

## Integration

- Feeds into Evolution agent's knowledge base
- Updates `shared/patterns/` directory
- Triggers alerts for critical anti-patterns

---

*Pattern Extractor: Learn from everything*
