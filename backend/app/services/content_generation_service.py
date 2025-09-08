"""
Consolidated Content Generation Service - Phase 1 Implementation

This service consolidates core content generation logic from:
- ContentGenerationService (721 lines)
- UnifiedContentService (314 lines) 
- QuestionService (1448 lines)

External services remain separate:
- JobManager (job tracking)
- PoolSelectionService (content pool management)
- PoolResponseConverter (response formatting)
- AIContentService (content storage)

Phase 1 Goal: Focus on core content generation only
Key benefit: Clean separation of concerns
"""

import time
import uuid
import asyncio
from typing import Dict, Any, Union, List, Optional, cast
from loguru import logger
from fastapi import HTTPException

from app.models import QuestionRequest
from app.models.requests import QuestionGenerationRequest, CompleteTestRequest, QuestionType, DifficultyLevel
from app.models.responses import (
    QuestionGenerationResponse, ReadingGenerationResponse, WritingGenerationResponse,
    GenerationMetadata, GeneratedQuestion, ReadingPassage, WritingPrompt,
    QuantitativeSection, SynonymSection, AnalogySection, ReadingSection, WritingSection
)
from app.content_generators import (
    generate_writing_prompts_with_metadata,
    generate_reading_passages_with_metadata,
    generate_standalone_questions_with_metadata,
    GenerationResult,
    ReadingPassage as GeneratorReadingPassage,
    WritingPrompt as GeneratorWritingPrompt
)
from app.generator import SSATGenerator


