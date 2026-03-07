"""
Prediction module for predictive context loader.
Uses embeddings and similarity search to predict which files will be needed.
"""

import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
from loguru import logger

from .cache import EmbeddingCache


@dataclass
class PredictionResult:
    """Result of a prediction."""
    file_path: str
    relevance_score: float
    confidence: float
    reason: str
    predicted_action: str


class ConversationAnalyzer:
    """Analyzes conversation history to extract intent and context."""
    
    # Keywords that suggest file types
    FILE_TYPE_PATTERNS = {
        'test': ['test', 'testing', 'spec', 'pytest', 'unittest'],
        'config': ['config', 'settings', 'env', 'environment', 'yaml', 'json'],
        'model': ['model', 'database', 'schema', 'entity', 'orm'],
        'route': ['route', 'endpoint', 'api', 'controller', 'handler'],
        'view': ['view', 'template', 'component', 'ui', 'frontend'],
        'service': ['service', 'logic', 'business', 'use case'],
        'util': ['util', 'helper', 'common', 'shared', 'lib'],
        'doc': ['doc', 'documentation', 'readme', 'markdown'],
    }
    
    # Action patterns
    ACTION_PATTERNS = {
        'read': ['show', 'display', 'view', 'read', 'get', 'find', 'look'],
        'edit': ['edit', 'modify', 'change', 'update', 'fix', 'refactor'],
        'create': ['create', 'add', 'new', 'implement', 'build', 'write'],
        'delete': ['delete', 'remove', 'drop', 'clean'],
        'test': ['test', 'verify', 'check', 'validate'],
    }
    
    def __init__(self):
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Lazy load the embedding model."""
        if self.model is None:
            logger.info("Loading sentence transformer model...")
            # Using a lightweight but effective model
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Model loaded successfully")
    
    def analyze(self, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Analyze conversation to extract intent and relevant keywords.
        
        Args:
            conversation_history: List of conversation messages with 'role' and 'content'
            
        Returns:
            Dictionary with analysis results
        """
        # Combine all user messages
        user_messages = [
            msg['content'] for msg in conversation_history 
            if msg.get('role') == 'user'
        ]
        combined_text = ' '.join(user_messages).lower()
        
        # Detect file types of interest
        detected_types = []
        for file_type, keywords in self.FILE_TYPE_PATTERNS.items():
            if any(kw in combined_text for kw in keywords):
                detected_types.append(file_type)
        
        # Detect likely action
        detected_action = 'read'  # default
        for action, keywords in self.ACTION_PATTERNS.items():
            if any(kw in combined_text for kw in keywords):
                detected_action = action
                break
        
        # Extract specific file mentions
        file_mentions = self._extract_file_mentions(combined_text)
        
        # Extract code symbols (functions, classes)
        code_symbols = self._extract_code_symbols(combined_text)
        
        # Create embedding of the conversation
        conversation_embedding = self.model.encode(combined_text)
        
        return {
            'detected_file_types': detected_types,
            'detected_action': detected_action,
            'file_mentions': file_mentions,
            'code_symbols': code_symbols,
            'embedding': conversation_embedding,
            'raw_text': combined_text,
            'message_count': len(user_messages)
        }
    
    def _extract_file_mentions(self, text: str) -> List[str]:
        """Extract potential file names mentioned in text."""
        import re
        
        # Match patterns like file.py, src/components/Button.tsx, etc.
        patterns = [
            r'[\w\-/]+\.(py|js|ts|tsx|jsx|rs|go|java|rb|php|cpp|c|h|hpp|yaml|yml|json|md|txt)',
            r'[\w\-]+\.\w{2,4}\b',  # generic file.extension
        ]
        
        mentions = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            mentions.extend(matches)
        
        return list(set(mentions))
    
    def _extract_code_symbols(self, text: str) -> List[str]:
        """Extract code symbols (function names, class names) from text."""
        import re
        
        # Look for patterns like function_name(), ClassName, module.name
        patterns = [
            r'\b([A-Z][a-zA-Z0-9_]*)\b',  # CamelCase classes
            r'\b([a-z_][a-z0-9_]*\(\))',   # snake_case functions
            r'`([^`]+)`',                   # backtick quoted
        ]
        
        symbols = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            symbols.extend(matches)
        
        return list(set(symbols))


