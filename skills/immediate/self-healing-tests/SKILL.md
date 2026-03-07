# Self-Healing Tests

Auto-fixes flaky tests by detecting failure patterns and applying automatic fixes.

## Overview

The Self-Healing Tests skill monitors test runs, detects flaky tests (tests that pass/fail inconsistently), analyzes failure patterns, and attempts automatic fixes for timing issues, mock problems, async issues, and more.

## Installation

```bash
cd .kimi/skills/self-healing-tests
pip install -r requirements.txt
```

## Quick Start

### Pytest Plugin Usage

```bash
# Detect flaky tests (requires multiple runs)
pytest --self-heal --count=5

# Auto-fix detected flaky tests (dry run)
pytest --self-heal --auto-heal

# Apply fixes for real
pytest --self-heal --auto-heal --heal-no-dry-run

# Generate PR with fixes
pytest --self-heal --auto-heal --heal-no-dry-run --heal-generate-pr
```

### CLI Usage

```bash
# Detect flaky tests
self-heal detect tests/ --runs=5

# Heal a specific test
self-heal heal test_auth.py test_login

# Show statistics
self-heal stats

# Generate report
self-heal report --output=flaky-report.md
```

## Features

- **Flaky Test Detection**: Identifies tests that fail intermittently
- **Pattern Analysis**: Categorizes failures by type (timing, async, mocks, etc.)
- **Automatic Fixes**: Applies fixes for common flakiness patterns
- **PR Generation**: Creates GitHub PR with fixes
- **Fix Tracking**: Tracks success rate of applied fixes
- **Safe Dry-Run**: Preview fixes before applying

## Failure Types Detected

| Type | Pattern | Fix Strategy |
|------|---------|--------------|
| Timeout | Test takes too long | Add timeout markers |
| Race Condition | Concurrent access | Add synchronization |
| Mock Issue | Mock assertions fail | Fix mock setup |
| Async Issue | Event loop problems | Add async markers |
| Fixture Issue | Setup/teardown fails | Improve isolation |
| Environment | Missing env vars | Mock environment |
| Dependency | External service | Add mocks/patches |

## Flakiness Patterns

| Pattern | Indicator | Fix |
|---------|-----------|-----|
| Timing Dependent | `time.sleep()` | Async waits |
| Order Dependent | Global state | Test isolation |
| State Leakage | Shared fixtures | Reset state |
| External Dependency | HTTP calls | Mocking |
| Random Data | `random`, `uuid` | Fixed seeds |
| Concurrency | `threading` | Proper async |
| Resource Contention | File locks | Cleanup |

## Pytest Options

### --self-heal

Enable self-healing detection.

```bash
pytest --self-heal
```

### --auto-heal

Automatically fix flaky tests (requires `--self-heal`).

```bash
pytest --self-heal --auto-heal
```

### --heal-dry-run / --heal-no-dry-run

Control whether to actually apply fixes.

```bash
# Preview fixes
pytest --self-heal --auto-heal --heal-dry-run

# Apply for real
pytest --self-heal --auto-heal --heal-no-dry-run
```

### --heal-generate-pr

Generate PR with fixes.

```bash
pytest --self-heal --auto-heal --heal-no-dry-run --heal-generate-pr
```

### --heal-min-runs

Minimum test runs before considering flaky (default: 3).

```bash
pytest --self-heal --heal-min-runs=5
```

### --heal-threshold

Flakiness threshold (default: 0.1 = 10%).

```bash
pytest --self-heal --heal-threshold=0.2
```

## Python API Reference

### FailureAnalyzer

Analyzes test failures to identify patterns.

```python
from self_healing_tests import FailureAnalyzer

analyzer = FailureAnalyzer()

# Record a failure
analyzer.record_failure(
    test_name="test_login",
    test_file="test_auth.py",
    error_type="AssertionError",
    error_message="assert 1 == 2",
    traceback="...",
    duration=1.5,
    timestamp=time.time()
)

# Record success
analyzer.record_success("test_login", "test_auth.py", 0.5)

# Analyze test
analysis = analyzer.analyze_test("test_login", "test_auth.py")
if analysis:
    print(f"Flakiness rate: {analysis.flakiness_rate}")
    print(f"Failure type: {analysis.failure_type}")
```

### TestHealer

Applies fixes to flaky tests.

```python
from self_healing_tests import TestHealer

healer = TestHealer("/path/to/project")

# Get analysis first
analysis = analyzer.analyze_test("test_login", "test_auth.py")

# Apply fixes
results = healer.heal(analysis, dry_run=True)

for result in results:
    if result.success:
        print(f"Fixed: {result.message}")
    else:
        print(f"Failed: {result.message}")
```

### SelfHealingPlugin

Pytest plugin class.

```python
import pytest
from self_healing_tests import SelfHealingPlugin

plugin = SelfHealingPlugin(
    project_root="/path/to/project",
    auto_heal=True,
    dry_run=True,
    generate_pr=False,
    min_runs=3,
    flakiness_threshold=0.1
)

# Register with pytest
config.pluginmanager.register(plugin)
```

