"""
Main loader module for predictive context loading.
Orchestrates caching, prediction, and file loading.
"""

import asyncio
import json
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
from dataclasses import asdict
from loguru import logger

from .cache import PredictionCache, EmbeddingCache
from .predictor import Predictor, PredictionResult


class PredictiveContextLoader:
    """
    Main class for predictive context loading.
    
    This loader analyzes conversation history, predicts which files
    will be needed next, and pre-loads them into context.
    
    Example:
        loader = PredictiveContextLoader(project_root="/path/to/project")
        loader.initialize()
        
        predictions = loader.predict([
            {"role": "user", "content": "I need to fix the authentication bug"}
        ])
        
        files = loader.load_predicted_files(predictions[:3])
    """
    
    def __init__(
        self,
        project_root: str | Path,
        cache_ttl: int = 3600,
        cache_max_size: int = 1000,
        prediction_cache_path: Optional[Path] = None,
        embedding_cache_dir: Optional[Path] = None,
        enable_logging: bool = True
    ):
        """
        Initialize the predictive context loader.
        
        Args:
            project_root: Root directory of the project
            cache_ttl: Time-to-live for predictions in seconds (default: 1 hour)
            cache_max_size: Maximum number of cached predictions
            prediction_cache_path: Path for prediction cache persistence
            embedding_cache_dir: Directory for embedding cache
            enable_logging: Whether to enable logging
        """
        self.project_root = Path(project_root)
        
        # Initialize caches
        self.prediction_cache = PredictionCache(
            ttl_seconds=cache_ttl,
            max_size=cache_max_size,
            persist_path=prediction_cache_path
        )
        
        embedding_cache = None
        if embedding_cache_dir:
            embedding_cache = EmbeddingCache(embedding_cache_dir)
        
        self.predictor = Predictor(project_root, embedding_cache)
        
        # Callbacks for pre-load events
        self._on_predict_callbacks: List[Callable] = []
        self._on_load_callbacks: List[Callable] = []
        
        if enable_logging:
            logger.enable("predictive_context_loader")
    
    def initialize(self, file_patterns: List[str] = None) -> 'PredictiveContextLoader':
        """
        Initialize by indexing the project.
        
        Args:
            file_patterns: Optional list of file patterns to index
            
        Returns:
            Self for chaining
        """
        logger.info("Initializing PredictiveContextLoader...")
        count = self.predictor.index_project(file_patterns)
        logger.info(f"Loader initialized with {count} indexed files")
        return self
    
    def predict(
        self,
        conversation_history: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        use_cache: bool = True
    ) -> List[PredictionResult]:
        """
        Predict which files will be needed.
        
        Args:
            conversation_history: List of conversation messages
            context: Optional additional context (e.g., current file, task type)
            top_k: Number of predictions to return
            use_cache: Whether to use cached predictions
            
        Returns:
            List of prediction results sorted by relevance
        """
        # Check cache first
        if use_cache:
            cached = self.prediction_cache.get(conversation_history, context)
            if cached is not None:
                logger.info("Using cached predictions")
                return [PredictionResult(**r) for r in cached]
        
        # Make predictions
        logger.info(f"Predicting files for conversation ({len(conversation_history)} messages)")
        predictions = self.predictor.predict(conversation_history, top_k)
        
        # Cache results
        if use_cache:
            self.prediction_cache.set(
                conversation_history,
                [asdict(p) for p in predictions],
                context
            )
        
        # Trigger callbacks
        for callback in self._on_predict_callbacks:
            try:
                callback(predictions)
            except Exception as e:
                logger.error(f"Prediction callback error: {e}")
        
        return predictions
    
    def load_predicted_files(
        self,
        predictions: List[PredictionResult],
        max_files: int = 5,
        confidence_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Load the content of predicted files.
        
        Args:
            predictions: List of predictions to load
            max_files: Maximum number of files to load
            confidence_threshold: Minimum confidence to load file
            
        Returns:
            List of file data dicts with content
        """
        loaded = []
        
        for pred in predictions[:max_files]:
            if pred.confidence < confidence_threshold:
                logger.debug(f"Skipping {pred.file_path} (confidence {pred.confidence} < {confidence_threshold})")
                continue
            
            try:
                file_data = self._load_file(pred)
                if file_data:
                    loaded.append(file_data)
            except Exception as e:
                logger.error(f"Failed to load {pred.file_path}: {e}")
        
        # Trigger callbacks
        for callback in self._on_load_callbacks:
            try:
                callback(loaded)
            except Exception as e:
                logger.error(f"Load callback error: {e}")
        
        logger.info(f"Loaded {len(loaded)} files into context")
        return loaded
    
    def _load_file(self, prediction: PredictionResult) -> Optional[Dict[str, Any]]:
        """Load a single file with metadata."""
        file_path = self.project_root / prediction.file_path
        
        if not file_path.exists():
            logger.warning(f"Predicted file not found: {file_path}")
            return None
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            return {
                'path': prediction.file_path,
                'absolute_path': str(file_path),
                'content': content,
                'predicted_action': prediction.predicted_action,
                'confidence': prediction.confidence,
                'reason': prediction.reason,
                'size_bytes': len(content.encode('utf-8')),
                'line_count': len(content.splitlines()),
            }
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return None
    
    async def predict_async(
        self,
        conversation_history: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None,
        top_k: int = 10
    ) -> List[PredictionResult]:
        """Async version of predict method."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            lambda: self.predict(conversation_history, context, top_k)
        )
    
    async def load_predicted_files_async(
        self,
        predictions: List[PredictionResult],
        max_files: int = 5,
        confidence_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Async version of load_predicted_files."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.load_predicted_files(predictions, max_files, confidence_threshold)
        )
    
    def on_predict(self, callback: Callable[[List[PredictionResult]], None]):
        """Register callback for prediction events."""
        self._on_predict_callbacks.append(callback)
        return callback
    
    def on_load(self, callback: Callable[[List[Dict[str, Any]]], None]):
        """Register callback for file load events."""
        self._on_load_callbacks.append(callback)
        return callback
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the prediction cache."""
        return self.prediction_cache.get_stats()
    
    def clear_cache(self, pattern: Optional[str] = None) -> int:
        """
        Clear prediction cache.
        
        Args:
            pattern: Optional pattern to match (clears all if None)
            
        Returns:
            Number of entries cleared
        """
        return self.prediction_cache.invalidate(pattern)
    
    def cleanup(self):
        """Cleanup resources."""
        self.prediction_cache.cleanup_expired()
        if self.predictor.cache:
            self.predictor.cache.cleanup_old()
    
    def export_predictions(
        self,
        predictions: List[PredictionResult],
        output_path: Optional[Path] = None
    ) -> str:
        """
        Export predictions to JSON.
        
        Args:
            predictions: Predictions to export
            output_path: Optional output file path
            
        Returns:
            JSON string of predictions
        """
        data = {
            'predictions': [asdict(p) for p in predictions],
            'total': len(predictions),
            'project_root': str(self.project_root),
        }
        
        json_str = json.dumps(data, indent=2)
        
        if output_path:
            output_path.write_text(json_str)
            logger.info(f"Exported predictions to {output_path}")
        
        return json_str


class ContextManager:
    """
    Manages context for interactive sessions.
    Maintains conversation history and provides predictive loading.
    """
    
    def __init__(self, loader: PredictiveContextLoader, auto_predict: bool = True):
        self.loader = loader
        self.conversation_history: List[Dict[str, str]] = []
        self.auto_predict = auto_predict
        self.last_predictions: List[PredictionResult] = []
        self.loaded_files: List[Dict[str, Any]] = []
    
    def add_message(self, role: str, content: str) -> Optional[List[PredictionResult]]:
        """
        Add a message to the conversation history.
        
        Args:
            role: 'user' or 'assistant'
            content: Message content
            
        Returns:
            Predictions if auto_predict is enabled
        """
        self.conversation_history.append({
            'role': role,
            'content': content,
            'timestamp': str(asyncio.get_event_loop().time()) if asyncio.get_event_loop().is_running() else None
        })
        
        if self.auto_predict and role == 'user':
            predictions = self.loader.predict(self.conversation_history)
            self.last_predictions = predictions
            return predictions
        
        return None
    
    def get_context_files(self, max_files: int = 5) -> List[Dict[str, Any]]:
        """Get predicted files loaded into context."""
        if not self.loaded_files and self.last_predictions:
            self.loaded_files = self.loader.load_predicted_files(
                self.last_predictions,
                max_files=max_files
            )
        return self.loaded_files
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history.clear()
        self.last_predictions.clear()
        self.loaded_files.clear()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of current context state."""
        return {
            'message_count': len(self.conversation_history),
            'last_predictions_count': len(self.last_predictions),
            'loaded_files_count': len(self.loaded_files),
            'loaded_file_paths': [f['path'] for f in self.loaded_files],
        }


def create_loader(
    project_root: str | Path,
    cache_dir: Optional[Path] = None,
    **kwargs
) -> PredictiveContextLoader:
    """
    Factory function to create a configured PredictiveContextLoader.
    
    Args:
        project_root: Project root directory
        cache_dir: Directory for caches (default: .kimi/cache)
        **kwargs: Additional arguments for PredictiveContextLoader
        
    Returns:
        Configured PredictiveContextLoader instance
    """
    project_root = Path(project_root)
    cache_dir = cache_dir or project_root / '.kimi' / 'cache'
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    return PredictiveContextLoader(
        project_root=project_root,
        prediction_cache_path=cache_dir / 'predictions.pkl',
        embedding_cache_dir=cache_dir / 'embeddings',
        **kwargs
    )