class FileIndexer:
    """Indexes project files with their embeddings."""
    
    def __init__(self, project_root: Path, cache: Optional[EmbeddingCache] = None):
        self.project_root = Path(project_root)
        self.cache = cache
        self.analyzer = ConversationAnalyzer()
        self._file_index: Dict[str, Dict[str, Any]] = {}
        self._embeddings_matrix: Optional[np.ndarray] = None
        self._file_paths: List[str] = []
    
    def index_project(self, file_patterns: List[str] = None) -> int:
        """
        Index all relevant files in the project.
        
        Args:
            file_patterns: List of glob patterns to include (default: common code files)
            
        Returns:
            Number of files indexed
        """
        if file_patterns is None:
            file_patterns = [
                '**/*.py', '**/*.js', '**/*.ts', '**/*.tsx', '**/*.jsx',
                '**/*.rs', '**/*.go', '**/*.java', '**/*.rb', '**/*.php',
                '**/*.md', '**/*.yaml', '**/*.yml', '**/*.json'
            ]
        
        files_to_index = []
        for pattern in file_patterns:
            files_to_index.extend(self.project_root.glob(pattern))
        
        # Remove duplicates and filter
        files_to_index = list(set(files_to_index))
        files_to_index = [
            f for f in files_to_index 
            if self._should_index_file(f)
        ]
        
        logger.info(f"Indexing {len(files_to_index)} files...")
        
        for file_path in files_to_index:
            self._index_file(file_path)
        
        # Build embeddings matrix for fast similarity search
        self._build_embeddings_matrix()
        
        logger.info(f"Indexed {len(self._file_index)} files successfully")
        return len(self._file_index)
    
    def _should_index_file(self, file_path: Path) -> bool:
        """Determine if a file should be indexed."""
        # Skip common non-source directories
        skip_dirs = {
            'node_modules', '.git', '__pycache__', '.venv', 'venv',
            'dist', 'build', '.pytest_cache', '.mypy_cache', '.tox',
            'coverage', 'htmlcov', '.kimi', '.cache'
        }
        
        for part in file_path.parts:
            if part in skip_dirs:
                return False
        
        # Skip very large files (>1MB)
        try:
            if file_path.stat().st_size > 1024 * 1024:
                return False
        except:
            return False
        
        return True
    
    def _index_file(self, file_path: Path):
        """Index a single file."""
        try:
            # Check cache first
            if self.cache:
                cached_embedding = self.cache.get_embedding(file_path)
                if cached_embedding is not None:
                    self._file_index[str(file_path)] = {
                        'path': str(file_path),
                        'relative_path': str(file_path.relative_to(self.project_root)),
                        'embedding': cached_embedding,
                        'file_type': file_path.suffix,
                    }
                    return
            
            # Read and process file
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Create a summary of the file
            summary = self._create_file_summary(file_path, content)
            
            # Generate embedding
            embedding = self.analyzer.model.encode(summary)
            
            # Cache the embedding
            if self.cache:
                self.cache.set_embedding(file_path, embedding.tolist())
            
            # Store in index
            self._file_index[str(file_path)] = {
                'path': str(file_path),
                'relative_path': str(file_path.relative_to(self.project_root)),
                'embedding': embedding,
                'file_type': file_path.suffix,
                'summary': summary[:500],  # Keep first 500 chars
            }
            
        except Exception as e:
            logger.warning(f"Failed to index {file_path}: {e}")
    
    def _create_file_summary(self, file_path: Path, content: str) -> str:
        """Create a text summary of a file for embedding."""
        lines = content.split('\n')[:50]  # First 50 lines
        
        summary_parts = [
            f"File: {file_path.name}",
            f"Path: {file_path}",
            f"Type: {file_path.suffix}",
            "Content preview:",
        ]
        
        # Extract key elements based on file type
        if file_path.suffix in ['.py', '.js', '.ts', '.tsx', '.jsx']:
            # Extract class and function definitions
            import re
            for line in lines:
                if re.match(r'^(class|def|function|const|let|var|interface|type)\s+', line.strip()):
                    summary_parts.append(line.strip())
        
        summary_parts.extend(lines[:30])  # Add first 30 lines
        
        return '\n'.join(summary_parts)
    
    def _build_embeddings_matrix(self):
        """Build numpy matrix of all embeddings for fast similarity search."""
        if not self._file_index:
            return
        
        self._file_paths = list(self._file_index.keys())
        embeddings = [
            self._file_index[path]['embedding'] 
            for path in self._file_paths
        ]
        self._embeddings_matrix = np.array(embeddings)
    
    def search_similar(self, query_embedding: np.ndarray, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Find most similar files to query embedding.
        
        Args:
            query_embedding: The embedding to search for
            top_k: Number of results to return
            
        Returns:
            List of file info dicts with similarity scores
        """
        if self._embeddings_matrix is None or len(self._file_index) == 0:
            return []
        
        # Compute cosine similarity
        similarities = np.dot(self._embeddings_matrix, query_embedding) / (
            np.linalg.norm(self._embeddings_matrix, axis=1) * 
            np.linalg.norm(query_embedding)
        )
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            file_path = self._file_paths[idx]
            file_info = self._file_index[file_path].copy()
            file_info['similarity_score'] = float(similarities[idx])
            # Remove embedding to keep result serializable
            file_info.pop('embedding', None)
            results.append(file_info)
        
        return results
    
    def get_indexed_files(self) -> List[str]:
        """Get list of all indexed file paths."""
        return list(self._file_index.keys())
    
    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get info for a specific file."""
        info = self._file_index.get(file_path)
        if info:
            info = info.copy()
            info.pop('embedding', None)
        return info


class Predictor:
    """Main prediction engine combining analysis and search."""
    
    def __init__(self, project_root: Path, cache: Optional[EmbeddingCache] = None):
        self.project_root = Path(project_root)
        self.analyzer = ConversationAnalyzer()
        self.indexer = FileIndexer(project_root, cache)
        self.cache = cache
    
    def predict(self, conversation_history: List[Dict[str, str]], 
                top_k: int = 10) -> List[PredictionResult]:
        """
        Predict which files will be needed based on conversation.
        
        Args:
            conversation_history: List of conversation messages
            top_k: Number of predictions to return
            
        Returns:
            List of prediction results
        """
        # Analyze conversation
        analysis = self.analyzer.analyze(conversation_history)
        
        # Search for similar files
        similar_files = self.indexer.search_similar(
            analysis['embedding'], 
            top_k=top_k * 2  # Get more to filter/boost
        )
        
        # Score and rank predictions
        predictions = self._score_predictions(
            similar_files, 
            analysis,
            top_k
        )
        
        return predictions
    
    def _score_predictions(self, similar_files: List[Dict[str, Any]], 
                          analysis: Dict[str, Any],
                          top_k: int) -> List[PredictionResult]:
        """Score and rank file predictions."""
        scored = []
        
        for file_info in similar_files:
            base_score = file_info.get('similarity_score', 0)
            confidence = base_score
            reasons = []
            
            # Boost score based on file type match
            file_type = self._categorize_file(file_info['file_type'])
            if file_type in analysis['detected_file_types']:
                base_score += 0.2
                reasons.append(f"Matches requested file type: {file_type}")
            
            # Boost for file mentions
            for mention in analysis['file_mentions']:
                if mention.lower() in file_info['relative_path'].lower():
                    base_score += 0.3
                    reasons.append(f"Matches mentioned file: {mention}")
                    break
            
            # Adjust confidence based on number of factors
            confidence = min(0.95, base_score)
            
            # Determine predicted action
            predicted_action = analysis['detected_action']
            
            scored.append(PredictionResult(
                file_path=file_info['relative_path'],
                relevance_score=round(base_score, 3),
                confidence=round(confidence, 3),
                reason='; '.join(reasons) if reasons else 'Semantic similarity match',
                predicted_action=predicted_action
            ))
        
        # Sort by relevance score
        scored.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return scored[:top_k]
    
    def _categorize_file(self, extension: str) -> str:
        """Categorize file by extension."""
        ext_map = {
            '.py': 'code',
            '.js': 'code',
            '.ts': 'code',
            '.tsx': 'code',
            '.jsx': 'code',
            '.rs': 'code',
            '.go': 'code',
            '.java': 'code',
            '.rb': 'code',
            '.php': 'code',
            '.test.py': 'test',
            '.spec.js': 'test',
            '.test.ts': 'test',
            '.md': 'doc',
            '.yaml': 'config',
            '.yml': 'config',
            '.json': 'config',
        }
        return ext_map.get(extension, 'other')
    
    def index_project(self, file_patterns: List[str] = None) -> int:
        """Index the project files."""
        return self.indexer.index_project(file_patterns)
