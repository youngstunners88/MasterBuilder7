#!/usr/bin/env python3
"""
APEX Pattern Database (Vector Store)

Stores extracted successful patterns from builds for reuse and learning.
Uses vector embeddings for semantic similarity search with multiple storage backends.

Features:
- Vector storage using ChromaDB or FAISS
- Similarity search with cosine similarity
- Pattern versioning and lineage tracking
- Success score tracking with usage analytics
- Category-based organization
- Redis caching for hot patterns
- SQLite fallback for resilience

Author: APEX Evolution Team
Version: 1.0.0
"""

import asyncio
import hashlib
import json
import logging
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, AsyncGenerator, Callable
from contextlib import asynccontextmanager
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger('PatternDatabase')

# Optional imports with graceful fallback
VECTOR_STORE_AVAILABLE = False
EMBEDDINGS_AVAILABLE = False
REDIS_AVAILABLE = False
NUMPY_AVAILABLE = False

# NumPy (required for vector operations)
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    logger.warning("numpy not available. Vector operations will be limited.")
    # Minimal numpy replacement for basic operations
    class MockLinalg:
        @staticmethod
        def norm(a):
            return sum(x ** 2 for x in a) ** 0.5
    
    class MockNumpy:
        ndarray = list
        linalg = MockLinalg()
        
        @staticmethod
        def array(data, dtype=None):
            return list(data)
        @staticmethod
        def dot(a, b):
            return sum(x * y for x, y in zip(a, b))
        @staticmethod
        def zeros(dim):
            return [0.0] * dim
    np = MockNumpy()

# ChromaDB
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    VECTOR_STORE_AVAILABLE = True
    VECTOR_BACKEND = "chromadb"
except ImportError:
    logger.debug("ChromaDB not available")

# FAISS fallback
try:
    import faiss
    if not VECTOR_STORE_AVAILABLE:
        VECTOR_BACKEND = "faiss"
        VECTOR_STORE_AVAILABLE = True
except ImportError:
    logger.debug("FAISS not available")

# Sentence Transformers
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    logger.debug("sentence-transformers not available")

# OpenAI embeddings fallback
try:
    import openai
    if not EMBEDDINGS_AVAILABLE:
        EMBEDDINGS_AVAILABLE = True
except ImportError:
    logger.debug("openai not available")

# Redis
try:
    import redis.asyncio as aioredis
    from redis.asyncio import Redis
    REDIS_AVAILABLE = True
except ImportError:
    logger.debug("redis not available")


class PatternType(Enum):
    """Pattern type classification"""
    COMPONENT = "component"           # React/Vue components
    API_ENDPOINT = "api_endpoint"     # FastAPI/Express endpoints
    DATABASE_MODEL = "database_model" # SQLAlchemy/Prisma models
    INTEGRATION = "integration"       # Third-party integrations
    TEST = "test"                     # Test patterns
    UTILITY = "utility"               # Utility functions
    CONFIG = "config"                 # Configuration patterns
    HOOK = "hook"                     # React/Vue hooks
    MIDDLEWARE = "middleware"         # Middleware patterns
    WORKFLOW = "workflow"             # Build/deployment workflows


class PatternStatus(Enum):
    """Pattern lifecycle status"""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"
    ARCHIVED = "archived"


@dataclass
class PatternVersion:
    """Pattern version information"""
    version: str
    parent_id: Optional[str] = None
    changes: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PatternMetadata:
    """Extended pattern metadata"""
    language: str = ""
    framework: str = ""
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    complexity_score: float = 0.0
    lines_of_code: int = 0
    author: str = ""
    source_file: str = ""
    source_url: str = ""
    license: str = "MIT"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PatternMetadata':
        return cls(**data)


