"""
Celery integration helpers for FastAPI routes.

Usage in routes:
    from app.celery_worker.integration import trigger_order_status_change
    
    @router.post("/orders/{order_id}/confirm")
    async def confirm_order(order_id: str):
        # Update DB
        ...
        # Trigger async processing
        trigger_order_status_change(order_id, "pending", "confirmed")
        return {"status": "confirmed"}
"""
from typing import Optional, Dict, Any
from app.celery_worker.tasks import (
    handle_order_status_change,
    handle_payment_event,
    find_available_rider,
)
from app.celery_worker.alerts import (
    send_customer_notification,
    send_merchant_notification,
    send_rider_notification,
    send_ops_alert,
)
from app.celery_worker.llm_tasks import (
    analyze_support_ticket,
    generate_nduna_response,
)


# ============ ORDER HELPERS ============

def trigger_order_status_change(
    order_id: str,
    old_status: str,
    new_status: str,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Trigger async order status processing.
    Call after updating order status in database.
    """
    handle_order_status_change.delay(order_id, old_status, new_status, metadata)


def trigger_payment_success(
    order_id: str,
    payment_reference: str,
    amount: float,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Trigger async payment success processing.
    Call after receiving payment webhook.
    """
    handle_payment_event.delay(
        order_id, "success", payment_reference, amount, metadata
    )


def trigger_payment_failure(
    order_id: str,
    payment_reference: str,
    amount: float,
    reason: Optional[str] = None
):
    """
    Trigger async payment failure processing.
    """
    handle_payment_event.delay(
        order_id, "failed", payment_reference, amount, {"reason": reason}
    )


# ============ NOTIFICATION HELPERS ============

def notify_customer(
    user_id: str,
    order_id: str,
    event: str,
    message: str,
    channels: list = ["push"]
):
    """Send notification to customer."""
    send_customer_notification.delay(user_id, order_id, event, message, channels)


def notify_merchant(
    merchant_id: str,
    order_id: str,
    event: str,
    message: str
):
    """Send notification to merchant."""
    send_merchant_notification.delay(merchant_id, order_id, event, message)


def notify_rider(
    rider_id: str,
    event: str,
    message: str,
    data: Optional[Dict[str, Any]] = None
):
    """Send notification to rider."""
    send_rider_notification.delay(rider_id, event, message, data)


def alert_ops(level: str, message: str, details: Optional[Dict[str, Any]] = None):
    """Send alert to ops team."""
    send_ops_alert.delay(level, message, details)


# ============ SUPPORT HELPERS ============

def analyze_ticket(ticket_id: str):
    """Trigger AI analysis of support ticket."""
    analyze_support_ticket.delay(ticket_id)


def get_ai_support_response(
    user_message: str,
    context: Optional[Dict[str, Any]] = None,
    language: str = "en"
):
    """
    Get AI support response (async).
    For synchronous response, use Nduna route directly.
    """
    return generate_nduna_response.delay(user_message, context, language)


# ============ RIDER HELPERS ============

def find_rider(order_id: str):
    """Trigger rider search for order."""
    find_available_rider.delay(order_id)
