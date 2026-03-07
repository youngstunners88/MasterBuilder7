from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from datetime import datetime
from contextlib import asynccontextmanager
import sentry_sdk
import logging

# Real routes only - no mocks
from app.routes.auth import router as auth_router
from app.routes.orders import router as orders_router
from app.routes.merchants import router as merchants_router
from app.routes.riders import router as riders_router
from app.routes.vendors import router as vendors_router
from app.routes.delivery_servicemen import router as servicemen_router
from app.routes.referrals import router as referrals_router
from app.routes.customer_rewards import router as customer_rewards_router
from app.routes.addresses import router as addresses_router
from app.routes.products import router as products_router
from app.routes.refunds import router as refunds_router
from app.routes import trips, payments
from app.routes.websocket import router as websocket_router, manager as ws_manager
from app.routes.nduna import router as nduna_router
from app.routes.route_memory import router as route_memory_router
from app.routes.pricing_intelligence import router as pricing_intelligence_router
from app.routes.community import router as community_router
from app.routes.nduna_intelligence import router as nduna_intelligence_router
from app.routes.quantum_orchestrator import router as quantum_router
from app.config import settings
from app.database import (
    connect_db, 
    close_db, 
    ensure_indexes,
    health_check as db_health_check,
)
from app.database import database
from app.core.redis_client import init_redis, close_redis
from app.middleware.rate_limit import setup_rate_limiting
from app.middleware.security_enhanced import (
    SecurityHeadersMiddleware,
    RequestValidationMiddleware,
    RequestIDMiddleware,
    LoggingMiddleware
)
from app.monitoring.metrics import init_app_info, get_metrics, update_websocket_connections

logger = logging.getLogger(__name__)

# Initialize GlitchTip (Sentry-compatible)
if settings.glitchtip_dsn:
    sentry_sdk.init(
        dsn=settings.glitchtip_dsn,
        traces_sample_rate=0.2,
        environment=settings.environment,
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting iHhashi API...")
    
    # Initialize MongoDB connection
    try:
        await connect_db()
        logger.info("MongoDB connected")
        
        # Create database indexes only if connected
        try:
            index_results = await ensure_indexes(database)
            logger.info(f"Database indexes created: {len(index_results)} collections updated")
        except Exception as e:
            logger.warning(f"Failed to create indexes: {e}")
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
    
    # Initialize Redis connection
    try:
        await init_redis()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning(f"Redis connection failed (caching disabled): {e}")
    
    # Initialize WebSocket manager with Redis
    try:
        await ws_manager.start()
        logger.info("WebSocket manager started")
    except Exception as e:
        logger.warning(f"WebSocket manager startup warning: {e}")
    
    # Initialize monitoring
    init_app_info(version="1.0.0", environment=settings.environment)
    logger.info(f"Monitoring initialized for {settings.environment}")
    
    logger.info("iHhashi API startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down iHhashi API...")
    
    # Stop WebSocket manager
    try:
        await ws_manager.stop()
        logger.info("WebSocket manager stopped")
    except Exception as e:
        logger.warning(f"Error stopping WebSocket manager: {e}")
    
    # Close Redis connection
    try:
        await close_redis()
        logger.info("Redis connection closed")
    except Exception as e:
        logger.warning(f"Error closing Redis: {e}")
    
    # Close MongoDB connection
    try:
        await close_db()
        logger.info("MongoDB connection closed")
    except Exception as e:
        logger.warning(f"Error closing MongoDB: {e}")

app = FastAPI(
    title="iHhashi API",
    description="Buyer-centric delivery platform for South Africa",
    version="1.0.0",
    lifespan=lifespan
)

# Enhanced security middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestValidationMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(LoggingMiddleware)

# Parse CORS origins from environment
cors_origins = [origin.strip() for origin in settings.cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "X-Request-ID"],
    max_age=600,
)

# Setup Redis-backed rate limiting
setup_rate_limiting(app)

