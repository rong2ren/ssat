"""FastAPI application for SSAT question generation."""

# FastAPI imports

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
from datetime import datetime
from loguru import logger

from app.models.requests import (
    QuestionGenerationRequest, 
    CompleteTestRequest,
    CompleteElementaryTestRequest
)
from app.models.responses import (
    QuestionGenerationResponse,
    CompleteTestResponse,
    CompleteElementaryTestResponse,
    ProviderStatusResponse,
    HealthResponse,
    GenerationMetadata
)
from app.services.question_service import QuestionService
from app.services.llm_service import LLMService
from app.services.ssat_test_service import ssat_test_service

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
question_service = QuestionService()
llm_service = LLMService()

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

@app.post("/generate", response_model=QuestionGenerationResponse)
async def generate_questions(request: QuestionGenerationRequest):
    """Generate individual SSAT questions based on request parameters."""
    try:
        logger.info(f"Generating {request.count} {request.question_type} questions")
        
        result = await question_service.generate_questions(request)
        
        return QuestionGenerationResponse(**result)
        
    except Exception as e:
        logger.error(f"Question generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Question generation failed: {str(e)}")

@app.post("/generate/complete-test", response_model=CompleteTestResponse)
async def generate_complete_test(request: CompleteTestRequest):
    """Generate a complete SSAT practice test with all sections."""
    try:
        logger.info(f"Generating complete SSAT test - difficulty: {request.difficulty}")
        
        result = await question_service.generate_complete_test(request)
        
        return CompleteTestResponse(**result)
        
    except Exception as e:
        logger.error(f"Complete test generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Complete test generation failed: {str(e)}")

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
        
        # Generate the complete test
        complete_test = await ssat_test_service.generate_complete_elementary_test(request)
        
        # Validate official structure
        validation_results = ssat_test_service.validate_generated_test(complete_test)
        if not validation_results["overall_valid"]:
            logger.warning(f"Generated test validation failed: {validation_results}")
        
        # Create sections summary
        sections_summary = {}
        for section in complete_test.sections:
            sections_summary[section.section_name] = section.question_count
        sections_summary["Writing"] = 1  # Add writing prompt
        
        # Create test instructions
        test_instructions = {
            section.section_name: section.instructions 
            for section in complete_test.sections
        }
        test_instructions["Writing"] = complete_test.writing_prompt.instructions
        
        # Official timing: 30+20+15+30+15 = 110 minutes
        estimated_time = complete_test.total_time_minutes
        
        # Create metadata
        generation_time = time.time() - start_time
        metadata = GenerationMetadata(
            generation_time=generation_time,
            provider_used="mixed",  # Multiple providers used across sections
            training_examples_count=0,  # Will be updated by individual generators
            timestamp=datetime.utcnow()
        )
        
        response = CompleteElementaryTestResponse(
            test=complete_test.model_dump(),  # Convert to dict for response
            sections_summary=sections_summary,
            total_questions=complete_test.total_scored_questions,
            estimated_completion_time=estimated_time,
            test_instructions=test_instructions,
            metadata=metadata
        )
        
        logger.info(f"Successfully generated official SSAT test: {sections_summary} in {generation_time:.2f}s")
        return response
        
    except Exception as e:
        logger.error(f"Official SSAT test generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Test generation failed: {str(e)}")

@app.get("/generate/official-ssat-specs")
async def get_official_ssat_specifications():
    """Get official SSAT Elementary Level test specifications"""
    try:
        specs = ssat_test_service.get_test_specifications()
        return specs
    except Exception as e:
        logger.error(f"Failed to get SSAT specifications: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get specifications: {str(e)}")

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
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)