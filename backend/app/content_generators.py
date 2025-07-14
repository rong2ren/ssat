"""
Type-specific content generators for SSAT questions.

This module provides the correct architecture for generating different types of SSAT content:
- Standalone questions (math, verbal, analogy, synonym)
- Reading passages (with multiple questions per passage)  
- Writing prompts (creative writing tasks)
"""

import time
import uuid
from typing import List, Dict, Any, Optional, Union
from loguru import logger

from app.core_models import QuestionRequest, QuestionType, DifficultyLevel, Question, Option
from app.generator import SSATGenerator, generate_questions, generate_reading_passage
from app.llm import llm_client, LLMProvider
from app.util import extract_json_from_text
from app.specifications import OFFICIAL_ELEMENTARY_SPECS, ELEMENTARY_WRITING_PROMPTS
import random


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


def generate_reading_passages(request: QuestionRequest, llm: Optional[str] = None) -> List[ReadingPassage]:
    """Generate reading passages with 4 questions each."""
    logger.info(f"Generating {request.count} reading passages")
    
    if request.question_type.value != "reading":
        raise ValueError("This function only generates reading passages")
    
    passages = []
    
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
        
        # Create ReadingPassage object
        passage = ReadingPassage(passage_data, questions)
        passages.append(passage)
        
        logger.info(f"Generated reading passage {i+1}/{request.count} with {len(questions)} questions")
    
    logger.info(f"Generated {len(passages)} reading passages total")
    return passages


def generate_writing_prompts(request: QuestionRequest, llm: Optional[str] = None) -> List[WritingPrompt]:
    """Generate writing prompts using AI with real SSAT training examples."""
    logger.info(f"Generating {request.count} writing prompts with AI")
    
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
            logger.info(f"Using {len(training_examples)} real SSAT writing examples for training")
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
        return prompts
        
    except Exception as e:
        logger.error(f"Error in AI writing prompt generation: {e}")
        # Fallback to static prompts
        logger.info("Falling back to static writing prompts")
        return generate_static_writing_prompts(request)

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


# Unified content generation function
def generate_content(request: QuestionRequest, llm: Optional[str] = None) -> Union[List[Question], List[ReadingPassage], List[WritingPrompt]]:
    """
    Generate content based on question type.
    
    Returns:
    - List[Question] for math, verbal, analogy, synonym
    - List[ReadingPassage] for reading comprehension  
    - List[WritingPrompt] for writing tasks
    """
    logger.info(f"Generating content for {request.question_type.value}")
    
    if request.question_type.value in ["quantitative", "verbal", "analogy", "synonym"]:
        return generate_standalone_questions(request, llm)
    elif request.question_type.value == "reading":
        return generate_reading_passages(request, llm)
    elif request.question_type.value == "writing":
        return generate_writing_prompts(request, llm)
    else:
        raise ValueError(f"Unknown question type: {request.question_type.value}")


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
    """Async version of generate_writing_prompts."""
    # Writing prompts are currently selected from predefined list, so no async needed
    return generate_writing_prompts(request, llm)


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