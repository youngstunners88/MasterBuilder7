"""
Enhanced database indexes for optimal query performance and production scaling
"""
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

logger = logging.getLogger(__name__)


async def create_indexes(db: AsyncIOMotorDatabase):
    """Create all required database indexes for production"""
    
    indexes_created = []
    
    # Orders collection indexes
    try:
        await db.orders.create_index("buyer_id")
        await db.orders.create_index("store_id")
        await db.orders.create_index("status")
        await db.orders.create_index("created_at")
        await db.orders.create_index([("created_at", -1)])
        await db.orders.create_index([("buyer_id", 1), ("status", 1)])
        await db.orders.create_index([("store_id", 1), ("status", 1)])
        # Compound index for order queries by status + date
        await db.orders.create_index([("status", 1), ("created_at", -1)])
        # Index for pending order queries
        await db.orders.create_index([("status", 1), ("buyer_id", 1)])
        indexes_created.append("orders")
        logger.info("Created orders indexes")
    except Exception as e:
        logger.error(f"Failed to create orders indexes: {e}")
    
    # Users collection indexes
    try:
        await db.users.create_index("email", unique=True)
        await db.users.create_index("phone", unique=True, sparse=True)
        await db.users.create_index([("email", 1), ("is_active", 1)])
        # Index for admin queries
        await db.users.create_index([("role", 1), ("created_at", -1)])
        indexes_created.append("users")
        logger.info("Created users indexes")
    except Exception as e:
        logger.error(f"Failed to create users indexes: {e}")
    
    # Drivers/Riders collection indexes
    try:
        await db.drivers.create_index("status")
        await db.drivers.create_index([("status", 1), ("vehicle_type", 1)])
        # Geo index for location-based queries
        await db.drivers.create_index([("current_location", "2dsphere")])
        # Index for driver rating queries
        await db.drivers.create_index([("rating", -1)])
        indexes_created.append("drivers")
        logger.info("Created drivers indexes")
    except Exception as e:
        logger.error(f"Failed to create drivers indexes: {e}")
    
    # Riders collection indexes (for delivery riders)
    try:
        await db.riders.create_index("status")
        await db.riders.create_index([("status", 1), ("vehicle_type", 1)])
        # Geo index for location-based queries
        await db.riders.create_index([("location", "2dsphere")])
        # TTL index for stale locks (auto-release after 10 minutes)
        await db.riders.create_index("locked_at", expireAfterSeconds=600)
        # Index for locked deliveries
        await db.riders.create_index(["locked_for_delivery", 1])
        indexes_created.append("riders")
        logger.info("Created riders indexes")
    except Exception as e:
        logger.error(f"Failed to create riders indexes: {e}")
    
    # Payments collection indexes
    try:
        await db.payments.create_index("reference", unique=True)
        await db.payments.create_index("user_id")
        await db.payments.create_index("status")
        await db.payments.create_index([("user_id", 1), ("created_at", -1)])
        # Index for payment reconciliation
        await db.payments.create_index([("status", 1), ("created_at", 1)])
        # Index for webhook lookups
        await db.payments.create_index(["transfer_code", 1], sparse=True)
        indexes_created.append("payments")
        logger.info("Created payments indexes")
    except Exception as e:
        logger.error(f"Failed to create payments indexes: {e}")
    
    # Payment Webhooks collection indexes (idempotency)
    try:
        # Unique index on event_id prevents duplicate webhook processing
        await db.payment_webhooks.create_index("event_id", unique=True)
        await db.payment_webhooks.create_index([("received_at", -1)])
        # TTL index for old webhook records (30 days)
        await db.payment_webhooks.create_index(
            "received_at", 
            expireAfterSeconds=2592000
        )
        indexes_created.append("payment_webhooks")
        logger.info("Created payment_webhooks indexes")
    except Exception as e:
        logger.error(f"Failed to create payment_webhooks indexes: {e}")
    
    # Products collection indexes
    try:
        await db.products.create_index("store_id")
        await db.products.create_index([("store_id", 1), ("category", 1)])
        await db.products.create_index([("store_id", 1), ("is_available", 1)])
        # Text index for search with weights
        await db.products.create_index(
            [("name", "text"), ("description", "text")],
            weights={"name": 10, "description": 5}
        )
        # Index for price range queries
        await db.products.create_index([("price", 1)])
        indexes_created.append("products")
        logger.info("Created products indexes")
    except Exception as e:
        logger.error(f"Failed to create products indexes: {e}")
    
    # Stores/Merchants collection indexes
    try:
        await db.stores.create_index("owner_id")
        await db.stores.create_index("status")
        await db.stores.create_index([("status", 1), ("is_open", 1)])
        # Geo index for location-based queries
        await db.stores.create_index([("location", "2dsphere")])
        # Text index for store search
        await db.stores.create_index(
            [("name", "text"), ("description", "text")]
        )
        indexes_created.append("stores")
        logger.info("Created stores indexes")
    except Exception as e:
        logger.error(f"Failed to create stores indexes: {e}")
    
    # Deliveries collection indexes
    try:
        await db.deliveries.create_index("customer_id")
        await db.deliveries.create_index("rider_id")
        await db.deliveries.create_index("status")
        await db.deliveries.create_index([("rider_id", 1), ("status", 1)])
        # Index for active deliveries lookup
        await db.deliveries.create_index([("customer_id", 1), ("status", 1)])
        # TTL index for completed deliveries (90 days retention)
        await db.deliveries.create_index(
            "completed_at",
            expireAfterSeconds=7776000,
            partialFilterExpression={"status": "completed"}
        )
        indexes_created.append("deliveries")
        logger.info("Created deliveries indexes")
    except Exception as e:
        logger.error(f"Failed to create deliveries indexes: {e}")
    
    # Notifications collection indexes
    try:
        await db.notifications.create_index([("user_id", 1), ("created_at", -1)])
        await db.notifications.create_index([("read", 1)])
        # TTL index to auto-delete old notifications (30 days)
        await db.notifications.create_index("created_at", expireAfterSeconds=2592000)
        # Index for notification type filtering
        await db.notifications.create_index([("type", 1), ("created_at", -1)])
        indexes_created.append("notifications")
        logger.info("Created notifications indexes")
    except Exception as e:
        logger.error(f"Failed to create notifications indexes: {e}")
    
    # Route Memory collections (Phase 1)
    try:
        # Route segments - geospatial index for location queries
        await db.route_segments.create_index([("start_point", "2dsphere")])
        await db.route_segments.create_index([("end_point", "2dsphere")])
        await db.route_segments.create_index("road_type")
        await db.route_segments.create_index([("created_at", -1)])
        # Compound index for route lookups
        await db.route_segments.create_index([
            ("start_point", "2dsphere"),
            ("end_point", "2dsphere")
        ])
        indexes_created.append("route_segments")
        logger.info("Created route_segments indexes")
    except Exception as e:
        logger.error(f"Failed to create route_segments indexes: {e}")
    
    try:
        # Driver insights - geospatial + type queries
        await db.driver_insights.create_index([("location", "2dsphere")])
        await db.driver_insights.create_index("type")
        await db.driver_insights.create_index("driver_id")
        await db.driver_insights.create_index([("created_at", -1)])
        await db.driver_insights.create_index("expires_at")
        # Compound index for driver insight queries
        await db.driver_insights.create_index([
            ("driver_id", 1),
            ("type", 1),
            ("created_at", -1)
        ])
        indexes_created.append("driver_insights")
        logger.info("Created driver_insights indexes")
    except Exception as e:
        logger.error(f"Failed to create driver_insights indexes: {e}")
    
    try:
        # Actual time records - driver stats + time queries
        await db.actual_time_records.create_index("driver_id")
        await db.actual_time_records.create_index("route_id")
        await db.actual_time_records.create_index([("driver_id", 1), ("created_at", -1)])
        await db.actual_time_records.create_index([("time_of_day", 1), ("day_of_week", 1)])
        # Index for ETA calculations
        await db.actual_time_records.create_index([
            ("route_id", 1),
            ("time_of_day", 1),
            ("day_of_week", 1)
        ])
        indexes_created.append("actual_time_records")
        logger.info("Created actual_time_records indexes")
    except Exception as e:
        logger.error(f"Failed to create actual_time_records indexes: {e}")
    
    try:
        # Route feedback - driver history queries
        await db.route_feedback.create_index("driver_id")
        await db.route_feedback.create_index("route_id")
        await db.route_feedback.create_index([("driver_id", 1), ("created_at", -1)])
        await db.route_feedback.create_index("feedback_type")
        # Compound index for route quality analysis
        await db.route_feedback.create_index([
            ("route_id", 1),
            ("feedback_type", 1),
            ("created_at", -1)
        ])
        indexes_created.append("route_feedback")
        logger.info("Created route_feedback indexes")
    except Exception as e:
        logger.error(f"Failed to create route_feedback indexes: {e}")
    
    # Referral and Rewards collections
    try:
        # Referral codes - unique codes and user lookups
        await db.referral_codes.create_index("code", unique=True)
        await db.referral_codes.create_index("user_id")
        await db.referral_codes.create_index("referral_type")
        await db.referral_codes.create_index([("user_id", 1), ("referral_type", 1)])
        indexes_created.append("referral_codes")
        logger.info("Created referral_codes indexes")
    except Exception as e:
        logger.error(f"Failed to create referral_codes indexes: {e}")
    
    try:
        # Referrals - track referrals efficiently
        await db.referrals.create_index("referrer_id")
        await db.referrals.create_index("referee_id")
        await db.referrals.create_index("referral_code")
        await db.referrals.create_index("status")
        await db.referrals.create_index([("referrer_id", 1), ("status", 1)])
        await db.referrals.create_index([("referral_type", 1), ("status", 1)])
        await db.referrals.create_index([("created_at", -1)])
        # Index for pending referral processing
        await db.referrals.create_index([
            ("status", 1),
            ("referral_type", 1),
            ("created_at", 1)
        ])
        indexes_created.append("referrals")
        logger.info("Created referrals indexes")
    except Exception as e:
        logger.error(f"Failed to create referrals indexes: {e}")
    
    try:
        # Customer reward accounts - unique customer_id and referral_code
        await db.customer_reward_accounts.create_index("customer_id", unique=True)
        await db.customer_reward_accounts.create_index("referral_code", unique=True, sparse=True)
        await db.customer_reward_accounts.create_index("tier")
        await db.customer_reward_accounts.create_index("hashi_coins_balance")
        # Index for tier upgrade queries
        await db.customer_reward_accounts.create_index([
            ("tier", 1),
            ("completed_referrals", 1)
        ])
        indexes_created.append("customer_reward_accounts")
        logger.info("Created customer_reward_accounts indexes")
    except Exception as e:
        logger.error(f"Failed to create customer_reward_accounts indexes: {e}")
    
    try:
        # Coin transactions - transaction history queries
        await db.coin_transactions.create_index("customer_id")
        await db.coin_transactions.create_index([("customer_id", -1), ("created_at", -1)])
        await db.coin_transactions.create_index("transaction_type")
        await db.coin_transactions.create_index("related_referral_id")
        # TTL index for old transactions (2 years)
        await db.coin_transactions.create_index(
            "created_at",
            expireAfterSeconds=63072000
        )
        indexes_created.append("coin_transactions")
        logger.info("Created coin_transactions indexes")
    except Exception as e:
        logger.error(f"Failed to create coin_transactions indexes: {e}")
    
    try:
        # Reward redemptions - redemption tracking
        await db.reward_redemptions.create_index("customer_id")
        await db.reward_redemptions.create_index("status")
        await db.reward_redemptions.create_index([("customer_id", -1), ("created_at", -1)])
        await db.reward_redemptions.create_index("expires_at")
        # Index for active redemption lookup
        await db.reward_redemptions.create_index([
            ("customer_id", 1),
            ("status", 1),
            ("expires_at", 1)
        ])
        indexes_created.append("reward_redemptions")
        logger.info("Created reward_redemptions indexes")
    except Exception as e:
        logger.error(f"Failed to create reward_redemptions indexes: {e}")
    
    # Audit log collection (new for compliance)
    try:
        await db.audit_logs.create_index("user_id")
        await db.audit_logs.create_index("action")
        await db.audit_logs.create_index([("created_at", -1)])
        await db.audit_logs.create_index("entity_type")
        await db.audit_logs.create_index("entity_id")
        # Compound index for audit queries
        await db.audit_logs.create_index([
            ("entity_type", 1),
            ("entity_id", 1),
            ("created_at", -1)
        ])
        # TTL index for old audit logs (7 years for compliance)
        await db.audit_logs.create_index(
            "created_at",
            expireAfterSeconds=220752000
        )
        indexes_created.append("audit_logs")
        logger.info("Created audit_logs indexes")
    except Exception as e:
        logger.error(f"Failed to create audit_logs indexes: {e}")
    
    logger.info(f"Created indexes for collections: {', '.join(indexes_created)}")
    return indexes_created


