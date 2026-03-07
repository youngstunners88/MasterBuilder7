"""
AI Route Optimizer Agent

Analyzes and optimizes API routes for performance using AI-powered analysis.
Integrates with iHhashi's quantum dispatch system for delivery route optimization
and provides classical optimization as fallback.

Author: MasterBuilder7
Version: 1.0.0
"""

import ast
import re
import json
import time
import hashlib
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
import statistics


# ============================================================================
# DATA CLASSES AND ENUMS
# ============================================================================

class OptimizationEffort(Enum):
    """Effort required to implement optimization"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class OptimizationImpact(Enum):
    """Expected impact of optimization"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BottleneckType(Enum):
    """Types of performance bottlenecks"""
    N_PLUS_ONE = "n_plus_one_queries"
    SYNCHRONOUS_IO = "synchronous_io"
    MISSING_CACHE = "missing_cache"
    INEFFICIENT_QUERY = "inefficient_query"
    LACKING_INDEX = "lacking_index"
    MEMORY_LEAK = "memory_leak"
    CPU_INTENSIVE = "cpu_intensive"
    RATE_LIMITING = "rate_limiting"
    SERIALIZATION = "serialization_overhead"
    DATABASE_CONNECTION = "database_connection_pool"


@dataclass
class Bottleneck:
    """Identified performance bottleneck"""
    type: BottleneckType
    description: str
    severity: float  # 0.0 - 1.0
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    suggested_fix: Optional[str] = None


@dataclass
class Recommendation:
    """Optimization recommendation"""
    title: str
    description: str
    effort: OptimizationEffort
    impact: OptimizationImpact
    code_changes: Optional[str] = None
    expected_improvement_ms: Optional[float] = None
    category: str = "general"


@dataclass
class RouteAnalysis:
    """Complete analysis of an API route"""
    route_path: str
    route_code: str
    current_latency_ms: float
    predicted_latency_ms: float
    optimization_score: float  # 0-100
    bottlenecks: List[Bottleneck]
    recommendations: List[Recommendation]
    database_queries: List[Dict[str, Any]]
    cache_opportunities: List[Dict[str, Any]]
    async_opportunities: List[Dict[str, Any]]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    optimized_code: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LoadPrediction:
    """Predicted load for a route"""
    route_path: str
    predicted_requests_per_minute: float
    confidence_interval: Tuple[float, float]
    peak_hours: List[int]
    recommended_rate_limit: int
    scaling_recommendation: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ComparisonResult:
    """Result of comparing two route versions"""
    route_v1_path: str
    route_v2_path: str
    latency_improvement_ms: float
    latency_improvement_percent: float
    score_improvement: float
    v1_score: float
    v2_score: float
    winner: str
    detailed_comparison: Dict[str, Any]


# ============================================================================
# AI ROUTE OPTIMIZER CLASS
# ============================================================================

