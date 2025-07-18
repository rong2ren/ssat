"""FastAPI application for SSAT question generation."""

# FastAPI imports

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import asyncio
import uuid
from datetime import datetime
from loguru import logger

from app.models.requests import (
    QuestionGenerationRequest, 
    CompleteTestRequest,
    CompleteElementaryTestRequest
)
from app.models.responses import (
    QuestionGenerationResponse,
    ReadingGenerationResponse,
    WritingGenerationResponse,
    CompleteElementaryTestResponse,
    ProviderStatusResponse,
    HealthResponse,
    GenerationMetadata
)
from app.services.question_service import QuestionService
from app.services.unified_content_service import UnifiedContentService
from app.services.llm_service import LLMService
from app.services.ai_content_service import AIContentService
from app.models import QuestionType

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
    """Health check endpoint."""
    try:
        # Test database connection
        db_status = await question_service.check_database_connection()
        
        return HealthResponse(
            status="healthy" if db_status else "degraded",
            message="API is running",
            version="1.0.0",
            database_connected=db_status
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            message=f"Health check failed: {str(e)}",
            version="1.0.0",
            database_connected=False
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
async def generate_content(request: QuestionGenerationRequest):
    """Generate SSAT content based on request parameters. Returns type-specific response."""
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
            })
            
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
                
                # Get training example IDs by fetching recent examples for this question type
                try:
                    from app.generator import SSATGenerator
                    from app.models import QuestionRequest, QuestionType as SSATQuestionType, DifficultyLevel as SSATDifficultyLevel
                    
                    # Map API types to internal types
                    ssat_type_mapping = {
                        "quantitative": SSATQuestionType.QUANTITATIVE,
                        "analogy": SSATQuestionType.ANALOGY,
                        "synonym": SSATQuestionType.SYNONYM,
                        "verbal": SSATQuestionType.VERBAL
                    }
                    ssat_difficulty_mapping = {
                        "Easy": SSATDifficultyLevel.EASY,
                        "Medium": SSATDifficultyLevel.MEDIUM,
                        "Hard": SSATDifficultyLevel.HARD
                    }
                    
                    # Create internal request to get training examples
                    ssat_request = QuestionRequest(
                        question_type=ssat_type_mapping.get(request.question_type.value, SSATQuestionType.VERBAL),
                        difficulty=ssat_difficulty_mapping.get(request.difficulty.value if request.difficulty else "Medium", SSATDifficultyLevel.MEDIUM),
                        topic=request.topic,
                        count=request.count
                    )
                    
                    generator = SSATGenerator()
                    training_examples = generator.get_training_examples(ssat_request)
                    training_example_ids = [ex.get('id', '') for ex in training_examples if ex.get('id')]
                    
                    logger.info(f"Captured training example IDs for saving: {training_example_ids}")
                except Exception as e:
                    logger.warning(f"Could not capture training example IDs: {e}")
                    training_example_ids = []
                
                await ai_content_service.save_generated_questions(
                    session_id, 
                    result.questions,
                    section_name, 
                    subsection or "",  # Convert None to empty string
                    training_example_ids
                )
            
            # Update session as completed
            await ai_content_service.update_session_status(session_id, "completed", request.count)
            logger.info(f"Saved single content generation to database: session {session_id}")
            
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
async def start_progressive_test_generation(request: CompleteTestRequest):
    """Start progressive test generation and return job ID for polling."""
    try:
        from app.services.job_manager import job_manager
        
        logger.info(f"Starting progressive test generation - difficulty: {request.difficulty}")
        
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
        })
        
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
                    if 'questions' in section_data:
                        total_questions += len(section_data['questions'])
                    elif 'reading_sections' in section_data:
                        for reading_section in section_data['reading_sections']:
                            total_questions += len(reading_section.get('questions', []))
                    elif 'writing_prompts' in section_data:
                        total_questions += len(section_data['writing_prompts'])
                    
                    # Track provider used
                    if 'metadata' in section_data and 'provider_used' in section_data['metadata']:
                        providers_used.add(section_data['metadata']['provider_used'])
            
            # Update AI session with final statistics
            generation_time_ms = int((time.time() - start_time) * 1000)
            await ai_content_service.update_session_status(
                job_id, 
                "completed", 
                total_questions, 
                list(providers_used), 
                generation_time_ms
            )
            
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
        section_count = custom_counts.get(section_type.value, {
            "quantitative": 10, "analogy": 4, "synonym": 6, "reading": 7, "writing": 1
        }.get(section_type.value, 5))
        
        # Update progress: about to start LLM generation (50% of section progress)
        job_manager.update_section_progress(job_id, section_type.value, 50, f"Generating {section_count} questions...")
        
        # Generate the section using async service methods for true parallelism
        if section_type.value == "writing":
            section = await question_service._generate_writing_section(request.difficulty)
        elif section_type.value == "reading":
            section = await question_service._generate_reading_section(
                request.difficulty, section_count, request.provider, use_async=True
            )
        else:
            section = await question_service._generate_standalone_section(
                section_type, request.difficulty, section_count, request.provider, use_async=True
            )
        
        # Update progress: generation complete, processing results (90%)
        job_manager.update_section_progress(job_id, section_type.value, 90, "Processing results...")
        
        # Convert section to dict for storage
        if hasattr(section, 'model_dump'):
            section_data = section.model_dump()
        else:
            section_data = section.__dict__
        
        # Save AI-generated content to database
        try:
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

