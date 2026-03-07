"""Tests for the repository indexer."""

import pytest
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, '../src')

from indexer import RepoIndexer, CodeIndex


class TestRepoIndexer:
    """Test cases for RepoIndexer."""
    
    def test_initialization(self):
        """Test indexer initialization."""
        indexer = RepoIndexer()
        assert indexer.index == {}
        assert indexer.metadata == {}
    
    def test_add_local_repo(self):
        """Test adding a local repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple Python file
            (Path(tmpdir) / "test.py").write_text("""
def hello():
    return "world"

class TestClass:
    def method(self):
        pass
""")
            
            indexer = RepoIndexer()
            repo_name = indexer.add_local_repo(tmpdir, "test_repo")
            
            assert repo_name == "test_repo"
            assert "test_repo" in indexer.index
            assert len(indexer.index["test_repo"]) > 0
    
    def test_detect_language(self):
        """Test language detection."""
        indexer = RepoIndexer()
        
        assert indexer._detect_language(Path("test.py")) == "python"
        assert indexer._detect_language(Path("test.js")) == "javascript"
        assert indexer._detect_language(Path("test.ts")) == "typescript"
        assert indexer._detect_language(Path("test.rs")) == "rust"
        assert indexer._detect_language(Path("test.go")) == "go"
    
    def test_search(self):
        """Test searching indexed code."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "test.py").write_text("""
def search_function():
    pass
""")
            
            indexer = RepoIndexer()
            indexer.add_local_repo(tmpdir, "test_repo")
            
            results = indexer.search("search_function")
            assert len(results) > 0
            assert any("search_function" in r.functions for r in results)
    
    def test_get_shared_symbols(self):
        """Test finding shared symbols across repos."""
        indexer = RepoIndexer()
        # This would need multiple repos set up
        # For now just test the method exists
        shared = indexer.get_shared_symbols()
        assert isinstance(shared, dict)
    
    def test_get_stats(self):
        """Test getting statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "test.py").write_text("def func(): pass")
            
            indexer = RepoIndexer()
            indexer.add_local_repo(tmpdir, "test_repo")
            
            stats = indexer.get_stats()
            assert stats["total_repos"] == 1
            assert stats["total_files"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])