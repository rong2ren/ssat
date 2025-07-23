"""FastAPI application for SSAT question generation."""

# FastAPI imports

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import asyncio
import uuid
from datetime import datetime
from loguru import logger

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
from app.auth import router as auth_router, get_current_user
from app.models.user import UserProfile

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

@app.post("/generate")
async def generate_content(request: QuestionGenerationRequest, current_user: UserProfile = Depends(get_current_user)):
    """Generate SSAT content based on request parameters. Returns type-specific response."""
    import time
    start_time = time.time()
    
    try:
        logger.info(f"Generating {request.count} {request.question_type.value} content")
        
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
            # Get the provider from the result metadata
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
        
        # Create job with request data
        job_id = job_manager.create_job({
            "difficulty": request.difficulty.value,
            "include_sections": [section.value for section in request.include_sections],
            "custom_counts": request.custom_counts,
            "provider": request.provider.value if request.provider else None
        })
        
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