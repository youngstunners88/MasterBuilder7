"""
MongoDB Migrations for iHhashi

This module provides a simple migration system for MongoDB.
Unlike SQL databases, MongoDB is schemaless, but we still need to:
1. Manage indexes
2. Set up schema validation rules
3. Perform data migrations for structure changes

Usage:
    python -m scripts.migrations.migrate --up        # Apply all pending migrations
    python -m scripts.migrations.migrate --down      # Rollback last migration
    python -m scripts.migrations.migrate --status    # Show migration status
    python -m scripts.migrations.migrate --create    # Create a new migration
"""

import asyncio
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, TEXT


class Migration:
    """Base migration class"""
    
    name: str = "base_migration"
    description: str = "Base migration class"
    
    async def up(self, db):
        """Apply migration"""
        raise NotImplementedError
    
    async def down(self, db):
        """Rollback migration"""
        raise NotImplementedError


class Migration001InitialIndexes(Migration):
    """Create initial indexes for optimal query performance"""
    
    name = "001_initial_indexes"
    description = "Create geospatial, text, and compound indexes"
    
    async def up(self, db):
        """Create all initial indexes"""
        
        # Users collection
        users = db.users
        await users.create_index([("email", ASCENDING)], unique=True, name="idx_email_unique")
        await users.create_index([("phone", ASCENDING)], unique=True, sparse=True, name="idx_phone_unique")
        await users.create_index([("location", "2dsphere")], name="idx_location_geo")
        await users.create_index([("role", ASCENDING), ("is_active", ASCENDING)], name="idx_role_active")
        await users.create_index([("created_at", DESCENDING)], name="idx_created_at")
        await users.create_index([("verification.level", ASCENDING)], name="idx_verification_level")
        
        # Merchants collection
        merchants = db.merchants
        await merchants.create_index([("name", TEXT), ("description", TEXT)], name="idx_merchant_search")
        await merchants.create_index([("location", "2dsphere")], name="idx_merchant_geo")
        await merchants.create_index([("is_active", ASCENDING)], name="idx_merchant_active")
        await merchants.create_index([("category", ASCENDING), ("is_active", ASCENDING)], name="idx_category_active")
        await merchants.create_index([("owner_id", ASCENDING)], name="idx_owner")
        await merchants.create_index([("verification.level", ASCENDING)], name="idx_verification_level")
        
        # Orders collection
        orders = db.orders
        await orders.create_index([("buyer_id", ASCENDING), ("status", ASCENDING)], name="idx_buyer_status")
        await orders.create_index([("driver_id", ASCENDING), ("status", ASCENDING)], name="idx_driver_status")
        await orders.create_index([("merchant_id", ASCENDING)], name="idx_merchant_orders")
        await orders.create_index([("created_at", DESCENDING)], name="idx_created_at")
        await orders.create_index([("status", ASCENDING), ("created_at", DESCENDING)], name="idx_status_date")
        
        # Products collection
        products = db.products
        await products.create_index([("merchant_id", ASCENDING), ("is_available", ASCENDING)], name="idx_merchant_products")
        await products.create_index([("category", ASCENDING)], name="idx_category")
        await products.create_index([("name", TEXT), ("description", TEXT)], name="idx_product_search")
        
        # Trips collection
        trips = db.trips
        await trips.create_index([("driver_id", ASCENDING), ("status", ASCENDING)], name="idx_driver_trips")
        await trips.create_index([("location", "2dsphere")], name="idx_trip_location")
        await trips.create_index([("order_id", ASCENDING)], name="idx_order")
        await trips.create_index([("created_at", DESCENDING)], name="idx_created_at")
        
        # Delivery servicemen (riders) collection
        riders = db.delivery_servicemen
        await riders.create_index([("user_id", ASCENDING)], unique=True, name="idx_user_unique")
        await riders.create_index([("location", "2dsphere")], name="idx_location_geo")
        await riders.create_index([("is_available", ASCENDING), ("status", ASCENDING)], name="idx_available_status")
        await riders.create_index([("vehicle_type", ASCENDING)], name="idx_vehicle_type")
        
        # Refunds collection
        refunds = db.refunds
        await refunds.create_index([("order_id", ASCENDING)], name="idx_order")
        await refunds.create_index([("user_id", ASCENDING)], name="idx_user")
        await refunds.create_index([("status", ASCENDING)], name="idx_status")
        await refunds.create_index([("created_at", DESCENDING)], name="idx_created_at")
        
        # Migrations tracking collection
        migrations = db._migrations
        await migrations.create_index([("name", ASCENDING)], unique=True, name="idx_name_unique")
        
        print(f"✅ Migration '{self.name}' applied successfully")
    
    async def down(self, db):
        """Remove all indexes (except _id)"""
        collections = ['users', 'merchants', 'orders', 'products', 'trips', 
                       'delivery_servicemen', 'refunds', '_migrations']
        
        for collection_name in collections:
            collection = db[collection_name]
            indexes = await collection.index_information()
            for index_name in indexes:
                if index_name != '_id_':
                    await collection.drop_index(index_name)
        
        print(f"✅ Migration '{self.name}' rolled back")