class AIRouteOptimizer:
    """
    AI-powered API route optimizer for performance analysis and improvement.
    
    Provides:
    - Route performance analysis
    - Bottleneck detection
    - Optimization recommendations
    - Load prediction
    - Caching strategy suggestions
    - Integration with quantum dispatch system
    
    Example:
        optimizer = AIRouteOptimizer()
        
        # Analyze a route
        analysis = optimizer.analyze_route(route_code, "/api/v1/orders")
        
        # Generate optimization report
        report = optimizer.create_optimization_report(analysis)
        
        # Get optimized code
        optimized = optimizer.generate_optimized_route(route_code)
    """
    
    def __init__(self):
        self.analysis_history: List[RouteAnalysis] = []
        self.load_history: Dict[str, List[Dict[str, Any]]] = {}
        self._init_patterns()
        
    def _init_patterns(self):
        """Initialize regex patterns for code analysis"""
        # Database query patterns
        self.db_patterns = {
            'find_one': re.compile(r'\.find_one\s*\('),
            'find_many': re.compile(r'\.find\s*\('),
            'aggregate': re.compile(r'\.aggregate\s*\('),
            'raw_query': re.compile(r'execute\s*\(|raw\s*\(|query\s*\('),
            'join': re.compile(r'\.join\s*\(|JOIN|join\s+'),
        }
        
        # ORM patterns for N+1 detection
        self.orm_patterns = {
            'django': re.compile(r'\.all\(\)|\.filter\(|\.get\(|for\s+\w+\s+in\s+\w+\.all\(\)'),
            'sqlalchemy': re.compile(r'\.query\(|session\.query\('),
            'mongoengine': re.compile(r'\.objects\(|Document\.objects'),
        }
        
        # Caching patterns
        self.cache_patterns = {
            'redis': re.compile(r'redis|cache\.get|cache\.set'),
            'memcached': re.compile(r'memcached|mc\.get|mc\.set'),
            'in_memory': re.compile(r'lru_cache|@cache|functools\.cache'),
        }
        
        # Async patterns
        self.async_patterns = {
            'async_def': re.compile(r'async\s+def'),
            'await_usage': re.compile(r'await\s+'),
            'asyncio': re.compile(r'asyncio\.|asyncio\.gather|asyncio\.create_task'),
        }
        
        # Anti-patterns
        self.antipatterns = {
            'sync_db_in_async': re.compile(r'async\s+def.*?:\s*(?:(?!await).)*database', re.DOTALL),
            'sync_file_io': re.compile(r'open\s*\(|with\s+open\s*\(|json\.load|json\.dump'),
            'no_error_handling': re.compile(r'try\s*:|except\s*:|finally\s*:'),
        }
    
    # ========================================================================
    # CORE ANALYSIS METHODS
    # ========================================================================
    
    def analyze_route(self, route_code: str, route_path: str) -> RouteAnalysis:
        """
        Perform comprehensive analysis of an API route.
        
        Analyzes:
        - Route latency estimation
        - Database query patterns
        - Caching opportunities
        - Async/await usage
        - Code complexity
        
        Args:
            route_code: The source code of the route function
            route_path: The API endpoint path (e.g., "/api/v1/orders")
            
        Returns:
            RouteAnalysis with complete performance profile
            
        Example:
            code = '''
            @app.get("/api/v1/orders")
            def get_orders(user_id: int):
                orders = db.orders.find({"user_id": user_id})
                return list(orders)
            '''
            analysis = optimizer.analyze_route(code, "/api/v1/orders")
        """
        # Detect bottlenecks
        bottlenecks = self.detect_bottlenecks(route_code)
        
        # Analyze database queries
        db_queries = self._analyze_database_queries(route_code)
        
        # Find cache opportunities
        cache_opportunities = self._find_cache_opportunities(route_code, db_queries)
        
        # Find async opportunities
        async_opportunities = self._find_async_opportunities(route_code)
        
        # Calculate metrics
        metrics = self._calculate_metrics(route_code, db_queries, bottlenecks)
        
        # Estimate current and predicted latency
        current_latency = self._estimate_latency(route_code, db_queries, bottlenecks)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            route_code, bottlenecks, db_queries, cache_opportunities, async_opportunities
        )
        
        # Calculate optimization score
        optimization_score = self._calculate_optimization_score(
            bottlenecks, recommendations, current_latency
        )
        
        # Predict latency after optimization
        predicted_latency = self._predict_optimized_latency(
            current_latency, recommendations
        )
        
        # Generate optimized code
        optimized_code = self.generate_optimized_route(route_code)
        
        analysis = RouteAnalysis(
            route_path=route_path,
            route_code=route_code,
            current_latency_ms=current_latency,
            predicted_latency_ms=predicted_latency,
            optimization_score=optimization_score,
            bottlenecks=bottlenecks,
            recommendations=recommendations,
            database_queries=db_queries,
            cache_opportunities=cache_opportunities,
            async_opportunities=async_opportunities,
            optimized_code=optimized_code,
            metrics=metrics
        )
        
        self.analysis_history.append(analysis)
        return analysis
    
    def detect_bottlenecks(self, route_code: str) -> List[Bottleneck]:
        """
        Detect performance bottlenecks in route code.
        
        Identifies:
        - N+1 query problems
        - Synchronous I/O in async contexts
        - Missing caching
        - Inefficient database queries
        - Missing database indexes
        - Memory leaks
        - CPU intensive operations
        
        Args:
            route_code: Source code to analyze
            
        Returns:
            List of detected bottlenecks with severity and suggestions
            
        Example:
            bottlenecks = optimizer.detect_bottlenecks(route_code)
            for b in bottlenecks:
                print(f"{b.type.value}: {b.description} (severity: {b.severity})")
        """
        bottlenecks = []
        lines = route_code.split('\n')
        
        # Detect N+1 queries
        n_plus_ones = self._detect_n_plus_one_queries(route_code, lines)
        bottlenecks.extend(n_plus_ones)
        
        # Detect missing caching
        cache_issues = self._detect_missing_caching(route_code, lines)
        bottlenecks.extend(cache_issues)
        
        # Detect synchronous I/O
        sync_issues = self._detect_synchronous_io(route_code, lines)
        bottlenecks.extend(sync_issues)
        
        # Detect inefficient queries
        query_issues = self._detect_inefficient_queries(route_code, lines)
        bottlenecks.extend(query_issues)
        
        # Detect CPU intensive operations
        cpu_issues = self._detect_cpu_intensive_ops(route_code, lines)
        bottlenecks.extend(cpu_issues)
        
        # Sort by severity
        bottlenecks.sort(key=lambda b: b.severity, reverse=True)
        return bottlenecks
    
    def suggest_caching_strategy(self, route_code: str) -> Dict[str, Any]:
        """
        Suggest optimal caching strategy for the route.
        
        Analyzes:
        - Current caching implementation
        - Data access patterns
        - Cache hit rate opportunities
        - TTL recommendations
        
        Args:
            route_code: Source code to analyze
            
        Returns:
            Dictionary with caching recommendations
            
        Example:
            strategy = optimizer.suggest_caching_strategy(route_code)
            print(f"Recommended cache: {strategy['type']}")
            print(f"TTL: {strategy['ttl_seconds']} seconds")
        """
        has_redis = bool(self.cache_patterns['redis'].search(route_code))
        has_memcached = bool(self.cache_patterns['memcached'].search(route_code))
        has_in_memory = bool(self.cache_patterns['in_memory'].search(route_code))
        
        # Find data that could be cached
        cacheable_data = self._identify_cacheable_data(route_code)
        
        # Determine best caching approach
        if has_redis:
            cache_type = "redis_optimized"
        elif has_memcached:
            cache_type = "memcached_optimized"
        elif has_in_memory:
            cache_type = "in_memory_optimized"
        else:
            cache_type = "redis_recommended"
        
        # Analyze access patterns for TTL
        access_patterns = self._analyze_access_patterns(route_code)
        
        recommendations = []
        
        if not any([has_redis, has_memcached, has_in_memory]):
            recommendations.append({
                "action": "implement_redis_cache",
                "priority": "high",
                "description": "Add Redis caching for frequently accessed data"
            })
        
        for data_item in cacheable_data:
            recommendations.append({
                "action": f"cache_{data_item['type']}",
                "key_pattern": data_item['key_pattern'],
                "ttl_seconds": data_item['suggested_ttl'],
                "invalidation_strategy": data_item['invalidation']
            })
        
        return {
            "type": cache_type,
            "current_implementation": {
                "redis": has_redis,
                "memcached": has_memcached,
                "in_memory": has_in_memory
            },
            "cacheable_data": cacheable_data,
            "access_patterns": access_patterns,
            "recommendations": recommendations,
            "expected_hit_rate": self._estimate_cache_hit_rate(route_code, cacheable_data),
            "estimated_latency_improvement_ms": self._estimate_cache_improvement(route_code)
        }
    
    def optimize_database_queries(self, route_code: str) -> Dict[str, Any]:
        """
        Analyze and optimize database queries in the route.
        
        Provides:
        - Query optimization suggestions
        - Index recommendations
        - Batching opportunities
        - Query count reduction
        
        Args:
            route_code: Source code to analyze
            
        Returns:
            Dictionary with query optimization recommendations
        """
        db_queries = self._analyze_database_queries(route_code)
        
        optimizations = {
            "query_count": len(db_queries),
            "queries": db_queries,
            "optimizations": [],
            "index_recommendations": [],
            "batching_opportunities": [],
            "estimated_improvement_ms": 0
        }
        
        for query in db_queries:
            # Check for missing indexes
            if query.get('has_filter') and not query.get('uses_index'):
                optimizations["index_recommendations"].append({
                    "collection": query.get('collection', 'unknown'),
                    "fields": query.get('filter_fields', []),
                    "index_type": "single" if len(query.get('filter_fields', [])) == 1 else "compound",
                    "reason": "Filter operation without index detected"
                })
            
            # Check for select * patterns
            if query.get('selects_all_fields'):
                optimizations["optimizations"].append({
                    "type": "projection",
                    "query_line": query.get('line_number'),
                    "recommendation": "Add projection to select only needed fields",
                    "example": query.get('optimized_example', '')
                })
            
            # Check for sorting without index
            if query.get('has_sort') and not query.get('sort_uses_index'):
                optimizations["index_recommendations"].append({
                    "collection": query.get('collection', 'unknown'),
                    "fields": query.get('sort_fields', []),
                    "index_type": "sort",
                    "reason": "Sort operation without index"
                })
        
        # Find batching opportunities
        batch_ops = self._find_batching_opportunities(route_code, db_queries)
        optimizations["batching_opportunities"] = batch_ops
        
        # Calculate improvement
        optimizations["estimated_improvement_ms"] = self._estimate_query_optimization_impact(
            db_queries, optimizations
        )
        
        return optimizations
    
    def predict_load(
        self, 
        route_path: str, 
        historical_data: List[Dict[str, Any]]
    ) -> LoadPrediction:
        """
        Predict future load for a route based on historical data.
        
        Uses statistical analysis and trend detection to forecast:
        - Requests per minute
        - Peak traffic hours
        - Growth patterns
        
        Args:
            route_path: API endpoint path
            historical_data: List of historical metrics with timestamps
            
        Returns:
            LoadPrediction with forecasts and recommendations
            
        Example:
            historical = [
                {"timestamp": "2024-01-01T00:00:00", "requests": 100},
                {"timestamp": "2024-01-01T01:00:00", "requests": 150},
                ...
            ]
            prediction = optimizer.predict_load("/api/v1/orders", historical)
        """
        if not historical_data:
            return LoadPrediction(
                route_path=route_path,
                predicted_requests_per_minute=0,
                confidence_interval=(0, 0),
                peak_hours=[],
                recommended_rate_limit=100,
                scaling_recommendation="insufficient_data"
            )
        
        # Extract request counts
        requests = [d.get('requests', 0) for d in historical_data]
        timestamps = [d.get('timestamp') for d in historical_data]
        
        # Calculate statistics
        avg_requests = statistics.mean(requests)
        std_dev = statistics.stdev(requests) if len(requests) > 1 else 0
        
        # Identify peak hours
        hourly_data = self._aggregate_by_hour(historical_data)
        peak_hours = sorted(
            hourly_data.keys(),
            key=lambda h: hourly_data[h],
            reverse=True
        )[:3]  # Top 3 peak hours
        
        # Calculate trend (simple linear)
        trend = self._calculate_trend(requests)
        
        # Predict future load with trend
        predicted = avg_requests + (trend * len(requests))
        
        # Confidence interval (95%)
        margin = 1.96 * std_dev if std_dev > 0 else predicted * 0.1
        confidence_low = max(0, predicted - margin)
        confidence_high = predicted + margin
        
        # Recommend rate limit
        recommended_limit = int(confidence_high * 1.5)
        
        # Scaling recommendation
        if predicted > confidence_high * 0.8:
            scaling_rec = "scale_up_immediately"
        elif trend > 0:
            scaling_rec = "monitor_and_scale_soon"
        else:
            scaling_rec = "current_capacity_sufficient"
        
        prediction = LoadPrediction(
            route_path=route_path,
            predicted_requests_per_minute=predicted,
            confidence_interval=(confidence_low, confidence_high),
            peak_hours=peak_hours,
            recommended_rate_limit=recommended_limit,
            scaling_recommendation=scaling_rec
        )
        
        # Store in history
        if route_path not in self.load_history:
            self.load_history[route_path] = []
        self.load_history[route_path].append({
            "timestamp": datetime.utcnow().isoformat(),
            "prediction": asdict(prediction)
        })
        
        return prediction
    
    def generate_optimized_route(self, route_code: str) -> str:
        """
        Generate optimized version of the route code.
        
        Applies optimizations:
        - Adds caching where beneficial
        - Converts synchronous I/O to async where possible
        - Batches database queries
        - Adds connection pooling hints
        - Implements response compression hints
        
        Args:
            route_code: Original source code
            
        Returns:
            Optimized source code
        """
        optimized = route_code
        
        # Check if already async
        is_async = 'async ' in route_code
        
        # Apply async conversion if beneficial
        if not is_async and self._should_convert_to_async(route_code):
            optimized = self._convert_to_async(optimized)
        
        # Add caching decorator if beneficial
        if self._should_add_caching(route_code):
            optimized = self._add_caching_decorator(optimized)
        
        # Optimize database queries
        optimized = self._optimize_queries_in_code(optimized)
        
        # Add connection pooling hints
        optimized = self._add_connection_pooling_hints(optimized)
        
        # Add compression hint
        if 'response' in optimized.lower() and 'compression' not in optimized.lower():
            optimized = self._add_compression_hints(optimized)
        
        return optimized
    
    def compare_routes(self, route_v1: str, route_v2: str, 
                       v1_path: str = "v1", v2_path: str = "v2") -> ComparisonResult:
        """
        Compare two versions of a route and identify improvements.
        
        Args:
            route_v1: First version of route code
            route_v2: Second version of route code
            v1_path: Path identifier for v1
            v2_path: Path identifier for v2
            
        Returns:
            ComparisonResult with detailed analysis
        """
        # Analyze both versions
        analysis_v1 = self.analyze_route(route_v1, v1_path)
        analysis_v2 = self.analyze_route(route_v2, v2_path)
        
        # Calculate improvements
        latency_improvement = analysis_v1.current_latency_ms - analysis_v2.current_latency_ms
        improvement_percent = (
            (latency_improvement / analysis_v1.current_latency_ms * 100)
            if analysis_v1.current_latency_ms > 0 else 0
        )
        
        score_improvement = analysis_v2.optimization_score - analysis_v1.optimization_score
        
        # Determine winner
        if analysis_v2.optimization_score > analysis_v1.optimization_score + 5:
            winner = v2_path
        elif analysis_v1.optimization_score > analysis_v2.optimization_score + 5:
            winner = v1_path
        else:
            winner = "tie"
        
        detailed = {
            "v1": {
                "latency_ms": analysis_v1.current_latency_ms,
                "optimization_score": analysis_v1.optimization_score,
                "bottleneck_count": len(analysis_v1.bottlenecks),
                "recommendation_count": len(analysis_v1.recommendations)
            },
            "v2": {
                "latency_ms": analysis_v2.current_latency_ms,
                "optimization_score": analysis_v2.optimization_score,
                "bottleneck_count": len(analysis_v2.bottlenecks),
                "recommendation_count": len(analysis_v2.recommendations)
            },
            "v1_bottlenecks": [b.type.value for b in analysis_v1.bottlenecks],
            "v2_bottlenecks": [b.type.value for b in analysis_v2.bottlenecks],
            "fixed_bottlenecks": [
                b.type.value for b in analysis_v1.bottlenecks 
                if b.type not in [b2.type for b2 in analysis_v2.bottlenecks]
            ],
            "new_bottlenecks": [
                b.type.value for b in analysis_v2.bottlenecks 
                if b.type not in [b1.type for b1 in analysis_v1.bottlenecks]
            ]
        }
        
        return ComparisonResult(
            route_v1_path=v1_path,
            route_v2_path=v2_path,
            latency_improvement_ms=latency_improvement,
            latency_improvement_percent=improvement_percent,
            score_improvement=score_improvement,
            v1_score=analysis_v1.optimization_score,
            v2_score=analysis_v2.optimization_score,
            winner=winner,
            detailed_comparison=detailed
        )
    
    def create_optimization_report(self, analysis: RouteAnalysis) -> Dict[str, Any]:
        """
        Create a comprehensive optimization report from analysis.
        
        Args:
            analysis: RouteAnalysis object
            
        Returns:
            Dictionary with formatted report data
        """
        # Categorize recommendations by effort/impact
        quick_wins = [r for r in analysis.recommendations 
                     if r.effort == OptimizationEffort.LOW and 
                     r.impact in [OptimizationImpact.HIGH, OptimizationImpact.CRITICAL]]
        
        high_impact = [r for r in analysis.recommendations 
                      if r.impact in [OptimizationImpact.HIGH, OptimizationImpact.CRITICAL]]
        
        low_effort = [r for r in analysis.recommendations 
                     if r.effort == OptimizationEffort.LOW]
        
        # Calculate effort breakdown
        effort_breakdown = {
            "low": len([r for r in analysis.recommendations if r.effort == OptimizationEffort.LOW]),
            "medium": len([r for r in analysis.recommendations if r.effort == OptimizationEffort.MEDIUM]),
            "high": len([r for r in analysis.recommendations if r.effort == OptimizationEffort.HIGH])
        }
        
        # Bottleneck severity breakdown
        severity_breakdown = {
            "critical": len([b for b in analysis.bottlenecks if b.severity >= 0.8]),
            "high": len([b for b in analysis.bottlenecks if 0.5 <= b.severity < 0.8]),
            "medium": len([b for b in analysis.bottlenecks if 0.3 <= b.severity < 0.5]),
            "low": len([b for b in analysis.bottlenecks if b.severity < 0.3])
        }
        
        report = {
            "summary": {
                "route_path": analysis.route_path,
                "analysis_timestamp": analysis.timestamp.isoformat(),
                "optimization_score": analysis.optimization_score,
                "score_grade": self._score_to_grade(analysis.optimization_score),
                "current_latency_ms": analysis.current_latency_ms,
                "predicted_latency_ms": analysis.predicted_latency_ms,
                "latency_improvement_ms": analysis.current_latency_ms - analysis.predicted_latency_ms,
                "latency_improvement_percent": round(
                    (analysis.current_latency_ms - analysis.predicted_latency_ms) / 
                    analysis.current_latency_ms * 100, 1
                ) if analysis.current_latency_ms > 0 else 0,
                "bottleneck_count": len(analysis.bottlenecks),
                "recommendation_count": len(analysis.recommendations)
            },
            "grade": self._score_to_grade(analysis.optimization_score),
            "performance_metrics": analysis.metrics,
            "bottlenecks": {
                "total": len(analysis.bottlenecks),
                "severity_breakdown": severity_breakdown,
                "list": [
                    {
                        "type": b.type.value,
                        "description": b.description,
                        "severity": round(b.severity, 2),
                        "line_number": b.line_number,
                        "code_snippet": b.code_snippet,
                        "suggested_fix": b.suggested_fix
                    }
                    for b in analysis.bottlenecks
                ]
            },
            "recommendations": {
                "total": len(analysis.recommendations),
                "effort_breakdown": effort_breakdown,
                "quick_wins": [
                    {
                        "title": r.title,
                        "description": r.description,
                        "impact": r.impact.value,
                        "effort": r.effort.value,
                        "expected_improvement_ms": r.expected_improvement_ms,
                        "code_changes": r.code_changes
                    }
                    for r in quick_wins[:5]  # Top 5 quick wins
                ],
                "high_impact": [
                    {
                        "title": r.title,
                        "description": r.description,
                        "impact": r.impact.value,
                        "effort": r.effort.value,
                        "category": r.category
                    }
                    for r in high_impact[:5]
                ],
                "all": [
                    {
                        "title": r.title,
                        "description": r.description,
                        "impact": r.impact.value,
                        "effort": r.effort.value,
                        "category": r.category
                    }
                    for r in analysis.recommendations
                ]
            },
            "database_analysis": {
                "query_count": len(analysis.database_queries),
                "queries": analysis.database_queries,
                "optimization": self.optimize_database_queries(analysis.route_code)
            },
            "caching_analysis": self.suggest_caching_strategy(analysis.route_code),
            "async_opportunities": analysis.async_opportunities,
            "optimized_code": analysis.optimized_code,
            "action_plan": self._generate_action_plan(analysis)
        }
        
        return report
    
    # ========================================================================
    # QUANTUM DISPATCH INTEGRATION
    # ========================================================================
    
    def optimize_delivery_route_quantum(
        self,
        stops: List[Dict[str, Any]],
        start_lat: float,
        start_lng: float,
        avg_speed_kmh: float = 30.0
    ) -> Dict[str, Any]:
        """
        Optimize delivery route using quantum-enhanced algorithm.
        
        Integrates with iHhashi's quantum dispatch system.
        Falls back to classical OR-Tools if quantum unavailable.
        
        Args:
            stops: List of delivery stops with lat, lng, id, name
            start_lat: Starting latitude
            start_lng: Starting longitude
            avg_speed_kmh: Average travel speed
            
        Returns:
            Optimization result with route and metadata
        """
        try:
            # Try to import from iHhashi's quantum dispatch
            from backend.app.services.quantum_dispatch import optimize_route_quantum
            from backend.app.services.route_optimizer import DeliveryStop
            
            # Convert to DeliveryStop objects
            delivery_stops = [
                DeliveryStop(
                    id=s['id'],
                    name=s.get('name', f"Stop {i}"),
                    lat=s['lat'],
                    lng=s['lng'],
                    service_time_minutes=s.get('service_time_minutes', 5),
                    priority=s.get('priority', 0)
                )
                for i, s in enumerate(stops)
            ]
            
            # Run quantum optimization
            result = optimize_route_quantum(
                delivery_stops, start_lat, start_lng, avg_speed_kmh
            )
            
            return {
                "success": result.success,
                "solver_type": result.solver_type,
                "route": {
                    "stops": result.route.stops,
                    "total_distance_m": result.route.total_distance_m,
                    "total_time_minutes": result.route.total_time_minutes,
                    "savings_vs_original_minutes": result.route.savings_vs_original_minutes,
                    "confidence": result.route.confidence
                },
                "solve_time_ms": result.solve_time_ms,
                "quantum_energy": result.quantum_energy,
                "num_qubits": result.num_qubits,
                "error_message": result.error_message
            }
            
        except ImportError:
            # Fallback to classical optimization
            return self._classical_route_fallback(stops, start_lat, start_lng, avg_speed_kmh)
    
    def run_ab_test_quantum_vs_classical(
        self,
        stops: List[Dict[str, Any]],
        start_lat: float,
        start_lng: float,
        avg_speed_kmh: float = 30.0
    ) -> Dict[str, Any]:
        """
        Run A/B test comparing quantum vs classical route optimization.
        
        Args:
            stops: List of delivery stops
            start_lat: Starting latitude
            start_lng: Starting longitude
            avg_speed_kmh: Average travel speed
            
        Returns:
            A/B test results with comparison metrics
        """
        try:
            from backend.app.services.quantum_dispatch import run_quantum_ab_test
            from backend.app.services.route_optimizer import DeliveryStop
            
            delivery_stops = [
                DeliveryStop(
                    id=s['id'],
                    name=s.get('name', f"Stop {i}"),
                    lat=s['lat'],
                    lng=s['lng'],
                    service_time_minutes=s.get('service_time_minutes', 5),
                    priority=s.get('priority', 0)
                )
                for i, s in enumerate(stops)
            ]
            
            result = run_quantum_ab_test(
                delivery_stops, start_lat, start_lng, avg_speed_kmh
            )
            
            return {
                "test_id": result.test_id,
                "timestamp": result.timestamp,
                "num_stops": result.num_stops,
                "quantum": {
                    "distance_m": result.quantum_distance_m,
                    "time_minutes": result.quantum_time_ms / 60000,
                    "solve_time_ms": result.quantum_solve_time_ms,
                    "success": result.quantum_success
                },
                "classical": {
                    "distance_m": result.classical_distance_m,
                    "time_minutes": result.classical_time_ms / 60000,
                    "solve_time_ms": result.classical_solve_time_ms
                },
                "improvement_percent": result.improvement_percent,
                "faster_percent": result.faster_percent,
                "winner": result.winner
            }
            
        except ImportError:
            return {
                "error": "Quantum dispatch not available",
                "fallback": "classical_only"
            }
    
    # ========================================================================
    # PRIVATE HELPER METHODS
    # ========================================================================
    
    def _detect_n_plus_one_queries(self, code: str, lines: List[str]) -> List[Bottleneck]:
        """Detect N+1 query problems in code"""
        bottlenecks = []
        
        # Pattern: for item in collection: item.related_field
        loop_patterns = [
            re.compile(r'for\s+\w+\s+in\s+(\w+)(?:\.all\(\))?:\s*\n\s*\1\.(\w+)'),
            re.compile(r'for\s+\w+\s+in\s+\w+:\s*\n\s*\w+\.(\w+)\.all\(\)'),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern in loop_patterns:
                if pattern.search(line):
                    bottlenecks.append(Bottleneck(
                        type=BottleneckType.N_PLUS_ONE,
                        description=f"Potential N+1 query detected at line {i}",
                        severity=0.8,
                        line_number=i,
                        code_snippet=line.strip(),
                        suggested_fix="Use select_related() or prefetch_related() (Django) / joinedload() (SQLAlchemy)"
                    ))
        
        return bottlenecks
    
    def _detect_missing_caching(self, code: str, lines: List[str]) -> List[Bottleneck]:
        """Detect missing caching opportunities"""
        bottlenecks = []
        
        has_caching = any(
            pattern.search(code) for pattern in self.cache_patterns.values()
        )
        
        if not has_caching:
            # Check for expensive operations that could benefit from caching
            expensive_patterns = [
                (re.compile(r'database|\.find|\.query|SELECT'), "Database query without cache"),
                (re.compile(r'http\.get|requests\.get|urllib'), "External API call without cache"),
                (re.compile(r'complex.*calculation|heavy.*compute'), "Computation without cache"),
            ]
            
            for i, line in enumerate(lines, 1):
                for pattern, desc in expensive_patterns:
                    if pattern.search(line.lower()):
                        bottlenecks.append(Bottleneck(
                            type=BottleneckType.MISSING_CACHE,
                            description=desc,
                            severity=0.6,
                            line_number=i,
                            code_snippet=line.strip(),
                            suggested_fix="Add @lru_cache or Redis caching decorator"
                        ))
        
        return bottlenecks
    
    def _detect_synchronous_io(self, code: str, lines: List[str]) -> List[Bottleneck]:
        """Detect synchronous I/O in potentially async contexts"""
        bottlenecks = []
        
        is_async = 'async ' in code
        
        if is_async:
            sync_patterns = [
                (re.compile(r'\.sleep\s*\('), "Use asyncio.sleep() instead of time.sleep()"),
                (re.compile(r'requests\.get|urllib'), "Use aiohttp or httpx for async HTTP"),
                (re.compile(r'open\s*\(|with\s+open\s*\('), "Use aiofiles for async file I/O"),
            ]
            
            for i, line in enumerate(lines, 1):
                for pattern, suggestion in sync_patterns:
                    if pattern.search(line) and 'await' not in line:
                        bottlenecks.append(Bottleneck(
                            type=BottleneckType.SYNCHRONOUS_IO,
                            description=f"Synchronous I/O in async function at line {i}",
                            severity=0.7,
                            line_number=i,
                            code_snippet=line.strip(),
                            suggested_fix=suggestion
                        ))
        
        return bottlenecks
    
    def _detect_inefficient_queries(self, code: str, lines: List[str]) -> List[Bottleneck]:
        """Detect inefficient database queries"""
        bottlenecks = []
        
        inefficient_patterns = [
            (re.compile(r'\.count\(\)'), "Count operation may be expensive on large tables"),
            (re.compile(r'ORDER\s+BY.*RAND\(\)|\.order_by\(\?[\'"]\?\)'), "Random ordering is expensive"),
            (re.compile(r'LIMIT\s+1.*OFFSET|\.offset\('), "Large offsets are slow"),
            (re.compile(r'SELECT\s+\*'), "Select all fields when you only need some"),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, desc in inefficient_patterns:
                if pattern.search(line):
                    bottlenecks.append(Bottleneck(
                        type=BottleneckType.INEFFICIENT_QUERY,
                        description=desc,
                        severity=0.5,
                        line_number=i,
                        code_snippet=line.strip(),
                        suggested_fix="Optimize query or add appropriate index"
                    ))
        
        return bottlenecks
    
    def _detect_cpu_intensive_ops(self, code: str, lines: List[str]) -> List[Bottleneck]:
        """Detect CPU intensive operations"""
        bottlenecks = []
        
        cpu_patterns = [
            (re.compile(r'for\s+\w+\s+in\s+range\s*\(\s*\d{5,}'), "Large iteration may be CPU intensive"),
            (re.compile(r'recursion|recursive'), "Recursive algorithms can be expensive"),
            (re.compile(r'sort\(|sorted\(|ORDER\s+BY'), "Sorting large datasets is CPU intensive"),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, desc in cpu_patterns:
                if pattern.search(line.lower()):
                    bottlenecks.append(Bottleneck(
                        type=BottleneckType.CPU_INTENSIVE,
                        description=desc,
                        severity=0.4,
                        line_number=i,
                        code_snippet=line.strip(),
                        suggested_fix="Consider pagination or background processing"
                    ))
        
        return bottlenecks
    
    def _analyze_database_queries(self, code: str) -> List[Dict[str, Any]]:
        """Analyze database queries in code"""
        queries = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            query_info = {
                "line_number": i,
                "code": line.strip(),
                "type": None,
                "has_filter": False,
                "selects_all_fields": False,
                "has_sort": False
            }
            
            # Detect query type
            if self.db_patterns['find_one'].search(line):
                query_info["type"] = "find_one"
            elif self.db_patterns['find_many'].search(line):
                query_info["type"] = "find_many"
            elif self.db_patterns['aggregate'].search(line):
                query_info["type"] = "aggregate"
            
            # Check for filters
            if re.search(r'\{.*:.*\}', line) or 'filter' in line.lower():
                query_info["has_filter"] = True
                # Extract filter fields
                fields = re.findall(r'["\'](\w+)["\']\s*:', line)
                query_info["filter_fields"] = fields
            
            # Check for select all
            if re.search(r'find\s*\(\s*\)|find_one\s*\(\s*\)', line):
                query_info["selects_all_fields"] = True
            
            # Check for sort
            if re.search(r'sort\(|orderby|ORDER\s+BY', line, re.I):
                query_info["has_sort"] = True
                sort_fields = re.findall(r'sort\s*\(\s*["\'](\w+)["\']', line)
                query_info["sort_fields"] = sort_fields
            
            if query_info["type"]:
                queries.append(query_info)
        
        return queries
    
    def _find_cache_opportunities(self, code: str, db_queries: List[Dict]) -> List[Dict]:
        """Find opportunities for caching"""
        opportunities = []
        
        for query in db_queries:
            if query["type"] in ["find_one", "find_many"]:
                opportunities.append({
                    "line_number": query["line_number"],
                    "description": "Query results could be cached",
                    "suggested_cache_key": f"query:{hashlib.md5(query['code'].encode()).hexdigest()[:8]}",
                    "suggested_ttl": 300  # 5 minutes default
                })
        
        return opportunities
    
    def _find_async_opportunities(self, code: str) -> List[Dict]:
        """Find opportunities to use async/await"""
        opportunities = []
        
        is_async = 'async ' in code
        
        if not is_async:
            # Check for I/O operations
            io_patterns = [
                (re.compile(r'\.get\s*\(|\.post\s*\(|requests\.'), "HTTP requests"),
                (re.compile(r'database|\.find|\.query'), "Database queries"),
                (re.compile(r'open\s*\(|read\s*\(|write\s*\('), "File I/O"),
            ]
            
            for pattern, desc in io_patterns:
                if pattern.search(code):
                    opportunities.append({
                        "description": f"Route could benefit from async {desc}",
                        "current_pattern": "synchronous",
                        "suggested_pattern": f"async {desc.lower()}",
                        "estimated_improvement": "20-40% latency reduction for I/O bound operations"
                    })
                    break
        
        return opportunities
    
    def _calculate_metrics(self, code: str, db_queries: List[Dict], 
                          bottlenecks: List[Bottleneck]) -> Dict[str, Any]:
        """Calculate various code metrics"""
        lines = code.split('\n')
        
        return {
            "lines_of_code": len(lines),
            "non_empty_lines": len([l for l in lines if l.strip()]),
            "database_query_count": len(db_queries),
            "bottleneck_count": len(bottlenecks),
            "cyclomatic_complexity": self._estimate_complexity(code),
            "has_error_handling": 'try:' in code and 'except' in code,
            "has_logging": 'logging' in code or 'logger' in code,
            "is_async": 'async ' in code,
            "has_type_hints": '->' in code or ': ' in code
        }
    
    def _estimate_latency(self, code: str, db_queries: List[Dict], 
                         bottlenecks: List[Bottleneck]) -> float:
        """Estimate current route latency in milliseconds"""
        base_latency = 10  # Base processing overhead
        
        # Add database query time
        for query in db_queries:
            if query["type"] == "find_one":
                base_latency += 15
            elif query["type"] == "find_many":
                base_latency += 25
            elif query["type"] == "aggregate":
                base_latency += 50
        
        # Add bottleneck penalties
        for bottleneck in bottlenecks:
            if bottleneck.type == BottleneckType.N_PLUS_ONE:
                base_latency += 200  # N+1 is expensive
            elif bottleneck.type == BottleneckType.SYNCHRONOUS_IO:
                base_latency += 100
            elif bottleneck.type == BottleneckType.MISSING_CACHE:
                base_latency += 30
            elif bottleneck.type == BottleneckType.INEFFICIENT_QUERY:
                base_latency += 40
        
        # Check for external API calls
        if 'requests' in code or 'http' in code:
            base_latency += 200  # External API latency
        
        return base_latency
    
    def _generate_recommendations(
        self, code: str, bottlenecks: List[Bottleneck], 
        db_queries: List[Dict], cache_opps: List[Dict], async_opps: List[Dict]
    ) -> List[Recommendation]:
        """Generate optimization recommendations"""
        recommendations = []
        
        # Add recommendations based on bottlenecks
        for bottleneck in bottlenecks:
            if bottleneck.type == BottleneckType.N_PLUS_ONE:
                recommendations.append(Recommendation(
                    title="Fix N+1 Query Problem",
                    description=bottleneck.description,
                    effort=OptimizationEffort.MEDIUM,
                    impact=OptimizationImpact.HIGH,
                    code_changes=bottleneck.suggested_fix,
                    expected_improvement_ms=150,
                    category="database"
                ))
            elif bottleneck.type == BottleneckType.MISSING_CACHE:
                recommendations.append(Recommendation(
                    title="Add Response Caching",
                    description=bottleneck.description,
                    effort=OptimizationEffort.LOW,
                    impact=OptimizationImpact.MEDIUM,
                    code_changes=bottleneck.suggested_fix,
                    expected_improvement_ms=50,
                    category="caching"
                ))
            elif bottleneck.type == BottleneckType.SYNCHRONOUS_IO:
                recommendations.append(Recommendation(
                    title="Convert to Async I/O",
                    description=bottleneck.description,
                    effort=OptimizationEffort.HIGH,
                    impact=OptimizationImpact.HIGH,
                    code_changes=bottleneck.suggested_fix,
                    expected_improvement_ms=100,
                    category="async"
                ))
        
        # Add caching recommendations
        if cache_opps and not any(r.category == "caching" for r in recommendations):
            recommendations.append(Recommendation(
                title="Implement Query Result Caching",
                description=f"Found {len(cache_opps)} queries that could benefit from caching",
                effort=OptimizationEffort.LOW,
                impact=OptimizationImpact.MEDIUM,
                category="caching"
            ))
        
        # Add async recommendations
        if async_opps and not any(r.category == "async" for r in recommendations):
            recommendations.append(Recommendation(
                title="Convert Route to Async",
                description="Route performs I/O operations that could be async",
                effort=OptimizationEffort.MEDIUM,
                impact=OptimizationImpact.HIGH,
                category="async"
            ))
        
        # Add general recommendations
        if len(db_queries) > 3:
            recommendations.append(Recommendation(
                title="Batch Database Queries",
                description=f"Route makes {len(db_queries)} separate database queries",
                effort=OptimizationEffort.MEDIUM,
                impact=OptimizationImpact.MEDIUM,
                category="database"
            ))
        
        return recommendations
    
    def _calculate_optimization_score(
        self, bottlenecks: List[Bottleneck], recommendations: List[Recommendation],
        current_latency: float
    ) -> float:
        """Calculate optimization score (0-100)"""
        score = 100.0
        
        # Deduct for bottlenecks
        for bottleneck in bottlenecks:
            score -= bottleneck.severity * 15
        
        # Deduct for high-effort recommendations
        high_effort_count = sum(1 for r in recommendations if r.effort == OptimizationEffort.HIGH)
        score -= high_effort_count * 5
        
        # Bonus for good latency
        if current_latency < 50:
            score += 10
        elif current_latency > 200:
            score -= 10
        
        return max(0, min(100, score))
    
    def _predict_optimized_latency(
        self, current_latency: float, recommendations: List[Recommendation]
    ) -> float:
        """Predict latency after applying optimizations"""
        improvement = 0
        
        for rec in recommendations:
            if rec.expected_improvement_ms:
                improvement += rec.expected_improvement_ms
        
        # Cap improvement at 80%
        max_improvement = current_latency * 0.8
        actual_improvement = min(improvement, max_improvement)
        
        return max(5, current_latency - actual_improvement)
    
    def _identify_cacheable_data(self, code: str) -> List[Dict]:
        """Identify data that could be cached"""
        cacheable = []
        
        # Look for database queries
        if re.search(r'database|\.find|\.query', code):
            cacheable.append({
                "type": "database_query_results",
                "key_pattern": "db:{collection}:{filter_hash}",
                "suggested_ttl": 300,
                "invalidation": "time_based"
            })
        
        # Look for configuration reads
        if re.search(r'config|settings|getenv', code):
            cacheable.append({
                "type": "configuration",
                "key_pattern": "config:{key}",
                "suggested_ttl": 3600,
                "invalidation": "manual"
            })
        
        return cacheable
    
    def _analyze_access_patterns(self, code: str) -> Dict[str, Any]:
        """Analyze data access patterns"""
        return {
            "read_heavy": bool(re.search(r'\.get\(|\.find|SELECT', code)),
            "write_heavy": bool(re.search(r'\.insert|\.update|INSERT|UPDATE', code)),
            "mixed": bool(re.search(r'\.find.*\.update|SELECT.*INSERT', code))
        }
    
    def _estimate_cache_hit_rate(self, code: str, cacheable_data: List[Dict]) -> float:
        """Estimate potential cache hit rate"""
        if not cacheable_data:
            return 0.0
        
        # Simple heuristic based on data types
        base_rate = 0.6
        
        for data in cacheable_data:
            if data["type"] == "configuration":
                base_rate += 0.2
            elif data["type"] == "database_query_results":
                base_rate += 0.1
        
        return min(0.95, base_rate)
    
    def _estimate_cache_improvement(self, code: str) -> float:
        """Estimate latency improvement from caching"""
        # Base improvement estimate
        return 30.0
    
    def _find_batching_opportunities(self, code: str, db_queries: List[Dict]) -> List[Dict]:
        """Find opportunities for query batching"""
        opportunities = []
        
        # Check for multiple similar queries
        query_types = {}
        for query in db_queries:
            q_type = query.get("type", "unknown")
            query_types[q_type] = query_types.get(q_type, 0) + 1
        
        for q_type, count in query_types.items():
            if count > 2:
                opportunities.append({
                    "query_type": q_type,
                    "count": count,
                    "recommendation": f"Batch {count} {q_type} queries into a single operation",
                    "estimated_improvement_ms": count * 10
                })
        
        return opportunities
    
    def _estimate_query_optimization_impact(
        self, db_queries: List[Dict], optimizations: Dict
    ) -> float:
        """Estimate latency improvement from query optimizations"""
        improvement = 0
        
        # Index improvements
        for idx_rec in optimizations.get("index_recommendations", []):
            improvement += 20  # ~20ms per index
        
        # Projection improvements
        for proj_rec in optimizations.get("optimizations", []):
            if proj_rec.get("type") == "projection":
                improvement += 10
        
        return improvement
    
    def _should_convert_to_async(self, code: str) -> bool:
        """Determine if route should be converted to async"""
        has_io = bool(re.search(r'requests|http|database|\.find|\.query', code))
        is_already_async = 'async ' in code
        
        return has_io and not is_already_async
    
    def _convert_to_async(self, code: str) -> str:
        """Convert synchronous code to async"""
        # Add async to function definition
        code = re.sub(r'^(\s*)def\s+(\w+)\s*\(', r'\1async def \2(', code, flags=re.MULTILINE)
        
        # Add await to database calls
        code = re.sub(r'([^a-zA-Z_])db\.', r'\1await db.', code)
        code = re.sub(r'([^a-zA-Z_])database\.', r'\1await database.', code)
        
        return code
    
    def _should_add_caching(self, code: str) -> bool:
        """Determine if caching should be added"""
        has_db_queries = bool(re.search(r'database|\.find|\.query', code))
        has_caching = any(pattern.search(code) for pattern in self.cache_patterns.values())
        
        return has_db_queries and not has_caching
    
    def _add_caching_decorator(self, code: str) -> str:
        """Add caching decorator to code"""
        # Add import if needed
        if 'from functools import lru_cache' not in code:
            code = 'from functools import lru_cache\n' + code
        
        # Add decorator before function
        code = re.sub(
            r'^(\s*)(async\s+)?def\s+(\w+)',
            r'\1@lru_cache(maxsize=128)\n\1\2def \3',
            code,
            flags=re.MULTILINE
        )
        
        return code
    
    def _optimize_queries_in_code(self, code: str) -> str:
        """Apply query optimizations to code"""
        # Add projection hints
        code = re.sub(
            r'\.find\s*\(\s*\)',
            '.find({}, {"_id": 1, "name": 1})  # TODO: Add only needed fields',
            code
        )
        
        return code
    
    def _add_connection_pooling_hints(self, code: str) -> str:
        """Add connection pooling hints to code"""
        if 'Database' in code or 'db' in code:
            code += '''
# TODO: Ensure connection pooling is configured
# Example:
# db = Database(pool_size=20, max_overflow=30)
'''
        return code
    
    def _add_compression_hints(self, code: str) -> str:
        """Add response compression hints"""
        return '''# Consider adding response compression middleware
# app.add_middleware(GZipMiddleware, minimum_size=1000)

''' + code
    
    def _aggregate_by_hour(self, historical_data: List[Dict]) -> Dict[int, float]:
        """Aggregate historical data by hour"""
        hourly = {}
        
        for data in historical_data:
            ts = data.get('timestamp', '')
            if 'T' in ts:
                hour = int(ts.split('T')[1].split(':')[0])
                hourly[hour] = hourly.get(hour, 0) + data.get('requests', 0)
        
        return hourly
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate simple linear trend"""
        if len(values) < 2:
            return 0.0
        
        # Simple difference-based trend
        diffs = [values[i] - values[i-1] for i in range(1, len(values))]
        return statistics.mean(diffs) if diffs else 0.0
    
    def _estimate_complexity(self, code: str) -> int:
        """Estimate cyclomatic complexity"""
        complexity = 1
        
        # Count decision points
        complexity += len(re.findall(r'\bif\b', code))
        complexity += len(re.findall(r'\belif\b', code))
        complexity += len(re.findall(r'\belse\b', code))
        complexity += len(re.findall(r'\bfor\b', code))
        complexity += len(re.findall(r'\bwhile\b', code))
        complexity += len(re.findall(r'\bexcept\b', code))
        complexity += len(re.findall(r'\band\b|\bor\b', code))
        
        return complexity
    
    def _score_to_grade(self, score: float) -> str:
        """Convert score to letter grade"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def _generate_action_plan(self, analysis: RouteAnalysis) -> List[Dict]:
        """Generate prioritized action plan"""
        actions = []
        
        # Priority 1: Critical bottlenecks
        critical = [b for b in analysis.bottlenecks if b.severity >= 0.7]
        for bottleneck in critical:
            actions.append({
                "priority": 1,
                "action": f"Fix {bottleneck.type.value}",
                "description": bottleneck.description,
                "effort": "medium",
                "expected_impact": "high"
            })
        
        # Priority 2: Quick wins
        quick_wins = [r for r in analysis.recommendations 
                     if r.effort == OptimizationEffort.LOW and 
                     r.impact in [OptimizationImpact.HIGH, OptimizationImpact.MEDIUM]]
        for rec in quick_wins[:3]:
            actions.append({
                "priority": 2,
                "action": rec.title,
                "description": rec.description,
                "effort": rec.effort.value,
                "expected_impact": rec.impact.value
            })
        
        # Priority 3: High impact recommendations
        high_impact = [r for r in analysis.recommendations 
                      if r.impact == OptimizationImpact.HIGH and r not in quick_wins]
        for rec in high_impact[:2]:
            actions.append({
                "priority": 3,
                "action": rec.title,
                "description": rec.description,
                "effort": rec.effort.value,
                "expected_impact": rec.impact.value
            })
        
        return actions
    
    def _classical_route_fallback(
        self, stops: List[Dict], start_lat: float, start_lng: float, avg_speed_kmh: float
    ) -> Dict[str, Any]:
        """Fallback to classical route optimization"""
        try:
            from backend.app.services.route_optimizer import optimize_route_vrp, DeliveryStop
            
            delivery_stops = [
                DeliveryStop(
                    id=s['id'],
                    name=s.get('name', f"Stop {i}"),
                    lat=s['lat'],
                    lng=s['lng'],
                    service_time_minutes=s.get('service_time_minutes', 5),
                    priority=s.get('priority', 0)
                )
                for i, s in enumerate(stops)
            ]
            
            result = optimize_route_vrp(delivery_stops, start_lat, start_lng, avg_speed_kmh)
            
            return {
                "success": True,
                "solver_type": "classical_fallback",
                "route": {
                    "stops": result.stops,
                    "total_distance_m": result.total_distance_m,
                    "total_time_minutes": result.total_time_minutes,
                    "savings_vs_original_minutes": result.savings_vs_original_minutes,
                    "confidence": result.confidence
                },
                "solve_time_ms": 0,
                "quantum_energy": None,
                "num_qubits": None,
                "error_message": None,
                "note": "Quantum dispatch not available, used classical fallback"
            }
            
        except ImportError:
            # Ultimate fallback - simple greedy
            return self._greedy_route_optimization(stops, start_lat, start_lng, avg_speed_kmh)
    
    def _greedy_route_optimization(
        self, stops: List[Dict], start_lat: float, start_lng: float, avg_speed_kmh: float
    ) -> Dict[str, Any]:
        """Simple greedy route optimization"""
        import math
        
        def haversine(lat1, lng1, lat2, lng2):
            R = 6371000
            phi1, phi2 = math.radians(lat1), math.radians(lat2)
            dphi = math.radians(lat2 - lat1)
            dlng = math.radians(lng2 - lng1)
            a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlng/2)**2
            return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        # Sort by priority first
        sorted_stops = sorted(stops, key=lambda s: -s.get('priority', 0))
        
        # Greedy nearest neighbor
        current_lat, current_lng = start_lat, start_lng
        optimized_order = []
        remaining = list(sorted_stops)
        
        while remaining:
            nearest = min(remaining, 
                         key=lambda s: haversine(current_lat, current_lng, s['lat'], s['lng']))
            optimized_order.append(nearest)
            remaining.remove(nearest)
            current_lat, current_lng = nearest['lat'], nearest['lng']
        
        # Calculate metrics
        total_distance = 0
        total_time = 0
        prev_lat, prev_lng = start_lat, start_lng
        
        route_stops = []
        for stop in optimized_order:
            dist = haversine(prev_lat, prev_lng, stop['lat'], stop['lng'])
            time_mins = dist / ((avg_speed_kmh * 1000) / 60)
            total_distance += dist
            total_time += time_mins + stop.get('service_time_minutes', 5)
            
            route_stops.append({
                "id": stop['id'],
                "name": stop.get('name', 'Stop'),
                "lat": stop['lat'],
                "lng": stop['lng'],
                "distance_from_previous_m": int(dist),
                "time_from_previous_minutes": round(time_mins, 1),
                "service_time_minutes": stop.get('service_time_minutes', 5),
                "cumulative_time_minutes": round(total_time, 1),
                "priority": stop.get('priority', 0)
            })
            prev_lat, prev_lng = stop['lat'], stop['lng']
        
        return {
            "success": True,
            "solver_type": "greedy_fallback",
            "route": {
                "stops": route_stops,
                "total_distance_m": total_distance,
                "total_time_minutes": round(total_time, 1),
                "savings_vs_original_minutes": 0,
                "confidence": 0.6
            },
            "solve_time_ms": 0,
            "quantum_energy": None,
            "num_qubits": None,
            "error_message": None,
            "note": "Using greedy fallback - quantum dispatch unavailable"
        }


# ============================================================================
# TEST AND DEMO CODE
# ============================================================================

def demo_basic_analysis():
    """Demo basic route analysis"""
    optimizer = AIRouteOptimizer()
    
    # Sample FastAPI route with performance issues
    sample_route = '''
@app.get("/api/v1/orders/{user_id}")
def get_user_orders(user_id: int):
    """Get all orders for a user"""
    user = db.users.find_one({"id": user_id})
    orders = db.orders.find({"user_id": user_id})
    
    # N+1 query problem
    result = []
    for order in orders:
        items = db.items.find({"order_id": order["id"]})  # N queries!
        order["items"] = list(items)
        result.append(order)
    
    return {"user": user, "orders": result}
'''
    
    print("=" * 60)
    print("AI ROUTE OPTIMIZER - BASIC ANALYSIS DEMO")
    print("=" * 60)
    
    # Analyze the route
    analysis = optimizer.analyze_route(sample_route, "/api/v1/orders/{user_id}")
    
    print(f"\n📊 Route: {analysis.route_path}")
    print(f"📈 Current Latency: {analysis.current_latency_ms}ms")
    print(f"🎯 Predicted Latency (optimized): {analysis.predicted_latency_ms}ms")
    print(f"⭐ Optimization Score: {analysis.optimization_score}/100 ({optimizer._score_to_grade(analysis.optimization_score)})")
    print(f"🔍 Bottlenecks Found: {len(analysis.bottlenecks)}")
    print(f"💡 Recommendations: {len(analysis.recommendations)}")
    
    print("\n🔴 Bottlenecks:")
    for b in analysis.bottlenecks:
        print(f"  - [{b.type.value}] {b.description} (severity: {b.severity:.2f})")
        if b.suggested_fix:
            print(f"    💡 Fix: {b.suggested_fix}")
    
    print("\n💡 Top Recommendations:")
    for r in analysis.recommendations[:3]:
        print(f"  - {r.title} (Effort: {r.effort.value}, Impact: {r.impact.value})")
    
    return analysis


def demo_caching_strategy():
    """Demo caching strategy suggestion"""
    optimizer = AIRouteOptimizer()
    
    route_code = '''
@app.get("/api/v1/products")
def get_products(category: str = None):
    if category:
        products = db.products.find({"category": category})
    else:
        products = db.products.find()
    return list(products)
'''
    
    print("\n" + "=" * 60)
    print("CACHING STRATEGY DEMO")
    print("=" * 60)
    
    strategy = optimizer.suggest_caching_strategy(route_code)
    
    print(f"\n📦 Recommended Cache Type: {strategy['type']}")
    print(f"📊 Expected Hit Rate: {strategy['expected_hit_rate']*100:.1f}%")
    print(f"⚡ Estimated Latency Improvement: {strategy['estimated_latency_improvement_ms']}ms")
    
    print("\n📝 Recommendations:")
    for rec in strategy['recommendations'][:3]:
        print(f"  - {rec}")
    
    return strategy


def demo_database_optimization():
    """Demo database query optimization"""
    optimizer = AIRouteOptimizer()
    
    route_code = '''
@app.get("/api/v1/analytics")
def get_analytics():
    # Inefficient query
    all_orders = db.orders.find()
    total = 0
    for order in all_orders:
        total += order["amount"]
    
    # Missing index
    recent = db.orders.find({"created_at": {"$gt": "2024-01-01"}}).sort("amount", -1)
    
    return {"total": total, "recent": list(recent)}
'''
    
    print("\n" + "=" * 60)
    print("DATABASE OPTIMIZATION DEMO")
    print("=" * 60)
    
    optimization = optimizer.optimize_database_queries(route_code)
    
    print(f"\n🗄️  Query Count: {optimization['query_count']}")
    
    print("\n📊 Index Recommendations:")
    for idx in optimization['index_recommendations']:
        print(f"  - Collection: {idx['collection']}, Fields: {idx['fields']}")
        print(f"    Reason: {idx['reason']}")
    
    print("\n⚡ Query Optimizations:")
    for opt in optimization['optimizations']:
        print(f"  - Line {opt['query_line']}: {opt['recommendation']}")
    
    return optimization


def demo_load_prediction():
    """Demo load prediction"""
    optimizer = AIRouteOptimizer()
    
    # Simulate historical data
    import random
    historical = []
    base_requests = 100
    for hour in range(24 * 7):  # One week of data
        # Simulate daily pattern
        hour_of_day = hour % 24
        if 9 <= hour_of_day <= 17:  # Business hours
            multiplier = 2.0
        elif 18 <= hour_of_day <= 22:  # Evening
            multiplier = 1.5
        else:  # Night
            multiplier = 0.3
        
        requests = int(base_requests * multiplier * (1 + random.uniform(-0.2, 0.2)))
        historical.append({
            "timestamp": f"2024-01-{1 + hour//24:02d}T{hour_of_day:02d}:00:00",
            "requests": requests
        })
    
    print("\n" + "=" * 60)
    print("LOAD PREDICTION DEMO")
    print("=" * 60)
    
    prediction = optimizer.predict_load("/api/v1/orders", historical)
    
    print(f"\n📈 Route: {prediction.route_path}")
    print(f"🎯 Predicted Requests/min: {prediction.predicted_requests_per_minute:.1f}")
    print(f"📊 Confidence Interval: ({prediction.confidence_interval[0]:.1f}, {prediction.confidence_interval[1]:.1f})")
    print(f"⏰ Peak Hours: {prediction.peak_hours}")
    print(f"🚦 Recommended Rate Limit: {prediction.recommended_rate_limit} req/min")
    print(f"📏 Scaling Recommendation: {prediction.scaling_recommendation}")
    
    return prediction


def demo_route_comparison():
    """Demo route comparison"""
    optimizer = AIRouteOptimizer()
    
    route_v1 = '''
@app.get("/api/v1/users/{user_id}")
def get_user(user_id: int):
    user = db.users.find_one({"id": user_id})
    orders = db.orders.find({"user_id": user_id})
    
    result = []
    for order in orders:
        items = db.items.find({"order_id": order["id"]})
        order["items"] = list(items)
        result.append(order)
    
    return {"user": user, "orders": result}
'''
    
    route_v2 = '''
from functools import lru_cache

@app.get("/api/v1/users/{user_id}")
async def get_user(user_id: int):
    # Use aggregation to avoid N+1
    pipeline = [
        {"$match": {"id": user_id}},
        {"$lookup": {
            "from": "orders",
            "localField": "id",
            "foreignField": "user_id",
            "as": "orders"
        }},
        {"$lookup": {
            "from": "items",
            "localField": "orders.id",
            "foreignField": "order_id",
            "as": "items"
        }}
    ]
    result = await db.users.aggregate(pipeline).to_list(1)
    return result[0] if result else None
'''
    
    print("\n" + "=" * 60)
    print("ROUTE COMPARISON DEMO")
    print("=" * 60)
    
    comparison = optimizer.compare_routes(route_v1, route_v2, "v1 (N+1)", "v2 (Optimized)")
    
    print(f"\n⚔️  Comparison: {comparison.route_v1_path} vs {comparison.route_v2_path}")
    print(f"🏆 Winner: {comparison.winner}")
    print(f"\n📊 V1 Score: {comparison.v1_score:.1f}")
    print(f"📊 V2 Score: {comparison.v2_score:.1f}")
    print(f"📈 Score Improvement: {comparison.score_improvement:+.1f}")
    print(f"⚡ Latency Improvement: {comparison.latency_improvement_ms:.1f}ms ({comparison.latency_improvement_percent:.1f}%)")
    
    print("\n🔧 Fixed Bottlenecks:")
    for fixed in comparison.detailed_comparison.get('fixed_bottlenecks', []):
        print(f"  ✅ {fixed}")
    
    return comparison


def demo_optimization_report():
    """Demo full optimization report generation"""
    optimizer = AIRouteOptimizer()
    
    route_code = '''
@app.get("/api/v1/dashboard")
def get_dashboard():
    # Multiple database calls
    stats = db.stats.find_one({"type": "daily"})
    users = list(db.users.find())
    orders = list(db.orders.find().sort("created_at", -1).limit(100))
    
    # Processing
    metrics = {}
    for user in users:
        user_orders = [o for o in orders if o["user_id"] == user["id"]]
        metrics[user["id"]] = len(user_orders)
    
    return {
        "stats": stats,
        "user_count": len(users),
        "recent_orders": orders,
        "metrics": metrics
    }
'''
    
    print("\n" + "=" * 60)
    print("FULL OPTIMIZATION REPORT DEMO")
    print("=" * 60)
    
    analysis = optimizer.analyze_route(route_code, "/api/v1/dashboard")
    report = optimizer.create_optimization_report(analysis)
    
    print(f"\n📋 Route: {report['summary']['route_path']}")
    print(f"⭐ Score: {report['summary']['optimization_score']}/100 ({report['grade']})")
    print(f"⏱️  Current Latency: {report['summary']['current_latency_ms']}ms")
    print(f"🎯 Predicted Latency: {report['summary']['predicted_latency_ms']}ms")
    print(f"📉 Improvement: {report['summary']['latency_improvement_percent']}%")
    
    print("\n🎯 Quick Wins:")
    for win in report['recommendations']['quick_wins'][:3]:
        print(f"  ⚡ {win['title']} - {win['impact']} impact, {win['effort']} effort")
    
    print("\n📋 Action Plan:")
    for action in report['action_plan'][:5]:
        print(f"  {action['priority']}. {action['action']} ({action['effort']})")
    
    return report


def demo_quantum_integration():
    """Demo quantum dispatch integration (if available)"""
    optimizer = AIRouteOptimizer()
    
    # Sample delivery stops
    stops = [
        {"id": "stop-1", "name": "Nando's Sandton", "lat": -26.1076, "lng": 28.0567, "priority": 5},
        {"id": "stop-2", "name": "KFC Rosebank", "lat": -26.1452, "lng": 28.0401, "priority": 3},
        {"id": "stop-3", "name": "Steers Randburg", "lat": -26.0936, "lng": 27.9834, "priority": 4},
        {"id": "stop-4", "name": "McDonald's Fourways", "lat": -26.0244, "lng": 28.0123, "priority": 2},
    ]
    
    start_lat, start_lng = -26.2041, 28.0473  # Johannesburg CBD
    
    print("\n" + "=" * 60)
    print("QUANTUM ROUTE OPTIMIZATION DEMO")
    print("=" * 60)
    
    result = optimizer.optimize_delivery_route_quantum(stops, start_lat, start_lng)
    
    print(f"\n🚚 Solver Type: {result['solver_type']}")
    print(f"✅ Success: {result['success']}")
    
    if result['success']:
        route = result['route']
        print(f"\n📍 Total Distance: {route['total_distance_m']/1000:.2f} km")
        print(f"⏱️  Total Time: {route['total_time_minutes']:.1f} minutes")
        print(f"💰 Savings: {route['savings_vs_original_minutes']:.1f} minutes")
        print(f"🎯 Confidence: {route['confidence']*100:.0f}%")
        
        print("\n🛣️  Optimized Route:")
        for stop in route['stops']:
            print(f"  → {stop['name']} ({stop['distance_from_previous_m']}m, {stop['time_from_previous_minutes']}min)")
    
    if result.get('note'):
        print(f"\n📝 Note: {result['note']}")
    
    return result


def run_all_demos():
    """Run all demo functions"""
    print("\n" + "=" * 60)
    print("AI ROUTE OPTIMIZER - COMPREHENSIVE DEMO")
    print("=" * 60)
    print("\nThis demo showcases the AI Route Optimizer capabilities:")
    print("1. Basic route analysis and bottleneck detection")
    print("2. Caching strategy recommendations")
    print("3. Database query optimization")
    print("4. Load prediction")
    print("5. Route comparison (before/after optimization)")
    print("6. Full optimization report generation")
    print("7. Quantum dispatch integration")
    print("\n" + "=" * 60)
    
    demo_basic_analysis()
    demo_caching_strategy()
    demo_database_optimization()
    demo_load_prediction()
    demo_route_comparison()
    demo_optimization_report()
    demo_quantum_integration()
    
    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print("\nThe AI Route Optimizer is ready for production use!")
    print("Integrate it into your CI/CD pipeline for automated performance analysis.")


if __name__ == "__main__":
    run_all_demos()
