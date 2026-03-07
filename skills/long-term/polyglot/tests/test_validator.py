"""
Tests for TranslationValidator.
"""

import pytest
from src.validator import TranslationValidator
from src.translator import TranslationRequest, TranslationResult, Language


class TestTranslationValidator:
    """Test cases for TranslationValidator."""
    
    def setup_method(self):
        self.validator = TranslationValidator()
    
    def test_validate_valid_python(self):
        """Test validating valid Python translation."""
        request = TranslationRequest(
            source_code="def func(): pass",
            source_language=Language.PYTHON,
            target_language=Language.JAVASCRIPT,
        )
        result = TranslationResult(
            target_code="function func() {}",
            source_language=Language.PYTHON,
            target_language=Language.JAVASCRIPT,
            warnings=[],
            info=[],
            dependencies=[],
            confidence=0.9,
        )
        
        validation = self.validator.validate(request, result)
        assert validation.syntax_valid is True
    
    def test_validate_invalid_python(self):
        """Test validating invalid Python translation."""
        request = TranslationRequest(
            source_code="def func(): pass",
            source_language=Language.PYTHON,
            target_language=Language.PYTHON,
        )
        result = TranslationResult(
            target_code="def func(",  # Invalid syntax
            source_language=Language.PYTHON,
            target_language=Language.PYTHON,
            warnings=[],
            info=[],
            dependencies=[],
            confidence=0.5,
        )
        
        validation = self.validator.validate(request, result)
        assert validation.syntax_valid is False
    
    def test_check_semantic_preservation(self):
        """Test semantic preservation check."""
        source = """
def func1():
    pass

def func2():
    pass
"""
        target = """
function func1() {}

function func2() {}
"""
        score = self.validator._check_semantic_preservation(
            source, target, Language.PYTHON, Language.JAVASCRIPT
        )
        assert score >= 0.8
    
    def test_check_comment_preservation(self):
        """Test comment preservation check."""
        source = """
# Comment 1
# Comment 2
def func():
    pass
"""
        target = """
// Comment 1
// Comment 2
function func() {}
"""
        score = self.validator._check_comment_preservation(source, target)
        assert score == 1.0
    
    def test_check_idioms_python(self):
        """Test idiom check for Python."""
        code = "console.log('hello')"
        warnings = self.validator._check_idioms(code, Language.PYTHON)
        assert any("console.log" in w for w in warnings)
    
    def test_check_idioms_javascript(self):
        """Test idiom check for JavaScript."""
        code = "range(10)"
        warnings = self.validator._check_idioms(code, Language.JAVASCRIPT)
        assert any("range" in w for w in warnings)
    
    def test_count_functions_python(self):
        """Test counting Python functions."""
        code = """
def func1(): pass
def func2(): pass
async def func3(): pass
"""
        count = self.validator._count_functions(code, Language.PYTHON)
        assert count == 3
    
    def test_count_functions_javascript(self):
        """Test counting JavaScript functions."""
        code = """
function func1() {}
const func2 = () => {}
"""
        count = self.validator._count_functions(code, Language.JAVASCRIPT)
        assert count >= 2
    
    def test_generate_validation_report(self):
        """Test report generation."""
        from src.validator import ValidationResult
        
        request = TranslationRequest(
            source_code="def func(): pass",
            source_language=Language.PYTHON,
            target_language=Language.JAVASCRIPT,
        )
        result = TranslationResult(
            target_code="function func() {}",
            source_language=Language.PYTHON,
            target_language=Language.JAVASCRIPT,
            warnings=[],
            info=[],
            dependencies=[],
            confidence=0.9,
        )
        validation = ValidationResult(
            is_valid=True,
            syntax_valid=True,
            semantic_preservation=0.9,
            warnings=[],
            errors=[],
        )
        
        report = self.validator.generate_validation_report(request, result, validation)
        assert "Validation Report" in report
        assert "Python" in report
        assert "JavaScript" in report
