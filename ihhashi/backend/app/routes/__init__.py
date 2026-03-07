from .auth import router as auth_router
from .users import router as users_router
from .merchants import router as merchants_router
from .orders import router as orders_router
from .riders import router as riders_router
from .trips import router as trips_router

__all__ = [
    "auth_router", "users_router", "merchants_router", 
    "orders_router", "riders_router", "trips_router"
]
