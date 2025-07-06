"""SSAT question generator using OpenAI API."""

import json
from typing import List, Optional

from ssat.models import Question, Option, QuestionRequest, CognitiveLevel
from loguru import logger
from ssat.llm import llm_client, LLMProvider
from ssat.util import extract_json_from_text

# System prompt template
SYSTEM_PROMPT = """
[Role] You are an experienced SSAT Elementary Level question designer with over 10 years of professional expertise.
[Task] Generate high-quality SSAT {level} level {question_type} questions with difficulty level {difficulty}.
[Rules]
1. Each question should have exactly 4 options (A, B, C, D) and one correct answer. 
2. For each question, include a detailed explanation of why the answer is correct.
3. Ensure all questions are culturally neutral, grammatically correct and and suitable for {level} Level students.
4. For each question, specify the cognitive level (REMEMBER, UNDERSTAND, APPLY, ANALYZE, EVALUATE) based on the question's complexity and required thinking skills.
5. For each question, provide relevant tags that categorize the question by subject, skill, and content area.
6. Each question must include the complete question text, not just a title or category.
7. Do NOT include question numbers (e.g., "Question 1:", "Question 2:", etc.) in the question text.
[Output]
- Only return a pure JSON object, without any extra text or code block markers.
- JSON structure must be:
{{
  "questions": [
    {{
      "text": "Complete question text here. For example: 'The school cafeteria sells 3 different types of fruit juices: apple, orange, and grape. If 1/4 of the students choose apple juice, 1/3 choose orange juice, and the rest choose grape juice, what fraction of the students choose grape juice?'",
      "options": [
        {{"letter": "A", "text": "option text"}},
        {{"letter": "B", "text": "option text"}},
        {{"letter": "C", "text": "option text"}},
        {{"letter": "D", "text": "option text"}}
      ],
      "correct_answer": "A",
      "explanation": "explanation text",
      "cognitive_level": "REMEMBER",  # Must be one of: REMEMBER, UNDERSTAND, APPLY, ANALYZE, EVALUATE
      "tags": ["tag1", "tag2", "tag3", ...]
    }}
  ]
}}
"""

# Dictionary of type-specific rules
TYPE_SPECIFIC_RULES = {
    "MATH": """
- Questions should cover different math concepts (arithmetic, basic geometry, fractions, word problems, etc.)
- Word problems should use realistic scenarios relevant to {level} Level students
- Include a mix of direct calculation and reasoning questions
- Minimum 2 and maximum 3 operational steps per question
- Include visual elements like simple charts or diagrams
- Distractors should include common error patterns
""",
    "READING": """
- Passages should be 150-300 words, appropriate for {level} Level students
- Include a mix of literal and inferential questions
- Questions should assess main idea, details, inference, and vocabulary in context
""",
    "VERBAL": """
- Vocabulary words should be appropriate for {level} Level students
- Mix of synonym and analogy questions.
- Distractors should include words with similar sounds or partial meaning overlap
""",
    "ANALOGY": """
-Generate an SSAT-style analogy with the structure 'A : B → C : D
- Relationships should be clear and unambiguous
- Use common relationship types: part-whole, cause-effect, synonym, antonym, category
- Distractors should include pairs with incorrect relationship types
""",
    "SYNONYM": """
- Include a mix of common and academic vocabulary
- Synonyms should match the same part of speech as the target word
- Distractors should include words with similar sounds or related meanings
""",
    "WRITING": """
- Prompts should be clear and focused on one main writing task
"""
}


def generate_prompt(request: QuestionRequest) -> str:
    """Generate a prompt for the AI model based on the request."""
    prompt = f"generate {request.count} {request.question_type.value} questions"
    # Add topic focus if specified
    if request.topic:
        prompt += f" Focus on the topic: {request.topic}."
    # Add type-specific rules with formatted placeholders
    if request.question_type.value.upper() in TYPE_SPECIFIC_RULES:
        # Format the type-specific rules with the level
        formatted_rules = TYPE_SPECIFIC_RULES[request.question_type.value.upper()].format(
            level=request.level
        )
        prompt += formatted_rules
    else:
        raise ValueError(f"Unsupported question type: {request.question_type}")
    return prompt


def generate_questions(request: QuestionRequest, llm: Optional[str] = "openai") -> List[Question]:
    """Generate questions based on the request."""
    logger.info(f"Generating questions for request: {request}")
    
    system_message = SYSTEM_PROMPT.format(
        difficulty=request.difficulty.value,
        level=request.level,
        question_type=request.question_type.value
    )

    # logger.debug(f"System message: {system_message}")

    user_message = generate_prompt(request)
    # logger.debug(f"User message: {user_message}")
    try:
        # Check available providers
        available_providers = llm_client.get_available_providers()
        
        if not available_providers:
            raise ValueError("No LLM providers available. Please configure at least one API key in .env file")
        
        # Use specified provider or fall back to first available
        provider_name = llm.lower() if llm else available_providers[0].value
        
        try:
            provider = LLMProvider(provider_name)
        except ValueError:
            available_names = [p.value for p in available_providers]
            raise ValueError(f"Unsupported LLM provider: {llm}. Available providers: {available_names}")
        
        if provider not in available_providers:
            available_names = [p.value for p in available_providers]
            raise ValueError(f"Provider {provider.value} not available. Available providers: {available_names}")
        
        logger.info(f"Using LLM provider: {provider.value}")
        
        content = llm_client.call_llm(
            provider=provider,
            system_message=system_message,
            prompt=user_message,
        )

        if content is None:
            raise ValueError(f"LLM call to {provider.value} failed - no content returned")

        data = extract_json_from_text(content)
        
        questions = []
        for q_data in data["questions"]:
            options = [Option(letter=opt["letter"], text=opt["text"]) for opt in q_data["options"]]
            # Convert cognitive level to uppercase
            cognitive_level = q_data["cognitive_level"].upper()
            question = Question(
                question_type=request.question_type,
                difficulty=request.difficulty,
                text=q_data["text"],
                options=options,
                correct_answer=q_data["correct_answer"],
                explanation=q_data["explanation"],
                topic=request.topic,
                cognitive_level=cognitive_level,
                tags=q_data["tags"]
            )
            questions.append(question)
        
        return questions
    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Failed to parse AI response: {e}") 