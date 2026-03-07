"""
A/B Testing Framework for Agent Prompts and Strategies

This module provides a comprehensive A/B testing system for:
- Prompt variations
- Agent configurations
- Strategy comparisons
- Model comparisons

Features:
- Statistical significance testing
- Traffic allocation
- Automatic winner selection
- PostgreSQL + Redis storage
- Export capabilities

Author: MasterBuilder7
Version: 1.0.0
"""

import json
import uuid
import hashlib
import asyncio
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Callable, Tuple, Union
from enum import Enum
from collections import defaultdict
import math
import random
import statistics

# Statistical libraries (with fallback)
try:
    from scipy import stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    stats = None

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

# Database imports (optional)
try:
    import asyncpg
    import aioredis
    HAS_DB = True
except ImportError:
    HAS_DB = False
    asyncpg = None
    aioredis = None

from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """Status of an A/B test."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    STOPPED = "stopped"


class TestType(Enum):
    """Types of A/B tests supported."""
    PROMPT_VARIATION = "prompt_variation"
    AGENT_CONFIGURATION = "agent_configuration"
    STRATEGY_COMPARISON = "strategy_comparison"
    MODEL_COMPARISON = "model_comparison"


class MetricType(Enum):
    """Types of metrics that can be tracked."""
    SUCCESS_RATE = "success_rate"  # Binary: 0 or 1
    CONSENSUS_SCORE = "consensus_score"  # Continuous: 0.0 to 1.0
    TOKEN_USAGE = "token_usage"  # Integer: token count
    EXECUTION_TIME = "execution_time"  # Float: seconds
    ERROR_RATE = "error_rate"  # Binary: 0 or 1 (1 = error)
    USER_SATISFACTION = "user_satisfaction"  # Integer: 1-5 or 1-10
    COST = "cost"  # Float: monetary cost
    QUALITY_SCORE = "quality_score"  # Continuous: 0.0 to 1.0


@dataclass
class VariantConfig:
    """Configuration for a test variant."""
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    model: Optional[str] = None
    strategy: Optional[str] = None
    additional_params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_prompt": self.system_prompt,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "model": self.model,
            "strategy": self.strategy,
            "additional_params": self.additional_params
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VariantConfig":
        return cls(
            system_prompt=data.get("system_prompt"),
            temperature=data.get("temperature"),
            max_tokens=data.get("max_tokens"),
            model=data.get("model"),
            strategy=data.get("strategy"),
            additional_params=data.get("additional_params", {})
        )


@dataclass
class Variant:
    """Represents a variant in an A/B test."""
    variant_id: str
    name: str
    config: VariantConfig
    traffic_percentage: float  # 0.0 to 100.0
    description: Optional[str] = None
    is_control: bool = False
    
    # Runtime metrics (not persisted)
    _results: List["TestResult"] = field(default_factory=list, repr=False)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "name": self.name,
            "config": self.config.to_dict(),
            "traffic_percentage": self.traffic_percentage,
            "description": self.description,
            "is_control": self.is_control
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Variant":
        return cls(
            variant_id=data["variant_id"],
            name=data["name"],
            config=VariantConfig.from_dict(data["config"]),
            traffic_percentage=data["traffic_percentage"],
            description=data.get("description"),
            is_control=data.get("is_control", False)
        )
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Calculate summary statistics for this variant."""
        if not self._results:
            return {"count": 0}
        
        summary = {"count": len(self._results)}
        
        # Calculate metrics for each type
        for metric_type in MetricType:
            values = [r.metrics.get(metric_type.value) for r in self._results 
                     if metric_type.value in r.metrics and r.metrics[metric_type.value] is not None]
            
            if values:
                summary[metric_type.value] = {
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "std": statistics.stdev(values) if len(values) > 1 else 0,
                    "min": min(values),
                    "max": max(values),
                    "count": len(values)
                }
        
        return summary


@dataclass
class TestResult:
    """Result from a single execution of a variant."""
    result_id: str
    variant_id: str
    test_id: str
    metrics: Dict[str, Any]
    timestamp: datetime
    context: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "variant_id": self.variant_id,
            "test_id": self.test_id,
            "metrics": self.metrics,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestResult":
        return cls(
            result_id=data["result_id"],
            variant_id=data["variant_id"],
            test_id=data["test_id"],
            metrics=data["metrics"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            context=data.get("context"),
            session_id=data.get("session_id"),
            user_id=data.get("user_id"),
            metadata=data.get("metadata")
        )


@dataclass
class StatisticalAnalysis:
    """Statistical analysis results for a metric comparison."""
    metric_name: str
    control_mean: float
    treatment_mean: float
    difference: float
    relative_improvement: float  # Percentage
    p_value: float
    confidence_interval: Tuple[float, float]  # 95% CI
    cohens_d: float  # Effect size
    is_significant: bool
    sample_size_control: int
    sample_size_treatment: int
    power: float  # Statistical power
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "control_mean": self.control_mean,
            "treatment_mean": self.treatment_mean,
            "difference": self.difference,
            "relative_improvement": self.relative_improvement,
            "p_value": self.p_value,
            "confidence_interval": list(self.confidence_interval),
            "cohens_d": self.cohens_d,
            "is_significant": self.is_significant,
            "sample_size_control": self.sample_size_control,
            "sample_size_treatment": self.sample_size_treatment,
            "power": self.power
        }


@dataclass
class WinnerResult:
    """Result of winner determination."""
    winner_variant_id: Optional[str]
    confidence: float
    primary_metric: str
    improvement_percentage: float
    is_statistically_significant: bool
    recommendation: str
    analysis_by_metric: Dict[str, StatisticalAnalysis]
    should_stop_early: bool
    reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "winner_variant_id": self.winner_variant_id,
            "confidence": self.confidence,
            "primary_metric": self.primary_metric,
            "improvement_percentage": self.improvement_percentage,
            "is_statistically_significant": self.is_statistically_significant,
            "recommendation": self.recommendation,
            "analysis_by_metric": {k: v.to_dict() for k, v in self.analysis_by_metric.items()},
            "should_stop_early": self.should_stop_early,
            "reason": self.reason
        }


@dataclass
class TestReport:
    """Comprehensive report for an A/B test."""
    test_id: str
    test_name: str
    test_type: str
    status: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    hypothesis: str
    total_samples: int
    variant_summaries: Dict[str, Dict[str, Any]]
    winner: Optional[WinnerResult]
    statistical_analyses: List[StatisticalAnalysis]
    recommendations: List[str]
    export_urls: Optional[Dict[str, str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "test_type": self.test_type,
            "status": self.status,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "hypothesis": self.hypothesis,
            "total_samples": self.total_samples,
            "variant_summaries": self.variant_summaries,
            "winner": self.winner.to_dict() if self.winner else None,
            "statistical_analyses": [a.to_dict() for a in self.statistical_analyses],
            "recommendations": self.recommendations,
            "export_urls": self.export_urls
        }
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)


@dataclass
class ABTest:
    """Represents an A/B test."""
    test_id: str
    name: str
    test_type: TestType
    variants: List[Variant]
    status: TestStatus
    hypothesis: str
    primary_metric: str
    secondary_metrics: List[str]
    min_sample_size: int
    confidence_threshold: float
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "name": self.name,
            "test_type": self.test_type.value,
            "variants": [v.to_dict() for v in self.variants],
            "status": self.status.value,
            "hypothesis": self.hypothesis,
            "primary_metric": self.primary_metric,
            "secondary_metrics": self.secondary_metrics,
            "min_sample_size": self.min_sample_size,
            "confidence_threshold": self.confidence_threshold,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ABTest":
        return cls(
            test_id=data["test_id"],
            name=data["name"],
            test_type=TestType(data["test_type"]),
            variants=[Variant.from_dict(v) for v in data["variants"]],
            status=TestStatus(data["status"]),
            hypothesis=data["hypothesis"],
            primary_metric=data["primary_metric"],
            secondary_metrics=data.get("secondary_metrics", []),
            min_sample_size=data.get("min_sample_size", 100),
            confidence_threshold=data.get("confidence_threshold", 0.95),
            start_time=datetime.fromisoformat(data["start_time"]) if data.get("start_time") else None,
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
            created_by=data.get("created_by"),
            metadata=data.get("metadata", {})
        )
    
    def get_control_variant(self) -> Optional[Variant]:
        """Get the control variant."""
        for variant in self.variants:
            if variant.is_control:
                return variant
        # If no control marked, return first variant
        return self.variants[0] if self.variants else None
    
    def validate_traffic_allocation(self) -> Tuple[bool, str]:
        """Validate that traffic percentages sum to 100."""
        total = sum(v.traffic_percentage for v in self.variants)
        if abs(total - 100.0) > 0.01:
            return False, f"Traffic percentages sum to {total}, must equal 100"
        return True, "Valid"


