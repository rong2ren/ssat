"""
Type-specific content generators for SSAT questions.

This module provides the correct architecture for generating different types of SSAT content:
- Standalone questions (math, verbal, analogy, synonym)
- Reading passages (with multiple questions per passage)  
- Writing prompts (creative writing tasks)
"""

import time
import uuid
import json
import random
import logging
from typing import List, Dict, Any, Optional, Union, NamedTuple
from loguru import logger

from app.models import QuestionRequest, Question, Option
from app.models.enums import QuestionType, DifficultyLevel
from app.generator import SSATGenerator, generate_questions, generate_reading_passages
from app.llm import llm_client, LLMProvider
from app.util import extract_json_from_text
from app.specifications import OFFICIAL_ELEMENTARY_SPECS

logger = logging.getLogger(__name__)

def _select_llm_provider(requested_provider: Optional[str]) -> LLMProvider:
    """Centralized provider selection logic."""
    available_providers = llm_client.get_available_providers()
    
    if not available_providers:
        raise ValueError("No LLM providers available. Please configure at least one API key in .env file")
    
    # Use specified provider or fall back to preferred provider order
    if requested_provider:
        provider_name = requested_provider.lower()
    else:
        # Preferred provider order: DeepSeek -> Gemini -> OpenAI
        preferred_order = ['deepseek', 'gemini', 'openai']
        provider_name = None
        
        for preferred in preferred_order:
            if any(p.value == preferred for p in available_providers):
                provider_name = preferred
                break
        
        # Fallback to first available if none of the preferred are available
        if not provider_name:
            provider_name = available_providers[0].value
    
    try:
        provider = LLMProvider(provider_name)
    except ValueError:
        available_names = [p.value for p in available_providers]
        raise ValueError(f"Unsupported LLM provider: {requested_provider}. Available providers: {available_names}")
    
    if provider not in available_providers:
        available_names = [p.value for p in available_providers]
        raise ValueError(f"Provider {provider.value} not available. Available providers: {available_names}")
    
    logger.info(f"Using LLM provider: {provider.value}")
    return provider


class GenerationResult(NamedTuple):
    """Result of content generation with metadata."""
    content: Union[List[Question], List['ReadingPassage'], List['WritingPrompt']]
    training_example_ids: List[str]
    provider_used: str


class ReadingPassage:
    """A reading passage with its associated questions."""
    def __init__(self, passage_data: Dict[str, Any], questions: List[Question]):
        self.id = str(uuid.uuid4())
        self.title = passage_data.get("title")
        self.text = passage_data["text"]
        
        # Normalize passage type to standard SSAT categories
        raw_type = passage_data.get("passage_type", "fiction").lower()
        type_mapping = {
            "science passage": "non_fiction",
            "science": "non_fiction", 
            "history": "non_fiction",
            "social studies": "non_fiction",
            "informational": "non_fiction",
            "story": "fiction",
            "narrative": "fiction",
            "poem": "poetry",
            "life story": "biography",
            "biography": "biography"
        }
        self.passage_type = type_mapping.get(raw_type, raw_type)
        
        self.grade_level = passage_data.get("grade_level", "3-4")
        self.topic = passage_data.get("topic", "Elementary Reading")
        self.questions = questions
        self.metadata = {"question_count": len(questions)}


class WritingPrompt:
    """A writing prompt for creative writing tasks."""
    def __init__(self, prompt_data: Dict[str, Any]):
        self.id = str(uuid.uuid4())
        self.prompt_text = prompt_data["prompt"]
        self.instructions = prompt_data.get("instructions", "Write a story with a beginning, middle, and end.")
        self.visual_description = prompt_data.get("visual_description")
        self.grade_level = prompt_data.get("grade_level", "3-4")
        self.prompt_type = prompt_data.get("prompt_type", "picture_story")
        self.subsection = prompt_data.get("subsection", "Picture Story")  # AI-determined subsection
        self.tags = prompt_data.get("tags", [])  # AI-determined tags


