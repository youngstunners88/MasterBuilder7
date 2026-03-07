"""
Business Logic Extractor: Understands what code does, not just how.

Extract business rules from code and generate human-readable documentation.
"""

from .extractor import BusinessLogicExtractor, ExtractionResult
from .rule_parser import RuleParser, BusinessRule
from .documenter import BusinessDocumenter

__version__ = "1.0.0"
__all__ = [
    "BusinessLogicExtractor",
    "ExtractionResult",
    "RuleParser",
    "BusinessRule",
    "BusinessDocumenter",
]
