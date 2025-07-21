"""
Type-specific content generators for SSAT questions.

This module provides the correct architecture for generating different types of SSAT content:
- Standalone questions (math, verbal, analogy, synonym)
- Reading passages (with multiple questions per passage)  
- Writing prompts (creative writing tasks)
"""

import time
import uuid
from typing import List, Dict, Any, Optional, Union, NamedTuple
from loguru import logger

from app.models import QuestionRequest, Question, Option
from app.models.enums import QuestionType, DifficultyLevel
from app.generator import SSATGenerator, generate_questions, generate_reading_passage
from app.llm import llm_client, LLMProvider
from app.util import extract_json_from_text
from app.specifications import OFFICIAL_ELEMENTARY_SPECS, ELEMENTARY_WRITING_PROMPTS
import random


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
        self.story_elements = prompt_data.get("story_elements", [])
        self.prompt_type = prompt_data.get("prompt_type", "picture_story")
        self.subsection = prompt_data.get("subsection", "Picture Story")  # AI-determined subsection
        self.tags = prompt_data.get("tags", [])  # AI-determined tags


# Type-specific generation functions
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


def generate_reading_passages_with_metadata(request: QuestionRequest, llm: Optional[str] = None) -> GenerationResult:
    """Generate reading passages with training examples metadata.
    
    Returns GenerationResult with content, training_example_ids, and provider_used.
    """
    logger.info(f"Generating {request.count} reading passages with metadata")
    
    if request.question_type.value != "reading":
        raise ValueError("This function only generates reading passages")
    
    passages = []
    all_training_example_ids = []
    provider_used = "auto-selected"
    
    # Get training examples once to capture IDs
    from app.generator import SSATGenerator
    generator = SSATGenerator()
    training_examples = generator.get_reading_training_examples()
    training_example_ids = [ex.get('question_id', '') for ex in training_examples if ex.get('question_id')]
    
    # Official SSAT: 7 passages × 4 questions = 28 questions
    # For individual requests, generate requested number of passages
    for i in range(request.count):
        # Create request for 4 questions per passage (SSAT standard)
        passage_request = QuestionRequest(
            question_type=request.question_type,
            difficulty=request.difficulty,
            topic=request.topic,
            count=4  # Always 4 questions per passage
        )
        
        # Generate passage with questions using dedicated function
        result = generate_reading_passage(passage_request, llm=llm)
        passage_data = result["passage"]
        questions = result["questions"]
        
        # Capture provider used (from the result if available)
        if "provider_used" in result:
            provider_used = result["provider_used"]
        elif llm:
            provider_used = llm
        
        # Create ReadingPassage object
        passage = ReadingPassage(passage_data, questions)
        passages.append(passage)
        
        logger.info(f"Generated reading passage {i+1}/{request.count} with {len(questions)} questions")
    
    logger.info(f"Generated {len(passages)} reading passages total with {len(training_example_ids)} training examples")
    return GenerationResult(
        content=passages,
        training_example_ids=training_example_ids,
        provider_used=provider_used
    )

def generate_writing_prompts_with_metadata(request: QuestionRequest, llm: Optional[str] = None) -> GenerationResult:
    """Generate writing prompts using AI with real SSAT training examples.
    
    Returns GenerationResult with content, training_example_ids, and provider_used.
    """
    logger.info(f"Generating {request.count} writing prompts with AI")
    
    if request.question_type.value != "writing":
        raise ValueError("This function only generates writing prompts")
    
    # Initialize generator
    generator = SSATGenerator()
    
    try:
        # Get writing training examples from database
        training_examples = generator.get_writing_training_examples(request.topic)
        system_message = generator.build_writing_few_shot_prompt(request, training_examples)
        
        # Extract training example IDs
        training_example_ids = [ex.get('id', '') for ex in training_examples if ex.get('id')]
        
        # Log training info
        if training_examples:
            logger.info(f"Using {len(training_examples)} real SSAT writing examples for training")
            logger.info(f"Training example IDs: {training_example_ids}")
        else:
            logger.info("No writing training examples found, using generic AI prompt")
        
        # Generate prompts using LLM (same pattern as other question types)
        available_providers = llm_client.get_available_providers()
        if not available_providers:
            raise ValueError("No LLM providers available")
        
        # Use specified provider or fall back to preferred order
        if llm:
            provider_name = llm.lower()
        else:
            preferred_order = ['deepseek', 'gemini', 'openai']
            provider_name = None
            for preferred in preferred_order:
                if any(p.value == preferred for p in available_providers):
                    provider_name = preferred
                    break
            if not provider_name:
                provider_name = available_providers[0].value
        
        provider = LLMProvider(provider_name)
        logger.info(f"Using LLM provider: {provider.value}")
        
        # Generate prompts using LLM
        content = llm_client.call_llm(
            provider=provider,
            system_message=system_message,
            prompt="Generate the writing prompts as specified.",
        )
        
        if content is None:
            raise ValueError(f"LLM call to {provider.value} failed - no content returned")
        
        data = extract_json_from_text(content)
        if data is None:
            raise ValueError("Failed to extract JSON from LLM response")
        
        # Parse generated prompts
        prompts = []
        for prompt_data in data["prompts"]:
            # Add standard instructions
            prompt_data["instructions"] = "Look at the picture and write a story with a beginning, middle, and end. Use proper grammar, punctuation, and spelling."
            prompt = WritingPrompt(prompt_data)
            prompts.append(prompt)
        
        logger.info(f"Successfully generated {len(prompts)} writing prompts using {'real SSAT examples' if training_examples else 'generic AI prompt'}")
        return GenerationResult(
            content=prompts, 
            training_example_ids=training_example_ids,
            provider_used=provider.value
        )
        
    except Exception as e:
        logger.error(f"Error in AI writing prompt generation: {e}")
        # Fallback to static prompts
        logger.info("Falling back to static writing prompts")
        static_prompts = generate_static_writing_prompts(request)
        return GenerationResult(
            content=static_prompts,
            training_example_ids=[],  # No training examples for static prompts
            provider_used="static"
        )

