"""
Tests for CodeSmellDetector.
"""

import pytest
from src.detector import CodeSmellDetector, SmellType


class TestCodeSmellDetector:
    """Test cases for CodeSmellDetector."""
    
    def setup_method(self):
        self.detector = CodeSmellDetector()
    
    def test_detect_long_method(self):
        """Test detection of long methods."""
        code = "def long_func():\n" + "    x = 1\n" * 60
        smells = self.detector.detect(code, "test.py")
        
        long_method_smells = [s for s in smells if s.smell_type == SmellType.LONG_METHOD]
        assert len(long_method_smells) > 0
        assert "60" in long_method_smells[0].message
    
    def test_detect_too_many_parameters(self):
        """Test detection of too many parameters."""
        code = "def func(a, b, c, d, e, f, g):\n    pass"
        smells = self.detector.detect(code, "test.py")
        
        param_smells = [s for s in smells if s.smell_type == SmellType.TOO_MANY_PARAMETERS]
        assert len(param_smells) > 0
    
    def test_detect_deep_nesting(self):
        """Test detection of deep nesting."""
        code = """
def nested():
    if True:
        if True:
            if True:
                if True:
                    pass
"""
        smells = self.detector.detect(code, "test.py")
        
        nesting_smells = [s for s in smells if s.smell_type == SmellType.DEEP_NESTING]
        assert len(nesting_smells) > 0
    
    def test_detect_missing_docstring(self):
        """Test detection of missing docstrings."""
        code = """
def no_doc():
    pass

class NoDoc:
    pass
"""
        smells = self.detector.detect(code, "test.py")
        
        doc_smells = [s for s in smells if s.smell_type == SmellType.MISSING_DOCSTRING]
        assert len(doc_smells) >= 2
    
    def test_detect_unused_import(self):
        """Test detection of unused imports."""
        code = """
import json
import os

def func():
    return os.path.join("a", "b")
"""
        smells = self.detector.detect(code, "test.py")
        
        import_smells = [s for s in smells if s.smell_type == SmellType.UNUSED_IMPORT]
        # json is unused, os is used
        json_unused = [s for s in import_smells if "json" in s.message]
        assert len(json_unused) > 0
    
    def test_detect_god_class(self):
        """Test detection of God Class."""
        code = "\n".join([f"    def method_{i}(self): pass" for i in range(25)])
        code = f"class BigClass:\n{code}"
        
        smells = self.detector.detect(code, "test.py")
        
        god_smells = [s for s in smells if s.smell_type == SmellType.GOD_CLASS]
        assert len(god_smells) > 0
    
    def test_detect_data_class(self):
        """Test detection of Data Class."""
        code = """
class Person:
    def get_name(self):
        return self._name
    
    def set_name(self, name):
        self._name = name
    
    def get_age(self):
        return self._age
    
    def set_age(self, age):
        self._age = age
"""
        smells = self.detector.detect(code, "test.py")
        
        data_smells = [s for s in smells if s.smell_type == SmellType.DATA_CLASS]
        assert len(data_smells) > 0
    
    def test_detect_js_smells(self):
        """Test detection of JavaScript smells."""
        code = """
function test() {
    if (true) {
        if (true) {
            if (true) {
                if (true) {
                    var x = 12345;
                }
            }
        }
    }
}
"""
        smells = self.detector.detect(code, "test.js", language="javascript")
        
        nesting_smells = [s for s in smells if s.smell_type == SmellType.DEEP_NESTING]
        assert len(nesting_smells) > 0
    
    def test_generate_report(self):
        """Test report generation."""
        code = "def long():\n" + "    pass\n" * 60
        smells = self.detector.detect(code, "test.py")
        report = self.detector.generate_report(smells)
        
        assert "Code Smell Detection Report" in report
        assert str(len(smells)) in report


class TestSmellType:
    """Test cases for SmellType enum."""
    
    def test_smell_types(self):
        """Test all smell types exist."""
        assert SmellType.LONG_METHOD
        assert SmellType.LONG_CLASS
        assert SmellType.TOO_MANY_PARAMETERS
        assert SmellType.DUPLICATE_CODE
        assert SmellType.GOD_CLASS
        assert SmellType.MISSING_DOCSTRING
