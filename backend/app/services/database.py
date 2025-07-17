"""Database connection service for SSAT application."""

from supabase import create_client, Client
from app.settings import settings

def get_database_connection() -> Client:
    """Get Supabase database connection."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)