@dataclass
class Pattern:
    """
    Core pattern data structure
    
    Attributes:
        id: Unique pattern identifier
        type: Pattern classification
        content: The actual code/content
        embedding: Vector embedding for similarity search
        success_score: Quality score (0-100)
        usage_count: How many times pattern was used
        created_at: Creation timestamp
        metadata: Additional pattern metadata
        status: Pattern lifecycle status
        version: Pattern version info
    """
    id: str
    type: PatternType
    content: str
    embedding: List[float] = field(default_factory=list)
    success_score: float = 0.0
    usage_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: PatternMetadata = field(default_factory=PatternMetadata)
    status: PatternStatus = PatternStatus.ACTIVE
    version: PatternVersion = field(default_factory=lambda: PatternVersion("1.0.0"))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert pattern to dictionary"""
        return {
            'id': self.id,
            'type': self.type.value,
            'content': self.content,
            'embedding': self.embedding,
            'success_score': self.success_score,
            'usage_count': self.usage_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'metadata': self.metadata.to_dict(),
            'status': self.status.value,
            'version': asdict(self.version)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Pattern':
        """Create pattern from dictionary"""
        return cls(
            id=data['id'],
            type=PatternType(data['type']),
            content=data['content'],
            embedding=data.get('embedding', []),
            success_score=data.get('success_score', 0.0),
            usage_count=data.get('usage_count', 0),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            metadata=PatternMetadata.from_dict(data.get('metadata', {})),
            status=PatternStatus(data.get('status', 'active')),
            version=PatternVersion(**data.get('version', {'version': '1.0.0'}))
        )
    
    def compute_hash(self) -> str:
        """Compute content hash for deduplication"""
        return hashlib.sha256(self.content.encode()).hexdigest()[:16]


@dataclass
class SearchResult:
    """Pattern search result with similarity score"""
    pattern: Pattern
    similarity_score: float
    matched_terms: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'pattern': self.pattern.to_dict(),
            'similarity_score': self.similarity_score,
            'matched_terms': self.matched_terms
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchResult':
        return cls(
            pattern=Pattern.from_dict(data['pattern']),
            similarity_score=data['similarity_score'],
            matched_terms=data.get('matched_terms', [])
        )


@dataclass
class BuildResult:
    """Build result for pattern extraction"""
    build_id: str
    success: bool
    score: float  # 0-100
    files_changed: List[str]
    evaluation_grade: str  # EXCELLENT, GOOD, FAIR, POOR
    consensus_approved: bool
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class EmbeddingGenerator:
    """
    Generate embeddings for pattern content
    
    Supports multiple backends:
    - sentence-transformers (default)
    - OpenAI embeddings
    - Simple hash-based fallback
    """
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        openai_model: str = "text-embedding-3-small",
        cache_enabled: bool = True
    ):
        self.model_name = model_name
        self.openai_model = openai_model
        self.cache_enabled = cache_enabled
        self._model = None
        self._cache: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()
        
        # Initialize model if available
        if EMBEDDINGS_AVAILABLE:
            try:
                self._model = SentenceTransformer(model_name)
                logger.info(f"Embedding model loaded: {model_name}")
            except Exception as e:
                logger.warning(f"Failed to load sentence-transformers: {e}")
    
    async def generate(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32
    ) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings for text(s)
        
        Args:
            texts: Single text or list of texts
            batch_size: Batch size for processing
            
        Returns:
            Embedding vector(s)
        """
        is_single = isinstance(texts, str)
        if is_single:
            texts = [texts]
        
        # Check cache
        if self.cache_enabled:
            embeddings = []
            uncached_texts = []
            uncached_indices = []
            
            for i, text in enumerate(texts):
                text_hash = hashlib.md5(text.encode()).hexdigest()
                if text_hash in self._cache:
                    embeddings.append((i, self._cache[text_hash]))
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)
            
            if uncached_texts:
                new_embeddings = await self._generate_batch(uncached_texts, batch_size)
                
                # Update cache
                for idx, text, emb in zip(uncached_indices, uncached_texts, new_embeddings):
                    text_hash = hashlib.md5(text.encode()).hexdigest()
                    self._cache[text_hash] = emb
                    embeddings.append((idx, emb))
            
            # Sort by original index
            embeddings.sort(key=lambda x: x[0])
            result = [emb for _, emb in embeddings]
        else:
            result = await self._generate_batch(texts, batch_size)
        
        return result[0] if is_single else result
    
    async def _generate_batch(
        self,
        texts: List[str],
        batch_size: int
    ) -> List[List[float]]:
        """Generate embeddings for a batch of texts"""
        if self._model:
            # Use sentence-transformers
            embeddings = self._model.encode(
                texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                show_progress_bar=False
            )
            return embeddings.tolist()
        
        # Fallback: simple hash-based embeddings (not semantic, just for structure)
        logger.warning("Using fallback embedding generation (not semantic)")
        return self._fallback_embeddings(texts)
    
    def _fallback_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Fallback embedding using character n-gram hashing
        Not semantic, but provides some structure for search
        """
        dim = 128
        embeddings = []
        
        for text in texts:
            # Simple character n-gram feature extraction
            vec = np.zeros(dim)
            text_lower = text.lower()
            
            # Character bigrams
            for i in range(len(text_lower) - 1):
                bigram = text_lower[i:i+2]
                idx = hash(bigram) % dim
                vec[idx] += 1
            
            # Keyword features
            keywords = ['def ', 'class ', 'import ', 'return', 'async', 'await',
                       'function', 'const', 'let', 'var', 'export', 'default']
            for kw in keywords:
                if kw in text_lower:
                    idx = hash(kw) % dim
                    vec[idx] += 5
            
            # Normalize
            norm = np.linalg.norm(vec)
            if norm > 0:
                if NUMPY_AVAILABLE:
                    vec = vec / norm
                    embeddings.append(vec.tolist())
                else:
                    embeddings.append([v / norm for v in vec])
            else:
                embeddings.append(vec if NUMPY_AVAILABLE else list(vec))
        
        return embeddings
    
    def clear_cache(self):
        """Clear embedding cache"""
        self._cache.clear()
        logger.info("Embedding cache cleared")


class SQLitePatternStore:
    """SQLite fallback storage with cosine similarity search"""
    
    def __init__(self, db_path: str = "/tmp/pattern_db.sqlite"):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    def _init_db(self):
        """Initialize SQLite database"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding BLOB,
                success_score REAL DEFAULT 0,
                usage_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}',
                status TEXT DEFAULT 'active',
                version TEXT DEFAULT '1.0.0'
            )
        """)
        
        # Pattern content hash for deduplication
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pattern_hashes (
                content_hash TEXT PRIMARY KEY,
                pattern_id TEXT NOT NULL,
                FOREIGN KEY (pattern_id) REFERENCES patterns(id)
            )
        """)
        
        # Usage tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pattern_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id TEXT NOT NULL,
                build_id TEXT,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                context TEXT,
                FOREIGN KEY (pattern_id) REFERENCES patterns(id)
            )
        """)
        
        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_patterns_status ON patterns(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_patterns_score ON patterns(success_score DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_patterns_created ON patterns(created_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_pattern ON pattern_usage(pattern_id)")
        
        conn.commit()
        logger.info(f"SQLite pattern store initialized: {self.db_path}")
    
    def store(self, pattern: Pattern) -> bool:
        """Store pattern in SQLite"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check for duplicate
            content_hash = pattern.compute_hash()
            cursor.execute(
                "SELECT pattern_id FROM pattern_hashes WHERE content_hash = ?",
                (content_hash,)
            )
            if cursor.fetchone():
                logger.debug(f"Pattern with hash {content_hash} already exists")
                return False
            
            # Store pattern
            cursor.execute("""
                INSERT OR REPLACE INTO patterns 
                (id, type, content, embedding, success_score, usage_count, 
                 created_at, updated_at, metadata, status, version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pattern.id,
                pattern.type.value,
                pattern.content,
                json.dumps(pattern.embedding) if pattern.embedding else None,
                pattern.success_score,
                pattern.usage_count,
                pattern.created_at.isoformat(),
                pattern.updated_at.isoformat(),
                json.dumps(pattern.metadata.to_dict()),
                pattern.status.value,
                pattern.version.version
            ))
            
            # Store hash
            cursor.execute("""
                INSERT OR IGNORE INTO pattern_hashes (content_hash, pattern_id)
                VALUES (?, ?)
            """, (content_hash, pattern.id))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"SQLite store error: {e}")
            return False
    
    def get(self, pattern_id: str) -> Optional[Pattern]:
        """Retrieve pattern by ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM patterns WHERE id = ?", (pattern_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_pattern(row)
            return None
        except Exception as e:
            logger.error(f"SQLite get error: {e}")
            return None
    
    def search_similar(
        self,
        query_embedding: List[float],
        pattern_type: Optional[PatternType] = None,
        top_k: int = 5,
        min_score: float = 0.0
    ) -> List[Tuple[Pattern, float]]:
        """
        Search for similar patterns using cosine similarity
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Build query
            query = "SELECT * FROM patterns WHERE embedding IS NOT NULL"
            params = []
            
            if pattern_type:
                query += " AND type = ?"
                params.append(pattern_type.value)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Calculate similarities
            results = []
            query_vec = np.array(query_embedding)
            
            for row in rows:
                emb_json = row['embedding']
                if emb_json:
                    pattern_vec = np.array(json.loads(emb_json))
                    similarity = self._cosine_similarity(query_vec, pattern_vec)
                    
                    if similarity >= min_score:
                        pattern = self._row_to_pattern(row)
                        results.append((pattern, similarity))
            
            # Sort by similarity and return top_k
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"SQLite search error: {e}")
            return []
    
    def search_by_type(
        self,
        pattern_type: PatternType,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50
    ) -> List[Pattern]:
        """Search patterns by type with optional filters"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = "SELECT * FROM patterns WHERE type = ?"
            params = [pattern_type.value]
            
            if filters:
                if 'min_score' in filters:
                    query += " AND success_score >= ?"
                    params.append(filters['min_score'])
                if 'status' in filters:
                    query += " AND status = ?"
                    params.append(filters['status'])
            
            query += " ORDER BY success_score DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [self._row_to_pattern(row) for row in rows]
        except Exception as e:
            logger.error(f"SQLite search_by_type error: {e}")
            return []
    
    def update_success_score(self, pattern_id: str, score: float) -> bool:
        """Update pattern success score"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE patterns 
                SET success_score = ?, updated_at = ?
                WHERE id = ?
            """, (score, datetime.utcnow().isoformat(), pattern_id))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"SQLite update score error: {e}")
            return False
    
    def increment_usage(self, pattern_id: str, build_id: Optional[str] = None) -> bool:
        """Increment pattern usage count"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE patterns 
                SET usage_count = usage_count + 1, updated_at = ?
                WHERE id = ?
            """, (datetime.utcnow().isoformat(), pattern_id))
            
            # Record usage
            cursor.execute("""
                INSERT INTO pattern_usage (pattern_id, build_id)
                VALUES (?, ?)
            """, (pattern_id, build_id))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"SQLite increment usage error: {e}")
            return False
    
    def get_trending(
        self,
        time_window: timedelta = timedelta(days=7),
        limit: int = 10
    ) -> List[Tuple[Pattern, int]]:
        """Get trending patterns by recent usage"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cutoff = (datetime.utcnow() - time_window).isoformat()
            
            cursor.execute("""
                SELECT pattern_id, COUNT(*) as usage_count
                FROM pattern_usage
                WHERE used_at > ?
                GROUP BY pattern_id
                ORDER BY usage_count DESC
                LIMIT ?
            """, (cutoff, limit))
            
            rows = cursor.fetchall()
            results = []
            
            for row in rows:
                pattern = self.get(row['pattern_id'])
                if pattern:
                    results.append((pattern, row['usage_count']))
            
            return results
        except Exception as e:
            logger.error(f"SQLite trending error: {e}")
            return []
    
    def delete(self, pattern_id: str) -> bool:
        """Delete pattern"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Delete related records first
            cursor.execute("DELETE FROM pattern_usage WHERE pattern_id = ?", (pattern_id,))
            cursor.execute("DELETE FROM pattern_hashes WHERE pattern_id = ?", (pattern_id,))
            cursor.execute("DELETE FROM patterns WHERE id = ?", (pattern_id,))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"SQLite delete error: {e}")
            return False
    
    def _row_to_pattern(self, row: sqlite3.Row) -> Pattern:
        """Convert database row to Pattern object"""
        embedding = None
        if row['embedding']:
            embedding = json.loads(row['embedding'])
        
        metadata = PatternMetadata()
        if row['metadata']:
            metadata = PatternMetadata.from_dict(json.loads(row['metadata']))
        
        return Pattern(
            id=row['id'],
            type=PatternType(row['type']),
            content=row['content'],
            embedding=embedding or [],
            success_score=row['success_score'],
            usage_count=row['usage_count'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            metadata=metadata,
            status=PatternStatus(row['status']),
            version=PatternVersion(row['version'])
        )
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))


