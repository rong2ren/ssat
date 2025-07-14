"""
Unified content generation service that routes to type-specific generators.

This replaces the old QuestionService with a proper architecture that handles
different content types appropriately.
"""

import time
import uuid
from typing import Dict, Any, Union, List
from loguru import logger

from app.core_models import QuestionRequest, QuestionType as SSATQuestionType, DifficultyLevel as SSATDifficultyLevel
from app.models.requests import QuestionGenerationRequest, QuestionType, DifficultyLevel
from app.models.responses import (
    QuestionGenerationResponse, ReadingGenerationResponse, WritingGenerationResponse,
    GenerationMetadata, GeneratedQuestion, ReadingPassage, WritingPrompt
)
from app.content_generators import (
    generate_content, generate_content_async, 
    ReadingPassage as GeneratorReadingPassage,
    WritingPrompt as GeneratorWritingPrompt
)


class UnifiedContentService:
    """Service that routes content generation to appropriate type-specific generators."""
    
    def __init__(self):
        """Initialize the unified content service."""
        logger.info("Unified Content Service initialized")
    
    def _convert_to_ssat_request(self, request: QuestionGenerationRequest) -> QuestionRequest:
        """Convert API request to internal SSAT request format."""
        # Map API enums to internal enums
        question_type_mapping = {
            QuestionType.QUANTITATIVE: SSATQuestionType.QUANTITATIVE,
            QuestionType.READING: SSATQuestionType.READING,
            QuestionType.VERBAL: SSATQuestionType.VERBAL,
            QuestionType.ANALOGY: SSATQuestionType.ANALOGY,
            QuestionType.SYNONYM: SSATQuestionType.SYNONYM,
            QuestionType.WRITING: SSATQuestionType.WRITING,
        }
        
        difficulty_mapping = {
            DifficultyLevel.EASY: SSATDifficultyLevel.EASY,
            DifficultyLevel.MEDIUM: SSATDifficultyLevel.MEDIUM,
            DifficultyLevel.HARD: SSATDifficultyLevel.HARD,
        }
        
        return QuestionRequest(
            question_type=question_type_mapping[request.question_type],
            difficulty=difficulty_mapping[request.difficulty],
            topic=request.topic,
            count=request.count,
            level=request.level
        )
    
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
            "story_elements": prompt.story_elements,
            "prompt_type": prompt.prompt_type
        }
        
        # Only include visual_description if it has meaningful content
        if prompt.visual_description and prompt.visual_description.strip():
            data["visual_description"] = prompt.visual_description
        
        return data
    
    async def generate_content(self, request: QuestionGenerationRequest) -> Union[QuestionGenerationResponse, ReadingGenerationResponse, WritingGenerationResponse]:
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
            
            # Generate content using unified generator
            content = generate_content(ssat_request, llm=provider)
            
            generation_time = time.time() - start_time
            
            # Create metadata
            metadata = GenerationMetadata(
                generation_time=generation_time,
                provider_used=provider or "auto-selected",
                training_examples_count=5,  # TODO: Get actual count from generators
                request_id=request_id
            )
            
            # Return type-specific response
            if request.question_type in [QuestionType.QUANTITATIVE, QuestionType.VERBAL, QuestionType.ANALOGY, QuestionType.SYNONYM]:
                # Standalone questions
                api_questions = self._convert_questions_to_api_format(content)
                return QuestionGenerationResponse(
                    questions=api_questions,
                    metadata=metadata,
                    status="success",
                    count=len(api_questions)
                )
            
            elif request.question_type == QuestionType.READING:
                # Reading passages
                api_passages = [self._convert_reading_passage_to_api_format(passage) for passage in content]
                total_questions = sum(len(passage["questions"]) for passage in api_passages)
                return ReadingGenerationResponse(
                    passages=api_passages,
                    metadata=metadata,
                    status="success",
                    count=len(api_passages),
                    total_questions=total_questions
                )
            
            elif request.question_type == QuestionType.WRITING:
                # Writing prompts
                api_prompts = [self._convert_writing_prompt_to_api_format(prompt) for prompt in content]
                return WritingGenerationResponse(
                    prompts=api_prompts,
                    metadata=metadata,
                    status="success",
                    count=len(api_prompts)
                )
            
            else:
                raise ValueError(f"Unknown question type: {request.question_type}")
                
        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            raise e
    
    async def generate_content_async(self, request: QuestionGenerationRequest) -> Union[QuestionGenerationResponse, ReadingGenerationResponse, WritingGenerationResponse]:
        """
        Async version of generate_content for parallel processing.
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        try:
            # Convert to internal request format
            ssat_request = self._convert_to_ssat_request(request)
            provider = request.provider.value if request.provider else None
            
            # Generate content using unified async generator
            content = await generate_content_async(ssat_request, llm=provider)
            
            generation_time = time.time() - start_time
            
            # Create metadata
            metadata = GenerationMetadata(
                generation_time=generation_time,
                provider_used=provider or "auto-selected",
                training_examples_count=5,  # TODO: Get actual count from generators
                request_id=request_id
            )
            
            # Return type-specific response
            if request.question_type in [QuestionType.QUANTITATIVE, QuestionType.VERBAL, QuestionType.ANALOGY, QuestionType.SYNONYM]:
                # Standalone questions
                api_questions = self._convert_questions_to_api_format(content)
                return QuestionGenerationResponse(
                    questions=api_questions,
                    metadata=metadata,
                    status="success",
                    count=len(api_questions)
                )
            
            elif request.question_type == QuestionType.READING:
                # Reading passages
                api_passages = [self._convert_reading_passage_to_api_format(passage) for passage in content]
                total_questions = sum(len(passage["questions"]) for passage in api_passages)
                return ReadingGenerationResponse(
                    passages=api_passages,
                    metadata=metadata,
                    status="success",
                    count=len(api_passages),
                    total_questions=total_questions
                )
            
            elif request.question_type == QuestionType.WRITING:
                # Writing prompts
                api_prompts = [self._convert_writing_prompt_to_api_format(prompt) for prompt in content]
                return WritingGenerationResponse(
                    prompts=api_prompts,
                    metadata=metadata,
                    status="success",
                    count=len(api_prompts)
                )
            
            else:
                raise ValueError(f"Unknown question type: {request.question_type}")
                
        except Exception as e:
            logger.error(f"Async content generation failed: {e}")
            raise e