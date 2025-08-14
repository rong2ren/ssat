"""FastAPI application for SSAT question generation."""

# FastAPI imports

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import time
import asyncio
import uuid
from datetime import datetime
from loguru import logger
from app.settings import settings

from app.models.requests import (
    QuestionGenerationRequest, 
    CompleteTestRequest,
    TrainingExamplesRequest
)
from app.models.responses import (
    QuestionGenerationResponse,
    ReadingGenerationResponse,
    WritingGenerationResponse,
    ProviderStatusResponse,
    HealthResponse,
    GenerationMetadata
)
from app.services.question_service import QuestionService
from app.services.unified_content_service import UnifiedContentService
from app.services.llm_service import LLMService
from app.services.ai_content_service import AIContentService
from app.models import QuestionType
from app.auth import router as auth_router, get_current_user, security
from app.models.user import UserProfile
from app.services.daily_limit_service import DailyLimitService
from app.services.database import get_database_connection
from app.services.embedding_service import get_embedding_service
from supabase import create_client
from app.services.training_examples_service import TrainingExamplesService
from app.services.job_manager import SectionStatus
from typing import Dict

# Initialize Supabase client
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# Initialize services
question_service = QuestionService()  # Keep for complete test generation
content_service = UnifiedContentService()  # New unified service for individual content
llm_service = LLMService()
ai_content_service = AIContentService()  # Service for saving AI-generated content

# Initialize embedding service
embedding_service = get_embedding_service()

# Initialize training examples service
training_examples_service = TrainingExamplesService(supabase, embedding_service)

class RoleUpdateRequest(BaseModel):
    role: str

# Loguru is configured automatically

# Create FastAPI app
app = FastAPI(
    title="SSAT Question Generator API",
    description="Generate high-quality SSAT elementary level questions and complete practice tests",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include auth router
app.include_router(auth_router)

@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint - health check."""
    return HealthResponse(
        status="healthy",
        message="SSAT Question Generator API is running",
        version="1.0.0"
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Simple health check endpoint - tests only critical dependencies."""
    try:
        # Test database connection (the only critical dependency)
        db_status = await question_service.check_database_connection()
        
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

@app.get("/providers/status", response_model=ProviderStatusResponse)
async def get_provider_status():
    """Get status of available LLM providers."""
    try:
        status = await llm_service.get_provider_status()
        return ProviderStatusResponse(**status)
    except Exception as e:
        logger.error(f"Failed to get provider status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get provider status: {str(e)}")

@app.get("/embedding/status")
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

@app.get("/pool/status")
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

@app.post("/generate")
async def generate_content(request: QuestionGenerationRequest, current_user: UserProfile = Depends(get_current_user)):
    """Generate SSAT content based on request parameters. Returns type-specific response."""
    import time
    start_time = time.time()
    
    try:
        logger.info(f"Generating {request.count} {request.question_type.value} content")
        
        # Check daily limits before generating content (CHECK PHASE ONLY)
        try:
            logger.info(f"🔍 DAILY LIMITS: Checking limits for user {current_user.id} generating {request.count} {request.question_type.value}")
            
            # Get Supabase client
            supabase = get_database_connection()
            
            # Initialize daily limit service
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
            
            logger.info(f"🔍 DAILY LIMITS: Determined section '{section}' for question type '{request.question_type.value}'")
            
            # Get user metadata from current_user (which includes role from authentication)
            user_metadata = {
                'full_name': current_user.full_name,
                'grade_level': current_user.grade_level.value if current_user.grade_level else None,
                'role': current_user.role,  # Use actual role from authentication
            }
            
            # Get usage and limits data for checking (NO INCREMENT YET)
            usage = await limit_service.get_current_usage(str(current_user.id))
            limits = await limit_service.get_user_limits(str(current_user.id), user_metadata)
            
            if not usage or not limits:
                logger.warning(f"🔍 DAILY LIMITS: Could not get usage or limits for user {current_user.id}")
                # Continue with generation even if limit check fails
            
            # Check if adding this count would exceed the limit
            current_usage = usage.get(f"{section}_generated", 0) if usage else 0
            limit_value = limits.get(section, 0) if limits else 0
            
            logger.info(f"🔍 DAILY LIMITS: User {current_user.id} has {current_usage}/{limit_value} for {section}, needs {request.count}")
            
            # If unlimited (-1), skip check
            if limit_value == -1:
                logger.debug(f"🔍 DAILY LIMITS: User {current_user.id} has unlimited access for {section}")
            else:
                # Check if adding this count would exceed the limit
                if limit_value and limit_value > 0 and (current_usage + request.count) > limit_value:
                    logger.warning(f"🔍 DAILY LIMITS: ❌ User {current_user.id} would exceed limit for {section}: {current_usage} + {request.count} > {limit_value}")
                    
                    # Create user-friendly error message
                    section_names = {
                        "quantitative": "quantiative questions",
                        "analogy": "analogy questions", 
                        "synonym": "synonym questions",
                        "reading_passages": "reading passages",
                        "writing": "writing prompts"
                    }
                    
                    section_display_name = section_names.get(section, section)
                    error_message = f"You've reached your daily limit for {section_display_name}. Please try again tomorrow or email ssat@schoolbase.org to upgrade your account."
                    
                    return JSONResponse(
                        status_code=400,  # Bad Request (more user-friendly than 429)
                        content={
                            "error": error_message,
                            "limits_info": {
                                "usage": usage,
                                "limits": limits,
                                "remaining": limit_service._calculate_remaining(usage, limits)
                            },
                            "limit_exceeded": True
                        }
                    )
            
            logger.info(f"🔍 DAILY LIMITS: ✅ Daily limit check passed for user {current_user.id}, section {section}")
            
        except Exception as e:
            logger.error(f"🔍 DAILY LIMITS: ❌ Error checking daily limits: {e}")
            # Continue with generation even if limit check fails
        
        # Try to get questions from existing AI-generated content pool first
        from app.services.pool_selection_service import PoolSelectionService
        from app.services.pool_response_converter import PoolResponseConverter
        
        pool_service = PoolSelectionService()
        pool_converter = PoolResponseConverter()
        
        # Determine section mapping for pool lookup
        section_mapping = {
            "quantitative": "Quantitative",
            "analogy": "Verbal",    # Analogies are part of Verbal section in database
            "synonym": "Verbal"    # Synonyms are part of Verbal section in database
        }
        
        # Determine subsection mapping for filtering
        subsection_mapping = {
            "analogy": "Analogies",
            "synonym": "Synonyms"
        }
        
        pool_result = None
        
        if request.question_type.value in ["quantitative", "analogy", "synonym"]:
            # For regular questions
            section_name = section_mapping.get(request.question_type.value, "Verbal")
            subsection_name = subsection_mapping.get(request.question_type.value)
            difficulty = request.difficulty.value if request.difficulty else None
            
            logger.debug(f"🔍 POOL DEBUG: Attempting pool retrieval for {request.question_type.value} questions")
            logger.debug(f"🔍 POOL DEBUG: Section={section_name}, Subsection={subsection_name}, Difficulty={difficulty}, Count={request.count}")
            
            pool_questions = await pool_service.get_unused_questions_for_user(
                user_id=str(current_user.id),
                section=section_name,
                subsection=subsection_name,  # Add subsection filtering
                count=request.count,
                difficulty=difficulty
            )
            
            logger.info(f"🔍 POOL DEBUG: Retrieved {len(pool_questions)} questions from pool, need {request.count}")
            
            if len(pool_questions) >= request.count:
                logger.info(f"🔍 POOL: ✅ Found {len(pool_questions)} unused questions in pool for user {current_user.id}")
                logger.debug(f"🔍 POOL DEBUG: Question IDs: {[q['id'][:8] + '...' for q in pool_questions[:request.count]]}")
                
                # Convert pool questions to API response format
                pool_result = pool_converter.convert_questions_to_response(pool_questions[:request.count], request)
                
                # Mark questions as used with specific content type
                question_ids = [q['id'] for q in pool_questions[:request.count]]
                try:
                    await pool_service.mark_content_as_used(
                        user_id=str(current_user.id),
                        question_ids=question_ids,
                        usage_type="custom_section",
                        content_type=request.question_type.value  # Pass specific content type
                    )
                    
                    logger.info(f"🔍 POOL: ✅ Successfully delivered {request.count} questions from pool")
                    logger.info(f"🔍 POOL DEBUG: Marked questions as used: {[qid[:8] + '...' for qid in question_ids]}")
                except Exception as mark_error:
                    # If marking fails, return service unavailable error
                    if "duplicate key value violates unique constraint" in str(mark_error):
                        logger.warning(f"🔍 POOL: ⚠️ Pool questions already used, returning service unavailable error")
                        raise HTTPException(
                            status_code=503,
                            detail="Service temporarily unavailable. Please try again in a few minutes."
                        )
                    else:
                        # Re-raise other errors
                        raise mark_error
            elif len(pool_questions) > 0:
                # Pool has some questions but not enough - return service unavailable error
                logger.info(f"🔍 POOL: ⚠️ Pool partially available - found {len(pool_questions)} questions, need {request.count}")
                logger.info(f"🔍 POOL: ❌ Returning service unavailable error instead of combining with LLM generation")
                raise HTTPException(
                    status_code=503,
                    detail="Service temporarily unavailable. Please try again in a few minutes."
                )
            else:
                logger.info(f"🔍 POOL: ❌ Pool exhausted - no questions available, need {request.count}")
        
        elif request.question_type.value == "reading":
            # For reading content - request.count now represents passages
            logger.info(f"🔍 POOL DEBUG: Attempting pool retrieval for reading passages")
            logger.info(f"🔍 POOL DEBUG: Passages requested={request.count}")
            
            pool_passages = await pool_service.get_unused_reading_content_for_user(
                user_id=str(current_user.id),
                count=request.count  # This is now passages, not questions
            )
            
            logger.info(f"🔍 POOL DEBUG: Retrieved {len(pool_passages)} reading passages from pool, need {request.count}")
            
            if len(pool_passages) >= request.count:
                logger.info(f"🔍 POOL: ✅ Found {len(pool_passages)} unused reading passages in pool for user {current_user.id}")
                logger.info(f"🔍 POOL DEBUG: Passage IDs: {[p['passage_id'][:8] + '...' for p in pool_passages[:request.count]]}")
                
                # Convert pool passages to API response format
                pool_result = pool_converter.convert_reading_to_response(pool_passages[:request.count], request)
                
                # Mark passages as used
                passage_ids = [p['passage_id'] for p in pool_passages[:request.count]]
                await pool_service.mark_content_as_used(
                    user_id=str(current_user.id),
                    passage_ids=passage_ids,
                    usage_type="custom_section"
                )
                
                logger.info(f"🔍 POOL: ✅ Successfully delivered {request.count} reading passages from pool")
                logger.info(f"🔍 POOL DEBUG: Marked passages as used: {[pid[:8] + '...' for pid in passage_ids]}")
            elif len(pool_passages) > 0:
                # Pool has some passages but not enough - return service unavailable error
                logger.info(f"🔍 POOL: ⚠️ Pool partially available - found {len(pool_passages)} passages, need {request.count}")
                logger.info(f"🔍 POOL: ❌ Returning service unavailable error instead of combining with LLM generation")
                raise HTTPException(
                    status_code=503,
                    detail="Service temporarily unavailable. Please try again in a few minutes."
                )
            else:
                logger.info(f"🔍 POOL: ❌ Pool exhausted - no reading passages available, need {request.count}")
        
        elif request.question_type.value == "writing":
            # For writing prompts
            logger.info(f"🔍 POOL DEBUG: Attempting pool retrieval for writing prompts")
            logger.info(f"🔍 POOL DEBUG: Count={request.count}")
            
            pool_prompts = await pool_service.get_unused_writing_prompts_for_user(
                user_id=str(current_user.id),
                count=request.count
            )
            
            logger.info(f"🔍 POOL DEBUG: Retrieved {len(pool_prompts)} writing prompts from pool, need {request.count}")
            
            if len(pool_prompts) >= request.count:
                logger.info(f"🔍 POOL: ✅ Found {len(pool_prompts)} unused writing prompts in pool for user {current_user.id}")
                logger.info(f"🔍 POOL DEBUG: Prompt IDs: {[p['id'][:8] + '...' for p in pool_prompts[:request.count]]}")
                
                # Convert pool prompts to API response format
                pool_result = pool_converter.convert_writing_to_response(pool_prompts[:request.count], request)
                
                # Mark prompts as used
                prompt_ids = [p['id'] for p in pool_prompts[:request.count]]
                await pool_service.mark_content_as_used(
                    user_id=str(current_user.id),
                    writing_prompt_ids=prompt_ids,
                    usage_type="custom_section"
                )
                
                logger.info(f"🔍 POOL: ✅ Successfully delivered {request.count} writing prompts from pool")
                logger.info(f"🔍 POOL DEBUG: Marked prompts as used: {[pid[:8] + '...' for pid in prompt_ids]}")
            elif len(pool_prompts) > 0:
                # Pool has some prompts but not enough - return service unavailable error
                logger.info(f"🔍 POOL: ⚠️ Pool partially available - found {len(pool_prompts)} prompts, need {request.count}")
                logger.info(f"🔍 POOL: ❌ Returning service unavailable error instead of combining with LLM generation")
                raise HTTPException(
                    status_code=503,
                    detail="Service temporarily unavailable. Please try again in a few minutes."
                )
            else:
                logger.info(f"🔍 POOL: ❌ Pool exhausted - no writing prompts available, need {request.count}")
        
        # If pool result is available, return it; otherwise fallback to on-demand generation
        if pool_result:
            logger.info(f"🔍 POOL: 🎉 Returning pool result - instant delivery!")
            
            # INCREMENT PHASE: Increment usage after successful pool delivery
            try:
                # Determine the count to increment based on section type and actual result
                increment_count = 0
                if section == "quantitative" or section == "analogy" or section == "synonym":
                    increment_count = request.count
                elif section == "reading_passages":
                    increment_count = request.count
                elif section == "writing":
                    increment_count = request.count
                
                logger.info(f"🔍 DAILY LIMITS: Incrementing usage for user {current_user.id}, section '{section}' by {increment_count}")
                
                response = supabase.rpc(
                    'increment_user_daily_usage',
                    {
                        'p_user_id': str(current_user.id),
                        'p_section': section,
                        'p_amount': increment_count
                    }
                ).execute()
                
                logger.info(f"🔍 DAILY LIMITS: Increment response: {response.data}")
                
            except Exception as e:
                logger.error(f"🔍 DAILY LIMITS: ❌ Error incrementing usage: {e}")
                # Don't fail the request if increment fails
            
            return pool_result
        
        # Pool exhausted - return user-friendly error instead of LLM fallback
        logger.info(f"🔍 POOL: ❌ Pool exhausted for user {current_user.id}, returning service unavailable error")
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again in a few minutes."
        )
        
    except Exception as e:
        logger.error(f"Content generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Content generation failed: {str(e)}")

