"""Tests for loader module."""

import pytest
import json
from pathlib import Path
import tempfile

from src.loader import (
    PredictiveContextLoader,
    ContextManager,
    create_loader
)
from src.predictor import PredictionResult


class TestPredictiveContextLoader:
    """Test PredictiveContextLoader class."""
    
    @pytest.fixture
    def temp_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            
            (root / "src").mkdir()
            (root / "src" / "auth.py").write_text("""
def authenticate():
    pass
""")
            (root / "src" / "models.py").write_text("""
class User:
    pass
""")
            (root / ".kimi").mkdir()
            (root / ".kimi" / "cache").mkdir()
            
            yield root
    
    @pytest.fixture
    def loader(self, temp_project):
        return PredictiveContextLoader(
            project_root=temp_project,
            enable_logging=False
        )
    
    def test_initialization(self, loader):
        assert loader.project_root.exists()
        assert loader.prediction_cache is not None
    
    def test_initialize(self, loader):
        result = loader.initialize()
        assert result is loader  # Returns self for chaining
    
    def test_predict(self, loader):
        loader.initialize()
        
        conversation = [
            {"role": "user", "content": "Fix authentication"}
        ]
        
        predictions = loader.predict(conversation, top_k=3)
        
        assert isinstance(predictions, list)
        assert len(predictions) <= 3
    
    def test_predict_with_cache(self, loader):
        loader.initialize()
        
        conversation = [
            {"role": "user", "content": "Fix authentication"}
        ]
        
        # First call - no cache
        predictions1 = loader.predict(conversation, use_cache=True)
        
        # Second call - should use cache
        predictions2 = loader.predict(conversation, use_cache=True)
        
        # Results should be the same
        assert len(predictions1) == len(predictions2)
    
    def test_load_predicted_files(self, loader):
        loader.initialize()
        
        predictions = [
            PredictionResult(
                file_path="src/auth.py",
                relevance_score=0.9,
                confidence=0.95,
                reason="Auth file",
                predicted_action="edit"
            )
        ]
        
        files = loader.load_predicted_files(predictions)
        
        assert len(files) == 1
        assert files[0]["path"] == "src/auth.py"
        assert "content" in files[0]
        assert "authenticate" in files[0]["content"]
    
    def test_load_predicted_files_confidence_filter(self, loader):
        loader.initialize()
        
        predictions = [
            PredictionResult(
                file_path="src/auth.py",
                relevance_score=0.9,
                confidence=0.3,  # Below threshold
                reason="Low confidence",
                predicted_action="edit"
            )
        ]
        
        files = loader.load_predicted_files(predictions, confidence_threshold=0.5)
        
        assert len(files) == 0  # Should be filtered out
    
    def test_load_predicted_files_max_files(self, loader):
        loader.initialize()
        
        predictions = [
            PredictionResult(
                file_path="src/auth.py",
                relevance_score=0.9,
                confidence=0.95,
                reason="Auth",
                predicted_action="edit"
            ),
            PredictionResult(
                file_path="src/models.py",
                relevance_score=0.8,
                confidence=0.9,
                reason="Models",
                predicted_action="edit"
            )
        ]
        
        files = loader.load_predicted_files(predictions, max_files=1)
        
        assert len(files) == 1
    
    def test_cache_stats(self, loader):
        loader.initialize()
        
        conversation = [{"role": "user", "content": "Test"}]
        loader.predict(conversation)
        
        stats = loader.get_cache_stats()
        
        assert "total_entries" in stats
        assert "active_entries" in stats
    
    def test_clear_cache(self, loader):
        loader.initialize()
        
        conversation = [{"role": "user", "content": "Test"}]
        loader.predict(conversation)
        
        count = loader.clear_cache()
        assert count == 1
        
        stats = loader.get_cache_stats()
        assert stats["total_entries"] == 0
    
    def test_export_predictions(self, loader, temp_project):
        loader.initialize()
        
        predictions = [
            PredictionResult(
                file_path="src/auth.py",
                relevance_score=0.9,
                confidence=0.95,
                reason="Auth",
                predicted_action="edit"
            )
        ]
        
        output_path = temp_project / "predictions.json"
        json_str = loader.export_predictions(predictions, output_path)
        
        assert output_path.exists()
        
        data = json.loads(json_str)
        assert data["total"] == 1
        assert len(data["predictions"]) == 1
    
    def test_callbacks(self, loader):
        loader.initialize()
        
        predict_called = []
        load_called = []
        
        @loader.on_predict
        def on_predict(predictions):
            predict_called.extend(predictions)
        
        @loader.on_load
        def on_load(files):
            load_called.extend(files)
        
        conversation = [{"role": "user", "content": "Test"}]
        predictions = loader.predict(conversation)
        
        assert len(predict_called) == len(predictions)


class TestContextManager:
    """Test ContextManager class."""
    
    @pytest.fixture
    def temp_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "test.py").write_text("# test")
            (root / ".kimi" / "cache").mkdir(parents=True, exist_ok=True)
            yield root
    
    @pytest.fixture
    def manager(self, temp_project):
        loader = PredictiveContextLoader(
            project_root=temp_project,
            enable_logging=False
        )
        loader.initialize()
        return ContextManager(loader, auto_predict=True)
    
    def test_add_message(self, manager):
        predictions = manager.add_message("user", "I need to see the test file")
        
        assert predictions is not None
        assert len(manager.conversation_history) == 1
    
    def test_add_message_no_auto_predict(self, temp_project):
        loader = PredictiveContextLoader(
            project_root=temp_project,
            enable_logging=False
        )
        loader.initialize()
        manager = ContextManager(loader, auto_predict=False)
        
        predictions = manager.add_message("user", "Test message")
        
        assert predictions is None
    
    def test_get_context_files(self, manager):
        manager.add_message("user", "I need to see the test file")
        files = manager.get_context_files(max_files=5)
        
        assert isinstance(files, list)
    
    def test_clear_history(self, manager):
        manager.add_message("user", "Test 1")
        manager.add_message("assistant", "Response")
        manager.add_message("user", "Test 2")
        
        manager.clear_history()
        
        assert len(manager.conversation_history) == 0
        assert len(manager.last_predictions) == 0
        assert len(manager.loaded_files) == 0
    
    def test_get_summary(self, manager):
        manager.add_message("user", "Test")
        
        summary = manager.get_summary()
        
        assert "message_count" in summary
        assert summary["message_count"] == 1


class TestCreateLoader:
    """Test create_loader factory function."""
    
    def test_create_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            loader = create_loader(root)
            
            assert isinstance(loader, PredictiveContextLoader)
            assert loader.project_root == Path(root)
    
    def test_create_loader_creates_cache_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            loader = create_loader(root)
            
            assert (root / ".kimi" / "cache").exists()
