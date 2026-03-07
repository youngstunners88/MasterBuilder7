"""
Enhanced security middleware for iHhashi
Includes security headers, request validation, and protection against common attacks
"""
from fastapi import Request, HTTPException, Response
from fastapi.middleware import Middleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import time
import hashlib
import hmac
import logging
from typing import Optional, Dict, List
import re

from app.core.config import settings

logger = logging.getLogger(__name__)


# Maximum request sizes
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB
MAX_JSON_SIZE = 5 * 1024 * 1024  # 5MB

# Allowed HTTP methods
ALLOWED_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}

# Suspicious patterns for basic request validation
SUSPICIOUS_PATTERNS = [
    r"(\.\./)",  # Path traversal
    r"(<script)",  # XSS attempts
    r"(\.env)",  # Environment file access
    r"(config\.)",  # Config file access
    r"(\$\{.*jndi:)",  # Log4j-style attacks
]


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add comprehensive security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # XSS Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy
        response.headers["Permissions-Policy"] = (
            "geolocation=(self), "
            "microphone=(), "
            "camera=(), "
            "payment=()"
        )
        
        # HTTPS only in production
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
            
            # Enhanced Content Security Policy for production
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://checkout.paystack.co; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self' https://api.paystack.co https://*.supabase.co; "
                "frame-src https://checkout.paystack.co; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "form-action 'self';"
            )
        else:
            # Relaxed CSP for development
            response.headers["Content-Security-Policy"] = (
                "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "connect-src 'self' *;"
            )
        
        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Validate incoming requests for security issues.
    Checks for:
    - Oversized requests
    - Suspicious patterns
    - Invalid content types
    - Missing required headers
    """
    
    async def dispatch(self, request: Request, call_next):
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > MAX_CONTENT_LENGTH:
                    logger.warning(f"Request too large: {size} bytes from {request.client.host}")
                    return Response(
                        content='{"detail":"Request entity too large"}',
                        status_code=413,
                        media_type="application/json"
                    )
            except ValueError:
                pass
        
        # Check for suspicious URL patterns
        path = request.url.path
        for pattern in SUSPICIOUS_PATTERNS:
            if re.search(pattern, path, re.IGNORECASE):
                logger.warning(f"Suspicious request pattern detected: {path} from {request.client.host}")
                return Response(
                    content='{"detail":"Invalid request"}',
                    status_code=400,
                    media_type="application/json"
                )
        
        # Validate HTTP method
        if request.method not in ALLOWED_METHODS:
            logger.warning(f"Invalid HTTP method: {request.method} from {request.client.host}")
            return Response(
                content='{"detail":"Method not allowed"}',
                status_code=405,
                media_type="application/json"
            )
        
        # Continue with request
        response = await call_next(request)
        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Add unique request ID for tracing and logging.
    """
    
    async def dispatch(self, request: Request, call_next):
        import uuid
        
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response
        response.headers["X-Request-ID"] = request_id
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Enhanced logging middleware for security audit trail.
    """
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Get client info
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Log request
        logger.info(
            f"Request {request_id}: {request.method} {request.url.path} "
            f"from {client_ip} - {user_agent[:50]}"
        )
        
        # Process request
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log response
            logger.info(
                f"Response {request_id}: {response.status_code} "
                f"in {process_time:.3f}s"
            )
            
            return response
        
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Error {request_id}: {type(e).__name__} in {process_time:.3f}s"
            )
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Get real client IP (handles proxies)"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"


class TimingMiddleware(BaseHTTPMiddleware):
    """Add request timing for performance monitoring"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.3f}s"
        
        # Log slow requests (over 2 seconds - bad for SA networks)
        if process_time > 2.0:
            print(f"SLOW REQUEST: {request.method} {request.url.path} took {process_time:.3f}s")
        
        return response


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify webhook signatures (Paystack, Yoco, etc.)"""
    expected_signature = hmac.new(
        secret.encode(), 
        payload, 
        hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)


def get_client_ip(request: Request) -> Optional[str]:
    """Get real client IP (handles proxies)"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent directory traversal attacks.
    """
    # Remove path separators
    filename = filename.replace("/", "").replace("\\", "")
    
    # Remove leading dots (hidden files)
    filename = filename.lstrip(".")
    
    # Allow only safe characters
    filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename[:250].rsplit('.', 1) if '.' in filename[:250] else (filename[:250], '')
        filename = f"{name}.{ext}" if ext else name
    
    return filename


def is_safe_content_type(content_type: str, allowed_types: List[str]) -> bool:
    """
    Check if content type is in the allowed list.
    """
    if not content_type:
        return False
    
    # Normalize content type
    content_type = content_type.lower().split(";")[0].strip()
    
    return content_type in [t.lower() for t in allowed_types]
