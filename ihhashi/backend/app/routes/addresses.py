"""
Address API routes - Full implementation with MongoDB
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional, List
from datetime import datetime, timezone
from bson import ObjectId
from pydantic import BaseModel

from app.services.auth import get_current_user
from app.models import User
from app.database import get_collection
from app.middleware.rate_limit import limiter

router = APIRouter(prefix="/addresses", tags=["addresses"])


class AddressCreate(BaseModel):
    label: str
    address: str
    lat: float
    lng: float
    instructions: Optional[str] = None


class AddressUpdate(BaseModel):
    label: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    instructions: Optional[str] = None


@router.get("/")
@limiter.limit("60/minute")
async def list_addresses(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get all saved addresses for user"""
    buyers_col = get_collection("buyers")
    
    buyer = await buyers_col.find_one({"user_id": current_user.id})
    if not buyer:
        # Return empty list if no buyer profile yet
        return {"addresses": []}
    
    addresses = buyer.get("addresses", [])
    return {"addresses": addresses}


@router.post("/")
@limiter.limit("20/minute")
async def create_address(
    request: Request,
    address_data: AddressCreate,
    current_user: User = Depends(get_current_user)
):
    """Add a new address"""
    buyers_col = get_collection("buyers")
    
    # Ensure buyer profile exists
    buyer = await buyers_col.find_one({"user_id": current_user.id})
    if not buyer:
        # Create buyer profile
        buyer = {
            "user_id": current_user.id,
            "addresses": [],
            "created_at": datetime.now(timezone.utc)
        }
        await buyers_col.insert_one(buyer)
    
    # Create address entry
    address_entry = {
        "id": str(ObjectId()),
        "label": address_data.label,
        "address_line1": address_data.address,
        "latitude": address_data.lat,
        "longitude": address_data.lng,
        "delivery_instructions": address_data.instructions,
        "is_default": len(buyer.get("addresses", [])) == 0,  # First address is default
        "created_at": datetime.now(timezone.utc)
    }
    
    await buyers_col.update_one(
        {"user_id": current_user.id},
        {"$push": {"addresses": address_entry}}
    )
    
    return {
        "message": "Address added",
        "address": address_entry
    }


@router.get("/{address_id}")
@limiter.limit("60/minute")
async def get_address(
    request: Request,
    address_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific address"""
    buyers_col = get_collection("buyers")
    
    buyer = await buyers_col.find_one({"user_id": current_user.id})
    if not buyer:
        raise HTTPException(status_code=404, detail="No addresses found")
    
    for addr in buyer.get("addresses", []):
        if addr.get("id") == address_id:
            return {"address": addr}
    
    raise HTTPException(status_code=404, detail="Address not found")


@router.patch("/{address_id}")
@limiter.limit("20/minute")
async def update_address(
    request: Request,
    address_id: str,
    address_data: AddressUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update an address"""
    buyers_col = get_collection("buyers")
    
    buyer = await buyers_col.find_one({"user_id": current_user.id})
    if not buyer:
        raise HTTPException(status_code=404, detail="No addresses found")
    
    addresses = buyer.get("addresses", [])
    found = False
    
    for i, addr in enumerate(addresses):
        if addr.get("id") == address_id:
            found = True
            if address_data.label:
                addresses[i]["label"] = address_data.label
            if address_data.address:
                addresses[i]["address_line1"] = address_data.address
            if address_data.lat is not None:
                addresses[i]["latitude"] = address_data.lat
            if address_data.lng is not None:
                addresses[i]["longitude"] = address_data.lng
            if address_data.instructions is not None:
                addresses[i]["delivery_instructions"] = address_data.instructions
            addresses[i]["updated_at"] = datetime.now(timezone.utc)
            break
    
    if not found:
        raise HTTPException(status_code=404, detail="Address not found")
    
    await buyers_col.update_one(
        {"user_id": current_user.id},
        {"$set": {"addresses": addresses}}
    )
    
    return {"message": "Address updated", "address": addresses[i]}


@router.delete("/{address_id}")
@limiter.limit("20/minute")
async def delete_address(
    request: Request,
    address_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete an address"""
    buyers_col = get_collection("buyers")
    
    buyer = await buyers_col.find_one({"user_id": current_user.id})
    if not buyer:
        raise HTTPException(status_code=404, detail="No addresses found")
    
    addresses = buyer.get("addresses", [])
    original_len = len(addresses)
    addresses = [a for a in addresses if a.get("id") != address_id]
    
    if len(addresses) == original_len:
        raise HTTPException(status_code=404, detail="Address not found")
    
    # If we deleted the default, make first address default
    if addresses and not any(a.get("is_default") for a in addresses):
        addresses[0]["is_default"] = True
    
    await buyers_col.update_one(
        {"user_id": current_user.id},
        {"$set": {"addresses": addresses}}
    )
    
    return {"message": "Address deleted"}


@router.post("/{address_id}/default")
@limiter.limit("20/minute")
async def set_default_address(
    request: Request,
    address_id: str,
    current_user: User = Depends(get_current_user)
):
    """Set an address as default"""
    buyers_col = get_collection("buyers")
    
    buyer = await buyers_col.find_one({"user_id": current_user.id})
    if not buyer:
        raise HTTPException(status_code=404, detail="No addresses found")
    
    addresses = buyer.get("addresses", [])
    found = False
    
    for addr in addresses:
        if addr.get("id") == address_id:
            addr["is_default"] = True
            found = True
        else:
            addr["is_default"] = False
    
    if not found:
        raise HTTPException(status_code=404, detail="Address not found")
    
    await buyers_col.update_one(
        {"user_id": current_user.id},
        {"$set": {"addresses": addresses}}
    )
    
    return {"message": "Default address updated"}
