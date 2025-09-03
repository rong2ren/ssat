"""User-related endpoints for SSAT API."""

from fastapi import APIRouter, HTTPException, Depends
from loguru import logger

from app.models.user import UserProfile
from app.auth import get_current_user
from app.services.database import get_database_connection
from app.services.daily_limit_service import DailyLimitService

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/limits")
async def get_user_limits(current_user: UserProfile = Depends(get_current_user)):
    """Get user's current daily usage limits and remaining counts."""
    try:
        # Get Supabase client
        supabase = get_database_connection()
        
        # Initialize daily limit service
        limit_service = DailyLimitService(supabase)
        
        # Use user data from the dependency (already verified)
        # Convert UserProfile to user_metadata format expected by DailyLimitService
        user_metadata = {
            'full_name': current_user.full_name,
            'grade_level': current_user.grade_level.value if current_user.grade_level else None,
            'role': current_user.role,  # Include role for proper limit calculation
        }
        
        # Get remaining limits
        limits_info = await limit_service.get_remaining_limits(
            str(current_user.id), 
            user_metadata
        )
        
        return {
            "success": True,
            "data": limits_info
        }
        
    except Exception as e:
        logger.error(f"Error getting user limits: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get user limits"
        )