# Type-specific generation functions
def generate_standalone_questions_with_metadata(request: QuestionRequest, llm: Optional[str] = None, custom_examples: Optional[str] = None) -> GenerationResult:
    """Generate standalone questions using AI with real SSAT training examples.
    
    Returns GenerationResult with content, training_example_ids, and provider_used.
    """
    logger.info(f"Generating {request.count} standalone {request.question_type.value} questions with AI")
    
    if request.question_type.value == "reading":
        raise ValueError("Reading questions should use generate_reading_passages_with_metadata()")
    if request.question_type.value == "writing":
        raise ValueError("Writing prompts should use generate_writing_prompts_with_metadata()")
    
    # Initialize generator
    generator = SSATGenerator()
    
    try:
        # Get training examples from database or custom examples
        if custom_examples:
            training_examples = generator.parse_custom_examples(custom_examples, request.question_type.value)
            training_example_ids = []
            logger.info(f"Using {len(training_examples)} custom training examples")
        else:
            training_examples = generator.get_training_examples(request, custom_examples)
            training_example_ids = [ex.get('id', '') for ex in training_examples if ex.get('id')]
            logger.info(f"Using {len(training_examples)} database training examples")
        
        # Generate questions using pre-fetched training examples to avoid duplicate calls
        questions = generate_questions(request, llm=llm, custom_examples=custom_examples, training_examples=training_examples)
        
        logger.info(f"Generated {len(questions)} standalone questions")
        return GenerationResult(
            content=questions,
            training_example_ids=training_example_ids,
            provider_used="deepseek"  # Default provider
        )
        
    except Exception as e:
        logger.error(f"Standalone question generation failed: {e}")
        raise e


def generate_standalone_questions(request: QuestionRequest, llm: Optional[str] = None) -> List[Question]:
    """Generate standalone questions for math, verbal, analogy, synonym."""
    logger.info(f"Generating {request.count} standalone {request.question_type.value} questions")
    
    if request.question_type.value == "reading":
        raise ValueError("Reading questions should use generate_reading_passages()")
    if request.question_type.value == "writing":
        raise ValueError("Writing prompts should use generate_writing_prompts()")
    
    # Use existing question generation logic
    questions = generate_questions(request, llm=llm)
    logger.info(f"Generated {len(questions)} standalone questions")
    return questions


def generate_reading_passages_with_metadata(request: QuestionRequest, llm: Optional[str] = None, custom_examples: Optional[str] = None) -> GenerationResult:
    """Generate reading passages with training examples metadata.
    
    Returns GenerationResult with content, training_example_ids, and provider_used.
    """
    logger.info(f"Generating {request.count} reading passages with metadata")
    
    if request.question_type.value != "reading":
        raise ValueError("This function only generates reading passages")
    
    # Get training examples once to capture IDs
    from app.generator import SSATGenerator, generate_reading_passages
    generator = SSATGenerator()
    
    if custom_examples:
        training_examples = generator.parse_custom_examples(custom_examples, "reading")
        training_example_ids = []
        logger.info(f"Using {len(training_examples)} custom reading training examples")
    else:
        training_examples = generator.get_reading_training_examples(topic=request.topic)
        training_example_ids = [ex.get('question_id', '') for ex in training_examples if ex.get('question_id')]
        logger.info(f"Using {len(training_examples)} database reading training examples")
    
    # Use single call for admin generation (efficiency for small batches)
    use_single_call = True
    # Pass pre-fetched training examples to avoid double fetching
    results = generate_reading_passages(request, llm=llm, custom_examples=custom_examples, use_single_call=use_single_call, training_examples=training_examples)
    
    # Convert results to ReadingPassage objects
    passages = []
    provider_used = "auto-selected"
    
    for i, result in enumerate(results):
        passage_data = result["passage"]
        questions = result["questions"]
        
        # Create ReadingPassage object
        passage_dict = {
            "text": passage_data,
            "passage_type": result.get("passage_type", "General"),
            "title": f"Passage {i+1}",
            "topic": "Elementary Reading"
        }
        passage = ReadingPassage(passage_dict, questions)
        passages.append(passage)
        
        logger.info(f"Generated reading passage {i+1}/{len(results)} with {len(questions)} questions")
    
    logger.info(f"Generated {len(passages)} reading passages total with {len(training_example_ids)} training examples")
    return GenerationResult(
        content=passages,
        training_example_ids=training_example_ids,
        provider_used=provider_used
    )

