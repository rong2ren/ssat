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
from app.services.database import get_database_connection
from app.services.daily_limit_service import DailyLimitService
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
        
        # Check daily limits before generating content
        try:
            logger.info(f"🔍 DAILY LIMITS: Checking limits for user {current_user.id} generating {request.count} {request.question_type.value}")
            
            supabase = get_database_connection()
            limit_service = DailyLimitService(supabase)
            
            # Determine the section based on request type
            if request.question_type.value == "writing":
                request_type = "writing"
                question_type = None
            elif request.question_type.value == "reading":
                request_type = "reading"
                question_type = None
            else:
                request_type = "questions"
                question_type = request.question_type.value
            
            section = limit_service.determine_section(
                request_type=request_type,
                question_type=question_type
            )
            
            user_metadata = {
                'full_name': current_user.full_name,
                'grade_level': current_user.grade_level.value if current_user.grade_level else None,
                'role': current_user.role,
            }
            
            # Check current limits first (without incrementing)
            remaining_info = await limit_service.get_remaining_limits(str(current_user.id), user_metadata)
            section_remaining = remaining_info.get("remaining", {}).get(section, 0)
            
            # Handle unlimited limits (admin/unlimited users have -1 which means unlimited)
            if section_remaining != -1 and section_remaining < request.count:
                raise HTTPException(
                    status_code=429,
                    detail=f"Daily limit exceeded. You have {section_remaining} {section} generations remaining today, but requested {request.count}."
                )
            
            logger.info(f"🔍 DAILY LIMITS: User {current_user.id} ({current_user.role}) - {section} remaining: {section_remaining} (unlimited: {section_remaining == -1})")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error checking daily limits: {e}")
            raise HTTPException(status_code=500, detail="Failed to check daily limits")
        
        # Generate content using the consolidated service
        try:
            # Normal users should NEVER use LLM generation - only pool access
            # Admin users can use LLM generation via the admin endpoints
            force_llm_generation = False  # Always False for normal user endpoints
            logger.info(f"🔍 USER ROLE: User {current_user.id} has role '{current_user.role}', force_llm_generation={force_llm_generation} (pool-only mode)")
            
            result = await get_content_service().generate_individual_content(request, force_llm_generation=force_llm_generation, user_id=str(current_user.id))
            
            # Record usage after successful generation
            # Use check_and_increment for the total count
            for i in range(request.count):
                success, usage_info = await limit_service.check_and_increment(
                    str(current_user.id),
                    section,
                    user_metadata
                )
                if not success:
                    logger.warning(f"Failed to record usage increment {i+1}/{request.count} for user {current_user.id}, section {section}. Usage info: {usage_info}")
                    # Continue anyway since generation was successful
            
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
        # Check daily limits before starting complete test generation
        try:
            logger.info(f"🔍 DAILY LIMITS: Checking limits for user {current_user.id} starting complete test generation")
            
            supabase = get_database_connection()
            limit_service = DailyLimitService(supabase)
            
            # Calculate total questions for all sections in the complete test
            total_questions = 0
            custom_counts = request.custom_counts or {}
            
            # Import official SSAT counts
            from app.specifications import get_official_question_counts
            official_counts = get_official_question_counts()
            
            for section in request.include_sections:
                # Use custom counts if provided, otherwise use official SSAT counts
                section_count = custom_counts.get(section.value, official_counts.get(section.value, 1))
                
                if section.value in ["quantitative", "analogy", "synonym"]:
                    # These are individual questions
                    total_questions += section_count
                elif section.value == "reading":
                    # Reading passages with multiple questions per passage
                    # Estimate 5 questions per passage (typical for SSAT)
                    # Note: This is an estimate for limit checking - actual count may vary
                    total_questions += section_count * 5
                elif section.value == "writing":
                    # Writing prompts count as 1 unit
                    total_questions += 1
            
            logger.info(f"🔍 DAILY LIMITS: Complete test will generate approximately {total_questions} total questions")
            
            # Check limits for questions (most restrictive category)
            user_metadata = {
                'full_name': current_user.full_name,
                'grade_level': current_user.grade_level.value if current_user.grade_level else None,
                'role': current_user.role,
            }
            
            # Check current limits (without incrementing)
            remaining_info = await limit_service.get_remaining_limits(str(current_user.id), user_metadata)
            logger.info(f"🔍 DAILY LIMITS: Raw remaining_info: {remaining_info}")
            
            remaining_limits = remaining_info.get("remaining", {})
            logger.info(f"🔍 DAILY LIMITS: Parsed remaining_limits: {remaining_limits}")
            
            # Check if user has enough remaining for each section
            insufficient_sections = []
            for section in request.include_sections:
                # Use custom counts if provided, otherwise use official SSAT counts
                section_count = custom_counts.get(section.value, official_counts.get(section.value, 1))
                
                # Map section names to daily limit keys
                limit_key = section.value
                if section.value == "reading":
                    limit_key = "reading_passages"
                
                remaining = remaining_limits.get(limit_key, 0)
                
                # Check if this section has enough remaining (unlimited = -1)
                if remaining != -1 and remaining < section_count:
                    insufficient_sections.append(f"{section.value} (need {section_count}, have {remaining})")
            
            # If any section is insufficient, raise error
            if insufficient_sections:
                # Create user-friendly error message with structured response
                from fastapi.responses import JSONResponse
                from fastapi import status
                
                error_response = {
                    "error": "You've reached your daily limit for this content type. Please try again tomorrow or email ssat@schoolbase.org to upgrade your account.",
                    "limit_exceeded": True,
                    "limits_info": {
                        "usage": remaining_info.get("usage", {}),
                        "limits": remaining_info.get("limits", {}),
                        "remaining": remaining_info.get("remaining", {})
                    }
                }
                
                logger.debug(f"🔍 DAILY LIMITS: Returning user-friendly error: {error_response}")
                
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content=error_response
                )
            
            logger.info(f"🔍 DAILY LIMITS: User {current_user.id} ({current_user.role}) - all sections have sufficient remaining limits. Complete test requires: {total_questions}")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error checking daily limits: {e}")
            raise HTTPException(status_code=500, detail="Failed to check daily limits")
        
        # Determine LLM generation access based on user role
        # ALL users (including admins) should use pool-first approach from regular endpoints
        # LLM generation is only available in admin dashboard
        force_llm_generation = False  # All users get pool access only
        logger.info(f"🔍 USER ROLE: User {current_user.id} has role '{current_user.role}', force_llm_generation={force_llm_generation} (pool-only mode for all users)")
        
        # Use content service for complete test generation
        result = await get_content_service().generate_complete_test_async(
            request, 
            str(current_user.id), 
            force_llm_generation=force_llm_generation
        )
        
        # Record usage after successful generation (only for users with actual limits)
        try:
            # Check if user has unlimited limits (admin users)
            has_unlimited_limits = all(
                remaining_limits.get(section.value, 0) == -1 
                for section in request.include_sections
                if section.value != "reading"  # reading maps to reading_passages
            ) and remaining_limits.get("reading_passages", 0) == -1
            
            if has_unlimited_limits:
                logger.info(f"🔍 DAILY LIMITS: User {current_user.id} has unlimited limits - skipping usage tracking")
            else:
                # Record usage for each section in the complete test
                for section in request.include_sections:
                    # Use custom counts if provided, otherwise use official SSAT counts
                    section_count = custom_counts.get(section.value, official_counts.get(section.value, 1))
                    
                    # Determine the section type for limit tracking
                    if section.value in ["quantitative", "analogy", "synonym"]:
                        request_type = "questions"
                        question_type = section.value
                    elif section.value == "reading":
                        request_type = "reading"
                        question_type = None
                    elif section.value == "writing":
                        request_type = "writing"
                        question_type = None
                    else:
                        continue  # Skip unknown section types
                    
                    # Record usage for this section
                    for i in range(section_count):
                        success, usage_info = await limit_service.check_and_increment(
                            str(current_user.id),
                            limit_service.determine_section(request_type, question_type),
                            user_metadata
                        )
                        if not success:
                            logger.warning(f"Failed to record usage increment {i+1}/{section_count} for user {current_user.id}, section {section.value}. Usage info: {usage_info}")
                            # Continue anyway since generation was successful
                    
                    logger.info(f"🔍 DAILY LIMITS: Recorded usage for {section_count} {section.value} items in complete test")
                
        except Exception as e:
            logger.error(f"Failed to record usage for complete test: {e}")
            # Continue anyway since generation was successful
        
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