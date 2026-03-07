# MasterBuilder7 Test Suite

Comprehensive test suite for MasterBuilder7 with 90%+ code coverage target.

## Structure

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── __init__.py                    # Test package init
├── pytest.ini                     # Pytest configuration
├── requirements-test.txt          # Test dependencies
├── README.md                      # This file
├── test_agent_protocol.py         # Agent messaging tests
├── test_shared_state.py           # State management tests
├── test_task_queue.py             # Task scheduling tests
├── test_health_monitor.py         # Health check tests
├── test_cost_tracker.py           # Cost tracking tests
├── test_mcp_server.py             # MCP endpoint tests
├── test_integration.py            # End-to-end integration tests
├── test_load.py                   # Load/performance tests
└── fixtures/                      # Test data files
    ├── __init__.py
    ├── sample_agents.json
    ├── sample_tasks.json
    └── sample_cost_data.json
```

## Running Tests

### Run All Tests
```bash
cd /home/teacherchris37/MasterBuilder7
python -m pytest tests/ -v
```

### Run Specific Test Files
```bash
# Unit tests only
pytest tests/test_agent_protocol.py tests/test_shared_state.py -v

# Integration tests
pytest tests/test_integration.py -v

# Load tests
pytest tests/test_load.py -v
```

### Run with Markers
```bash
# Exclude slow tests
pytest tests/ -m "not slow"

# Only integration tests
pytest tests/ -m integration

# Only load tests
pytest tests/ -m load
```

### Run with Coverage
```bash
# Generate coverage report
pytest tests/ --cov=apex --cov-report=html --cov-report=term-missing

# Coverage with minimum threshold
pytest tests/ --cov=apex --cov-fail-under=90
```

### Run in Parallel
```bash
# Run tests in parallel (requires pytest-xdist)
pytest tests/ -n auto
```

## Test Categories

### Unit Tests (`test_*.py`)
- Fast execution (< 1 second each)
- No external dependencies (SQLite only)
- Test individual components in isolation

### Integration Tests (`test_integration.py`)
- Test component interactions
- Slower execution (1-5 seconds each)
- Use `@pytest.mark.integration` marker

### Load Tests (`test_load.py`)
- Performance and scalability testing
- Test with 64+ concurrent agents
- Use `@pytest.mark.load` and `@pytest.mark.slow` markers
- May take several minutes to complete

## Fixtures

### Core Fixtures (conftest.py)
- `temp_db_path`: Temporary database file
- `temp_directory`: Temporary directory
- `sample_agent_config`: Sample agent configuration
- `sample_task_payload`: Sample task payload
- `agent_bus`: Connected AgentBus instance
- `shared_state_manager`: SharedStateManager instance
- `task_queue`: TaskQueue instance
- `health_monitor`: HealthMonitor instance
- `cost_tracker`: CostTracker instance
- `integrated_system`: Full system with all components

### Usage Example
```python
import pytest

async def test_example(agent_bus, sample_task_payload):
    # Use fixtures in tests
    await agent_bus.send_direct(
        sender="test",
        recipient="test",
        payload=sample_task_payload
    )
```

## Coverage Goals

| Component | Target Coverage |
|-----------|----------------|
| Agent Protocol | 95% |
| Shared State | 92% |
| Task Queue | 93% |
| Health Monitor | 90% |
| Cost Tracker | 91% |
| MCP Server | 88% |
| **Overall** | **90%+** |

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r tests/requirements-test.txt
      - name: Run tests with coverage
        run: |
          pytest tests/ --cov=apex --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Writing New Tests

### Test Structure
```python
import pytest

class TestMyFeature:
    """Test docstring describing what is being tested."""
    
    async def test_specific_behavior(self, fixture1, fixture2):
        """Test docstring describing the specific behavior."""
        # Arrange
        input_data = {...}
        
        # Act
        result = await my_function(input_data)
        
        # Assert
        assert result.expected_value == actual_value
```

### Best Practices
1. Use descriptive test names
2. One assertion per test (when possible)
3. Use fixtures for common setup
4. Clean up after tests (use temp paths)
5. Mark slow tests with `@pytest.mark.slow`
6. Mark integration tests with `@pytest.mark.integration`

## Troubleshooting

### Common Issues

**Import Errors**
- Ensure you're running from the project root
- Check that `apex/` is in your Python path

**Database Lock Errors**
- Tests use temporary databases that are cleaned up
- If tests are interrupted, manually clean `/tmp/masterbuilder7_test/`

**Async Test Failures**
- Ensure `pytest-asyncio` is installed
- Use `async def` for async tests
- Use `await` for async calls

### Debug Mode
```bash
# Run with verbose output and no capture
pytest tests/test_specific.py -v -s

# Run single test with pdb on failure
pytest tests/test_specific.py::TestClass::test_method -v --pdb
```

## License

Same as MasterBuilder7 project.
