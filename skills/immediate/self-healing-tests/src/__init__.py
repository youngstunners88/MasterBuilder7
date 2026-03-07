"""
Self-Healing Tests - Auto-fixes flaky tests.

This module provides pytest integration for detecting and automatically
fixing flaky tests by analyzing failure patterns and applying fixes.
"""

from .analyzer import (
    FailureAnalyzer,
    TestAnalysis,
    FailureType,
    FlakinessPattern,
    FailureInstance,
    TestCodeAnalyzer
)
from .healer import (
    TestHealer,
    PRGenerator,
    FixApplication
)
from .plugin import SelfHealingPlugin

__version__ = "1.0.0"
__all__ = [
    "FailureAnalyzer",
    "TestAnalysis",
    "FailureType",
    "FlakinessPattern",
    "FailureInstance",
    "TestCodeAnalyzer",
    "TestHealer",
    "PRGenerator",
    "FixApplication",
    "SelfHealingPlugin",
]
