# Skill 8: Performance Prophet

Predicts bottlenecks before deployment and suggests optimizations.

## Overview

The Performance Prophet analyzes code performance, database queries, and predicts scaling bottlenecks before they impact production. It provides:

- CPU and memory profiling
- Database query analysis (N+1 detection)
- Bottleneck prediction at various load levels
- Automated optimization suggestions
- Load test scenario generation

## Features

- 📊 **Code Profiling** - cProfile integration with visualizations
- 🔍 **Query Analysis** - Detect N+1, missing indexes, anti-patterns
- 🔮 **Bottleneck Prediction** - ML-based scaling predictions
- ⚡ **Auto-Optimizations** - Suggested code improvements
- 🧪 **Load Test Generation** - Locust test scenarios

## Installation

```bash
cd skill8-performance-prophet
pip install -r requirements.txt
```

## Quick Start

```python
from src.profiler import Profiler
from src.query_analyzer import QueryAnalyzer
from src.predictor import BottleneckPredictor
from src.optimizer import Optimizer

# Profile code
profiler = Profiler()
result, output = profiler.profile_function(your_function, arg1, arg2)
profiler.display_results(result)

# Analyze queries
analyzer = QueryAnalyzer()
issues = analyzer.analyze_directory("./src", pattern="**/*.py")
analyzer.display_issues()

# Predict bottlenecks
predictor = BottleneckPredictor()
predictions = predictor.predict_bottlenecks(result, target_loads=[100, 500, 1000])
predictor.display_predictions(predictions)

# Get optimization suggestions
optimizer = Optimizer()
plan = optimizer.generate_optimization_plan(result, issues)
optimizer.display_suggestions()
```

## Core Components

### Profiler

CPU and memory profiling using cProfile.

```python
from src.profiler import Profiler

profiler = Profiler()

# Profile a function
result, output = profiler.profile_function(your_expensive_function, arg1, arg2)

# Profile with decorator
@profiler.profile_with_decorator(memory=True)
def my_function():
    pass

# Profile entire module
result = profiler.profile_module("mymodule", run_func="main")

# Profile script
result = profiler.profile_script("script.py")

# Continuous profiling
profiler.start_continuous()
# ... run your code ...
result = profiler.stop_continuous()

# Display results
profiler.display_results(result)

# Export for visualization
profiler.export_to_pstats("profile.prof")
# Then run: snakeviz profile.prof
```

### QueryAnalyzer

Detect database query issues.

```python
from src.query_analyzer import QueryAnalyzer, QueryIssueType

analyzer = QueryAnalyzer()

# Analyze a file
issues = analyzer.analyze_code("models.py")

# Analyze entire directory
issues = analyzer.analyze_directory("./src", pattern="**/*.py")

# Analyze raw SQL
issues = analyzer.analyze_sql("SELECT * FROM users")

# Get summary
summary = analyzer.get_summary()
print(f"Total issues: {summary['total_issues']}")
print(f"Critical: {summary['critical_issues']}")

# Display
analyzer.display_issues()
analyzer.display_issues(severity_filter="critical")

# Index recommendations
recommendations = analyzer.generate_index_recommendations()
```

### BottleneckPredictor

Predict performance at scale.

```python
from src.predictor import BottleneckPredictor, ScalingPrediction

predictor = BottleneckPredictor()

# Add historical data
predictor.add_historical_data(previous_profile)

# Predict bottlenecks
predictions = predictor.predict_bottlenecks(
    current_profile,
    target_loads=[100, 500, 1000, 5000, 10000]
)

# Predict database bottlenecks
db_predictions = predictor.predict_database_bottlenecks(
    query_issues,
    user_growth=[100, 1000, 10000]
)

# Display
predictor.display_predictions(predictions)

# Generate load test scenarios
scenarios = predictor.generate_load_test_scenarios(
    current_profile,
    predictions
)

# Save predictions
predictor.save_predictions(
    "predictions.json",
    predictions,
    db_predictions
)
```

### Optimizer

Generate optimization suggestions.

```python
from src.optimizer import Optimizer, OptimizationType

optimizer = Optimizer()

# Analyze profile
suggestions = optimizer.analyze_profile(profile_result)

# Analyze queries
suggestions = optimizer.analyze_queries(query_issues)

# Generate comprehensive plan
plan = optimizer.generate_optimization_plan(
    profile_result,
    query_issues
)

# Display suggestions
optimizer.display_suggestions()

# Apply automatic optimizations
for suggestion in plan['quick_wins']:
    if suggestion.auto_applicable:
        optimizer.apply_optimization(suggestion, dry_run=False)

# Generate load test code
load_test_code = optimizer.generate_load_test_code(scenarios)
with open("load_test.py", "w") as f:
    f.write(load_test_code)

# Save optimization plan
optimizer.save_optimization_plan("optimization_plan.md", plan)
```

