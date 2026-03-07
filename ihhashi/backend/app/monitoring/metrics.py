"""
Prometheus metrics for iHhashi monitoring
Provides visibility into application performance and health
"""
from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest
from functools import wraps
import time
import logging

logger = logging.getLogger(__name__)

# Application info
APP_INFO = Info("ihhashi", "iHhashi application information")

# HTTP request metrics
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"]
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

# Database metrics
DB_OPERATIONS_TOTAL = Counter(
    "db_operations_total",
    "Database operations",
    ["operation", "collection", "status"]
)

DB_OPERATION_DURATION = Histogram(
    "db_operation_duration_seconds",
    "Database operation duration",
    ["operation", "collection"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

# Business metrics
ORDERS_CREATED_TOTAL = Counter(
    "orders_created_total",
    "Total orders created",
    ["status", "payment_method"]
)

ORDERS_COMPLETED_TOTAL = Counter(
    "orders_completed_total",
    "Total orders completed"
)

PAYMENTS_PROCESSED_TOTAL = Counter(
    "payments_processed_total",
    "Total payments processed",
    ["status", "payment_method"]
)

RIDERS_ASSIGNED_TOTAL = Counter(
    "riders_assigned_total",
    "Total rider assignments",
    ["status"]
)

REFERRALS_COMPLETED_TOTAL = Counter(
    "referrals_completed_total",
    "Total referrals completed",
    ["referral_type"]
)

# WebSocket metrics
WEBSOCKET_CONNECTIONS = Gauge(
    "websocket_connections_active",
    "Active WebSocket connections",
    ["room_type"]
)

WEBSOCKET_MESSAGES_TOTAL = Counter(
    "websocket_messages_total",
    "Total WebSocket messages",
    ["direction", "message_type"]
)

# System metrics
ACTIVE_USERS = Gauge(
    "active_users",
    "Number of active users",
    ["user_type"]
)

QUEUE_SIZE = Gauge(
    "queue_size",
    "Size of internal queues",
    ["queue_name"]
)

# Error metrics
ERRORS_TOTAL = Counter(
    "errors_total",
    "Total errors",
    ["type", "endpoint"]
)

# External service metrics
EXTERNAL_API_CALLS = Counter(
    "external_api_calls_total",
    "External API calls",
    ["service", "status"]
)

EXTERNAL_API_DURATION = Histogram(
    "external_api_duration_seconds",
    "External API call duration",
    ["service"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)


def track_request_duration(method: str, endpoint: str):
    """Decorator to track HTTP request duration"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                status = "200"
                return result
            except Exception as e:
                status = "500"
                raise
            finally:
                duration = time.time() - start_time
                HTTP_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
                HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status_code=status).inc()
        return wrapper
    return decorator


def track_db_operation(operation: str, collection: str):
    """Decorator to track database operations"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                DB_OPERATIONS_TOTAL.labels(operation=operation, collection=collection, status="success").inc()
                return result
            except Exception as e:
                DB_OPERATIONS_TOTAL.labels(operation=operation, collection=collection, status="error").inc()
                raise
            finally:
                duration = time.time() - start_time
                DB_OPERATION_DURATION.labels(operation=operation, collection=collection).observe(duration)
        return wrapper
    return decorator


def track_external_api(service: str):
    """Decorator to track external API calls"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                EXTERNAL_API_CALLS.labels(service=service, status="success").inc()
                return result
            except Exception as e:
                EXTERNAL_API_CALLS.labels(service=service, status="error").inc()
                raise
            finally:
                duration = time.time() - start_time
                EXTERNAL_API_DURATION.labels(service=service).observe(duration)
        return wrapper
    return decorator


def record_order_created(status: str, payment_method: str):
    """Record order creation metric"""
    ORDERS_CREATED_TOTAL.labels(status=status, payment_method=payment_method).inc()


def record_order_completed():
    """Record order completion metric"""
    ORDERS_COMPLETED_TOTAL.inc()


def record_payment_processed(status: str, payment_method: str):
    """Record payment processing metric"""
    PAYMENTS_PROCESSED_TOTAL.labels(status=status, payment_method=payment_method).inc()


def record_rider_assigned(status: str):
    """Record rider assignment metric"""
    RIDERS_ASSIGNED_TOTAL.labels(status=status).inc()


def record_error(error_type: str, endpoint: str):
    """Record error metric"""
    ERRORS_TOTAL.labels(type=error_type, endpoint=endpoint).inc()


def update_websocket_connections(room_type: str, count: int):
    """Update WebSocket connection gauge"""
    WEBSOCKET_CONNECTIONS.labels(room_type=room_type).set(count)


def update_active_users(user_type: str, count: int):
    """Update active users gauge"""
    ACTIVE_USERS.labels(user_type=user_type).set(count)


def get_metrics():
    """Get current metrics in Prometheus format"""
    return generate_latest()


def init_app_info(version: str, environment: str):
    """Initialize application info"""
    APP_INFO.info({
        "version": version,
        "environment": environment
    })
