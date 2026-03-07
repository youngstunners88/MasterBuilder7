"""
Celery tasks for iHhashi - Rule-based triggers, no LLM overhead.

Task categories:
1. Order lifecycle (status changes → actions)
2. Payment events (webhooks → updates)
3. Driver events (location, availability)
4. Scheduled maintenance (cleanup, analytics)
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from celery import shared_task
from pymongo import ASCENDING, DESCENDING

logger = logging.getLogger(__name__)


# ============ DATABASE HELPERS ============

def get_db():
    """Get MongoDB database connection."""
    from app.db import get_db as _get_db
    return _get_db()


# ============ ORDER STATUS TRIGGERS ============

# Rule definitions for order status changes
ORDER_RULES = {
    # Order confirmed → notify customer, notify merchant
    "confirmed": {
        "notify_customer": True,
        "notify_merchant": True,
        "start_prep_timer": True,
    },
    # Order preparing → update ETA
    "preparing": {
        "update_eta": True,
    },
    # Order ready → find rider
    "ready": {
        "find_rider": True,
        "notify_nearby_riders": True,
    },
    # Order picked up → track delivery
    "picked_up": {
        "start_tracking": True,
        "notify_customer_pickup": True,
    },
    # Order in transit → share live location
    "in_transit": {
        "enable_live_tracking": True,
        "notify_customer_en_route": True,
    },
    # Order delivered → request review, process payout
    "delivered": {
        "request_review": True,
        "process_payout": True,
        "update_stats": True,
    },
    # Order cancelled → refund if needed, notify
    "cancelled": {
        "process_refund": True,
        "notify_all": True,
        "update_availability": True,
    },
}


@shared_task(bind=True, max_retries=2)
def handle_order_status_change(
    self,
    order_id: str,
    old_status: str,
    new_status: str,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Handle order status changes with rule-based triggers.
    
    No LLM needed - simple state machine with predefined actions.
    """
    logger.info(f"Order {order_id}: {old_status} → {new_status}")
    
    db = get_db()
    orders = db.orders
    
    # Get order details
    order = orders.find_one({"_id": order_id})
    if not order:
        logger.error(f"Order {order_id} not found")
        return {"status": "error", "message": "Order not found"}
    
    # Get rules for new status
    rules = ORDER_RULES.get(new_status, {})
    
    actions_taken = []
    
    # Execute rules
    if rules.get("notify_customer"):
        from app.celery_worker.alerts import send_customer_notification
        send_customer_notification.delay(
            user_id=order.get("buyer_id"),
            order_id=order_id,
            event="order_status",
            message=f"Your order #{order_id[-6:]} is now {new_status}",
            channels=["push", "sms"]
        )
        actions_taken.append("notified_customer")
    
    if rules.get("notify_merchant"):
        from app.celery_worker.alerts import send_merchant_notification
        send_merchant_notification.delay(
            merchant_id=order.get("store_id"),
            order_id=order_id,
            event="new_order" if new_status == "confirmed" else "order_update",
            message=f"Order #{order_id[-6:]} - {new_status}"
        )
        actions_taken.append("notified_merchant")
    
    if rules.get("find_rider"):
        # Find available rider
        find_available_rider.delay(order_id)
        actions_taken.append("finding_rider")
    
    if rules.get("notify_nearby_riders"):
        # Notify nearby riders of new delivery opportunity
        notify_nearby_riders.delay(order_id)
        actions_taken.append("notifying_nearby_riders")
    
    if rules.get("notify_customer_pickup"):
        from app.celery_worker.alerts import send_customer_notification
        send_customer_notification.delay(
            user_id=order.get("buyer_id"),
            order_id=order_id,
            event="rider_picked_up",
            message="Your order has been picked up and is on the way!",
            channels=["push", "sms"]
        )
        actions_taken.append("notified_pickup")
    
    if rules.get("process_payout"):
        # Calculate and queue merchant payout
        process_merchant_payout.delay(order_id)
        actions_taken.append("processing_payout")
    
    if rules.get("request_review"):
        # Send review request after 30 minutes
        request_order_review.apply_async(
            args=[order_id],
            countdown=1800  # 30 minutes
        )
        actions_taken.append("review_scheduled")
    
    if rules.get("process_refund"):
        # Check if payment was made, process refund
        if order.get("payment_status") == "paid":
            process_refund.delay(order_id, reason=metadata.get("reason", "Order cancelled"))
            actions_taken.append("refund_initiated")
    
    # Update order status history
    orders.update_one(
        {"_id": order_id},
        {
            "$push": {
                "status_history": {
                    "from": old_status,
                    "to": new_status,
                    "timestamp": datetime.utcnow(),
                    "actions": actions_taken
                }
            }
        }
    )
    
    return {
        "status": "completed",
        "order_id": order_id,
        "actions": actions_taken
    }


