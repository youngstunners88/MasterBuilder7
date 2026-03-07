from fastapi import Request, HTTPException, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from typing import Callable, TypeVar, ParamSpec

P = ParamSpec("P")
R = TypeVar("R")

# Redis-backed rate limiter for production scaling
# Falls back to in-memory if Redis is not available
def get_storage_uri() -> str | None:
    """Get Redis storage URI for distributed rate limiting"""
    if settings.redis_url:
        return settings.redis_url
    return None  # Falls back to in-memory

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=get_storage_uri(),
    enabled=True
)

def setup_rate_limiting(app) -> None:
    """Attach rate limiter to FastAPI app"""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

def rate_limit(limit: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Reusable rate limiting decorator factory.
    
    Args:
        limit: Rate limit string (e.g., "5/minute", "100/hour")
    
    Returns:
        Decorator that applies the rate limit to the wrapped function.
    
    Example:
        @rate_limit("10/minute")
        async def my_endpoint(): ...
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        return limiter.limit(limit)(func)
    return decorator

# Preset rate limit configurations for common use cases
PRESETS = {
    "auth": "5/minute",      # Strict: auth endpoints are sensitive
    "api": "100/minute",     # Standard: general API access
    "payment": "10/minute",  # Moderate: financial operations
    "webhook": "100/minute", # High: trusted external services
    "order": "20/minute",    # Moderate: order placement
}

def auth_rate_limit(limit: str = PRESETS["auth"]) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Rate limiting decorator for auth endpoints (stricter)"""
    return rate_limit(limit)

def api_rate_limit(limit: str = PRESETS["api"]) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Rate limiting decorator for general API endpoints"""
    return rate_limit(limit)

def payment_rate_limit(limit: str = PRESETS["payment"]) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Rate limiting decorator for payment endpoints (moderate)"""
    return rate_limit(limit)

def webhook_rate_limit(limit: str = PRESETS["webhook"]) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Rate limiting decorator for webhook endpoints (allow high volume from trusted sources)"""
    return rate_limit(limit)

def order_rate_limit(limit: str = PRESETS["order"]) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Rate limiting decorator for order endpoints (moderate)"""
    return rate_limit(limit)