class ContentGenerationService:
    """Consolidated service for core SSAT content generation logic."""
    
    def __init__(self):
        """Initialize the consolidated content generation service."""
        self.generator = None
        self._init_generator()
        logger.info("Consolidated Content Generation Service initialized")
    
    def _init_generator(self):
        """Initialize SSAT generator with database connection."""
        try:
            self.generator = SSATGenerator()
            logger.info("SSAT Generator initialized for Consolidated Content Generation Service")
        except Exception as e:
            logger.error(f"Failed to initialize generator: {e}")
            self.generator = None
    
    async def check_database_connection(self) -> bool:
        """Check if database connection is healthy."""
        try:
            if self.generator is None:
                return False
            
            # Try to get training examples as a health check
            test_request = QuestionRequest(
                question_type=QuestionType.QUANTITATIVE,
                difficulty=DifficultyLevel.MEDIUM,
                count=1
            )
            self.generator.get_training_examples(test_request)  # Just check if it works
            return True  # If no exception, connection is healthy
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def _convert_to_ssat_request(self, request: QuestionGenerationRequest) -> QuestionRequest:
        """Convert API request to internal SSAT request format."""
        # Map API enums to internal enums
        question_type_mapping = {
            QuestionType.QUANTITATIVE: QuestionType.QUANTITATIVE,
            QuestionType.READING: QuestionType.READING,
            QuestionType.VERBAL: QuestionType.VERBAL,
            QuestionType.ANALOGY: QuestionType.ANALOGY,
            QuestionType.SYNONYM: QuestionType.SYNONYM,
            QuestionType.WRITING: QuestionType.WRITING,
        }
        
        difficulty_mapping = {
            DifficultyLevel.EASY: DifficultyLevel.EASY,
            DifficultyLevel.MEDIUM: DifficultyLevel.MEDIUM,
            DifficultyLevel.HARD: DifficultyLevel.HARD,
        }
        
        # Determine if we should use explicit topics for diverse reading generation
        use_explicit_topics = (
            request.question_type == QuestionType.READING and
            request.count > 1 and
            not request.use_custom_examples and
            not request.topic
        )
        
        return QuestionRequest(
            question_type=question_type_mapping[request.question_type],
            difficulty=difficulty_mapping[request.difficulty],
            topic=request.topic,
            count=request.count,
            level=request.level,
            input_format=request.input_format,
            is_official_format=getattr(request, 'is_official_format', False),
            use_explicit_topics=use_explicit_topics
        )
    
    async def generate_individual_content(
        self, 
        request: QuestionGenerationRequest,
        force_llm_generation: bool = False,
        user_id: str = None,
        user_metadata: Optional[Dict[str, Any]] = None
    ) -> Union[QuestionGenerationResponse, ReadingGenerationResponse, WritingGenerationResponse]:
        """Generate individual SSAT content (1-20 questions)."""
        try:
            logger.info(f"Generating {request.count} {request.question_type.value} content (force_llm={force_llm_generation})")
            
            if force_llm_generation:
                # Admin user - always use LLM generation
                logger.info(f"🔍 ADMIN: Force LLM generation enabled, generating via LLM for {request.question_type.value}")
                return await self._generate_content_directly(request)
            else:
                # Normal user - try pool first, no LLM fallback
                logger.info(f"🔍 USER: Pool-only mode, attempting pool retrieval for {request.question_type.value}")
                return await self._generate_content_from_pool_only(request, user_id, user_metadata)
            
        except Exception as e:
            logger.error(f"Individual content generation failed: {e}")
            raise
    
    async def _generate_content_directly(self, request: QuestionGenerationRequest) -> Union[QuestionGenerationResponse, ReadingGenerationResponse, WritingGenerationResponse]:
        """Generate content directly via LLM for admin users."""
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        try:
            # Convert to internal request format
            ssat_request = self._convert_to_ssat_request(request)
            provider = request.provider.value if request.provider else "deepseek"  # Default to deepseek for admin generation
            
            # Extract custom examples if provided
            custom_examples = request.custom_examples if request.use_custom_examples else None
            
            # Handle each question type completely in its own branch to avoid union types
            if request.question_type == QuestionType.WRITING:
                # Generate writing prompts with metadata
                generation_result = generate_writing_prompts_with_metadata(ssat_request, llm=provider, custom_examples=custom_examples)
                writing_content = cast(List[GeneratorWritingPrompt], generation_result.content)
                training_example_ids = generation_result.training_example_ids
                actual_provider = generation_result.provider_used
                
                # Create metadata
                generation_time = time.time() - start_time
                metadata = GenerationMetadata(
                    generation_time=generation_time,
                    provider_used=actual_provider,
                    training_examples_count=len(training_example_ids),
                    training_example_ids=training_example_ids,
                    request_id=request_id
                )
                
                # Convert and return writing response
                api_prompts = [self._convert_writing_prompt_to_api_format(prompt) for prompt in writing_content]
                return WritingGenerationResponse(
                    prompts=cast(List[WritingPrompt], api_prompts),
                    metadata=metadata,
                    status="success",
                    count=len(api_prompts)
                )
                
            elif request.question_type == QuestionType.READING:
                # Generate reading passages with metadata
                generation_result = generate_reading_passages_with_metadata(ssat_request, llm=provider, custom_examples=custom_examples)
                reading_content = cast(List[GeneratorReadingPassage], generation_result.content)
                training_example_ids = generation_result.training_example_ids
                actual_provider = generation_result.provider_used
                
                # Create metadata
                generation_time = time.time() - start_time
                metadata = GenerationMetadata(
                    generation_time=generation_time,
                    provider_used=actual_provider,
                    training_examples_count=len(training_example_ids),
                    training_example_ids=training_example_ids,
                    request_id=request_id
                )
                
                # Convert and return reading response
                api_passages = [self._convert_reading_passage_to_api_format(passage) for passage in reading_content]
                total_questions = sum(len(passage["questions"]) for passage in api_passages)
                return ReadingGenerationResponse(
                    passages=cast(List[ReadingPassage], api_passages),
                    metadata=metadata,
                    status="success",
                    count=len(api_passages),
                    total_questions=total_questions
                )
                
            else:
                # For math/verbal questions, generate using functions that return training example IDs
                from app.content_generators import generate_standalone_questions_with_metadata
                generation_result = generate_standalone_questions_with_metadata(ssat_request, llm=provider, custom_examples=custom_examples)
                question_content = generation_result.content
                training_example_ids = generation_result.training_example_ids
                actual_provider = generation_result.provider_used
                
                # Create metadata
                generation_time = time.time() - start_time
                metadata = GenerationMetadata(
                    generation_time=generation_time,
                    provider_used=actual_provider,
                    training_examples_count=len(training_example_ids),
                    training_example_ids=training_example_ids,
                    request_id=request_id
                )
                
                # Convert and return question response
                api_questions = self._convert_questions_to_api_format(question_content)
                return QuestionGenerationResponse(
                    questions=cast(List[GeneratedQuestion], api_questions),
                    metadata=metadata,
                    status="success",
                    count=len(api_questions)
                )
                
        except Exception as e:
            logger.error(f"Direct content generation failed: {e}")
            raise
    
    async def _generate_content_from_pool_only(self, request: QuestionGenerationRequest, user_id: str, user_metadata: Optional[Dict[str, Any]] = None) -> Union[QuestionGenerationResponse, ReadingGenerationResponse, WritingGenerationResponse]:
        """Generate content from pool only for normal users (no LLM fallback)."""
        try:
            # Check daily limits first
            await self._check_daily_limits_for_pool(request, user_id, user_metadata)
            
            # Try to get content from existing AI-generated content pool
            from app.services.pool_selection_service import PoolSelectionService
            from app.services.pool_response_converter import PoolResponseConverter
            
            pool_service = PoolSelectionService()
            pool_converter = PoolResponseConverter()
            
            # Determine section mapping for pool lookup
            section_mapping = {
                "quantitative": "Quantitative",
                "analogy": "Verbal",
                "synonym": "Verbal"
            }
            
            # Determine subsection mapping for filtering
            subsection_mapping = {
                "analogy": "Analogies",
                "synonym": "Synonyms"
            }
            
            if request.question_type.value in ["quantitative", "analogy", "synonym"]:
                # For regular questions
                section_name = section_mapping.get(request.question_type.value, "Verbal")
                subsection_name = subsection_mapping.get(request.question_type.value)
                difficulty = request.difficulty.value if request.difficulty else None
                
                logger.info(f"🔍 POOL: Attempting pool retrieval for {request.question_type.value} questions")
                logger.info(f"🔍 POOL: Section={section_name}, Subsection={subsection_name}, Difficulty={difficulty}, Count={request.count}")
                
                pool_questions = await pool_service.get_unused_questions_for_user(
                    user_id=user_id,
                    section=section_name,
                    subsection=subsection_name,
                    count=request.count,
                    difficulty=difficulty
                )
                
                logger.info(f"🔍 POOL: Retrieved {len(pool_questions)} questions from pool, need {request.count}")
                
                if len(pool_questions) >= request.count:
                    logger.info(f"🔍 POOL: ✅ Found {len(pool_questions)} unused questions in pool")
                    
                    # Convert pool questions to API response format
                    pool_result = pool_converter.convert_questions_to_response(pool_questions[:request.count], request)
                    
                    # Mark questions as used with specific content type
                    question_ids = [q['id'] for q in pool_questions[:request.count]]
                    try:
                        await pool_service.mark_content_as_used(
                            user_id=user_id,
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
                    
                    # INCREMENT PHASE: Increment usage after successful pool delivery
                    try:
                        from app.services.database import get_database_connection
                        supabase = get_database_connection()
                        
                        # Map question type to section name for daily limits
                        section_mapping = {
                            "quantitative": "quantitative",
                            "analogy": "analogy", 
                            "synonym": "synonym",
                            "reading": "reading_passages",
                            "writing": "writing"
                        }
                        
                        section = section_mapping.get(request.question_type.value)
                        if section:
                            logger.info(f"🔍 DAILY LIMITS: Incrementing usage for user {user_id}, section '{section}' by {request.count}")
                            logger.info(f"🔍 DAILY LIMITS: Calling increment_user_daily_usage with p_user_id={user_id}, p_section='{section}', p_amount={request.count}")
                            
                            response = supabase.rpc(
                                'increment_user_daily_usage',
                                {
                                    'p_user_id': user_id,
                                    'p_section': section,
                                    'p_amount': request.count
                                }
                            ).execute()
                            
                            logger.info(f"🔍 DAILY LIMITS: Increment response: {response.data}")
                            logger.info(f"🔍 DAILY LIMITS: Response status: {response}")
                            
                            # Check if the increment actually worked by querying the current usage
                            try:
                                current_usage = supabase.rpc('get_or_create_user_daily_limits', {'p_user_id': user_id}).execute()
                                logger.info(f"🔍 DAILY LIMITS: Current usage after increment: {current_usage.data}")
                            except Exception as check_error:
                                logger.error(f"🔍 DAILY LIMITS: Error checking current usage: {check_error}")
                                
                        else:
                            logger.warning(f"🔍 DAILY LIMITS: Unknown section for question type {request.question_type.value}")
                            
                    except Exception as e:
                        logger.error(f"🔍 DAILY LIMITS: ❌ Error incrementing usage: {e}")
                        logger.error(f"🔍 DAILY LIMITS: ❌ Error type: {type(e)}")
                        logger.error(f"🔍 DAILY LIMITS: ❌ Error details: {str(e)}")
                        # Don't fail the request if increment fails
                    
                    return pool_result
                else:
                    # Not enough questions in pool
                    raise HTTPException(
                        status_code=404,
                        detail=f"Not enough {request.question_type.value} content available in pool. Please try again later or contact support."
                    )
                    
            elif request.question_type.value == "reading":
                # For reading sections
                logger.info(f"🔍 POOL: Attempting pool retrieval for reading content")
                
                difficulty = request.difficulty.value if request.difficulty else None
                
                pool_content = await pool_service.get_unused_reading_content_for_user(
                    user_id=user_id,
                    count=request.count,
                    difficulty=difficulty
                )
                
                logger.info(f"🔍 POOL: Retrieved {len(pool_content)} reading passages from pool, need {request.count}")
                
                if len(pool_content) >= request.count:
                    logger.info(f"🔍 POOL: ✅ Found {len(pool_content)} unused reading passages in pool")
                    
                    # Convert pool content to API response format
                    pool_result = pool_converter.convert_reading_to_response(pool_content[:request.count], request)
                    
                    # Mark reading passages as used
                    passage_ids = [p['passage_id'] for p in pool_content[:request.count]]
                    try:
                        await pool_service.mark_content_as_used(
                            user_id=user_id,
                            passage_ids=passage_ids,
                            usage_type="custom_section",
                            content_type="reading"
                        )
                        
                        logger.info(f"🔍 POOL: ✅ Successfully delivered {request.count} reading passages from pool")
                        logger.info(f"🔍 POOL DEBUG: Marked passages as used: {[pid[:8] + '...' for pid in passage_ids]}")
                    except Exception as mark_error:
                        # If marking fails, return service unavailable error
                        if "duplicate key value violates unique constraint" in str(mark_error):
                            logger.warning(f"🔍 POOL: ⚠️ Pool passages already used, returning service unavailable error")
                            raise HTTPException(
                                status_code=503,
                                detail="Service temporarily unavailable. Please try again in a few minutes."
                            )
                        else:
                            # Re-raise other errors
                            raise mark_error
                    
                    # INCREMENT PHASE: Increment usage after successful pool delivery
                    try:
                        from app.services.database import get_database_connection
                        supabase = get_database_connection()
                        
                        logger.info(f"🔍 DAILY LIMITS: Incrementing usage for user {user_id}, section 'reading_passages' by {request.count}")
                        logger.info(f"🔍 DAILY LIMITS: Calling increment_user_daily_usage with p_user_id={user_id}, p_section='reading_passages', p_amount={request.count}")
                        
                        response = supabase.rpc(
                            'increment_user_daily_usage',
                            {
                                'p_user_id': user_id,
                                'p_section': 'reading_passages',
                                'p_amount': request.count
                            }
                        ).execute()
                        
                        logger.info(f"🔍 DAILY LIMITS: Increment response: {response.data}")
                        logger.info(f"🔍 DAILY LIMITS: Response status: {response}")
                        
                        # Check if the increment actually worked by querying the current usage
                        try:
                            current_usage = supabase.rpc('get_or_create_user_daily_limits', {'p_user_id': user_id}).execute()
                            logger.info(f"🔍 DAILY LIMITS: Current usage after increment: {current_usage.data}")
                        except Exception as check_error:
                            logger.error(f"🔍 DAILY LIMITS: Error checking current usage: {check_error}")
                            
                    except Exception as e:
                        logger.error(f"🔍 DAILY LIMITS: ❌ Error incrementing usage: {e}")
                        logger.error(f"🔍 DAILY LIMITS: ❌ Error type: {type(e)}")
                        logger.error(f"🔍 DAILY LIMITS: ❌ Error details: {str(e)}")
                        # Don't fail the request if increment fails
                    
                    return pool_result
                else:
                    # Not enough reading content in pool
                    raise HTTPException(
                        status_code=404,
                        detail=f"Not enough reading content available in pool. Please try again later or contact support."
                    )
                    
            elif request.question_type.value == "writing":
                # For writing sections
                logger.info(f"🔍 POOL: Attempting pool retrieval for writing prompts")
                
                pool_prompts = await pool_service.get_unused_writing_prompts_for_user(
                    user_id=user_id,
                    count=request.count
                )
                
                logger.info(f"🔍 POOL: Retrieved {len(pool_prompts)} writing prompts from pool, need {request.count}")
                
                if len(pool_prompts) >= request.count:
                    logger.info(f"🔍 POOL: ✅ Found {len(pool_prompts)} unused writing prompts in pool")
                    
                    # Convert pool content to API response format
                    pool_result = pool_converter.convert_writing_to_response(pool_prompts[:request.count], request)
                    
                    # Mark writing prompts as used
                    prompt_ids = [p['id'] for p in pool_prompts[:request.count]]
                    try:
                        await pool_service.mark_content_as_used(
                            user_id=user_id,
                            writing_prompt_ids=prompt_ids,
                            usage_type="custom_section",
                            content_type="writing"
                        )
                        
                        logger.info(f"🔍 POOL: ✅ Successfully delivered {request.count} writing prompts from pool")
                        logger.info(f"🔍 POOL DEBUG: Marked prompts as used: {[pid[:8] + '...' for pid in prompt_ids]}")
                    except Exception as mark_error:
                        # If marking fails, return service unavailable error
                        if "duplicate key value violates unique constraint" in str(mark_error):
                            logger.warning(f"🔍 POOL: ⚠️ Pool prompts already used, returning service unavailable error")
                            raise HTTPException(
                                status_code=503,
                                detail="Service temporarily unavailable. Please try again in a few minutes."
                            )
                        else:
                            # Re-raise other errors
                            raise mark_error
                    
                    # INCREMENT PHASE: Increment usage after successful pool delivery
                    try:
                        from app.services.database import get_database_connection
                        supabase = get_database_connection()
                        
                        logger.info(f"🔍 DAILY LIMITS: Incrementing usage for user {user_id}, section 'writing' by {request.count}")
                        logger.info(f"🔍 DAILY LIMITS: Calling increment_user_daily_usage with p_user_id={user_id}, p_section='writing', p_amount={request.count}")
                        
                        response = supabase.rpc(
                            'increment_user_daily_usage',
                            {
                                'p_user_id': user_id,
                                'p_section': 'writing',
                                'p_amount': request.count
                            }
                        ).execute()
                        
                        logger.info(f"🔍 DAILY LIMITS: Increment response: {response.data}")
                        logger.info(f"🔍 DAILY LIMITS: Response status: {response}")
                        
                        # Check if the increment actually worked by querying the current usage
                        try:
                            current_usage = supabase.rpc('get_or_create_user_daily_limits', {'p_user_id': user_id}).execute()
                            logger.info(f"🔍 DAILY LIMITS: Current usage after increment: {current_usage.data}")
                        except Exception as check_error:
                            logger.error(f"🔍 DAILY LIMITS: Error checking current usage: {check_error}")
                            
                    except Exception as e:
                        logger.error(f"🔍 DAILY LIMITS: ❌ Error incrementing usage: {e}")
                        logger.error(f"🔍 DAILY LIMITS: ❌ Error type: {type(e)}")
                        logger.error(f"🔍 DAILY LIMITS: ❌ Error details: {str(e)}")
                        # Don't fail the request if increment fails
                    
                    return pool_result
                else:
                    # Not enough writing prompts in pool
                    raise HTTPException(
                        status_code=404,
                        detail=f"Not enough writing prompts available in pool. Please try again later or contact support."
                    )
            
            else:
                raise ValueError(f"Unsupported question type: {request.question_type.value}")
                
        except Exception as e:
            logger.error(f"Pool-only content generation failed: {e}")
            raise
    
    async def _convert_section_to_response(
        self, 
        section_result: Any, 
        original_request: QuestionGenerationRequest
    ) -> Union[QuestionGenerationResponse, ReadingGenerationResponse, WritingGenerationResponse]:
        """Convert section result from _generate_single_section_background to API response format."""
        try:
            # Extract the section data from the result
            if hasattr(section_result, 'model_dump'):
                section_data = section_result.model_dump()
            else:
                section_data = section_result.__dict__ if hasattr(section_result, '__dict__') else section_result
            
            # Handle different content types
            if original_request.question_type.value in ["quantitative", "analogy", "synonym"]:
                # For questions
                questions = section_data.get('questions', [])
                metadata = GenerationMetadata(
                    generation_time=0.0,  # Pool access is instant
                    provider_used="pool",
                    training_examples_count=0,
                    training_example_ids=[],
                    request_id=str(uuid.uuid4())
                )
                
                return QuestionGenerationResponse(
                    questions=questions,
                    metadata=metadata,
                    status="success",
                    count=len(questions)
                )
                
            elif original_request.question_type.value == "reading":
                # For reading passages
                passages = section_data.get('passages', [])
                total_questions = sum(len(passage.get("questions", [])) for passage in passages)
                metadata = GenerationMetadata(
                    generation_time=0.0,  # Pool access is instant
                    provider_used="pool",
                    training_examples_count=0,
                    training_example_ids=[],
                    request_id=str(uuid.uuid4())
                )
                
                return ReadingGenerationResponse(
                    passages=passages,
                    metadata=metadata,
                    status="success",
                    count=len(passages),
                    total_questions=total_questions
                )
                
            elif original_request.question_type.value == "writing":
                # For writing prompts
                prompts = section_data.get('prompts', [])
                metadata = GenerationMetadata(
                    generation_time=0.0,  # Pool access is instant
                    provider_used="pool",
                    training_examples_count=0,
                    training_example_ids=[],
                    request_id=str(uuid.uuid4())
                )
                
                return WritingGenerationResponse(
                    prompts=prompts,
                    metadata=metadata,
                    status="success",
                    count=len(prompts)
                )
            
            else:
                raise ValueError(f"Unsupported question type: {original_request.question_type.value}")
                
        except Exception as e:
            logger.error(f"Failed to convert section to response: {e}")
            raise
    
    async def generate_complete_test_async(
        self, 
        request: CompleteTestRequest, 
        user_id: str,
        force_llm_generation: bool = False,
        user_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Start generating a complete SSAT practice test asynchronously."""
        try:
            # Use the real job manager for complete test generation
            from app.services.job_manager import job_manager
            
            logger.info(f"Starting complete test generation for user {user_id} (force_llm={force_llm_generation})")
            
            # Create job with request data and user ID  
            job_id = job_manager.create_job({
                "difficulty": request.difficulty.value,
                "provider": request.provider.value if request.provider else None,
                "include_sections": [section.value for section in request.include_sections],
                "custom_counts": request.custom_counts,
                "is_official_format": request.is_official_format,
                "force_llm_generation": force_llm_generation,  # Add flag to job data
                "user_role": user_metadata.get('role', 'user') if user_metadata else "user",  # Store user role for background processing
                "user_metadata": user_metadata  # Store full user metadata for daily limit checking
            }, user_id)
            
            # Start background generation task
            import asyncio
            asyncio.create_task(self._generate_test_sections_background(job_id, request, force_llm_generation))
            
            return {
                "job_id": job_id,
                "status": "started", 
                "message": "Complete test generation started",
                "estimated_time_minutes": 10,
                "sections": [section.value for section in request.include_sections]
            }
            
        except Exception as e:
            logger.error(f"Failed to start complete test generation: {e}")
            raise
    
    async def get_job_status(self, job_id: str, user_id: str) -> Dict[str, Any]:
        """Get the status of a background generation job."""
        try:
            # Use the real job manager to get status
            from app.services.job_manager import job_manager
            
            # Get real job status from job manager with user authorization
            status = job_manager.get_job_status(job_id, user_id)
            
            if status is None:
                raise ValueError(f"Job {job_id} not found")
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get job status for {job_id}: {e}")
            raise
    
    async def get_topic_suggestions(self, question_type: str) -> List[str]:
        """Get suggested topics for a given question type."""
        try:
            # Use the real generator's topic suggestion logic
            if self.generator is None:
                logger.error("Generator not initialized for topic suggestions")
                raise ValueError("Generator service not properly initialized")
            
            # Delegate to the generator's topic suggestion method
            if hasattr(self.generator, 'get_topic_suggestions'):
                return await self.generator.get_topic_suggestions(question_type)
            else:
                # Fallback to static suggestions if generator doesn't have the method
                logger.warning("Generator doesn't have get_topic_suggestions method, using fallback")
                suggestions_map = {
                    "quantitative": ["Fractions", "Decimals", "Geometry", "Word Problems", "Algebra Basics"],
                    "analogy": ["Relationships", "Synonyms", "Categories", "Function"],
                    "synonym": ["Elementary Vocabulary", "Academic Terms", "Common Words"],
                    "reading": ["Fiction", "Science", "History", "Biography"],
                    "writing": ["Descriptive", "Narrative", "Creative", "Personal Experience"]
                }
                return suggestions_map.get(question_type, [])
            
        except Exception as e:
            logger.error(f"Failed to get topic suggestions: {e}")
            raise
    
    # Content Generation Methods (from UnifiedContentService)
    
    def _convert_questions_to_api_format(self, questions: List) -> List[Dict[str, Any]]:
        """Convert Question objects to API format."""
        api_questions = []
        for question in questions:
            api_question = {
                "id": question.id,
                "question_type": question.question_type.value,
                "difficulty": question.difficulty.value,
                "text": question.text,
                "options": [
                    {"letter": opt.letter, "text": opt.text} 
                    for opt in question.options
                ],
                "correct_answer": question.correct_answer,
                "explanation": question.explanation,
                "cognitive_level": question.cognitive_level,
                "tags": question.tags,
                "metadata": question.metadata
            }
            
            # Only include visual_description if it has meaningful content
            if question.visual_description and question.visual_description.strip() and \
               question.visual_description.lower() not in ["none", "no visual elements", "no visual elements required"]:
                api_question["visual_description"] = question.visual_description
            
            # Include subsection if provided by AI
            if hasattr(question, 'subsection') and question.subsection:
                api_question["subsection"] = question.subsection
            api_questions.append(api_question)
        
        return api_questions
    
    def _convert_reading_passage_to_api_format(self, passage: GeneratorReadingPassage) -> Dict[str, Any]:
        """Convert ReadingPassage object to API format."""
        return {
            "id": passage.id,
            "title": passage.title,
            "text": passage.text,
            "passage_type": passage.passage_type,
            "grade_level": passage.grade_level,
            "topic": passage.topic,
            "questions": self._convert_questions_to_api_format(passage.questions),
            "metadata": passage.metadata
        }
    
    def _convert_writing_prompt_to_api_format(self, prompt: GeneratorWritingPrompt) -> Dict[str, Any]:
        """Convert WritingPrompt object to API format."""
        data = {
            "prompt_text": prompt.prompt_text,
            "instructions": prompt.instructions,
            "grade_level": prompt.grade_level,
            "prompt_type": prompt.prompt_type,
            "tags": prompt.tags,  # Include AI-generated tags
            "subsection": prompt.subsection  # Include AI-generated subsection
        }
        
        # Only include visual_description if it has meaningful content
        if prompt.visual_description and prompt.visual_description.strip():
            data["visual_description"] = prompt.visual_description
        
        return data
    
    async def _generate_content_on_demand(self, request: QuestionGenerationRequest) -> Union[QuestionGenerationResponse, ReadingGenerationResponse, WritingGenerationResponse]:
        """
        Generate content based on request type.
        
        Routes to appropriate generator and returns type-specific response.
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        try:
            # Convert to internal request format
            ssat_request = self._convert_to_ssat_request(request)
            provider = request.provider.value if request.provider else None
            
            # Extract custom examples if provided
            custom_examples = request.custom_examples if request.use_custom_examples else None
            
            # Handle each question type completely in its own branch to avoid union types
            if request.question_type == QuestionType.WRITING:
                # Generate writing prompts with metadata
                generation_result = generate_writing_prompts_with_metadata(ssat_request, llm=provider, custom_examples=custom_examples)
                writing_content = cast(List[GeneratorWritingPrompt], generation_result.content)
                training_example_ids = generation_result.training_example_ids
                actual_provider = generation_result.provider_used
                
                # Create metadata
                generation_time = time.time() - start_time
                metadata = GenerationMetadata(
                    generation_time=generation_time,
                    provider_used=actual_provider,
                    training_examples_count=len(training_example_ids),
                    training_example_ids=training_example_ids,
                    request_id=request_id
                )
                
                # Convert and return writing response
                api_prompts = [self._convert_writing_prompt_to_api_format(prompt) for prompt in writing_content]
                return WritingGenerationResponse(
                    prompts=cast(List[WritingPrompt], api_prompts),
                    metadata=metadata,
                    status="success",
                    count=len(api_prompts)
                )
                
            elif request.question_type == QuestionType.READING:
                # Generate reading passages with metadata
                generation_result = generate_reading_passages_with_metadata(ssat_request, llm=provider, custom_examples=custom_examples)
                reading_content = cast(List[GeneratorReadingPassage], generation_result.content)
                training_example_ids = generation_result.training_example_ids
                actual_provider = generation_result.provider_used
                
                # Create metadata
                generation_time = time.time() - start_time
                metadata = GenerationMetadata(
                    generation_time=generation_time,
                    provider_used=actual_provider,
                    training_examples_count=len(training_example_ids),
                    training_example_ids=training_example_ids,
                    request_id=request_id
                )
                
                # Convert and return reading response
                api_passages = [self._convert_reading_passage_to_api_format(passage) for passage in reading_content]
                total_questions = sum(len(passage["questions"]) for passage in api_passages)
                return ReadingGenerationResponse(
                    passages=cast(List[ReadingPassage], api_passages),
                    metadata=metadata,
                    status="success",
                    count=len(api_passages),
                    total_questions=total_questions
                )
                
            else:
                # For math/verbal questions, generate using functions that return training example IDs
                from app.content_generators import generate_standalone_questions_with_metadata
                generation_result = generate_standalone_questions_with_metadata(ssat_request, llm=provider, custom_examples=custom_examples)
                question_content = generation_result.content
                training_example_ids = generation_result.training_example_ids
                actual_provider = generation_result.provider_used
                
                # Create metadata
                generation_time = time.time() - start_time
                metadata = GenerationMetadata(
                    generation_time=generation_time,
                    provider_used=actual_provider,
                    training_examples_count=len(training_example_ids),
                    training_example_ids=training_example_ids,
                    request_id=request_id
                )
                
                # Convert and return question response
                api_questions = self._convert_questions_to_api_format(question_content)
                return QuestionGenerationResponse(
                    questions=cast(List[GeneratedQuestion], api_questions),
                    metadata=metadata,
                    status="success",
                    count=len(api_questions)
                )
                
        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            raise e

    # Section Generation Methods (Phase 2 Implementation)
    
    async def _generate_writing_section(self, difficulty: DifficultyLevel) -> WritingSection:
        """Generate a writing section with prompts."""
        try:
            # Create request for writing prompts
            request = QuestionRequest(
                question_type=QuestionType.WRITING,
                difficulty=difficulty,
                count=1,
                level="elementary"
            )
            
            # Generate writing prompts using content generators
            generation_result = generate_writing_prompts_with_metadata(request, llm=None)
            writing_prompts = generation_result.content
            
            if not writing_prompts:
                raise ValueError("Failed to generate writing prompts")
            
            # Convert to API format
            prompt_data = self._convert_writing_prompt_to_api_format(writing_prompts[0])
            
            return WritingSection(
                prompt=prompt_data,
                instructions=self._get_section_instructions(QuestionType.WRITING),
                metadata={
                    "provider_used": generation_result.provider_used,
                    "training_examples_count": len(generation_result.training_example_ids),
                    "training_example_ids": generation_result.training_example_ids
                }
            )
            
        except Exception as e:
            logger.error(f"Writing section generation failed: {e}")
            raise
    
    async def _generate_reading_section(
        self, 
        difficulty: DifficultyLevel, 
        num_passages: int, 
        provider: Optional[Any], 
        use_async: bool = False, 
        is_official_format: bool = False, 
        topic: Optional[str] = None
    ) -> ReadingSection:
        """Generate a reading section with passages and questions."""
        try:
            # Create request for reading passages
            request = QuestionRequest(
                question_type=QuestionType.READING,
                difficulty=difficulty,
                count=num_passages,
                level="elementary",
                topic=topic,
                is_official_format=is_official_format
            )
            
            # Generate reading passages using content generators
            if use_async:
                generation_result = await self._generate_reading_passages_async(request, provider, is_official_format, topic)
            else:
                generation_result = generate_reading_passages_with_metadata(request, llm=provider.value if provider else None)
            
            reading_passages = generation_result.content
            
            if not reading_passages:
                raise ValueError("Failed to generate reading passages")
            
            # Convert to API format
            passages_data = [self._convert_reading_passage_to_api_format(passage) for passage in reading_passages]
            
            return ReadingSection(
                passages=passages_data,
                instructions=self._get_section_instructions(QuestionType.READING),
                metadata={
                    "provider_used": generation_result.provider_used,
                    "training_examples_count": len(generation_result.training_example_ids),
                    "training_example_ids": generation_result.training_example_ids
                }
            )
            
        except Exception as e:
            logger.error(f"Reading section generation failed: {e}")
            raise

    async def _generate_reading_passages_async(
        self, 
        request: QuestionRequest, 
        provider: Optional[Any], 
        is_official_format: bool, 
        topic: Optional[str]
    ) -> "GenerationResult":
        """Generate reading passages asynchronously (matching working version)."""
        from app.generator import generate_reading_passages_async, SSATGenerator
        from app.content_generators import GenerationResult, ReadingPassage as GeneratorReadingPassage
        
        # Get training examples metadata first (matching working version)
        generator = SSATGenerator()
        training_examples = generator.get_reading_training_examples(topic=topic)
        training_example_ids = [ex.get('question_id', '') for ex in training_examples if ex.get('question_id')]
        
        logger.info(f"📚 DEBUG: Reading section will use {len(training_example_ids)} training examples: {training_example_ids}")
        
        # Use multiple calls for full test generation (quality over efficiency)
        use_single_call = False
        provider_name = provider.value if provider else None
        
        # For admin complete tests (is_official_format), use diverse examples; otherwise use pre-fetched
        if is_official_format:
            # Admin complete test: Don't pass pre-fetched examples to ensure diverse content
            results = await generate_reading_passages_async(request, llm=provider_name, use_single_call=use_single_call, training_examples=None)
        else:
            # Regular generation: Use pre-fetched examples for consistency
            results = await generate_reading_passages_async(request, llm=provider_name, use_single_call=use_single_call, training_examples=training_examples)
        
        # Convert results to ReadingPassage objects (matching working version)
        passages = []
        for i, result in enumerate(results):
            passage_data = result["passage"]
            questions = result["questions"]
            
            # Create passage object using the generator's ReadingPassage class
            passage_dict = {
                "text": passage_data,
                "passage_type": result.get("passage_type", "General"),
                "title": f"Passage {i+1}",
                "topic": "Elementary Reading"
            }
            passage = GeneratorReadingPassage(passage_dict, questions)
            passages.append(passage)
        
        # Create GenerationResult to match expected format
        return GenerationResult(
            content=passages,
            training_example_ids=training_example_ids,
            provider_used="auto-selected"
        )
    
    async def _generate_quantitative_section_official_5_calls(
        self, 
        difficulty: DifficultyLevel, 
        total_count: int, 
        provider: Optional[Any], 
        use_async: bool = False
    ) -> QuantitativeSection:
        """Generate quantitative section using domain distribution."""
        try:
            # Get domain distribution for quantitative questions
            domain_distribution = self._get_quantitative_domain_distribution(difficulty, total_count)
            
            all_questions = []
            training_example_ids = []
            providers_used = set()
            
            # Generate questions for each domain
            for domain, count in domain_distribution.items():
                if count > 0:
                    # Create request for this domain
                    request = QuestionRequest(
                        question_type=QuestionType.QUANTITATIVE,
                        difficulty=difficulty,
                        count=count,
                        level="elementary",
                        topic=domain
                    )
                    
                    # Generate questions for this domain
                    generation_result = generate_standalone_questions_with_metadata(
                        request, 
                        llm=provider.value if provider else None
                    )
                    
                    domain_questions = generation_result.content
                    if domain_questions:
                        all_questions.extend(domain_questions)
                        training_example_ids.extend(generation_result.training_example_ids)
                        if generation_result.provider_used:
                            providers_used.add(generation_result.provider_used)
            
            if not all_questions:
                raise ValueError("Failed to generate quantitative questions")
            
            # Convert to API format
            questions_data = self._convert_questions_to_api_format(all_questions)
            
            return QuantitativeSection(
                questions=questions_data,
                instructions=self._get_section_instructions(QuestionType.QUANTITATIVE),
                metadata={
                    "provider_used": list(providers_used)[0] if providers_used else None,
                    "training_examples_count": len(training_example_ids),
                    "training_example_ids": training_example_ids,
                    "domain_distribution": domain_distribution
                }
            )
            
        except Exception as e:
            logger.error(f"Quantitative section generation failed: {e}")
            raise
    
    async def _generate_analogy_section(
        self, 
        difficulty: DifficultyLevel, 
        count: int, 
        provider: Optional[Any], 
        use_async: bool = False
    ) -> AnalogySection:
        """Generate analogy section."""
        try:
            # Create request for analogy questions
            request = QuestionRequest(
                question_type=QuestionType.ANALOGY,
                difficulty=difficulty,
                count=count,
                level="elementary"
            )
            
            # Generate analogy questions using content generators
            generation_result = generate_standalone_questions_with_metadata(
                request, 
                llm=provider.value if provider else None
            )
            analogy_questions = generation_result.content
            
            if not analogy_questions:
                raise ValueError("Failed to generate analogy questions")
            
            # Convert to API format
            questions_data = self._convert_questions_to_api_format(analogy_questions)
            
            return AnalogySection(
                questions=questions_data,
                instructions=self._get_section_instructions(QuestionType.ANALOGY),
                metadata={
                    "provider_used": generation_result.provider_used,
                    "training_examples_count": len(generation_result.training_example_ids),
                    "training_example_ids": generation_result.training_example_ids
                }
            )
            
        except Exception as e:
            logger.error(f"Analogy section generation failed: {e}")
            raise
    
    async def _generate_synonym_section(
        self, 
        difficulty: DifficultyLevel, 
        count: int, 
        provider: Optional[Any], 
        use_async: bool = False
    ) -> SynonymSection:
        """Generate synonym section."""
        try:
            # Create request for synonym questions
            request = QuestionRequest(
                question_type=QuestionType.SYNONYM,
                difficulty=difficulty,
                count=count,
                level="elementary"
            )
            
            # Generate synonym questions using content generators
            generation_result = generate_standalone_questions_with_metadata(
                request, 
                llm=provider.value if provider else None
            )
            synonym_questions = generation_result.content
            
            if not synonym_questions:
                raise ValueError("Failed to generate synonym questions")
            
            # Convert to API format
            questions_data = self._convert_questions_to_api_format(synonym_questions)
            
            return SynonymSection(
                questions=questions_data,
                instructions=self._get_section_instructions(QuestionType.SYNONYM),
                metadata={
                    "provider_used": generation_result.provider_used,
                    "training_examples_count": len(generation_result.training_example_ids),
                    "training_example_ids": generation_result.training_example_ids
                }
            )
            
        except Exception as e:
            logger.error(f"Synonym section generation failed: {e}")
            raise

    # Domain-Specific Prompt Builders (Phase 2 Implementation)
    
    def _get_section_instructions(self, section_type: QuestionType) -> str:
        """Get instructions for a specific test section."""
        instructions = {
            QuestionType.QUANTITATIVE: "Solve each problem and choose the best answer. You may use scratch paper for calculations.",
            QuestionType.VERBAL: "Choose the word that best completes each sentence or answers each question.",
            QuestionType.READING: "Read each passage carefully and answer the questions that follow.",
            QuestionType.WRITING: "Write a short essay in response to the prompt. Use proper grammar and organization.",
            QuestionType.ANALOGY: "Choose the pair of words that has the same relationship as the given pair.",
            QuestionType.SYNONYM: "Choose the word that means the same or nearly the same as the given word."
        }
        return instructions.get(section_type, "Answer all questions to the best of your ability.")
    
    def _get_quantitative_domain_distribution(self, difficulty: DifficultyLevel, total_count: int) -> Dict[str, int]:
        """Get domain distribution for quantitative questions based on difficulty using predefined subsections."""
        
        if difficulty == DifficultyLevel.EASY:
            # Focus on basic operations for easy level
            return {
                "Number Sense": max(1, total_count // 3),
                "Arithmetic": max(1, total_count // 3),
                "Fractions": max(1, total_count // 4),
                "Measurement": max(1, total_count // 6)
            }
        elif difficulty == DifficultyLevel.MEDIUM:
            # Balanced distribution for medium level
            return {
                "Number Sense": max(1, total_count // 5),
                "Arithmetic": max(1, total_count // 5),
                "Fractions": max(1, total_count // 5),
                "Algebra": max(1, total_count // 5),
                "Area": max(1, total_count // 5)
            }
        else:  # HARD
            # More advanced topics for hard level
            return {
                "Algebra": max(1, total_count // 3),
                "Area": max(1, total_count // 4),
                "Fractions": max(1, total_count // 4),
                "Percentages": max(1, total_count // 6),
                "Probability": max(1, total_count // 6)
            }
    
    
    async def _generate_test_sections_background(self, job_id: str, request: CompleteTestRequest, force_llm_generation: bool = False):
        """Background task to generate test sections in parallel."""
        from app.services.job_manager import job_manager, JobStatus, SectionStatus
        
        providers_used = set()
        total_questions = 0
        
        try:
            job_manager.update_job_status(job_id, JobStatus.RUNNING)
            
            # Get user metadata from job data
            job = job_manager.get_job(job_id)
            user_metadata = job.request_data.get('user_metadata') if job else None
            
            # Create tasks for all sections to run in parallel
            section_tasks = []
            for section_type in request.include_sections:
                task = asyncio.create_task(
                    self._generate_single_section_background(job_id, section_type, request, force_llm_generation, user_metadata)
                )
                section_tasks.append(task)
            
            # Wait for all sections to complete (or fail)
            results = await asyncio.gather(*section_tasks, return_exceptions=True)
            
            # Log any exceptions that occurred during section generation
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    section_type = request.include_sections[i].value
                    logger.error(f"❌ Section {section_type} failed with exception: {result}")
            
            # Check final job status
            job = job_manager.get_job(job_id)
            if job and job.completed_sections > 0:  # Allow partial success
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
                            if 'questions' in section_data:
                                section_questions = len(section_data['questions'])
                                total_questions += section_questions
                        elif section_type == 'reading':
                            if 'passages' in section_data:
                                for passage in section_data['passages']:
                                    if 'questions' in passage:
                                        section_questions += len(passage['questions'])
                                total_questions += section_questions
                        elif section_type == 'writing':
                            section_questions = 1
                            total_questions += section_questions
                        
                        logger.info(f"📊 DEBUG: Section {section_type}: {section_questions} questions")
                        
                        # Track provider used
                        if 'metadata' in section_data and 'provider_used' in section_data['metadata']:
                            provider = section_data['metadata']['provider_used']
                            if provider:
                                providers_used.add(provider)
                
                logger.info(f"📊 DEBUG: Session {job_id} completed with {total_questions} total questions")
                logger.info(f"📊 DEBUG: Providers used: {list(providers_used)}")
                logger.info(f"Complete test job {job_id}: {job.completed_sections}/{job.total_sections} sections completed, {total_questions} questions")
                
            else:
                # No sections completed - mark as failed
                job_manager.update_job_status(job_id, JobStatus.FAILED, "No sections could be completed")
                logger.error(f"❌ Complete test job {job_id}: No sections completed - marking as failed")
        
        except Exception as e:
            logger.error(f"Background generation failed for job {job_id}: {e}")
            job_manager.update_job_status(job_id, JobStatus.FAILED, str(e))
    
    async def _generate_single_section_background(self, job_id: str, section_type, request: CompleteTestRequest, force_llm_generation: bool = False, user_metadata: Optional[Dict[str, Any]] = None):
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
                "quantitative": 1, "analogy": 1, "synonym": 1, "reading": 1, "writing": 1
            }.get(section_type.value, 5))
            
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
            
            # Check daily limits before attempting pool retrieval (only for non-admin users)
            if not force_llm_generation:
                await self._check_daily_limits_for_background_section(job.user_id, section_type.value, section_count, user_metadata)
            
            # Determine section mapping for pool lookup
            section_mapping = {
                "quantitative": "Quantitative",
                "analogy": "Verbal",
                "synonym": "Verbal"
            }
            
            # Determine subsection mapping for filtering
            subsection_mapping = {
                "analogy": "Analogies",
                "synonym": "Synonyms"
            }
            
            pool_result = None
            
            # Skip pool retrieval if force_llm_generation is True
            if force_llm_generation:
                logger.info(f"🔍 ADMIN: Force LLM generation enabled, skipping pool for {section_type.value}")
            elif section_type.value in ["quantitative", "analogy", "synonym"]:
                # For regular questions
                section_name = section_mapping.get(section_type.value, "Verbal")
                subsection_name = subsection_mapping.get(section_type.value)
                difficulty = request.difficulty.value if request.difficulty else None
                
                logger.info(f"🔍 POOL DEBUG: Attempting pool retrieval for {section_type.value} questions")
                logger.info(f"🔍 POOL DEBUG: Section={section_name}, Subsection={subsection_name}, Difficulty={difficulty}, Count={section_count}")
                
                pool_questions = await pool_service.get_unused_questions_for_user(
                    user_id=job.user_id,
                    section=section_name,
                    subsection=subsection_name,
                    count=section_count,
                    difficulty=difficulty
                )
                
                logger.info(f"🔍 POOL DEBUG: Retrieved {len(pool_questions)} questions from pool, need {section_count}")
                
                if len(pool_questions) >= section_count:
                    logger.info(f"🔍 POOL: ✅ Found {len(pool_questions)} unused questions in pool for user {job.user_id}")
                    
                    # Convert pool questions to API response format
                    pool_result = pool_converter.convert_questions_to_section(pool_questions[:section_count], section_type.value)
                    
                    # Mark questions as used
                    question_ids = [q['id'] for q in pool_questions[:section_count]]
                    try:
                        await pool_service.mark_content_as_used(
                            user_id=job.user_id,
                            question_ids=question_ids,
                            usage_type="complete_test",
                            content_type=section_type.value
                        )
                        
                        logger.info(f"🔍 POOL: ✅ Marked {len(question_ids)} questions as used")
                        
                        # INCREMENT PHASE: Increment usage after successful pool delivery
                        try:
                            from app.services.database import get_database_connection
                            supabase = get_database_connection()
                            
                            # Map question type to section name for daily limits
                            section_mapping = {
                                "quantitative": "quantitative",
                                "analogy": "analogy", 
                                "synonym": "synonym",
                                "reading": "reading_passages",
                                "writing": "writing"
                            }
                            
                            section = section_mapping.get(section_type.value)
                            if section:
                                logger.info(f"🔍 DAILY LIMITS: Incrementing usage for user {job.user_id}, section '{section}' by {section_count}")
                                logger.info(f"🔍 DAILY LIMITS: Calling increment_user_daily_usage with p_user_id={job.user_id}, p_section='{section}', p_amount={section_count}")
                                
                                response = supabase.rpc(
                                    'increment_user_daily_usage',
                                    {
                                        'p_user_id': job.user_id,
                                        'p_section': section,
                                        'p_amount': section_count
                                    }
                                ).execute()
                                
                                logger.info(f"🔍 DAILY LIMITS: Increment response: {response.data}")
                                logger.info(f"🔍 DAILY LIMITS: Response status: {response}")
                                
                                # Check if the increment actually worked by querying the current usage
                                try:
                                    current_usage = supabase.rpc('get_or_create_user_daily_limits', {'p_user_id': job.user_id}).execute()
                                    logger.info(f"🔍 DAILY LIMITS: Current usage after increment: {current_usage.data}")
                                except Exception as check_error:
                                    logger.error(f"🔍 DAILY LIMITS: Error checking current usage: {check_error}")
                                    
                            else:
                                logger.warning(f"🔍 DAILY LIMITS: Unknown section for question type {section_type.value}")
                                
                        except Exception as e:
                            logger.error(f"🔍 DAILY LIMITS: ❌ Error incrementing usage: {e}")
                            logger.error(f"🔍 DAILY LIMITS: ❌ Error type: {type(e)}")
                            logger.error(f"🔍 DAILY LIMITS: ❌ Error details: {str(e)}")
                            # Don't fail the request if increment fails
                            
                    except Exception as mark_error:
                        if "duplicate key value violates unique constraint" in str(mark_error):
                            logger.warning(f"🔍 POOL: ⚠️ Pool questions already used, failing section {section_type.value}")
                            job_manager.update_section_progress(job_id, section_type.value, 100, "Service temporarily unavailable")
                            job_manager.fail_section(job_id, section_type.value, "Service temporarily unavailable. Please try again in a few minutes.")
                            return
                        else:
                            raise mark_error
                elif len(pool_questions) > 0:
                    # Pool has some questions but not enough - use what we have
                    logger.info(f"🔍 POOL: ⚠️ Pool has {len(pool_questions)} questions, need {section_count}")
                    logger.info(f"🔍 POOL: ✅ Using available {len(pool_questions)} questions from pool")
                    
                    # Use available pool content
                    pool_result = pool_converter.convert_questions_to_section(pool_questions, section_type.value)
                    
                    # Mark questions as used
                    try:
                        question_ids = [item['id'] for item in pool_questions]
                        await pool_service.mark_content_as_used(
                            user_id=job.user_id,
                            question_ids=question_ids,
                            usage_type="complete_test"
                        )
                        logger.info(f"🔍 POOL: ✅ Marked {len(question_ids)} questions as used")
                    except Exception as mark_error:
                        if "duplicate key value violates unique constraint" in str(mark_error):
                            logger.warning(f"🔍 POOL: ⚠️ Pool questions already used")
                            pool_result = None
                        else:
                            logger.error(f"🔍 POOL: ❌ Error marking questions as used: {mark_error}")
                            # Continue without marking as used rather than failing
                else:
                    logger.info(f"🔍 POOL: ❌ No questions available in pool for {section_type.value}, will generate {section_count} on-demand")
            
            elif section_type.value == "reading" and not force_llm_generation:
                # For reading sections
                logger.info(f"🔍 POOL DEBUG: Attempting pool retrieval for reading content")
                logger.info(f"🔍 POOL DEBUG: Passages requested={section_count}")
                
                difficulty = request.difficulty.value if request.difficulty else None
                
                pool_content = await pool_service.get_unused_reading_content_for_user(
                    user_id=job.user_id,
                    count=section_count,
                    difficulty=difficulty
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
                        
                        # INCREMENT PHASE: Increment usage after successful pool delivery
                        try:
                            from app.services.database import get_database_connection
                            supabase = get_database_connection()
                            
                            logger.info(f"🔍 DAILY LIMITS: Incrementing usage for user {job.user_id}, section 'reading_passages' by {section_count}")
                            logger.info(f"🔍 DAILY LIMITS: Calling increment_user_daily_usage with p_user_id={job.user_id}, p_section='reading_passages', p_amount={section_count}")
                            
                            response = supabase.rpc(
                                'increment_user_daily_usage',
                                {
                                    'p_user_id': job.user_id,
                                    'p_section': 'reading_passages',
                                    'p_amount': section_count
                                }
                            ).execute()
                            
                            logger.info(f"🔍 DAILY LIMITS: Increment response: {response.data}")
                            logger.info(f"🔍 DAILY LIMITS: Response status: {response}")
                            
                            # Check if the increment actually worked by querying the current usage
                            try:
                                current_usage = supabase.rpc('get_or_create_user_daily_limits', {'p_user_id': job.user_id}).execute()
                                logger.info(f"🔍 DAILY LIMITS: Current usage after increment: {current_usage.data}")
                            except Exception as check_error:
                                logger.error(f"🔍 DAILY LIMITS: Error checking current usage: {check_error}")
                                
                        except Exception as e:
                            logger.error(f"🔍 DAILY LIMITS: ❌ Error incrementing usage: {e}")
                            logger.error(f"🔍 DAILY LIMITS: ❌ Error type: {type(e)}")
                            logger.error(f"🔍 DAILY LIMITS: ❌ Error details: {str(e)}")
                            # Don't fail the request if increment fails
                            
                    except Exception as mark_error:
                        if "duplicate key value violates unique constraint" in str(mark_error):
                            logger.warning(f"🔍 POOL: ⚠️ Pool passages already used, failing section {section_type.value}")
                            job_manager.update_section_progress(job_id, section_type.value, 100, "Service temporarily unavailable")
                            job_manager.fail_section(job_id, section_type.value, "Service temporarily unavailable. Please try again in a few minutes.")
                            return
                        else:
                            raise mark_error
                    
                    logger.info(f"🔍 POOL: ✅ Successfully delivered {section_count} reading passages from pool")
                elif len(pool_content) > 0:
                    # Pool has some passages but not enough - use what we have
                    logger.info(f"🔍 POOL: ⚠️ Pool has {len(pool_content)} passages, need {section_count}")
                    logger.info(f"🔍 POOL: ✅ Using available {len(pool_content)} passages from pool")
                    
                    # Use available pool content
                    pool_result = pool_converter.convert_reading_to_section(pool_content)
                    
                    # Mark passages as used
                    try:
                        # Debug: log the structure of pool content
                        logger.debug(f"🔍 POOL DEBUG: Pool content structure: {type(pool_content)}")
                        if pool_content:
                            logger.debug(f"🔍 POOL DEBUG: First item keys: {list(pool_content[0].keys()) if isinstance(pool_content[0], dict) else 'Not a dict'}")
                        
                        # Extract IDs safely - reading passages use 'passage_id'
                        passage_ids = []
                        for item in pool_content:
                            if isinstance(item, dict) and 'passage_id' in item:
                                passage_ids.append(item['passage_id'])
                            elif isinstance(item, dict) and 'id' in item:
                                passage_ids.append(item['id'])
                            else:
                                logger.warning(f"🔍 POOL: ⚠️ Pool item missing 'passage_id' or 'id' key: {item}")
                        
                        if passage_ids:
                            await pool_service.mark_content_as_used(
                                user_id=job.user_id,
                                passage_ids=passage_ids,
                                usage_type="complete_test"
                            )
                            logger.info(f"🔍 POOL: ✅ Marked {len(passage_ids)} reading passages as used")
                        else:
                            logger.warning(f"🔍 POOL: ⚠️ No valid passage IDs found, skipping mark as used")
                    except Exception as mark_error:
                        if "duplicate key value violates unique constraint" in str(mark_error):
                            logger.warning(f"🔍 POOL: ⚠️ Pool passages already used")
                            pool_result = None
                        else:
                            logger.error(f"🔍 POOL: ❌ Error marking passages as used: {mark_error}")
                            # Continue without marking as used rather than failing
                else:
                    logger.info(f"🔍 POOL: ❌ No reading content available in pool, will generate {section_count} on-demand")
            
            elif section_type.value == "writing" and not force_llm_generation:
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
                        
                        # INCREMENT PHASE: Increment usage after successful pool delivery
                        try:
                            from app.services.database import get_database_connection
                            supabase = get_database_connection()
                            
                            logger.info(f"🔍 DAILY LIMITS: Incrementing usage for user {job.user_id}, section 'writing' by {section_count}")
                            logger.info(f"🔍 DAILY LIMITS: Calling increment_user_daily_usage with p_user_id={job.user_id}, p_section='writing', p_amount={section_count}")
                            
                            response = supabase.rpc(
                                'increment_user_daily_usage',
                                {
                                    'p_user_id': job.user_id,
                                    'p_section': 'writing',
                                    'p_amount': section_count
                                }
                            ).execute()
                            
                            logger.info(f"🔍 DAILY LIMITS: Increment response: {response.data}")
                            logger.info(f"🔍 DAILY LIMITS: Response status: {response}")
                            
                            # Check if the increment actually worked by querying the current usage
                            try:
                                current_usage = supabase.rpc('get_or_create_user_daily_limits', {'p_user_id': job.user_id}).execute()
                                logger.info(f"🔍 DAILY LIMITS: Current usage after increment: {current_usage.data}")
                            except Exception as check_error:
                                logger.error(f"🔍 DAILY LIMITS: Error checking current usage: {check_error}")
                                
                        except Exception as e:
                            logger.error(f"🔍 DAILY LIMITS: ❌ Error incrementing usage: {e}")
                            logger.error(f"🔍 DAILY LIMITS: ❌ Error type: {type(e)}")
                            logger.error(f"🔍 DAILY LIMITS: ❌ Error details: {str(e)}")
                            # Don't fail the request if increment fails
                            
                    except Exception as mark_error:
                        if "duplicate key value violates unique constraint" in str(mark_error):
                            logger.warning(f"🔍 POOL: ⚠️ Pool prompts already used, failing section {section_type.value}")
                            job_manager.update_section_progress(job_id, section_type.value, 100, "Service temporarily unavailable")
                            job_manager.fail_section(job_id, section_type.value, "Service temporarily unavailable. Please try again in a few minutes.")
                            return
                        else:
                            raise mark_error
                    
                    logger.info(f"🔍 POOL: ✅ Successfully delivered {section_count} writing prompts from pool")
                elif len(pool_prompts) > 0:
                    # Pool has some prompts but not enough - use what we have
                    logger.info(f"🔍 POOL: ⚠️ Pool has {len(pool_prompts)} prompts, need {section_count}")
                    logger.info(f"🔍 POOL: ✅ Using available {len(pool_prompts)} prompts from pool")
                    
                    # Use available pool content
                    pool_result = pool_converter.convert_writing_to_section(pool_prompts)
                    
                    # Mark prompts as used
                    try:
                        # Debug: log the structure of pool content
                        logger.debug(f"🔍 POOL DEBUG: Pool prompts structure: {type(pool_prompts)}")
                        if pool_prompts:
                            logger.debug(f"🔍 POOL DEBUG: First item keys: {list(pool_prompts[0].keys()) if isinstance(pool_prompts[0], dict) else 'Not a dict'}")
                        
                        # Extract IDs safely
                        prompt_ids = []
                        for item in pool_prompts:
                            if isinstance(item, dict) and 'id' in item:
                                prompt_ids.append(item['id'])
                            else:
                                logger.warning(f"🔍 POOL: ⚠️ Pool item missing 'id' key: {item}")
                        
                        if prompt_ids:
                            await pool_service.mark_content_as_used(
                                user_id=job.user_id,
                                writing_prompt_ids=prompt_ids,
                                usage_type="complete_test"
                            )
                            logger.info(f"🔍 POOL: ✅ Marked {len(prompt_ids)} writing prompts as used")
                        else:
                            logger.warning(f"🔍 POOL: ⚠️ No valid prompt IDs found, skipping mark as used")
                    except Exception as mark_error:
                        if "duplicate key value violates unique constraint" in str(mark_error):
                            logger.warning(f"🔍 POOL: ⚠️ Pool prompts already used")
                            pool_result = None
                        else:
                            logger.error(f"🔍 POOL: ❌ Error marking prompts as used: {mark_error}")
                            # Continue without marking as used rather than failing
                else:
                    logger.info(f"🔍 POOL: ❌ No writing prompts available in pool, will generate {section_count} on-demand")
            
            # If we have pool results, use them; otherwise handle based on user role
            if pool_result:
                # Pool has content - use pool only
                logger.info(f"🔍 POOL: ✅ Using pool results for {section_type.value}")
                section = pool_result
            else:
                # Pool exhausted - check user role to determine next action
                job = job_manager.get_job(job_id)
                user_role = job.request_data.get('user_role', 'user') if job else 'user'
                
                if user_role == 'admin' and force_llm_generation:
                    # Admin user with LLM fallback enabled - generate via LLM
                    logger.info(f"🔍 POOL: 🔄 Pool exhausted for admin user, generating via LLM for {section_type.value}")
                else:
                    # Normal user or admin without LLM fallback - fail gracefully
                    logger.warning(f"🔍 POOL: ❌ Pool exhausted for {user_role} user, no LLM fallback available for {section_type.value}")
                    job_manager.update_section_progress(job_id, section_type.value, 100, f"No {section_type.value} content available in pool")
                    job_manager.fail_section(job_id, section_type.value, f"No {section_type.value} content available in pool. Please try again later or contact support.")
                    return
                
                # Generate content via LLM using direct content generators
                if section_type.value == "writing":
                    logger.debug(f"📝 Using writing section generation")
                    section = await self._generate_writing_section(request.difficulty)
                elif section_type.value == "reading":
                    logger.debug(f"📖 Using reading section generation")
                    logger.info(f"🔍 POOL: 🔄 About to call reading generation with difficulty={request.difficulty}, count={section_count}, provider={request.provider}")
                    try:
                        section = await self._generate_reading_section(
                            request.difficulty, section_count, request.provider, use_async=True, is_official_format=request.is_official_format, topic=None
                        )
                        logger.info(f"🔍 POOL: ✅ Successfully generated {section_count} reading passages via LLM")
                    except Exception as e:
                        logger.error(f"🔍 POOL: ❌ Error generating reading passages: {e}")
                        raise
                elif section_type.value == "quantitative":
                    logger.debug(f"🎯 Using quantitative section generation")
                    section = await self._generate_quantitative_section_official_5_calls(
                        request.difficulty, section_count, request.provider, use_async=True
                    )
                elif section_type.value == "analogy":
                    logger.debug(f"🔗 Using analogy section generation")
                    section = await self._generate_analogy_section(
                        request.difficulty, section_count, request.provider, use_async=True
                    )
                elif section_type.value == "synonym":
                    logger.debug(f"📚 Using synonym section generation")
                    section = await self._generate_synonym_section(
                        request.difficulty, section_count, request.provider, use_async=True
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
                if 'questions' in section_data and section_data['questions']:
                    for question in section_data['questions']:
                        if isinstance(question, dict) and 'metadata' in question:
                            provider_used = question['metadata'].get('provider_used')
                            break
            elif section_type.value == 'reading':
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
                    # Check if content came from pool
                    if pool_result is not None:
                        logger.debug(f"📊 DEBUG: Section {section_type.value} uses pool content (no current provider needed)")
                    else:
                        logger.debug(f"📊 DEBUG: No provider available for section {section_type.value}")
            
            # Ensure section_type is set in section_data for proper tracking
            section_data['section_type'] = section_type.value
            
            # Calculate question count for the section
            question_count = 0
            if section_type.value in ['quantitative', 'analogy', 'synonym']:
                if 'questions' in section_data and section_data['questions']:
                    question_count = len(section_data['questions'])
            elif section_type.value == 'reading':
                if 'passages' in section_data and section_data['passages']:
                    for passage in section_data['passages']:
                        if isinstance(passage, dict) and 'questions' in passage:
                            question_count += len(passage['questions'])
            elif section_type.value == 'writing':
                question_count = 1  # Count as 1 unit
            
            # Only save to database if content was AI-generated, not if it came from pool
            saved_ids = None
            if pool_result is None:
                # Content was AI-generated - save to database
                try:
                    from app.services.ai_content_service import AIContentService
                    ai_content_service = AIContentService()
                    
                    # Log section completion
                    logger.info(f"📝 Completed section {section_type.value}")
                    
                    saved_ids = await ai_content_service.save_test_section(job_id, section)
                    logger.debug(f"Saved AI-generated content for section {section_type.value}: {saved_ids}")
                    # Add AI generation source to metadata for clarity
                    section_data['metadata']['content_source'] = 'ai_generation'
                except Exception as e:
                    logger.error(f"Failed to save AI-generated content for section {section_type.value}: {e}")
                    # Continue with job completion even if saving fails
            else:
                # Content came from pool - no need to save to database again
                logger.info(f"📝 Completed section {section_type.value} (pool content - no database save needed)")
                # Add pool source to metadata for clarity
                section_data['metadata']['content_source'] = 'pool'
            
            job_manager.complete_section(job_id, section_type.value, section_data)
            logger.info(f"Completed section {section_type.value} for job {job_id}")
            
            return {
                'section_type': section_type.value,
                'provider_used': provider_used,
                'question_count': question_count,
                'section_data': section_data
            }
            
        except Exception as e:
            logger.error(f"Failed to generate section {section_type.value} for job {job_id}: {e}")
            return {
                'section_type': section_type.value,
                'error': str(e)
            }
    
    async def _check_daily_limits_for_pool(self, request: QuestionGenerationRequest, user_id: str, user_metadata: Optional[Dict[str, Any]] = None):
        """Check daily limits before attempting pool content retrieval."""
        try:
            from app.services.daily_limit_service import DailyLimitService
            from app.services.database import get_database_connection
            
            # Initialize daily limit service
            supabase = get_database_connection()
            daily_limit_service = DailyLimitService(supabase)
            
            # Map question type to section name for daily limits
            section_mapping = {
                "quantitative": "quantitative",
                "analogy": "analogy", 
                "synonym": "synonym",
                "reading": "reading_passages",
                "writing": "writing"
            }
            
            section = section_mapping.get(request.question_type.value)
            if not section:
                logger.warning(f"Unknown question type for daily limits: {request.question_type.value}")
                return
            
            # Check if user can generate this content
            can_generate, usage_info = await daily_limit_service.check_limits(
                user_id=user_id,
                section=section,
                user_metadata=user_metadata
            )
            
            if not can_generate:
                remaining = usage_info.get('remaining', {})
                limit = remaining.get(section, 0)
                raise HTTPException(
                    status_code=429,
                    detail=f"Daily limit exceeded for {section}. You have {limit} remaining. Please try again tomorrow."
                )
            
            logger.info(f"Daily limit check passed for {section} (need {request.count} {section})")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Daily limit check failed: {e}")
            # Don't block content generation if limit check fails
            logger.warning("Continuing with content generation despite limit check failure")
    
    async def _check_daily_limits_for_background_section(self, user_id: str, section_type: str, count: int, user_metadata: Optional[Dict[str, Any]] = None):
        """Check daily limits for background section generation."""
        try:
            from app.services.daily_limit_service import DailyLimitService
            from app.services.database import get_database_connection
            
            # Initialize daily limit service
            supabase = get_database_connection()
            daily_limit_service = DailyLimitService(supabase)
            
            # Map section type to section name for daily limits
            section_mapping = {
                "quantitative": "quantitative",
                "analogy": "analogy", 
                "synonym": "synonym",
                "reading": "reading_passages",
                "writing": "writing"
            }
            
            section = section_mapping.get(section_type)
            if not section:
                logger.warning(f"Unknown section type for daily limits: {section_type}")
                return
            
            # Check if user can generate this content
            can_generate, usage_info = await daily_limit_service.check_limits(
                user_id=user_id,
                section=section,
                user_metadata=user_metadata
            )
            
            if not can_generate:
                remaining = usage_info.get('remaining', {})
                limit = remaining.get(section, 0)
                raise HTTPException(
                    status_code=429,
                    detail=f"Daily limit exceeded for {section}. You have {limit} remaining. Please try again tomorrow."
                )
            
            logger.info(f"Daily limit check passed for {section} (need {count} {section})")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Daily limit check failed for background section: {e}")
            # Don't block content generation if limit check fails
            logger.warning("Continuing with background section generation despite limit check failure")

