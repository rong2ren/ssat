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
    CompleteTestRequest
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

# Initialize Supabase client
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

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

# Initialize services
question_service = QuestionService()  # Keep for complete test generation
content_service = UnifiedContentService()  # New unified service for individual content
llm_service = LLMService()
ai_content_service = AIContentService()  # Service for saving AI-generated content

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
                        "quantitative": "math questions",
                        "analogy": "analogy questions", 
                        "synonyms": "synonym questions",
                        "reading_passages": "reading passages",
                        "writing": "writing prompts"
                    }
                    
                    section_display_name = section_names.get(section, section)
                    error_message = f"You've reached your daily limit for {section_display_name}. Please try again tomorrow or upgrade your account for higher limits."
                    
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
        
        # Use unified content service for proper type-specific generation
        result = await content_service.generate_content(request)
        
        # Save AI-generated content to database
        try:
            import uuid
            session_id = str(uuid.uuid4())
            
            # Create session for single content generation
            await ai_content_service.create_generation_session(session_id, {
                "question_type": request.question_type.value,
                "count": request.count,
                "difficulty": request.difficulty.value if request.difficulty else None,
                "topic": request.topic,
                "provider": request.provider.value if request.provider else None
            }, current_user.id)
            
            # Save the generated content based on actual response type (using proper type narrowing)
            training_example_ids = result.metadata.training_example_ids if hasattr(result.metadata, 'training_example_ids') else []
            
            if isinstance(result, WritingGenerationResponse):
                # WritingGenerationResponse has .prompts
                logger.info(f"Saving writing prompts to database - session: {session_id}, prompts count: {len(result.prompts)}")
                await ai_content_service.save_writing_prompts(session_id, {"writing_prompts": result.prompts}, training_example_ids)
                logger.info(f"Successfully saved writing prompts to database")
            elif isinstance(result, ReadingGenerationResponse):
                # ReadingGenerationResponse has .passages
                logger.info(f"Saving reading content to database - session: {session_id}, passages count: {len(result.passages)}")
                await ai_content_service.save_reading_content(
                    session_id, 
                    {"reading_sections": result.passages}, 
                    training_example_ids,
                    topic=request.topic or ""  # Pass the topic for tagging, default to empty string
                )
                logger.info(f"Successfully saved reading content to database")
            elif isinstance(result, QuestionGenerationResponse):
                # Regular questions (quantitative, analogy, synonym)
                # QuestionGenerationResponse has .questions
                section_mapping = {
                    "quantitative": "Quantitative",
                    "analogy": "Verbal",    # Analogies are part of Verbal section in database
                    "synonym": "Verbal"     # Synonyms are part of Verbal section in database
                }
                section_name = section_mapping.get(request.question_type.value, "Verbal")
                
                # Use AI-determined subsection - DO NOT OVERRIDE the AI's intelligent categorization
                if request.question_type.value == "analogy":
                    subsection = "Analogies"  # Fixed subsection for analogy questions
                elif request.question_type.value == "synonym":
                    subsection = "Synonyms"  # Fixed subsection for synonym questions
                else:
                    # For quantitative and verbal questions, ALWAYS use AI-determined subsection
                    # The AI has analyzed the content and provided specific, educational categorization
                    subsection = None  # Will be extracted per question in save_generated_questions
                
                # Get training example IDs from the result metadata
                training_example_ids = result.metadata.training_example_ids
                logger.debug(f"Using training example IDs from result metadata: {training_example_ids}")
                
                await ai_content_service.save_generated_questions(
                    session_id, 
                    result.questions,
                    section_name, 
                    subsection or "",  # Convert None to empty string
                    training_example_ids
                )
            
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
            logger.debug(f"Saved single content generation to database: session {session_id} with provider: {provider_used}, duration: {generation_time_ms}ms")
            
        except Exception as save_error:
            logger.error(f"Failed to save single content generation: {save_error}")
            # Continue without failing the request
        
        # INCREMENT PHASE: Increment usage after successful generation
        try:
            # Determine the count to increment based on section type and actual result
            increment_count = 0
            if section == "quantitative" or section == "analogy" or section == "synonyms":
                if isinstance(result, QuestionGenerationResponse):
                    increment_count = len(result.questions)
                else:
                    increment_count = request.count
            elif section == "reading_passages":
                if isinstance(result, ReadingGenerationResponse):
                    increment_count = len(result.passages)
                else:
                    increment_count = request.count
            elif section == "writing":
                if isinstance(result, WritingGenerationResponse):
                    increment_count = len(result.prompts)
                else:
                    increment_count = 1
            
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
        
        # Return the type-specific response (QuestionGenerationResponse, ReadingGenerationResponse, or WritingGenerationResponse)
        return result
        
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
                    synonyms_count = verbal_count - analogy_count
                    sections_to_check.append(("analogy", analogy_count))
                    sections_to_check.append(("synonyms", synonyms_count))
            
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
                        "synonyms": "synonym questions",
                        "reading_passages": "reading passages",
                        "writing": "writing prompts"
                    }
                    
                    section_display_name = section_names.get(section_name, section_name)
                    error_message = f"You've reached your daily limit for {section_display_name}. Please try again tomorrow or upgrade your account for higher limits."
                    
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
        await asyncio.gather(*section_tasks, return_exceptions=True)
        
        # Check final job status and update AI session
        job = job_manager.get_job(job_id)
        if job and job.completed_sections == job.total_sections:
            job_manager.update_job_status(job_id, JobStatus.COMPLETED)
            
            # Count total questions and providers used
            for section_progress in job.sections.values():
                if section_progress.section_data:
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
            await ai_content_service.update_session_status(
                job_id, 
                "completed", 
                total_questions, 
                providers_list, 
                generation_time_ms
            )
            
            logger.info(f"📊 DEBUG: Session {job_id} completed with {total_questions} total questions")
            logger.info(f"📊 DEBUG: Providers used: {list(providers_used)}")
            logger.info(f"All sections completed for job {job_id}: {total_questions} questions, {generation_time_ms}ms")
            
            # After all sections are completed, batch increment daily limits for the user
            if job and job.user_id:
                # Aggregate counts for each section
                quantitative = 0
                analogy = 0
                synonyms = 0
                reading_passages = 0
                writing = 0
                for section_progress in job.sections.values():
                    if section_progress.section_data:
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
                                synonyms += len(section_data['questions'])
                        elif section_type == 'reading':
                            if 'passages' in section_data:
                                reading_passages += len(section_data['passages'])
                        elif section_type == 'writing':
                            # Count writing prompts from section data
                            if 'prompts' in section_data:
                                writing += len(section_data['prompts'])
                            elif 'writing_prompts' in section_data:
                                writing += len(section_data['writing_prompts'])
                            else:
                                # Fallback: if no specific prompts array, count as 1
                                writing += 1
                try:
                    supabase = get_database_connection()
                    logger.info(f"🔍 DAILY LIMITS: Batch increment for user {job.user_id}: quantitative={quantitative}, analogy={analogy}, synonyms={synonyms}, reading_passages={reading_passages}, writing={writing}")
                    response = supabase.rpc(
                        'increment_user_daily_usage_batch',
                        {
                            'p_user_id': job.user_id,
                            'p_quantitative': quantitative,
                            'p_analogy': analogy,
                            'p_synonyms': synonyms,
                            'p_reading_passages': reading_passages,
                            'p_writing': writing
                        }
                    ).execute()
                    logger.info(f"🔍 DAILY LIMITS: Batch increment response: {response.data}")
                except Exception as e:
                    logger.error(f"🔍 DAILY LIMITS: ❌ Error in batch increment: {e}")
        else:
            # Update session as failed
            await ai_content_service.update_session_status(job_id, "failed")
        
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
        
        # Update progress: about to start LLM generation (50% of section progress)
        job_manager.update_section_progress(job_id, section_type.value, 50, f"Generating {section_count} questions...")
        
        # Generate the section using async service methods for true parallelism
        logger.debug(f"🔍 DEBUG: Generating section {section_type.value} with is_official_format={request.is_official_format}")
        
        if section_type.value == "writing":
            logger.debug(f"📝 DEBUG: Using writing section generation")
            section = await question_service._generate_writing_section(request.difficulty)
        elif section_type.value == "reading":
            logger.debug(f"📖 DEBUG: Using reading section generation")
            section = await question_service._generate_reading_section(
                request.difficulty, section_count, request.provider, use_async=True
            )
        elif section_type.value == "quantitative" and request.is_official_format:
            # Use official topic breakdown for quantitative questions
            logger.debug(f"🎯 DEBUG: Using OFFICIAL quantitative generation with topic breakdown for {section_count} questions")
            section = await question_service._generate_quantitative_section_official(
                request.difficulty, section_count, request.provider, use_async=True
            )
        else:
            logger.debug(f"⚙️ DEBUG: Using regular standalone generation for {section_type.value}")
            section = await question_service._generate_standalone_section(
                section_type, request.difficulty, section_count, request.provider, use_async=True, is_official_format=request.is_official_format
            )
        
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
                    "synonyms": custom_limits.get("synonyms", DailyLimitService.DEFAULT_LIMITS["synonyms"]),
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
                    "synonyms_generated": user_limits.get('synonyms_generated', 0),
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)