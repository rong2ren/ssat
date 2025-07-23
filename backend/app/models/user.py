"""Simple user models for SSAT application."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field
from enum import Enum

# ========================================
# ENUMS
# ========================================

class GradeLevel(str, Enum):
    THIRD = "3rd"
    FOURTH = "4th"
    FIFTH = "5th"
    SIXTH = "6th"
    SEVENTH = "7th"
    EIGHTH = "8th"

# ========================================
# USER MODELS (Using auth.users with metadata)
# ========================================

class UserMetadata(BaseModel):
    """User metadata stored in auth.users.raw_user_meta_data"""
    full_name: Optional[str] = None
    grade_level: Optional[GradeLevel] = None

class UserProfile(BaseModel):
    """User profile from auth.users table with metadata"""
    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    grade_level: Optional[GradeLevel] = None
    created_at: datetime
    updated_at: datetime
    last_sign_in_at: Optional[datetime] = None
    email_confirmed_at: Optional[datetime] = None

class UserProfileUpdate(BaseModel):
    """Data for updating user profile"""
    full_name: Optional[str] = None
    grade_level: Optional[GradeLevel] = None

class UserLogin(BaseModel):
    """User login credentials"""
    email: EmailStr
    password: str = Field(..., min_length=6)

class ResetPasswordRequest(BaseModel):
    """Request password reset"""
    email: EmailStr



class UserRegister(BaseModel):
    """User registration data"""
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None
    grade_level: Optional[GradeLevel] = None

class UserContentStats(BaseModel):
    """User content generation statistics by section type."""
    quantitative_count: int
    analogy_count: int
    synonym_count: int
    reading_count: int
    writing_count: int

# ========================================
# RESPONSE MODELS
# ========================================

class AuthResponse(BaseModel):
    """Authentication response"""
    success: bool
    message: str
    user: Optional[UserProfile] = None
    token: Optional[str] = None



class UserStatsResponse(BaseModel):
    """User statistics response"""
    success: bool
    message: str
    stats: Optional[UserContentStats] = None 