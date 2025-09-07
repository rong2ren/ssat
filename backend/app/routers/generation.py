"""Generation endpoints for SSAT API."""

from typing import Union
from fastapi import APIRouter, HTTPException, Depends
from loguru import logger

from app.models.user import UserProfile
from app.models.requests import QuestionGenerationRequest, CompleteTestRequest
from app.models.responses import (
    QuestionGenerationResponse, 
    ReadingGenerationResponse, 
    WritingGenerationResponse,
)
from app.auth import get_current_user
from app.services.content_generation_service import ContentGenerationService
from app.services.job_manager import job_manager

router = APIRouter(prefix="/generate", tags=["generation"])

# Initialize consolidated service (singleton pattern)
content_service = None

def get_content_service():
    global content_service
    if content_service is None:
        content_service = ContentGenerationService()
    return content_service


@router.post("")
async def generate_content(
    request: QuestionGenerationRequest, 
    current_user: UserProfile = Depends(get_current_user)
) -> Union[QuestionGenerationResponse, ReadingGenerationResponse, WritingGenerationResponse]:
    """Generate SSAT content based on request parameters. Returns type-specific response."""
    
    try:
        logger.info(f"Generating {request.count} {request.question_type.value} content")
        
        # Generate content using the consolidated service
        try:
            # Normal users should NEVER use LLM generation - only pool access
            # Admin users can use LLM generation via the admin endpoints
            force_llm_generation = False  # Always False for normal user endpoints
            logger.info(f"🔍 USER ROLE: User {current_user.id} has role '{current_user.role}', force_llm_generation={force_llm_generation} (pool-only mode)")
            
            # Create user metadata for daily limit service
            user_metadata = {
                'full_name': current_user.full_name,
                'grade_level': current_user.grade_level.value if current_user.grade_level else None,
                'role': current_user.role,
            }
            
            result = await get_content_service().generate_individual_content(
                request, 
                force_llm_generation=force_llm_generation, 
                user_id=str(current_user.id),
                user_metadata=user_metadata
            )
            
            # 🔧 FIX: Usage tracking is now handled in the content generation service
            # No need to track usage here since it's done atomically with pool content retrieval
            logger.info(f"🔍 DAILY LIMITS: Usage tracking handled in content generation service")
            
            return result
            
        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Content generation failed: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_content: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/complete-test/start")
async def start_complete_test_generation(
    request: CompleteTestRequest,
    current_user: UserProfile = Depends(get_current_user)
):
    """Start generating a complete SSAT practice test asynchronously."""
    try:
        # Determine LLM generation access based on user role
        # ALL users (including admins) should use pool-first approach from regular endpoints
        # LLM generation is only available in admin dashboard
        force_llm_generation = False  # All users get pool access only
        logger.info(f"🔍 USER ROLE: User {current_user.id} has role '{current_user.role}', force_llm_generation={force_llm_generation} (pool-only mode for all users)")
        
        # Create user metadata for daily limit service
        user_metadata = {
            'full_name': current_user.full_name,
            'grade_level': current_user.grade_level.value if current_user.grade_level else None,
            'role': current_user.role,
        }
        
        # Use content service for complete test generation
        result = await get_content_service().generate_complete_test_async(
            request, 
            str(current_user.id), 
            force_llm_generation=force_llm_generation,
            user_metadata=user_metadata
        )
        
        # 🔧 FIX: Usage tracking is now handled in the content generation service
        # No need to track usage here since it's done atomically with pool content retrieval
        logger.info(f"🔍 DAILY LIMITS: Usage tracking handled in content generation service")
        
        return result
    except Exception as e:
        logger.error(f"Failed to start complete test generation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start test generation: {str(e)}")


@router.get("/complete-test/{job_id}/status")
async def get_complete_test_status(job_id: str, current_user: UserProfile = Depends(get_current_user)):
    """Get the status of a complete test generation job."""
    try:
        logger.info(f"🔍 DEBUG: Router get_complete_test_status called with job_id={job_id}, user_id={current_user.id}")
        
        status = await get_content_service().get_job_status(job_id, str(current_user.id))
        
        logger.info(f"🔍 DEBUG: Router received status from content service")
        return status
    except ValueError as e:
        if "access denied" in str(e).lower():
            logger.warning(f"User {current_user.id} attempted to access job {job_id} without authorization")
            raise HTTPException(status_code=403, detail="Access denied to this job")
        else:
            logger.error(f"Job not found: {e}")
            raise HTTPException(status_code=404, detail="Job not found")
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")


@router.get("/debug/job/{job_id}")
async def debug_job(job_id: str, current_user: UserProfile = Depends(get_current_user)):
    """Debug endpoint to check if a job exists in the job manager."""
    try:
        logger.info(f"🔍 DEBUG: Debug job endpoint called for job_id={job_id}")
        
        # Check if job exists
        job = job_manager.get_job(job_id)
        if not job:
            return {"exists": False, "message": "Job not found"}
        
        return {
            "exists": True,
            "job_id": job.job_id,
            "user_id": job.user_id,
            "requesting_user_id": str(current_user.id),
            "user_match": job.user_id == str(current_user.id),
            "status": job.status.value
        }
    except Exception as e:
        logger.error(f"Debug job failed: {e}")
        return {"error": str(e)}


@router.get("/debug/jobs")
async def debug_jobs():
    """Debug endpoint to list all jobs in the job manager."""
    try:
        logger.info(f"🔍 DEBUG: Debug jobs endpoint called")
        
        jobs = []
        for job_id, job in job_manager.jobs.items():
            jobs.append({
                "job_id": job_id,
                "user_id": job.user_id,
                "status": job.status.value,
                "created_at": job.created_at.isoformat()
            })
        
        return {"jobs": jobs, "count": len(jobs)}
    except Exception as e:
        logger.error(f"Debug jobs failed: {e}")
        return {"error": str(e)}


@router.get("/debug/test")
async def debug_test():
    """Simple test endpoint to check if the router is working."""
    try:
        logger.info(f"🔍 DEBUG: Debug test endpoint called")
        
        # Create a test job
        test_job_id = job_manager.create_job({"test": True}, "test-user")
        
        # Get the job back
        test_job = job_manager.get_job(test_job_id)
        
        # Clean up
        if test_job_id in job_manager.jobs:
            del job_manager.jobs[test_job_id]
        
        return {
            "success": True,
            "test_job_id": test_job_id,
            "job_found": test_job is not None,
            "job_user_id": test_job.user_id if test_job else None
        }
    except Exception as e:
        logger.error(f"Debug test failed: {e}")
        return {"error": str(e)}


@router.get("/debug/status-test/{job_id}")
async def debug_status_test(job_id: str):
    """Debug endpoint to test status check without authentication."""
    try:
        logger.info(f"🔍 DEBUG: Debug status test endpoint called for job_id={job_id}")
        
        # Try to get job status without authentication
        status = job_manager.get_job_status(job_id, "test-user")
        
        return {
            "success": True,
            "job_id": job_id,
            "status_found": status is not None,
            "status": status
        }
    except Exception as e:
        logger.error(f"Debug status test failed: {e}")
        return {"error": str(e)}


# Specifications endpoint moved to separate router or main app level
# @router.get("/specifications/official-format")
# async def get_official_format_specification():
#     """Get the official SSAT elementary format specification."""
#     return OFFICIAL_ELEMENTARY_SPECS