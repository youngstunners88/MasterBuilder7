"""
Alert dispatcher for iHhashi - simple multi-channel notifications.

Channels:
- Push (Firebase Cloud Messaging)
- SMS (Twilio)
- Email (SMTP or SendGrid)
- Telegram (for ops team alerts)
"""
import logging
import os
import httpx
from datetime import datetime
from typing import Optional, Dict, Any, List
from celery import shared_task

logger = logging.getLogger(__name__)


# ============ CONFIGURATION ============

# Twilio (SMS)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

# Firebase (Push)
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
FIREBASE_PRIVATE_KEY = os.getenv("FIREBASE_PRIVATE_KEY")
FIREBASE_CLIENT_EMAIL = os.getenv("FIREBASE_CLIENT_EMAIL")

# Telegram (Ops alerts)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_OPS_CHAT_ID = os.getenv("TELEGRAM_OPS_CHAT_ID")

# SendGrid (Email)
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@ihhashi.app")


# ============ BASE NOTIFICATION ============

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_notification(
    self,
    channel: str,
    recipient: str,
    title: str,
    message: str,
    data: Optional[Dict[str, Any]] = None
):
    """
    Base notification sender - routes to appropriate channel.
    """
    if channel == "push":
        return send_push_notification(recipient, title, message, data)
    elif channel == "sms":
        return send_sms(recipient, message)
    elif channel == "email":
        return send_email(recipient, title, message)
    elif channel == "telegram":
        return send_telegram_message(recipient, message)
    else:
        logger.error(f"Unknown channel: {channel}")
        return {"status": "error", "message": f"Unknown channel: {channel}"}


# ============ PUSH NOTIFICATIONS (Firebase) ============

def get_firebase_access_token():
    """Get Firebase access token for FCM."""
    import json
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    
    if not FIREBASE_PRIVATE_KEY or not FIREBASE_CLIENT_EMAIL:
        return None
    
    credentials_dict = {
        "type": "service_account",
        "project_id": FIREBASE_PROJECT_ID,
        "private_key": FIREBASE_PRIVATE_KEY.replace("\\n", "\n"),
        "client_email": FIREBASE_CLIENT_EMAIL,
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    
    credentials = service_account.Credentials.from_service_account_info(
        credentials_dict,
        scopes=["https://www.googleapis.com/auth/firebase.messaging"]
    )
    
    credentials.refresh(Request())
    return credentials.token


def send_push_notification(token: str, title: str, body: str, data: Optional[Dict] = None):
    """Send push notification via Firebase Cloud Messaging."""
    if not FIREBASE_PROJECT_ID:
        logger.warning("Firebase not configured - skipping push notification")
        return {"status": "skipped", "reason": "Firebase not configured"}
    
    try:
        access_token = get_firebase_access_token()
        if not access_token:
            return {"status": "error", "reason": "Failed to get access token"}
        
        url = f"https://fcm.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/messages:send"
        
        message = {
            "message": {
                "token": token,
                "notification": {
                    "title": title,
                    "body": body
                },
                "data": data or {}
            }
        }
        
        with httpx.Client() as client:
            response = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json=message,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Push sent to {token[:20]}...")
                return {"status": "sent"}
            else:
                logger.error(f"Push failed: {response.text}")
                return {"status": "error", "reason": response.text}
                
    except Exception as e:
        logger.error(f"Push notification error: {e}")
        return {"status": "error", "reason": str(e)}


# ============ SMS (Twilio) ============

def send_sms(to_number: str, message: str):
    """Send SMS via Twilio."""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        logger.warning("Twilio not configured - skipping SMS")
        return {"status": "skipped", "reason": "Twilio not configured"}
    
    # Format phone number for SA
    if to_number.startswith("0"):
        to_number = "+27" + to_number[1:]
    elif not to_number.startswith("+"):
        to_number = "+27" + to_number
    
    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
        
        with httpx.Client() as client:
            response = client.post(
                url,
                auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
                data={
                    "From": TWILIO_PHONE_NUMBER,
                    "To": to_number,
                    "Body": message
                },
                timeout=10
            )
            
            if response.status_code == 201:
                logger.info(f"SMS sent to {to_number}")
                return {"status": "sent"}
            else:
                logger.error(f"SMS failed: {response.text}")
                return {"status": "error", "reason": response.text}
                
    except Exception as e:
        logger.error(f"SMS error: {e}")
        return {"status": "error", "reason": str(e)}


# ============ EMAIL (SendGrid) ============

def send_email(to_email: str, subject: str, content: str):
    """Send email via SendGrid."""
    if not SENDGRID_API_KEY:
        logger.warning("SendGrid not configured - skipping email")
        return {"status": "skipped", "reason": "SendGrid not configured"}
    
    try:
        url = "https://api.sendgrid.com/v3/mail/send"
        
        email_data = {
            "personalizations": [{
                "to": [{"email": to_email}],
                "subject": subject
            }],
            "from": {"email": EMAIL_FROM},
            "content": [{
                "type": "text/plain",
                "value": content
            }]
        }
        
        with httpx.Client() as client:
            response = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {SENDGRID_API_KEY}",
                    "Content-Type": "application/json"
                },
                json=email_data,
                timeout=10
            )
            
            if response.status_code == 202:
                logger.info(f"Email sent to {to_email}")
                return {"status": "sent"}
            else:
                logger.error(f"Email failed: {response.text}")
                return {"status": "error", "reason": response.text}
                
    except Exception as e:
        logger.error(f"Email error: {e}")
        return {"status": "error", "reason": str(e)}


# ============ TELEGRAM (Ops Alerts) ============

