"""Simple authentication endpoints for SSAT application."""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
from loguru import logger
from typing import Optional
from uuid import UUID
from datetime import datetime

from app.models.user import (
    UserLogin, UserRegister, UserProfileUpdate,
    ResetPasswordRequest,
    AuthResponse, UserStatsResponse,
    UserProfile, UserContentStats, UserMetadata
)
from app.services.user_service import UserService
from app.settings import settings

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

# Initialize Supabase client
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# Initialize user service
user_service = UserService()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserProfile:
    """Extract and validate user from JWT token (following NestJS pattern with signature verification)."""
    try:
        # Decode JWT token to get user data (following NestJS pattern)
        token = credentials.credentials
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication token"
            )
            
        # Use Supabase's built-in token verification with retry logic
        max_retries = 3
        retry_delay = 1  # seconds
        user = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🔍 DEBUG: Token verification attempt {attempt + 1}/{max_retries}")
                user_response = supabase.auth.get_user(token)
                user = user_response.user  # type: ignore[attr-defined]
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid authentication token"
                    )
                break  # Success, exit retry loop
            except Exception as e:
                logger.error(f"🔍 DEBUG: Token verification failed (attempt {attempt + 1}/{max_retries}): {e}")
                
                # If this is the last attempt, raise the exception
                if attempt == max_retries - 1:
                    logger.error(f"Supabase token verification failed after {max_retries} attempts: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid authentication token"
                    )
                
                # Wait before retrying
                import time
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
        
        # Extract user data from Supabase user object
        user_id = user.id  # type: ignore[attr-defined]
        email = user.email or ''  # type: ignore[attr-defined]
        user_metadata = user.user_metadata or {}  # type: ignore[attr-defined]
        
        # Create user profile from Supabase user data
        profile = UserProfile(
            id=UUID(user_id),
            email=str(email),
            full_name=user_metadata.get('full_name'),
            grade_level=user_metadata.get('grade_level'),
            role=user_metadata.get('role', 'free'),  # Add role with default 'free'
            created_at=datetime.utcnow(),  # Use current time as fallback
            updated_at=datetime.utcnow(),
            last_sign_in_at=datetime.utcnow(),
            email_confirmed_at=datetime.utcnow() if user.email_confirmed_at else None  # type: ignore[attr-defined]
        )
        
        # Log successful JWT validation
        logger.info(f"✅ JWT validation successful for user {user_id} ({email})")
        
        return profile
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

@router.post("/register", response_model=AuthResponse)
async def register_user(user_data: UserRegister):
    """Register a new user with metadata."""
    try:
        # Prepare metadata for registration
        metadata = UserMetadata(
            full_name=user_data.full_name,
            grade_level=user_data.grade_level
        )
        
        # Register user with Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password,
            "options": {
                "data": metadata.dict(exclude_none=True)  # Store in user_metadata
            }
        })
        
        if auth_response.user:
            # Check if email confirmation is required
            if auth_response.session is None:
                # Email confirmation required
                return AuthResponse(
                    success=True,
                    message="Registration successful! Please check your email to confirm your account before logging in.",
                    user=None,
                    token=None
                )
            else:
                # Email already confirmed or confirmation disabled
                # Create profile from session data (no database query)
                profile = UserProfile(
                    id=UUID(auth_response.user.id),
                    email=auth_response.user.email if auth_response.user.email else '',
                    full_name=metadata.full_name,
                    grade_level=metadata.grade_level,
                    created_at=datetime.utcnow(),  # Use current time for new user
                    updated_at=datetime.utcnow(),
                    last_sign_in_at=None,
                    email_confirmed_at=datetime.utcnow() if auth_response.user.email_confirmed_at else None
                )
                return AuthResponse(
                    success=True,
                    message="User registered successfully",
                    user=profile,
                    token=auth_response.session.access_token
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user account"
            )
            
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        error_msg = str(e)
        
        if "User already registered" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration failed. Please try again."
            )

@router.post("/login", response_model=AuthResponse)
async def login_user(credentials: UserLogin):
    """Login user and return profile with token."""
    try:
        # Authenticate with Supabase
        auth_response = supabase.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password
        })
        
        if auth_response.user:
            # Check if email is confirmed
            if not auth_response.user.email_confirmed_at:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Please confirm your email address before logging in. Check your inbox for a confirmation email."
                )
            
            # Create profile from session data (no database query)
            user_metadata = auth_response.user.user_metadata or {}
            profile = UserProfile(
                id=UUID(auth_response.user.id),
                email=auth_response.user.email if auth_response.user.email else '',
                full_name=user_metadata.get('full_name'),
                grade_level=user_metadata.get('grade_level'),
                created_at=datetime.utcnow(),  # Use current time
                updated_at=datetime.utcnow(),
                last_sign_in_at=datetime.utcnow(),
                email_confirmed_at=datetime.utcnow() if auth_response.user.email_confirmed_at else None
            )
            
            return AuthResponse(
                success=True,
                message="Login successful",
                user=profile,
                token=auth_response.session.access_token if auth_response.session else None
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
            
    except Exception as e:
        logger.error(f"Login failed: {e}")
        error_msg = str(e)
        
        if "Invalid login credentials" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Login failed. Please try again."
            )

@router.post("/logout")
async def logout_user(current_user: UserProfile = Depends(get_current_user)):
    """Logout user."""
    try:
        supabase.auth.sign_out()
        return {"success": True, "message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )





@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(current_user: UserProfile = Depends(get_current_user)):
    """Get current user's content generation statistics."""
    try:
        stats = await user_service.get_user_content_stats(current_user.id)
        return UserStatsResponse(
            success=True,
            message="Statistics retrieved successfully",
            stats=stats
        )
    except Exception as e:
        logger.error(f"Failed to get user stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )

@router.post("/resend-confirmation")
async def resend_confirmation_email(email: str):
    """Resend email confirmation."""
    try:
        result = supabase.auth.resend({
            "type": "signup",
            "email": email
        })
        
        return {
            "success": True,
            "message": "Confirmation email sent. Please check your inbox."
        }
    except Exception as e:
        logger.error(f"Failed to resend confirmation email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend confirmation email"
        )

@router.post("/forgot-password")
async def forgot_password(request: ResetPasswordRequest):
    """Request password reset email."""
    try:
        result = supabase.auth.reset_password_for_email(
            request.email,
            {
                "redirect_to": f"{settings.SUPABASE_URL}/auth/reset-password"
            }
        )
        
        return {
            "success": True,
            "message": "Password reset email sent. Please check your inbox."
        }
    except Exception as e:
        logger.error(f"Failed to send password reset email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send password reset email"
        )




# ========================================
# HEALTH CHECK ENDPOINT
# ========================================

@router.get("/health")
async def auth_health_check():
    """Simple health check for authentication service."""
    try:
        # Test database connectivity (the only critical dependency for auth)
        result = supabase.table("ai_generation_sessions").select("id").limit(1).execute()
        
        return {
            "status": "healthy",
            "message": "Authentication service is running",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Auth health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": f"Authentication service error: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        } 