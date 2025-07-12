"""SSAT question generator using real SSAT examples for training."""

import json
import random
from typing import List, Optional, Dict, Any
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer

from app.core_models import Question, Option, QuestionRequest
from loguru import logger
from app.llm import llm_client, LLMProvider
from app.util import extract_json_from_text
from app.settings import settings

class SSATGenerator:
    """SSAT question generator with training examples from database."""
    
    def __init__(self):
        """Initialize generator with Supabase connection and embedding model."""
        self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')  # 384 dimensions
        logger.info("SSAT Generator initialized with database connection")
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using Sentence-Transformers."""
        try:
            embedding = self.embedding_model.encode(text).tolist()
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return []
    
    def get_training_examples(self, request: QuestionRequest) -> List[Dict[str, Any]]:
        """Get real SSAT questions as training examples from database using embeddings."""
        try:
            # Map QuestionType to database sections and subsections
            section_mapping = {
                "quantitative": ("Quantitative", None),
                "verbal": ("Verbal", None),  # Get mixed verbal examples
                "analogy": ("Verbal", "Analogies"),  # Get only analogy examples
                "synonym": ("Verbal", "Synonyms")    # Get only synonym examples
            }
            
            section_filter, subsection_filter = section_mapping.get(
                request.question_type.value, 
                (request.question_type.value.title(), None)
            )
            
            if request.topic:
                # Use embedding-based similarity search for specific topics
                # Hybrid approach: get top 15, randomly select 5
                topic_query = f"{request.topic} {request.question_type.value}"
                query_embedding = self.generate_embedding(topic_query)
                
                if query_embedding:
                    response = self.supabase.rpc('get_training_examples_by_embedding', {
                        'query_embedding': query_embedding,
                        'section_filter': section_filter,
                        'subsection_filter': subsection_filter,
                        'difficulty_filter': request.difficulty.value.title(),
                        'limit_count': 15  # Get more candidates
                    }).execute()
                    
                    if response.data:
                        # Randomly select 5 from the top 15 most similar
                        candidates = response.data
                        selected_count = min(5, len(candidates))
                        return random.sample(candidates, selected_count)
            
            # Fallback: get examples by section only (when no topic or embedding fails)
            # Also use hybrid approach: get more candidates, randomly select
            response = self.supabase.rpc('get_training_examples_by_section', {
                'section_filter': section_filter,
                'subsection_filter': subsection_filter,
                'difficulty_filter': request.difficulty.value.title(),
                'limit_count': 15  # Get more candidates for diversity
            }).execute()
            
            if response.data:
                # Randomly select 5 from available candidates
                candidates = response.data
                selected_count = min(5, len(candidates))
                return random.sample(candidates, selected_count)
            
            return []
                
        except Exception as e:
            logger.warning(f"Failed to get training examples: {e}")
            # Return empty list to fall back to generic prompts
            return []
    
    def get_reading_training_examples(self, passage_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get reading comprehension training examples."""
        try:
            response = self.supabase.rpc('get_reading_training_examples', {
                'passage_type_filter': passage_type,
                'limit_count': 2
            }).execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.warning(f"Failed to get reading training examples: {e}")
            return []
    
    def build_few_shot_prompt(self, request: QuestionRequest, training_examples: List[Dict[str, Any]]) -> str:
        """Build few-shot prompt with real SSAT examples."""
        
        if not training_examples:
            # Fallback to generic prompt
            return self.build_generic_prompt(request)
        
        examples_text = ""
        for i, example in enumerate(training_examples, 1):
            # Include visual description if present
            visual_info = f"\nVisual Description: {example['visual_description']}" if example.get('visual_description') else ""
            
            # Skip examples with missing answer data
            if example.get('answer') is None:
                continue
                
            examples_text += f"""
REAL SSAT EXAMPLE {i}:
Question: {example['question']}{visual_info}
Choices: {example['choices']}
Correct Answer: {chr(65 + example['answer'])}  # Convert 0,1,2,3 to A,B,C,D
Explanation: {example['explanation']}
Difficulty: {example['difficulty']}
Subsection: {example['subsection']}

"""
        
        system_prompt = f"""You are an expert SSAT question generator. Study these REAL SSAT questions from official tests:

{examples_text}

Your task: Generate {request.count} NEW {request.question_type.value} questions that match the EXACT style, difficulty, and format of these examples.

CRITICAL REQUIREMENTS:
1. Follow the EXACT question structure and phrasing style from the examples
2. Match the difficulty level: {request.difficulty.value}
3. Use the same answer choice format (A, B, C, D)
4. Provide detailed explanations like the examples
5. Questions must be suitable for elementary level students
6. Each question should have exactly 4 options

"""
        
        if request.topic:
            system_prompt += f"7. Focus specifically on the topic: {request.topic}\n"
        
        system_prompt += """
OUTPUT FORMAT - Return ONLY a JSON object:
{
  "questions": [
    {
      "text": "Complete question text here",
      "options": [
        {"letter": "A", "text": "option text"},
        {"letter": "B", "text": "option text"},
        {"letter": "C", "text": "option text"},
        {"letter": "D", "text": "option text"}
      ],
      "correct_answer": "A",
      "explanation": "detailed explanation",
      "cognitive_level": "REMEMBER",
      "tags": ["tag1", "tag2"],
      "visual_description": "Description of any diagrams, charts, or visual elements (if applicable)"
    }
  ]
}"""
        
        return system_prompt
    
    def build_generic_prompt(self, request: QuestionRequest) -> str:
        """Fallback generic prompt when no training examples available."""
        
        type_specific_rules = {
            "quantitative": "Focus on arithmetic, fractions, basic geometry, and word problems suitable for elementary students.",
            "verbal": "Focus on vocabulary appropriate for elementary students, including synonyms and analogies.",
            "analogy": "Create analogies with clear relationships that elementary students can understand.",
            "synonym": "Use vocabulary words appropriate for grades 3-4.",
            "reading": "Create passages and questions appropriate for elementary reading level.",
            "writing": "Create clear, focused writing prompts for elementary students."
        }
        
        rules = type_specific_rules.get(request.question_type.value, "Generate appropriate elementary-level questions.")
        
        return f"""You are an expert SSAT Elementary Level question designer.

Generate {request.count} high-quality {request.question_type.value} questions with {request.difficulty.value} difficulty.

REQUIREMENTS:
1. Each question has exactly 4 options (A, B, C, D)
2. Include detailed explanations
3. Suitable for elementary level students
4. {rules}

{'Focus on topic: ' + request.topic if request.topic else ''}

Return JSON format:
{{
  "questions": [
    {{
      "text": "question text",
      "options": [{{"letter": "A", "text": "option"}}, ...],
      "correct_answer": "A",
      "explanation": "explanation",
      "cognitive_level": "REMEMBER",
      "tags": ["tag1", "tag2"],
      "visual_description": "Description of any visual elements (if applicable)"
    }}
  ]
}}"""

