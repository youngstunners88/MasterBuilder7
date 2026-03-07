# Test Engineer Agent

Automated test generation and execution.

## Overview

**Platform**: Testing Framework
**Status**: Beta
**Languages**: Python, TypeScript

## Test Types

| Type | Framework | Target |
|------|-----------|--------|
| Unit | pytest | 80% coverage |
| Integration | pytest | All endpoints |
| E2E | Playwright | Critical paths |
| Load | Locust | Key APIs |
| Contract | Pact | All APIs |

## Usage

```bash
# Generate tests for changes
kimi --agent test-engineer --generate

# Run all tests
kimi --agent test-engineer --run

# Check coverage
kimi --agent test-engineer --coverage
```

## Configuration

```yaml
test:
  coverage_target: 80
  browsers: [chromium, firefox]
  load_users: 1000
```
