"""Celery app configuration for iHhashi."""
from celery import Celery
from celery.schedules import crontab
import os

# Get Redis URL from environment
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize Celery
celery_app = Celery(
    "ihhashi",
    broker=redis_url,
    backend=redis_url,
    include=[
        "app.celery_worker.tasks",
        "app.celery_worker.alerts",
        "app.celery_worker.quantum_optimizer",
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Johannesburg",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=5 * 60,  # 5 minutes max
    task_soft_time_limit=4 * 60,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Result backend settings
    result_expires=3600,  # 1 hour
    # Task routing
    task_routes={
        "app.celery_worker.alerts.*": {"queue": "alerts"},
        "app.celery_worker.tasks.*": {"queue": "default"},
        "app.celery_worker.quantum_optimizer.*": {"queue": "quantum"},
    },
    # Beat schedule for periodic tasks
    beat_schedule={
        # Check stuck orders every 5 minutes
        "check-stuck-orders": {
            "task": "app.celery_worker.tasks.check_stuck_orders",
            "schedule": 300.0,  # 5 minutes
        },
        # Cleanup expired sessions every hour
        "cleanup-sessions": {
            "task": "app.celery_worker.tasks.cleanup_expired_sessions",
            "schedule": crontab(minute=0),  # Every hour
        },
        # Daily analytics at midnight SAST
        "daily-analytics": {
            "task": "app.celery_worker.tasks.generate_daily_analytics",
            "schedule": crontab(hour=0, minute=0),
        },
        # Driver availability check every 10 minutes
        "check-driver-availability": {
            "task": "app.celery_worker.tasks.check_driver_availability",
            "schedule": 600.0,  # 10 minutes
        },
        # Quantum route optimization every 3 minutes
        "quantum-route-optimization": {
            "task": "app.celery_worker.quantum_optimizer.batch_optimize_all_routes",
            "schedule": 180.0,  # 3 minutes
        },
    },
)