class StatisticalCalculator:
    """Handles statistical calculations for A/B testing."""
    """Handles statistical calculations for A/B testing."""
    
    @staticmethod
    def _norm_ppf(p: float) -> float:
        """Approximation of inverse normal CDF (probit function)."""
        # Abramowitz and Stegun approximation
        if p <= 0 or p >= 1:
            return 0.0
        
        # Use scipy if available
        if HAS_SCIPY:
            return stats.norm.ppf(p)
        
        # Fallback approximation
        a1 = -3.969683028665376e+01
        a2 = 2.209460984245205e+02
        a3 = -2.759285104469687e+02
        a4 = 1.383577518672690e+02
        a5 = -3.066479806614716e+01
        a6 = 2.506628277459239e+00

        b1 = -5.447609879822406e+01
        b2 = 1.615858368580409e+02
        b3 = -1.556989798598866e+02
        b4 = 6.680131188771972e+01
        b5 = -1.328068155288572e+01

        c1 = -7.784894002430293e-03
        c2 = -3.223964580411365e-01
        c3 = -2.400758277161838e+00
        c4 = -2.549732539343734e+00
        c5 = 4.374664141464968e+00
        c6 = 2.938163982698783e+00

        d1 = 7.784695709041462e-03
        d2 = 3.224671290700398e-01
        d3 = 2.445134137142996e+00
        d4 = 3.754408661907416e+00

        p_low = 0.02425
        p_high = 1 - p_low

        if p < p_low:
            q = math.sqrt(-2 * math.log(p))
            x = (((((c1 * q + c2) * q + c3) * q + c4) * q + c5) * q + c6) / \
                ((((d1 * q + d2) * q + d3) * q + d4) * q + 1)
        elif p <= p_high:
            q = p - 0.5
            r = q * q
            x = (((((a1 * r + a2) * r + a3) * r + a4) * r + a5) * r + a6) * q / \
                (((((b1 * r + b2) * r + b3) * r + b4) * r + b5) * r + 1)
        else:
            q = math.sqrt(-2 * math.log(1 - p))
            x = -(((((c1 * q + c2) * q + c3) * q + c4) * q + c5) * q + c6) / \
                 ((((d1 * q + d2) * q + d3) * q + d4) * q + 1)
        
        return x

    @staticmethod
    def _t_cdf(t: float, df: int) -> float:
        """Approximation of Student's t CDF."""
        if HAS_SCIPY:
            return stats.t.cdf(t, df)
        
        # Fallback: approximate with normal for large df
        if df > 30:
            return 0.5 * (1 + math.erf(t / math.sqrt(2)))
        
        # Simple approximation for small df
        x = df / (df + t * t)
        # Incomplete beta approximation would go here
        return 0.5 * (1 + math.erf(t / math.sqrt(2)))  # Fallback to normal

    @staticmethod
    def _t_ppf(p: float, df: int) -> float:
        """Approximation of Student's t inverse CDF."""
        if HAS_SCIPY:
            return stats.t.ppf(p, df)
        
        # Approximate with normal for large df
        if df > 30:
            return StatisticalCalculator._norm_ppf(p)
        
        # Wilson-Hilferty approximation
        z = StatisticalCalculator._norm_ppf(p)
        t = z + (z**3 + z) / (4 * df) + (5*z**5 + 16*z**3 + 3*z) / (96 * df**2)
        return t

    @staticmethod
    def calculate_sample_size(
        baseline_rate: float,
        minimum_detectable_effect: float,
        alpha: float = 0.05,
        power: float = 0.8
    ) -> int:
        """
        Calculate required sample size per variant.
        
        Args:
            baseline_rate: Baseline conversion rate (0-1)
            minimum_detectable_effect: Relative effect size (e.g., 0.1 for 10%)
            alpha: Significance level (default 0.05)
            power: Statistical power (default 0.8)
        
        Returns:
            Required sample size per variant
        """
        # Z-scores for alpha and power
        z_alpha = StatisticalCalculator._norm_ppf(1 - alpha / 2)
        z_beta = StatisticalCalculator._norm_ppf(power)
        
        # Treatment rate
        treatment_rate = baseline_rate * (1 + minimum_detectable_effect)
        
        # Pooled probability
        p_pooled = (baseline_rate + treatment_rate) / 2
        
        # Sample size calculation
        numerator = (z_alpha * math.sqrt(2 * p_pooled * (1 - p_pooled)) +
                    z_beta * math.sqrt(baseline_rate * (1 - baseline_rate) + 
                                      treatment_rate * (1 - treatment_rate))) ** 2
        denominator = (treatment_rate - baseline_rate) ** 2
        
        if denominator == 0:
            return 100
        
        sample_size = math.ceil(numerator / denominator)
        return max(sample_size, 100)  # Minimum 100 samples
    
    @staticmethod
    def calculate_p_value(control_values: List[float], treatment_values: List[float]) -> float:
        """Calculate p-value using Welch's t-test."""
        if len(control_values) < 2 or len(treatment_values) < 2:
            return 1.0
        
        if HAS_SCIPY:
            # Welch's t-test (doesn't assume equal variances)
            _, p_value = stats.ttest_ind(control_values, treatment_values, equal_var=False)
            return float(p_value)
        
        # Manual Welch's t-test
        n1, n2 = len(control_values), len(treatment_values)
        mean1 = statistics.mean(control_values)
        mean2 = statistics.mean(treatment_values)
        var1 = statistics.variance(control_values) if n1 > 1 else 0
        var2 = statistics.variance(treatment_values) if n2 > 1 else 0
        
        # Standard error
        se1 = math.sqrt(var1 / n1)
        se2 = math.sqrt(var2 / n2)
        se_diff = math.sqrt(se1**2 + se2**2)
        
        if se_diff == 0:
            return 1.0
        
        # t-statistic
        t_stat = (mean1 - mean2) / se_diff
        
        # Degrees of freedom (Welch-Satterthwaite)
        numerator = (se1**2 + se2**2)**2
        denominator = (se1**4 / (n1 - 1)) + (se2**4 / (n2 - 1))
        df = numerator / denominator if denominator > 0 else n1 + n2 - 2
        
        # Two-tailed p-value
        p_value = 2 * (1 - StatisticalCalculator._t_cdf(abs(t_stat), int(df)))
        return max(0.0, min(1.0, p_value))
    
    @staticmethod
    def calculate_confidence_interval(
        control_values: List[float],
        treatment_values: List[float],
        confidence: float = 0.95
    ) -> Tuple[float, float]:
        """Calculate confidence interval for difference in means."""
        if len(control_values) < 2 or len(treatment_values) < 2:
            return (0.0, 0.0)
        
        mean_diff = statistics.mean(treatment_values) - statistics.mean(control_values)
        
        # Standard error
        se_control = statistics.stdev(control_values) / math.sqrt(len(control_values))
        se_treatment = statistics.stdev(treatment_values) / math.sqrt(len(treatment_values))
        se_diff = math.sqrt(se_control ** 2 + se_treatment ** 2)
        
        # Critical value
        df = len(control_values) + len(treatment_values) - 2
        t_critical = StatisticalCalculator._t_ppf((1 + confidence) / 2, df)
        
        margin = t_critical * se_diff
        return (mean_diff - margin, mean_diff + margin)
    
    @staticmethod
    def calculate_cohens_d(control_values: List[float], treatment_values: List[float]) -> float:
        """Calculate Cohen's d effect size."""
        if len(control_values) < 2 or len(treatment_values) < 2:
            return 0.0
        
        mean_control = statistics.mean(control_values)
        mean_treatment = statistics.mean(treatment_values)
        
        # Pooled standard deviation
        var_control = statistics.variance(control_values)
        var_treatment = statistics.variance(treatment_values)
        n1, n2 = len(control_values), len(treatment_values)
        pooled_std = math.sqrt(((n1 - 1) * var_control + (n2 - 1) * var_treatment) / (n1 + n2 - 2))
        
        if pooled_std == 0:
            return 0.0
        
        return (mean_treatment - mean_control) / pooled_std
    
    @staticmethod
    def calculate_power(control_values: List[float], treatment_values: List[float], alpha: float = 0.05) -> float:
        """Calculate statistical power post-hoc."""
        if len(control_values) < 2 or len(treatment_values) < 2:
            return 0.0
        
        effect_size = StatisticalCalculator.calculate_cohens_d(control_values, treatment_values)
        n1, n2 = len(control_values), len(treatment_values)
        
        if HAS_SCIPY:
            # Approximate power calculation using scipy
            try:
                analysis = stats.TTestIndPower()
                power = analysis.solve_power(effect_size=effect_size, nobs1=n1, alpha=alpha, ratio=n2/n1)
                return float(power)
            except:
                pass
        
        # Fallback power approximation
        # Power ≈ Φ(ES * √(n/2) - Z_(1-α/2))
        z_alpha = StatisticalCalculator._norm_ppf(1 - alpha / 2)
        n_avg = (n1 + n2) / 2
        z_power = effect_size * math.sqrt(n_avg / 2) - z_alpha
        power = 0.5 * (1 + math.erf(z_power / math.sqrt(2)))
        return max(0.0, min(1.0, power))
    
    @staticmethod
    def check_early_stopping(
        control_values: List[float],
        treatment_values: List[float],
        min_samples: int = 100,
        max_samples: int = 10000
    ) -> Tuple[bool, str]:
        """
        Check if test should stop early based on sequential testing.
        
        Returns:
            (should_stop, reason)
        """
        total_samples = len(control_values) + len(treatment_values)
        
        if total_samples < min_samples:
            return False, f"Need at least {min_samples} samples, have {total_samples}"
        
        if total_samples >= max_samples:
            return True, f"Reached maximum sample size ({max_samples})"
        
        # Check for significant effect
        p_value = StatisticalCalculator.calculate_p_value(control_values, treatment_values)
        
        # Sequential testing with alpha spending
        # Using O'Brien-Fleming-like spending function
        information_fraction = total_samples / max_samples
        alpha_boundary = 0.05 * math.sqrt(information_fraction)  # Conservative
        
        if p_value < alpha_boundary:
            cohens_d = StatisticalCalculator.calculate_cohens_d(control_values, treatment_values)
            if abs(cohens_d) > 0.5:  # Medium to large effect
                return True, f"Significant effect detected (p={p_value:.4f}, d={cohens_d:.2f})"
        
        # Check for futility (no chance of significance)
        if total_samples > min_samples * 2:
            ci = StatisticalCalculator.calculate_confidence_interval(control_values, treatment_values)
            if abs(ci[1] - ci[0]) < 0.01:  # Very narrow CI with no effect
                return True, "Futility: No meaningful effect likely"
        
        return False, "Continue testing"
    
    @staticmethod
    def analyze_metric(
        metric_name: str,
        control_values: List[float],
        treatment_values: List[float],
        confidence_threshold: float = 0.95
    ) -> StatisticalAnalysis:
        """Perform complete statistical analysis on a metric."""
        
        control_mean = statistics.mean(control_values) if control_values else 0
        treatment_mean = statistics.mean(treatment_values) if treatment_values else 0
        difference = treatment_mean - control_mean
        
        relative_improvement = ((treatment_mean - control_mean) / control_mean * 100) if control_mean != 0 else 0
        
        p_value = StatisticalCalculator.calculate_p_value(control_values, treatment_values)
        confidence_interval = StatisticalCalculator.calculate_confidence_interval(
            control_values, treatment_values, confidence_threshold
        )
        cohens_d = StatisticalCalculator.calculate_cohens_d(control_values, treatment_values)
        power = StatisticalCalculator.calculate_power(control_values, treatment_values)
        
        is_significant = p_value < (1 - confidence_threshold)
        
        return StatisticalAnalysis(
            metric_name=metric_name,
            control_mean=control_mean,
            treatment_mean=treatment_mean,
            difference=difference,
            relative_improvement=relative_improvement,
            p_value=p_value,
            confidence_interval=confidence_interval,
            cohens_d=cohens_d,
            is_significant=is_significant,
            sample_size_control=len(control_values),
            sample_size_treatment=len(treatment_values),
            power=power
        )


