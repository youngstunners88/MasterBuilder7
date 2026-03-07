"""
Embeddings module for semantic code search.
Handles creation and management of code embeddings.
"""

import hashlib
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
from loguru import logger


@dataclass
class CodeEmbedding:
    """Embedding for a code element."""
    id: str
    file_path: str
    element_type: str  # function, class, method, etc.
    name: str
    content: str
    start_line: int
    end_line: int
    embedding: np.ndarray
    language: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (without embedding for serialization)."""
        return {
            'id': self.id,
            'file_path': self.file_path,
            'element_type': self.element_type,
            'name': self.name,
            'content': self.content[:500],  # Truncate for storage
            'start_line': self.start_line,
            'end_line': self.end_line,
            'language': self.language,
            'metadata': self.metadata,
        }


class EmbeddingManager:
    """Manages embeddings for code elements."""
    
    # Models optimized for code understanding
    CODE_MODELS = {
        'default': 'all-MiniLM-L6-v2',
        'code': 'microsoft/codebert-base',
        'code-multi': 'intfloat/multilingual-e5-large',
    }
    
    def __init__(self, model_name: Optional[str] = None, device: Optional[str] = None):
        """
        Initialize embedding manager.
        
        Args:
            model_name: Name of the sentence-transformer model
            device: Device to run on ('cpu', 'cuda', or None for auto)
        """
        self.model_name = model_name or self.CODE_MODELS['default']
        self.device = device
        self.model: Optional[SentenceTransformer] = None
        self._embedding_cache: Dict[str, np.ndarray] = {}
    
    def load_model(self) -> SentenceTransformer:
        """Lazy load the embedding model."""
        if self.model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name, device=self.device)
            logger.info(f"Model loaded on {self.model.device}")
        return self.model
    
    def create_embedding(self, text: str) -> np.ndarray:
        """
        Create embedding for text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as numpy array
        """
        model = self.load_model()
        embedding = model.encode(text, show_progress_bar=False)
        return embedding
    
    def create_code_embedding(
        self,
        file_path: str,
        element_type: str,
        name: str,
        content: str,
        start_line: int,
        end_line: int,
        language: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CodeEmbedding:
        """
        Create embedding for a code element.
        
        Args:
            file_path: Path to the file
            element_type: Type of code element (function, class, etc.)
            name: Name of the element
            content: Source code content
            start_line: Starting line number
            end_line: Ending line number
            language: Programming language
            metadata: Additional metadata
            
        Returns:
            CodeEmbedding object
        """
        # Create rich text representation for embedding
        text_repr = self._create_text_representation(
            element_type, name, content, language
        )
        
        # Generate embedding
        embedding = self.create_embedding(text_repr)
        
        # Generate unique ID
        id_hash = hashlib.sha256(
            f"{file_path}:{name}:{start_line}".encode()
        ).hexdigest()[:16]
        
        return CodeEmbedding(
            id=id_hash,
            file_path=file_path,
            element_type=element_type,
            name=name,
            content=content,
            start_line=start_line,
            end_line=end_line,
            embedding=embedding,
            language=language,
            metadata=metadata or {}
        )
    
    def _create_text_representation(
        self,
        element_type: str,
        name: str,
        content: str,
        language: str
    ) -> str:
        """
        Create rich text representation for better semantic understanding.
        
        Args:
            element_type: Type of code element
            name: Name of the element
            content: Source code
            language: Programming language
            
        Returns:
            Text representation for embedding
        """
        # Extract docstring/comments if present
        docstring = self._extract_docstring(content, language)
        
        # Build representation
        parts = [
            f"Type: {element_type}",
            f"Name: {name}",
            f"Language: {language}",
        ]
        
        if docstring:
            parts.append(f"Documentation: {docstring}")
        
        # Add signature/content summary
        parts.append(f"Code:\n{content[:1000]}")  # Limit code length
        
        return "\n".join(parts)
    
    def _extract_docstring(self, content: str, language: str) -> Optional[str]:
        """Extract docstring or comments from code."""
        if language == 'python':
            # Look for triple-quoted strings
            import re
            patterns = [
                r'"""(.*?)"""',
                r"'''(.*?)'''",
            ]
            for pattern in patterns:
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    return match.group(1).strip()[:500]
        
        elif language in ['javascript', 'typescript']:
            # Look for JSDoc comments
            import re
            match = re.search(r'/\*\*(.*?)\*/', content, re.DOTALL)
            if match:
                doc = match.group(1)
                # Remove leading asterisks
                lines = [line.lstrip(' *') for line in doc.split('\n')]
                return '\n'.join(lines).strip()[:500]
        
        return None
    
    def batch_create_embeddings(
        self,
        elements: List[Dict[str, Any]]
    ) -> List[CodeEmbedding]:
        """
        Create embeddings for multiple elements efficiently.
        
        Args:
            elements: List of element dictionaries
            
        Returns:
            List of CodeEmbedding objects
        """
        model = self.load_model()
        
        # Create text representations
        texts = []
        for elem in elements:
            text = self._create_text_representation(
                elem['element_type'],
                elem['name'],
                elem['content'],
                elem['language']
            )
            texts.append(text)
        
        # Batch encode
        logger.info(f"Creating embeddings for {len(texts)} elements...")
        embeddings = model.encode(texts, show_progress_bar=True)
        
        # Create CodeEmbedding objects
        results = []
        for elem, embedding in zip(elements, embeddings):
            id_hash = hashlib.sha256(
                f"{elem['file_path']}:{elem['name']}:{elem['start_line']}".encode()
            ).hexdigest()[:16]
            
            code_embedding = CodeEmbedding(
                id=id_hash,
                file_path=elem['file_path'],
                element_type=elem['element_type'],
                name=elem['name'],
                content=elem['content'],
                start_line=elem['start_line'],
                end_line=elem['end_line'],
                embedding=embedding,
                language=elem['language'],
                metadata=elem.get('metadata', {})
            )
            results.append(code_embedding)
        
        return results
    
    def compute_similarity(
        self,
        query_embedding: np.ndarray,
        code_embeddings: List[CodeEmbedding]
    ) -> List[Tuple[CodeEmbedding, float]]:
        """
        Compute cosine similarity between query and code embeddings.
        
        Args:
            query_embedding: Query embedding vector
            code_embeddings: List of code embeddings to compare
            
        Returns:
            List of (embedding, similarity_score) tuples sorted by score
        """
        results = []
        query_norm = np.linalg.norm(query_embedding)
        
        for code_emb in code_embeddings:
            emb_norm = np.linalg.norm(code_emb.embedding)
            if emb_norm == 0 or query_norm == 0:
                similarity = 0.0
            else:
                similarity = np.dot(query_embedding, code_emb.embedding) / (query_norm * emb_norm)
            
            results.append((code_emb, float(similarity)))
        
        # Sort by similarity (descending)
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results
    
    def save_embeddings(
        self,
        embeddings: List[CodeEmbedding],
        output_path: Path
    ):
        """
        Save embeddings to disk.
        
        Args:
            embeddings: List of embeddings to save
            output_path: Path to save to
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'model_name': self.model_name,
            'embeddings': [
                {
                    **emb.to_dict(),
                    'embedding': emb.embedding.tolist()
                }
                for emb in embeddings
            ]
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f)
        
        logger.info(f"Saved {len(embeddings)} embeddings to {output_path}")
    
    def load_embeddings(self, input_path: Path) -> List[CodeEmbedding]:
        """
        Load embeddings from disk.
        
        Args:
            input_path: Path to load from
            
        Returns:
            List of CodeEmbedding objects
        """
        with open(input_path, 'r') as f:
            data = json.load(f)
        
        embeddings = []
        for emb_data in data['embeddings']:
            embedding = CodeEmbedding(
                id=emb_data['id'],
                file_path=emb_data['file_path'],
                element_type=emb_data['element_type'],
                name=emb_data['name'],
                content=emb_data['content'],
                start_line=emb_data['start_line'],
                end_line=emb_data['end_line'],
                embedding=np.array(emb_data['embedding']),
                language=emb_data['language'],
                metadata=emb_data.get('metadata', {})
            )
            embeddings.append(embedding)
        
        logger.info(f"Loaded {len(embeddings)} embeddings from {input_path}")
        return embeddings