def generate_questions(request: QuestionRequest, llm: Optional[str] = "deepseek") -> List[Question]:
    """Generate questions based on request with real SSAT training examples."""
    logger.info(f"Generating questions for request: {request}")
    
    # Initialize generator
    generator = SSATGenerator()
    
    try:
        # Get training examples from database
        if request.question_type.value == "reading":
            # Handle reading comprehension differently
            training_examples = generator.get_reading_training_examples()
            # For reading, you might want to generate passages + questions
            # This is a simplified version - you could expand this
            system_message = generator.build_generic_prompt(request)
        else:
            # Get math/verbal training examples
            training_examples = generator.get_training_examples(request)
            system_message = generator.build_few_shot_prompt(request, training_examples)
        
        # Log training info
        if training_examples:
            logger.info(f"Using {len(training_examples)} real SSAT examples for training")
        else:
            logger.info("No training examples found, using generic prompt")
        
        # Get available LLM providers
        available_providers = llm_client.get_available_providers()
        
        if not available_providers:
            raise ValueError("No LLM providers available. Please configure at least one API key in .env file")
        
        # Use specified provider or fall back to preferred provider order
        if llm:
            provider_name = llm.lower()
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
            raise ValueError(f"Unsupported LLM provider: {llm}. Available providers: {available_names}")
        
        if provider not in available_providers:
            available_names = [p.value for p in available_providers]
            raise ValueError(f"Provider {provider.value} not available. Available providers: {available_names}")
        
        logger.info(f"Using LLM provider: {provider.value}")
        
        # Generate questions using LLM
        content = llm_client.call_llm(
            provider=provider,
            system_message=system_message,
            prompt="Generate the questions as specified.",
        )

        if content is None:
            raise ValueError(f"LLM call to {provider.value} failed - no content returned")

        data = extract_json_from_text(content)
        
        if data is None:
            raise ValueError("Failed to extract JSON from LLM response")
        
        # Parse generated questions
        questions = []
        for q_data in data["questions"]:
            options = [Option(letter=opt["letter"], text=opt["text"]) for opt in q_data["options"]]
            # Convert cognitive level to uppercase
            cognitive_level = q_data.get("cognitive_level", "UNDERSTAND").upper()
            question = Question(
                question_type=request.question_type,
                difficulty=request.difficulty,
                text=q_data["text"],
                options=options,
                correct_answer=q_data["correct_answer"],
                explanation=q_data["explanation"],
                cognitive_level=cognitive_level,
                tags=q_data.get("tags", []),
                visual_description=q_data.get("visual_description")
            )
            questions.append(question)
        
        logger.info(f"Successfully generated {len(questions)} questions using {'real SSAT examples' if training_examples else 'generic prompt'}")
        return questions
        
    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Failed to parse AI response: {e}")
    except Exception as e:
        logger.error(f"Error in question generation: {e}")
        raise

