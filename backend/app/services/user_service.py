"""Simple user service for basic authentication and user management."""

import logging
from typing import Optional
from uuid import UUID
from supabase import create_client, Client
from app.models.user import UserContentStats
from app.settings import settings

logger = logging.getLogger(__name__)

class UserService:
    """Service for managing user content statistics using RPC calls."""
    
    def __init__(self):
        self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    

    
    async def get_user_content_stats(self, user_id: UUID) -> UserContentStats:
        """Get user's content generation statistics using RPC."""
        try:
            result = self.supabase.rpc("get_user_content_count", {"p_user_id": str(user_id)}).execute()
            if result.data:
                stats_data = result.data[0]
                return UserContentStats(**stats_data)
            else:
                return UserContentStats(
                    quantitative_count=0,
                    analogy_count=0,
                    synonym_count=0,
                    reading_count=0,
                    writing_count=0
                )
        except Exception as e:
            logger.error(f"Failed to get user content stats for {user_id}: {e}")
            raise 