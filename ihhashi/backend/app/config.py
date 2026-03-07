from pydantic_settings import BaseSettings
from pydantic import Field, validator
from functools import lru_cache
from typing import Optional, List
import secrets
import os
import logging


logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Database
    mongodb_url: str = Field(default="mongodb://localhost:27017", env="MONGODB_URL")
    db_name: str = Field(default="ihhashi", env="DB_NAME")
    mongodb_max_pool_size: int = 100
    mongodb_min_pool_size: int = 10
    mongodb_timeout_ms: int = 30000
    
    # Security - MUST be set in production
    secret_key: str = Field(default="", env="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Password requirements
    min_password_length: int = 8
    require_password_uppercase: bool = True
    require_password_number: bool = True
    require_password_special: bool = False  # SA users often struggle with special chars
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_period: int = 60
    auth_rate_limit: str = "5/minute"
    api_rate_limit: str = "100/minute"
    
    # CORS - strict in production
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000", 
        env="CORS_ORIGINS"
    )
    
    # Callback URLs (configurable, whitelisted)
    payment_callback_url: str = Field(
        default="https://ihhashi.app/payment/callback",
        env="PAYMENT_CALLBACK_URL"
    )
    
    # South Africa Specific
    default_currency: str = "ZAR"
    supported_languages: List[str] = ["en", "zu", "xh", "af", "st", "tn", "so", "nso", "ts", "ve", "nr"]
    vat_rate: float = 0.15
    default_timezone: str = "Africa/Johannesburg"
    
    # Free Trial Configuration
    free_trial_days: int = 45
    free_trial_platform_fee_percent: float = 0.0
    standard_platform_fee_percent: float = 15.0
    
    # Delivery Pricing (SA market-competitive)
    base_delivery_fee: float = 20.0  # R20 base
    per_km_rate: float = 5.0  # R5/km
    min_delivery_fee: float = 15.0
    long_distance_surcharge_km: int = 15  # After 15km
    long_distance_surcharge_rate: float = 7.0  # R7/km after 15km
    
    # Supabase - REQUIRED for phone OTP auth
    supabase_url: str = Field(default="", env="SUPABASE_URL")
    supabase_anon_key: str = Field(default="", env="SUPABASE_ANON_KEY")
    supabase_service_role_key: str = Field(default="", env="SUPABASE_SERVICE_ROLE_KEY")
    
    # Payments - Paystack (Nigeria-based, works in SA)
    paystack_secret_key: str = Field(default="", env="PAYSTACK_SECRET_KEY")
    paystack_public_key: str = Field(default="", env="PAYSTACK_PUBLIC_KEY")
    paystack_webhook_secret: str = Field(default="", env="PAYSTACK_WEBHOOK_SECRET")
    
    # Payments - Yoco (South African)
    yoco_secret_key: str = Field(default="", env="YOCO_SECRET_KEY")
    yoco_webhook_secret: str = Field(default="", env="YOCO_WEBHOOK_SECRET")
    
    # Maps & Geolocation
    google_maps_api_key: str = Field(default="", env="GOOGLE_MAPS_API_KEY")
    google_geocoding_api_key: str = Field(default="", env="GOOGLE_GEOCODING_API_KEY")
    
    # Firebase (Push Notifications)
    firebase_project_id: str = Field(default="", env="FIREBASE_PROJECT_ID")
    firebase_private_key_id: str = Field(default="", env="FIREBASE_PRIVATE_KEY_ID")
    firebase_private_key: str = Field(default="", env="FIREBASE_PRIVATE_KEY")
    firebase_client_email: str = Field(default="", env="FIREBASE_CLIENT_EMAIL")
    
    # Twilio (SMS for SA)
    twilio_account_sid: str = Field(default="", env="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(default="", env="TWILIO_AUTH_TOKEN")
    twilio_phone_number: str = Field(default="", env="TWILIO_PHONE_NUMBER")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # Monitoring - GlitchTip (self-hosted Sentry alternative)
    glitchtip_dsn: str = Field(default="", env="GLITCHTIP_DSN")
    sentry_dsn: str = Field(default="", env="SENTRY_DSN")  # Alias for compatibility
    
    # PostHog Analytics
    posthog_api_key: str = Field(default="", env="POSTHOG_API_KEY")
    posthog_host: str = Field(default="https://app.posthog.com", env="POSTHOG_HOST")
    
    # Groq (for Nduna chatbot)
    groq_api_keys: str = Field(default="", env="GROQ_API_KEYS")  # Comma-separated for rotation
    
    # Security Headers
    content_security_policy: str = "default-src 'self'"
    x_frame_options: str = "DENY"
    x_content_type_options: str = "nosniff"
    strict_transport_security: str = "max-age=31536000; includeSubDomains"

    @validator("secret_key", pre=True, always=True)
    def validate_secret_key(cls, v, values):
        env = values.get("environment", "development")
        if env == "production":
            if not v or len(v) < 32:
                raise ValueError("SECRET_KEY must be at least 32 characters in production")
            if "dev" in v.lower() or "secret" in v.lower() or "change" in v.lower():
                raise ValueError("SECRET_KEY appears to be a default/placeholder. Generate a secure key.")
        elif not v:
            # Generate a random key for development
            logger.warning("SECRET_KEY not set - using auto-generated key for development")
            return secrets.token_urlsafe(32)
        return v

    @validator("debug", pre=True, always=True)
    def validate_debug(cls, v, values):
        env = values.get("environment", "development")
        # Handle string values from environment
        if isinstance(v, str):
            v = v.lower() in ("true", "1", "yes")
        # Only raise error if debug is explicitly True in production
        if v is True and env == "production":
            raise ValueError("DEBUG must be False in production")
        return v

    @validator("cors_origins", pre=True, always=True)
    def validate_cors_origins(cls, v, values):
        env = values.get("environment", "development")
        if env == "production" and v:
            origins = [o.strip() for o in v.split(",")]
            localhost_origins = [o for o in origins if "localhost" in o or "127.0.0.1" in o]
            if localhost_origins:
                logger.warning(f"CORS contains localhost origins in production: {localhost_origins}")
            # Ensure production domains are included
            prod_domains = ["ihhashi.app", "kofi.zo.computer"]
            if not any(any(d in o for d in prod_domains) for o in origins):
                logger.warning("CORS_ORIGINS does not include production domain (ihhashi.app)")
        return v

    @validator("supabase_url", pre=True, always=True)
    def validate_supabase(cls, v, values):
        env = values.get("environment", "development")
        if env == "production" and not v:
            logger.warning("SUPABASE_URL not set - phone OTP auth will not work")
        return v

    @validator("paystack_secret_key", pre=True, always=True)
    def validate_paystack(cls, v, values):
        env = values.get("environment", "development")
        if env == "production":
            if not v:
                logger.warning("PAYSTACK_SECRET_KEY not set - payments will not work")
            elif v.startswith("sk_test_"):
                logger.warning("Using Paystack TEST key in production environment!")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
