"""
Cross-Language Polyglot: Seamlessly works across Python/JS/Rust/etc.

Translate code between programming languages while maintaining semantic equivalence.
"""

from .translator import PolyglotTranslator, TranslationRequest, TranslationResult
from .validator import TranslationValidator

__version__ = "1.0.0"
__all__ = ["PolyglotTranslator", "TranslationRequest", "TranslationResult", "TranslationValidator"]
