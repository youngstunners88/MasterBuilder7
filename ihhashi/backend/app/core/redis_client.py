"""
Redis client configuration and utilities for iHhashi.

Provides:
- Redis connection management
- Token blacklisting for logout
- Caching utilities
"""

import logging
from typing import Optional
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)

# Global redis client
redis_client = None


async def init_redis():
    """Initialize Redis connection."""
    global redis_client
    try:
        import redis.asyncio as redis
        redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        # Test connection
        await redis_client.ping()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")
        redis_client = None


async def close_redis():
    """Close Redis connection."""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None
        logger.info("Redis connection closed")


def get_redis():
    """Get Redis client instance."""
    return redis_client


class TokenBlacklist:
    """Token blacklisting for secure logout."""
    
    @staticmethod
    async def add(token: str, ttl: int) -> bool:
        """Add a token to the blacklist."""
        if not redis_client:
            logger.warning("Redis not available, token blacklist disabled")
            return False
        try:
            key = f"blacklist:{token}"
            await redis_client.setex(key, ttl, "1")
            return True
        except Exception as e:
            logger.error(f"Failed to blacklist token: {e}")
            return False
    
    @staticmethod
    async def is_blacklisted(token: str) -> bool:
        """Check if a token is blacklisted."""
        if not redis_client:
            return False
        try:
            key = f"blacklist:{token}"
            result = await redis_client.exists(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to check token blacklist: {e}")
            return False


class Cache:
    """Simple caching utilities."""
    
    @staticmethod
    async def get(key: str) -> Optional[str]:
        """Get value from cache."""
        if not redis_client:
            return None
        try:
            return await redis_client.get(key)
        except Exception as e:
            logger.error(f"Cache get failed: {e}")
            return None
    
    @staticmethod
    async def set(key: str, value: str, ttl: int = 3600) -> bool:
        """Set value in cache with TTL."""
        if not redis_client:
            return False
        try:
            await redis_client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.error(f"Cache set failed: {e}")
            return False
    
    @staticmethod
    async def delete(key: str) -> bool:
        """Delete value from cache."""
        if not redis_client:
            return False
        try:
            await redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete failed: {e}")
            return False
    
    @staticmethod
    async def increment(key: str, amount: int = 1) -> int:
        """Increment a counter."""
        if not redis_client:
            return 0
        try:
            return await redis_client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Cache increment failed: {e}")
            return 0
