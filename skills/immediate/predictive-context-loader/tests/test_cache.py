"""Tests for cache module."""

import pytest
import time
import tempfile
from pathlib import Path

from src.cache import PredictionCache, EmbeddingCache, CacheEntry


class TestCacheEntry:
    """Test CacheEntry dataclass."""
    
    def test_cache_entry_creation(self):
        entry = CacheEntry(
            key="test_key",
            data={"files": ["a.py"]},
            timestamp=time.time(),
            ttl=3600
        )
        assert entry.key == "test_key"
        assert entry.access_count == 0
    
    def test_cache_entry_expiration(self):
        entry = CacheEntry(
            key="test_key",
            data={},
            timestamp=time.time() - 7200,  # 2 hours ago
            ttl=3600  # 1 hour TTL
        )
        assert entry.is_expired() is True
    
    def test_cache_entry_not_expired(self):
        entry = CacheEntry(
            key="test_key",
            data={},
            timestamp=time.time(),
            ttl=3600
        )
        assert entry.is_expired() is False
    
    def test_cache_entry_touch(self):
        entry = CacheEntry(
            key="test_key",
            data={},
            timestamp=time.time(),
            ttl=3600
        )
        entry.touch()
        assert entry.access_count == 1
        assert entry.last_accessed > 0


class TestPredictionCache:
    """Test PredictionCache class."""
    
    @pytest.fixture
    def cache(self):
        return PredictionCache(ttl_seconds=3600, max_size=100)
    
    @pytest.fixture
    def sample_conversation(self):
        return [
            {"role": "user", "content": "I need to fix the auth bug"},
            {"role": "assistant", "content": "Let me help you"}
        ]
    
    def test_cache_set_and_get(self, cache, sample_conversation):
        data = {"predictions": [{"file": "auth.py"}]}
        key = cache.set(sample_conversation, data)
        
        retrieved = cache.get(sample_conversation)
        assert retrieved == data
    
    def test_cache_miss(self, cache):
        conversation = [{"role": "user", "content": "Hello"}]
        result = cache.get(conversation)
        assert result is None
    
    def test_cache_expiration(self, cache, sample_conversation):
        data = {"predictions": []}
        
        # Set with 1 second TTL
        cache.set(sample_conversation, data, ttl=1)
        
        # Should be available immediately
        assert cache.get(sample_conversation) == data
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired
        assert cache.get(sample_conversation) is None
    
    def test_cache_with_context(self, cache, sample_conversation):
        data = {"files": ["test.py"]}
        context = {"current_file": "main.py"}
        
        cache.set(sample_conversation, data, context)
        
        # Should match with same context
        assert cache.get(sample_conversation, context) == data
        
        # Should not match without context
        assert cache.get(sample_conversation) is None
    
    def test_cache_invalidation_all(self, cache, sample_conversation):
        cache.set(sample_conversation, {"data": 1})
        cache.set([{"role": "user", "content": "Other"}], {"data": 2})
        
        count = cache.invalidate()
        assert count == 2
        assert cache.get(sample_conversation) is None
    
    def test_cache_invalidation_pattern(self, cache):
        cache.set([{"role": "user", "content": "auth"}], {"data": 1})
        cache.set([{"role": "user", "content": "other"}], {"data": 2})
        
        count = cache.invalidate(pattern="auth")
        assert count == 1
    
    def test_cache_stats(self, cache, sample_conversation):
        cache.set(sample_conversation, {"data": 1})
        cache.get(sample_conversation)  # Access once
        cache.get(sample_conversation)  # Access twice
        
        stats = cache.get_stats()
        assert stats["total_entries"] == 1
        assert stats["active_entries"] == 1
        assert stats["average_access_count"] == 2.0
    
    def test_cache_eviction(self):
        cache = PredictionCache(ttl_seconds=3600, max_size=2)
        
        # Add 3 items to trigger eviction
        cache.set([{"role": "user", "content": "1"}], {"data": 1})
        cache.set([{"role": "user", "content": "2"}], {"data": 2})
        
        # Access first item to make it more recent
        cache.get([{"role": "user", "content": "1"}])
        
        cache.set([{"role": "user", "content": "3"}], {"data": 3})
        
        # Item 2 should be evicted (least recently used)
        assert cache.get([{"role": "user", "content": "1"}]) is not None
        assert cache.get([{"role": "user", "content": "3"}]) is not None
    
    def test_cache_persistence(self, sample_conversation):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = Path(tmp.name)
        
        try:
            # Create and populate cache
            cache = PredictionCache(persist_path=tmp_path)
            cache.set(sample_conversation, {"predictions": ["a.py"]})
            
            # Create new cache instance with same path
            cache2 = PredictionCache(persist_path=tmp_path)
            
            # Should load from disk
            result = cache2.get(sample_conversation)
            assert result == {"predictions": ["a.py"]}
        finally:
            tmp_path.unlink(missing_ok=True)


class TestEmbeddingCache:
    """Test EmbeddingCache class."""
    
    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            yield Path(tmp)
    
    @pytest.fixture
    def embedding_cache(self, temp_dir):
        return EmbeddingCache(temp_dir, ttl_days=7)
    
    def test_set_and_get_embedding(self, embedding_cache, temp_dir):
        # Create a test file
        test_file = temp_dir / "test.py"
        test_file.write_text("print('hello')")
        
        embedding = [0.1, 0.2, 0.3, 0.4]
        
        embedding_cache.set_embedding(test_file, embedding)
        retrieved = embedding_cache.get_embedding(test_file)
        
        assert retrieved == embedding
    
    def test_get_missing_embedding(self, embedding_cache, temp_dir):
        test_file = temp_dir / "nonexistent.py"
        test_file.write_text("content")
        
        result = embedding_cache.get_embedding(test_file)
        assert result is None
    
    def test_embedding_cache_invalidated_on_change(self, embedding_cache, temp_dir):
        test_file = temp_dir / "test.py"
        test_file.write_text("version 1")
        
        embedding_cache.set_embedding(test_file, [0.1, 0.2])
        
        # Modify file
        time.sleep(0.1)
        test_file.write_text("version 2")
        
        # Should return None (different mtime = different hash)
        result = embedding_cache.get_embedding(test_file)
        assert result is None
    
    def test_cleanup_old_cache(self, embedding_cache, temp_dir):
        # Create old cache file
        old_file = temp_dir / "old_cache.pkl"
        old_file.write_text("old data")
        
        # Set modification time to 40 days ago
        old_time = time.time() - (40 * 24 * 3600)
        import os
        os.utime(old_file, (old_time, old_time))
        
        removed = embedding_cache.cleanup_old(max_age_days=30)
        assert removed == 1
        assert not old_file.exists()
