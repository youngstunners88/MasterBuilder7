"""
Speech-to-Code: Natural language to working code synthesis.

Convert spoken or written descriptions into complete, production-ready code.
"""

from .synthesizer import CodeSynthesizer
from .template_engine import TemplateEngine
from .validator import CodeValidator

__version__ = "1.0.0"
__all__ = ["CodeSynthesizer", "TemplateEngine", "CodeValidator"]
