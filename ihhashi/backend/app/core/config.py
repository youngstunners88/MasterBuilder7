"""
Core configuration settings for iHhashi.

Provides:
- Security settings
- JWT configuration
- Redis settings
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class CoreSettings(BaseSettings):
    """Core application settings."""
    
    # Security
    secret_key: str = "test-secret-key-for-development-only-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_core_settings():
    return CoreSettings()


settings = get_core_settings()