# Progressive Test Generation Endpoints (Smart Polling)

@app.post("/generate/complete-test/start")
async def start_progressive_test_generation(request: CompleteTestRequest, current_user: UserProfile = Depends(get_current_user)):
    """Start progressive test generation and return job ID for polling."""
    try:
        from app.services.job_manager import job_manager
        
        logger.info(f"Starting progressive test generation - difficulty: {request.difficulty}")
        logger.debug(f"🔍 DEBUG: Request include_sections: {[s.value for s in request.include_sections]}")
        logger.debug(f"🔍 DEBUG: Request custom_counts: {request.custom_counts}")
        logger.debug(f"🔍 DEBUG: Request is_official_format: {request.is_official_format}")
        
        # Check daily limits for complete test generation
        try:
            logger.info(f"🔍 DAILY LIMITS: Checking limits for user {current_user.id} generating complete test with sections: {[s.value for s in request.include_sections]}")
            
            # Get Supabase client
            supabase = get_database_connection()
            
            # Initialize daily limit service
            limit_service = DailyLimitService(supabase)
            
            # For complete tests, we need to check multiple sections
            # We'll check the most restrictive section first
            sections_to_check = []
            
            for section in request.include_sections:
                if section.value == "reading":
                    sections_to_check.append(("reading_passages", 1))  # 1 passage = 1 unit
                elif section.value == "writing":
                    sections_to_check.append(("writing", 1))  # 1 prompt = 1 unit
                elif section.value == "math":
                    # Math questions are counted individually
                    math_count = (request.custom_counts or {}).get("math", 25)  # Default 25 questions
                    sections_to_check.append(("quantitative", math_count))
                elif section.value == "verbal":
                    # Verbal questions are counted individually
                    verbal_count = (request.custom_counts or {}).get("verbal", 30)  # Default 30 questions
                    # Split between analogy and synonyms (rough estimate)
                    analogy_count = verbal_count // 2
                    synonym_count = verbal_count - analogy_count
                    sections_to_check.append(("analogy", analogy_count))
                    sections_to_check.append(("synonym", synonym_count))
            
            logger.debug(f"🔍 DAILY LIMITS: Complete test will check sections: {sections_to_check}")
            
            # Get user metadata from current_user (which includes role from authentication)
            user_metadata = {
                'full_name': current_user.full_name,
                'grade_level': current_user.grade_level.value if current_user.grade_level else None,
                'role': current_user.role,  # Use actual role from authentication
            }
            
            # Get usage and limits data once (optimization)
            usage = await limit_service.get_current_usage(str(current_user.id))
            limits = await limit_service.get_user_limits(str(current_user.id), user_metadata)
            
            if not usage or not limits:
                logger.warning(f"🔍 DAILY LIMITS: Could not get usage or limits for user {current_user.id}")
                # Continue with generation even if limit check fails
            
            # Check each section using the same data
            for section_name, count in sections_to_check:
                logger.debug(f"🔍 DAILY LIMITS: Checking section {section_name} with count {count}")
                
                current_usage = usage.get(f"{section_name}_generated", 0) if usage else 0
                limit_value = limits.get(section_name, 0) if limits else 0
                
                logger.debug(f"🔍 DAILY LIMITS: User {current_user.id} has {current_usage}/{limit_value} for {section_name}, needs {count}")
                
                # If unlimited (-1), skip check
                if limit_value == -1:
                    logger.debug(f"🔍 DAILY LIMITS: User {current_user.id} has unlimited access for {section_name}")
                    continue
                
                # Check if adding this count would exceed the limit
                if limit_value and limit_value > 0 and (current_usage + count) > limit_value:
                    logger.warning(f"🔍 DAILY LIMITS: ❌ User {current_user.id} would exceed limit for {section_name}: {current_usage} + {count} > {limit_value}")
                    
                    # Create user-friendly error message
                    section_names = {
                        "quantitative": "math questions",
                        "analogy": "analogy questions", 
                        "synonym": "synonym questions",
                        "reading_passages": "reading passages",
                        "writing": "writing prompts"
                    }
                    
                    section_display_name = section_names.get(section_name, section_name)
                    error_message = f"You've reached your daily limit for {section_display_name}. Please try again tomorrow or email ssat@schoolbase.org to upgrade your account."
                    
                    return JSONResponse(
                        status_code=400,  # Bad Request (more user-friendly than 429)
                        content={
                            "error": error_message,
                            "limits_info": {
                                "usage": usage,
                                "limits": limits,
                                "remaining": limit_service._calculate_remaining(usage, limits)
                            },
                            "limit_exceeded": True
                        }
                    )
            
            logger.info(f"🔍 DAILY LIMITS: ✅ Daily limit check passed for user {current_user.id} complete test generation")
            
        except Exception as e:
            logger.error(f"🔍 DAILY LIMITS: ❌ Error checking daily limits for complete test: {e}")
            # Continue with generation even if limit check fails
        
        # Create job with request data and user ID
        job_id = job_manager.create_job({
            "difficulty": request.difficulty.value,
            "include_sections": [section.value for section in request.include_sections],
            "custom_counts": request.custom_counts,
            "provider": request.provider.value if request.provider else None
        }, str(current_user.id))
        
        # Create AI generation session for tracking
        await ai_content_service.create_generation_session(job_id, {
            "difficulty": request.difficulty.value,
            "include_sections": [section.value for section in request.include_sections],
            "custom_counts": request.custom_counts,
            "provider": request.provider.value if request.provider else None
        }, current_user.id)
        
        # Start background generation
        asyncio.create_task(generate_test_sections_background(job_id, request))
        
        return {
            "job_id": job_id,
            "status": "started",
            "message": "Test generation started. Use the job_id to poll for progress."
        }
        
    except Exception as e:
        logger.error(f"Failed to start progressive test generation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start test generation: {str(e)}")

