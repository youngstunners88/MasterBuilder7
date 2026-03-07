# A/B Testing Framework

A production-ready A/B testing framework for agent prompts, configurations, and strategies. This framework enables systematic experimentation with statistical rigor.

## Features

- **Test Types**: Prompt variations, agent configurations, strategy comparisons, model comparisons
- **Traffic Allocation**: Percentage-based with sticky user assignments
- **Statistical Analysis**: P-values, confidence intervals, Cohen's d effect size, power analysis
- **Early Stopping**: Sequential testing with automatic winner detection
- **Storage**: PostgreSQL + Redis with in-memory fallback for testing
- **Export**: CSV and JSON export for external analysis

## Quick Start

```python
import asyncio
from ab_testing import ABTestFramework, TestType

async def main():
    # Initialize framework
    framework = ABTestFramework()
    await framework.initialize()
    
    # Create a test
    test = await framework.create_test(
        name="Prompt Optimization Test",
        test_type=TestType.PROMPT_VARIATION,
        variants=[
            {
                "name": "Control",
                "config": {"system_prompt": "You are a helpful assistant.", "temperature": 0.7},
                "traffic_percentage": 50,
                "is_control": True
            },
            {
                "name": "Treatment",
                "config": {"system_prompt": "You are an expert assistant...", "temperature": 0.5},
                "traffic_percentage": 50
            }
        ],
        hypothesis="Structured prompt improves response quality",
        primary_metric="consensus_score",
        auto_start=True
    )
    
    # Assign variant to user
    variant = await framework.assign_variant(test.test_id, user_id="user_123")
    
    # Use the variant config
    print(f"Using variant: {variant.name}")
    print(f"Config: {variant.config}")
    
    # Record result
    await framework.record_result(
        test_id=test.test_id,
        variant_id=variant.variant_id,
        metrics={
            "consensus_score": 0.85,
            "success_rate": 1,
            "token_usage": 450,
            "execution_time": 1.5
        },
        user_id="user_123"
    )
    
    # Analyze and determine winner
    winner = await framework.determine_winner(test.test_id)
    print(f"Winner: {winner.recommendation}")
    
    await framework.close()

asyncio.run(main())
```

## Core Classes

### ABTest
Represents an A/B test with:
- `test_id`: Unique identifier
- `name`: Human-readable name
- `test_type`: Type of test (prompt, config, strategy, model)
- `variants`: List of Variant objects
- `status`: draft, running, paused, completed, stopped
- `hypothesis`: The hypothesis being tested
- `primary_metric`: Main metric for winner determination
- `secondary_metrics`: Additional metrics to track

### Variant
Represents a test variant with:
- `variant_id`: Unique identifier
- `name`: Human-readable name
- `config`: VariantConfig with prompt, temperature, model, etc.
- `traffic_percentage`: Percentage of traffic (0-100)
- `is_control`: Whether this is the control variant

### TestResult
Represents a single execution result:
- `result_id`: Unique identifier
- `variant_id`: Variant that was used
- `metrics`: Dictionary of metric values
- `timestamp`: When the result was recorded
- `context`: Additional context

### TestReport
Comprehensive test report with:
- Variant summaries
- Statistical analyses
- Winner determination
- Recommendations

## Metrics

Built-in metrics to track:

| Metric | Type | Description |
|--------|------|-------------|
| `success_rate` | Binary (0/1) | Task completion success |
| `consensus_score` | Continuous (0-1) | Average consensus score |
| `token_usage` | Integer | Token count (cost) |
| `execution_time` | Float (seconds) | Execution time |
| `error_rate` | Binary (0/1) | Error occurrence |
| `user_satisfaction` | Integer (1-5/10) | User rating |
| `cost` | Float | Monetary cost |
| `quality_score` | Continuous (0-1) | Quality assessment |

## Statistical Analysis

The framework provides rigorous statistical analysis:

### P-Value Calculation
Welch's t-test (unequal variances) for comparing means between variants.

### Confidence Intervals
95% confidence intervals for the difference in means.

### Effect Size (Cohen's d)
- Small: 0.2
- Medium: 0.5
- Large: 0.8

### Sample Size Calculation
```python
calculator = StatisticalCalculator()
n = calculator.calculate_sample_size(
    baseline_rate=0.5,      # 50% baseline
    minimum_detectable_effect=0.1,  # 10% improvement
    alpha=0.05,             # 5% significance
    power=0.8               # 80% power
)
# Returns: ~3,900 samples per variant
```

### Early Stopping
The framework supports sequential testing with:
- Automatic significance detection
- Futility checking
- Maximum sample enforcement

