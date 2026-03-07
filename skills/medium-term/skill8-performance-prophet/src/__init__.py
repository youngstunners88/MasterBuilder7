"""Performance Prophet - Predicts bottlenecks before deployment."""

__version__ = "1.0.0"
__author__ = "RobeetsDay Team"

from .profiler import Profiler, ProfileResult
from .query_analyzer import QueryAnalyzer, QueryIssue
from .predictor import BottleneckPredictor, ScalingPrediction
from .optimizer import Optimizer, OptimizationSuggestion

__all__ = [
    "Profiler",
    "ProfileResult",
    "QueryAnalyzer",
    "QueryIssue",
    "BottleneckPredictor",
    "ScalingPrediction",
    "Optimizer",
    "OptimizationSuggestion"
]