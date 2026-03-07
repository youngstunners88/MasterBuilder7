"""
iHhashi Backend Application
"""
# Import commonly used modules for convenience
from app.database import connect_db, close_db, get_collection
from app.config import settings

__version__ = "0.4.2"
__all__ = ["connect_db", "close_db", "get_collection", "settings"]