@app.get("/generate/complete-test/{job_id}/status")
async def get_test_generation_status(job_id: str):
    """Get the current status of a progressive test generation job."""
    try:
        from app.services.job_manager import job_manager
        
        job = job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get completed sections in the proper format
        completed_sections = job_manager.get_completed_sections(job_id)
        
        return {
            "job_id": job_id,
            "status": job.status,
            "progress": {
                "completed": job.completed_sections,
                "total": job.total_sections,
                "percentage": int((job.completed_sections / max(job.total_sections, 1)) * 100)
            },
            "sections": completed_sections,
            "section_details": {k: v.to_dict() for k, v in job.sections.items()},
            "error": job.error,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")


async def generate_test_sections_background(job_id: str, request: CompleteTestRequest):
    """Background task to generate test sections in parallel."""
    from app.services.job_manager import job_manager, JobStatus
    
    start_time = time.time()
    providers_used = set()
    total_questions = 0
    
    try:
        job_manager.update_job_status(job_id, JobStatus.RUNNING)
        
        # Create tasks for all sections to run in parallel
        section_tasks = []
        for section_type in request.include_sections:
            task = asyncio.create_task(
                generate_single_section_background(job_id, section_type, request)
            )
            section_tasks.append(task)
        
        # Wait for all sections to complete (or fail)
        results = await asyncio.gather(*section_tasks, return_exceptions=True)
        
        # Log any exceptions that occurred during section generation
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                section_type = request.include_sections[i].value
                logger.error(f"❌ Section {section_type} failed with exception: {result}")
        
        # Check final job status and update AI session
        job = job_manager.get_job(job_id)
        if job and job.completed_sections > 0:  # Allow partial success - at least one section completed
            # Let job manager determine the final status (already done in complete_section/fail_section)
            # Just log the current status
            if job.status == JobStatus.COMPLETED:
                logger.info(f"✅ Complete test job {job_id}: All {job.completed_sections}/{job.total_sections} sections completed")
            elif job.status == JobStatus.PARTIAL:
                logger.info(f"⚠️ Complete test job {job_id}: Partial success - {job.completed_sections}/{job.total_sections} sections completed")
            else:
                logger.info(f"❌ Complete test job {job_id}: Failed - {job.completed_sections}/{job.total_sections} sections completed")
            
            # Count total questions and providers used (only from completed sections)
            for section_progress in job.sections.values():
                if section_progress.section_data and section_progress.status == SectionStatus.COMPLETED:
                    section_data = section_progress.section_data
                    section_type = section_data.get('section_type', '')
                    
                    # Count questions based on section type
                    section_questions = 0
                    if section_type in ['quantitative', 'analogy', 'synonym']:
                        # Question-based sections
                        if 'questions' in section_data:
                            section_questions = len(section_data['questions'])
                            total_questions += section_questions
                    elif section_type == 'reading':
                        # Reading sections have passages with questions
                        if 'passages' in section_data:
                            for passage in section_data['passages']:
                                if 'questions' in passage:
                                    section_questions += len(passage['questions'])
                            total_questions += section_questions
                    elif section_type == 'writing':
                        # Writing sections count as 1 (not as questions)
                        section_questions = 1
                        total_questions += section_questions
                    
                    logger.info(f"📊 DEBUG: Section {section_type}: {section_questions} questions")
                    
                    # Track provider used with structured information
                    if 'metadata' in section_data and 'provider_used' in section_data['metadata']:
                        provider = section_data['metadata']['provider_used']
                        # Only add real provider names
                        if provider:
                            # Just add the provider name (no mode info)
                            providers_used.add(provider)
            
            # Update AI session with final statistics
            generation_time_ms = int((time.time() - start_time) * 1000)
            # Convert set to list for database storage
            providers_list = list(providers_used)
            
            # Use appropriate status based on job status
            session_status = "completed" if job.status == JobStatus.COMPLETED else "partial"
            await ai_content_service.update_session_status(
                job_id, 
                session_status, 
                total_questions, 
                providers_list, 
                generation_time_ms
            )
            
            logger.info(f"📊 DEBUG: Session {job_id} {session_status} with {total_questions} total questions")
            logger.info(f"📊 DEBUG: Providers used: {list(providers_used)}")
            logger.info(f"Complete test job {job_id}: {job.completed_sections}/{job.total_sections} sections {session_status}, {total_questions} questions, {generation_time_ms}ms")
            
            # After all sections are completed, batch increment daily limits for the user (only successful sections)
            if job and job.user_id:
                # Aggregate counts for each section (only completed sections)
                quantitative = 0
                analogy = 0
                synonym = 0
                reading_passages = 0
                writing = 0
                for section_progress in job.sections.values():
                    if section_progress.section_data and section_progress.status == SectionStatus.COMPLETED:
                        section_data = section_progress.section_data
                        section_type = section_data.get('section_type', '')
                        if section_type == 'quantitative':
                            if 'questions' in section_data:
                                quantitative += len(section_data['questions'])
                        elif section_type == 'analogy':
                            if 'questions' in section_data:
                                analogy += len(section_data['questions'])
                        elif section_type == 'synonym':
                            if 'questions' in section_data:
                                synonym += len(section_data['questions'])
                        elif section_type == 'reading':
                            if 'passages' in section_data:
                                reading_passages += len(section_data['passages'])
                        elif section_type == 'writing':
                            # Count writing prompts from section data
                            if 'prompt' in section_data:
                                # WritingSection has a single 'prompt' field
                                writing += 1
                            elif 'prompts' in section_data:
                                writing += len(section_data['prompts'])
                            elif 'writing_prompts' in section_data:
                                writing += len(section_data['writing_prompts'])
                            else:
                                # Fallback: if no specific prompts array, count as 1
                                writing += 1
                try:
                    supabase = get_database_connection()
                    logger.info(f"🔍 DAILY LIMITS: Batch increment for user {job.user_id}: quantitative={quantitative}, analogy={analogy}, synonym={synonym}, reading_passages={reading_passages}, writing={writing}")
                    response = supabase.rpc(
                        'increment_user_daily_limits',
                        {
                            'p_user_id': job.user_id,
                            'p_quantitative': quantitative,
                            'p_analogy': analogy,
                            'p_synonym': synonym,
                            'p_reading_passages': reading_passages,
                            'p_writing': writing
                        }
                    ).execute()
                    logger.info(f"🔍 DAILY LIMITS: Batch increment response: {response.data}")
                except Exception as e:
                    logger.error(f"🔍 DAILY LIMITS: ❌ Error in batch increment: {e}")
        else:
            # No sections completed - mark as failed
            job_manager.update_job_status(job_id, JobStatus.FAILED, "No sections could be completed")
            await ai_content_service.update_session_status(job_id, "failed")
            logger.error(f"❌ Complete test job {job_id}: No sections completed - marking as failed")
        
    except Exception as e:
        logger.error(f"Background generation failed for job {job_id}: {e}")
        job_manager.update_job_status(job_id, JobStatus.FAILED, str(e))
        await ai_content_service.update_session_status(job_id, "failed")

async def generate_single_section_background(job_id: str, section_type, request: CompleteTestRequest):
    """Generate a single section in the background."""
    from app.services.job_manager import job_manager
    
    try:
        job_manager.start_section(job_id, section_type.value)
        logger.info(f"Starting generation for section {section_type.value} in job {job_id}")
        
        # Note: Daily limits are now incremented in batch after all sections are completed
        # to avoid multiple database calls and ensure consistency
        
        # Update progress: section started (25% of section progress)
        job_manager.update_section_progress(job_id, section_type.value, 25, "Preparing generation...")
        
        # Get custom count for this section
        custom_counts = request.custom_counts or {}
        logger.debug(f"🔍 DEBUG: Section {section_type.value}, custom_counts: {custom_counts}")
        section_count = custom_counts.get(section_type.value, {
            "quantitative": 1, "analogy": 1, "synonym": 1, "reading": 1, "writing": 1
        }.get(section_type.value, 5))
        logger.debug(f"🔍 DEBUG: Final section_count for {section_type.value}: {section_count}")
        
        # Update progress: about to start generation (50% of section progress)
        job_manager.update_section_progress(job_id, section_type.value, 50, f"Generating {section_count} questions...")
        
        # Try to get questions from existing AI-generated content pool first
        from app.services.pool_selection_service import PoolSelectionService
        from app.services.pool_response_converter import PoolResponseConverter
        
        pool_service = PoolSelectionService()
        pool_converter = PoolResponseConverter()
        
        # Get job to access user_id
        job = job_manager.get_job(job_id)
        if not job or not job.user_id:
            logger.error(f"Job {job_id} not found or has no user_id")
            return
        
        # Determine section mapping for pool lookup
        section_mapping = {
            "quantitative": "Quantitative",
            "analogy": "Verbal",    # Analogies are part of Verbal section in database
            "synonym": "Verbal"    # Synonyms are part of Verbal section in database
        }
        
        # Determine subsection mapping for filtering
        subsection_mapping = {
            "analogy": "Analogies",
            "synonym": "Synonyms"
        }
        
        pool_result = None
        
        if section_type.value in ["quantitative", "analogy", "synonym"]:
            # For regular questions
            section_name = section_mapping.get(section_type.value, "Verbal")
            subsection_name = subsection_mapping.get(section_type.value)
            difficulty = request.difficulty.value if request.difficulty else None
            
            logger.info(f"🔍 POOL DEBUG: Attempting pool retrieval for {section_type.value} questions")
            logger.info(f"🔍 POOL DEBUG: Section={section_name}, Subsection={subsection_name}, Difficulty={difficulty}, Count={section_count}")
            
            # Special handling for quantitative complete tests with 30 questions
            if (section_type.value == "quantitative" and 
                section_count == 30 and 
                request.is_official_format):
                logger.info(f"🎯 COMPLETE TEST: Using subsection-aware pool selection for 30 quantitative questions")
                pool_questions = await pool_service.get_quantitative_questions_with_subsection_breakdown(
                    user_id=job.user_id,
                    total_count=section_count,
                    difficulty=difficulty
                )
            else:
                # Regular pool selection for all other cases
                pool_questions = await pool_service.get_unused_questions_for_user(
                    user_id=job.user_id,  # Use job.user_id since we don't have current_user here
                    section=section_name,
                    subsection=subsection_name,
                    count=section_count,
                    difficulty=difficulty
                )
            
            logger.info(f"🔍 POOL DEBUG: Retrieved {len(pool_questions)} questions from pool, need {section_count}")
            
            if len(pool_questions) >= section_count:
                logger.info(f"🔍 POOL: ✅ Found {len(pool_questions)} unused questions in pool for user {job.user_id}")
                logger.info(f"🔍 POOL DEBUG: Question IDs: {[q['id'][:8] + '...' for q in pool_questions[:section_count]]}")
                
                # Convert pool questions to API response format
                pool_result = pool_converter.convert_questions_to_section(pool_questions[:section_count], section_type.value)
                
                # Mark questions as used with specific content type
                question_ids = [q['id'] for q in pool_questions[:section_count]]
                try:
                    await pool_service.mark_content_as_used(
                        user_id=job.user_id,
                        question_ids=question_ids,
                        usage_type="complete_test",
                        content_type=section_type.value
                    )
                    
                    logger.info(f"🔍 POOL: ✅ Marked {len(question_ids)} questions as used")
                except Exception as mark_error:
                    # If marking fails, fail this section only
                    if "duplicate key value violates unique constraint" in str(mark_error):
                        logger.warning(f"🔍 POOL: ⚠️ Pool questions already used, failing section {section_type.value}")
                        job_manager.update_section_progress(job_id, section_type.value, 100, "Service temporarily unavailable")
                        job_manager.fail_section(job_id, section_type.value, "Service temporarily unavailable. Please try again in a few minutes.")
                        return
                    else:
                        # Re-raise other errors
                        raise mark_error
            elif len(pool_questions) > 0:
                # Pool has some questions but not enough - fail this section only
                logger.info(f"🔍 POOL: ⚠️ Pool partially available - found {len(pool_questions)} questions, need {section_count}")
                logger.info(f"🔍 POOL: ❌ Failing section {section_type.value} instead of combining with LLM generation")
                job_manager.update_section_progress(job_id, section_type.value, 100, "Service temporarily unavailable")
                job_manager.fail_section(job_id, section_type.value, "Service temporarily unavailable. Please try again in a few minutes.")
                return
            else:
                logger.info(f"🔍 POOL: ❌ No questions available in pool for {section_type.value}, will generate {section_count} on-demand")
        
        elif section_type.value == "reading":
            # For reading sections
            logger.info(f"🔍 POOL DEBUG: Attempting pool retrieval for reading content")
            logger.info(f"🔍 POOL DEBUG: Passages requested={section_count}")
            
            pool_content = await pool_service.get_unused_reading_content_for_user(
                user_id=job.user_id,
                count=section_count  # This is now passages, not questions
            )
            
            logger.info(f"🔍 POOL DEBUG: Retrieved {len(pool_content)} reading passages from pool, need {section_count}")
            
            if len(pool_content) >= section_count:
                logger.info(f"🔍 POOL: ✅ Found {len(pool_content)} unused reading passages in pool for user {job.user_id}")
                
                # Convert pool content to API response format
                pool_result = pool_converter.convert_reading_to_section(pool_content[:section_count])
                
                # Mark passages as used
                passage_ids = [item['passage_id'] for item in pool_content[:section_count]]
                try:
                    await pool_service.mark_content_as_used(
                        user_id=job.user_id,
                        passage_ids=passage_ids,
                        usage_type="complete_test"
                    )
                    
                    logger.info(f"🔍 POOL: ✅ Marked {len(passage_ids)} reading passages as used")
                except Exception as mark_error:
                    # If marking fails, fail this section only
                    if "duplicate key value violates unique constraint" in str(mark_error):
                        logger.warning(f"🔍 POOL: ⚠️ Pool passages already used, failing section {section_type.value}")
                        job_manager.update_section_progress(job_id, section_type.value, 100, "Service temporarily unavailable")
                        job_manager.fail_section(job_id, section_type.value, "Service temporarily unavailable. Please try again in a few minutes.")
                        return
                    else:
                        # Re-raise other errors
                        raise mark_error
                
                logger.info(f"🔍 POOL: ✅ Successfully delivered {section_count} reading passages from pool")
            elif len(pool_content) > 0:
                # Pool has some passages but not enough - fail this section only
                logger.info(f"🔍 POOL: ⚠️ Pool partially available - found {len(pool_content)} passages, need {section_count}")
                logger.info(f"🔍 POOL: ❌ Failing section {section_type.value} instead of combining with LLM generation")
                job_manager.update_section_progress(job_id, section_type.value, 100, "Service temporarily unavailable")
                job_manager.fail_section(job_id, section_type.value, "Service temporarily unavailable. Please try again in a few minutes.")
                return
            else:
                logger.info(f"🔍 POOL: ❌ No reading content available in pool, will generate {section_count} on-demand")
        
        elif section_type.value == "writing":
            # For writing sections
            logger.info(f"🔍 POOL DEBUG: Attempting pool retrieval for writing prompts")
            
            pool_prompts = await pool_service.get_unused_writing_prompts_for_user(
                user_id=job.user_id,
                count=section_count
            )
            
            logger.info(f"🔍 POOL DEBUG: Retrieved {len(pool_prompts)} writing prompts from pool, need {section_count}")
            
            if len(pool_prompts) >= section_count:
                logger.info(f"🔍 POOL: ✅ Found {len(pool_prompts)} unused writing prompts in pool for user {job.user_id}")
                
                # Convert pool content to API response format
                pool_result = pool_converter.convert_writing_to_section(pool_prompts[:section_count])
                
                # Mark prompts as used
                prompt_ids = [item['id'] for item in pool_prompts[:section_count]]
                try:
                    await pool_service.mark_content_as_used(
                        user_id=job.user_id,
                        writing_prompt_ids=prompt_ids,
                        usage_type="complete_test"
                    )
                    
                    logger.info(f"🔍 POOL: ✅ Marked {len(prompt_ids)} writing prompts as used")
                except Exception as mark_error:
                    # If marking fails, fail this section only
                    if "duplicate key value violates unique constraint" in str(mark_error):
                        logger.warning(f"🔍 POOL: ⚠️ Pool prompts already used, failing section {section_type.value}")
                        job_manager.update_section_progress(job_id, section_type.value, 100, "Service temporarily unavailable")
                        job_manager.fail_section(job_id, section_type.value, "Service temporarily unavailable. Please try again in a few minutes.")
                        return
                    else:
                        # Re-raise other errors
                        raise mark_error
                
                logger.info(f"🔍 POOL: ✅ Successfully delivered {section_count} writing prompts from pool")
            elif len(pool_prompts) > 0:
                # Pool has some prompts but not enough - fail this section only
                logger.info(f"🔍 POOL: ⚠️ Pool partially available - found {len(pool_prompts)} prompts, need {section_count}")
                logger.info(f"🔍 POOL: ❌ Failing section {section_type.value} instead of combining with LLM generation")
                job_manager.update_section_progress(job_id, section_type.value, 100, "Service temporarily unavailable")
                job_manager.fail_section(job_id, section_type.value, "Service temporarily unavailable. Please try again in a few minutes.")
                return
            else:
                logger.info(f"🔍 POOL: ❌ No writing prompts available in pool, will generate {section_count} on-demand")
        
        # If we have pool results, use them; otherwise return service unavailable error
        if pool_result:
            logger.info(f"🔍 POOL: ✅ Using pool results for {section_type.value}")
            section = pool_result
            # Note: Usage will be incremented in batch after all sections complete
        else:
            # Pool exhausted - fail this section only
            logger.info(f"🔍 POOL: ❌ Pool exhausted for complete test section {section_type.value}, failing section only")
            job_manager.update_section_progress(job_id, section_type.value, 100, "Service temporarily unavailable")
            job_manager.fail_section(job_id, section_type.value, "Service temporarily unavailable. Please try again in a few minutes.")
            return
        
        # Update progress: generation complete, processing results (90%)
        job_manager.update_section_progress(job_id, section_type.value, 90, "Processing results...")
        
        # Convert section to dict for storage
        if hasattr(section, 'model_dump'):
            section_data = section.model_dump()
        else:
            section_data = section.__dict__
        
        # Add provider_used metadata to section data
        provider_used = None
        
        # Extract provider from section_data based on section type
        if section_type.value in ['quantitative', 'analogy', 'synonym']:
            # For question-based sections
            if 'questions' in section_data and section_data['questions']:
                for question in section_data['questions']:
                    if isinstance(question, dict) and 'metadata' in question:
                        provider_used = question['metadata'].get('provider_used')
                        break
        elif section_type.value == 'reading':
            # For reading sections
            if 'passages' in section_data and section_data['passages']:
                for passage in section_data['passages']:
                    if isinstance(passage, dict) and 'questions' in passage:
                        for question in passage['questions']:
                            if isinstance(question, dict) and 'metadata' in question:
                                provider_used = question['metadata'].get('provider_used')
                                break
                        if provider_used:
                            break
        elif section_type.value == 'writing':
            # For writing sections
            if 'prompt' in section_data and section_data['prompt']:
                if isinstance(section_data['prompt'], dict) and 'metadata' in section_data['prompt']:
                    provider_used = section_data['prompt']['metadata'].get('provider_used')
        
        # Add metadata to section_data
        if 'metadata' not in section_data:
            section_data['metadata'] = {}
        if provider_used:
            section_data['metadata']['provider_used'] = provider_used
            logger.debug(f"📊 DEBUG: Added provider_used={provider_used} to section {section_type.value}")
        else:
            # Fallback to request provider if available
            fallback_provider = request.provider.value if request.provider else None
            if fallback_provider:
                section_data['metadata']['provider_used'] = fallback_provider
                logger.debug(f"📊 DEBUG: Using fallback provider_used={fallback_provider} for section {section_type.value}")
            else:
                # No provider available, don't set provider_used
                logger.debug(f"📊 DEBUG: No provider available for section {section_type.value}")
        
        # Ensure section_type is set in section_data for proper tracking
        section_data['section_type'] = section_type.value
        
        # Save AI-generated content to database
        try:
            # Log section completion
            logger.info(f"📝 Completed section {section_type.value}")
            
            saved_ids = await ai_content_service.save_test_section(job_id, section)
            logger.info(f"Saved AI content for section {section_type.value}: {saved_ids}")
        except Exception as e:
            logger.error(f"Failed to save AI content for section {section_type.value}: {e}")
            # Continue with job completion even if saving fails
        
        job_manager.complete_section(job_id, section_type.value, section_data)
        logger.info(f"Completed section {section_type.value} for job {job_id}")
        
    except Exception as e:
        logger.error(f"Failed to generate section {section_type.value} for job {job_id}: {e}")
        job_manager.fail_section(job_id, section_type.value, str(e))

@app.get("/topics/suggestions")
async def get_topic_suggestions(question_type: str):
    """Get suggested topics for a given question type."""
    try:
        suggestions = await question_service.get_topic_suggestions(question_type)
        return {"topics": suggestions}
    except Exception as e:
        logger.error(f"Failed to get topic suggestions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get topic suggestions: {str(e)}")

@app.get("/user/limits")
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

@app.get("/admin/users")
async def get_all_users(current_user: UserProfile = Depends(get_current_user)):
    """Get all users with their daily limits (admin only)."""
    try:
        logger.info("🔍 ADMIN: Starting get_all_users function")
        
        # Check if user is admin using the role from the dependency
        if current_user.role != 'admin':
            logger.warning("🔍 ADMIN: User is not admin")
            raise HTTPException(
                status_code=403,
                detail="Admin access required"
            )
        
        logger.info("🔍 ADMIN: User is admin, proceeding with admin operations")
        
        # Use service role key for admin operations
        service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY
        if not service_role_key:
            logger.error("🔍 ADMIN: Service role key not set in environment")
            raise HTTPException(status_code=500, detail='Service role key not set in environment')
        
        logger.info("🔍 ADMIN: Service role key found, creating admin client")
        supabase_url = settings.SUPABASE_URL
        admin_client = create_client(supabase_url, service_role_key)
        
        # Get all users from auth.users
        logger.info("🔍 ADMIN: Calling admin_client.auth.admin.list_users()")
        response = admin_client.auth.admin.list_users()
        users = response
        logger.info(f"🔍 ADMIN: Retrieved {len(users)} users from auth.users")
        
        # Get daily limits for all users
        logger.info("🔍 ADMIN: Calling admin_client.table('user_daily_limits').select('*').execute()")
        limits_response = admin_client.table('user_daily_limits').select('*').execute()
        limits_data = {row['user_id']: row for row in limits_response.data} if limits_response.data else {}
        logger.info(f"🔍 ADMIN: Retrieved limits data for {len(limits_data)} users")
        
        # Combine user data with limits
        logger.info("🔍 ADMIN: Combining user data with limits")
        users_with_limits = []
        for user in users:
            user_limits = limits_data.get(user.id, {})
            user_metadata = user.user_metadata or {}
            # Determine user role and limits
            role = user_metadata.get('role', 'free')
            if role == 'admin':
                limits = DailyLimitService.UNLIMITED_LIMITS
            elif role == 'premium':
                limits = DailyLimitService.PREMIUM_LIMITS
            else:
                custom_limits = user_metadata.get('daily_limits', {})
                limits = {
                    "quantitative": custom_limits.get("quantitative", DailyLimitService.DEFAULT_LIMITS["quantitative"]),
                    "analogy": custom_limits.get("analogy", DailyLimitService.DEFAULT_LIMITS["analogy"]),
                    "synonym": custom_limits.get("synonym", DailyLimitService.DEFAULT_LIMITS["synonym"]),
                    "reading_passages": custom_limits.get("reading_passages", DailyLimitService.DEFAULT_LIMITS["reading_passages"]),
                    "writing": custom_limits.get("writing", DailyLimitService.DEFAULT_LIMITS["writing"])
                }
            users_with_limits.append({
                "id": user.id,
                "email": user.email,
                "role": role,
                "created_at": user.created_at,
                "last_sign_in_at": user.last_sign_in_at,
                "limits": limits,
                "usage": {
                    "quantitative_generated": user_limits.get('quantitative_generated', 0),
                    "analogy_generated": user_limits.get('analogy_generated', 0),
                    "synonym_generated": user_limits.get('synonym_generated', 0),
                    "reading_passages_generated": user_limits.get('reading_passages_generated', 0),
                    "writing_generated": user_limits.get('writing_generated', 0),
                    "last_reset_date": user_limits.get('last_reset_date')
                }
            })
        
        logger.info(f"🔍 ADMIN: Successfully processed {len(users_with_limits)} users with limits")
        return {
            "success": True,
            "data": users_with_limits
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error getting all users: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail="Failed to get users"
        )

@app.put("/admin/users/{user_id}/role")
async def update_user_role(
    user_id: str, 
    request: RoleUpdateRequest,
    current_user: UserProfile = Depends(get_current_user)
):
    role = request.role
    """Update user role (admin only)."""
    try:
        # Check if user is admin using the role from the dependency
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=403,
                detail="Admin access required"
            )
        
        # Validate role
        if role not in ['free', 'premium', 'admin']:
            raise HTTPException(
                status_code=400,
                detail="Invalid role. Must be 'free', 'premium', or 'admin'"
            )
        
        # Use service role key for admin operations
        service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY
        if not service_role_key:
            logger.error("🔍 ADMIN: Service role key not set in environment")
            raise HTTPException(status_code=500, detail='Service role key not set in environment')
        
        supabase_url = settings.SUPABASE_URL
        admin_client = create_client(supabase_url, service_role_key)
        
        # Get target user directly by ID (optimization)
        try:
            user_response = admin_client.auth.admin.get_user_by_id(user_id)
            target_user = user_response.user  # type: ignore[attr-defined]
        except Exception as e:
            logger.error(f"🔍 ADMIN: Failed to get user {user_id}: {e}")
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        if not target_user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        # Update user metadata
        current_metadata = target_user.user_metadata or {}
        updated_metadata = {
            **current_metadata,
            "role": role
        }
        
        # Set appropriate limits based on role
        if role == 'admin':
            updated_metadata['daily_limits'] = DailyLimitService.UNLIMITED_LIMITS
        elif role == 'premium':
            updated_metadata['daily_limits'] = DailyLimitService.PREMIUM_LIMITS
        else:  # free
            updated_metadata['daily_limits'] = DailyLimitService.DEFAULT_LIMITS
        
        # Update the user
        admin_client.auth.admin.update_user_by_id(
            user_id,
            {"user_metadata": updated_metadata}
        )
        
        return {
            "success": True,
            "message": f"User role updated to {role}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user role: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update user role"
        )

