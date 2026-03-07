"""
Cache module for predictive context loader.
Handles caching of predictions and embeddings with TTL support.
"""

import json
import hashlib
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from pathlib import Path
import pickle
import threading
from loguru import logger


@dataclass
class CacheEntry:
    """Single cache entry with metadata."""
    key: str
    data: Any
    timestamp: float
    ttl: int  # Time to live in seconds
    access_count: int = 0
    last_accessed: float = 0.0
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return time.time() - self.timestamp > self.ttl
    
    def touch(self):
        """Update access metadata."""
        self.access_count += 1
        self.last_accessed = time.time()


class PredictionCache:
    """
    LRU cache with TTL support for predictions.
    Thread-safe implementation with persistence option.
    """
    
    def __init__(self, ttl_seconds: int = 3600, max_size: int = 1000, 
                 persist_path: Optional[Path] = None):
        """
        Initialize prediction cache.
        
        Args:
            ttl_seconds: Default TTL for cache entries (default: 1 hour)
            max_size: Maximum number of entries in cache
            persist_path: Optional path for cache persistence
        """
        self.ttl = ttl_seconds
        self.max_size = max_size
        self.persist_path = persist_path
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        
        # Load persisted cache if available
        if persist_path and persist_path.exists():
            self._load_from_disk()
    
    def _generate_key(self, conversation_hash: str, context: Dict[str, Any]) -> str:
        """Generate cache key from conversation and context."""
        key_data = f"{conversation_hash}:{json.dumps(context, sort_keys=True, default=str)}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]
    
    def get(self, conversation_history: List[Dict[str, str]], 
            context: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """
        Retrieve cached prediction if available and not expired.
        
        Args:
            conversation_history: List of conversation messages
            context: Optional additional context
            
        Returns:
            Cached data or None if not found/expired
        """
        context = context or {}
        conversation_hash = self._hash_conversation(conversation_history)
        key = self._generate_key(conversation_hash, context)
        
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                logger.debug(f"Cache miss for key: {key}")
                return None
            
            if entry.is_expired():
                logger.debug(f"Cache expired for key: {key}")
                del self._cache[key]
                return None
            
            entry.touch()
            logger.debug(f"Cache hit for key: {key} (access count: {entry.access_count})")
            return entry.data
    
    def set(self, conversation_history: List[Dict[str, str]], 
            data: Any, 
            context: Optional[Dict[str, Any]] = None,
            ttl: Optional[int] = None) -> str:
        """
        Store prediction in cache.
        
        Args:
            conversation_history: List of conversation messages
            data: Data to cache
            context: Optional additional context
            ttl: Optional custom TTL (uses default if not specified)
            
        Returns:
            Cache key
        """
        context = context or {}
        ttl = ttl or self.ttl
        conversation_hash = self._hash_conversation(conversation_history)
        key = self._generate_key(conversation_hash, context)
        
        with self._lock:
            # Evict oldest entries if cache is full
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_oldest()
            
            self._cache[key] = CacheEntry(
                key=key,
                data=data,
                timestamp=time.time(),
                ttl=ttl,
                last_accessed=time.time()
            )
            
            logger.debug(f"Cached prediction with key: {key}, TTL: {ttl}s")
            
            # Persist if path is set
            if self.persist_path:
                self._save_to_disk()
            
            return key
    
    def invalidate(self, pattern: Optional[str] = None) -> int:
        """
        Invalidate cache entries.
        
        Args:
            pattern: Optional pattern to match keys (invalidates all if None)
            
        Returns:
            Number of entries invalidated
        """
        with self._lock:
            if pattern is None:
                count = len(self._cache)
                self._cache.clear()
                logger.info(f"Invalidated all {count} cache entries")
                return count
            
            keys_to_remove = [k for k in self._cache if pattern in k]
            for key in keys_to_remove:
                del self._cache[key]
            
            logger.info(f"Invalidated {len(keys_to_remove)} entries matching '{pattern}'")
            return len(keys_to_remove)
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count removed."""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items() 
                if entry.is_expired()
            ]
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired entries")
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = len(self._cache)
            expired = sum(1 for e in self._cache.values() if e.is_expired())
            active = total - expired
            
            if total > 0:
                avg_access_count = sum(e.access_count for e in self._cache.values()) / total
                oldest = min(e.timestamp for e in self._cache.values())
                newest = max(e.timestamp for e in self._cache.values())
            else:
                avg_access_count = 0
                oldest = newest = 0
            
            return {
                "total_entries": total,
                "active_entries": active,
                "expired_entries": expired,
                "max_size": self.max_size,
                "default_ttl": self.ttl,
                "average_access_count": round(avg_access_count, 2),
                "oldest_entry_age_seconds": round(time.time() - oldest, 2) if oldest else 0,
                "newest_entry_age_seconds": round(time.time() - newest, 2) if newest else 0,
            }
    
    def _hash_conversation(self, conversation_history: List[Dict[str, str]]) -> str:
        """Create hash of conversation for cache key."""
        conv_str = json.dumps(conversation_history, sort_keys=True, default=str)
        return hashlib.sha256(conv_str.encode()).hexdigest()[:16]
    
    def _evict_oldest(self):
        """Evict least recently used entries."""
        if not self._cache:
            return
        
        # Find entry with oldest last_accessed
        oldest_key = min(
            self._cache.keys(), 
            key=lambda k: self._cache[k].last_accessed or self._cache[k].timestamp
        )
        del self._cache[oldest_key]
        logger.debug(f"Evicted oldest cache entry: {oldest_key}")
    
    def _save_to_disk(self):
        """Persist cache to disk."""
        try:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.persist_path, 'wb') as f:
                pickle.dump(self._cache, f)
        except Exception as e:
            logger.error(f"Failed to persist cache: {e}")
    
    def _load_from_disk(self):
        """Load cache from disk."""
        try:
            with open(self.persist_path, 'rb') as f:
                loaded = pickle.load(f)
                # Only load non-expired entries
                self._cache = {
                    k: v for k, v in loaded.items() 
                    if not v.is_expired()
                }
                logger.info(f"Loaded {len(self._cache)} entries from disk")
        except Exception as e:
            logger.error(f"Failed to load cache from disk: {e}")
            self._cache = {}


class EmbeddingCache:
    """Separate cache for file embeddings to avoid recomputation."""
    
    def __init__(self, cache_dir: Path, ttl_days: int = 7):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_days * 24 * 3600
        self._memory_cache: Dict[str, tuple] = {}
        self._lock = threading.RLock()
    
    def _get_file_hash(self, file_path: Path, mtime: float) -> str:
        """Generate hash based on file path and modification time."""
        data = f"{file_path.resolve()}:{mtime}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]
    
    def get_embedding(self, file_path: Path) -> Optional[List[float]]:
        """Get cached embedding for file if available and current."""
        try:
            stat = file_path.stat()
            cache_key = self._get_file_hash(file_path, stat.st_mtime)
            
            # Check memory cache first
            with self._lock:
                if cache_key in self._memory_cache:
                    embedding, timestamp = self._memory_cache[cache_key]
                    if time.time() - timestamp < self.ttl_seconds:
                        return embedding
            
            # Check disk cache
            cache_file = self.cache_dir / f"{cache_key}.pkl"
            if cache_file.exists():
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                    embedding = data['embedding']
                    # Update memory cache
                    with self._lock:
                        self._memory_cache[cache_key] = (embedding, time.time())
                    return embedding
            
            return None
        except Exception as e:
            logger.error(f"Error retrieving embedding cache: {e}")
            return None
    
    def set_embedding(self, file_path: Path, embedding: List[float]):
        """Cache embedding for file."""
        try:
            stat = file_path.stat()
            cache_key = self._get_file_hash(file_path, stat.st_mtime)
            
            # Update memory cache
            with self._lock:
                self._memory_cache[cache_key] = (embedding, time.time())
            
            # Update disk cache
            cache_file = self.cache_dir / f"{cache_key}.pkl"
            with open(cache_file, 'wb') as f:
                pickle.dump({
                    'embedding': embedding,
                    'file_path': str(file_path),
                    'mtime': stat.st_mtime,
                    'cached_at': time.time()
                }, f)
            
            logger.debug(f"Cached embedding for {file_path}")
        except Exception as e:
            logger.error(f"Error saving embedding cache: {e}")
    
    def cleanup_old(self, max_age_days: int = 30) -> int:
        """Remove cache files older than max_age_days."""
        removed = 0
        cutoff = time.time() - (max_age_days * 24 * 3600)
        
        for cache_file in self.cache_dir.glob("*.pkl"):
            try:
                if cache_file.stat().st_mtime < cutoff:
                    cache_file.unlink()
                    removed += 1
            except Exception as e:
                logger.error(f"Error removing old cache file {cache_file}: {e}")
        
        logger.info(f"Cleaned up {removed} old embedding cache files")
        return removed
