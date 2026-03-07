"""
Tests for CodeValidator.
"""

import pytest
from src.validator import CodeValidator, ValidationIssue, SecurityValidator


class TestCodeValidator:
    """Test cases for CodeValidator."""
    
    def setup_method(self):
        self.validator = CodeValidator()
    
    def test_validate_valid_python(self):
        """Test validating valid Python code."""
        code = """
def hello():
    return "world"
"""
        result = self.validator.validate(code, "python")
        assert result.is_valid is True
        assert result.syntax_valid is True
    
    def test_validate_invalid_python(self):
        """Test validating invalid Python code."""
        code = "def hello("
        result = self.validator.validate(code, "python")
        assert result.is_valid is False
        assert result.syntax_valid is False
    
    def test_check_imports_dangerous(self):
        """Test detecting dangerous imports."""
        code = "import os\nos.system('rm -rf /')"
        issues = self.validator._check_imports(code)
        
        dangerous_issues = [i for i in issues if "os" in i.message]
        assert len(dangerous_issues) > 0
    
    def test_check_naming_conventions(self):
        """Test naming convention checks."""
        code = """
def BadFunctionName():
    pass

class bad_class_name:
    pass
"""
        issues = self.validator._check_naming_conventions(code)
        
        function_issues = [i for i in issues if "Function name" in i.message]
        class_issues = [i for i in issues if "Class name" in i.message]
        
        assert len(function_issues) > 0
        assert len(class_issues) > 0
    
    def test_check_docstrings(self):
        """Test docstring checks."""
        code = """
def undocumented_function():
    pass

class UndocumentedClass:
    pass
"""
        issues = self.validator._check_docstrings(code)
        assert len(issues) >= 2
    
    def test_check_complexity_long_function(self):
        """Test complexity check for long functions."""
        code = "def long_function():\n" + "    x = 1\n" * 60
        issues = self.validator._check_complexity(code)
        
        long_issues = [i for i in issues if "long" in i.message.lower()]
        assert len(long_issues) > 0
    
    def test_calculate_metrics(self):
        """Test metrics calculation."""
        code = """
def func1():
    x = 1
    return x

def func2():
    y = 2
    return y
"""
        metrics = self.validator._calculate_metrics(code, "python")
        
        assert "total_lines" in metrics
        assert "code_lines" in metrics
        assert metrics.get("functions") == 2
    
    def test_format_report(self):
        """Test report formatting."""
        from src.validator import ValidationResult
        
        result = ValidationResult(
            is_valid=True,
            issues=[ValidationIssue("warning", "Test warning", line=1)],
            metrics={"lines": 10}
        )
        
        report = self.validator.format_report(result, "test.py")
        assert "Validation Report" in report
        assert "test.py" in report
        assert "Test warning" in report


class TestSecurityValidator:
    """Test cases for SecurityValidator."""
    
    def setup_method(self):
        self.validator = SecurityValidator()
    
    def test_validate_security_eval(self):
        """Test detecting eval() usage."""
        code = "eval(user_input)"
        result = self.validator.validate_security(code, "python")
        
        assert result.is_valid is False
        assert any("eval" in i.message for i in result.issues)
    
    def test_validate_security_exec(self):
        """Test detecting exec() usage."""
        code = "exec(malicious_code)"
        result = self.validator.validate_security(code, "python")
        
        assert result.is_valid is False
        assert any("exec" in i.message for i in result.issues)
    
    def test_validate_security_sql_injection(self):
        """Test detecting SQL injection patterns."""
        code = "query = 'SELECT * FROM users WHERE id = %s' % user_id"
        result = self.validator.validate_security(code, "python")
        
        assert any("SQL" in i.message for i in result.issues)
    
    def test_validate_js_security(self):
        """Test JavaScript security validation."""
        code = "eval(userInput)"
        result = self.validator.validate_security(code, "javascript")
        
        assert result.is_valid is False
        assert any("eval" in i.message for i in result.issues)