@app.post("/admin/generate")
async def admin_generate_content(request: QuestionGenerationRequest, current_user: UserProfile = Depends(get_current_user)):
    """Admin endpoint to generate content directly with LLM and save to pool (bypasses daily limits)."""
    import time
    import uuid
    start_time = time.time()
    
    try:
        # Check if user is admin
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=403,
                detail="Admin access required"
            )
        
        logger.info(f"🔍 ADMIN GENERATE: Generating {request.count} {request.question_type.value} content for admin")
        
        # Create session for admin generation
        session_id = str(uuid.uuid4())
        
        # Create session for admin generation
        await ai_content_service.create_generation_session(session_id, {
            "question_type": request.question_type.value,
            "count": request.count,
            "difficulty": request.difficulty.value if request.difficulty else None,
            "topic": request.topic,
            "provider": request.provider.value if request.provider else None,
            "admin_generation": True  # Mark as admin generation
        }, current_user.id)
        
        # Use unified content service for proper type-specific generation
        result = await content_service.generate_content(request)
        
        # Save AI-generated content to database
        try:
            training_example_ids = result.metadata.training_example_ids if hasattr(result.metadata, 'training_example_ids') else []
            
            if isinstance(result, WritingGenerationResponse):
                # WritingGenerationResponse has .prompts
                logger.info(f"🔍 ADMIN GENERATE: Saving writing prompts to database - session: {session_id}, prompts count: {len(result.prompts)}")
                saved_prompt_ids = await ai_content_service.save_writing_prompts(session_id, {"writing_prompts": result.prompts}, training_example_ids)
                
                # Assign the database IDs back to the WritingPrompt objects
                for i, prompt in enumerate(result.prompts):
                    if i < len(saved_prompt_ids):
                        prompt.id = saved_prompt_ids[i]
                        logger.debug(f"Assigned database ID {saved_prompt_ids[i]} to writing prompt {i}")
                
                logger.info(f"🔍 ADMIN GENERATE: Successfully saved writing prompts to database")
            elif isinstance(result, ReadingGenerationResponse):
                # ReadingGenerationResponse has .passages
                logger.info(f"🔍 ADMIN GENERATE: Saving reading content to database - session: {session_id}, passages count: {len(result.passages)}")
                saved_ids = await ai_content_service.save_reading_content(
                    session_id, 
                    {"reading_sections": result.passages}, 
                    training_example_ids,
                    topic=request.topic or ""  # Pass the topic for tagging, default to empty string
                )
                
                # Assign the database IDs back to the ReadingPassage objects
                for i, passage in enumerate(result.passages):
                    if i < len(saved_ids.get('passage_ids', [])):
                        passage.id = saved_ids['passage_ids'][i]
                        logger.debug(f"Assigned database ID {saved_ids['passage_ids'][i]} to passage {i}")
                
                logger.info(f"🔍 ADMIN GENERATE: Successfully saved reading content to database")
            elif isinstance(result, QuestionGenerationResponse):
                # Regular questions (quantitative, analogy, synonym)
                # QuestionGenerationResponse has .questions
                section_mapping = {
                    "quantitative": "Quantitative",
                    "analogy": "Verbal",    # Analogies are part of Verbal section in database
                    "synonym": "Verbal"    # Synonyms are part of Verbal section in database
                }
                section_name = section_mapping.get(request.question_type.value, "Verbal")
                
                # Use AI-determined subsection - DO NOT OVERRIDE the AI's intelligent categorization
                if request.question_type.value == "analogy":
                    subsection = "Analogies"  # Fixed subsection for analogy questions
                elif request.question_type.value == "synonym":
                    subsection = "Synonyms"  # Fixed subsection for synonyms questions
                else:
                    # For quantitative and verbal questions, ALWAYS use AI-determined subsection
                    # The AI has analyzed the content and provided specific, educational categorization
                    subsection = None  # Will be extracted per question in save_generated_questions
                
                # Get training example IDs from the result metadata
                training_example_ids = result.metadata.training_example_ids
                logger.debug(f"Using training example IDs from result metadata: {training_example_ids}")
                
                # Save questions to database and get the generated IDs
                saved_question_ids = await ai_content_service.save_generated_questions(
                    session_id, 
                    result.questions,
                    section_name, 
                    subsection or "",  # Convert None to empty string
                    training_example_ids
                )
                
                # Assign the database IDs back to the GeneratedQuestion objects
                for i, question in enumerate(result.questions):
                    if i < len(saved_question_ids):
                        question.id = saved_question_ids[i]
                        logger.debug(f"Assigned database ID {saved_question_ids[i]} to question {i}")
            
            # Get the provider used from the result metadata
            provider_used = result.metadata.provider_used
            
            # Calculate generation duration
            generation_time_ms = int((time.time() - start_time) * 1000)
            
            # Update session as completed with provider information and duration
            await ai_content_service.update_session_status(
                session_id, 
                "completed", 
                request.count, 
                [provider_used],
                generation_time_ms
            )
            logger.info(f"🔍 ADMIN GENERATE: Saved admin generation to database: session {session_id} with provider: {provider_used}, duration: {generation_time_ms}ms")
            
        except Exception as save_error:
            logger.error(f"🔍 ADMIN GENERATE: Failed to save admin generation: {save_error}")
            # Continue without failing the request
        
        # Return the full generated content to admin
        return {
            "success": True,
            "message": f"Successfully generated {request.count} {request.question_type.value} questions",
            "session_id": session_id,
            "generation_time_ms": generation_time_ms,
            "provider_used": provider_used,
            "content": result.model_dump() if hasattr(result, 'model_dump') else result
        }
        
    except Exception as e:
        logger.error(f"🔍 ADMIN GENERATE: Error in admin generation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Admin generation failed: {str(e)}"
        )

