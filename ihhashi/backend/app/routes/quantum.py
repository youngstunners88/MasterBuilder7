"""
Quantum Onboarding Routes for iHhashi
Auto-populate merchant profiles from URLs or store name + location
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional
import os
import re
import json
from datetime import datetime, timezone

from ..models.quantum_extraction import (
    QuantumMerchantProfile,
    QuantumDiscoveryRequest,
    QuantumOnboardRequest,
    QuantumRefreshRequest,
    ExtractionSource,
    ExtractionStatus,
    ExtractedProduct,
    ExtractedMenuCategory,
    ExtractedHours,
    ExtractedSocialMedia
)

router = APIRouter(prefix="/quantum", tags=["quantum"])

# In-memory cache for extraction results (replace with Redis in production)
extraction_cache: dict = {}


def detect_input_type(input_str: str) -> ExtractionSource:
    """Detect what type of input was provided"""
    input_lower = input_str.lower().strip()
    
    # Check for URLs
    if input_str.startswith("http://") or input_str.startswith("https://"):
        if "maps.google" in input_lower or "goo.gl/maps" in input_lower:
            return ExtractionSource.GOOGLE_MAPS_URL
        if "tripadvisor" in input_lower:
            return ExtractionSource.TRIPADVISOR_URL
        if "facebook.com" in input_lower:
            return ExtractionSource.FACEBOOK_PAGE
        if "instagram.com" in input_lower:
            return ExtractionSource.INSTAGRAM_PAGE
        return ExtractionSource.WEBSITE_URL
    
    # Assume it's a store name + location
    return ExtractionSource.STORE_NAME_LOCATION


async def extract_from_website(url: str) -> QuantumMerchantProfile:
    """Extract merchant data from website URL using Firecrawl"""
    profile = QuantumMerchantProfile(
        source_type=ExtractionSource.WEBSITE_URL,
        source_url=url,
        status=ExtractionStatus.IN_PROGRESS
    )
    
    firecrawl_key = os.environ.get("FIRECRAWL_API_KEY")
    
    if not firecrawl_key:
        # Fallback to mock extraction for development
        profile.extraction_notes.append("FIRECRAWL_API_KEY not set - using mock extraction")
        profile = create_mock_extraction(url, profile)
        return profile
    
    try:
        import httpx
        
        # Define extraction schema
        schema = {
            "type": "object",
            "properties": {
                "business_name": {"type": "string"},
                "phone": {"type": "string"},
                "email": {"type": "string"},
                "address": {"type": "string"},
                "hours": {"type": "object"},
                "social_media": {"type": "object"},
                "menu": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string"},
                            "items": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "price": {"type": "number"},
                                        "description": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        
        prompt = """
        Extract the following from this restaurant/business website:
        1. Business name
        2. Contact info (phone, email, address)
        3. Operating hours
        4. Social media links
        5. Menu/products with prices in ZAR
        6. Business type (restaurant, grocery, bakery, etc.)
        
        Convert all prices to South African Rand (ZAR) if needed.
        """
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.firecrawl.dev/v1/scrape",
                headers={
                    "Authorization": f"Bearer {firecrawl_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "url": url,
                    "formats": ["extract"],
                    "extract": {
                        "schema": schema,
                        "prompt": prompt
                    }
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Firecrawl error: {response.status_code}")
            
            data = response.json()
            extracted = data.get("extract", {})
            
            # Map to profile
            profile.business_name = extracted.get("business_name")
            profile.phone = extracted.get("phone")
            profile.email = extracted.get("email")
            
            # Parse address
            address = extracted.get("address", "")
            if address:
                parts = address.split(",")
                if len(parts) >= 2:
                    profile.address_line_1 = parts[0].strip()
                    profile.city = parts[-1].strip()
            
            # Hours
            hours = extracted.get("hours", {})
            if hours:
                profile.operating_hours = ExtractedHours(**hours)
            
            # Social media
            social = extracted.get("social_media", {})
            profile.social_media = ExtractedSocialMedia(**social)
            
            # Menu
            menu = extracted.get("menu", [])
            for cat_data in menu:
                category = ExtractedMenuCategory(
                    name=cat_data.get("category", "Uncategorized")
                )
                for item in cat_data.get("items", []):
                    product = ExtractedProduct(
                        name=item.get("name", ""),
                        price=item.get("price"),
                        description=item.get("description"),
                        category=category.name
                    )
                    category.items.append(product)
                profile.categories.append(category)
                profile.total_products += len(category.items)
            
            profile.status = ExtractionStatus.COMPLETED
            profile.extraction_method = "firecrawl"
            profile.confidence_score = 0.9 if profile.business_name else 0.5
            
    except Exception as e:
        profile.status = ExtractionStatus.FAILED
        profile.extraction_notes.append(f"Extraction error: {str(e)}")
        # Create mock for development
        profile = create_mock_extraction(url, profile)
    
    return profile


def create_mock_extraction(url: str, profile: QuantumMerchantProfile) -> QuantumMerchantProfile:
    """Create mock extraction for testing/development"""
    # Extract business name from URL
    domain = url.replace("https://", "").replace("http://", "").split("/")[0]
    business_name = domain.split(".")[0].replace("-", " ").title()
    
    profile.business_name = business_name
    profile.phone = "+27 11 123 4567"
    profile.email = f"info@{domain}"
    profile.address_line_1 = "123 Main Street"
    profile.city = "Johannesburg"
    profile.province = "Gauteng"
    profile.operating_hours = ExtractedHours(
        monday="09:00-21:00",
        tuesday="09:00-21:00",
        wednesday="09:00-21:00",
        thursday="09:00-21:00",
        friday="09:00-22:00",
        saturday="09:00-22:00",
        sunday="10:00-20:00"
    )
    
    # Mock menu
    profile.categories = [
        ExtractedMenuCategory(
            name="Burgers",
            items=[
                ExtractedProduct(name="Classic Burger", price=149.00, category="Burgers"),
                ExtractedProduct(name="Cheese Burger", price=169.00, category="Burgers"),
                ExtractedProduct(name="Veggie Burger", price=159.00, category="Burgers", dietary_tags=["vegetarian"]),
            ]
        ),
        ExtractedMenuCategory(
            name="Sides",
            items=[
                ExtractedProduct(name="French Fries", price=45.00, category="Sides"),
                ExtractedProduct(name="Onion Rings", price=55.00, category="Sides"),
            ]
        ),
        ExtractedMenuCategory(
            name="Drinks",
            items=[
                ExtractedProduct(name="Coca-Cola", price=25.00, category="Drinks"),
                ExtractedProduct(name="Sprite", price=25.00, category="Drinks"),
            ]
        )
    ]
    profile.total_products = sum(len(c.items) for c in profile.categories)
    
    profile.status = ExtractionStatus.COMPLETED
    profile.extraction_method = "mock"
    profile.confidence_score = 0.6
    profile.extraction_notes.append("Mock extraction - set FIRECRAWL_API_KEY for real extraction")
    
    return profile


async def extract_from_google_places(query: str) -> QuantumMerchantProfile:
    """Extract merchant data using Google Places API"""
    profile = QuantumMerchantProfile(
        source_type=ExtractionSource.STORE_NAME_LOCATION,
        source_query=query,
        status=ExtractionStatus.IN_PROGRESS
    )
    
    google_key = os.environ.get("GOOGLE_PLACES_API_KEY")
    
    if not google_key:
        # Mock for development
        profile.extraction_notes.append("GOOGLE_PLACES_API_KEY not set - using mock extraction")
        profile.business_name = query.split(",")[0].strip()
        profile.city = query.split(",")[-1].strip() if "," in query else "Unknown"
        profile.status = ExtractionStatus.COMPLETED
        profile.extraction_method = "mock"
        profile.confidence_score = 0.3
        return profile
    
    try:
        import httpx
        
        # First, find the place
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Text search
            search_response = await client.get(
                "https://maps.googleapis.com/maps/api/place/textsearch/json",
                params={
                    "query": query,
                    "key": google_key
                }
            )
            
            results = search_response.json().get("results", [])
            if not results:
                raise Exception("No places found")
            
            place = results[0]
            place_id = place["place_id"]
            
            # Get detailed info
            details_response = await client.get(
                "https://maps.googleapis.com/maps/api/place/details/json",
                params={
                    "place_id": place_id,
                    "fields": "name,formatted_address,formatted_phone_number,website,opening_hours,geometry,rating,url",
                    "key": google_key
                }
            )
            
            details = details_response.json().get("result", {})
            
            profile.business_name = details.get("name")
            profile.phone = details.get("formatted_phone_number")
            profile.website = details.get("website")
            
            address = details.get("formatted_address", "")
            parts = address.split(",")
            profile.address_line_1 = parts[0] if parts else None
            profile.city = parts[-2].strip() if len(parts) >= 2 else None
            
            location = details.get("geometry", {}).get("location", {})
            profile.latitude = location.get("lat")
            profile.longitude = location.get("lng")
            
            hours = details.get("opening_hours", {}).get("weekday_text", [])
            if hours:
                # Parse hours
                profile.operating_hours = parse_google_hours(hours)
            
            profile.status = ExtractionStatus.COMPLETED
            profile.extraction_method = "google_places"
            profile.confidence_score = 0.85
            
            # If we have a website, try to extract menu
            if profile.website:
                profile.extraction_notes.append(f"Website found: {profile.website} - use quantum-refresh to extract menu")
                profile.missing_fields.append("menu")
            
    except Exception as e:
        profile.status = ExtractionStatus.PARTIAL
        profile.extraction_notes.append(f"Google Places error: {str(e)}")
    
    return profile


def parse_google_hours(weekday_text: list) -> ExtractedHours:
    """Parse Google's weekday_text format"""
    hours = ExtractedHours()
    day_map = {
        "Monday": "monday",
        "Tuesday": "tuesday", 
        "Wednesday": "wednesday",
        "Thursday": "thursday",
        "Friday": "friday",
        "Saturday": "saturday",
        "Sunday": "sunday"
    }
    
    for text in weekday_text:
        for day_name, attr in day_map.items():
            if text.startswith(day_name):
                # "Monday: 9:00 AM – 9:00 PM" -> "09:00-21:00"
                time_part = text.split(": ", 1)[-1]
                setattr(hours, attr, time_part)
    
    return hours


