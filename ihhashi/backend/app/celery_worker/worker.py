#!/usr/bin/env python3
"""
Celery worker startup script for iHhashi.

Usage:
    # Start default worker
    python -m app.celery_worker.worker
    
    # Start beat scheduler
    celery -A app.celery_worker.celery_app beat -l info
    
    # Start specific queue
    celery -A app.celery_worker.celery_app worker -Q alerts -l info
    
    # Start everything (worker + beat)
    celery -A app.celery_worker.celery_app worker -B -l info
"""
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.celery_worker.celery_app import celery_app

if __name__ == "__main__":
    celery_app.start()
