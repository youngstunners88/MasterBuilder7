# Implementer Agent

Kimi CLI agent for code generation and implementation.

## Overview

**Platform**: Kimi CLI
**Status**: Production Ready
**Input**: GitHub Issues, CLI commands

## Features

- Feature implementation
- Bug fixes
- Refactoring
- Test generation
- Documentation

## Usage

```bash
# From issue
kimi --agent implementer --issue 123

# From task
kimi --agent implementer --task "implement refund system"

# With skill
kimi --agent implementer --skill quantum --task "extract menu"
```

## Workflow

1. Read requirements
2. Analyze existing code
3. Implement solution
4. Add tests
5. Update docs
6. Create PR

## Configuration

```yaml
implementer:
  default_branch: main
  test_coverage: 80
  commit_style: conventional
```