async def ensure_indexes(app):
    """FastAPI startup event to ensure indexes exist"""
    from app.database import get_database
    
    @app.on_event("startup")
    async def startup_event():
        db = get_database()
        await create_indexes(db)


async def get_index_stats(db: AsyncIOMotorDatabase) -> dict:
    """
    Get statistics about indexes in the database.
    """
    stats = {}
    
    collections = [
        "users", "orders", "drivers", "payments", "products", 
        "stores", "deliveries", "notifications", "audit_logs"
    ]
    
    for collection_name in collections:
        try:
            collection = db[collection_name]
            indexes = await collection.list_indexes().to_list(length=100)
            stats[collection_name] = {
                "count": len(indexes),
                "indexes": [
                    {
                        "name": idx.get("name"),
                        "keys": list(idx.get("key", {}).keys()),
                        "unique": idx.get("unique", False),
                    }
                    for idx in indexes
                ]
            }
        except Exception as e:
            stats[collection_name] = {"error": str(e)}
    
    return stats


async def drop_all_indexes(db: AsyncIOMotorDatabase) -> dict:
    """
    Drop all non-_id indexes from collections.
    WARNING: This is a destructive operation. Use with caution.
    """
    results = {}
    
    collections = [
        "users", "orders", "drivers", "payments", "products", 
        "stores", "deliveries", "notifications"
    ]
    
    for collection_name in collections:
        try:
            collection = db[collection_name]
            await collection.drop_indexes()
            results[collection_name] = {"status": "success", "message": "All indexes dropped"}
        except Exception as e:
            results[collection_name] = {"status": "error", "message": str(e)}
    
    logger.warning(f"Dropped all indexes from collections: {', '.join(collections)}")
    return results
