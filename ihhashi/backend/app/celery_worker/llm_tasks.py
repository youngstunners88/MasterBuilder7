"""
LLM-enhanced tasks - ONLY where LLM adds value:

1. Support ticket analysis (sentiment, priority)
2. Complaint classification
3. Review summarization
4. Nduna support responses

NOT used for:
- Routing (simple dispatch)
- Anomaly detection (rules are faster)
- Status changes (deterministic)
"""
import logging
import os
import httpx
from typing import Optional, Dict, Any
from celery import shared_task
from datetime import datetime

logger = logging.getLogger(__name__)

# Groq API for fast, cheap LLM
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


def get_groq_completion(
    prompt: str,
    system: str,
    max_tokens: int = 500,
    temperature: float = 0.3
) -> str:
    """
    Get completion from Groq (fast, cheap).
    """
    if not GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set")
        return ""
    
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                logger.error(f"Groq error: {response.text}")
                return ""
                
    except Exception as e:
        logger.error(f"Groq completion error: {e}")
        return ""


# ============ SUPPORT TICKET ANALYSIS ============

@shared_task
def analyze_support_ticket(ticket_id: str):
    """
    Analyze support ticket for:
    - Sentiment (negative/neutral/positive)
    - Priority (low/medium/high/urgent)
    - Category (delivery, payment, refund, app_bug, other)
    - Suggested response
    
    This is where LLM adds real value - understanding human language.
    """
    from app.db import get_db
    
    db = get_db()
    ticket = db.support_tickets.find_one({"_id": ticket_id})
    
    if not ticket:
        return {"status": "error", "message": "Ticket not found"}
    
    message = ticket.get("message", "")
    user_id = ticket.get("user_id")
    
    # Get context (recent orders)
    recent_orders = list(db.orders.find(
        {"buyer_id": user_id},
        sort=[("created_at", -1)],
        limit=3
    ))
    
    context = f"User's recent orders: {len(recent_orders)}"
    if recent_orders:
        last_order = recent_orders[0]
        context += f" (last: {last_order.get('status', 'unknown')})"
    
    prompt = f"""Analyze this support ticket:

User message: "{message}"

Context: {context}

Respond in JSON format:
{{
    "sentiment": "negative|neutral|positive",
    "priority": "low|medium|high|urgent",
    "category": "delivery|payment|refund|app_bug|account|other",
    "summary": "One sentence summary",
    "suggested_response": "Brief empathetic response to send to user"
}}

Priority rules:
- urgent: refund requested, money lost, offensive language
- high: order not received, wrong order, significant delay
- medium: minor complaint, feature request
- low: general question, feedback"""

    response = get_groq_completion(
        prompt,
        system="You are a support ticket analyzer. Respond only in valid JSON.",
        max_tokens=300,
        temperature=0.2
    )
    
    if response:
        try:
            import json
            analysis = json.loads(response)
            
            # Update ticket
            db.support_tickets.update_one(
                {"_id": ticket_id},
                {"$set": {
                    "ai_analysis": analysis,
                    "analyzed_at": datetime.utcnow()
                }}
            )
            
            # If high priority, alert ops
            if analysis.get("priority") in ["high", "urgent"]:
                from app.celery_worker.alerts import send_ops_alert
                send_ops_alert.delay(
                    level=analysis["priority"],
                    message=f"Support ticket: {analysis.get('summary', 'No summary')}",
                    details={"ticket_id": ticket_id, "sentiment": analysis.get("sentiment")}
                )
            
            return {"status": "completed", "analysis": analysis}
            
        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM response: {response}")
            return {"status": "error", "message": "Failed to parse analysis"}
    
    return {"status": "error", "message": "LLM request failed"}


# ============ COMPLAINT CLASSIFICATION ============

