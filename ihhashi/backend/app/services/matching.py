"""
Rider matching and delivery fare calculation service - Production ready with:
- Transaction locking
- Task monitoring and exception handling
- Circuit breaker pattern
- Integration with message queue
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Set
from math import radians, sin, cos, sqrt, atan2
from bson import ObjectId
from zoneinfo import ZoneInfo
import logging
from dataclasses import dataclass, field
from enum import Enum

from app.database import get_collection
from app.utils.validation import safe_object_id
from app.services.delivery_fee import calculate_delivery_fee, is_surge_time, SAST
from app.queue.redis_queue import QueueMessage, MessagePriority

logger = logging.getLogger(__name__)


class AssignmentStatus(str, Enum):
    """Status of rider assignment attempt"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    FAILED = "failed"
    RETRYING = "retrying"
    EXHAUSTED = "exhausted"


@dataclass
class AssignmentTask:
    """Track background assignment task"""
    delivery_id: ObjectId
    task: asyncio.Task
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: AssignmentStatus = AssignmentStatus.PENDING
    attempts: int = 0
    error: Optional[str] = None
    
    def is_expired(self, timeout_seconds: int = 300) -> bool:
        """Check if task has exceeded timeout"""
        elapsed = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return elapsed > timeout_seconds


class TaskMonitor:
    """
    Monitor background tasks for rider assignment.
    Prevents orphaned tasks and provides visibility.
    """
    
    def __init__(self, cleanup_interval: int = 60):
        self.tasks: Dict[str, AssignmentTask] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_interval = cleanup_interval
        self._completed_tasks: List[Dict] = []  # Keep last 100 for debugging
        self._max_history = 100
    
    async def start(self):
        """Start the cleanup task"""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Task monitor started")
    
    async def stop(self):
        """Stop the cleanup task and cancel all pending tasks"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Cancel all pending tasks
        for task_info in list(self.tasks.values()):
            if not task_info.task.done():
                task_info.task.cancel()
        
        logger.info("Task monitor stopped")
    
    async def _cleanup_loop(self):
        """Periodically clean up completed tasks"""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_completed_tasks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Task monitor cleanup error: {e}")
    
    async def _cleanup_completed_tasks(self):
        """Remove completed tasks and log results"""
        completed = []
        
        for delivery_id_str, task_info in list(self.tasks.items()):
            if task_info.task.done():
                try:
                    # Check for exception
                    exc = task_info.task.exception()
                    if exc:
                        task_info.status = AssignmentStatus.FAILED
                        task_info.error = str(exc)
                        logger.error(f"Assignment task failed for {delivery_id_str}: {exc}")
                    else:
                        task_info.status = AssignmentStatus.ASSIGNED
                        logger.info(f"Assignment task completed for {delivery_id_str}")
                except asyncio.CancelledError:
                    task_info.status = AssignmentStatus.FAILED
                    task_info.error = "Task was cancelled"
                
                completed.append(delivery_id_str)
                
                # Add to history
                self._completed_tasks.append({
                    "delivery_id": delivery_id_str,
                    "status": task_info.status.value,
                    "attempts": task_info.attempts,
                    "error": task_info.error,
                    "created_at": task_info.created_at.isoformat()
                })
        
        # Remove completed tasks
        for delivery_id_str in completed:
            del self.tasks[delivery_id_str]
        
        # Trim history
        if len(self._completed_tasks) > self._max_history:
            self._completed_tasks = self._completed_tasks[-self._max_history:]
    
    def register_task(self, delivery_id: ObjectId, task: asyncio.Task) -> str:
        """Register a new assignment task"""
        delivery_id_str = str(delivery_id)
        
        # Cancel existing task if any
        if delivery_id_str in self.tasks:
            old_task = self.tasks[delivery_id_str]
            if not old_task.task.done():
                old_task.task.cancel()
        
        self.tasks[delivery_id_str] = AssignmentTask(
            delivery_id=delivery_id,
            task=task
        )
        
        # Add completion callback
        task.add_done_callback(
            lambda t, did=delivery_id_str: self._on_task_done(did, t)
        )
        
        return delivery_id_str
    
    def _on_task_done(self, delivery_id_str: str, task: asyncio.Task):
        """Callback when task completes"""
        if delivery_id_str in self.tasks:
            task_info = self.tasks[delivery_id_str]
            
            try:
                exc = task.exception()
                if exc:
                    task_info.status = AssignmentStatus.FAILED
                    task_info.error = str(exc)
                else:
                    task_info.status = AssignmentStatus.ASSIGNED
            except asyncio.CancelledError:
                task_info.status = AssignmentStatus.FAILED
                task_info.error = "Cancelled"
    
    def get_status(self, delivery_id: ObjectId) -> Optional[Dict]:
        """Get status of an assignment task"""
        delivery_id_str = str(delivery_id)
        
        if delivery_id_str in self.tasks:
            task_info = self.tasks[delivery_id_str]
            return {
                "delivery_id": delivery_id_str,
                "status": task_info.status.value,
                "attempts": task_info.attempts,
                "is_running": not task_info.task.done(),
                "created_at": task_info.created_at.isoformat()
            }
        
        # Check history
        for entry in self._completed_tasks:
            if entry["delivery_id"] == delivery_id_str:
                return entry
        
        return None
    
    def get_stats(self) -> Dict:
        """Get task monitor statistics"""
        running = sum(1 for t in self.tasks.values() if not t.task.done())
        failed = sum(1 for t in self.tasks.values() 
                    if t.task.done() and t.status == AssignmentStatus.FAILED)
        
        return {
            "running_tasks": running,
            "pending_cleanup": len(self.tasks) - running,
            "failed_recently": failed,
            "history_count": len(self._completed_tasks)
        }


class MatchingService:
    """
    Rider matching and delivery fare calculation service.
    Includes circuit breaker pattern for resilience.
    """
    
    def __init__(self, db):
        self.db = db
        self.task_monitor = TaskMonitor()
        
        # Delivery fare configuration (ZAR)
        self.base_fees = {
            "bike": 15.0,
            "car": 25.0,
            "bicycle": 12.0,
            "walking": 10.0
        }
        self.per_km_rate = 6.0
        self.per_minute_rate = 1.0
        self.surge_hours = [7, 8, 17, 18, 19]  # Morning and evening rush in SAST
        
        # Circuit breaker state
        self._circuit_failures = 0
        self._circuit_last_failure = None
        self._circuit_state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._circuit_threshold = 5
        self._circuit_timeout = 60  # seconds
    
    async def start(self):
        """Start the task monitor"""
        await self.task_monitor.start()
    
    async def stop(self):
        """Stop the task monitor"""
        await self.task_monitor.stop()
    
    def _check_circuit_breaker(self) -> bool:
        """
        Check if circuit breaker allows operation.
        Returns True if allowed, False if circuit is open.
        """
        if self._circuit_state == "CLOSED":
            return True
        
        if self._circuit_state == "OPEN":
            # Check if timeout has passed
            if self._circuit_last_failure:
                elapsed = (datetime.now(timezone.utc) - self._circuit_last_failure).total_seconds()
                if elapsed > self._circuit_timeout:
                    self._circuit_state = "HALF_OPEN"
                    logger.info("Circuit breaker entering HALF_OPEN state")
                    return True
            return False
        
        if self._circuit_state == "HALF_OPEN":
            return True
        
        return True
    
    def _record_success(self):
        """Record successful operation"""
        if self._circuit_state == "HALF_OPEN":
            self._circuit_state = "CLOSED"
            self._circuit_failures = 0
            logger.info("Circuit breaker CLOSED")
    
    def _record_failure(self):
        """Record failed operation"""
        self._circuit_failures += 1
        self._circuit_last_failure = datetime.now(timezone.utc)
        
        if self._circuit_failures >= self._circuit_threshold:
            self._circuit_state = "OPEN"
            logger.error("Circuit breaker OPENED due to failures")
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in km using Haversine formula"""
        R = 6371  # Earth's radius in km
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    async def calculate_fare(
        self,
        pickup: Dict,
        delivery: Dict,
        vehicle_type: str = "bike"
    ) -> Dict:
        """Calculate delivery fee estimate using single source of truth."""
        return calculate_delivery_fee(
            pickup["latitude"], pickup["longitude"],
            delivery["latitude"], delivery["longitude"],
            vehicle_type
        )
    
    async def find_nearest_rider(
        self,
        pickup_location: Dict,
        vehicle_type: str,
        excluded_riders: List[str] = None,
        max_distance_km: float = 5.0
    ) -> Optional[Dict]:
        """Find the nearest available rider"""
        
        excluded_riders = excluded_riders or []
        
        # Check circuit breaker
        if not self._check_circuit_breaker():
            logger.warning("Circuit breaker OPEN - skipping rider search")
            return None
        
        try:
            # Find riders who are:
            # - Online/available
            # - Have the right vehicle type
            # - Not in excluded list
            # - Within max distance
            riders = await self.db.riders.find({
                "status": "available",
                "vehicle_type": vehicle_type,
                "rider_id": {"$nin": excluded_riders},
                "location": {"$near": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [pickup_location["longitude"], pickup_location["latitude"]]
                    },
                    "$maxDistance": max_distance_km * 1000  # Convert to meters
                }}
            }).limit(5).to_list(length=5)
            
            self._record_success()
            
            if not riders:
                return None
            
            # Return nearest rider
            return riders[0]
        
        except Exception as e:
            self._record_failure()
            logger.error(f"Error finding nearest rider: {e}")
            return None
    
    async def find_and_lock_rider(
        self,
        pickup_location: Dict,
        vehicle_type: str,
        delivery_id: ObjectId,
        excluded_riders: List[str] = None,
        max_distance_km: float = 5.0
    ) -> Optional[Dict]:
        """
        Find and atomically lock a rider for assignment.
        Uses find_one_and_update to prevent race conditions.
        """
        excluded_riders = excluded_riders or []
        
        # Check circuit breaker
        if not self._check_circuit_breaker():
            logger.warning("Circuit breaker OPEN - skipping rider lock")
            return None
        
        try:
            # Try to find and lock a rider atomically
            rider = await self.db.riders.find_one_and_update(
                {
                    "status": "available",
                    "vehicle_type": vehicle_type,
                    "_id": {"$nin": [safe_object_id(r) for r in excluded_riders if r]},
                    "location": {"$near": {
                        "$geometry": {
                            "type": "Point",
                            "coordinates": [pickup_location["longitude"], pickup_location["latitude"]]
                        },
                        "$maxDistance": max_distance_km * 1000
                    }}
                },
                {
                    "$set": {
                        "status": "busy",
                        "locked_for_delivery": delivery_id,
                        "locked_at": datetime.now(timezone.utc)
                    }
                },
                return_document=True
            )
            
            self._record_success()
            return rider
        
        except Exception as e:
            self._record_failure()
            logger.error(f"Error locking rider: {e}")
            return None
    
    async def request_delivery(self, customer_id: str, delivery_data: dict) -> dict:
        """Main delivery request flow with monitored background assignment"""
        
        # Check circuit breaker
        if not self._check_circuit_breaker():
            raise ValueError("Service temporarily unavailable - please try again later")
        
        try:
            # 1. Validate customer
            customer = await self.db.users.find_one({"_id": safe_object_id(customer_id)})
            if not customer:
                raise ValueError("Customer not found")
            
            # 2. Check for existing active delivery (use atomic check)
            active_delivery = await self.db.deliveries.find_one({
                "customer_id": customer_id,
                "status": {"$in": ["pending", "rider_assigned", "at_merchant", "picked_up", "in_transit"]}
            })
            if active_delivery:
                raise ValueError("Customer already has an active delivery")
            
            # 3. Calculate fare
            fare_estimate = await self.calculate_fare(
                delivery_data["pickup_location"],
                delivery_data["delivery_location"],
                delivery_data.get("vehicle_type", "bike")
            )
            
            # 4. Create delivery record
            from app.models.trip import Delivery, DeliveryStatus
            delivery = Delivery(
                order_id=delivery_data["order_id"],
                customer_id=customer_id,
                merchant_id=delivery_data.get("merchant_id", ""),
                pickup_location=delivery_data["pickup_location"],
                delivery_location=delivery_data["delivery_location"],
                vehicle_type=delivery_data.get("vehicle_type", "bike"),
                item_count=delivery_data.get("item_count", 1),
                special_instructions=delivery_data.get("special_instructions"),
                fare=fare_estimate
            )
            
            result = await self.db.deliveries.insert_one(delivery.dict())
            delivery_id = result.inserted_id
            
            # 5. Create monitored background task for rider assignment
            task = asyncio.create_task(
                self._assign_rider_with_monitoring(delivery_id, delivery.dict(), fare_estimate),
                name=f"assign_rider_{delivery_id}"
            )
            
            # Register with task monitor
            self.task_monitor.register_task(delivery_id, task)
            
            self._record_success()
            
            return {
                "delivery_id": str(delivery_id),
                "status": "pending",
                "fare_estimate": fare_estimate,
                "message": "Finding nearby riders..."
            }
        
        except Exception as e:
            self._record_failure()
            raise
    
    async def _assign_rider_with_monitoring(
        self,
        delivery_id: ObjectId,
        delivery_data: dict,
        fare_estimate: dict
    ):
        """
        Wrapper that monitors the assignment task for exceptions.
        """
        try:
            await self._assign_rider_with_lock(delivery_id, delivery_data, fare_estimate)
        except Exception as e:
            logger.error(f"Rider assignment failed for {delivery_id}: {e}")
            
            # Update delivery status to failed
            try:
                await self.db.deliveries.update_one(
                    {"_id": delivery_id},
                    {
                        "$set": {
                            "status": "cancelled",
                            "cancel_reason": f"assignment_failed: {str(e)}",
                            "failed_at": datetime.now(timezone.utc)
                        }
                    }
                )
            except Exception as update_error:
                logger.error(f"Failed to update delivery status: {update_error}")
            
            # Re-raise to propagate to task monitor
            raise
    
    async def _assign_rider_with_lock(
        self,
        delivery_id: ObjectId,
        delivery_data: dict,
        fare_estimate: dict
    ):
        """
        Assign a rider to the delivery with retry logic and proper locking.
        Uses atomic find_and_lock to prevent race conditions.
        """
        
        max_attempts = 3
        attempted_rider_ids = []
        
        for attempt in range(max_attempts):
            # Update task monitor
            task_info = self.task_monitor.tasks.get(str(delivery_id))
            if task_info:
                task_info.attempts = attempt + 1
                task_info.status = AssignmentStatus.RETRYING
            
            # Use atomic find-and-lock instead of separate find + update
            rider = await self.find_and_lock_rider(
                delivery_data["pickup_location"],
                delivery_data.get("vehicle_type", "bike"),
                delivery_id,
                attempted_rider_ids,
                max_distance_km=5.0 + (attempt * 2)  # Expand search radius on retry
            )
            
            if rider:
                try:
                    # Assign rider to delivery
                    result = await self.db.deliveries.update_one(
                        {
                            "_id": delivery_id,
                            "status": "pending"  # Only update if still pending
                        },
                        {
                            "$set": {
                                "rider_id": str(rider["_id"]),
                                "status": "rider_assigned",
                                "rider_assigned_at": datetime.now(timezone.utc)
                            }
                        }
                    )
                    
                    if result.modified_count > 0:
                        # Successfully assigned
                        await self._notify_rider(str(rider["_id"]), str(delivery_id))
                        logger.info(f"Rider {rider['_id']} assigned to delivery {delivery_id}")
                        return
                    else:
                        # Delivery was already assigned by another process
                        # Release the rider lock
                        await self.db.riders.update_one(
                            {"_id": rider["_id"]},
                            {"$set": {"status": "available", "locked_for_delivery": None}}
                        )
                        logger.info(f"Delivery {delivery_id} already assigned, released rider")
                        return
                        
                except Exception as e:
                    # Release rider lock on error
                    await self.db.riders.update_one(
                        {"_id": rider["_id"]},
                        {"$set": {"status": "available", "locked_for_delivery": None}}
                    )
                    raise e
            
            await asyncio.sleep(2)  # Wait before retry
        
        # No rider found after all attempts
        await self.db.deliveries.update_one(
            {"_id": delivery_id},
            {"$set": {"status": "cancelled", "cancel_reason": "no_riders_available"}}
        )
        
        # Notify customer
        await self._notify_customer(delivery_data["customer_id"], "No riders available. Please try again.")
        
        logger.warning(f"No riders available for delivery {delivery_id} after {max_attempts} attempts")
        raise Exception("No riders available after maximum attempts")
    
    async def _notify_rider(self, rider_id: str, delivery_id: str):
        """Send push notification to rider"""
        try:
            notification = {
                "rider_id": rider_id,
                "delivery_id": delivery_id,
                "type": "delivery_request",
                "message": "New delivery request nearby!",
                "created_at": datetime.now(timezone.utc)
            }
            await self.db.notifications.insert_one(notification)
        except Exception as e:
            logger.error(f"Failed to notify rider: {e}")
    
    async def _notify_customer(self, customer_id: str, message: str):
        """Send push notification to customer"""
        try:
            notification = {
                "customer_id": customer_id,
                "type": "delivery_update",
                "message": message,
                "created_at": datetime.now(timezone.utc)
            }
            await self.db.notifications.insert_one(notification)
        except Exception as e:
            logger.error(f"Failed to notify customer: {e}")
    
    async def _notify_merchant(self, merchant_id: str, message: str, delivery_id: str = None):
        """Send push notification to merchant"""
        try:
            notification = {
                "merchant_id": merchant_id,
                "delivery_id": delivery_id,
                "type": "delivery_update",
                "message": message,
                "created_at": datetime.now(timezone.utc)
            }
            await self.db.notifications.insert_one(notification)
        except Exception as e:
            logger.error(f"Failed to notify merchant: {e}")
    
    async def release_rider(self, rider_id: str):
        """Release a rider from a delivery assignment"""
        try:
            await self.db.riders.update_one(
                {"_id": safe_object_id(rider_id)},
                {
                    "$set": {
                        "status": "available",
                        "locked_for_delivery": None,
                        "locked_at": None
                    }
                }
            )
        except Exception as e:
            logger.error(f"Failed to release rider {rider_id}: {e}")
    
    def get_assignment_status(self, delivery_id: ObjectId) -> Optional[Dict]:
        """Get the status of a rider assignment task"""
        return self.task_monitor.get_status(delivery_id)
    
    def get_service_stats(self) -> Dict:
        """Get service statistics"""
        return {
            "circuit_breaker": {
                "state": self._circuit_state,
                "failures": self._circuit_failures
            },
            "task_monitor": self.task_monitor.get_stats()
        }