# ============ PAYMENT EVENTS ============

PAYMENT_RULES = {
    "success": {
        "confirm_order": True,
        "send_receipt": True,
    },
    "failed": {
        "notify_customer": True,
        "mark_payment_failed": True,
    },
    "refunded": {
        "notify_customer": True,
        "update_order": True,
    },
}


@shared_task(bind=True, max_retries=3)
def handle_payment_event(
    self,
    order_id: str,
    payment_status: str,
    payment_reference: str,
    amount: float,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Handle payment webhooks with rule-based triggers.
    """
    logger.info(f"Payment {payment_reference}: {payment_status} for order {order_id}")
    
    db = get_db()
    orders = db.orders
    
    order = orders.find_one({"_id": order_id})
    if not order:
        logger.error(f"Order {order_id} not found for payment event")
        return {"status": "error", "message": "Order not found"}
    
    rules = PAYMENT_RULES.get(payment_status, {})
    actions_taken = []
    
    if rules.get("confirm_order") and order.get("status") == "pending":
        # Update order status
        orders.update_one(
            {"_id": order_id},
            {"$set": {"status": "confirmed", "payment_status": "paid"}}
        )
        # Trigger order status change handler
        handle_order_status_change.delay(order_id, "pending", "confirmed")
        actions_taken.append("order_confirmed")
    
    if rules.get("send_receipt"):
        from app.celery_worker.alerts import send_customer_notification
        send_customer_notification.delay(
            user_id=order.get("buyer_id"),
            order_id=order_id,
            event="payment_success",
            message=f"Payment of R{amount:.2f} received for order #{order_id[-6:]}",
            channels=["push", "sms"]
        )
        actions_taken.append("receipt_sent")
    
    if rules.get("notify_customer"):
        from app.celery_worker.alerts import send_customer_notification
        send_customer_notification.delay(
            user_id=order.get("buyer_id"),
            order_id=order_id,
            event="payment_failed",
            message=f"Payment for order #{order_id[-6:]} failed. Please try again.",
            channels=["push", "sms"]
        )
        actions_taken.append("customer_notified")
    
    # Update payment info
    orders.update_one(
        {"_id": order_id},
        {
            "$set": {
                "payment_status": payment_status,
                "payment_reference": payment_reference,
                "payment_updated_at": datetime.utcnow()
            }
        }
    )
    
    return {
        "status": "completed",
        "order_id": order_id,
        "actions": actions_taken
    }


# ============ DRIVER/RIDER TASKS ============

@shared_task(bind=True, max_retries=2)
def find_available_rider(self, order_id: str):
    """
    Find an available rider for an order.
    
    Uses simple distance-based matching, no LLM needed.
    """
    from app.services.matching import find_nearest_riders
    
    db = get_db()
    order = db.orders.find_one({"_id": order_id})
    
    if not order:
        return {"status": "error", "message": "Order not found"}
    
    # Get delivery location
    delivery_loc = order.get("delivery_info", {}).get("coordinates")
    store_loc = order.get("store_location")
    
    if not delivery_loc or not store_loc:
        return {"status": "error", "message": "Missing location data"}
    
    # Find nearest available riders
    riders = find_nearest_riders(
        store_location=store_loc,
        delivery_location=delivery_loc,
        limit=5
    )
    
    if not riders:
        # No riders available - escalate
        logger.warning(f"No riders available for order {order_id}")
        escalate_no_rider.delay(order_id)
        return {"status": "pending", "message": "No riders available"}
    
    # Offer delivery to nearest rider
    offer_delivery_to_rider.delay(order_id, riders[0]["id"])
    
    return {"status": "success", "riders_found": len(riders)}


@shared_task(bind=True, max_retries=2)
def offer_delivery_to_rider(self, order_id: str, rider_id: str, timeout: int = 60):
    """
    Offer a delivery to a specific rider.
    """
    db = get_db()
    
    # Create delivery offer
    offer = {
        "order_id": order_id,
        "rider_id": rider_id,
        "status": "pending",
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(seconds=timeout)
    }
    
    db.delivery_offers.insert_one(offer)
    
    # Notify rider
    from app.celery_worker.alerts import send_rider_notification
    send_rider_notification.delay(
        rider_id=rider_id,
        event="new_delivery",
        message=f"New delivery available! Accept within {timeout}s",
        data={"order_id": order_id, "offer_id": str(offer["_id"])}
    )
    
    return {"status": "offered", "rider_id": rider_id}


@shared_task
def notify_nearby_riders(order_id: str, radius_km: float = 5.0):
    """
    Broadcast delivery opportunity to nearby riders.
    """
    db = get_db()
    order = db.orders.find_one({"_id": order_id})
    
    if not order:
        return {"status": "error", "message": "Order not found"}
    
    store_loc = order.get("store_location")
    if not store_loc:
        return {"status": "error", "message": "Missing store location"}
    
    # Find nearby riders (geo query)
    riders = db.drivers.find({
        "status": "available",
        "location": {
            "$near": {
                "$geometry": store_loc,
                "$maxDistance": radius_km * 1000
            }
        }
    }).limit(10)
    
    notified = 0
    for rider in riders:
        send_rider_notification.delay(
            rider_id=str(rider["_id"]),
            event="nearby_delivery",
            message="New delivery opportunity nearby!",
            data={"order_id": order_id}
        )
        notified += 1
    
    return {"status": "success", "riders_notified": notified}


@shared_task
def escalate_no_rider(order_id: str):
    """
    Escalate when no riders are available.
    Rule-based escalation, no LLM.
    """
    from app.celery_worker.alerts import send_ops_alert
    
    db = get_db()
    order = db.orders.find_one({"_id": order_id})
    
    # Check how long waiting
    wait_time = (datetime.utcnow() - order.get("created_at", datetime.utcnow())).total_seconds()
    
    if wait_time > 600:  # 10 minutes
        # Auto-cancel and refund
        handle_order_status_change.delay(
            order_id, 
            order.get("status", "ready"), 
            "cancelled",
            {"reason": "No rider available"}
        )
        send_ops_alert.delay(
            level="high",
            message=f"Order {order_id} auto-cancelled - no rider for {wait_time/60:.1f} min"
        )
    else:
        # Just alert ops team
        send_ops_alert.delay(
            level="medium",
            message=f"Order {order_id} waiting {wait_time/60:.1f} min for rider"
        )
    
    return {"status": "escalated", "wait_time": wait_time}


# ============ SCHEDULED TASKS ============

@shared_task
def check_stuck_orders():
    """
    Find orders stuck in a status too long.
    Rule-based anomaly detection - no LLM needed.
    """
    db = get_db()
    
    # Define time limits for each status (in minutes)
    time_limits = {
        "pending": 15,     # Should be confirmed within 15 min
        "confirmed": 30,   # Should start prep within 30 min
        "preparing": 45,   # Should be ready within 45 min
        "ready": 10,       # Should have rider within 10 min
        "picked_up": 60,   # Should be delivered within 60 min
        "in_transit": 45,  # Should be delivered within 45 min
    }
    
    alerts = []
    
    for status, limit_minutes in time_limits.items():
        threshold = datetime.utcnow() - timedelta(minutes=limit_minutes)
        
        stuck_orders = db.orders.find({
            "status": status,
            "updated_at": {"$lt": threshold}
        })
        
        for order in stuck_orders:
            stuck_time = (datetime.utcnow() - order.get("updated_at", datetime.utcnow())).total_seconds() / 60
            
            alerts.append({
                "order_id": str(order["_id"]),
                "status": status,
                "stuck_minutes": stuck_time,
                "limit_minutes": limit_minutes
            })
            
            # Auto-escalate
            from app.celery_worker.alerts import send_ops_alert
            send_ops_alert.delay(
                level="medium",
                message=f"Order {order['_id']} stuck in {status} for {stuck_time:.0f} min (limit: {limit_minutes} min)"
            )
    
    return {"status": "completed", "alerts": len(alerts), "details": alerts}


@shared_task
def check_driver_availability():
    """
    Monitor driver availability and alert if coverage is low.
    """
    db = get_db()
    
    # Count available drivers by area
    pipeline = [
        {"$match": {"status": "available"}},
        {"$group": {
            "_id": "$current_area",
            "count": {"$sum": 1}
        }}
    ]
    
    availability = list(db.drivers.aggregate(pipeline))
    
    # Alert if any area has < 2 drivers
    low_coverage = [a for a in availability if a["count"] < 2]
    
    if low_coverage:
        from app.celery_worker.alerts import send_ops_alert
        for area in low_coverage:
            send_ops_alert.delay(
                level="medium",
                message=f"Low driver coverage in {area['_id']}: {area['count']} available"
            )
    
    return {
        "status": "completed",
        "total_available": sum(a["count"] for a in availability),
        "low_coverage_areas": len(low_coverage)
    }


@shared_task
def cleanup_expired_sessions():
    """Clean up expired sessions and OTP codes."""
    db = get_db()
    
    # Remove expired sessions
    sessions_result = db.sessions.delete_many({
        "expires_at": {"$lt": datetime.utcnow()}
    })
    
    # Remove expired OTPs
    otps_result = db.otps.delete_many({
        "expires_at": {"$lt": datetime.utcnow()}
    })
    
    # Remove expired delivery offers
    offers_result = db.delivery_offers.delete_many({
        "expires_at": {"$lt": datetime.utcnow()},
        "status": "pending"
    })
    
    logger.info(f"Cleanup: {sessions_result.deleted_count} sessions, {otps_result.deleted_count} OTPs, {offers_result.deleted_count} offers")
    
    return {
        "sessions_deleted": sessions_result.deleted_count,
        "otps_deleted": otps_result.deleted_count,
        "offers_deleted": offers_result.deleted_count
    }


@shared_task
def generate_daily_analytics():
    """
    Generate daily analytics report.
    Could trigger LLM summary if needed, but raw data is rules-based.
    """
    db = get_db()
    
    yesterday = datetime.utcnow() - timedelta(days=1)
    yesterday_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # Order stats
    total_orders = db.orders.count_documents({
        "created_at": {"$gte": yesterday_start, "$lte": yesterday_end}
    })
    
    completed_orders = db.orders.count_documents({
        "status": "delivered",
        "delivered_at": {"$gte": yesterday_start, "$lte": yesterday_end}
    })
    
    cancelled_orders = db.orders.count_documents({
        "status": "cancelled",
        "updated_at": {"$gte": yesterday_start, "$lte": yesterday_end}
    })
    
    # Revenue
    pipeline = [
        {"$match": {
            "status": "delivered",
            "delivered_at": {"$gte": yesterday_start, "$lte": yesterday_end}
        }},
        {"$group": {
            "_id": None,
            "total_revenue": {"$sum": "$total"},
            "total_delivery_fees": {"$sum": "$delivery_fee"}
        }}
    ]
    
    revenue = list(db.orders.aggregate(pipeline))
    total_revenue = revenue[0]["total_revenue"] if revenue else 0
    total_fees = revenue[0]["total_delivery_fees"] if revenue else 0
    
    # Save report
    report = {
        "date": yesterday_start,
        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "cancelled_orders": cancelled_orders,
        "completion_rate": completed_orders / total_orders if total_orders > 0 else 0,
        "total_revenue": total_revenue,
        "total_delivery_fees": total_fees,
        "generated_at": datetime.utcnow()
    }
    
    db.analytics.insert_one(report)
    
    # Optionally send report (could use LLM for summary here)
    from app.celery_worker.alerts import send_ops_alert
    send_ops_alert.delay(
        level="info",
        message=f"Daily Report: {completed_orders} orders completed, R{total_revenue:.2f} revenue"
    )
    
    return report


# ============ PAYOUT & REFUND TASKS ============

@shared_task(bind=True, max_retries=3)
def process_merchant_payout(self, order_id: str):
    """
    Process payout to merchant after successful delivery.
    """
    db = get_db()
    order = db.orders.find_one({"_id": order_id})
    
    if not order:
        return {"status": "error", "message": "Order not found"}
    
    merchant_id = order.get("store_id")
    subtotal = order.get("subtotal", 0)
    platform_fee = subtotal * 0.15  # 15% platform fee
    
    payout_amount = subtotal - platform_fee
    
    # Create payout record
    payout = {
        "merchant_id": merchant_id,
        "order_id": order_id,
        "amount": payout_amount,
        "platform_fee": platform_fee,
        "status": "pending",
        "created_at": datetime.utcnow()
    }
    
    db.payouts.insert_one(payout)
    
    # TODO: Integrate with payment provider for actual transfer
    
    return {
        "status": "pending",
        "payout_amount": payout_amount,
        "platform_fee": platform_fee
    }


@shared_task(bind=True, max_retries=3)
def process_refund(self, order_id: str, reason: str, amount: Optional[float] = None):
    """
    Process refund for cancelled order.
    """
    db = get_db()
    order = db.orders.find_one({"_id": order_id})
    
    if not order:
        return {"status": "error", "message": "Order not found"}
    
    if order.get("payment_status") != "paid":
        return {"status": "skipped", "message": "No payment to refund"}
    
    refund_amount = amount or order.get("total", 0)
    
    # Create refund record
    refund = {
        "order_id": order_id,
        "amount": refund_amount,
        "reason": reason,
        "status": "pending",
        "created_at": datetime.utcnow()
    }
    
    db.refunds.insert_one(refund)
    
    # TODO: Integrate with Paystack/Yoco for actual refund
    
    # Update order
    db.orders.update_one(
        {"_id": order_id},
        {"$set": {"payment_status": "refunded"}}
    )
    
    return {
        "status": "pending",
        "refund_amount": refund_amount,
        "reason": reason
    }


@shared_task
def request_order_review(order_id: str):
    """
    Send review request after delivery.
    """
    db = get_db()
    order = db.orders.find_one({"_id": order_id})
    
    if not order:
        return {"status": "error", "message": "Order not found"}
    
    # Don't request review for cancelled orders
    if order.get("status") == "cancelled":
        return {"status": "skipped", "message": "Order was cancelled"}
    
    from app.celery_worker.alerts import send_customer_notification
    send_customer_notification.delay(
        user_id=order.get("buyer_id"),
        order_id=order_id,
        event="review_request",
        message=f"How was your order #{order_id[-6:]}? Rate your experience!",
        channels=["push"]
    )
    
    return {"status": "sent"}