def generate_static_writing_prompts(request: QuestionRequest) -> List[WritingPrompt]:
    """Fallback function that uses the current static approach."""
    logger.info(f"Generating {request.count} static writing prompts (fallback)")
    
    prompts = []
    
    # Ensure we don't select more prompts than available
    available_prompts = ELEMENTARY_WRITING_PROMPTS.copy()
    actual_count = min(request.count, len(available_prompts))
    
    if request.count > len(available_prompts):
        logger.warning(f"Requested {request.count} prompts but only {len(available_prompts)} available. Generating {actual_count} unique prompts.")
    
    # Select unique prompts without replacement
    selected_prompts = random.sample(available_prompts, actual_count)
    
    for i, prompt_data in enumerate(selected_prompts):
        # Add standard instructions
        prompt_data = prompt_data.copy()  # Don't modify the original
        prompt_data["instructions"] = "Look at the picture and write a story with a beginning, middle, and end. Use proper grammar, punctuation, and spelling."
        
        prompt = WritingPrompt(prompt_data)
        prompts.append(prompt)
        
        logger.info(f"Generated static writing prompt {i+1}/{actual_count}")
    
    logger.info(f"Generated {len(prompts)} unique static writing prompts total")
    return prompts


# Async versions for parallel generation
async def generate_standalone_questions_async(request: QuestionRequest, llm: Optional[str] = None) -> List[Question]:
    """Async version of generate_standalone_questions."""
    logger.info(f"Generating {request.count} standalone {request.question_type.value} questions async")
    
    if request.question_type.value == "reading":
        raise ValueError("Reading questions should use generate_reading_passages_async()")
    if request.question_type.value == "writing":
        raise ValueError("Writing prompts should use generate_writing_prompts_async()")
    
    from app.generator import generate_questions_async
    questions = await generate_questions_async(request, llm=llm)
    logger.info(f"Generated {len(questions)} standalone questions async")
    return questions


async def generate_reading_passages_async(request: QuestionRequest, llm: Optional[str] = None) -> List[ReadingPassage]:
    """Async version of generate_reading_passages."""
    logger.info(f"Generating {request.count} reading passages async")
    
    if request.question_type.value != "reading":
        raise ValueError("This function only generates reading passages")
    
    passages = []
    
    for i in range(request.count):
        # Create request for 4 questions per passage (SSAT standard)
        passage_request = QuestionRequest(
            question_type=request.question_type,
            difficulty=request.difficulty,
            topic=request.topic,
            count=4  # Always 4 questions per passage
        )
        
        # Generate passage with questions using dedicated async function
        from app.generator import generate_reading_passage_async
        result = await generate_reading_passage_async(passage_request, llm=llm)
        passage_data = result["passage"]
        questions = result["questions"]
        
        # Create ReadingPassage object
        passage = ReadingPassage(passage_data, questions)
        passages.append(passage)
        
        logger.info(f"Generated reading passage {i+1}/{request.count} with {len(questions)} questions async")
    
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
        available_providers = llm_client.get_available_providers()
        if not available_providers:
            raise ValueError("No LLM providers available")
        
        # Use specified provider or fall back to preferred order
        if llm:
            provider_name = llm.lower()
        else:
            preferred_order = ['deepseek', 'gemini', 'openai']
            provider_name = None
            for preferred in preferred_order:
                if any(p.value == preferred for p in available_providers):
                    provider_name = preferred
                    break
            if not provider_name:
                provider_name = available_providers[0].value
        
        try:
            provider = LLMProvider(provider_name)
        except ValueError:
            available_names = [p.value for p in available_providers]
            raise ValueError(f"Unsupported LLM provider: {llm}. Available providers: {available_names}")
        
        if provider not in available_providers:
            available_names = [p.value for p in available_providers]
            raise ValueError(f"Provider {provider.value} not available. Available providers: {available_names}")
        
        logger.info(f"Using LLM provider: {provider.value} (async)")
        
        # Generate prompts using async LLM call for true parallelism
        content = await llm_client.call_llm_async(
            provider=provider,
            system_message=system_message,
            prompt="Generate the writing prompts as specified.",
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
        # Fallback to static prompts for reliability
        logger.info("Falling back to static writing prompts (async)")
        static_prompts = generate_static_writing_prompts(request)
        return static_prompts


async def generate_content_async(request: QuestionRequest, llm: Optional[str] = None) -> Union[List[Question], List[ReadingPassage], List[WritingPrompt]]:
    """
    Async version of generate_content.
    
    Returns:
    - List[Question] for math, verbal, analogy, synonym
    - List[ReadingPassage] for reading comprehension  
    - List[WritingPrompt] for writing tasks
    """
    logger.info(f"Generating content for {request.question_type.value} async")
    
    if request.question_type.value in ["quantitative", "verbal", "analogy", "synonym"]:
        return await generate_standalone_questions_async(request, llm)
    elif request.question_type.value == "reading":
        return await generate_reading_passages_async(request, llm)
    elif request.question_type.value == "writing":
        return await generate_writing_prompts_async(request, llm)
    else:
        raise ValueError(f"Unknown question type: {request.question_type.value}")