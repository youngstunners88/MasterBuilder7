"""
Semantic Code Search - Natural language to code location.

This module provides semantic search capabilities for codebases,
using tree-sitter parsers and embeddings to understand code structure.
"""

from .search import (
    SemanticSearchEngine,
    CodeNavigator,
    SearchResult
)
from .indexer import (
    TreeSitterIndexer,
    CodeElement,
    LanguageMapper,
    get_parser
)
from .embeddings import (
    EmbeddingManager,
    CodeEmbedding,
    QueryExpander
)

__version__ = "1.0.0"
__all__ = [
    "SemanticSearchEngine",
    "CodeNavigator",
    "SearchResult",
    "TreeSitterIndexer",
    "CodeElement",
    "LanguageMapper",
    "get_parser",
    "EmbeddingManager",
    "CodeEmbedding",
    "QueryExpander",
]