class Migration002SchemaValidation(Migration):
    """Set up schema validation rules for data integrity"""
    
    name = "002_schema_validation"
    description = "Create JSON schema validation rules"
    
    async def up(self, db):
        """Apply schema validation rules"""
        
        # Users schema validation
        await db.command({
            'collMod': 'users',
            'validator': {
                '$jsonSchema': {
                    'bsonType': 'object',
                    'required': ['email', 'role', 'created_at'],
                    'properties': {
                        'email': {'bsonType': 'string', 'pattern': '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'},
                        'phone': {'bsonType': 'string', 'pattern': '^\\+27[0-9]{9}$'},
                        'role': {'enum': ['buyer', 'merchant', 'driver', 'admin']},
                        'is_active': {'bsonType': 'bool'},
                        'location': {
                            'bsonType': 'object',
                            'required': ['type', 'coordinates'],
                            'properties': {
                                'type': {'enum': ['Point']},
                                'coordinates': {'bsonType': 'array', 'items': {'bsonType': 'double'}}
                            }
                        }
                    }
                }
            },
            'validationLevel': 'moderate',
            'validationAction': 'warn'
        })
        
        # Orders schema validation
        await db.command({
            'collMod': 'orders',
            'validator': {
                '$jsonSchema': {
                    'bsonType': 'object',
                    'required': ['buyer_id', 'merchant_id', 'items', 'status', 'total_amount', 'created_at'],
                    'properties': {
                        'status': {'enum': ['pending', 'confirmed', 'preparing', 'ready', 'picked_up', 'in_transit', 'delivered', 'cancelled']},
                        'total_amount': {'bsonType': 'number', 'minimum': 0},
                        'items': {
                            'bsonType': 'array',
                            'items': {
                                'bsonType': 'object',
                                'required': ['product_id', 'quantity', 'price'],
                                'properties': {
                                    'quantity': {'bsonType': 'int', 'minimum': 1},
                                    'price': {'bsonType': 'number', 'minimum': 0}
                                }
                            }
                        }
                    }
                }
            },
            'validationLevel': 'moderate',
            'validationAction': 'warn'
        })
        
        print(f"✅ Migration '{self.name}' applied successfully")
    
    async def down(self, db):
        """Remove schema validation rules"""
        for collection in ['users', 'orders']:
            await db.command({
                'collMod': collection,
                'validator': {},
                'validationLevel': 'off'
            })
        
        print(f"✅ Migration '{self.name}' rolled back")


# Registry of all migrations in order
MIGRATIONS: List[Migration] = [
    Migration001InitialIndexes(),
    Migration002SchemaValidation(),
]


