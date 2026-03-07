"""Bottleneck predictor using profiling data and machine learning."""

import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import math

try:
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import PolynomialFeatures
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .profiler import ProfileResult, FunctionProfile
from .query_analyzer import QueryIssue, QueryIssueType

console = Console()


@dataclass
class ScalingPrediction:
    """Prediction of how code will scale."""
    component: str
    current_load: int
    predicted_loads: Dict[int, float]  # load -> predicted time
    bottleneck_at: Optional[int] = None
    confidence: str = "medium"  # low, medium, high
    limiting_factor: str = ""
    recommendations: List[str] = field(default_factory=list)


@dataclass
class BottleneckPrediction:
    """Predicted bottleneck under load."""
    function_name: str
    file_path: str
    current_time_ms: float
    predicted_time_at_load: Dict[int, float]
    risk_level: str  # low, medium, high, critical
    probability: float
    impact_description: str


class BottleneckPredictor:
    """Predicts performance bottlenecks before they occur in production."""
    
    def __init__(self):
        self.historical_data: List[ProfileResult] = []
        self.scaling_models: Dict[str, Any] = {}
    
    def add_historical_data(self, profile: ProfileResult):
        """Add historical profiling data for trend analysis."""
        self.historical_data.append(profile)
    
    def predict_bottlenecks(self, current_profile: ProfileResult,
                           target_loads: List[int] = None) -> List[BottleneckPrediction]:
        """Predict bottlenecks at various load levels."""
        target_loads = target_loads or [100, 500, 1000, 5000, 10000]
        predictions = []
        
        # Get hotspots
        hotspots = current_profile.get_hotspots(20)
        
        for func in hotspots:
            if func.cumulative_time < 0.001:  # Skip very fast functions
                continue
            
            # Predict scaling behavior
            predicted_times = {}
            for load in target_loads:
                # Simple model: time scales with load, but with diminishing returns
                # for CPU-bound and linear for I/O bound
                predicted_time = self._predict_time(func, load)
                predicted_times[load] = predicted_time
            
            # Determine risk level
            max_predicted = max(predicted_times.values())
            current_ms = func.cumulative_time * 1000
            
            if max_predicted > current_ms * 100:  # 100x increase
                risk = "critical"
                probability = 0.9
            elif max_predicted > current_ms * 10:  # 10x increase
                risk = "high"
                probability = 0.75
            elif max_predicted > current_ms * 2:  # 2x increase
                risk = "medium"
                probability = 0.5
            else:
                risk = "low"
                probability = 0.25
            
            if risk in ("high", "critical"):
                impact = self._describe_impact(func, predicted_times)
                
                prediction = BottleneckPrediction(
                    function_name=func.name,
                    file_path=func.file,
                    current_time_ms=current_ms,
                    predicted_time_at_load=predicted_times,
                    risk_level=risk,
                    probability=probability,
                    impact_description=impact
                )
                predictions.append(prediction)
        
        return sorted(predictions, key=lambda x: x.probability, reverse=True)
    
    def _predict_time(self, func: FunctionProfile, load: int) -> float:
        """Predict execution time at a given load."""
        base_time = func.cumulative_time * 1000  # Convert to ms
        
        # Different scaling models based on function characteristics
        if func.call_count > 1000:
            # High call count suggests O(n) or worse
            # Time scales linearly with load
            return base_time * (load / 100)
        elif base_time > 100:
            # Slow function - CPU bound
            # May not scale linearly due to resource contention
            return base_time * math.log(load / 100 + 1, 2)
        else:
            # Fast function - probably fine
            return base_time * math.sqrt(load / 100)
    
    def _describe_impact(self, func: FunctionProfile, 
                        predictions: Dict[int, float]) -> str:
        """Generate human-readable impact description."""
        max_load = max(predictions.keys())
        max_time = predictions[max_load]
        
        if func.call_count > 1000:
            return f"Called {func.call_count:,} times, could take {max_time:.0f}ms at {max_load} concurrent users"
        elif max_time > 1000:
            return f"Could become a major bottleneck, taking {max_time/1000:.1f}s per call"
        else:
            return f"Response time may degrade to {max_time:.0f}ms"
    
    def predict_database_bottlenecks(self, query_issues: List[QueryIssue],
                                     user_growth: List[int] = None) -> List[ScalingPrediction]:
        """Predict database bottlenecks based on query analysis."""
        user_growth = user_growth or [100, 500, 1000, 5000, 10000]
        predictions = []
        
        # Group issues by type
        n_plus_one = [i for i in query_issues if i.issue_type == QueryIssueType.N_PLUS_ONE]
        missing_index = [i for i in query_issues if i.issue_type == QueryIssueType.MISSING_INDEX]
        full_scans = [i for i in query_issues if i.issue_type == QueryIssueType.FULL_TABLE_SCAN]
        
        # N+1 predictions
        if n_plus_one:
            pred = self._predict_n_plus_one_scaling(n_plus_one, user_growth)
            predictions.append(pred)
        
        # Missing index predictions
        if missing_index:
            pred = self._predict_index_scaling(missing_index, user_growth)
            predictions.append(pred)
        
        # Full table scan predictions
        if full_scans:
            pred = self._predict_scan_scaling(full_scans, user_growth)
            predictions.append(pred)
        
        return predictions
    
    def _predict_n_plus_one_scaling(self, issues: List[QueryIssue],
                                   user_growth: List[int]) -> ScalingPrediction:
        """Predict N+1 query scaling issues."""
        current_queries = 2  # Assume current optimization
        
        predicted = {}
        bottleneck_at = None
        
        for users in user_growth:
            # N+1 means queries = 1 + N (where N = number of items)
            # Assume average 50 items per user
            queries = 1 + (users * 50)
            
            # Convert to response time (assume 10ms per query)
            response_time = queries * 0.01
            predicted[users] = response_time
            
            # Mark bottleneck point
            if bottleneck_at is None and response_time > 10:  # > 10 seconds
                bottleneck_at = users
        
        return ScalingPrediction(
            component="Database (N+1 Queries)",
            current_load=100,
            predicted_loads=predicted,
            bottleneck_at=bottleneck_at,
            confidence="high",
            limiting_factor="Database connection pool and query latency",
            recommendations=[
                "Implement batch loading with select_related() / prefetch_related()",
                "Use DataLoader pattern for GraphQL",
                "Consider caching frequently accessed data",
                "Add database connection pooling"
            ]
        )
    
    def _predict_index_scaling(self, issues: List[QueryIssue],
                              user_growth: List[int]) -> ScalingPrediction:
        """Predict missing index scaling issues."""
        # Logarithmic scaling without index, constant with index
        predicted = {}
        bottleneck_at = None
        
        for users in user_growth:
            # Assume table grows with users
            table_size = users * 10
            # Without index: O(log n) to O(n) depending on data
            response_time = 0.1 * math.log(table_size + 1, 10)
            predicted[users] = response_time
            
            if bottleneck_at is None and response_time > 1:
                bottleneck_at = users
        
        return ScalingPrediction(
            component="Database (Missing Indexes)",
            current_load=100,
            predicted_loads=predicted,
            bottleneck_at=bottleneck_at,
            confidence="medium",
            limiting_factor="Full table scans on growing tables",
            recommendations=[
                "Add indexes on frequently filtered columns",
                "Use EXPLAIN ANALYZE to verify query plans",
                "Monitor slow query log",
                "Consider covering indexes for common queries"
            ]
        )
    
    def _predict_scan_scaling(self, issues: List[QueryIssue],
                             user_growth: List[int]) -> ScalingPrediction:
        """Predict full table scan scaling issues."""
        predicted = {}
        bottleneck_at = None
        
        for users in user_growth:
            # Full scans scale linearly with table size
            table_size_mb = users * 0.01  # Assume 10KB per user
            response_time = table_size_mb * 0.1  # 100ms per MB
            predicted[users] = response_time
            
            if bottleneck_at is None and response_time > 1:
                bottleneck_at = users
        
        return ScalingPrediction(
            component="Database (Full Table Scans)",
            current_load=100,
            predicted_loads=predicted,
            bottleneck_at=bottleneck_at,
            confidence="high",
            limiting_factor="Disk I/O for reading entire tables",
            recommendations=[
                "Add WHERE clauses to limit scanned rows",
                "Create appropriate indexes",
                "Implement pagination for large result sets",
                "Use covering indexes when possible"
            ]
        )
    
    def generate_load_test_scenarios(self, profile: ProfileResult,
                                    predictions: List[BottleneckPrediction]) -> List[Dict[str, Any]]:
        """Generate load test scenarios based on predictions."""
        scenarios = []
        
        # Baseline scenario
        scenarios.append({
            'name': 'Baseline',
            'users': 10,
            'spawn_rate': 2,
            'duration': '5m',
            'purpose': 'Establish baseline performance'
        })
        
        # Stress test based on predicted bottlenecks
        for pred in predictions[:3]:  # Top 3 bottlenecks
            if pred.risk_level in ('high', 'critical'):
                scenario = {
                    'name': f"Stress-{pred.function_name[:30]}",
                    'users': 1000,
                    'spawn_rate': 50,
                    'duration': '10m',
                    'purpose': f"Test {pred.function_name} under load",
                    'focus': pred.file_path
                }
                scenarios.append(scenario)
        
        # Spike test
        scenarios.append({
            'name': 'Spike Test',
            'users': 5000,
            'spawn_rate': 200,
            'duration': '2m',
            'purpose': 'Test sudden traffic spike handling'
        })
        
        # Endurance test
        scenarios.append({
            'name': 'Endurance',
            'users': 500,
            'spawn_rate': 10,
            'duration': '30m',
            'purpose': 'Test for memory leaks and degradation'
        })
        
        return scenarios
    
    def display_predictions(self, predictions: List[BottleneckPrediction]):
        """Display bottleneck predictions in console."""
        if not predictions:
            console.print("[green]✓ No critical bottlenecks predicted[/green]")
            return
        
        console.print(f"\n[bold]🔮 Predicted Bottlenecks:[/bold] ({len(predictions)} found)")
        
        for pred in predictions[:10]:  # Show top 10
            color = {
                'critical': 'red',
                'high': 'orange3',
                'medium': 'yellow',
                'low': 'green'
            }.get(pred.risk_level, 'white')
            
            console.print(f"\n[{color}]●[/[{color}] [bold]{pred.function_name}[/bold]")
            console.print(f"   File: {pred.file_path}")
            console.print(f"   Current: {pred.current_time_ms:.2f}ms")
            console.print(f"   Risk: {pred.risk_level.upper()} (confidence: {pred.probability:.0%})")
            console.print(f"   Impact: {pred.impact_description}")
            
            # Show scaling predictions
            table = Table(show_header=False)
            table.add_column("Load")
            table.add_column("Predicted Time")
            
            for load, time in sorted(pred.predicted_time_at_load.items()):
                table.add_row(f"{load} users", f"{time:.2f}ms")
            
            console.print(table)
    
    def save_predictions(self, output_path: str, 
                        predictions: List[BottleneckPrediction],
                        scaling_predictions: List[ScalingPrediction] = None):
        """Save predictions to JSON file."""
        data = {
            'timestamp': datetime.now().isoformat(),
            'bottleneck_predictions': [
                {
                    'function': p.function_name,
                    'file': p.file_path,
                    'current_time_ms': p.current_time_ms,
                    'risk_level': p.risk_level,
                    'probability': p.probability,
                    'impact': p.impact_description,
                    'predictions': p.predicted_time_at_load
                }
                for p in predictions
            ],
            'scaling_predictions': [
                {
                    'component': p.component,
                    'current_load': p.current_load,
                    'predictions': p.predicted_loads,
                    'bottleneck_at': p.bottleneck_at,
                    'confidence': p.confidence,
                    'limiting_factor': p.limiting_factor,
                    'recommendations': p.recommendations
                }
                for p in (scaling_predictions or [])
            ]
        }
        
        Path(output_path).write_text(json.dumps(data, indent=2))
        console.print(f"[green]✓[/green] Predictions saved to {output_path}")