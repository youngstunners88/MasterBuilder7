"""
Database seeding script for iHhashi
Run with: python -m scripts.seed_database
"""
import asyncio
from datetime import datetime
from bson import ObjectId
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_database


async def seed_database():
    db = await get_database()
    
    print("🌱 Seeding iHhashi database...")
    
    # Clear existing data (optional - comment out to preserve)
    await db.users.delete_many({})
    await db.merchants.delete_many({})
    await db.verification_documents.delete_many({})
    await db.delivery_servicemen.delete_many({})
    
    # Create admin user
    admin_user = {
        "_id": ObjectId(),
        "phone_number": "+27821234567",
        "email": "admin@ihhashi.co.za",
        "full_name": "System Administrator",
        "user_type": "admin",
        "status": "active",
        "is_super_admin": True,
        "created_at": datetime.utcnow()
    }
    await db.users.insert_one(admin_user)
    print(f"✅ Created admin user: {admin_user['email']}")
    
    # Create sample delivery servicemen with various transport modes
    sample_servicemen = [
        {
            "_id": ObjectId(),
            "user_id": str(ObjectId()),
            "full_name": "Thabo Mokoena",
            "phone": "+27831234567",
            "transport_mode": "car",
            "vehicle_make": "Toyota",
            "vehicle_model": "Corolla",
            "vehicle_year": 2019,
            "vehicle_color": "White",
            "number_plate": "CA123456",
            "is_online": True,
            "is_available": True,
            "rating": 4.8,
            "total_deliveries": 150,
            "total_earnings": 12500.00,
            "is_verified": True,
            "blue_horse_verified": True,
            "bank_name": "FNB",
            "account_number": "****1234",
            "pricing": {
                "base_fee": 25.0,
                "per_km_rate": 5.0,
                "minimum_fee": 30.0,
                "maximum_distance_km": 15.0
            },
            "created_at": datetime.utcnow()
        },
        {
            "_id": ObjectId(),
            "user_id": str(ObjectId()),
            "full_name": "Nomsa Dlamini",
            "phone": "+27832345678",
            "transport_mode": "motorcycle",
            "vehicle_make": "Honda",
            "vehicle_model": "CG125",
            "vehicle_year": 2021,
            "vehicle_color": "Red",
            "number_plate": "GP789012",
            "is_online": True,
            "is_available": True,
            "rating": 4.9,
            "total_deliveries": 280,
            "total_earnings": 22000.00,
            "is_verified": True,
            "blue_horse_verified": True,
            "bank_name": "Capitec",
            "account_number": "****5678",
            "pricing": {
                "base_fee": 20.0,
                "per_km_rate": 4.0,
                "minimum_fee": 25.0,
                "maximum_distance_km": 10.0
            },
            "created_at": datetime.utcnow()
        },
        {
            "_id": ObjectId(),
            "user_id": str(ObjectId()),
            "full_name": "Sipho Ndlovu",
            "phone": "+27833456789",
            "transport_mode": "bicycle",
            "is_online": True,
            "is_available": True,
            "rating": 4.7,
            "total_deliveries": 95,
            "total_earnings": 6500.00,
            "is_verified": True,
            "blue_horse_verified": False,
            "bank_name": "Standard Bank",
            "account_number": "****9012",
            "pricing": {
                "base_fee": 15.0,
                "per_km_rate": 3.0,
                "minimum_fee": 20.0,
                "maximum_distance_km": 5.0
            },
            "created_at": datetime.utcnow()
        },
        {
            "_id": ObjectId(),
            "user_id": str(ObjectId()),
            "full_name": "Lerato Molefe",
            "phone": "+27834567890",
            "transport_mode": "on_foot",
            "is_online": True,
            "is_available": True,
            "rating": 4.6,
            "total_deliveries": 45,
            "total_earnings": 2800.00,
            "is_verified": True,
            "blue_horse_verified": False,
            "bank_name": "FNB",
            "account_number": "****3456",
            "pricing": {
                "base_fee": 12.0,
                "per_km_rate": 2.5,
                "minimum_fee": 15.0,
                "maximum_distance_km": 3.0
            },
            "created_at": datetime.utcnow()
        },
        {
            "_id": ObjectId(),
            "user_id": str(ObjectId()),
            "full_name": "David van der Merwe",
            "phone": "+27835678901",
            "transport_mode": "wheelchair",
            "is_online": True,
            "is_available": True,
            "rating": 4.9,
            "total_deliveries": 120,
            "total_earnings": 8500.00,
            "is_verified": True,
            "blue_horse_verified": True,
            "bank_name": "Nedbank",
            "account_number": "****7890",
            "pricing": {
                "base_fee": 12.0,
                "per_km_rate": 2.5,
                "minimum_fee": 15.0,
                "maximum_distance_km": 4.0
            },
            "created_at": datetime.utcnow()
        },
        {
            "_id": ObjectId(),
            "user_id": str(ObjectId()),
            "full_name": "Zanele Khumalo",
            "phone": "+27836789012",
            "transport_mode": "running",
            "is_online": True,
            "is_available": True,
            "rating": 4.8,
            "total_deliveries": 78,
            "total_earnings": 5200.00,
            "is_verified": True,
            "blue_horse_verified": False,
            "bank_name": "Capitec",
            "account_number": "****2345",
            "pricing": {
                "base_fee": 10.0,
                "per_km_rate": 3.0,
                "minimum_fee": 15.0,
                "maximum_distance_km": 5.0
            },
            "created_at": datetime.utcnow()
        },
        {
            "_id": ObjectId(),
            "user_id": str(ObjectId()),
            "full_name": "Marco Santos",
            "phone": "+27837890123",
            "transport_mode": "rollerblade",
            "is_online": True,
            "is_available": True,
            "rating": 4.7,
            "total_deliveries": 62,
            "total_earnings": 4100.00,
            "is_verified": True,
            "blue_horse_verified": False,
            "bank_name": "FNB",
            "account_number": "****6789",
            "pricing": {
                "base_fee": 12.0,
                "per_km_rate": 2.5,
                "minimum_fee": 18.0,
                "maximum_distance_km": 6.0
            },
            "created_at": datetime.utcnow()
        }
    ]
    await db.delivery_servicemen.insert_many(sample_servicemen)
    print(f"✅ Created {len(sample_servicemen)} sample delivery servicemen")
    
    # Create sample verification documents
    sample_docs = [
        {
            "_id": ObjectId(),
            "user_id": str(sample_servicemen[0]["user_id"]),
            "document_type": "drivers_license",
            "status": "approved",
            "file_url": "https://storage.ihhashi.co.za/docs/sample_license.pdf",
            "uploaded_at": datetime.utcnow(),
            "reviewed_by": admin_user['_id'],
            "reviewed_at": datetime.utcnow(),
            "rejection_reason": None
        },
        {
            "_id": ObjectId(),
            "user_id": str(sample_servicemen[0]["user_id"]),
            "document_type": "vehicle_registration",
            "status": "approved",
            "file_url": "https://storage.ihhashi.co.za/docs/sample_vehicle.pdf",
            "uploaded_at": datetime.utcnow(),
            "reviewed_by": admin_user['_id'],
            "reviewed_at": datetime.utcnow(),
            "rejection_reason": None
        }
    ]
    await db.verification_documents.insert_many(sample_docs)
    print(f"✅ Created {len(sample_docs)} sample documents")
    
    # Create sample merchants/vendors
    sample_merchants = [
        {
            "_id": ObjectId(),
            "business_name": "Bree Street Fish & Chips",
            "business_type": "restaurant",
            "description": "Best fish and chips in Johannesburg CBD",
            "phone_number": "+27111234567",
            "email": "info@brefish.co.za",
            "address": "45 Bree Street, Johannesburg",
            "city": "Johannesburg",
            "province": "Gauteng",
            "coordinates": {"lat": -26.2041, "lng": 28.0473},
            "status": "active",
            "is_verified": True,
            "blue_horse_verified": True,
            "commission_rate": 0.15,
            "rating": 4.5,
            "total_orders": 0,
            "opening_hours": {
                "monday": {"open": "09:00", "close": "20:00"},
                "tuesday": {"open": "09:00", "close": "20:00"},
                "wednesday": {"open": "09:00", "close": "20:00"},
                "thursday": {"open": "09:00", "close": "20:00"},
                "friday": {"open": "09:00", "close": "21:00"},
                "saturday": {"open": "10:00", "close": "21:00"},
                "sunday": {"open": "11:00", "close": "18:00"}
            },
            "created_at": datetime.utcnow()
        },
        {
            "_id": ObjectId(),
            "business_name": "Mama's Kota Spot",
            "business_type": "restaurant",
            "description": "Authentic South African kotas with all the fillings",
            "phone_number": "+27119876543",
            "email": "mamas.kota@gmail.com",
            "address": "123 Commissioner Street, Johannesburg",
            "city": "Johannesburg",
            "province": "Gauteng",
            "coordinates": {"lat": -26.2055, "lng": 28.0410},
            "status": "active",
            "is_verified": True,
            "blue_horse_verified": False,
            "commission_rate": 0.15,
            "rating": 4.7,
            "total_orders": 0,
            "opening_hours": {
                "monday": {"open": "08:00", "close": "22:00"},
                "tuesday": {"open": "08:00", "close": "22:00"},
                "wednesday": {"open": "08:00", "close": "22:00"},
                "thursday": {"open": "08:00", "close": "22:00"},
                "friday": {"open": "08:00", "close": "23:00"},
                "saturday": {"open": "09:00", "close": "23:00"},
                "sunday": {"open": "10:00", "close": "21:00"}
            },
            "created_at": datetime.utcnow()
        },
        {
            "_id": ObjectId(),
            "business_name": "Durban Bunny Chow House",
            "business_type": "restaurant",
            "description": "Traditional Durban bunny chow - quarter, half, or full loaf",
            "phone_number": "+27311234567",
            "email": "info@bunnychow.co.za",
            "address": "78 Florida Road, Durban",
            "city": "Durban",
            "province": "KwaZulu-Natal",
            "coordinates": {"lat": -29.8587, "lng": 31.0218},
            "status": "active",
            "is_verified": True,
            "blue_horse_verified": True,
            "commission_rate": 0.15,
            "rating": 4.8,
            "total_orders": 0,
            "opening_hours": {
                "monday": {"open": "10:00", "close": "21:00"},
                "tuesday": {"open": "10:00", "close": "21:00"},
                "wednesday": {"open": "10:00", "close": "21:00"},
                "thursday": {"open": "10:00", "close": "21:00"},
                "friday": {"open": "10:00", "close": "22:00"},
                "saturday": {"open": "10:00", "close": "22:00"},
                "sunday": {"open": "11:00", "close": "20:00"}
            },
            "created_at": datetime.utcnow()
        }
    ]
    await db.merchants.insert_many(sample_merchants)
    print(f"✅ Created {len(sample_merchants)} sample merchants")
    
    print("\n🎉 Database seeding complete!")
    print("\n📊 Summary:")
    print(f"   • 1 admin user")
    print(f"   • {len(sample_servicemen)} delivery servicemen (car, motorcycle, bicycle, on-foot, wheelchair, running, rollerblade)")
    print(f"   • {len(sample_docs)} verification documents")
    print(f"   • {len(sample_merchants)} merchants")


if __name__ == "__main__":
    asyncio.run(seed_database())
