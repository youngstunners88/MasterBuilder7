# AI Route Optimizer Skill

Analyzes and optimizes API routes for performance using AI-powered analysis.

## Overview

The AI Route Optimizer provides comprehensive performance analysis for API routes, detecting bottlenecks, suggesting optimizations, and generating actionable reports. It integrates with the iHhashi quantum dispatch system for delivery route optimization.

## Features

- **Route Performance Analysis**: Comprehensive latency and performance profiling
- **Bottleneck Detection**: N+1 queries, synchronous I/O, missing caches, inefficient queries
- **Optimization Recommendations**: Prioritized by effort vs impact
- **Load Prediction**: Statistical forecasting of route traffic
- **Caching Strategy**: Intelligent cache recommendations with TTL
- **Database Optimization**: Index suggestions, query batching
- **Quantum Integration**: Delivery route optimization via D-Wave

## Usage

### Basic Analysis

```python
from ai_route_optimizer import AIRouteOptimizer

optimizer = AIRouteOptimizer()

# Analyze a route
analysis = optimizer.analyze_route(route_code, "/api/v1/orders")

print(f"Score: {analysis.optimization_score}/100")
print(f"Current latency: {analysis.current_latency_ms}ms")
print(f"Predicted latency: {analysis.predicted_latency_ms}ms")
```

### Generate Optimization Report

```python
report = optimizer.create_optimization_report(analysis)

# Access report data
print(f"Grade: {report['grade']}")
print(f"Quick wins: {len(report['recommendations']['quick_wins'])}")
print(f"Bottlenecks: {report['bottlenecks']['total']}")
```

### Caching Strategy

```python
strategy = optimizer.suggest_caching_strategy(route_code)

print(f"Recommended cache: {strategy['type']}")
print(f"Expected hit rate: {strategy['expected_hit_rate']*100}%")
print(f"TTL recommendations: {strategy['recommendations']}")
```

### Database Optimization

```python
optimization = optimizer.optimize_database_queries(route_code)

for idx in optimization['index_recommendations']:
    print(f"Add index on {idx['collection']}: {idx['fields']}")
```

### Load Prediction

```python
historical_data = [
    {"timestamp": "2024-01-01T00:00:00", "requests": 100},
    {"timestamp": "2024-01-01T01:00:00", "requests": 150},
    # ...
]

prediction = optimizer.predict_load("/api/v1/orders", historical_data)
print(f"Predicted: {prediction.predicted_requests_per_minute} req/min")
print(f"Recommended rate limit: {prediction.recommended_rate_limit}")
```

### Route Comparison

```python
comparison = optimizer.compare_routes(route_v1, route_v2, "v1", "v2")

print(f"Winner: {comparison.winner}")
print(f"Latency improvement: {comparison.latency_improvement_ms}ms")
print(f"Score improvement: {comparison.score_improvement}")
```

### Quantum Route Optimization

```python
stops = [
    {"id": "1", "name": "Store A", "lat": -26.1, "lng": 28.0},
    {"id": "2", "name": "Store B", "lat": -26.2, "lng": 28.1},
]

result = optimizer.optimize_delivery_route_quantum(
    stops, start_lat=-26.0, start_lng=28.0
)

print(f"Optimized route: {result['route']['stops']}")
print(f"Total distance: {result['route']['total_distance_m']}m")
```

## API Reference

### AIRouteOptimizer

Main class for route optimization analysis.

#### Methods

- `analyze_route(route_code: str, route_path: str) -> RouteAnalysis`
- `detect_bottlenecks(route_code: str) -> List[Bottleneck]`
- `suggest_caching_strategy(route_code: str) -> Dict[str, Any]`
- `optimize_database_queries(route_code: str) -> Dict[str, Any]`
- `predict_load(route_path: str, historical_data: List[Dict]) -> LoadPrediction`
- `generate_optimized_route(route_code: str) -> str`
- `compare_routes(route_v1: str, route_v2: str, v1_path: str, v2_path: str) -> ComparisonResult`
- `create_optimization_report(analysis: RouteAnalysis) -> Dict[str, Any]`
- `optimize_delivery_route_quantum(stops: List[Dict], ...) -> Dict[str, Any]`
- `run_ab_test_quantum_vs_classical(stops: List[Dict], ...) -> Dict[str, Any]`

### Data Classes

- `RouteAnalysis`: Complete analysis result
- `Bottleneck`: Detected performance issue
- `Recommendation`: Optimization suggestion
- `LoadPrediction`: Traffic forecast
- `ComparisonResult`: Route comparison data

### Enums

- `OptimizationEffort`: LOW, MEDIUM, HIGH
- `OptimizationImpact`: LOW, MEDIUM, HIGH, CRITICAL
- `BottleneckType`: N_PLUS_ONE, SYNCHRONOUS_IO, MISSING_CACHE, etc.

## Running Demos

```bash
cd /home/teacherchris37/MasterBuilder7/skills/ai-route-optimizer
python ai_route_optimizer.py
```

This runs comprehensive demos showcasing all features.

## Integration with iHhashi

The optimizer integrates with iHhashi's quantum dispatch system:

- Uses D-Wave quantum annealing for delivery routes when available
- Falls back to classical OR-Tools or greedy algorithms
- Provides A/B testing between quantum and classical

## Report Structure

```json
{
  "summary": {
    "route_path": "/api/v1/orders",
    "optimization_score": 75,
    "score_grade": "C",
    "current_latency_ms": 150,
    "predicted_latency_ms": 80,
    "latency_improvement_percent": 46.7
  },
  "bottlenecks": [...],
  "recommendations": {
    "quick_wins": [...],
    "high_impact": [...],
    "all": [...]
  },
  "action_plan": [...],
  "optimized_code": "..."
}
```

## Optimization Strategies

- **Query Batching**: Combine multiple queries
- **Response Caching**: Redis, memcached, or in-memory
- **Async Conversion**: I/O bound to async/await
- **Database Indexing**: Automatic index suggestions
- **Connection Pooling**: Pool configuration hints
- **Compression**: Response compression hints

## Performance Metrics

The optimizer tracks:
- Lines of code
- Cyclomatic complexity
- Database query count
- Bottleneck severity
- Cache hit rates (predicted)
- Latency estimates

## Author

MasterBuilder7