@app.post("/generate/complete-elementary-test", response_model=CompleteElementaryTestResponse)
async def generate_complete_elementary_test(request: CompleteElementaryTestRequest):
    """Generate a complete SSAT Elementary Level test (Official Format: 88 scored questions + writing)"""
    try:
        logger.info(f"Generating official SSAT Elementary test: {request}")
        start_time = time.time()
        
        # Convert to progressive test request with minimal counts for testing
        # TODO: Make this configurable for production (use testing_mode flag)
        testing_mode = True  # Set to False for production
        
        if testing_mode:
            # Minimal counts for testing to save tokens
            custom_counts = {
                "quantitative": 1,  # Testing: 1 question
                "verbal": 1,        # Testing: 1 question
                "reading": 1,       # Testing: 1 question (1 passage × 1 question)
                "writing": 1        # Testing: 1 prompt
            }
        else:
            # Official SSAT Elementary spec for production
            custom_counts = {
                "quantitative": 30,  # Official SSAT Elementary spec
                "verbal": 30,        # Official SSAT Elementary spec  
                "reading": 28,       # Official SSAT Elementary spec (7 passages × 4 questions)
                "writing": 1         # Official SSAT Elementary spec
            }
        
        progressive_request = CompleteTestRequest(
            difficulty=request.difficulty,
            include_sections=[QuestionType.QUANTITATIVE, QuestionType.VERBAL, QuestionType.READING, QuestionType.WRITING],
            custom_counts=custom_counts,
            provider=None  # Use best available provider
        )
        
        # Use the SAME generation logic as progressive tests for consistency
        job_id = str(uuid.uuid4())
        
        # Create AI generation session for tracking
        await ai_content_service.create_generation_session(job_id, {
            "test_type": "official_elementary",
            "difficulty": request.difficulty.value,
            "include_sections": [section.value for section in progressive_request.include_sections],
            "custom_counts": progressive_request.custom_counts,
            "student_grade": request.student_grade,
            "test_focus": request.test_focus
        })
        
        # Generate all sections using the same background logic (but synchronously for official test)
        sections_data = {}
        
        # Generate sections in parallel using the same logic as progressive tests
        from app.services.job_manager import job_manager
        
        # Create a temporary job for tracking (but don't expose it as progressive)
        temp_job_id = job_manager.create_job({
            "difficulty": progressive_request.difficulty.value,
            "include_sections": [section.value for section in progressive_request.include_sections],
            "custom_counts": progressive_request.custom_counts,
            "provider": None
        })
        
        # Generate sections in parallel
        section_tasks = []
        for section_type in progressive_request.include_sections:
            task = asyncio.create_task(
                generate_single_section_background(temp_job_id, section_type, progressive_request)
            )
            section_tasks.append(task)
        
        # Wait for all sections to complete
        await asyncio.gather(*section_tasks, return_exceptions=True)
        
        # Get completed sections from job manager
        completed_sections_list = job_manager.get_completed_sections(temp_job_id)
        
        # Convert list to dict format for easier processing
        completed_sections = {}
        for section in completed_sections_list:
            section_name = section.get("section_name", "").lower()
            completed_sections[section_name] = section
        
        # Convert to official test format
        sections_summary = {}
        test_instructions = {}
        
        for section_name, section_data in completed_sections.items():
            sections_summary[section_name] = len(section_data.get("questions", [])) if section_name != "writing" else 1
            test_instructions[section_name] = section_data.get("instructions", "")
        
        # Calculate totals
        total_questions = sum(count for section, count in sections_summary.items() if section != "writing") + 1  # +1 for writing
        estimated_time = 110  # Official SSAT Elementary timing: 30+20+15+30+15 = 110 minutes
        
        # Create metadata
        generation_time = time.time() - start_time
        metadata = GenerationMetadata(
            generation_time=generation_time,
            provider_used="mixed",  # Multiple providers used across sections
            training_examples_count=0,  # Will be updated by individual generators
            training_example_ids=[],
            request_id=job_id,
            timestamp=datetime.utcnow()
        )
        
        # Format as official test response
        response = CompleteElementaryTestResponse(
            test=dict(completed_sections),  # Convert to proper dict format
            sections_summary=sections_summary,
            total_questions=total_questions,
            estimated_completion_time=estimated_time,
            test_instructions=test_instructions,
            metadata=metadata,
            status="success"
        )
        
        logger.info(f"Successfully generated official SSAT test: {sections_summary} in {generation_time:.2f}s")
        return response
        
    except Exception as e:
        logger.error(f"Official SSAT test generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Test generation failed: {str(e)}")

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