class ChromaDBStore:
    """ChromaDB vector store implementation"""
    
    def __init__(self, collection_name: str = "patterns", persist_dir: str = "./chroma_db"):
        self.collection_name = collection_name
        self.persist_dir = persist_dir
        self._client = None
        self._collection = None
        
        if VECTOR_STORE_AVAILABLE and VECTOR_BACKEND == "chromadb":
            self._init_chroma()
    
    def _init_chroma(self):
        """Initialize ChromaDB client"""
        try:
            os.makedirs(self.persist_dir, exist_ok=True)
            
            self._client = chromadb.Client(
                ChromaSettings(
                    persist_directory=self.persist_dir,
                    anonymized_telemetry=False
                )
            )
            
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            
            logger.info(f"ChromaDB store initialized: {self.persist_dir}")
        except Exception as e:
            logger.error(f"ChromaDB init error: {e}")
            self._client = None
            self._collection = None
    
    def is_available(self) -> bool:
        return self._collection is not None
    
    def store(self, pattern: Pattern) -> bool:
        """Store pattern in ChromaDB"""
        if not self._collection:
            return False
        
        try:
            self._collection.add(
                ids=[pattern.id],
                embeddings=[pattern.embedding] if pattern.embedding else None,
                documents=[pattern.content],
                metadatas=[{
                    'type': pattern.type.value,
                    'success_score': pattern.success_score,
                    'usage_count': pattern.usage_count,
                    'status': pattern.status.value,
                    'created_at': pattern.created_at.isoformat(),
                    'metadata': json.dumps(pattern.metadata.to_dict())
                }]
            )
            return True
        except Exception as e:
            logger.error(f"ChromaDB store error: {e}")
            return False
    
    def search_similar(
        self,
        query_embedding: List[float],
        pattern_type: Optional[PatternType] = None,
        top_k: int = 5,
        min_score: float = 0.0
    ) -> List[Tuple[str, float]]:
        """
        Search for similar patterns
        Returns list of (pattern_id, score) tuples
        """
        if not self._collection:
            return []
        
        try:
            where_filter = None
            if pattern_type:
                where_filter = {"type": pattern_type.value}
            
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter
            )
            
            patterns = []
            if results['ids']:
                for i, pattern_id in enumerate(results['ids'][0]):
                    distance = results['distances'][0][i]
                    # ChromaDB returns distance, convert to similarity
                    similarity = 1.0 - distance
                    if similarity >= min_score:
                        patterns.append((pattern_id, similarity))
            
            return patterns
        except Exception as e:
            logger.error(f"ChromaDB search error: {e}")
            return []
    
    def delete(self, pattern_id: str) -> bool:
        """Delete pattern from ChromaDB"""
        if not self._collection:
            return False
        
        try:
            self._collection.delete(ids=[pattern_id])
            return True
        except Exception as e:
            logger.error(f"ChromaDB delete error: {e}")
            return False


