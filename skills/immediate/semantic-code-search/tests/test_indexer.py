"""Tests for indexer module."""

import pytest
from pathlib import Path
import tempfile

from src.indexer import (
    LanguageMapper,
    TreeSitterIndexer,
    CodeElement,
    get_parser
)


class TestLanguageMapper:
    """Test LanguageMapper class."""
    
    def test_get_language_python(self):
        assert LanguageMapper.get_language(Path("test.py")) == "python"
    
    def test_get_language_javascript(self):
        assert LanguageMapper.get_language(Path("test.js")) == "javascript"
        assert LanguageMapper.get_language(Path("test.jsx")) == "javascript"
    
    def test_get_language_typescript(self):
        assert LanguageMapper.get_language(Path("test.ts")) == "typescript"
        assert LanguageMapper.get_language(Path("test.tsx")) == "tsx"
    
    def test_get_language_rust(self):
        assert LanguageMapper.get_language(Path("test.rs")) == "rust"
    
    def test_get_language_go(self):
        assert LanguageMapper.get_language(Path("test.go")) == "go"
    
    def test_get_language_java(self):
        assert LanguageMapper.get_language(Path("test.java")) == "java"
    
    def test_get_language_unknown(self):
        assert LanguageMapper.get_language(Path("test.unknown")) is None
    
    def test_is_supported(self):
        assert LanguageMapper.is_supported(Path("test.py")) is True
        assert LanguageMapper.is_supported(Path("test.txt")) is False
    
    def test_get_supported_extensions(self):
        exts = LanguageMapper.get_supported_extensions()
        assert ".py" in exts
        assert ".js" in exts
        assert ".ts" in exts


class TestCodeElement:
    """Test CodeElement dataclass."""
    
    def test_creation(self):
        elem = CodeElement(
            element_type="function",
            name="test_func",
            content="def test(): pass",
            start_line=1,
            end_line=3,
            file_path="src/test.py",
            language="python",
            signature="def test()",
            docstring="Test function"
        )
        
        assert elem.element_type == "function"
        assert elem.name == "test_func"
        assert elem.file_path == "src/test.py"
    
    def test_to_dict(self):
        elem = CodeElement(
            element_type="class",
            name="TestClass",
            content="class TestClass:" + " pass" * 100,
            start_line=10,
            end_line=20,
            file_path="src/models.py",
            language="python",
            signature="class TestClass",
            modifiers=["public"],
            parameters=["self", "name"],
            return_type="None"
        )
        
        d = elem.to_dict()
        assert d['element_type'] == "class"
        assert d['name'] == "TestClass"
        assert d['modifiers'] == ["public"]
        assert len(d['content_preview']) < len(elem.content)  # Truncated


class TestTreeSitterIndexer:
    """Test TreeSitterIndexer class."""
    
    @pytest.fixture
    def temp_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            
            # Create Python files
            (root / "src").mkdir()
            (root / "src" / "auth.py").write_text("""
def authenticate(username, password):
    \"\"\"Authenticate a user.\"\"\"
    return True

class AuthManager:
    def __init__(self):
        self.users = {}
    
    def login(self, user, pwd):
        return authenticate(user, pwd)
""")
            (root / "src" / "models.py").write_text("""
class User:
    def __init__(self, name):
        self.name = name
""")
            
            # Create JavaScript file
            (root / "static").mkdir()
            (root / "static" / "app.js").write_text("""
function initApp() {
    console.log('App initialized');
}

class UserComponent {
    render() {
        return '<div>User</div>';
    }
}
""")
            
            # Create directory that should be excluded
            (root / "node_modules").mkdir()
            (root / "node_modules" / "package.js").write_text("module.exports = {};")
            
            yield root
    
    def test_initialization(self, temp_project):
        indexer = TreeSitterIndexer(temp_project)
        assert indexer.project_root == temp_project
    
    def test_index_project(self, temp_project):
        indexer = TreeSitterIndexer(temp_project)
        count = indexer.index_project()
        
        assert count > 0
        assert len(indexer.get_elements()) == count
    
    def test_get_elements_by_language(self, temp_project):
        indexer = TreeSitterIndexer(temp_project)
        indexer.index_project()
        
        python_elements = indexer.get_elements_by_language("python")
        js_elements = indexer.get_elements_by_language("javascript")
        
        assert all(e.language == "python" for e in python_elements)
        assert all(e.language == "javascript" for e in js_elements)
    
    def test_get_elements_by_type(self, temp_project):
        indexer = TreeSitterIndexer(temp_project)
        indexer.index_project()
        
        functions = indexer.get_elements_by_type("function")
        classes = indexer.get_elements_by_type("class")
        
        assert all(e.element_type == "function" for e in functions)
        assert all(e.element_type == "class" for e in classes)
    
    def test_get_elements_in_file(self, temp_project):
        indexer = TreeSitterIndexer(temp_project)
        indexer.index_project()
        
        elements = indexer.get_elements_in_file("src/auth.py")
        
        assert all("src/auth.py" in e.file_path for e in elements)
        assert any(e.name == "authenticate" for e in elements)
        assert any(e.name == "AuthManager" for e in elements)
    
    def test_excludes_node_modules(self, temp_project):
        indexer = TreeSitterIndexer(temp_project)
        indexer.index_project()
        
        elements = indexer.get_elements()
        assert not any("node_modules" in e.file_path for e in elements)
    
    def test_excludes_large_files(self, temp_project):
        # Create a large file (>500KB)
        large_file = temp_project / "src" / "large.py"
        large_file.write_text("x = " + "'a' * (1024 * 600))  # > 600KB
        
        indexer = TreeSitterIndexer(temp_project)
        indexer.index_project()
        
        assert not any("large.py" in e.file_path for e in indexer.get_elements())
    
    def test_save_and_load_index(self, temp_project):
        indexer = TreeSitterIndexer(temp_project)
        indexer.index_project()
        
        with tempfile.TemporaryDirectory() as tmp:
            index_path = Path(tmp) / "index.json"
            
            indexer.save_index(index_path)
            assert index_path.exists()
            
            # Load into new indexer
            new_indexer = TreeSitterIndexer(temp_project)
            new_indexer.load_index(index_path)
            
            assert len(new_indexer.file_hashes) > 0


class TestParsers:
    """Test parser loading."""
    
    def test_get_parser_python(self):
        parser = get_parser("python")
        assert parser is not None
    
    def test_get_parser_javascript(self):
        parser = get_parser("javascript")
        assert parser is not None
    
    def test_get_parser_typescript(self):
        parser = get_parser("typescript")
        assert parser is not None
    
    def test_get_parser_rust(self):
        parser = get_parser("rust")
        assert parser is not None
    
    def test_get_parser_go(self):
        parser = get_parser("go")
        assert parser is not None
    
    def test_get_parser_java(self):
        parser = get_parser("java")
        assert parser is not None
    
    def test_get_parser_unknown(self):
        parser = get_parser("unknown")
        assert parser is None