# ============================================================================
# Create /api/v1 router - matches frontend expectations
# ============================================================================
api_v1 = APIRouter(prefix="/api/v1")

# Mount all real routes under /api/v1
api_v1.include_router(auth_router, prefix="/auth", tags=["auth"])
api_v1.include_router(orders_router, prefix="/orders", tags=["orders"])
api_v1.include_router(merchants_router, prefix="/merchants", tags=["merchants"])
api_v1.include_router(riders_router, prefix="/riders", tags=["riders"])
api_v1.include_router(vendors_router, prefix="/vendors", tags=["vendors"])
api_v1.include_router(servicemen_router, prefix="/delivery-servicemen", tags=["delivery-servicemen"])
api_v1.include_router(referrals_router, prefix="/referrals", tags=["referrals"])
api_v1.include_router(customer_rewards_router, prefix="/customer-rewards", tags=["customer-rewards"])
api_v1.include_router(refunds_router, prefix="/refunds", tags=["refunds"])
api_v1.include_router(trips.router, prefix="/trips", tags=["trips"])
api_v1.include_router(payments.router, prefix="/payments", tags=["payments"])
api_v1.include_router(pricing_intelligence_router, prefix="/pricing-intelligence", tags=["pricing-intelligence"])
api_v1.include_router(community_router, prefix="/community", tags=["community"])
api_v1.include_router(nduna_intelligence_router, prefix="/nduna-intelligence", tags=["nduna-intelligence"])

# Addresses and products
api_v1.include_router(addresses_router, prefix="/addresses", tags=["addresses"])
api_v1.include_router(products_router, prefix="/products", tags=["products"])

# Users routes
from app.routes.users import router as users_router
api_v1.include_router(users_router, prefix="/users", tags=["users"])

# Include the v1 router in main app
app.include_router(api_v1)

# WebSocket and chatbot at different prefixes
app.include_router(websocket_router, prefix="/ws", tags=["websocket"])
app.include_router(nduna_router, prefix="/api/nduna", tags=["nduna-chatbot"])
app.include_router(route_memory_router, prefix="/api/route-memory", tags=["route-memory"])

# Quantum routing endpoints
app.include_router(quantum_router, prefix="/api/v1", tags=["quantum-routing"])


@app.get("/")
async def root():
    return {
        "name": "iHhashi API",
        "version": "1.0.0",
        "status": "operational",
        "features": [
            "Blue Horse verification",
            "Multi-modal delivery",
            "45-day free trial + referral bonuses",
            "0% tip fee",
            "iHhashi Coins rewards for customers",
            "Tiered loyalty program"
        ],
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health():
    """Health check with database and Redis connectivity test"""
    # Check MongoDB
    try:
        db_status = await db_health_check()
    except Exception as e:
        db_status = {"status": "unhealthy", "message": str(e)}
    
    # Check Redis
    redis_status = "disconnected"
    try:
        from app.core.redis_client import get_redis
        redis_client = get_redis()
        if redis_client:
            await redis_client.ping()
            redis_status = "connected"
    except Exception:
        redis_status = "unavailable"
    
    # Check WebSocket manager
    ws_status = "active" if ws_manager.get_connection_count() >= 0 else "inactive"
    update_websocket_connections("total", ws_manager.get_connection_count())
    
    # Determine overall status
    overall_status = "healthy"
    if db_status.get("status") != "healthy":
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "database": db_status,
        "redis": redis_status,
        "websocket": ws_status,
        "environment": settings.environment,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus metrics endpoint"""
    return get_metrics()


@app.get("/ready")
async def ready():
    """Readiness probe for Kubernetes"""
    try:
        # Check critical dependencies
        db_ok = (await db_health_check()).get("status") == "healthy"
        
        if db_ok:
            return {"status": "ready"}
        else:
            return {"status": "not ready", "reason": "database unhealthy"}
    except Exception as e:
        return {"status": "not ready", "reason": str(e)}


@app.get("/live")
async def live():
    """Liveness probe for Kubernetes"""
    return {"status": "alive"}