@app.post("/admin/generate/complete-test")
async def admin_generate_complete_test(request: CompleteTestRequest, current_user: UserProfile = Depends(get_current_user)):
    """Admin endpoint to generate complete test directly with LLM and save to pool (bypasses daily limits)."""
    import time
    import uuid
    import asyncio
    start_time = time.time()
    
    try:
        # Check if user is admin
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=403,
                detail="Admin access required"
            )
        
        logger.info(f"🔍 ADMIN COMPLETE TEST: Generating complete test for admin with sections: {[s.value for s in request.include_sections]}")
        
        # Create session for admin generation
        session_id = str(uuid.uuid4())
        
        # Create session for admin generation
        await ai_content_service.create_generation_session(session_id, {
            "difficulty": request.difficulty.value,
            "include_sections": [section.value for section in request.include_sections],
            "custom_counts": request.custom_counts,
            "provider": request.provider.value if request.provider else None,
            "admin_generation": True,  # Mark as admin generation
            "complete_test": True  # Mark as complete test generation
        }, current_user.id)
        
        # Start background generation using existing function but bypass daily limits
        asyncio.create_task(generate_test_sections_background_admin(session_id, request))
        
        # Determine which counts are being used
        from app.specifications import get_official_question_counts
        official_counts = get_official_question_counts()
        
        # Use official counts if is_official_format is True, otherwise use custom counts
        actual_counts = official_counts if request.is_official_format else request.custom_counts
        
        return {
            "success": True,
            "message": f"Complete test generation started with {len(request.include_sections)} sections",
            "session_id": session_id,
            "sections": [s.value for s in request.include_sections],
            "custom_counts": actual_counts,
            "is_official_format": request.is_official_format
        }
        
    except Exception as e:
        logger.error(f"🔍 ADMIN COMPLETE TEST: Error in admin complete test generation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Admin complete test generation failed: {str(e)}"
        )