## CLI Usage

```bash
# Profile a function
python -m src.profiler --target mymodule:my_function --output profile.json

# Analyze queries
python -m src.query_analyzer --input ./src --output issues.json

# Predict bottlenecks
python -m src.predictor --profile profile.json --loads 100,500,1000

# Generate optimizations
python -m src.optimizer --profile profile.json --issues issues.json --output plan.md

# Full pipeline
python -m src.cli --input ./src --predict --optimize
```

## Detected Query Issues

| Issue Type | Description | Severity |
|------------|-------------|----------|
| N+1 Queries | Queries inside loops | Critical |
| Missing Index | No index on filtered columns | High |
| SELECT * | Retrieving unnecessary columns | Medium |
| Missing WHERE | Unbounded queries | High |
| Unbounded Query | No LIMIT on ORDER BY | Medium |
| Inefficient Join | Too many JOINs | Low |
| Nested Subquery | Multiple nested SELECTs | Medium |

## Optimization Types

| Type | Description | Example |
|------|-------------|---------|
| Caching | Add memoization/caching | @lru_cache |
| Algorithm | Improve time complexity | O(n²) → O(n) |
| Database | Query optimizations | Add indexes |
| Memory | Reduce memory usage | Use generators |
| Concurrency | Parallel processing | asyncio/multiprocessing |
| Vectorization | Use numpy/pandas | Array operations |

## Bottleneck Prediction

The predictor estimates performance at different load levels:

```
Function: get_user_data
Current: 5ms
At 100 users: 8ms
At 500 users: 35ms
At 1000 users: 120ms (CRITICAL)
```

Predictions consider:
- Current execution time
- Call frequency
- Algorithmic complexity
- Resource contention
- Database query patterns

## Load Test Generation

Automatically generates Locust test scenarios:

```python
from locust import HttpUser, task, between

class PerformanceTest(HttpUser):
    wait_time = between(1, 3)
    
    @task(1)
    def baseline(self):
        self.client.get('/api/users')
    
    @task(3)
    def stress_hotspot(self):
        self.client.get('/api/expensive-endpoint')
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Performance Analysis

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r skill8-performance-prophet/requirements.txt
      
      - name: Profile application
        run: |
          python -c "
          from src.profiler import Profiler
          from src.query_analyzer import QueryAnalyzer
          from src.predictor import BottleneckPredictor
          
          profiler = Profiler()
          # Run your application's test suite with profiling
          result = profiler.profile_module('tests.load_test', 'run')
          profiler.save_report('profile.json', result)
          
          # Analyze queries
          analyzer = QueryAnalyzer()
          issues = analyzer.analyze_directory('./src')
          
          # Predict bottlenecks at production scale
          predictor = BottleneckPredictor()
          predictions = predictor.predict_bottlenecks(result, [1000, 10000])
          
          if any(p.risk_level in ('critical', 'high') for p in predictions):
              print('::warning::Performance bottlenecks predicted')
          "
      
      - name: Upload profile
        uses: actions/upload-artifact@v3
        with:
          name: performance-profile
          path: profile.json
      
      - name: Comment PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const profile = JSON.parse(fs.readFileSync('profile.json'));
            // Post performance summary as PR comment
```

## Configuration

### Environment Variables

```bash
PERFORMANCE_TARGET_LOADS=100,500,1000,5000
PERFORMANCE_ALERT_THRESHOLD=1000ms
PROFILING_ENABLED=true
```

### Profiler Options

```python
profiler = Profiler()

# Profile with memory tracking
result, _ = profiler.profile_function(func, memory=True)

# Profile with line-by-line detail
@Profiler.profile_lines(follow=[helper_func])
def my_function():
    pass

# Profile memory usage
@Profiler.profile_memory
def memory_heavy_function():
    pass
```

## Examples

See the `examples/` directory:

- `profile_flask_app.py` - Profile a Flask application
- `detect_n_plus_one.py` - Find N+1 query issues
- `predict_scaling.py` - Predict scaling bottlenecks
- `generate_load_tests.py` - Create Locust tests

## Visualization

Export profiling data for visualization tools:

```python
# Snakeviz
profiler.export_to_pstats("profile.prof")
# Run: snakeviz profile.prof

# Flamegraph
profiler.generate_flamegraph("flamegraph.svg")

# Chrome DevTools
# Convert to Chrome tracing format
```

## Testing

```bash
pytest tests/
```

## License

MIT - RobeetsDay Project