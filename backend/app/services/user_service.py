"""Simple user service for basic authentication and user management."""

import logging
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from supabase import create_client, Client
from app.models.user import UserProfile, UserProfileUpdate, UserContentStats, UserMetadata
from app.settings import settings

logger = logging.getLogger(__name__)

class UserService:
    """Service for managing user profiles using auth.users with metadata."""
    
    def __init__(self):
        self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    
    def _create_profile_from_user(self, user) -> UserProfile:
        """Create UserProfile from Supabase User object (following NestJS pattern)."""
        metadata = user.user_metadata or {}
        return UserProfile(
            id=UUID(user.id),
            email=user.email or '',
            full_name=metadata.get('full_name'),
            grade_level=metadata.get('grade_level'),
            created_at=user.created_at,
            updated_at=user.updated_at or user.created_at,
            last_sign_in_at=user.last_sign_in_at,
            email_confirmed_at=user.email_confirmed_at
        )
    
    async def get_user_profile(self, user_id: UUID) -> Optional[UserProfile]:
        """Get user profile using admin API (following NestJS pattern)."""
        try:
            # Use admin API to get user data (no database query needed)
            result = self.supabase.auth.admin.get_user_by_id(str(user_id))
            
            if result.user:
                return self._create_profile_from_user(result.user)
            return None
        except Exception as e:
            logger.error(f"Failed to get user profile for {user_id}: {e}")
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[UserProfile]:
        """Get user profile by email using admin API (following NestJS pattern)."""
        try:
            # Use admin API to get user by email
            result = self.supabase.auth.admin.list_users()
            
            for user in result:
                if user.email == email:
                    return self._create_profile_from_user(user)
            return None
        except Exception as e:
            logger.error(f"Failed to get user by email {email}: {e}")
            return None
    
    async def check_user_exists(self, user_id: UUID) -> bool:
        """Check if user exists in auth.users table."""
        try:
            result = self.supabase.auth.admin.get_user_by_id(str(user_id))
            return result.user is not None
        except Exception as e:
            logger.error(f"Failed to check user existence for {user_id}: {e}")
            return False
    
    async def get_user_count(self) -> int:
        """Get total number of users."""
        try:
            result = self.supabase.auth.admin.list_users()
            return len(result) if result else 0
        except Exception as e:
            logger.error(f"Failed to get user count: {e}")
            return 0
    
    async def update_user_profile(self, user_id: UUID, update_data: UserProfileUpdate) -> Optional[UserProfile]:
        """Update user profile metadata using Auth API (standard approach)."""
        try:
            # Use standard Auth API for user to update their own profile
            result = self.supabase.auth.update_user({
                "data": update_data.dict(exclude_none=True)
            })
            
            if result.user:
                # Return updated profile from Auth API response
                return self._create_profile_from_user(result.user)
            return None
        except Exception as e:
            logger.error(f"Failed to update user profile for {user_id}: {e}")
            return None
    
    async def get_user_content_stats(self, user_id: UUID) -> UserContentStats:
        """Get user's content generation statistics."""
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
    
    async def create_user_profile_from_auth(self, user_id: UUID, email: str, metadata: UserMetadata) -> Optional[UserProfile]:
        """Create user profile metadata during registration (following NestJS pattern)."""
        try:
            # Update user metadata using admin API
            result = self.supabase.auth.admin.update_user_by_id(
                str(user_id),
                {"user_metadata": metadata.dict(exclude_none=True)}
            )
            
            if result.user:
                return self._create_profile_from_user(result.user)
            return None
        except Exception as e:
            logger.error(f"Failed to create user profile for {user_id}: {e}")
            return None 