def send_telegram_message(chat_id: str, message: str):
    """Send Telegram message."""
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram bot not configured - skipping message")
        return {"status": "skipped", "reason": "Telegram not configured"}
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        
        with httpx.Client() as client:
            response = client.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "HTML"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Telegram message sent to {chat_id}")
                return {"status": "sent"}
            else:
                logger.error(f"Telegram failed: {response.text}")
                return {"status": "error", "reason": response.text}
                
    except Exception as e:
        logger.error(f"Telegram error: {e}")
        return {"status": "error", "reason": str(e)}


# ============ HIGH-LEVEL ALERT FUNCTIONS ============

@shared_task
def send_customer_notification(
    user_id: str,
    order_id: str,
    event: str,
    message: str,
    channels: List[str] = ["push"]
):
    """
    Send notification to customer through specified channels.
    
    Looks up user's contact info from database.
    """
    from app.db import get_db
    
    db = get_db()
    user = db.users.find_one({"_id": user_id})
    
    if not user:
        logger.error(f"User {user_id} not found")
        return {"status": "error", "message": "User not found"}
    
    results = {}
    
    for channel in channels:
        if channel == "push":
            fcm_token = user.get("fcm_token")
            if fcm_token:
                results["push"] = send_push_notification(
                    fcm_token,
                    "iHhashi Update",
                    message,
                    {"order_id": order_id, "event": event}
                )
        
        elif channel == "sms":
            phone = user.get("phone")
            if phone:
                results["sms"] = send_sms(phone, message)
        
        elif channel == "email":
            email = user.get("email")
            if email:
                results["email"] = send_email(email, f"iHhashi - {event}", message)
    
    return {"status": "completed", "results": results}


@shared_task
def send_merchant_notification(
    merchant_id: str,
    order_id: str,
    event: str,
    message: str
):
    """
    Send notification to merchant/store.
    """
    from app.db import get_db
    
    db = get_db()
    merchant = db.merchants.find_one({"_id": merchant_id})
    
    if not merchant:
        logger.error(f"Merchant {merchant_id} not found")
        return {"status": "error", "message": "Merchant not found"}
    
    results = {}
    
    # Push notification
    fcm_token = merchant.get("fcm_token")
    if fcm_token:
        results["push"] = send_push_notification(
            fcm_token,
            "iHhashi - New Order" if event == "new_order" else "iHhashi Update",
            message,
            {"order_id": order_id, "event": event}
        )
    
    # Email for important events
    if event in ["new_order", "order_cancelled"]:
        email = merchant.get("email") or merchant.get("owner_email")
        if email:
            results["email"] = send_email(email, f"iHhashi - {event}", message)
    
    return {"status": "completed", "results": results}


@shared_task
def send_rider_notification(
    rider_id: str,
    event: str,
    message: str,
    data: Optional[Dict] = None
):
    """
    Send notification to rider/driver.
    """
    from app.db import get_db
    
    db = get_db()
    rider = db.drivers.find_one({"_id": rider_id})
    
    if not rider:
        logger.error(f"Rider {rider_id} not found")
        return {"status": "error", "message": "Rider not found"}
    
    results = {}
    
    # Push notification (primary)
    fcm_token = rider.get("fcm_token")
    if fcm_token:
        results["push"] = send_push_notification(
            fcm_token,
            "iHhashi Delivery",
            message,
            data or {}
        )
    
    # SMS for urgent events
    if event in ["new_delivery", "order_cancelled"]:
        phone = rider.get("phone")
        if phone:
            results["sms"] = send_sms(phone, message)
    
    return {"status": "completed", "results": results}


@shared_task
def send_ops_alert(level: str, message: str, details: Optional[Dict] = None):
    """
    Send alert to operations team via Telegram.
    
    Levels: info, medium, high, critical
    """
    if not TELEGRAM_OPS_CHAT_ID:
        logger.warning("Telegram ops chat ID not configured")
        return {"status": "skipped", "reason": "Ops chat not configured"}
    
    # Format message with level emoji
    level_emojis = {
        "info": "ℹ️",
        "medium": "⚠️",
        "high": "🔴",
        "critical": "🚨"
    }
    
    emoji = level_emojis.get(level, "📢")
    
    formatted_message = f"{emoji} <b>[{level.upper()}]</b>\n\n{message}"
    
    if details:
        formatted_message += f"\n\n<pre>{details}</pre>"
    
    formatted_message += f"\n\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} SAST"
    
    return send_telegram_message(TELEGRAM_OPS_CHAT_ID, formatted_message)


# ============ BATCH NOTIFICATIONS ============

@shared_task
def broadcast_to_riders(
    message: str,
    area: Optional[str] = None,
    rider_ids: Optional[List[str]] = None
):
    """
    Broadcast message to all or specific riders.
    """
    from app.db import get_db
    
    db = get_db()
    
    if rider_ids:
        query = {"_id": {"$in": rider_ids}}
    elif area:
        query = {"current_area": area, "status": "available"}
    else:
        query = {"status": "available"}
    
    riders = db.drivers.find(query)
    
    sent = 0
    for rider in riders:
        fcm_token = rider.get("fcm_token")
        if fcm_token:
            send_push_notification(fcm_token, "iHhashi", message, {})
            sent += 1
    
    return {"status": "completed", "riders_notified": sent}


@shared_task
def broadcast_to_merchants(message: str, category: Optional[str] = None):
    """
    Broadcast message to merchants.
    """
    from app.db import get_db
    
    db = get_db()
    
    query = {"is_active": True}
    if category:
        query["category"] = category
    
    merchants = db.merchants.find(query)
    
    sent = 0
    for merchant in merchants:
        fcm_token = merchant.get("fcm_token")
        if fcm_token:
            send_push_notification(fcm_token, "iHhashi", message, {})
            sent += 1
    
    return {"status": "completed", "merchants_notified": sent}
