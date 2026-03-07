"""
Tests for PolyglotTranslator.
"""

import pytest
from src.translator import PolyglotTranslator, TranslationRequest, Language


class TestPolyglotTranslator:
    """Test cases for PolyglotTranslator."""
    
    def setup_method(self):
        self.translator = PolyglotTranslator()
    
    def test_translate_python_to_javascript_function(self):
        """Test translating Python function to JavaScript."""
        request = TranslationRequest(
            source_code="""
def greet(name):
    return f"Hello, {name}!"
""",
            source_language=Language.PYTHON,
            target_language=Language.JAVASCRIPT,
        )
        
        result = self.translator.translate(request)
        assert "function greet(name)" in result.target_code
        assert result.confidence >= 0.7
    
    def test_translate_python_to_javascript_class(self):
        """Test translating Python class to JavaScript."""
        request = TranslationRequest(
            source_code="""
class User:
    def __init__(self, name):
        self.name = name
""",
            source_language=Language.PYTHON,
            target_language=Language.JAVASCRIPT,
        )
        
        result = self.translator.translate(request)
        assert "class User" in result.target_code
        assert "constructor" in result.target_code
    
    def test_translate_javascript_to_python(self):
        """Test translating JavaScript to Python."""
        request = TranslationRequest(
            source_code="""
function add(a, b) {
    return a + b;
}
""",
            source_language=Language.JAVASCRIPT,
            target_language=Language.PYTHON,
        )
        
        result = self.translator.translate(request)
        assert "def add(a, b)" in result.target_code
        assert ":" in result.target_code
    
    def test_translate_python_to_rust(self):
        """Test translating Python to Rust."""
        request = TranslationRequest(
            source_code="""
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
""",
            source_language=Language.PYTHON,
            target_language=Language.RUST,
        )
        
        result = self.translator.translate(request)
        assert "fn factorial" in result.target_code
    
    def test_translate_python_to_go(self):
        """Test translating Python to Go."""
        request = TranslationRequest(
            source_code="""
def hello():
    print("Hello, World!")
""",
            source_language=Language.PYTHON,
            target_language=Language.GO,
        )
        
        result = self.translator.translate(request)
        assert "package main" in result.target_code
    
    def test_preserve_comments(self):
        """Test comment preservation."""
        request = TranslationRequest(
            source_code="""
# This is a comment
def func():
    pass
""",
            source_language=Language.PYTHON,
            target_language=Language.JAVASCRIPT,
            preserve_comments=True,
        )
        
        result = self.translator.translate(request)
        # Comments should be converted to JS style
        assert "//" in result.target_code or "comment" in result.target_code.lower()
    
    def test_detect_language_from_extension(self):
        """Test language detection from file extension."""
        lang = self.translator._detect_language(".py")
        assert lang == Language.PYTHON
        
        lang = self.translator._detect_language(".js")
        assert lang == Language.JAVASCRIPT
        
        lang = self.translator._detect_language(".ts")
        assert lang == Language.TYPESCRIPT
    
    def test_get_dependencies_python(self):
        """Test extracting Python dependencies."""
        code = "import json\nimport requests"
        deps = self.translator._get_dependencies(Language.PYTHON, code)
        assert "json" in deps
        assert "requests" in deps
    
    def test_get_dependencies_javascript(self):
        """Test extracting JavaScript dependencies."""
        code = "fetch('/api/data')"
        deps = self.translator._get_dependencies(Language.JAVASCRIPT, code)
        assert "node-fetch" in deps


class TestTranslationRequest:
    """Test cases for TranslationRequest."""
    
    def test_default_values(self):
        """Test default request values."""
        request = TranslationRequest(
            source_code="pass",
            source_language=Language.PYTHON,
            target_language=Language.JAVASCRIPT,
        )
        assert request.preserve_comments is True
        assert request.preserve_docstrings is True
    
    def test_custom_values(self):
        """Test custom request values."""
        request = TranslationRequest(
            source_code="pass",
            source_language=Language.PYTHON,
            target_language=Language.JAVASCRIPT,
            preserve_comments=False,
            target_style="literal",
        )
        assert request.preserve_comments is False
        assert request.target_style == "literal"
