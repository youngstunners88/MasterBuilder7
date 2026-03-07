"""
Single source of truth for delivery fee calculation.
All route files must import from here.
"""
import math
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


SAST = ZoneInfo("Africa/Johannesburg")

# Config (matches core/config.py)
BASE_FEE = 20.0       # R20 base
PER_KM_RATE = 5.0     # R5/km
MIN_FEE = 15.0        # Minimum R15
LONG_DISTANCE_KM = 15 # After 15km, higher rate
LONG_DISTANCE_RATE = 7.0  # R7/km after threshold
MAX_FEE = 200.0       # Hard cap

# Surge hours in SAST (correct timezone!)
SURGE_HOURS_SAST = [7, 8, 17, 18, 19]
SURGE_MULTIPLIER = 1.3

VEHICLE_BASE: dict[str, float] = {
    "bike": BASE_FEE,
    "car": BASE_FEE + 10.0,
    "bicycle": BASE_FEE - 5.0,
    "walking": BASE_FEE - 8.0,
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km between two lat/lng points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def is_surge_time() -> bool:
    """Check if current SAST time is a surge period."""
    now_sast = datetime.now(SAST)
    return now_sast.hour in SURGE_HOURS_SAST


def calculate_delivery_fee(
    pickup_lat: float, pickup_lng: float,
    delivery_lat: float, delivery_lng: float,
    vehicle_type: str = "bike",
) -> dict:
    """
    Calculate delivery fee. Single source of truth — import from here, not inline.
    Returns a breakdown dict for transparency.
    """
    distance_km = haversine_km(pickup_lat, pickup_lng, delivery_lat, delivery_lng)

    base = VEHICLE_BASE.get(vehicle_type, BASE_FEE)

    if distance_km <= LONG_DISTANCE_KM:
        distance_cost = distance_km * PER_KM_RATE
    else:
        distance_cost = (LONG_DISTANCE_KM * PER_KM_RATE) + \
                        ((distance_km - LONG_DISTANCE_KM) * LONG_DISTANCE_RATE)

    surge = SURGE_MULTIPLIER if is_surge_time() else 1.0
    total = max(MIN_FEE, min(MAX_FEE, (base + distance_cost) * surge))

    return {
        "base_fee": round(base, 2),
        "distance_km": round(distance_km, 2),
        "distance_cost": round(distance_cost, 2),
        "surge_multiplier": surge,
        "total": round(total, 2),
        "currency": "ZAR",
    }
