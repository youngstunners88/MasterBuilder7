from supabase import create_client, Client
from app.config import settings
from typing import Optional

_client: Optional[Client] = None
_admin_client: Optional[Client] = None

def get_supabase() -> Client:
    """Get Supabase client with anon key for user operations."""
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_anon_key)
    return _client

def get_supabase_admin() -> Client:
    """Get Supabase client with service role key for admin operations."""
    global _admin_client
    if _admin_client is None:
        _admin_client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _admin_client