class QueryExpander:
    """Expands natural language queries for better code search."""
    
    # Synonyms and related terms for common programming concepts
    QUERY_EXPANSIONS = {
        'auth': ['authentication', 'login', 'authorize', 'credential'],
        'db': ['database', 'storage', 'persistence', 'orm', 'model'],
        'api': ['endpoint', 'route', 'controller', 'handler', 'rest'],
        'ui': ['interface', 'component', 'view', 'frontend', 'display'],
        'test': ['spec', 'unittest', 'pytest', 'verify', 'assert'],
        'config': ['settings', 'configuration', 'env', 'environment'],
        'util': ['helper', 'utility', 'common', 'shared', 'tool'],
        'error': ['exception', 'fault', 'failure', 'bug', 'crash'],
        'async': ['promise', 'future', 'concurrent', 'await', 'callback'],
        'http': ['request', 'response', 'web', 'server', 'client'],
    }
    
    def expand(self, query: str) -> List[str]:
        """
        Expand query with synonyms.
        
        Args:
            query: Original query string
            
        Returns:
            List of expanded query variations
        """
        query_lower = query.lower()
        expanded = [query]  # Always include original
        
        for term, synonyms in self.QUERY_EXPANSIONS.items():
            if term in query_lower:
                for synonym in synonyms:
                    expanded_query = query_lower.replace(term, synonym)
                    if expanded_query != query_lower:
                        expanded.append(expanded_query)
        
        return list(set(expanded))
    
    def create_code_specific_query(self, query: str) -> str:
        """
        Enhance query with code-specific context.
        
        Args:
            query: Original query
            
        Returns:
            Enhanced query string
        """
        # Add context hints for better code understanding
        code_hints = []
        
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['function', 'method', 'def']):
            code_hints.append("Type: function")
        
        if any(word in query_lower for word in ['class', 'object', 'type']):
            code_hints.append("Type: class")
        
        if any(word in query_lower for word in ['import', 'require', 'use']):
            code_hints.append("Type: import")
        
        if code_hints:
            return f"{query}\n\nContext:\n" + "\n".join(code_hints)
        
        return query