def generate_writing_prompts_with_metadata(request: QuestionRequest, llm: Optional[str] = None, custom_examples: Optional[str] = None) -> GenerationResult:
    """Generate writing prompts using AI with real SSAT training examples.
    
    Returns GenerationResult with content, training_example_ids, and provider_used.
    """
    logger.info(f"Generating {request.count} writing prompts with AI")
    
    if request.question_type.value != "writing":
        raise ValueError("This function only generates writing prompts")
    
    # Initialize generator
    generator = SSATGenerator()
    
    try:
        # Get writing training examples from database or custom examples
        if custom_examples:
            training_examples = generator.parse_custom_examples(custom_examples, "writing")
            training_example_ids = []
            logger.info(f"Using {len(training_examples)} custom writing training examples")
        else:
            training_examples = generator.get_writing_training_examples(request.topic)
            training_example_ids = [ex.get('id', '') for ex in training_examples if ex.get('id')]
            logger.info(f"Using {len(training_examples)} database writing training examples")
        
        system_message = generator.build_writing_few_shot_prompt(request, training_examples)
        
        # Log training info
        if training_examples:
            logger.info(f"Using {len(training_examples)} writing examples for training")
            if not custom_examples:
                logger.info(f"Training example IDs: {training_example_ids}")
        else:
            logger.info("No writing training examples found, using generic AI prompt")
        
        # Generate prompts using LLM (same pattern as other question types)
        provider = _select_llm_provider(llm)
        
        # Generate prompts using LLM
        content = llm_client.call_llm(
            provider=provider,
            system_message=system_message,
            prompt="Generate the writing prompts as specified.",
            temperature=0.8,  # Higher temperature for more variety
        )
        
        if content is None:
            raise ValueError(f"LLM call to {provider.value} failed - no content returned")
        
        data = extract_json_from_text(content)
        if data is None:
            raise ValueError("Failed to extract JSON from LLM response")
        
        # Parse generated prompts
        prompts = []
        if "prompts" in data:
            for prompt_data in data["prompts"]:
                prompt = WritingPrompt(prompt_data)
                prompts.append(prompt)
        else:
            raise ValueError("Invalid response format: missing 'prompts' key")
        
        logger.info(f"Generated {len(prompts)} writing prompts")
        return GenerationResult(
            content=prompts,
            training_example_ids=training_example_ids,
            provider_used=provider.value
        )
        
    except Exception as e:
        logger.error(f"Writing prompt generation failed: {e}")
        raise e




# Async versions for parallel generation
async def generate_standalone_questions_async(request: QuestionRequest, llm: Optional[str] = None, custom_examples: Optional[str] = None) -> List[Question]:
    """Async version of generate_standalone_questions."""
    logger.info(f"Generating {request.count} standalone {request.question_type.value} questions async")
    
    if request.question_type.value == "reading":
        raise ValueError("Reading questions should use generate_reading_passages_async()")
    if request.question_type.value == "writing":
        raise ValueError("Writing prompts should use generate_writing_prompts_async()")
    
    # Initialize generator and get training examples once to avoid duplicate calls
    generator = SSATGenerator()
    
    try:
        # Get training examples from database or custom examples
        if custom_examples:
            training_examples = generator.parse_custom_examples(custom_examples, request.question_type.value)
            logger.info(f"Using {len(training_examples)} custom training examples")
        else:
            training_examples = generator.get_training_examples(request, custom_examples)
            logger.info(f"Using {len(training_examples)} database training examples")
        
        # Generate questions using pre-fetched training examples to avoid duplicate calls
        from app.generator import generate_questions_async
        questions = await generate_questions_async(request, llm=llm, custom_examples=custom_examples, training_examples=training_examples)
        logger.info(f"Generated {len(questions)} standalone questions async")
        return questions
        
    except Exception as e:
        logger.error(f"Async standalone question generation failed: {e}")
        raise e


