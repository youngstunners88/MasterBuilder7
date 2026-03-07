"""Tests for predictor module."""

import pytest
import numpy as np
from pathlib import Path
import tempfile

from src.predictor import (
    ConversationAnalyzer,
    FileIndexer,
    Predictor,
    PredictionResult
)
from src.cache import EmbeddingCache


class TestConversationAnalyzer:
    """Test ConversationAnalyzer class."""
    
    @pytest.fixture
    def analyzer(self):
        return ConversationAnalyzer()
    
    def test_analyze_basic(self, analyzer):
        conversation = [
            {"role": "user", "content": "I need to fix the authentication bug"}
        ]
        
        result = analyzer.analyze(conversation)
        
        assert "embedding" in result
        assert "detected_file_types" in result
        assert "detected_action" in result
        assert isinstance(result["embedding"], np.ndarray)
    
    def test_detect_file_types(self, analyzer):
        conversation = [
            {"role": "user", "content": "Update the test files and config settings"}
        ]
        
        result = analyzer.analyze(conversation)
        
        assert "test" in result["detected_file_types"]
        assert "config" in result["detected_file_types"]
    
    def test_detect_action(self, analyzer):
        tests = [
            ([{"role": "user", "content": "Show me the code"}], "read"),
            ([{"role": "user", "content": "Fix the bug"}], "edit"),
            ([{"role": "user", "content": "Create a new file"}], "create"),
            ([{"role": "user", "content": "Delete old code"}], "delete"),
            ([{"role": "user", "content": "Test the feature"}], "test"),
        ]
        
        for conversation, expected_action in tests:
            result = analyzer.analyze(conversation)
            assert result["detected_action"] == expected_action
    
    def test_extract_file_mentions(self, analyzer):
        conversation = [
            {"role": "user", "content": "Check src/auth.py and config/settings.yaml"}
        ]
        
        result = analyzer.analyze(conversation)
        mentions = result["file_mentions"]
        
        assert any("auth.py" in m for m in mentions)
    
    def test_extract_code_symbols(self, analyzer):
        conversation = [
            {"role": "user", "content": "The User class and authenticate() function"}
        ]
        
        result = analyzer.analyze(conversation)
        symbols = result["code_symbols"]
        
        assert "User" in symbols or "authenticate" in str(symbols)


class TestFileIndexer:
    """Test FileIndexer class."""
    
    @pytest.fixture
    def temp_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            
            # Create test files
            (root / "src").mkdir()
            (root / "tests").mkdir()
            
            (root / "src" / "main.py").write_text("""
def main():
    print("Hello")

class App:
    def run(self):
        pass
""")
            (root / "src" / "utils.py").write_text("""
def helper():
    return 42
""")
            (root / "tests" / "test_main.py").write_text("""
def test_main():
    assert True
""")
            (root / "README.md").write_text("# Test Project")
            
            yield root
    
    def test_index_project(self, temp_project):
        indexer = FileIndexer(temp_project)
        count = indexer.index_project()
        
        assert count >= 3  # At least our test files
        assert len(indexer.get_indexed_files()) >= 3
    
    def test_search_similar(self, temp_project):
        indexer = FileIndexer(temp_project)
        indexer.index_project()
        
        # Create a query embedding (simplified)
        query = indexer.analyzer.model.encode("main application entry point")
        results = indexer.search_similar(query, top_k=3)
        
        assert len(results) > 0
        assert all("similarity_score" in r for r in results)
        # Results should be sorted by similarity
        for i in range(len(results) - 1):
            assert results[i]["similarity_score"] >= results[i+1]["similarity_score"]
    
    def test_should_skip_node_modules(self, temp_project):
        # Create node_modules
        (temp_project / "node_modules").mkdir()
        (temp_project / "node_modules" / "test.js").write_text("// should be skipped")
        
        indexer = FileIndexer(temp_project)
        indexer.index_project(file_patterns=["**/*.js"])
        
        files = indexer.get_indexed_files()
        assert not any("node_modules" in f for f in files)
    
    def test_should_skip_large_files(self, temp_project):
        # Create a large file (>1MB)
        large_file = temp_project / "large.py"
        large_file.write_text("x" * (1024 * 1024 + 1))
        
        indexer = FileIndexer(temp_project)
        indexer.index_project()
        
        assert str(large_file) not in indexer.get_indexed_files()


class TestPredictor:
    """Test Predictor class."""
    
    @pytest.fixture
    def temp_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            
            (root / "src").mkdir()
            (root / "src" / "auth.py").write_text("""
def authenticate(username, password):
    return True

class AuthManager:
    pass
""")
            (root / "src" / "main.py").write_text("""
def main():
    pass
""")
            
            yield root
    
    @pytest.fixture
    def predictor(self, temp_project):
        return Predictor(temp_project)
    
    def test_predict(self, temp_project, predictor):
        predictor.index_project()
        
        conversation = [
            {"role": "user", "content": "I need to fix the authentication"}
        ]
        
        predictions = predictor.predict(conversation, top_k=5)
        
        assert len(predictions) > 0
        assert all(isinstance(p, PredictionResult) for p in predictions)
        assert all(0 <= p.confidence <= 1 for p in predictions)
    
    def test_prediction_has_reason(self, temp_project, predictor):
        predictor.index_project()
        
        conversation = [
            {"role": "user", "content": "Fix auth bug"}
        ]
        
        predictions = predictor.predict(conversation)
        
        for p in predictions:
            assert p.reason is not None
            assert len(p.reason) > 0
    
    def test_prediction_action(self, temp_project, predictor):
        predictor.index_project()
        
        conversation = [
            {"role": "user", "content": "Create new test file"}
        ]
        
        predictions = predictor.predict(conversation)
        
        assert predictions[0].predicted_action == "create"


class TestPredictionResult:
    """Test PredictionResult dataclass."""
    
    def test_creation(self):
        result = PredictionResult(
            file_path="src/auth.py",
            relevance_score=0.95,
            confidence=0.88,
            reason="Matches auth keywords",
            predicted_action="edit"
        )
        
        assert result.file_path == "src/auth.py"
        assert result.relevance_score == 0.95
        assert result.confidence == 0.88