class MockStorage:
    """In-memory mock storage for testing without database."""
    
    def __init__(self):
        self._tests: Dict[str, ABTest] = {}
        self._results: Dict[str, List[TestResult]] = defaultdict(list)
        self._user_assignments: Dict[str, str] = {}
        self._counters: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    
    async def initialize(self):
        pass
    
    async def close(self):
        pass
    
    async def save_test(self, test: ABTest) -> bool:
        self._tests[test.test_id] = test
        return True
    
    async def get_test(self, test_id: str) -> Optional[ABTest]:
        return self._tests.get(test_id)
    
    async def list_tests(
        self,
        status: Optional[TestStatus] = None,
        test_type: Optional[TestType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ABTest]:
        tests = list(self._tests.values())
        if status:
            tests = [t for t in tests if t.status == status]
        if test_type:
            tests = [t for t in tests if t.test_type == test_type]
        return tests[offset:offset+limit]
    
    async def save_result(self, result: TestResult) -> bool:
        self._results[result.test_id].append(result)
        self._counters[result.test_id][result.variant_id] += 1
        return True
    
    async def get_results(
        self,
        test_id: str,
        variant_id: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[TestResult]:
        results = self._results.get(test_id, [])
        if variant_id:
            results = [r for r in results if r.variant_id == variant_id]
        if since:
            results = [r for r in results if r.timestamp > since]
        return results
    
    async def get_assignment_count(self, test_id: str, variant_id: str) -> int:
        return self._counters[test_id][variant_id]
    
    async def get_user_assignment(self, test_id: str, user_id: str) -> Optional[str]:
        return self._user_assignments.get(f"{test_id}:{user_id}")
    
    async def set_user_assignment(self, test_id: str, user_id: str, variant_id: str, ttl: int = 86400):
        self._user_assignments[f"{test_id}:{user_id}"] = variant_id
    
    async def export_to_csv(self, test_id: str, filepath: str) -> str:
        return filepath
    
    async def export_to_json(self, test_id: str, filepath: str) -> str:
        return filepath


class ABTestStorage:
    """Storage backend for A/B tests using PostgreSQL and Redis."""
    
    def __init__(
        self,
        postgres_dsn: str = "postgresql://localhost/ab_testing",
        redis_url: str = "redis://localhost:6379",
        fallback_to_mock: bool = True
    ):
        self.postgres_dsn = postgres_dsn
        self.redis_url = redis_url
        self.fallback_to_mock = fallback_to_mock
        self._pg_pool = None
        self._redis = None
        self._mock = None
    
    async def initialize(self):
        """Initialize database connections."""
        if not HAS_DB:
            if self.fallback_to_mock:
                logger.warning("Database libraries not available, using mock storage")
                self._mock = MockStorage()
                await self._mock.initialize()
                return
            else:
                raise RuntimeError("Database libraries (asyncpg, aioredis) not installed")
        
        # PostgreSQL
        self._pg_pool = await asyncpg.create_pool(self.postgres_dsn)
        await self._create_tables()
        
        # Redis
        self._redis = await aioredis.from_url(self.redis_url, decode_responses=True)
        
        logger.info("Storage initialized")
    
    def _is_mock(self) -> bool:
        return self._mock is not None
    
    async def close(self):
        """Close database connections."""
        if self._is_mock():
            await self._mock.close()
            return
        if self._pg_pool:
            await self._pg_pool.close()
        if self._redis:
            await self._redis.close()
    
    async def _create_tables(self):
        """Create necessary database tables."""
        async with self._pg_pool.acquire() as conn:
            # Tests table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ab_tests (
                    test_id VARCHAR(64) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    test_type VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'draft',
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
                )
            """)
            
            # Results table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ab_test_results (
                    result_id VARCHAR(64) PRIMARY KEY,
                    test_id VARCHAR(64) REFERENCES ab_tests(test_id),
                    variant_id VARCHAR(64) NOT NULL,
                    metrics JSONB NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    context JSONB,
                    session_id VARCHAR(100),
                    user_id VARCHAR(100),
                    metadata JSONB
                )
            """)
            
            # Indexes
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_results_test_id ON ab_test_results(test_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_results_variant_id ON ab_test_results(variant_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_results_timestamp ON ab_test_results(timestamp)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tests_status ON ab_tests(status)
            """)
    
    async def save_test(self, test: ABTest) -> bool:
        """Save or update an A/B test."""
        if self._is_mock():
            return await self._mock.save_test(test)
        async with self._pg_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO ab_tests (
                    test_id, name, test_type, status, hypothesis,
                    primary_metric, secondary_metrics, min_sample_size,
                    confidence_threshold, start_time, end_time,
                    created_at, updated_at, created_by, metadata, variants
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                ON CONFLICT (test_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    status = EXCLUDED.status,
                    hypothesis = EXCLUDED.hypothesis,
                    primary_metric = EXCLUDED.primary_metric,
                    secondary_metrics = EXCLUDED.secondary_metrics,
                    min_sample_size = EXCLUDED.min_sample_size,
                    confidence_threshold = EXCLUDED.confidence_threshold,
                    start_time = EXCLUDED.start_time,
                    end_time = EXCLUDED.end_time,
                    updated_at = EXCLUDED.updated_at,
                    metadata = EXCLUDED.metadata,
                    variants = EXCLUDED.variants
            """,
                test.test_id,
                test.name,
                test.test_type.value,
                test.status.value,
                test.hypothesis,
                test.primary_metric,
                json.dumps(test.secondary_metrics),
                test.min_sample_size,
                test.confidence_threshold,
                test.start_time,
                test.end_time,
                test.created_at or datetime.utcnow(),
                datetime.utcnow(),
                test.created_by,
                json.dumps(test.metadata),
                json.dumps([v.to_dict() for v in test.variants])
            )
        return True
    
    async def get_test(self, test_id: str) -> Optional[ABTest]:
        """Get an A/B test by ID."""
        if self._is_mock():
            return await self._mock.get_test(test_id)
        async with self._pg_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM ab_tests WHERE test_id = $1",
                test_id
            )
            
            if not row:
                return None
            
            return self._row_to_test(row)
    
    async def list_tests(
        self,
        status: Optional[TestStatus] = None,
        test_type: Optional[TestType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ABTest]:
        """List A/B tests with optional filtering."""
        if self._is_mock():
            return await self._mock.list_tests(status, test_type, limit, offset)
        async with self._pg_pool.acquire() as conn:
            query = "SELECT * FROM ab_tests WHERE 1=1"
            params = []
            
            if status:
                query += f" AND status = ${len(params) + 1}"
                params.append(status.value)
            
            if test_type:
                query += f" AND test_type = ${len(params) + 1}"
                params.append(test_type.value)
            
            query += f" ORDER BY created_at DESC LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
            params.extend([limit, offset])
            
            rows = await conn.fetch(query, *params)
            return [self._row_to_test(row) for row in rows]
    
    async def save_result(self, result: TestResult) -> bool:
        """Save a test result."""
        if self._is_mock():
            return await self._mock.save_result(result)
        async with self._pg_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO ab_test_results (
                    result_id, test_id, variant_id, metrics,
                    timestamp, context, session_id, user_id, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
                result.result_id,
                result.test_id,
                result.variant_id,
                json.dumps(result.metrics),
                result.timestamp,
                json.dumps(result.context) if result.context else None,
                result.session_id,
                result.user_id,
                json.dumps(result.metadata) if result.metadata else None
            )
        
        # Also update Redis counters for real-time tracking
        await self._redis.hincrby(f"test:{result.test_id}:counters", result.variant_id, 1)
        
        return True
    
    async def get_results(
        self,
        test_id: str,
        variant_id: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[TestResult]:
        """Get test results with optional filtering."""
        if self._is_mock():
            return await self._mock.get_results(test_id, variant_id, since)
        async with self._pg_pool.acquire() as conn:
            query = "SELECT * FROM ab_test_results WHERE test_id = $1"
            params = [test_id]
            
            if variant_id:
                query += f" AND variant_id = ${len(params) + 1}"
                params.append(variant_id)
            
            if since:
                query += f" AND timestamp > ${len(params) + 1}"
                params.append(since)
            
            query += " ORDER BY timestamp DESC"
            
            rows = await conn.fetch(query, *params)
            return [self._row_to_result(row) for row in rows]
    
    async def get_assignment_count(self, test_id: str, variant_id: str) -> int:
        """Get real-time assignment count from Redis."""
        if self._is_mock():
            return await self._mock.get_assignment_count(test_id, variant_id)
        count = await self._redis.hget(f"test:{test_id}:counters", variant_id)
        return int(count) if count else 0
    
    async def get_user_assignment(self, test_id: str, user_id: str) -> Optional[str]:
        """Get variant assignment for a user (sticky assignment)."""
        if self._is_mock():
            return await self._mock.get_user_assignment(test_id, user_id)
        return await self._redis.get(f"test:{test_id}:user:{user_id}")
    
    async def set_user_assignment(self, test_id: str, user_id: str, variant_id: str, ttl: int = 86400):
        """Set variant assignment for a user."""
        if self._is_mock():
            return await self._mock.set_user_assignment(test_id, user_id, variant_id, ttl)
        await self._redis.setex(f"test:{test_id}:user:{user_id}", ttl, variant_id)
    
    def _row_to_test(self, row: Any) -> ABTest:
        """Convert database row to ABTest object."""
        return ABTest(
            test_id=row["test_id"],
            name=row["name"],
            test_type=TestType(row["test_type"]),
            variants=[Variant.from_dict(v) for v in row["variants"]],
            status=TestStatus(row["status"]),
            hypothesis=row["hypothesis"],
            primary_metric=row["primary_metric"],
            secondary_metrics=row["secondary_metrics"],
            min_sample_size=row["min_sample_size"],
            confidence_threshold=row["confidence_threshold"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            created_by=row["created_by"],
            metadata=row["metadata"]
        )
    
    def _row_to_result(self, row: Any) -> TestResult:
        """Convert database row to TestResult object."""
        return TestResult(
            result_id=row["result_id"],
            test_id=row["test_id"],
            variant_id=row["variant_id"],
            metrics=row["metrics"],
            timestamp=row["timestamp"],
            context=row["context"],
            session_id=row["session_id"],
            user_id=row["user_id"],
            metadata=row["metadata"]
        )
    
    async def export_to_csv(self, test_id: str, filepath: str) -> str:
        """Export test results to CSV."""
        if self._is_mock():
            return await self._mock.export_to_csv(test_id, filepath)
        import csv
        
        results = await self.get_results(test_id)
        
        if not results:
            return filepath
        
        # Get all metric keys
        all_metrics = set()
        for r in results:
            all_metrics.update(r.metrics.keys())
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            header = ['result_id', 'variant_id', 'timestamp', 'session_id', 'user_id']
            header.extend(sorted(all_metrics))
            writer.writerow(header)
            
            # Data
            for r in results:
                row = [
                    r.result_id,
                    r.variant_id,
                    r.timestamp.isoformat(),
                    r.session_id or '',
                    r.user_id or ''
                ]
                for metric in sorted(all_metrics):
                    row.append(r.metrics.get(metric, ''))
                writer.writerow(row)
        
        return filepath
    
    async def export_to_json(self, test_id: str, filepath: str) -> str:
        """Export test results to JSON."""
        if self._is_mock():
            return await self._mock.export_to_json(test_id, filepath)
        results = await self.get_results(test_id)
        
        data = {
            "test_id": test_id,
            "exported_at": datetime.utcnow().isoformat(),
            "total_results": len(results),
            "results": [r.to_dict() for r in results]
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        return filepath


class ABTestFramework:
    """
    Main A/B Testing Framework for agent prompts and strategies.
    
    Features:
    - Test creation and management
    - Traffic allocation with sticky assignments
    - Result collection and statistical analysis
    - Automatic winner determination
    - Early stopping criteria
    - PostgreSQL + Redis storage
    """
    
    def __init__(
        self,
        postgres_dsn: str = "postgresql://localhost/ab_testing",
        redis_url: str = "redis://localhost:6379"
    ):
        self.storage = ABTestStorage(postgres_dsn, redis_url)
        self.calculator = StatisticalCalculator()
        self._initialized = False
        
        # In-memory cache for active tests
        self._active_tests: Dict[str, ABTest] = {}
    
    async def initialize(self):
        """Initialize the framework."""
        await self.storage.initialize()
        self._initialized = True
        
        # Load active tests into memory
        active_tests = await self.storage.list_tests(status=TestStatus.RUNNING)
        for test in active_tests:
            self._active_tests[test.test_id] = test
        
        logger.info(f"AB Test Framework initialized with {len(active_tests)} active tests")
    
    async def close(self):
        """Close the framework."""
        await self.storage.close()
        self._initialized = False
    
    def _generate_id(self) -> str:
        """Generate a unique ID."""
        return hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:16]
    
    async def create_test(
        self,
        name: str,
        test_type: TestType,
        variants: List[Dict[str, Any]],
        hypothesis: str,
        primary_metric: str = "success_rate",
        secondary_metrics: Optional[List[str]] = None,
        min_sample_size: Optional[int] = None,
        confidence_threshold: float = 0.95,
        created_by: Optional[str] = None,
        auto_start: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ABTest:
        """
        Create a new A/B test.
        
        Args:
            name: Human-readable test name
            test_type: Type of test (prompt, config, strategy, model)
            variants: List of variant configs with keys: name, config, traffic_percentage, [description], [is_control]
            hypothesis: The hypothesis being tested
            primary_metric: Primary metric for winner determination
            secondary_metrics: Additional metrics to track
            min_sample_size: Minimum samples before winner can be determined (auto-calculated if None)
            confidence_threshold: Statistical confidence threshold (default 0.95)
            created_by: User/system creating the test
            auto_start: Whether to start the test immediately
            metadata: Additional test metadata
        
        Returns:
            Created ABTest object
        """
        if not self._initialized:
            raise RuntimeError("Framework not initialized. Call initialize() first.")
        
        # Validate variants
        if len(variants) < 2:
            raise ValueError("At least 2 variants required")
        
        # Build variant objects
        variant_objects = []
        has_control = False
        
        for i, v in enumerate(variants):
            variant = Variant(
                variant_id=self._generate_id(),
                name=v["name"],
                config=VariantConfig.from_dict(v["config"]),
                traffic_percentage=v["traffic_percentage"],
                description=v.get("description"),
                is_control=v.get("is_control", i == 0)  # First variant is control by default
            )
            if variant.is_control:
                has_control = True
            variant_objects.append(variant)
        
        # Ensure exactly one control
        if not has_control:
            variant_objects[0].is_control = True
        
        # Validate traffic allocation
        total_traffic = sum(v.traffic_percentage for v in variant_objects)
        if abs(total_traffic - 100.0) > 0.01:
            raise ValueError(f"Traffic percentages must sum to 100, got {total_traffic}")
        
        # Calculate minimum sample size if not provided
        if min_sample_size is None:
            # Assume baseline success rate of 0.5, looking for 10% improvement
            min_sample_size = self.calculator.calculate_sample_size(
                baseline_rate=0.5,
                minimum_detectable_effect=0.1
            )
        
        test = ABTest(
            test_id=self._generate_id(),
            name=name,
            test_type=test_type,
            variants=variant_objects,
            status=TestStatus.RUNNING if auto_start else TestStatus.DRAFT,
            hypothesis=hypothesis,
            primary_metric=primary_metric,
            secondary_metrics=secondary_metrics or [],
            min_sample_size=min_sample_size,
            confidence_threshold=confidence_threshold,
            start_time=datetime.utcnow() if auto_start else None,
            created_at=datetime.utcnow(),
            created_by=created_by,
            metadata=metadata or {}
        )
        
        # Save to database
        await self.storage.save_test(test)
        
        if auto_start:
            self._active_tests[test.test_id] = test
        
        logger.info(f"Created test {test.test_id}: {name}")
        return test
    
    async def start_test(self, test_id: str) -> ABTest:
        """Start a draft test."""
        test = await self.storage.get_test(test_id)
        if not test:
            raise ValueError(f"Test {test_id} not found")
        
        if test.status != TestStatus.DRAFT:
            raise ValueError(f"Cannot start test with status {test.status}")
        
        test.status = TestStatus.RUNNING
        test.start_time = datetime.utcnow()
        test.updated_at = datetime.utcnow()
        
        await self.storage.save_test(test)
        self._active_tests[test_id] = test
        
        logger.info(f"Started test {test_id}")
        return test
    
    async def assign_variant(
        self,
        test_id: str,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Variant:
        """
        Assign a variant for a test session.
        
        Uses consistent hashing for sticky assignments when user_id is provided.
        Otherwise uses weighted random selection based on traffic percentages.
        
        Args:
            test_id: The test ID
            context: Additional context for assignment (can influence bucketing)
            user_id: User ID for sticky assignment
            session_id: Session ID for tracking
        
        Returns:
            Assigned Variant
        """
        # Check cache first
        if test_id in self._active_tests:
            test = self._active_tests[test_id]
        else:
            test = await self.storage.get_test(test_id)
            if test and test.status == TestStatus.RUNNING:
                self._active_tests[test_id] = test
        
        if not test:
            raise ValueError(f"Test {test_id} not found")
        
        if test.status != TestStatus.RUNNING:
            raise ValueError(f"Test {test_id} is not running (status: {test.status.value})")
        
        # Check for sticky assignment
        if user_id:
            cached_variant_id = await self.storage.get_user_assignment(test_id, user_id)
            if cached_variant_id:
                for variant in test.variants:
                    if variant.variant_id == cached_variant_id:
                        return variant
        
        # Weighted random selection
        rand = random.random() * 100
        cumulative = 0
        
        for variant in test.variants:
            cumulative += variant.traffic_percentage
            if rand <= cumulative:
                # Cache assignment
                if user_id:
                    await self.storage.set_user_assignment(test_id, user_id, variant.variant_id)
                return variant
        
        # Fallback to last variant
        return test.variants[-1]
    
    async def record_result(
        self,
        test_id: str,
        variant_id: str,
        metrics: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TestResult:
        """
        Record a result for a variant.
        
        Args:
            test_id: The test ID
            variant_id: The variant ID
            metrics: Dictionary of metric values
            context: Context of the execution
            session_id: Session ID
            user_id: User ID
            metadata: Additional metadata
        
        Returns:
            Created TestResult
        """
        result = TestResult(
            result_id=self._generate_id(),
            variant_id=variant_id,
            test_id=test_id,
            metrics=metrics,
            timestamp=datetime.utcnow(),
            context=context,
            session_id=session_id,
            user_id=user_id,
            metadata=metadata
        )
        
        await self.storage.save_result(result)
        
        # Update in-memory cache
        if test_id in self._active_tests:
            for variant in self._active_tests[test_id].variants:
                if variant.variant_id == variant_id:
                    variant._results.append(result)
                    break
        
        logger.debug(f"Recorded result for test {test_id}, variant {variant_id}")
        return result
    
    async def analyze_results(self, test_id: str) -> List[StatisticalAnalysis]:
        """
        Perform statistical analysis on all metrics for a test.
        
        Returns:
            List of StatisticalAnalysis objects for each metric
        """
        test = await self.storage.get_test(test_id)
        if not test:
            raise ValueError(f"Test {test_id} not found")
        
        # Load results
        results = await self.storage.get_results(test_id)
        
        if not results:
            return []
        
        # Group by variant
        results_by_variant: Dict[str, List[TestResult]] = defaultdict(list)
        for r in results:
            results_by_variant[r.variant_id].append(r)
        
        # Find control variant
        control_variant = test.get_control_variant()
        if not control_variant:
            raise ValueError("No control variant found")
        
        control_results = results_by_variant.get(control_variant.variant_id, [])
        
        # Analyze each metric
        analyses = []
        all_metrics = set()
        for r in results:
            all_metrics.update(r.metrics.keys())
        
        for metric in all_metrics:
            control_values = [r.metrics[metric] for r in control_results 
                            if metric in r.metrics and r.metrics[metric] is not None]
            
            for variant in test.variants:
                if variant.is_control:
                    continue
                
                treatment_results = results_by_variant.get(variant.variant_id, [])
                treatment_values = [r.metrics[metric] for r in treatment_results 
                                   if metric in r.metrics and r.metrics[metric] is not None]
                
                if len(control_values) >= 2 and len(treatment_values) >= 2:
                    analysis = self.calculator.analyze_metric(
                        metric_name=metric,
                        control_values=control_values,
                        treatment_values=treatment_values,
                        confidence_threshold=test.confidence_threshold
                    )
                    analyses.append(analysis)
        
        return analyses
    
    async def determine_winner(
        self,
        test_id: str,
        confidence_threshold: Optional[float] = None
    ) -> WinnerResult:
        """
        Determine the winning variant for a test.
        
        Args:
            test_id: The test ID
            confidence_threshold: Override confidence threshold
        
        Returns:
            WinnerResult with winner details and recommendations
        """
        test = await self.storage.get_test(test_id)
        if not test:
            raise ValueError(f"Test {test_id} not found")
        
        threshold = confidence_threshold or test.confidence_threshold
        
        # Load results
        results = await self.storage.get_results(test_id)
        
        if not results:
            return WinnerResult(
                winner_variant_id=None,
                confidence=0.0,
                primary_metric=test.primary_metric,
                improvement_percentage=0.0,
                is_statistically_significant=False,
                recommendation="No results available yet",
                analysis_by_metric={},
                should_stop_early=False,
                reason="Insufficient data"
            )
        
        # Group by variant
        results_by_variant: Dict[str, List[TestResult]] = defaultdict(list)
        for r in results:
            results_by_variant[r.variant_id].append(r)
        
        # Get control
        control_variant = test.get_control_variant()
        control_results = results_by_variant.get(control_variant.variant_id, [])
        control_count = len(control_results)
        
        # Check minimum sample size
        total_samples = sum(len(v) for v in results_by_variant.values())
        if total_samples < test.min_sample_size:
            return WinnerResult(
                winner_variant_id=None,
                confidence=0.0,
                primary_metric=test.primary_metric,
                improvement_percentage=0.0,
                is_statistically_significant=False,
                recommendation=f"Need at least {test.min_sample_size} samples, have {total_samples}",
                analysis_by_metric={},
                should_stop_early=False,
                reason=f"Insufficient sample size ({total_samples}/{test.min_sample_size})"
            )
        
        # Analyze primary metric
        control_values = [r.metrics.get(test.primary_metric) for r in control_results 
                         if test.primary_metric in r.metrics and r.metrics[test.primary_metric] is not None]
        
        analysis_by_metric = {}
        best_variant = None
        best_improvement = -float('inf')
        should_stop = False
        
        for variant in test.variants:
            if variant.is_control:
                continue
            
            treatment_results = results_by_variant.get(variant.variant_id, [])
            treatment_values = [r.metrics.get(test.primary_metric) for r in treatment_results 
                              if test.primary_metric in r.metrics and r.metrics[test.primary_metric] is not None]
            
            if len(control_values) >= 2 and len(treatment_values) >= 2:
                analysis = self.calculator.analyze_metric(
                    metric_name=test.primary_metric,
                    control_values=control_values,
                    treatment_values=treatment_values,
                    confidence_threshold=threshold
                )
                analysis_by_metric[variant.variant_id] = analysis
                
                if analysis.relative_improvement > best_improvement:
                    best_improvement = analysis.relative_improvement
                    best_variant = variant
                
                # Check early stopping
                stop, reason = self.calculator.check_early_stopping(
                    control_values, treatment_values,
                    min_samples=test.min_sample_size
                )
                if stop:
                    should_stop = True
        
        # Determine winner
        if best_variant and test.primary_metric in [a.metric_name for a in analysis_by_metric.values()]:
            best_analysis = [a for a in analysis_by_metric.values() 
                           if a.metric_name == test.primary_metric][0]
            
            is_significant = best_analysis.is_significant
            
            if is_significant and best_improvement > 0:
                recommendation = (
                    f"Variant '{best_variant.name}' is the winner with "
                    f"{best_improvement:.1f}% improvement in {test.primary_metric} "
                    f"(p={best_analysis.p_value:.4f}, d={best_analysis.cohens_d:.2f}). "
                    f"Roll out to 100% traffic."
                )
            elif is_significant and best_improvement < 0:
                recommendation = (
                    f"Control variant is significantly better. "
                    f"Treatment performed {abs(best_improvement):.1f}% worse. "
                    f"Keep control or investigate issues."
                )
                best_variant = control_variant
                best_improvement = 0
            else:
                recommendation = (
                    f"No significant winner yet. Best variant '{best_variant.name}' shows "
                    f"{best_improvement:.1f}% improvement but not statistically significant "
                    f"(p={best_analysis.p_value:.4f}). Continue testing."
                )
            
            return WinnerResult(
                winner_variant_id=best_variant.variant_id if is_significant and best_improvement > 0 else None,
                confidence=best_analysis.power if is_significant else 0.0,
                primary_metric=test.primary_metric,
                improvement_percentage=best_improvement,
                is_statistically_significant=is_significant,
                recommendation=recommendation,
                analysis_by_metric={test.primary_metric: best_analysis},
                should_stop_early=should_stop and is_significant,
                reason="Significant result detected" if should_stop else None
            )
        
        return WinnerResult(
            winner_variant_id=None,
            confidence=0.0,
            primary_metric=test.primary_metric,
            improvement_percentage=0.0,
            is_statistically_significant=False,
            recommendation="Insufficient data for analysis",
            analysis_by_metric=analysis_by_metric,
            should_stop_early=False,
            reason="No comparable data"
        )
    
    async def stop_test(
        self,
        test_id: str,
        reason: str,
        winner_variant_id: Optional[str] = None
    ) -> ABTest:
        """
        Stop a running test.
        
        Args:
            test_id: The test ID
            reason: Reason for stopping
            winner_variant_id: Optional winner to declare
        
        Returns:
            Updated ABTest
        """
        test = await self.storage.get_test(test_id)
        if not test:
            raise ValueError(f"Test {test_id} not found")
        
        test.status = TestStatus.COMPLETED if winner_variant_id else TestStatus.STOPPED
        test.end_time = datetime.utcnow()
        test.updated_at = datetime.utcnow()
        test.metadata["stop_reason"] = reason
        test.metadata["winner_variant_id"] = winner_variant_id
        
        await self.storage.save_test(test)
        
        if test_id in self._active_tests:
            del self._active_tests[test_id]
        
        logger.info(f"Stopped test {test_id}: {reason}")
        return test
    
    async def get_test_report(self, test_id: str, include_exports: bool = False) -> TestReport:
        """
        Generate a comprehensive test report.
        
        Args:
            test_id: The test ID
            include_exports: Whether to generate CSV/JSON exports
        
        Returns:
            TestReport object
        """
        test = await self.storage.get_test(test_id)
        if not test:
            raise ValueError(f"Test {test_id} not found")
        
        # Load results
        results = await self.storage.get_results(test_id)
        total_samples = len(results)
        
        # Build variant summaries
        variant_summaries = {}
        results_by_variant: Dict[str, List[TestResult]] = defaultdict(list)
        
        for r in results:
            results_by_variant[r.variant_id].append(r)
        
        for variant in test.variants:
            variant_results = results_by_variant.get(variant.variant_id, [])
            
            # Calculate metrics
            metrics_summary = {"count": len(variant_results)}
            
            all_metrics = set()
            for r in variant_results:
                all_metrics.update(r.metrics.keys())
            
            for metric in all_metrics:
                values = [r.metrics[metric] for r in variant_results 
                         if metric in r.metrics and r.metrics[metric] is not None]
                if values:
                    metrics_summary[metric] = {
                        "mean": statistics.mean(values),
                        "median": statistics.median(values),
                        "std": statistics.stdev(values) if len(values) > 1 else 0,
                        "min": min(values),
                        "max": max(values),
                        "count": len(values)
                    }
            
            variant_summaries[variant.variant_id] = {
                "name": variant.name,
                "is_control": variant.is_control,
                "traffic_percentage": variant.traffic_percentage,
                "metrics": metrics_summary
            }
        
        # Statistical analysis
        analyses = await self.analyze_results(test_id)
        
        # Determine winner
        winner = await self.determine_winner(test_id)
        
        # Generate recommendations
        recommendations = []
        
        if winner.is_statistically_significant and winner.winner_variant_id:
            winner_name = variant_summaries.get(winner.winner_variant_id, {}).get("name", "Unknown")
            recommendations.append(
                f"Roll out variant '{winner_name}' to 100% traffic "
                f"({winner.improvement_percentage:.1f}% improvement)"
            )
        elif not winner.is_statistically_significant and total_samples >= test.min_sample_size:
            recommendations.append(
                f"No significant difference detected after {total_samples} samples. "
                f"Consider stopping the test and keeping the control variant."
            )
        elif total_samples < test.min_sample_size:
            remaining = test.min_sample_size - total_samples
            recommendations.append(
                f"Continue testing. Need {remaining} more samples to reach statistical significance."
            )
        
        # Check for data quality issues
        for variant_id, summary in variant_summaries.items():
            if summary["metrics"]["count"] == 0:
                recommendations.append(
                    f"Warning: Variant '{summary['name']}' has no recorded results"
                )
        
        # Exports
        export_urls = None
        if include_exports:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            csv_path = f"/tmp/ab_test_{test_id}_{timestamp}.csv"
            json_path = f"/tmp/ab_test_{test_id}_{timestamp}.json"
            
            await self.storage.export_to_csv(test_id, csv_path)
            await self.storage.export_to_json(test_id, json_path)
            
            export_urls = {
                "csv": csv_path,
                "json": json_path
            }
        
        return TestReport(
            test_id=test.test_id,
            test_name=test.name,
            test_type=test.test_type.value,
            status=test.status.value,
            start_time=test.start_time,
            end_time=test.end_time,
            hypothesis=test.hypothesis,
            total_samples=total_samples,
            variant_summaries=variant_summaries,
            winner=winner,
            statistical_analyses=analyses,
            recommendations=recommendations,
            export_urls=export_urls
        )
    
    async def list_active_tests(self) -> List[ABTest]:
        """List all currently running tests."""
        return list(self._active_tests.values())
    
    async def list_all_tests(
        self,
        status: Optional[TestStatus] = None,
        test_type: Optional[TestType] = None,
        limit: int = 100
    ) -> List[ABTest]:
        """List all tests with optional filtering."""
        return await self.storage.list_tests(status, test_type, limit)
    
    async def pause_test(self, test_id: str) -> ABTest:
        """Pause a running test."""
        test = await self.storage.get_test(test_id)
        if not test:
            raise ValueError(f"Test {test_id} not found")
        
        if test.status != TestStatus.RUNNING:
            raise ValueError(f"Cannot pause test with status {test.status}")
        
        test.status = TestStatus.PAUSED
        test.updated_at = datetime.utcnow()
        
        await self.storage.save_test(test)
        
        if test_id in self._active_tests:
            del self._active_tests[test_id]
        
        return test
    
    async def resume_test(self, test_id: str) -> ABTest:
        """Resume a paused test."""
        test = await self.storage.get_test(test_id)
        if not test:
            raise ValueError(f"Test {test_id} not found")
        
        if test.status != TestStatus.PAUSED:
            raise ValueError(f"Cannot resume test with status {test.status}")
        
        test.status = TestStatus.RUNNING
        test.updated_at = datetime.utcnow()
        
        await self.storage.save_test(test)
        self._active_tests[test_id] = test
        
        return test
    
    async def calculate_required_sample_size(
        self,
        baseline_rate: float,
        minimum_detectable_effect: float,
        alpha: float = 0.05,
        power: float = 0.8
    ) -> int:
        """
        Calculate required sample size for a test.
        
        Args:
            baseline_rate: Expected baseline conversion/success rate (0-1)
            minimum_detectable_effect: Minimum effect size to detect (e.g., 0.1 for 10%)
            alpha: Significance level (default 0.05)
            power: Statistical power (default 0.8)
        
        Returns:
            Required sample size per variant
        """
        return self.calculator.calculate_sample_size(
            baseline_rate, minimum_detectable_effect, alpha, power
        )


# ============================================================================
# DEMO / TEST CODE
# ============================================================================

async def run_demo():
    """Run a demonstration of the A/B testing framework."""
    
    print("=" * 80)
    print("A/B Testing Framework Demo")
    print("=" * 80)
    
    # Initialize framework (using in-memory simulation for demo)
    framework = ABTestFramework(
        postgres_dsn="postgresql://localhost/ab_testing",
        redis_url="redis://localhost:6379"
    )
    
    try:
        await framework.initialize()
    except Exception as e:
        print(f"Note: Database not available, running in simulation mode")
        # Create mock storage for demo
        framework._initialized = True
    
    print("\n" + "=" * 80)
    print("1. Creating A/B Test: Prompt Variations")
    print("=" * 80)
    
    # Create a prompt variation test
    test = await framework.create_test(
        name="Code Review Prompt Optimization",
        test_type=TestType.PROMPT_VARIATION,
        variants=[
            {
                "name": "Control - Standard Prompt",
                "config": {
                    "system_prompt": "You are a code reviewer. Review the code and provide feedback.",
                    "temperature": 0.7,
                    "max_tokens": 1000
                },
                "traffic_percentage": 50.0,
                "description": "Current production prompt",
                "is_control": True
            },
            {
                "name": "Treatment - Structured Prompt",
                "config": {
                    "system_prompt": """You are an expert code reviewer. Analyze the code systematically:
1. Check for bugs and logical errors
2. Review code style and best practices
3. Evaluate performance implications
4. Provide specific, actionable feedback

Format your response as:
- Summary
- Issues (if any)
- Suggestions
- Overall Rating (1-10)""",
                    "temperature": 0.5,
                    "max_tokens": 1500
                },
                "traffic_percentage": 50.0,
                "description": "More structured prompt with specific instructions"
            }
        ],
        hypothesis="A structured prompt with specific instructions will yield higher quality code reviews (measured by consensus score)",
        primary_metric="consensus_score",
        secondary_metrics=["success_rate", "token_usage", "execution_time"],
        min_sample_size=200,
        confidence_threshold=0.95,
        created_by="demo_system",
        auto_start=True,
        metadata={
            "domain": "code_review",
            "team": "ai_platform",
            "priority": "high"
        }
    )
    
    print(f"Test created: {test.test_id}")
    print(f"Name: {test.name}")
    print(f"Type: {test.test_type.value}")
    print(f"Hypothesis: {test.hypothesis}")
    print(f"Primary Metric: {test.primary_metric}")
    print(f"Min Sample Size: {test.min_sample_size}")
    print(f"Status: {test.status.value}")
    
    print("\nVariants:")
    for v in test.variants:
        print(f"  - {v.name} ({v.traffic_percentage}% traffic, control={v.is_control})")
    
    print("\n" + "=" * 80)
    print("2. Simulating Traffic and Results")
    print("=" * 80)
    
    # Simulate traffic
    num_sessions = 250
    
    for i in range(num_sessions):
        # Assign variant
        variant = await framework.assign_variant(
            test_id=test.test_id,
            user_id=f"user_{i % 100}",  # 100 unique users
            session_id=f"session_{i}"
        )
        
        # Simulate metrics based on variant
        # Treatment should perform slightly better
        if variant.is_control:
            consensus_score = random.gauss(0.72, 0.15)  # Mean 0.72
            success_rate = 1 if random.random() < 0.85 else 0
            token_usage = random.gauss(850, 100)
            execution_time = random.gauss(2.5, 0.5)
        else:
            consensus_score = random.gauss(0.81, 0.12)  # Mean 0.81 (better!)
            success_rate = 1 if random.random() < 0.90 else 0
            token_usage = random.gauss(1100, 120)  # More tokens due to structure
            execution_time = random.gauss(2.8, 0.4)
        
        # Clamp values
        consensus_score = max(0.0, min(1.0, consensus_score))
        token_usage = max(100, int(token_usage))
        execution_time = max(0.1, execution_time)
        
        # Record result
        await framework.record_result(
            test_id=test.test_id,
            variant_id=variant.variant_id,
            metrics={
                "consensus_score": round(consensus_score, 3),
                "success_rate": success_rate,
                "token_usage": token_usage,
                "execution_time": round(execution_time, 3)
            },
            session_id=f"session_{i}",
            user_id=f"user_{i % 100}",
            context={"task_type": "code_review", "language": "python"}
        )
        
        if (i + 1) % 50 == 0:
            print(f"  Recorded {i + 1} results...")
    
    print(f"\nTotal results recorded: {num_sessions}")
    
    print("\n" + "=" * 80)
    print("3. Analyzing Results")
    print("=" * 80)
    
    # Get variant summaries
    for variant in test.variants:
        results = await framework.storage.get_results(test.test_id, variant.variant_id)
        if results:
            summary = variant.get_metrics_summary()
            print(f"\n{variant.name}:")
            print(f"  Samples: {summary['count']}")
            for metric, stats in summary.items():
                if metric != "count":
                    print(f"  {metric}: mean={stats['mean']:.3f}, std={stats['std']:.3f}")
    
    print("\n" + "=" * 80)
    print("4. Statistical Analysis")
    print("=" * 80)
    
    analyses = await framework.analyze_results(test.test_id)
    
    for analysis in analyses:
        print(f"\nMetric: {analysis.metric_name}")
        print(f"  Control mean: {analysis.control_mean:.4f}")
        print(f"  Treatment mean: {analysis.treatment_mean:.4f}")
        print(f"  Difference: {analysis.difference:.4f}")
        print(f"  Relative improvement: {analysis.relative_improvement:.2f}%")
        print(f"  P-value: {analysis.p_value:.6f}")
        print(f"  95% CI: [{analysis.confidence_interval[0]:.4f}, {analysis.confidence_interval[1]:.4f}]")
        print(f"  Cohen's d: {analysis.cohens_d:.4f}")
        print(f"  Statistically significant: {analysis.is_significant}")
        print(f"  Statistical power: {analysis.power:.2f}")
    
    print("\n" + "=" * 80)
    print("5. Winner Determination")
    print("=" * 80)
    
    winner = await framework.determine_winner(test.test_id)
    
    print(f"Winner Variant ID: {winner.winner_variant_id}")
    print(f"Confidence: {winner.confidence:.2%}")
    print(f"Primary Metric: {winner.primary_metric}")
    print(f"Improvement: {winner.improvement_percentage:.2f}%")
    print(f"Statistically Significant: {winner.is_statistically_significant}")
    print(f"Should Stop Early: {winner.should_stop_early}")
    print(f"\nRecommendation: {winner.recommendation}")
    
    print("\n" + "=" * 80)
    print("6. Full Test Report")
    print("=" * 80)
    
    report = await framework.get_test_report(test.test_id, include_exports=True)
    
    print(f"\nTest: {report.test_name}")
    print(f"Status: {report.status}")
    print(f"Total Samples: {report.total_samples}")
    print(f"\nVariant Summaries:")
    for vid, summary in report.variant_summaries.items():
        print(f"  {summary['name']}: n={summary['metrics']['count']}")
    
    print(f"\nRecommendations:")
    for rec in report.recommendations:
        print(f"  - {rec}")
    
    if report.export_urls:
        print(f"\nExports:")
        for fmt, path in report.export_urls.items():
            print(f"  - {fmt.upper()}: {path}")
    
    print("\n" + "=" * 80)
    print("7. Stopping Test")
    print("=" * 80)
    
    if winner.is_statistically_significant:
        final_test = await framework.stop_test(
            test_id=test.test_id,
            reason="Statistically significant winner determined",
            winner_variant_id=winner.winner_variant_id
        )
        print(f"Test stopped with status: {final_test.status.value}")
        print(f"Winner: {winner.winner_variant_id}")
    else:
        final_test = await framework.stop_test(
            test_id=test.test_id,
            reason="Demo complete - no significant winner"
        )
        print(f"Test stopped with status: {final_test.status.value}")
    
    print("\n" + "=" * 80)
    print("Demo Complete!")
    print("=" * 80)
    
    await framework.close()


def run_sample_size_calculation_demo():
    """Demonstrate sample size calculation."""
    print("\n" + "=" * 80)
    print("Sample Size Calculation Examples")
    print("=" * 80)
    
    calculator = StatisticalCalculator()
    
    scenarios = [
        ("High baseline (50%), small effect (5%)", 0.50, 0.05),
        ("Medium baseline (30%), medium effect (10%)", 0.30, 0.10),
        ("Low baseline (10%), large effect (20%)", 0.10, 0.20),
        ("Very low baseline (5%), large effect (30%)", 0.05, 0.30),
    ]
    
    print(f"\n{'Scenario':<45} {'Per Variant':<15} {'Total':<10}")
    print("-" * 80)
    
    for name, baseline, effect in scenarios:
        n = calculator.calculate_sample_size(baseline, effect)
        print(f"{name:<45} {n:<15,} {n*2:<10,}")
    
    print("\nNote: These are minimum samples per variant for 80% power at α=0.05")


if __name__ == "__main__":
    # Run sample size demo (no async needed)
    run_sample_size_calculation_demo()
    
    # Run full demo
    print("\n" + "=" * 80)
    print("Starting A/B Testing Framework Demo")
    print("Note: This demo simulates database operations")
    print("=" * 80)
    
    asyncio.run(run_demo())
