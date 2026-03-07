"""
AI Route Optimizer Agent

Analyzes and optimizes API routes for performance using AI-powered analysis.
Integrates with iHhashi's quantum dispatch system for delivery route optimization.

Usage:
    from ai_route_optimizer import AIRouteOptimizer
    
    optimizer = AIRouteOptimizer()
    analysis = optimizer.analyze_route(route_code, "/api/v1/orders")
    report = optimizer.create_optimization_report(analysis)
"""

from .ai_route_optimizer import (
    AIRouteOptimizer,
    RouteAnalysis,
    Bottleneck,
    Recommendation,
    LoadPrediction,
    ComparisonResult,
    OptimizationEffort,
    OptimizationImpact,
    BottleneckType,
)

__version__ = "1.0.0"
__author__ = "MasterBuilder7"

__all__ = [
    "AIRouteOptimizer",
    "RouteAnalysis",
    "Bottleneck",
    "Recommendation",
    "LoadPrediction",
    "ComparisonResult",
    "OptimizationEffort",
    "OptimizationImpact",
    "BottleneckType",
]