@shared_task
def classify_complaint(complaint_id: str):
    """
    Classify delivery/order complaint for refund processing.
    
    Determines if complaint is valid and what action to take.
    """
    from app.db import get_db
    
    db = get_db()
    complaint = db.complaints.find_one({"_id": complaint_id})
    
    if not complaint:
        return {"status": "error", "message": "Complaint not found"}
    
    order_id = complaint.get("order_id")
    order = db.orders.find_one({"_id": order_id}) if order_id else None
    
    prompt = f"""Classify this delivery complaint:

Complaint: "{complaint.get('message', '')}"

Order details:
- Status: {order.get('status', 'N/A') if order else 'N/A'}
- Total: R{order.get('total', 0) if order else 0}
- Delivery time: {complaint.get('delivery_time', 'N/A')}

Respond in JSON:
{{
    "is_valid": true|false,
    "issue_type": "late_delivery|wrong_order|missing_items|quality|other",
    "severity": "minor|moderate|major",
    "suggested_action": "none|partial_refund|full_refund|credit|investigate",
    "credit_amount": 0-100,
    "explanation": "Brief explanation"
}}"""

    response = get_groq_completion(
        prompt,
        system="You are a complaint classifier. Be fair to both customer and business. Respond only in valid JSON.",
        max_tokens=200,
        temperature=0.2
    )
    
    if response:
        try:
            import json
            classification = json.loads(response)
            
            db.complaints.update_one(
                {"_id": complaint_id},
                {"$set": {
                    "classification": classification,
                    "classified_at": datetime.utcnow()
                }}
            )
            
            return {"status": "completed", "classification": classification}
            
        except json.JSONDecodeError:
            return {"status": "error", "message": "Failed to parse classification"}
    
    return {"status": "error", "message": "LLM request failed"}


# ============ REVIEW SUMMARIZATION ============

@shared_task
def summarize_merchant_reviews(merchant_id: str):
    """
    Summarize recent reviews for a merchant.
    
    Provides actionable insights without reading all reviews manually.
    """
    from app.db import get_db
    
    db = get_db()
    
    # Get last 20 reviews
    reviews = list(db.reviews.find(
        {"merchant_id": merchant_id},
        sort=[("created_at", -1)],
        limit=20
    ))
    
    if not reviews:
        return {"status": "skipped", "message": "No reviews found"}
    
    reviews_text = "\n".join([
        f"- {r.get('rating', 0)}/5: {r.get('comment', 'No comment')[:100]}"
        for r in reviews
    ])
    
    avg_rating = sum(r.get("rating", 0) for r in reviews) / len(reviews)
    
    prompt = f"""Summarize these merchant reviews:

{reviews_text}

Average rating: {avg_rating:.1f}/5

Respond in JSON:
{{
    "overall_sentiment": "positive|mixed|negative",
    "strengths": ["strength1", "strength2"],
    "improvements": ["improvement1", "improvement2"],
    "summary": "2-3 sentence summary for the merchant"
}}"""

    response = get_groq_completion(
        prompt,
        system="You are a review analyst. Be constructive and specific. Respond only in valid JSON.",
        max_tokens=250,
        temperature=0.3
    )
    
    if response:
        try:
            import json
            summary = json.loads(response)
            
            db.merchant_review_summaries.insert_one({
                "merchant_id": merchant_id,
                "summary": summary,
                "reviews_analyzed": len(reviews),
                "average_rating": avg_rating,
                "created_at": datetime.utcnow()
            })
            
            return {"status": "completed", "summary": summary}
            
        except json.JSONDecodeError:
            return {"status": "error", "message": "Failed to parse summary"}
    
    return {"status": "error", "message": "LLM request failed"}


# ============ NDUNA SUPPORT RESPONSE ============

@shared_task
def generate_nduna_response(
    user_message: str,
    context: Optional[Dict] = None,
    language: str = "en"
):
    """
    Generate support response from Nduna (iHhashi's AI assistant).
    
    This is the main LLM use case - conversational support.
    """
    # Language-specific system prompts
    system_prompts = {
        "en": """You are Nduna, a helpful support assistant for iHhashi, a delivery platform in South Africa.
You help customers with orders, tracking, refunds, and general questions.
Be friendly, concise, and helpful. Use South African context when appropriate.
If you cannot help, suggest contacting support@ihhashi.app""",
        
        "zu": """You are Nduna, a helpful support assistant for iHhashi.
Respond in isiZulu. Be friendly and helpful.""",
        
        "xh": """You are Nduna, a helpful support assistant for iHhashi.
Respond in isiXhosa. Be friendly and helpful.""",
        
        "af": """You are Nduna, a helpful support assistant for iHhashi.
Respond in Afrikaans. Be friendly and helpful."""
    }
    
    system = system_prompts.get(language, system_prompts["en"])
    
    # Add context if available
    if context:
        context_str = f"\n\nContext:\n"
        if context.get("order_status"):
            context_str += f"Order status: {context['order_status']}\n"
        if context.get("recent_orders"):
            context_str += f"Recent orders: {context['recent_orders']}\n"
        system += context_str
    
    response = get_groq_completion(
        user_message,
        system=system,
        max_tokens=400,
        temperature=0.7
    )
    
    if response:
        return {
            "status": "completed",
            "response": response,
            "language": language
        }
    
    return {"status": "error", "message": "LLM request failed"}