## Storage

### PostgreSQL Schema

**ab_tests table:**
```sql
CREATE TABLE ab_tests (
    test_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    test_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'draft',
    hypothesis TEXT,
    primary_metric VARCHAR(50) NOT NULL,
    secondary_metrics JSONB DEFAULT '[]',
    min_sample_size INTEGER DEFAULT 100,
    confidence_threshold FLOAT DEFAULT 0.95,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    metadata JSONB DEFAULT '{}',
    variants JSONB NOT NULL
);
```

**ab_test_results table:**
```sql
CREATE TABLE ab_test_results (
    result_id VARCHAR(64) PRIMARY KEY,
    test_id VARCHAR(64) REFERENCES ab_tests(test_id),
    variant_id VARCHAR(64) NOT NULL,
    metrics JSONB NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    context JSONB,
    session_id VARCHAR(100),
    user_id VARCHAR(100),
    metadata JSONB
);
```

### Redis Usage
- Real-time assignment counters
- Sticky user assignments (TTL: 24 hours)
- Test status caching

### Mock Storage
When database libraries are not available, the framework automatically falls back to in-memory mock storage for testing.

## Framework Methods

### Test Management
- `create_test(...)`: Create a new A/B test
- `start_test(test_id)`: Start a draft test
- `pause_test(test_id)`: Pause a running test
- `resume_test(test_id)`: Resume a paused test
- `stop_test(test_id, reason, winner_variant_id)`: Stop a test
- `list_active_tests()`: List running tests
- `list_all_tests(status, test_type)`: List all tests

### Traffic & Results
- `assign_variant(test_id, context, user_id)`: Assign variant to user
- `record_result(test_id, variant_id, metrics)`: Record execution result

### Analysis
- `analyze_results(test_id)`: Perform statistical analysis
- `determine_winner(test_id)`: Determine winning variant
- `get_test_report(test_id)`: Generate comprehensive report

### Utilities
- `calculate_required_sample_size(...)`: Calculate needed samples
- `export_to_csv(test_id, filepath)`: Export to CSV
- `export_to_json(test_id, filepath)`: Export to JSON

## Demo

Run the built-in demo:

```bash
cd /home/teacherchris37/MasterBuilder7/apex/evolution
python ab_testing.py
```

The demo simulates:
1. Creating a prompt variation test
2. Recording 250 results
3. Statistical analysis
4. Winner determination
5. Test completion

## Configuration

### Environment Variables
```bash
# PostgreSQL
DATABASE_URL=postgresql://user:pass@localhost/ab_testing

# Redis
REDIS_URL=redis://localhost:6379
```

### Framework Initialization
```python
framework = ABTestFramework(
    postgres_dsn="postgresql://localhost/ab_testing",
    redis_url="redis://localhost:6379"
)
```

## Best Practices

1. **Define Clear Hypotheses**: Always include a specific, testable hypothesis
2. **Choose Primary Metric**: Select ONE primary metric for winner determination
3. **Calculate Sample Size**: Use `calculate_required_sample_size()` beforehand
4. **Run Until Significant**: Don't peek at results too early
5. **Document Context**: Record context with results for post-hoc analysis

## Example: Model Comparison Test

```python
test = await framework.create_test(
    name="kimi-k2-5 vs kimi-k1-5",
    test_type=TestType.MODEL_COMPARISON,
    variants=[
        {
            "name": "kimi-k2-5",
            "config": {"model": "kimi-k2-5", "temperature": 0.7},
            "traffic_percentage": 50,
            "is_control": True
        },
        {
            "name": "kimi-k1-5",
            "config": {"model": "kimi-k1-5", "temperature": 0.7},
            "traffic_percentage": 50
        }
    ],
    hypothesis="kimi-k2-5 produces higher quality responses",
    primary_metric="quality_score",
    secondary_metrics=["token_usage", "execution_time"],
    min_sample_size=500
)
```

## Example: Strategy Comparison

```python
test = await framework.create_test(
    name="Single vs Multi-Agent Strategy",
    test_type=TestType.STRATEGY_COMPARISON,
    variants=[
        {
            "name": "Single Agent",
            "config": {"strategy": "single_agent"},
            "traffic_percentage": 50,
            "is_control": True
        },
        {
            "name": "Multi-Agent",
            "config": {"strategy": "multi_agent"},
            "traffic_percentage": 50
        }
    ],
    hypothesis="Multi-agent strategy improves task completion",
    primary_metric="success_rate"
)
```

## License

MIT License - Part of MasterBuilder7 Apex Framework