async def generate_reading_passages_async(request: QuestionRequest, llm: Optional[str] = None, custom_examples: Optional[str] = None) -> List[ReadingPassage]:
    """Async version of generate_reading_passages."""
    logger.info(f"Generating {request.count} reading passages async")
    
    if request.question_type.value != "reading":
        raise ValueError("This function only generates reading passages")
    
    # Get training examples once to avoid double fetching
    from app.generator import SSATGenerator, generate_reading_passages_async as generate_reading_async
    generator = SSATGenerator()
    
    if custom_examples:
        training_examples = generator.parse_custom_examples(custom_examples, "reading")
        logger.info(f"Using {len(training_examples)} custom reading training examples")
    else:
        training_examples = generator.get_reading_training_examples(topic=request.topic)
        logger.info(f"Using {len(training_examples)} database reading training examples")
    
    # Use single call for admin generation (efficiency for small batches)
    use_single_call = True
    # Pass pre-fetched training examples to avoid double fetching
    results = await generate_reading_async(request, llm=llm, custom_examples=custom_examples, use_single_call=use_single_call, training_examples=training_examples)
    
    # Convert results to ReadingPassage objects
    passages = []
    
    for i, result in enumerate(results):
        passage_data = result["passage"]
        questions = result["questions"]
        
        # Create ReadingPassage object
        passage_dict = {
            "text": passage_data,
            "passage_type": result.get("passage_type", "General"),
            "title": f"Passage {i+1}",
            "topic": "Elementary Reading"
        }
        passage = ReadingPassage(passage_dict, questions)
        passages.append(passage)
        
        logger.info(f"Generated reading passage {i+1}/{len(results)} with {len(questions)} questions async")
    
    logger.info(f"Generated {len(passages)} reading passages total async")
    return passages


async def generate_writing_prompts_async(request: QuestionRequest, llm: Optional[str] = None) -> List[WritingPrompt]:
    """Async version of generate_writing_prompts using AI with real SSAT training examples."""
    logger.info(f"Generating {request.count} writing prompts with AI (async)")
    
    if request.question_type.value != "writing":
        raise ValueError("This function only generates writing prompts")
    
    # Initialize generator
    generator = SSATGenerator()
    
    try:
        # Get writing training examples from database
        training_examples = generator.get_writing_training_examples(request.topic)
        system_message = generator.build_writing_few_shot_prompt(request, training_examples)
        
        # Log training info
        if training_examples:
            logger.info(f"Using {len(training_examples)} real SSAT writing examples for training (async)")
        else:
            logger.info("No writing training examples found, using generic AI prompt (async)")
        
        # Generate prompts using async LLM (same pattern as other question types)
        provider = _select_llm_provider(llm)
        logger.info(f"Using LLM provider: {provider.value} (async)")
        
        # Generate prompts using async LLM call for true parallelism
        content = await llm_client.call_llm_async(
            provider=provider,
            system_message=system_message,
            prompt="Generate the writing prompts as specified.",
            temperature=0.8,  # Higher temperature for more variety
        )
        
        if content is None:
            raise ValueError(f"Async LLM call to {provider.value} failed - no content returned")
        
        data = extract_json_from_text(content)
        if data is None:
            raise ValueError("Failed to extract JSON from async LLM response")
        
        # Parse generated prompts
        prompts = []
        for prompt_data in data["prompts"]:
            # Add standard instructions
            prompt_data["instructions"] = "Look at the picture and write a story with a beginning, middle, and end. Use proper grammar, punctuation, and spelling."
            prompt = WritingPrompt(prompt_data)
            prompts.append(prompt)
        
        logger.info(f"Successfully generated {len(prompts)} writing prompts using async AI with {'real SSAT examples' if training_examples else 'generic AI prompt'}")
        return prompts
        
    except Exception as e:
        logger.error(f"Error in async AI writing prompt generation: {e}")
        # No fallback - let the error propagate
        raise ValueError(f"Failed to generate writing prompts: {e}")


async def generate_content_async(request: QuestionRequest, llm: Optional[str] = None, custom_examples: Optional[str] = None) -> Union[List[Question], List[ReadingPassage], List[WritingPrompt]]:
    """
    Async version of generate_content.
    
    Returns:
    - List[Question] for math, verbal, analogy, synonym
    - List[ReadingPassage] for reading comprehension  
    - List[WritingPrompt] for writing tasks
    """
    logger.info(f"Generating content for {request.question_type.value} async")
    
    if request.question_type.value in ["quantitative", "verbal", "analogy", "synonym"]:
        return await generate_standalone_questions_async(request, llm, custom_examples)
    elif request.question_type.value == "reading":
        return await generate_reading_passages_async(request, llm, custom_examples)
    elif request.question_type.value == "writing":
        return await generate_writing_prompts_async(request, llm)
    else:
        raise ValueError(f"Unknown question type: {request.question_type.value}")