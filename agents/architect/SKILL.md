# Architect Agent

GitHub-based system design and code review agent.

## Overview

**Platform**: GitHub Actions
**Status**: Beta
**Trigger**: PR labels, Issue labels

## Features

- Design reviews
- Tech spec generation
- Code review
- Security audit
- Documentation updates

## Triggers

| Label | Action |
|-------|--------|
| `needs-design-review` | Architecture review |
| `tech-spec-needed` | Generate tech spec |
| `security-critical` | Security review |
| `documentation` | Update docs |

## Configuration

```yaml
architect:
  github_token: ${GITHUB_TOKEN}
  openai_key: ${OPENAI_API_KEY}
  rules:
    - require_tests
    - max_complexity: 10
    - require_docstrings
```

## Workflow

1. PR created with label
2. Agent analyzes changes
3. Posts review comments
4. Updates documentation on merge
