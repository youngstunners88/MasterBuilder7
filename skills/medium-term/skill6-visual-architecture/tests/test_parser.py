"""Tests for the code parser."""

import pytest
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, '../src')

from parser import CodeParser


class TestCodeParser:
    """Test cases for CodeParser."""
    
    def test_initialization(self):
        """Test parser initialization."""
        parser = CodeParser()
        assert parser is not None
    
    def test_detect_language(self):
        """Test language detection from file extension."""
        parser = CodeParser()
        
        assert parser._detect_language(Path("test.py")) == "python"
        assert parser._detect_language(Path("test.js")) == "javascript"
        assert parser._detect_language(Path("test.jsx")) == "javascript"
        assert parser._detect_language(Path("test.ts")) == "typescript"
        assert parser._detect_language(Path("test.tsx")) == "typescript"
        assert parser._detect_language(Path("test.rs")) == "rust"
        assert parser._detect_language(Path("test.unknown")) is None
    
    def test_parse_python_class(self):
        """Test parsing a Python class."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
class MyClass:
    def __init__(self, name):
        self.name = name
    
    def greet(self):
        return f"Hello, {self.name}"
""")
            tmpfile = f.name
        
        try:
            parser = CodeParser()
            result = parser.parse_file(tmpfile)
            
            assert result is not None
            assert result.language == "python"
            assert len(result.classes) == 1
            assert result.classes[0].name == "MyClass"
            assert len(result.classes[0].methods) == 2
        finally:
            Path(tmpfile).unlink()
    
    def test_parse_python_function(self):
        """Test parsing Python functions."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
def standalone_function():
    pass

async def async_function():
    pass
""")
            tmpfile = f.name
        
        try:
            parser = CodeParser()
            result = parser.parse_file(tmpfile)
            
            assert result is not None
            assert len(result.functions) == 2
        finally:
            Path(tmpfile).unlink()
    
    def test_parse_imports(self):
        """Test parsing imports."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
import os
import sys
from typing import List
from collections import defaultdict
""")
            tmpfile = f.name
        
        try:
            parser = CodeParser()
            result = parser.parse_file(tmpfile)
            
            assert result is not None
            assert len(result.imports) >= 2
        finally:
            Path(tmpfile).unlink()
    
    def test_parse_directory(self):
        """Test parsing a directory of files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "file1.py").write_text("def func1(): pass")
            (Path(tmpdir) / "file2.py").write_text("def func2(): pass")
            
            parser = CodeParser()
            results = parser.parse_directory(tmpdir, pattern="*.py")
            
            assert len(results) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])