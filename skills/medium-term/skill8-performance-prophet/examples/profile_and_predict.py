#!/usr/bin/env python3
"""Example: Profile code and predict bottlenecks."""

import sys
sys.path.insert(0, '..')

import time
from src.profiler import Profiler
from src.query_analyzer import QueryAnalyzer
from src.predictor import BottleneckPredictor
from src.optimizer import Optimizer

# Example function to profile
def example_function():
    """A function with intentional performance issues for demonstration."""
    result = []
    
    # Simulate some work
    for i in range(1000):
        # This loop could be optimized
        result.append(i ** 2)
    
    # Simulate database-like operation
    data = list(range(100))
    processed = []
    for item in data:
        # N+1 pattern simulation
        time.sleep(0.001)  # Simulate query
        processed.append(item * 2)
    
    return sum(result) + sum(processed)

def main():
    print("=" * 60)
    print("Performance Prophet - Profile & Predict Example")
    print("=" * 60)
    
    # Profile the function
    print("\n1. Profiling example function...")
    profiler = Profiler()
    result, output = profiler.profile_function(example_function, memory=True)
    
    # Display results
    print("\n2. Profile Results:")
    profiler.display_results(result)
    
    # Save profile
    profiler.save_report("profile_result.json", result)
    print("\n   ✓ Saved profile to profile_result.json")
    
    # Analyze code for query issues
    print("\n3. Analyzing code for query issues...")
    analyzer = QueryAnalyzer()
    
    # Scan the examples directory
    issues = analyzer.analyze_directory(".", pattern="*.py")
    
    summary = analyzer.get_summary()
    print(f"   Total issues: {summary['total_issues']}")
    print(f"   Critical: {summary['critical_issues']}")
    print(f"   High: {summary['high_issues']}")
    
    if issues:
        analyzer.display_issues()
    
    # Predict bottlenecks
    print("\n4. Predicting bottlenecks at scale...")
    predictor = BottleneckPredictor()
    
    predictions = predictor.predict_bottlenecks(
        result,
        target_loads=[100, 500, 1000, 5000]
    )
    
    predictor.display_predictions(predictions)
    
    # Predict database bottlenecks
    print("\n5. Predicting database bottlenecks...")
    db_predictions = predictor.predict_database_bottlenecks(
        issues,
        user_growth=[100, 500, 1000, 5000, 10000]
    )
    
    for pred in db_predictions:
        print(f"\n   {pred.component}")
        print(f"   Bottleneck expected at: {pred.bottleneck_at or 'Not in tested range'} users")
        print(f"   Confidence: {pred.confidence}")
        print(f"   Recommendations:")
        for rec in pred.recommendations[:3]:
            print(f"     - {rec}")
    
    # Save predictions
    predictor.save_predictions(
        "predictions.json",
        predictions,
        db_predictions
    )
    print("\n   ✓ Saved predictions to predictions.json")
    
    # Generate load test scenarios
    print("\n6. Generating load test scenarios...")
    scenarios = predictor.generate_load_test_scenarios(result, predictions)
    
    print(f"   Generated {len(scenarios)} scenarios:")
    for scenario in scenarios:
        print(f"     - {scenario['name']}: {scenario['users']} users, {scenario['duration']}")
    
    # Generate optimization plan
    print("\n7. Generating optimization plan...")
    optimizer = Optimizer()
    
    plan = optimizer.generate_optimization_plan(result, issues)
    
    print(f"   Quick wins: {len(plan['quick_wins'])}")
    print(f"   Planned: {len(plan['planned'])}")
    print(f"   Strategic: {len(plan['strategic'])}")
    print(f"   Estimated improvement: {plan['estimated_total_improvement']}")
    
    optimizer.display_suggestions()
    
    # Save optimization plan
    optimizer.save_optimization_plan("optimization_plan.md", plan)
    print("\n   ✓ Saved optimization plan to optimization_plan.md")
    
    # Generate load test code
    print("\n8. Generating load test code...")
    load_test_code = optimizer.generate_load_test_code(scenarios)
    
    with open("load_test.py", "w") as f:
        f.write(load_test_code)
    print("   ✓ Saved load test to load_test.py")
    
    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()