async def generate_questions_async(request: QuestionRequest, llm: Optional[str] = "deepseek") -> List[Question]:
    """Async version of generate_questions for true parallel execution."""
    logger.info(f"Generating questions async for request: {request}")
    
    # Initialize generator
    generator = SSATGenerator()
    
    try:
        # Get training examples from database
        if request.question_type.value == "reading":
            # Handle reading comprehension differently
            training_examples = generator.get_reading_training_examples()
            system_message = generator.build_generic_prompt(request)
        else:
            # Get math/verbal training examples
            training_examples = generator.get_training_examples(request)
            system_message = generator.build_few_shot_prompt(request, training_examples)
        
        # Log training info
        if training_examples:
            logger.info(f"Using {len(training_examples)} real SSAT examples for training")
        else:
            logger.info("No training examples found, using generic prompt")
        
        # Get available LLM providers
        available_providers = llm_client.get_available_providers()
        
        if not available_providers:
            raise ValueError("No LLM providers available. Please configure at least one API key in .env file")
        
        # Use specified provider or fall back to preferred provider order
        if llm:
            provider_name = llm.lower()
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
            raise ValueError(f"Unsupported LLM provider: {llm}. Available providers: {available_names}")
        
        if provider not in available_providers:
            available_names = [p.value for p in available_providers]
            raise ValueError(f"Provider {provider.value} not available. Available providers: {available_names}")
        
        logger.info(f"Using LLM provider: {provider.value}")
        
        # Generate questions using async LLM call for true parallelism
        content = await llm_client.call_llm_async(
            provider=provider,
            system_message=system_message,
            prompt="Generate the questions as specified.",
        )

        if content is None:
            raise ValueError(f"LLM call to {provider.value} failed - no content returned")

        data = extract_json_from_text(content)
        
        if data is None:
            raise ValueError("Failed to extract JSON from LLM response")
        
        # Parse generated questions
        questions = []
        for q_data in data["questions"]:
            options = [Option(letter=opt["letter"], text=opt["text"]) for opt in q_data["options"]]
            # Convert cognitive level to uppercase
            cognitive_level = q_data.get("cognitive_level", "UNDERSTAND").upper()
            question = Question(
                question_type=request.question_type,
                difficulty=request.difficulty,
                text=q_data["text"],
                options=options,
                correct_answer=q_data["correct_answer"],
                explanation=q_data["explanation"],
                cognitive_level=cognitive_level,
                tags=q_data.get("tags", []),
                visual_description=q_data.get("visual_description")
            )
            questions.append(question)
        
        logger.info(f"Successfully generated {len(questions)} questions async using {'real SSAT examples' if training_examples else 'generic prompt'}")
        return questions
        
    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Failed to parse AI response: {e}")
    except Exception as e:
        logger.error(f"Error in async question generation: {e}")
        raise