async def generate_test_sections_background_admin(session_id: str, request: CompleteTestRequest):
    """Background task to generate test sections for admin (bypasses daily limits)."""
    from app.services.job_manager import JobStatus
    
    start_time = time.time()
    providers_used = set()
    total_questions = 0
    completed_sections = []
    
    try:
        logger.info(f"🔍 ADMIN COMPLETE TEST: Starting background generation for session {session_id}")
        
        # Create tasks for all sections to run in parallel
        section_tasks = []
        for section_type in request.include_sections:
            task = asyncio.create_task(
                generate_single_section_background_admin(session_id, section_type, request)
            )
            section_tasks.append(task)
        
        # Wait for all sections to complete (or fail)
        section_results = await asyncio.gather(*section_tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(section_results):
            if isinstance(result, Exception):
                logger.error(f"🔍 ADMIN COMPLETE TEST: Section {request.include_sections[i].value} failed: {result}")
            elif isinstance(result, dict):
                completed_sections.append(result)
                if 'provider_used' in result and result['provider_used']:  # Only add non-None providers
                    providers_used.add(result['provider_used'])
                if 'question_count' in result:
                    total_questions += result['question_count']
        
        # Update session as completed
        generation_time_ms = int((time.time() - start_time) * 1000)
        providers_list = list(providers_used)
        await ai_content_service.update_session_status(
            session_id, 
            "completed", 
            total_questions, 
            providers_list, 
            generation_time_ms
        )
        
        logger.info(f"🔍 ADMIN COMPLETE TEST: Session {session_id} completed with {total_questions} total questions")
        logger.info(f"🔍 ADMIN COMPLETE TEST: Providers used: {list(providers_used)}")
        logger.info(f"🔍 ADMIN COMPLETE TEST: Completed sections: {[s.get('section_type', 'unknown') for s in completed_sections]}")
        
    except Exception as e:
        logger.error(f"🔍 ADMIN COMPLETE TEST: Background generation failed for session {session_id}: {e}")
        await ai_content_service.update_session_status(session_id, "failed")

async def generate_single_section_background_admin(session_id: str, section_type, request: CompleteTestRequest):
    """Generate a single section for admin (bypasses daily limits)."""
    try:
        logger.info(f"🔍 ADMIN COMPLETE TEST: Starting generation for section {section_type.value} in session {session_id}")
        
        # Use official test counts if is_official_format is True, otherwise use custom counts
        if request.is_official_format:
            # Use centralized official counts from specifications
            from app.specifications import get_official_question_counts
            official_counts = get_official_question_counts()
            section_count = official_counts.get(section_type.value, 5)
            logger.info(f"🔍 ADMIN COMPLETE TEST: Using OFFICIAL count: {section_count} for section {section_type.value}")
        else:
            # Use custom counts if provided, otherwise use defaults
            custom_counts = request.custom_counts or {}
            section_count = custom_counts.get(section_type.value, {
                "quantitative": 25, "analogy": 15, "synonyms": 15, "reading": 7, "writing": 1
            }.get(section_type.value, 5))
            logger.info(f"🔍 ADMIN COMPLETE TEST: Using CUSTOM count: {section_count} for section {section_type.value}")
        
        logger.info(f"🔍 ADMIN COMPLETE TEST: Generating {section_count} items for section {section_type.value}")
        
        # Generate the section using existing service methods
        if section_type.value == "writing":
            logger.debug(f"📝 ADMIN COMPLETE TEST: Using writing section generation")
            section = await question_service._generate_writing_section(request.difficulty)
        elif section_type.value == "reading":
            logger.debug(f"📖 ADMIN COMPLETE TEST: Using reading section generation")
            section = await question_service._generate_reading_section(
                request.difficulty, section_count, request.provider, use_async=True, is_official_format=request.is_official_format, topic=None
            )
        elif section_type.value == "quantitative":
            # Use 5-call strategy for all admin quantitative generation (token efficiency)
            logger.debug(f"🎯 ADMIN COMPLETE TEST: Using enhanced 5-call quantitative generation for {section_count} questions")
            section = await question_service._generate_quantitative_section_official_5_calls(
                request.difficulty, section_count, request.provider, use_async=True
            )
        # NOTE: Custom format quantitative route commented out (unused - admin always uses official format)
        # else:
        #     logger.debug(f"⚙️ ADMIN COMPLETE TEST: Using regular standalone generation for {section_type.value}")
        #     section = await question_service._generate_standalone_section(
        #         section_type, request.difficulty, section_count, request.provider, use_async=True, is_official_format=request.is_official_format
        #     )
        
        # Convert section to dict for storage
        if hasattr(section, 'model_dump'):
            section_data = section.model_dump()
        else:
            section_data = section.__dict__
        
        # Extract provider and question count
        provider_used = None
        question_count = 0
        
        # Extract provider from section_data based on section type
        if section_type.value in ['quantitative', 'analogy', 'synonym']:
            # For question-based sections
            if 'questions' in section_data and section_data['questions']:
                question_count = len(section_data['questions'])
                for question in section_data['questions']:
                    if isinstance(question, dict) and 'metadata' in question:
                        provider_used = question['metadata'].get('provider_used')
                        break
        elif section_type.value == 'reading':
            # For reading sections
            if 'passages' in section_data and section_data['passages']:
                for passage in section_data['passages']:
                    if isinstance(passage, dict) and 'questions' in passage:
                        question_count += len(passage['questions'])
                        for question in passage['questions']:
                            if isinstance(question, dict) and 'metadata' in question:
                                provider_used = question['metadata'].get('provider_used')
                                break
                        if provider_used:
                            break
        elif section_type.value == 'writing':
            # For writing sections
            question_count = 1  # Count as 1 unit
            if 'prompt' in section_data and section_data['prompt']:
                if isinstance(section_data['prompt'], dict) and 'metadata' in section_data['prompt']:
                    provider_used = section_data['prompt']['metadata'].get('provider_used')
        
        # Add metadata to section_data
        if 'metadata' not in section_data:
            section_data['metadata'] = {}
        if provider_used:
            section_data['metadata']['provider_used'] = provider_used
        else:
            # Fallback to request provider if available
            fallback_provider = request.provider.value if request.provider else None
            if fallback_provider:
                section_data['metadata']['provider_used'] = fallback_provider
        
        # Ensure section_type is set in section_data for proper tracking
        section_data['section_type'] = section_type.value
        
        # Save AI-generated content to database
        try:
            logger.info(f"📝 ADMIN COMPLETE TEST: Completed section {section_type.value}")
            
            saved_ids = await ai_content_service.save_test_section(session_id, section)
            logger.info(f"🔍 ADMIN COMPLETE TEST: Saved AI content for section {section_type.value}: {saved_ids}")
        except Exception as e:
            logger.error(f"🔍 ADMIN COMPLETE TEST: Failed to save AI content for section {section_type.value}: {e}")
            # Continue with session completion even if saving fails
        
        logger.info(f"🔍 ADMIN COMPLETE TEST: Completed section {section_type.value} for session {session_id}")
        
        return {
            'section_type': section_type.value,
            'provider_used': provider_used,
            'question_count': question_count,
            'section_data': section_data
        }
        
    except Exception as e:
        logger.error(f"🔍 ADMIN COMPLETE TEST: Failed to generate section {section_type.value} for session {session_id}: {e}")
        return {
            'section_type': section_type.value,
            'error': str(e)
        }

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "status_code": 500}
    )