class MigrationRunner:
    """Manages migration execution"""
    
    def __init__(self, mongodb_url: str, db_name: str = "ihhashi"):
        self.mongodb_url = mongodb_url
        self.db_name = db_name
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
    
    async def connect(self):
        """Connect to MongoDB"""
        self.client = AsyncIOMotorClient(self.mongodb_url)
        self.db = self.client[self.db_name]
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
    
    async def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration names"""
        migrations_col = self.db._migrations
        applied = await migrations_col.find({}, {'name': 1}).to_list(None)
        return [m['name'] for m in applied]
    
    async def record_migration(self, migration: Migration):
        """Record a migration as applied"""
        await self.db._migrations.insert_one({
            'name': migration.name,
            'description': migration.description,
            'applied_at': datetime.utcnow()
        })
    
    async def remove_migration_record(self, migration: Migration):
        """Remove migration record"""
        await self.db._migrations.delete_one({'name': migration.name})
    
    async def migrate_up(self):
        """Apply all pending migrations"""
        applied = await self.get_applied_migrations()
        
        for migration in MIGRATIONS:
            if migration.name not in applied:
                print(f"⏳ Applying migration: {migration.name}")
                await migration.up(self.db)
                await self.record_migration(migration)
        
        print("✅ All migrations applied")
    
    async def migrate_down(self):
        """Rollback the last migration"""
        applied = await self.get_applied_migrations()
        
        if not applied:
            print("ℹ️  No migrations to rollback")
            return
        
        last_name = applied[-1]
        for migration in reversed(MIGRATIONS):
            if migration.name == last_name:
                print(f"⏳ Rolling back migration: {migration.name}")
                await migration.down(self.db)
                await self.remove_migration_record(migration)
                break
        
        print("✅ Migration rolled back")
    
    async def status(self):
        """Show migration status"""
        applied = await self.get_applied_migrations()
        
        print("\n📋 Migration Status:")
        print("-" * 60)
        
        for migration in MIGRATIONS:
            status = "✅ Applied" if migration.name in applied else "⏳ Pending"
            print(f"  {migration.name}: {status}")
            print(f"    {migration.description}")
        
        print("-" * 60)
        print(f"Total: {len(MIGRATIONS)} migrations, {len(applied)} applied\n")


async def main():
    parser = argparse.ArgumentParser(description='MongoDB Migrations for iHhashi')
    parser.add_argument('--up', action='store_true', help='Apply pending migrations')
    parser.add_argument('--down', action='store_true', help='Rollback last migration')
    parser.add_argument('--status', action='store_true', help='Show migration status')
    parser.add_argument('--create', type=str, help='Create a new migration with the given name')
    parser.add_argument('--mongodb-url', type=str, default=os.getenv('MONGODB_URL', 'mongodb://localhost:27017'))
    parser.add_argument('--db-name', type=str, default=os.getenv('DB_NAME', 'ihhashi'))
    
    args = parser.parse_args()
    
    runner = MigrationRunner(args.mongodb_url, args.db_name)
    
    try:
        await runner.connect()
        
        if args.up:
            await runner.migrate_up()
        elif args.down:
            await runner.migrate_down()
        elif args.status:
            await runner.status()
        elif args.create:
            await create_new_migration(args.create)
        else:
            parser.print_help()
    finally:
        await runner.disconnect()


async def create_new_migration(name: str):
    """Create a new migration file"""
    migrations_dir = Path(__file__).parent
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    migration_name = f"{timestamp}_{name.replace(' ', '_').lower()}"
    filename = migrations_dir / f"{migration_name}.py"
    
    content = f'''"""
{name.replace('_', ' ').title()}

Revision ID: {migration_name}
Create Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
from typing import Sequence, Union
from scripts.migrations.migrate import Migration


class Migration{migration_name.replace("_", "").title()}(Migration):
    """TODO: Add description"""
    
    name = "{migration_name}"
    description = "TODO: Add description"
    
    async def up(self, db):
        """Apply migration"""
        # TODO: Implement migration
        pass
    
    async def down(self, db):
        """Rollback migration"""
        # TODO: Implement rollback
        pass
'''
    
    filename.write_text(content)
    print(f"✅ Created migration: {filename}")


if __name__ == '__main__':
    asyncio.run(main())