class PatternDatabase:
    """
    Main Pattern Database with vector storage, caching, and fallback
    
    Architecture:
    - Primary: ChromaDB or FAISS for vector search
    - Fallback: SQLite with cosine similarity
    - Cache: Redis for hot patterns
    - Embeddings: sentence-transformers or OpenAI
    
    Features:
    - Async operations throughout
    - Pattern versioning and lineage
    - Success tracking and analytics
    - Category-based organization
    - Automatic extraction from builds
    """
    
    # Redis key prefixes
    REDIS_PREFIX = "apex:pattern:"
    REDIS_HOT_PATTERNS = "apex:patterns:hot"
    REDIS_TRENDING = "apex:patterns:trending"
    
    def __init__(
        self,
        vector_store_path: str = "./pattern_vectors",
        sqlite_path: str = "/tmp/pattern_db.sqlite",
        redis_url: Optional[str] = None,
        embedding_model: str = "all-MiniLM-L6-v2",
        cache_ttl: int = 3600,
        enable_chroma: bool = True
    ):
        """
        Initialize Pattern Database
        
        Args:
            vector_store_path: Path for vector store persistence
            sqlite_path: Path for SQLite fallback
            redis_url: Redis connection URL
            embedding_model: Name of embedding model
            cache_ttl: Cache TTL in seconds
            enable_chroma: Whether to use ChromaDB
        """
        self.vector_store_path = vector_store_path
        self.sqlite_path = sqlite_path
        self.cache_ttl = cache_ttl
        self._redis: Optional[Redis] = None
        
        # Initialize embedding generator
        self.embedder = EmbeddingGenerator(model_name=embedding_model)
        
        # Initialize storage backends
        self._sqlite = SQLitePatternStore(sqlite_path)
        
        self._chroma: Optional[ChromaDBStore] = None
        if enable_chroma and VECTOR_STORE_AVAILABLE and VECTOR_BACKEND == "chromadb":
            self._chroma = ChromaDBStore(
                collection_name="patterns",
                persist_dir=vector_store_path
            )
        
        # Initialize Redis if available
        if REDIS_AVAILABLE and redis_url:
            try:
                self._redis = aioredis.from_url(redis_url, decode_responses=True)
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
        
        logger.info("PatternDatabase initialized")
    
    async def connect(self) -> bool:
        """Connect to all storage backends"""
        # Test Redis connection
        if self._redis:
            try:
                await self._redis.ping()
                logger.info("Redis connected")
            except Exception as e:
                logger.warning(f"Redis ping failed: {e}")
                self._redis = None
        
        return True
    
    async def disconnect(self):
        """Disconnect from all backends"""
        if self._redis:
            await self._redis.close()
            self._redis = None
    
    # ==================== Pattern CRUD Operations ====================
    
    async def add_pattern(
        self,
        pattern: Pattern,
        generate_embedding: bool = True
    ) -> bool:
        """
        Add a new pattern to the database
        
        Args:
            pattern: Pattern to add
            generate_embedding: Whether to generate embedding if missing
            
        Returns:
            True if successful
        """
        # Generate embedding if needed
        if generate_embedding and not pattern.embedding:
            pattern.embedding = await self.embedder.generate(pattern.content)
        
        # Store in SQLite (always)
        success = self._sqlite.store(pattern)
        
        # Store in ChromaDB if available
        if success and self._chroma and self._chroma.is_available():
            chroma_success = self._chroma.store(pattern)
            if not chroma_success:
                logger.warning(f"Failed to store pattern in ChromaDB: {pattern.id}")
        
        # Cache in Redis
        if success and self._redis:
            await self._cache_pattern(pattern)
        
        return success
    
    async def get_pattern(self, pattern_id: str) -> Optional[Pattern]:
        """
        Retrieve pattern by ID
        
        Args:
            pattern_id: Pattern identifier
            
        Returns:
            Pattern if found, None otherwise
        """
        # Check cache first
        if self._redis:
            cached = await self._get_cached_pattern(pattern_id)
            if cached:
                return cached
        
        # Get from SQLite
        pattern = self._sqlite.get(pattern_id)
        
        # Cache if found
        if pattern and self._redis:
            await self._cache_pattern(pattern)
        
        return pattern
    
    async def search_similar(
        self,
        query: Union[str, List[float]],
        pattern_type: Optional[PatternType] = None,
        top_k: int = 5,
        min_score: float = 0.7,
        use_cache: bool = True
    ) -> List[SearchResult]:
        """
        Search for similar patterns
        
        Args:
            query: Search query text or embedding vector
            pattern_type: Filter by pattern type
            top_k: Number of results to return
            min_score: Minimum similarity score
            use_cache: Whether to use cache
            
        Returns:
            List of search results
        """
        # Generate embedding if query is text
        if isinstance(query, str):
            query_embedding = await self.embedder.generate(query)
        else:
            query_embedding = query
        
        # Check cache
        cache_key = None
        if use_cache and self._redis and isinstance(query, str):
            cache_key = f"search:{hashlib.md5(query.encode()).hexdigest()}:{pattern_type.value if pattern_type else 'all'}:{top_k}"
            cached = await self._redis.get(f"{self.REDIS_PREFIX}{cache_key}")
            if cached:
                return [SearchResult.from_dict(r) for r in json.loads(cached)]
        
        results = []
        
        # Try ChromaDB first
        if self._chroma and self._chroma.is_available():
            chroma_results = self._chroma.search_similar(
                query_embedding, pattern_type, top_k, min_score
            )
            for pattern_id, score in chroma_results:
                pattern = await self.get_pattern(pattern_id)
                if pattern:
                    results.append(SearchResult(pattern, score))
        
        # Fallback to SQLite
        if not results:
            sqlite_results = self._sqlite.search_similar(
                query_embedding, pattern_type, top_k, min_score
            )
            for pattern, score in sqlite_results:
                results.append(SearchResult(pattern, score))
        
        # Cache results
        if cache_key and self._redis:
            await self._redis.setex(
                f"{self.REDIS_PREFIX}{cache_key}",
                self.cache_ttl,
                json.dumps([r.to_dict() for r in results])
            )
        
        return results
    
    async def search_by_type(
        self,
        pattern_type: PatternType,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50,
        use_cache: bool = True
    ) -> List[Pattern]:
        """
        Search patterns by type with optional filters
        
        Args:
            pattern_type: Type of patterns to search
            filters: Optional filters (min_score, status, etc.)
            limit: Maximum results
            use_cache: Whether to use cache
            
        Returns:
            List of matching patterns
        """
        # Check cache
        cache_key = None
        if use_cache and self._redis:
            filter_hash = hashlib.md5(json.dumps(filters, sort_keys=True).encode()).hexdigest()[:8]
            cache_key = f"type:{pattern_type.value}:{filter_hash}:{limit}"
            cached = await self._redis.get(f"{self.REDIS_PREFIX}{cache_key}")
            if cached:
                return [Pattern.from_dict(p) for p in json.loads(cached)]
        
        # Search in SQLite
        patterns = self._sqlite.search_by_type(pattern_type, filters, limit)
        
        # Cache results
        if cache_key and self._redis and patterns:
            await self._redis.setex(
                f"{self.REDIS_PREFIX}{cache_key}",
                self.cache_ttl,
                json.dumps([p.to_dict() for p in patterns])
            )
        
        return patterns
    
    async def update_success_score(
        self,
        pattern_id: str,
        score: float,
        build_id: Optional[str] = None
    ) -> bool:
        """
        Update pattern success score
        
        Args:
            pattern_id: Pattern identifier
            score: New success score (0-100)
            build_id: Associated build ID
            
        Returns:
            True if successful
        """
        # Update in SQLite
        success = self._sqlite.update_success_score(pattern_id, score)
        
        # Update usage
        if success and build_id:
            self._sqlite.increment_usage(pattern_id, build_id)
        
        # Invalidate cache
        if success and self._redis:
            await self._invalidate_pattern_cache(pattern_id)
        
        return success
    
    async def delete_pattern(self, pattern_id: str) -> bool:
        """
        Delete pattern from all storage
        
        Args:
            pattern_id: Pattern identifier
            
        Returns:
            True if deleted
        """
        # Delete from ChromaDB
        if self._chroma and self._chroma.is_available():
            self._chroma.delete(pattern_id)
        
        # Delete from SQLite
        success = self._sqlite.delete(pattern_id)
        
        # Invalidate cache
        if self._redis:
            await self._invalidate_pattern_cache(pattern_id)
        
        return success
    
    # ==================== Pattern Extraction ====================
    
    async def extract_patterns_from_build(
        self,
        build_result: BuildResult,
        min_score_threshold: float = 90.0
    ) -> List[Pattern]:
        """
        Extract patterns from successful builds
        
        Only extracts from:
        - Builds with score > min_score_threshold
        - Consensus-approved outputs
        - EXCELLENT evaluation grades
        
        Args:
            build_result: Build result data
            min_score_threshold: Minimum score for extraction
            
        Returns:
            List of extracted patterns
        """
        extracted = []
        
        # Check if build qualifies
        if not build_result.success:
            logger.info(f"Build {build_result.build_id} failed, skipping pattern extraction")
            return extracted
        
        if build_result.score < min_score_threshold:
            logger.info(f"Build {build_result.build_id} score {build_result.score} below threshold")
            return extracted
        
        if not build_result.consensus_approved:
            logger.info(f"Build {build_result.build_id} not consensus approved")
            return extracted
        
        if build_result.evaluation_grade != "EXCELLENT":
            logger.info(f"Build {build_result.build_id} grade {build_result.evaluation_grade} not EXCELLENT")
            return extracted
        
        # Extract patterns from files
        for file_path in build_result.files_changed:
            patterns = await self._extract_from_file(file_path, build_result)
            extracted.extend(patterns)
        
        # Store extracted patterns
        for pattern in extracted:
            pattern.success_score = build_result.score
            await self.add_pattern(pattern)
        
        logger.info(f"Extracted {len(extracted)} patterns from build {build_result.build_id}")
        return extracted
    
    async def _extract_from_file(
        self,
        file_path: str,
        build_result: BuildResult
    ) -> List[Pattern]:
        """Extract patterns from a single file"""
        patterns = []
        
        try:
            # Determine pattern type from file extension
            pattern_type = self._detect_pattern_type(file_path)
            
            # Read file content
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            else:
                # File path might be relative or from metadata
                content = build_result.metadata.get('file_contents', {}).get(file_path, '')
            
            if not content:
                return patterns
            
            # Extract components based on type
            if pattern_type == PatternType.COMPONENT:
                patterns.extend(self._extract_components(content, file_path))
            elif pattern_type == PatternType.API_ENDPOINT:
                patterns.extend(self._extract_api_endpoints(content, file_path))
            elif pattern_type == PatternType.DATABASE_MODEL:
                patterns.extend(self._extract_models(content, file_path))
            elif pattern_type == PatternType.TEST:
                patterns.extend(self._extract_tests(content, file_path))
            else:
                # Generic extraction
                pattern = Pattern(
                    id=f"pat_{uuid.uuid4().hex[:12]}",
                    type=pattern_type,
                    content=content,
                    metadata=PatternMetadata(
                        language=self._detect_language(file_path),
                        source_file=file_path,
                        lines_of_code=len(content.split('\n'))
                    )
                )
                patterns.append(pattern)
        
        except Exception as e:
            logger.error(f"Error extracting from {file_path}: {e}")
        
        return patterns
    
    def _extract_components(self, content: str, file_path: str) -> List[Pattern]:
        """Extract React/Vue components"""
        import re
        patterns = []
        
        # Match React function components
        component_pattern = r'(?:export\s+)?(?:default\s+)?function\s+(\w+)[^{]*\{[^}]*\}'
        matches = re.finditer(component_pattern, content, re.DOTALL)
        
        for match in matches:
            component_name = match.group(1)
            if component_name[0].isupper():  # Component names start with uppercase
                pattern = Pattern(
                    id=f"comp_{uuid.uuid4().hex[:12]}",
                    type=PatternType.COMPONENT,
                    content=match.group(0),
                    metadata=PatternMetadata(
                        language="typescript",
                        framework="react",
                        source_file=file_path,
                        tags=["component", component_name]
                    )
                )
                patterns.append(pattern)
        
        return patterns
    
    def _extract_api_endpoints(self, content: str, file_path: str) -> List[Pattern]:
        """Extract FastAPI/Express endpoints"""
        import re
        patterns = []
        
        # Match FastAPI decorators
        endpoint_pattern = r'@app\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)'
        matches = re.finditer(endpoint_pattern, content)
        
        for match in matches:
            method = match.group(1).upper()
            path = match.group(2)
            pattern = Pattern(
                id=f"api_{uuid.uuid4().hex[:12]}",
                type=PatternType.API_ENDPOINT,
                content=match.group(0),
                metadata=PatternMetadata(
                    language="python",
                    framework="fastapi",
                    source_file=file_path,
                    tags=["endpoint", method, path]
                )
            )
            patterns.append(pattern)
        
        return patterns
    
    def _extract_models(self, content: str, file_path: str) -> List[Pattern]:
        """Extract SQLAlchemy/Prisma models"""
        import re
        patterns = []
        
        # Match class definitions inheriting from Base
        model_pattern = r'class\s+(\w+)\s*\(\s*Base\s*\):([^\n]*\n(?:\s+[^\n]*\n)*)'
        matches = re.finditer(model_pattern, content)
        
        for match in matches:
            model_name = match.group(1)
            pattern = Pattern(
                id=f"model_{uuid.uuid4().hex[:12]}",
                type=PatternType.DATABASE_MODEL,
                content=match.group(0),
                metadata=PatternMetadata(
                    language="python",
                    framework="sqlalchemy",
                    source_file=file_path,
                    tags=["model", model_name]
                )
            )
            patterns.append(pattern)
        
        return patterns
    
    def _extract_tests(self, content: str, file_path: str) -> List[Pattern]:
        """Extract test functions"""
        import re
        patterns = []
        
        # Match pytest test functions
        test_pattern = r'def\s+(test_\w+)\s*\([^)]*\):([^\n]*\n(?:\s+[^\n]*\n)*)'
        matches = re.finditer(test_pattern, content)
        
        for match in matches:
            test_name = match.group(1)
            pattern = Pattern(
                id=f"test_{uuid.uuid4().hex[:12]}",
                type=PatternType.TEST,
                content=match.group(0),
                metadata=PatternMetadata(
                    language="python",
                    framework="pytest",
                    source_file=file_path,
                    tags=["test", test_name]
                )
            )
            patterns.append(pattern)
        
        return patterns
    
    # ==================== Analytics ====================
    
    async def get_trending_patterns(
        self,
        time_window: timedelta = timedelta(days=7),
        limit: int = 10
    ) -> List[Tuple[Pattern, int]]:
        """
        Get trending patterns by recent usage
        
        Args:
            time_window: Time window for trending calculation
            limit: Number of patterns to return
            
        Returns:
            List of (pattern, usage_count) tuples
        """
        # Check cache
        if self._redis:
            cache_key = f"trending:{time_window.days}:{limit}"
            cached = await self._redis.get(f"{self.REDIS_PREFIX}{cache_key}")
            if cached:
                data = json.loads(cached)
                return [(Pattern.from_dict(p), c) for p, c in data]
        
        # Get from SQLite
        results = self._sqlite.get_trending(time_window, limit)
        
        # Cache results
        if self._redis and results:
            cache_key = f"trending:{time_window.days}:{limit}"
            await self._redis.setex(
                f"{self.REDIS_PREFIX}{cache_key}",
                300,  # 5 minute cache
                json.dumps([(p.to_dict(), c) for p, c in results])
            )
        
        return results
    
    async def get_pattern_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        # This would be implemented with proper aggregation queries
        return {
            'total_patterns': 0,  # Would query from DB
            'by_type': {},
            'average_success_score': 0.0,
            'total_usage': 0,
            'storage_backends': {
                'sqlite': True,
                'chromadb': self._chroma is not None and self._chroma.is_available(),
                'redis': self._redis is not None
            }
        }
    
    # ==================== Helper Methods ====================
    
    def _detect_pattern_type(self, file_path: str) -> PatternType:
        """Detect pattern type from file path"""
        path_lower = file_path.lower()
        
        if any(x in path_lower for x in ['component', 'page', 'view', '.tsx', '.jsx', '.vue']):
            return PatternType.COMPONENT
        elif any(x in path_lower for x in ['api', 'route', 'endpoint', 'controller']):
            return PatternType.API_ENDPOINT
        elif any(x in path_lower for x in ['model', 'schema', 'entity', 'table']):
            return PatternType.DATABASE_MODEL
        elif any(x in path_lower for x in ['test', 'spec', '__tests__']):
            return PatternType.TEST
        elif any(x in path_lower for x in ['integration', 'service', 'client']):
            return PatternType.INTEGRATION
        elif any(x in path_lower for x in ['util', 'helper', 'lib']):
            return PatternType.UTILITY
        elif any(x in path_lower for x in ['config', 'settings', 'env']):
            return PatternType.CONFIG
        elif any(x in path_lower for x in ['hook', 'composable']):
            return PatternType.HOOK
        elif any(x in path_lower for x in ['middleware', 'interceptor']):
            return PatternType.MIDDLEWARE
        elif any(x in path_lower for x in ['workflow', 'pipeline', 'action']):
            return PatternType.WORKFLOW
        
        return PatternType.UTILITY
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension"""
        ext = Path(file_path).suffix.lower()
        
        lang_map = {
            '.py': 'python',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.vue': 'vue',
            '.go': 'go',
            '.rs': 'rust',
            '.java': 'java',
            '.kt': 'kotlin',
            '.rb': 'ruby',
            '.php': 'php',
            '.cs': 'csharp',
            '.swift': 'swift',
            '.sql': 'sql',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.json': 'json',
            '.md': 'markdown',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
        }
        
        return lang_map.get(ext, 'unknown')
    
    async def _cache_pattern(self, pattern: Pattern):
        """Cache pattern in Redis"""
        if not self._redis:
            return
        
        try:
            key = f"{self.REDIS_PREFIX}{pattern.id}"
            await self._redis.setex(
                key,
                self.cache_ttl,
                json.dumps(pattern.to_dict())
            )
        except Exception as e:
            logger.debug(f"Cache error: {e}")
    
    async def _get_cached_pattern(self, pattern_id: str) -> Optional[Pattern]:
        """Get pattern from cache"""
        if not self._redis:
            return None
        
        try:
            key = f"{self.REDIS_PREFIX}{pattern_id}"
            data = await self._redis.get(key)
            if data:
                return Pattern.from_dict(json.loads(data))
        except Exception as e:
            logger.debug(f"Cache get error: {e}")
        
        return None
    
    async def _invalidate_pattern_cache(self, pattern_id: str):
        """Invalidate pattern cache"""
        if not self._redis:
            return
        
        try:
            await self._redis.delete(f"{self.REDIS_PREFIX}{pattern_id}")
            # Also invalidate search caches (simplified)
            await self._redis.delete(f"{self.REDIS_PREFIX}trending:*")
        except Exception as e:
            logger.debug(f"Cache invalidation error: {e}")


# ==================== Test/Demo Code ====================

async def demo_pattern_database():
    """Demo and test the Pattern Database"""
    print("=" * 60)
    print("APEX Pattern Database Demo")
    print("=" * 60)
    
    # Initialize database
    db = PatternDatabase(
        vector_store_path="./demo_chroma_db",
        sqlite_path="/tmp/demo_pattern_db.sqlite",
        embedding_model="all-MiniLM-L6-v2"
    )
    
    await db.connect()
    
    # Sample patterns
    sample_patterns = [
        Pattern(
            id="comp_react_button_001",
            type=PatternType.COMPONENT,
            content='''
export function Button({ children, onClick, variant = 'primary' }: ButtonProps) {
  return (
    <button 
      className={`btn btn-${variant}`}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
            '''.strip(),
            metadata=PatternMetadata(
                language="typescript",
                framework="react",
                tags=["component", "button", "ui"],
                complexity_score=2.5,
                lines_of_code=10
            )
        ),
        Pattern(
            id="api_fastapi_crud_001",
            type=PatternType.API_ENDPOINT,
            content='''
@app.get("/api/items/{item_id}")
async def get_item(item_id: int, db: Session = Depends(get_db)):
    """Get item by ID"""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.post("/api/items")
async def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    """Create new item"""
    db_item = Item(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item
            '''.strip(),
            metadata=PatternMetadata(
                language="python",
                framework="fastapi",
                tags=["api", "crud", "rest"],
                complexity_score=5.0,
                lines_of_code=18
            )
        ),
        Pattern(
            id="model_sqlalchemy_001",
            type=PatternType.DATABASE_MODEL,
            content='''
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    items = relationship("Item", back_populates="owner")
            '''.strip(),
            metadata=PatternMetadata(
                language="python",
                framework="sqlalchemy",
                tags=["model", "user", "orm"],
                complexity_score=4.0,
                lines_of_code=11
            )
        ),
        Pattern(
            id="test_pytest_async_001",
            type=PatternType.TEST,
            content='''
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_item(client: AsyncClient):
    """Test creating an item"""
    response = await client.post(
        "/api/items",
        json={"name": "Test Item", "price": 9.99}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Item"
    assert data["price"] == 9.99
            '''.strip(),
            metadata=PatternMetadata(
                language="python",
                framework="pytest",
                tags=["test", "async", "api"],
                complexity_score=3.0,
                lines_of_code=13
            )
        ),
        Pattern(
            id="integration_paystack_001",
            type=PatternType.INTEGRATION,
            content='''
class PaystackClient:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.base_url = "https://api.paystack.co"
    
    async def initialize_transaction(
        self,
        email: str,
        amount: int,  # in kobo
        callback_url: str
    ) -> Dict[str, Any]:
        """Initialize a payment transaction"""
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
        data = {
            "email": email,
            "amount": amount,
            "callback_url": callback_url
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/transaction/initialize",
                headers=headers,
                json=data
            ) as response:
                return await response.json()
            '''.strip(),
            metadata=PatternMetadata(
                language="python",
                framework="aiohttp",
                tags=["integration", "payment", "paystack"],
                complexity_score=6.0,
                lines_of_code=28
            )
        )
    ]
    
    # Add patterns
    print("\n📦 Adding sample patterns...")
    for pattern in sample_patterns:
        success = await db.add_pattern(pattern)
        print(f"  {'✓' if success else '✗'} {pattern.id} ({pattern.type.value})")
    
    # Test retrieval
    print("\n🔍 Testing pattern retrieval...")
    retrieved = await db.get_pattern("comp_react_button_001")
    if retrieved:
        print(f"  ✓ Retrieved: {retrieved.id}")
        print(f"    Type: {retrieved.type.value}")
        print(f"    Language: {retrieved.metadata.language}")
    
    # Test semantic search
    print("\n🔎 Testing semantic search...")
    
    # Search for React components
    results = await db.search_similar(
        "React button component with TypeScript",
        pattern_type=PatternType.COMPONENT,
        top_k=3
    )
    print(f"\n  Query: 'React button component with TypeScript'")
    print(f"  Found {len(results)} results:")
    for r in results:
        print(f"    • {r.pattern.id} (score: {r.similarity_score:.3f})")
    
    # Search for API patterns
    results = await db.search_similar(
        "FastAPI CRUD endpoints with SQLAlchemy",
        pattern_type=PatternType.API_ENDPOINT,
        top_k=3
    )
    print(f"\n  Query: 'FastAPI CRUD endpoints with SQLAlchemy'")
    print(f"  Found {len(results)} results:")
    for r in results:
        print(f"    • {r.pattern.id} (score: {r.similarity_score:.3f})")
    
    # Search for database models
    results = await db.search_similar(
        "SQLAlchemy user model with relationships",
        pattern_type=PatternType.DATABASE_MODEL,
        top_k=3
    )
    print(f"\n  Query: 'SQLAlchemy user model with relationships'")
    print(f"  Found {len(results)} results:")
    for r in results:
        print(f"    • {r.pattern.id} (score: {r.similarity_score:.3f})")
    
    # Test type-based search
    print("\n📂 Testing type-based search...")
    python_patterns = await db.search_by_type(
        PatternType.API_ENDPOINT,
        filters={'min_score': 0.0},
        limit=5
    )
    print(f"  Found {len(python_patterns)} API endpoint patterns")
    for p in python_patterns:
        print(f"    • {p.id} ({p.metadata.language})")
    
    # Test success score update
    print("\n📊 Testing success score update...")
    await db.update_success_score("comp_react_button_001", 95.5, build_id="build_001")
    updated = await db.get_pattern("comp_react_button_001")
    print(f"  ✓ Updated score: {updated.success_score}")
    print(f"  ✓ Usage count: {updated.usage_count}")
    
    # Test build extraction
    print("\n🏗️  Testing pattern extraction from build...")
    build_result = BuildResult(
        build_id="build_excellent_001",
        success=True,
        score=95.0,
        files_changed=["src/components/Button.tsx", "src/api/items.py"],
        evaluation_grade="EXCELLENT",
        consensus_approved=True,
        metadata={
            'file_contents': {
                'src/components/Button.tsx': '''
export function IconButton({ icon, onClick }: IconButtonProps) {
  return <button onClick={onClick}><Icon name={icon} /></button>;
}
                '''
            }
        }
    )
    
    extracted = await db.extract_patterns_from_build(build_result)
    print(f"  ✓ Extracted {len(extracted)} patterns from build")
    for p in extracted:
        print(f"    • {p.id} ({p.type.value})")
    
    # Test trending patterns
    print("\n📈 Testing trending patterns...")
    # Increment usage a few times
    for _ in range(3):
        await db.update_success_score("comp_react_button_001", 95.0, build_id="build_trend")
    
    trending = await db.get_trending_patterns(time_window=timedelta(days=1), limit=5)
    print(f"  Found {len(trending)} trending patterns")
    for pattern, count in trending:
        print(f"    • {pattern.id}: {count} uses")
    
    # Test stats
    print("\n📋 Database Statistics:")
    stats = await db.get_pattern_stats()
    print(f"  Storage backends:")
    for backend, available in stats['storage_backends'].items():
        print(f"    • {backend}: {'✓' if available else '✗'}")
    
    # Cleanup
    print("\n🧹 Cleaning up...")
    for pattern in sample_patterns:
        await db.delete_pattern(pattern.id)
    print("  ✓ Deleted sample patterns")
    
    await db.disconnect()
    print("\n✅ Demo completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo_pattern_database())