@app.get("/specifications/official-format")
async def get_official_format_specs():
    """Get official SSAT Elementary format specifications."""
    from app.specifications import OFFICIAL_ELEMENTARY_SPECS, get_official_question_counts
    
    # Use centralized official counts
    official_counts = get_official_question_counts()
    specs = OFFICIAL_ELEMENTARY_SPECS
    
    return {
        "quantitative": official_counts["quantitative"],  # 30
        "analogy": official_counts["analogy"],  # 12 (40% of 30)
        "synonym": official_counts["synonym"],   # 18 (60% of 30)
        "reading": official_counts["reading"],  # 28 questions (7 passages)
        "writing": official_counts["writing"],  # 1
        "total_questions": specs["total_scored_questions"],  # 88
        "total_time": specs["total_time"]  # 110 minutes
    }

@app.post("/admin/save-training-examples")
async def save_training_examples(
    request: TrainingExamplesRequest,
    current_user: UserProfile = Depends(get_current_user)
):
    """Save training examples to database (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        result = await training_examples_service.save_training_examples(request, current_user.id)
        logger.info(f"✅ Admin saved {result['saved_count']} training examples for {request.section_type}")
        return result
    except Exception as e:
        logger.error(f"❌ Failed to save training examples: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/migrate-training-to-pool")
async def admin_migrate_training_to_pool(current_user: UserProfile = Depends(get_current_user)):
    """Admin endpoint to migrate all training examples to user-facing pool."""
    try:
        # Check if user is admin
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=403,
                detail="Admin access required"
            )
        
        logger.info(f"🔍 ADMIN MIGRATION: Starting migration of training examples to user pool")
        
        # Get migration statistics before migration
        stats_response = supabase.rpc('get_migration_statistics').execute()
        before_stats = stats_response.data[0] if stats_response.data else {}
        
        # Run the migration
        migration_response = supabase.rpc('migrate_all_training_to_pool').execute()
        migration_result = migration_response.data[0] if migration_response.data else {}
        
        # Get migration statistics after migration
        stats_response_after = supabase.rpc('get_migration_statistics').execute()
        after_stats = stats_response_after.data[0] if stats_response_after.data else {}
        
        return {
            "success": True,
            "message": "Training examples successfully migrated to user pool",
            "migration_results": {
                "questions_migrated": migration_result.get('migrated_questions', 0),
                "passages_migrated": migration_result.get('migrated_passages', 0),
                "reading_questions_migrated": migration_result.get('migrated_reading_questions', 0),
                "writing_prompts_migrated": migration_result.get('migrated_writing_prompts', 0),
                "total_skipped": migration_result.get('total_skipped', 0),
                "total_errors": migration_result.get('total_errors', 0)
            },
            "before_migration": {
                "training_questions": before_stats.get('training_questions_count', 0),
                "training_passages": before_stats.get('training_passages_count', 0),
                "training_reading_questions": before_stats.get('training_reading_questions_count', 0),
                "training_writing_prompts": before_stats.get('training_writing_prompts_count', 0),
                "pool_questions": before_stats.get('pool_questions_count', 0),
                "pool_passages": before_stats.get('pool_passages_count', 0),
                "pool_reading_questions": before_stats.get('pool_reading_questions_count', 0),
                "pool_writing_prompts": before_stats.get('pool_writing_prompts_count', 0)
            },
            "after_migration": {
                "pool_questions": after_stats.get('pool_questions_count', 0),
                "pool_passages": after_stats.get('pool_passages_count', 0),
                "pool_reading_questions": after_stats.get('pool_reading_questions_count', 0),
                "pool_writing_prompts": after_stats.get('pool_writing_prompts_count', 0)
            }
        }
        
    except Exception as e:
        logger.error(f"🔍 ADMIN MIGRATION: Error in migration: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Migration failed: {str(e)}"
        )

@app.get("/admin/migration-statistics")
async def admin_get_migration_statistics(current_user: UserProfile = Depends(get_current_user)):
    """Admin endpoint to get migration statistics."""
    try:
        # Check if user is admin
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=403,
                detail="Admin access required"
            )
        
        # Get migration statistics
        stats_response = supabase.rpc('get_migration_statistics').execute()
        stats = stats_response.data[0] if stats_response.data else {}
        
        return {
            "success": True,
            "statistics": {
                "training_content": {
                    "questions": stats.get('training_questions_count', 0),
                    "passages": stats.get('training_passages_count', 0),
                    "reading_questions": stats.get('training_reading_questions_count', 0),
                    "writing_prompts": stats.get('training_writing_prompts_count', 0)
                },
                "pool_content": {
                    "questions": stats.get('pool_questions_count', 0),
                    "passages": stats.get('pool_passages_count', 0),
                    "reading_questions": stats.get('pool_reading_questions_count', 0),
                    "writing_prompts": stats.get('pool_writing_prompts_count', 0)
                },
                "migrated_content": {
                    "questions": stats.get('migrated_questions_count', 0),
                    "passages": stats.get('migrated_passages_count', 0),
                    "reading_questions": stats.get('migrated_reading_questions_count', 0),
                    "writing_prompts": stats.get('migrated_writing_prompts_count', 0)
                }
            }
        }
        
    except Exception as e:
        logger.error(f"🔍 ADMIN MIGRATION: Error getting statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get migration statistics: {str(e)}"
        )

@app.post("/admin/cleanup-migrated-content")
async def admin_cleanup_migrated_content(current_user: UserProfile = Depends(get_current_user)):
    """Admin endpoint to cleanup migrated content."""
    try:
        # Check if user is admin
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=403,
                detail="Admin access required"
            )
        
        # Cleanup migrated content
        cleanup_response = supabase.rpc('cleanup_migrated_content').execute()
        cleanup_result = cleanup_response.data[0] if cleanup_response.data else {}
        
        return {
            "success": True,
            "message": "Migrated content cleaned up successfully",
            "removed": {
                "questions": cleanup_result.get('removed_questions', 0),
                "passages": cleanup_result.get('removed_passages', 0),
                "reading_questions": cleanup_result.get('removed_reading_questions', 0),
                "writing_prompts": cleanup_result.get('removed_writing_prompts', 0)
            }
        }
        
    except Exception as e:
        logger.error(f"🔍 ADMIN CLEANUP: Error cleaning up content: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Cleanup failed: {str(e)}"
        )

# ========================================
# ADMIN STATISTICS ENDPOINTS
# ========================================

@app.get("/admin/statistics/overview")
async def admin_get_overview_statistics(current_user: UserProfile = Depends(get_current_user)):
    """Admin endpoint to get platform overview statistics."""
    try:
        # Check if user is admin
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=403,
                detail="Admin access required"
            )
        
        # Get overview statistics
        stats_response = supabase.rpc('get_platform_overview_statistics').execute()
        stats = stats_response.data[0] if stats_response.data else {}
        
        return {
            "success": True,
            "statistics": {
                "users": {
                    "total_users": stats.get('total_users', 0)
                },
                "content": {
                    "total_training_content": stats.get('total_training_content', 0),
                    "total_ai_generated_content": stats.get('total_ai_generated_content', 0)
                },
                "generation": {
                    "total_generation_sessions": stats.get('total_generation_sessions', 0),
                    "successful_generations_last_7_days": stats.get('successful_generations_last_7_days', 0),
                    "failed_generations_last_7_days": stats.get('failed_generations_last_7_days', 0),
                    "success_rate_percentage": float(stats.get('success_rate_percentage', 0))
                }
            }
        }
        
    except Exception as e:
        logger.error(f"🔍 ADMIN STATISTICS: Error getting overview statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get overview statistics: {str(e)}"
        )

@app.get("/admin/statistics/content")
async def admin_get_content_statistics(current_user: UserProfile = Depends(get_current_user)):
    """Admin endpoint to get content breakdown statistics."""
    try:
        # Check if user is admin
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=403,
                detail="Admin access required"
            )
        
        # Get content statistics
        stats_response = supabase.rpc('get_content_breakdown_statistics').execute()
        stats = stats_response.data[0] if stats_response.data else {}
        
        return {
            "success": True,
            "statistics": {
                "training_content": {
                    "quantitative": stats.get('training_quantitative', 0),
                    "analogies": stats.get('training_analogies', 0),
                    "synonyms": stats.get('training_synonyms', 0),
                    "reading_passages": stats.get('training_reading_passages', 0),
                    "reading_questions": stats.get('training_reading_questions', 0),
                    "writing_prompts": stats.get('training_writing_prompts', 0)
                },
                "ai_generated_content": {
                    "quantitative": stats.get('ai_quantitative', 0),
                    "analogies": stats.get('ai_analogies', 0),
                    "synonyms": stats.get('ai_synonyms', 0),
                    "reading_passages": stats.get('ai_reading_passages', 0),
                    "reading_questions": stats.get('ai_reading_questions', 0),
                    "writing_prompts": stats.get('ai_writing_prompts', 0)
                }
            }
        }
        
    except Exception as e:
        logger.error(f"🔍 ADMIN STATISTICS: Error getting content statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get content statistics: {str(e)}"
        )



@app.get("/admin/statistics/pool")
async def admin_get_pool_statistics(current_user: UserProfile = Depends(get_current_user)):
    """Admin endpoint to get pool utilization statistics."""
    try:
        # Check if user is admin
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=403,
                detail="Admin access required"
            )
        
        # Get pool statistics
        stats_response = supabase.rpc('get_pool_utilization_statistics').execute()
        stats = stats_response.data[0] if stats_response.data else {}
        
        return {
            "success": True,
            "statistics": {
                "quantitative": {
                    "used": stats.get('quantitative_used', 0),
                    "remaining": stats.get('quantitative_remaining', 0)
                },
                "analogy": {
                    "used": stats.get('analogy_used', 0),
                    "remaining": stats.get('analogy_remaining', 0)
                },
                "synonym": {
                    "used": stats.get('synonym_used', 0),
                    "remaining": stats.get('synonym_remaining', 0)
                },
                "reading": {
                    "used": stats.get('reading_used', 0),
                    "remaining": stats.get('reading_remaining', 0)
                },
                "writing": {
                    "used": stats.get('writing_used', 0),
                    "remaining": stats.get('writing_remaining', 0)
                }
            }
        }
        
    except Exception as e:
        logger.error(f"🔍 ADMIN STATISTICS: Error getting pool statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pool statistics: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)