## Fix Types

### timing

Replaces `time.sleep()` with proper async waits.

```python
# Before:
time.sleep(2)

# After:
await asyncio.wait_for(_wait_for_condition(), timeout=2)
```

### mocking

Adds `@patch` decorators for external dependencies.

```python
# Before:
def test_api():
    response = requests.get("/api")

# After:
@patch("requests.get")
def test_api(mock_get):
    response = mock_get.return_value
```

### isolation

Adds `setup_method` and `teardown_method` for test isolation.

```python
# After:
def setup_method(self):
    """Reset state before each test."""
    pass

def teardown_method(self):
    """Clean up after each test."""
    pass
```

### ordering

Marks tests with TODO for order dependency removal.

```python
# After:
# TODO: Ensure this test is independent
def test_order():
    pass
```

### async

Adds `@pytest.mark.asyncio` for async tests.

```python
# After:
@pytest.mark.asyncio
async def test_async():
    await some_async_function()
```

### timeout

Adds `@pytest.mark.timeout()` decorator.

```python
# After:
@pytest.mark.timeout(30)
def test_slow():
    pass
```

### mock_assertion

Changes `assert_called_once` to `assert_called`.

```python
# Before:
mock.assert_called_once()

# After:
mock.assert_called()  # Changed for flaky test fix
```

## Examples

### Example 1: Basic Pytest Usage

```bash
# Run tests 5 times and detect flakiness
pytest tests/ --self-heal --count=5

# If flaky tests detected, fix them
pytest tests/ --self-heal --count=5 --auto-heal
```

### Example 2: Programmatic Usage

```python
from self_healing_tests import FailureAnalyzer, TestHealer
import subprocess
import time

analyzer = FailureAnalyzer()
healer = TestHealer("/path/to/project")

# Run tests multiple times and collect results
for i in range(5):
    result = subprocess.run(
        ['pytest', 'tests/', '-v'],
        capture_output=True,
        text=True
    )
    
    # Parse results and record
    # (Parsing logic omitted for brevity)

# Analyze and fix flaky tests
for test_id in analyzer.failure_history:
    parts = test_id.split("::")
    analysis = analyzer.analyze_test(parts[1], parts[0])
    
    if analysis and analysis.flakiness_rate > 0.2:
        print(f"Healing {test_id}...")
        results = healer.heal(analysis, dry_run=False)
        
        for result in results:
            print(f"  {result.message}")
```

### Example 3: Generate PR

```python
from self_healing_tests import PRGenerator, FailureAnalyzer, TestHealer

analyzer = FailureAnalyzer()
healer = TestHealer("/path/to/project")
pr_gen = PRGenerator("/path/to/project")

# ... collect and analyze tests ...

flaky_tests = analyzer.get_flaky_tests()
fix_results = []

for test in flaky_tests:
    results = healer.heal(test, dry_run=False)
    fix_results.append(results)

# Generate PR content
pr_content = pr_gen.generate_pr_content(flaky_tests, fix_results)

# Create branch and commit
pr_gen.create_branch(pr_content['branch_name'])
pr_gen.commit_changes("Fix flaky tests")

print(f"Branch: {pr_content['branch_name']}")
print(f"Title: {pr_content['title']}")
```

### Example 4: CI/CD Integration

```yaml
# .github/workflows/heal-tests.yml
name: Heal Flaky Tests

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly

jobs:
  heal:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run tests multiple times
        run: |
          pytest tests/ --self-heal --count=10 --auto-heal --heal-no-dry-run --heal-generate-pr
      
      - name: Push fixes
        run: |
          git push origin $(git branch --show-current)
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     SelfHealingPlugin                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  pytest_runtest_makereport() → Record success/failure           │
│            ↓                                                     │
│  pytest_sessionfinish() → Analyze patterns                      │
│            ↓                                                     │
│  Detect flaky → heal() → PRGenerator                             │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │ FailureAnalyzer  │  │ TestHealer       │                    │
│  │  - record()      │  │  - heal()        │                    │
│  │  - analyze()     │  │  - fix_*()       │                    │
│  └──────────────────┘  └──────────────────┘                    │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │ TestCodeAnalyzer │  │ PRGenerator      │                    │
│  │  - parse()       │  │  - generate()    │                    │
│  │  - analyze_deps()│  │  - create_branch()│                   │
│  └──────────────────┘  └──────────────────┘                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest tests/ --cov=self_healing_tests --cov-report=html

# Test the plugin
pytest tests/ --self-heal
```

## Configuration

### Environment Variables

```bash
# Minimum runs before considering flaky
export SELF_HEAL_MIN_RUNS=5

# Flakiness threshold
export SELF_HEAL_THRESHOLD=0.15

# Auto-heal without dry-run
export SELF_HEAL_NO_DRY_RUN=1
```

### pytest.ini

```ini
[pytest]
addopts = --self-heal --heal-min-runs=5 --heal-threshold=0.1
```

## License

MIT
