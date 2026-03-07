"""
Payment Scheduler for iHhashi
Schedules automatic payouts every Sunday at 11:11 AM SAST
"""
from datetime import datetime, timedelta
from typing import List, Optional
import asyncio
from enum import Enum

# SAST = UTC+2
SAST_OFFSET = timedelta(hours=2)


class PayoutStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ScheduledPayout:
    """Scheduled payout for delivery servicemen"""
    serviceman_id: str
    amount: float  # ZAR
    status: PayoutStatus = PayoutStatus.PENDING
    scheduled_for: datetime  # Next Sunday 11:11 SAST
    processed_at: Optional[datetime] = None
    reference: Optional[str] = None
    error_message: Optional[str] = None


def get_next_payout_date() -> datetime:
    """
    Calculate next Sunday at 11:11 AM SAST
    
    Returns UTC datetime
    """
    now = datetime.utcnow()
    
    # Days until next Sunday (0 = Monday, 6 = Sunday)
    days_until_sunday = (6 - now.weekday()) % 7
    if days_until_sunday == 0:
        # Today is Sunday - check if 11:11 SAST has passed
        sast_now = now + SAST_OFFSET
        target_time_sast = sast_now.replace(hour=11, minute=11, second=0, microsecond=0)
        if sast_now >= target_time_sast:
            # Already past 11:11 SAST, schedule for next Sunday
            days_until_sunday = 7
    
    next_sunday = now + timedelta(days=days_until_sunday)
    
    # 11:11 AM SAST = 09:11 AM UTC
    target_utc = (next_sunday + SAST_OFFSET).replace(
        hour=11, minute=11, second=0, microsecond=0
    ) - SAST_OFFSET
    
    return target_utc


def is_payout_time() -> bool:
    """Check if current time is Sunday 11:11 AM SAST (with 5-minute window)"""
    now = datetime.utcnow()
    sast_now = now + SAST_OFFSET
    
    # Check if Sunday
    if sast_now.weekday() != 6:  # Sunday
        return False
    
    # Check if between 11:11 and 11:16 SAST
    current_minutes = sast_now.hour * 60 + sast_now.minute
    target_minutes = 11 * 60 + 11  # 11:11 AM
    end_minutes = 11 * 60 + 16  # 11:16 AM
    
    return target_minutes <= current_minutes < end_minutes


async def calculate_weekly_earnings(db, serviceman_id: str) -> float:
    """
    Calculate total earnings for a serviceman in the past week
    (Sunday 11:11 AM to next Sunday 11:11 AM SAST)
    """
    now = datetime.utcnow()
    sast_now = now + SAST_OFFSET
    
    # Start of current payout period (last Sunday 11:11 SAST)
    days_since_sunday = (sast_now.weekday() + 1) % 7
    if days_since_sunday == 0:
        days_since_sunday = 7
    period_start_sast = (sast_now - timedelta(days=days_since_sunday)).replace(
        hour=11, minute=11, second=0, microsecond=0
    )
    period_start_utc = period_start_sast - SAST_OFFSET
    
    # Query orders completed by this serviceman in the period
    pipeline = [
        {
            "$match": {
                "serviceman_id": serviceman_id,
                "status": "delivered",
                "delivered_at": {"$gte": period_start_utc, "$lt": now}
            }
        },
        {
            "$group": {
                "_id": None,
                "total_earnings": {"$sum": "$delivery_fee"},
                "total_tips": {"$sum": "$tip_amount"}
            }
        }
    ]
    
    result = await db.orders.aggregate(pipeline).to_list(1)
    
    if result:
        return result[0].get("total_earnings", 0) + result[0].get("total_tips", 0)
    return 0.0


async def process_weekly_payouts(db, paystack_service) -> dict:
    """
    Process all pending payouts for delivery servicemen
    
    Called every Sunday at 11:11 AM SAST
    
    Returns summary of processed payouts
    """
    if not is_payout_time():
        return {"status": "skipped", "reason": "Not payout time"}
    
    print(f"💰 Processing weekly payouts - {datetime.utcnow().isoformat()}")
    
    # Get all active servicemen with pending earnings
    servicemen = await db.delivery_servicemen.find({
        "is_verified": True,
        "total_earnings": {"$gt": 100}  # Minimum R100 for payout
    }).to_list(None)
    
    results = {
        "processed": 0,
        "failed": 0,
        "total_amount": 0.0,
        "payouts": []
    }
    
    for serviceman in servicemen:
        try:
            # Calculate weekly earnings
            weekly_earnings = await calculate_weekly_earnings(db, str(serviceman["_id"]))
            
            if weekly_earnings < 100:  # Minimum payout threshold
                continue
            
            # Create payout
            if serviceman.get("bank_name") and serviceman.get("account_number"):
                payout_result = await paystack_service.create_payout(
                    account_number=serviceman["account_number"],
                    bank_code=get_bank_code(serviceman["bank_name"]),
                    amount=weekly_earnings,
                    reason=f"iHhashi weekly payout - Week of {datetime.utcnow().strftime('%Y-%m-%d')}"
                )
                
                if payout_result.get("status"):
                    results["processed"] += 1
                    results["total_amount"] += weekly_earnings
                    results["payouts"].append({
                        "serviceman_id": str(serviceman["_id"]),
                        "name": serviceman.get("full_name"),
                        "amount": weekly_earnings,
                        "status": "success"
                    })
                    
                    # Reset weekly earnings
                    await db.delivery_servicemen.update_one(
                        {"_id": serviceman["_id"]},
                        {"$set": {"weekly_earnings": 0, "last_payout": datetime.utcnow()}}
                    )
                else:
                    results["failed"] += 1
                    results["payouts"].append({
                        "serviceman_id": str(serviceman["_id"]),
                        "name": serviceman.get("full_name"),
                        "amount": weekly_earnings,
                        "status": "failed",
                        "error": payout_result.get("message")
                    })
                    
        except Exception as e:
            results["failed"] += 1
            print(f"❌ Payout failed for {serviceman.get('full_name')}: {e}")
    
    print(f"✅ Payouts complete: {results['processed']} processed, R{results['total_amount']:.2f} total")
    
    return results


def get_bank_code(bank_name: str) -> str:
    """Get Paystack bank code for South African banks"""
    SA_BANK_CODES = {
        "ABSA": "632005",
        "Capitec": "470010",
        "FNB": "250655",
        "Nedbank": "198765",
        "Standard Bank": "051001",
        "African Bank": "430000",
        "Bidvest Bank": "462005",
        "Discovery Bank": "400200",
        "Investec": "580105",
        "Sasfin Bank": "683000",
        "TymeBank": "678910",
    }
    return SA_BANK_CODES.get(bank_name, "")


# Cron job setup for FastAPI
async def payout_scheduler_task():
    """Background task to check for payout time"""
    while True:
        try:
            if is_payout_time():
                from app.database import get_database
                from app.services.paystack import PaystackService
                
                db = await get_database()
                paystack = PaystackService()
                await process_weekly_payouts(db, paystack)
            
            # Check every minute
            await asyncio.sleep(60)
            
        except Exception as e:
            print(f"Scheduler error: {e}")
            await asyncio.sleep(60)
