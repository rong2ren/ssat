"""Router modules for SSAT API endpoints."""

from .health import router as health_router
from .generation import router as generation_router
from .admin import router as admin_router
from .user import router as user_router

__all__ = ["health_router", "generation_router", "admin_router", "user_router"]