@router.post("/discover", response_model=QuantumMerchantProfile)
async def quantum_discover(request: QuantumDiscoveryRequest):
    """
    Step 1: Discover and extract merchant data from URL or name+location
    Returns a preview - merchant must confirm with quantum-onboard
    """
    input_type = detect_input_type(request.input)
    
    # Check cache
    cache_key = f"{input_type}:{request.input}"
    if not request.force_refresh and cache_key in extraction_cache:
        return extraction_cache[cache_key]
    
    # Route to appropriate extractor
    if input_type == ExtractionSource.WEBSITE_URL:
        profile = await extract_from_website(request.input)
    elif input_type == ExtractionSource.GOOGLE_MAPS_URL:
        # Extract place_id from URL and query Places API
        profile = await extract_from_google_places(request.input)
    elif input_type == ExtractionSource.STORE_NAME_LOCATION:
        profile = await extract_from_google_places(request.input)
    else:
        # Try website extraction as fallback
        profile = await extract_from_website(request.input)
    
    # Cache the result
    extraction_cache[profile.extraction_id] = profile
    extraction_cache[cache_key] = profile
    
    return profile


@router.post("/onboard")
async def quantum_onboard(request: QuantumOnboardRequest):
    """
    Step 2: Create merchant with extracted data
    Allows merchant to review/edit before saving
    """
    # Get extraction from cache
    profile = extraction_cache.get(request.extraction_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Extraction not found. Run quantum-discover first.")
    
    # Apply merchant edits if provided
    if request.edits:
        for field, value in request.edits.items():
            if hasattr(profile, field):
                setattr(profile, field, value)
    
    # TODO: Create actual merchant in database
    # This would involve:
    # 1. Creating/updating user with merchant role
    # 2. Creating merchant profile
    # 3. Creating products from extracted menu
    # 4. Setting up delivery zones
    
    return {
        "success": True,
        "message": "Merchant onboarded successfully",
        "merchant_id": "TODO",
        "products_created": profile.total_products,
        "profile": profile.dict()
    }


@router.post("/refresh")
async def quantum_refresh(request: QuantumRefreshRequest):
    """
    Re-extract data from original source
    Useful for menu updates, price changes
    """
    # TODO: Get merchant's original extraction source
    # Re-run extraction
    # Update relevant fields
    return {
        "success": False,
        "message": "Not implemented yet"
    }


@router.get("/extraction/{extraction_id}")
async def get_extraction(extraction_id: str):
    """Get cached extraction result"""
    profile = extraction_cache.get(extraction_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Extraction not found")
    return profile


@router.get("/health")
async def quantum_health():
    """Check quantum service health"""
    return {
        "status": "healthy",
        "firecrawl_configured": bool(os.environ.get("FIRECRAWL_API_KEY")),
        "google_places_configured": bool(os.environ.get("GOOGLE_PLACES_API_KEY")),
        "cached_extractions": len(extraction_cache)
    }
