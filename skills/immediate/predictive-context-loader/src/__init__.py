"""
Predictive Context Loader - Pre-fetches relevant files before user asks.

This module provides intelligent file prediction based on conversation history
using embeddings and vector similarity search.
"""

from .loader import (
    PredictiveContextLoader,
    ContextManager,
    create_loader
)
from .predictor import (
    Predictor,
    ConversationAnalyzer,
    FileIndexer,
    PredictionResult
)
from .cache import (
    PredictionCache,
    EmbeddingCache
)

__version__ = "1.0.0"
__all__ = [
    "PredictiveContextLoader",
    "ContextManager",
    "create_loader",
    "Predictor",
    "ConversationAnalyzer",
    "FileIndexer",
    "PredictionResult",
    "PredictionCache",
    "EmbeddingCache",
]
