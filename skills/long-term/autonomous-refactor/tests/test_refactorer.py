"""
Tests for Refactorer.
"""

import pytest
from src.refactorer import Refactorer, Refactoring, RefactoringType
from src.detector import CodeSmell, SmellType


class TestRefactorer:
    """Test cases for Refactorer."""
    
    def setup_method(self):
        self.refactorer = Refactorer()
    
    def test_refactor_long_method(self):
        """Test refactoring long methods."""
        code = """
def long_method():
    x = 1
    y = 2
    return x + y
"""
        smell = CodeSmell(
            smell_type=SmellType.LONG_METHOD,
            message="Method is too long",
            filename="test.py",
            line_start=1,
            line_end=5,
            severity="high",
            confidence=0.9,
            metadata={"method_name": "long_method", "lines": 100}
        )
        
        refactoring = self.refactorer.refactor(code, smell, "test.py")
        assert refactoring is not None
        assert refactoring.refactoring_type == RefactoringType.EXTRACT_METHOD
    
    def test_refactor_missing_docstring(self):
        """Test adding missing docstrings."""
        code = """
def undocumented():
    pass
"""
        smell = CodeSmell(
            smell_type=SmellType.MISSING_DOCSTRING,
            message="Missing docstring",
            filename="test.py",
            line_start=1,
            line_end=3,
            severity="low",
            confidence=0.9,
            metadata={"name": "undocumented"}
        )
        
        refactoring = self.refactorer.refactor(code, smell, "test.py")
        assert refactoring is not None
        assert refactoring.refactoring_type == RefactoringType.ADD_DOCSTRING
        assert '"""' in refactoring.refactored_code
    
    def test_refactor_unused_import(self):
        """Test removing unused imports."""
        code = """import json
import os

def func():
    return os.path.join("a", "b")
"""
        smell = CodeSmell(
            smell_type=SmellType.UNUSED_IMPORT,
            message="Unused import: json",
            filename="test.py",
            line_start=1,
            line_end=1,
            severity="low",
            confidence=0.9,
            metadata={"import_name": "json"}
        )
        
        refactoring = self.refactorer.refactor(code, smell, "test.py")
        assert refactoring is not None
        assert refactoring.refactoring_type == RefactoringType.REMOVE_UNUSED_IMPORT
        assert "import json" not in refactoring.refactored_code
    
    def test_refactor_magic_numbers(self):
        """Test replacing magic numbers."""
        code = """
def calculate():
    return amount * 0.15
"""
        smell = CodeSmell(
            smell_type=SmellType.MAGIC_NUMBER,
            message="Magic number: 0.15",
            filename="test.py",
            line_start=3,
            line_end=3,
            severity="low",
            confidence=0.7,
            metadata={"number": "0.15"}
        )
        
        refactoring = self.refactorer.refactor(code, smell, "test.py")
        assert refactoring is not None
        assert refactoring.refactoring_type == RefactoringType.REPLACE_MAGIC_NUMBERS
    
    def test_refactor_data_class(self):
        """Test converting to dataclass."""
        code = """
class Person:
    def get_name(self):
        return self._name
    def set_name(self, name):
        self._name = name
"""
        smell = CodeSmell(
            smell_type=SmellType.DATA_CLASS,
            message="Should use dataclass",
            filename="test.py",
            line_start=1,
            line_end=5,
            severity="low",
            confidence=0.7,
            metadata={"class_name": "Person"}
        )
        
        refactoring = self.refactorer.refactor(code, smell, "test.py")
        assert refactoring is not None
        assert "@dataclass" in refactoring.refactored_code
    
    def test_refactor_all(self):
        """Test refactoring multiple smells."""
        code = """
def func():
    pass
"""
        smells = [
            CodeSmell(
                smell_type=SmellType.MISSING_DOCSTRING,
                message="Missing docstring",
                filename="test.py",
                line_start=1,
                line_end=3,
                severity="low",
                confidence=0.9,
                metadata={"name": "func"}
            )
        ]
        
        refactorings = self.refactorer.refactor_all(code, smells, "test.py")
        assert len(refactorings) > 0
    
    def test_generate_refactoring_plan(self):
        """Test generating refactoring plan."""
        smells = [
            CodeSmell(
                smell_type=SmellType.LONG_METHOD,
                message="Long method",
                filename="test.py",
                line_start=1,
                line_end=100,
                severity="high",
                confidence=0.9,
                metadata={}
            ),
            CodeSmell(
                smell_type=SmellType.MISSING_DOCSTRING,
                message="Missing docstring",
                filename="test.py",
                line_start=1,
                line_end=1,
                severity="low",
                confidence=0.9,
                metadata={}
            )
        ]
        
        plan = self.refactorer.generate_refactoring_plan(smells, max_effort_hours=4.0)
        
        assert "planned_refactorings" in plan
        assert "total_effort_hours" in plan
        assert plan["total_effort_hours"] <= 4.0


class TestRefactoringHistory:
    """Test cases for RefactoringHistory."""
    
    def test_add_refactoring(self):
        """Test adding refactoring to history."""
        from src.refactorer import RefactoringHistory
        
        history = RefactoringHistory()
        refactoring = Refactoring(
            refactoring_type=RefactoringType.ADD_DOCSTRING,
            description="Added docstring",
            original_code="def func(): pass",
            refactored_code='def func():\n    """Docstring."""\n    pass',
            filename="test.py",
            line_start=1,
            line_end=1,
            confidence=0.9,
        )
        
        history.add(refactoring)
        assert len(history.refactorings) == 1
    
    def test_reject_refactoring(self):
        """Test rejecting refactoring."""
        from src.refactorer import RefactoringHistory
        
        history = RefactoringHistory()
        refactoring = Refactoring(
            refactoring_type=RefactoringType.ADD_DOCSTRING,
            description="Added docstring",
            original_code="",
            refactored_code="",
            filename="test.py",
            line_start=1,
            line_end=1,
            confidence=0.9,
        )
        
        history.reject(refactoring, "Broke API")
        assert len(history.rejected) == 1
    
    def test_get_success_rate(self):
        """Test calculating success rate."""
        from src.refactorer import RefactoringHistory
        
        history = RefactoringHistory()
        refactoring = Refactoring(
            refactoring_type=RefactoringType.ADD_DOCSTRING,
            description="Added docstring",
            original_code="",
            refactored_code="",
            filename="test.py",
            line_start=1,
            line_end=1,
            confidence=0.9,
        )
        
        history.add(refactoring)
        history.reject(refactoring, "Broke API")
        
        rate = history.get_success_rate()
        assert rate == 0.5
