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
            
            training_examples = response.data if response.data else []
            
            # Log each real SSAT reading example for debugging
            for i, example in enumerate(training_examples, 1):
                logger.info(f"REAL SSAT READING EXAMPLE {i}:")
                logger.info(f"  Passage: {example.get('passage', 'N/A')[:100] if example.get('passage') else 'N/A'}...")
                logger.info(f"  Question: {example.get('question', 'N/A')}")
                logger.info(f"  Choices: {example.get('choices', 'N/A')}")
                if example.get('answer') is not None:
                    logger.info(f"  Answer: {chr(65 + example['answer'])}")
                logger.info(f"  Passage Type: {example.get('passage_type', 'N/A')}")
                logger.info("---")
            
            if training_examples:
                logger.info(f"📚 READING TRAINING SUMMARY: Using {len(training_examples)} real SSAT reading examples")
            
            return training_examples
            
        except Exception as e:
            logger.warning(f"Failed to get reading training examples: {e}")
            return []
    
    def get_writing_training_examples(self, topic: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get writing prompt training examples from database."""
        try:
            # For now, return empty list since we don't have real writing training data
            # This function is ready for when writing prompts are properly uploaded to database
            logger.info("Writing training examples not yet available in database")
            return []
            
            # TODO: Implement when database has writing training examples
            # if topic:
            #     # Use embedding-based similarity search for specific topics
            #     topic_query = f"writing prompt {topic}"
            #     query_embedding = self.generate_embedding(topic_query)
            #     
            #     if query_embedding:
            #         response = self.supabase.rpc('get_writing_training_examples', {
            #             'query_embedding': query_embedding,
            #             'topic_filter': topic,
            #             'limit_count': 3
            #         }).execute()
            #         
            #         if response.data:
            #             return response.data
            # 
            # # Fallback: get random examples
            # response = self.supabase.rpc('get_writing_training_examples', {
            #     'limit_count': 3
            # }).execute()
            # 
            # return response.data if response.data else []
            
        except Exception as e:
            logger.warning(f"Failed to get writing training examples: {e}")
            return []
    
    def build_writing_few_shot_prompt(self, request: QuestionRequest, training_examples: List[Dict[str, Any]]) -> str:
        """Build few-shot prompt for writing prompts with real SSAT examples."""
        
        if not training_examples:
            # Fallback to generic prompt
            return self.build_generic_writing_prompt(request)
        
        examples_text = ""
        valid_examples = 0
        
        for i, example in enumerate(training_examples, 1):
            if not example.get('prompt'):
                continue
                
            valid_examples += 1
            visual_info = f"\nVisual Description: {example['visual_description']}" if example.get('visual_description') else ""
            
            example_text = f"""
REAL SSAT WRITING EXAMPLE {valid_examples}:
Prompt: {example['prompt']}{visual_info}
Tags: {', '.join(example.get('tags', []))}

"""
            examples_text += example_text
            
            logger.info(f"REAL SSAT WRITING EXAMPLE {valid_examples}:")
            logger.info(f"  Prompt: {example['prompt'][:100]}...")
            if example.get('visual_description'):
                logger.info(f"  Visual: {example['visual_description']}")
            logger.info("---")
        
        logger.info(f"📚 WRITING TRAINING SUMMARY: Using {valid_examples} real SSAT writing examples")
        
        system_prompt = f"""You are an expert SSAT Elementary writing prompt generator. Study these REAL writing prompts from official SSAT tests:

{examples_text}

Your task: Generate {request.count} NEW writing prompts that match the EXACT style and format of these examples.

CRITICAL REQUIREMENTS:
1. Follow the EXACT prompt structure and style from the examples
2. Create elementary-appropriate prompts (grades 3-4)
3. Include clear, engaging visual descriptions for picture prompts
4. Focus on creative storytelling with beginning, middle, and end
5. Use simple, age-appropriate language and concepts

"""
        
        if request.topic:
            system_prompt += f"6. Focus specifically on the topic: {request.topic}\n"
        
        system_prompt += """
OUTPUT FORMAT - Return ONLY a JSON object:
{
  "prompts": [
    {
      "prompt": "Complete writing prompt text here (JUST the creative prompt, NO instructions)",
      "visual_description": "Description of the picture that would accompany this prompt",
      "grade_level": "3-4",
      "story_elements": ["element1", "element2", "element3"],
      "prompt_type": "picture_story"
    }
  ]
}

IMPORTANT: Generate ONLY the creative writing prompt. Do NOT include instructions like "Write a story with beginning, middle, and end" - those will be added separately."""
        
        return system_prompt
    
    def build_generic_writing_prompt(self, request: QuestionRequest) -> str:
        """Build generic writing prompt when no training examples are available."""
        topic_guidance = f" related to {request.topic}" if request.topic else ""
        
        system_prompt = f"""You are an expert SSAT Elementary writing prompt generator. Create {request.count} engaging writing prompts for grades 3-4 students{topic_guidance}.

REQUIREMENTS:
1. Elementary-appropriate language and concepts (grades 3-4)
2. Each prompt should inspire creative storytelling with beginning, middle, and end
3. Include visual descriptions for picture-based prompts
4. Focus on themes like friendship, adventure, family, animals, or everyday experiences
5. Prompts should be clear and specific enough to guide student writing

"""
        
        if request.topic:
            system_prompt += f"6. Focus specifically on the topic: {request.topic}\n"
        
        system_prompt += """
OUTPUT FORMAT - Return ONLY a JSON object:
{
  "prompts": [
    {
      "prompt": "Complete writing prompt text here (JUST the creative prompt, NO instructions)",
      "visual_description": "Description of the picture that would accompany this prompt",
      "grade_level": "3-4",
      "story_elements": ["element1", "element2", "element3"],
      "prompt_type": "picture_story"
    }
  ]
}

IMPORTANT: Generate ONLY the creative writing prompt. Do NOT include instructions like "Write a story with beginning, middle, and end" - those will be added separately."""
        
        return system_prompt
    
    def build_few_shot_prompt(self, request: QuestionRequest, training_examples: List[Dict[str, Any]]) -> str:
        """Build few-shot prompt with real SSAT examples."""
        
        if not training_examples:
            # Fallback to generic prompt
            return self.build_generic_prompt(request)
        
        examples_text = ""
        valid_examples = 0
        
        for i, example in enumerate(training_examples, 1):
            # Include visual description if present
            visual_info = f"\nVisual Description: {example['visual_description']}" if example.get('visual_description') else ""
            
            # Skip examples with missing answer data
            if example.get('answer') is None:
                logger.debug(f"Skipping example {i} - missing answer data")
                continue
            
            valid_examples += 1
            example_text = f"""
REAL SSAT EXAMPLE {valid_examples}:
Question: {example['question']}{visual_info}
Choices: {example['choices']}
Correct Answer: {chr(65 + example['answer'])}  # Convert 0,1,2,3 to A,B,C,D
Explanation: {example['explanation']}
Difficulty: {example['difficulty']}
Subsection: {example['subsection']}

"""
            examples_text += example_text
            
            # Log each real SSAT example for debugging
            logger.info(f"REAL SSAT TRAINING EXAMPLE {valid_examples}:")
            logger.info(f"  Question: {example['question']}")
            logger.info(f"  Choices: {example['choices']}")
            logger.info(f"  Answer: {chr(65 + example['answer'])}")
            logger.info(f"  Difficulty: {example['difficulty']}")
            logger.info(f"  Subsection: {example['subsection']}")
            if example.get('visual_description'):
                logger.info(f"  Visual: {example['visual_description']}")
            logger.info("---")
        
        logger.info(f"📚 TRAINING SUMMARY: Using {valid_examples} real SSAT examples for {request.question_type.value} questions")
        
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
    
    def build_reading_few_shot_prompt(self, request: QuestionRequest, training_examples: List[Dict[str, Any]]) -> str:
        """Build few-shot prompt specifically for reading comprehension with real SSAT examples."""
        
        if not training_examples:
            # Fallback to generic prompt
            return self.build_generic_prompt(request)
        
        examples_text = ""
        valid_examples = 0
        
        for i, example in enumerate(training_examples, 1):
            # Skip examples with missing data - log what's missing
            missing_fields = []
            if not example.get('passage'):
                missing_fields.append('passage')
            if not example.get('question'):
                missing_fields.append('question')
            if example.get('answer') is None:
                missing_fields.append('answer')
            
            if missing_fields:
                logger.warning(f"Skipping reading example {i} - missing fields: {missing_fields}")
                logger.debug(f"Example {i} data keys: {list(example.keys())}")
                continue
            
            valid_examples += 1
            example_text = f"""
REAL SSAT READING EXAMPLE {valid_examples}:

PASSAGE:
{example['passage']}

QUESTION: {example['question']}
CHOICES: {example['choices']}
CORRECT ANSWER: {chr(65 + example['answer'])}
EXPLANATION: {example.get('explanation', 'N/A')}
PASSAGE TYPE: {example.get('passage_type', 'N/A')}

"""
            examples_text += example_text
        
        logger.info(f"📚 READING TRAINING SUMMARY: Using {valid_examples} real SSAT reading examples for {request.question_type.value} questions")
        
        system_prompt = f"""You are an expert SSAT reading comprehension question generator. Study these REAL SSAT reading examples from official tests:

{examples_text}

Your task: Generate {request.count} NEW reading comprehension questions that match the EXACT style, difficulty, and format of these examples.

CRITICAL REQUIREMENTS:
1. Create a reading passage first (similar length and style to examples)
2. Follow the EXACT question structure and phrasing style from the examples
3. Match the difficulty level: {request.difficulty.value}
4. Use the same answer choice format (A, B, C, D)
5. Questions must test reading comprehension skills
6. Suitable for elementary level students
7. Each question should have exactly 4 options

"""
        
        if request.topic:
            system_prompt += f"8. Focus the passage topic on: {request.topic}\n"
        
        system_prompt += """
OUTPUT FORMAT - Return ONLY a JSON object with SEPARATE passage and questions:
{
  "passage": {
    "text": "The complete reading passage goes here (similar length to examples)",
    "title": "Optional passage title",
    "passage_type": "fiction",
    "grade_level": "3-4",
    "topic": "passage topic"
  },
  "questions": [
    {
      "text": "Question about the passage (without repeating the passage)",
      "options": [
        {"letter": "A", "text": "option text"},
        {"letter": "B", "text": "option text"},
        {"letter": "C", "text": "option text"},
        {"letter": "D", "text": "option text"}
      ],
      "correct_answer": "A",
      "explanation": "detailed explanation",
      "cognitive_level": "UNDERSTAND",
      "tags": ["reading", "comprehension"],
      "visual_description": "Description of any visual elements in the passage"
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
    """Generate questions based on request with real SSAT training examples (non-reading questions only)."""
    logger.info(f"Generating questions for request: {request}")
    
    # Initialize generator
    generator = SSATGenerator()
    
    try:
        # Reading comprehension should use generate_reading_passage() instead
        if request.question_type.value == "reading":
            raise ValueError("Reading comprehension questions should use generate_reading_passage() function instead of generate_questions()")
        
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
        
        # Parse generated questions (non-reading questions only)
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

def generate_reading_passage(request: QuestionRequest, llm: Optional[str] = "deepseek") -> Dict[str, Any]:
    """Generate a reading passage with questions specifically for reading comprehension."""
    logger.info(f"Generating reading passage for request: {request}")
    
    # Initialize generator
    generator = SSATGenerator()
    
    try:
        # Get reading training examples
        training_examples = generator.get_reading_training_examples()
        system_message = generator.build_reading_few_shot_prompt(request, training_examples)
        
        # Log training info
        if training_examples:
            logger.info(f"Using {len(training_examples)} real SSAT reading examples for training")
        else:
            logger.info("No reading training examples found, using generic prompt")
        
        # Get available LLM providers
        from app.llm import llm_client, LLMProvider
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
        
        # Generate passage and questions using LLM
        content = llm_client.call_llm(
            provider=provider,
            system_message=system_message,
            prompt="Generate the reading passage and questions as specified.",
        )

        if content is None:
            raise ValueError(f"LLM call to {provider.value} failed - no content returned")

        from app.util import extract_json_from_text
        data = extract_json_from_text(content)
        
        if data is None:
            raise ValueError("Failed to extract JSON from LLM response")
        
        # Validate response has both passage and questions
        if "passage" not in data or "questions" not in data:
            raise ValueError("LLM response missing passage or questions structure")
        
        passage_data = data["passage"]
        questions_data = data["questions"]
        
        # Parse questions into proper format
        from app.core_models import Option, Question
        questions = []
        for q_data in questions_data:
            options = [Option(letter=opt["letter"], text=opt["text"]) for opt in q_data["options"]]
            cognitive_level = q_data.get("cognitive_level", "UNDERSTAND").upper()
            question = Question(
                question_type=request.question_type,
                difficulty=request.difficulty,
                text=q_data["text"],  # Just the question, not the passage
                options=options,
                correct_answer=q_data["correct_answer"],
                explanation=q_data["explanation"],
                cognitive_level=cognitive_level,
                tags=q_data.get("tags", []),
                visual_description=q_data.get("visual_description")
            )
            questions.append(question)
        
        logger.info(f"Successfully generated reading passage with {len(questions)} questions using {'real SSAT examples' if training_examples else 'generic prompt'}")
        
        return {
            "passage": passage_data,
            "questions": questions
        }
        
    except Exception as e:
        logger.error(f"Error in reading passage generation: {e}")
        raise

async def generate_reading_passage_async(request: QuestionRequest, llm: Optional[str] = "deepseek") -> Dict[str, Any]:
    """Async version of generate_reading_passage for true parallel execution."""
    logger.info(f"Generating reading passage async for request: {request}")
    
    # Initialize generator
    generator = SSATGenerator()
    
    try:
        # Get reading training examples
        training_examples = generator.get_reading_training_examples()
        system_message = generator.build_reading_few_shot_prompt(request, training_examples)
        
        # Log training info
        if training_examples:
            logger.info(f"Using {len(training_examples)} real SSAT reading examples for training")
        else:
            logger.info("No reading training examples found, using generic prompt")
        
        # Get available LLM providers
        from app.llm import llm_client, LLMProvider
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
        
        # Generate passage and questions using async LLM call
        content = await llm_client.call_llm_async(
            provider=provider,
            system_message=system_message,
            prompt="Generate the reading passage and questions as specified.",
        )

        if content is None:
            raise ValueError(f"LLM call to {provider.value} failed - no content returned")

        from app.util import extract_json_from_text
        data = extract_json_from_text(content)
        
        if data is None:
            raise ValueError("Failed to extract JSON from LLM response")
        
        # Validate response has both passage and questions
        if "passage" not in data or "questions" not in data:
            raise ValueError("LLM response missing passage or questions structure")
        
        passage_data = data["passage"]
        questions_data = data["questions"]
        
        # Parse questions into proper format
        from app.core_models import Option, Question
        questions = []
        for q_data in questions_data:
            options = [Option(letter=opt["letter"], text=opt["text"]) for opt in q_data["options"]]
            cognitive_level = q_data.get("cognitive_level", "UNDERSTAND").upper()
            question = Question(
                question_type=request.question_type,
                difficulty=request.difficulty,
                text=q_data["text"],  # Just the question, not the passage
                options=options,
                correct_answer=q_data["correct_answer"],
                explanation=q_data["explanation"],
                cognitive_level=cognitive_level,
                tags=q_data.get("tags", []),
                visual_description=q_data.get("visual_description")
            )
            questions.append(question)
        
        logger.info(f"Successfully generated reading passage async with {len(questions)} questions using {'real SSAT examples' if training_examples else 'generic prompt'}")
        
        return {
            "passage": passage_data,
            "questions": questions
        }
        
    except Exception as e:
        logger.error(f"Error in async reading passage generation: {e}")
        raise

async def generate_questions_async(request: QuestionRequest, llm: Optional[str] = "deepseek") -> List[Question]:
    """Async version of generate_questions for true parallel execution (non-reading questions only)."""
    logger.info(f"Generating questions async for request: {request}")
    
    # Initialize generator
    generator = SSATGenerator()
    
    try:
        # Reading comprehension should use generate_reading_passage_async() instead
        if request.question_type.value == "reading":
            raise ValueError("Reading comprehension questions should use generate_reading_passage_async() function instead of generate_questions_async()")
        
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
        
        # Parse generated questions (non-reading questions only)
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