"""Health and status endpoints for SSAT API."""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from loguru import logger

from app.models.responses import HealthResponse, ProviderStatusResponse
from app.models.user import UserProfile
from app.auth import get_current_user
from app.services.content_generation_service import ContentGenerationService
from app.services.llm_service import LLMService
from app.services.embedding_service import get_embedding_service

router = APIRouter(tags=["health"])

# Initialize services - will be refactored later with dependency injection (singleton pattern)
content_service = None

def get_content_service():
    global content_service
    if content_service is None:
        content_service = ContentGenerationService()
    return content_service

def get_llm_service():
    """Get LLM service instance."""
    return LLMService()


@router.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint - health check."""
    return HealthResponse(
        status="healthy",
        message="SSAT Question Generator API is running",
        version="1.0.0"
    )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Simple health check endpoint - tests only critical dependencies."""
    try:
        # Test database connection (the only critical dependency)
        db_status = await get_content_service().check_database_connection()
        
        return HealthResponse(
            status="healthy" if db_status else "unhealthy",
            message="API is running" if db_status else "Database connection failed",
            version="1.0.0",
            database_connected=db_status,
            timestamp=datetime.utcnow()
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            message=f"Health check failed: {str(e)}",
            version="1.0.0",
            database_connected=False,
            timestamp=datetime.utcnow()
        )


@router.get("/providers/status", response_model=ProviderStatusResponse)
async def get_provider_status():
    """Get status of available LLM providers."""
    try:
        llm_service = get_llm_service()
        status = await llm_service.get_provider_status()
        return ProviderStatusResponse(**status)
    except Exception as e:
        logger.error(f"Failed to get provider status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get provider status: {str(e)}")


@router.get("/embedding/status")
async def get_embedding_status():
    """Get status of the embedding service."""
    try:
        embedding_service = get_embedding_service()
        model_info = embedding_service.get_model_info()
        available_models = embedding_service.get_available_models()
        
        return {
            "embedding_service": model_info,
            "backup_models": embedding_service.BACKUP_MODELS,
            "cached_models": available_models,
            "network_status": "offline" if not available_models else "online",
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Failed to get embedding status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get embedding status")


@router.get("/pool/status")
async def get_pool_status(current_user: UserProfile = Depends(get_current_user)):
    """Get pool statistics and user usage information."""
    try:
        from app.services.pool_selection_service import PoolSelectionService
        
        pool_service = PoolSelectionService()
        
        # Get overall pool statistics
        pool_stats = await pool_service.get_pool_statistics()
        
        # Get user-specific usage statistics
        user_stats = await pool_service.get_user_usage_statistics(str(current_user.id))
        
        return {
            "status": "success",
            "data": {
                "pool_statistics": pool_stats,
                "user_statistics": user_stats
            }
        }
    except Exception as e:
        logger.error(f"Error getting pool status: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@router.get("/topics/suggestions")
async def get_topic_suggestions(question_type: str):
    """Get suggested topics for a given question type."""
    try:
        suggestions = await get_content_service().get_topic_suggestions(question_type)
        return {"topics": suggestions}
    except Exception as e:
        logger.error(f"Failed to get topic suggestions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get topic suggestions: {str(e)}")