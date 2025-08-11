"""SSAT question generator using real SSAT examples for training."""

import asyncio
import json
from math import e
import random
import uuid
from typing import List, Optional, Dict, Any
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer

from app.models.base import Question, Option, QuestionRequest
from loguru import logger
from app.llm import llm_client, LLMProvider
from app.util import extract_json_from_text
from app.settings import settings
from app.services.embedding_service import get_embedding_service

logger = logger

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

class SSATGenerator:
    """SSAT question generator with training examples from database."""
    
    def __init__(self):
        """Initialize generator with Supabase connection and shared embedding service."""
        self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        self.embedding_service = get_embedding_service()
        logger.info("SSAT Generator initialized with database connection and shared embedding service")
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding using the shared embedding service."""
        return self.embedding_service.generate_embedding(text)
    
    def parse_custom_examples(self, custom_examples_text: str, question_type: str) -> List[Dict[str, Any]]:
        """Parse custom training examples from text input."""
        if not custom_examples_text or not custom_examples_text.strip():
            return []
        
        logger.info(f"🔍 DEBUG: Parsing custom examples for {question_type}")
        logger.info(f"🔍 DEBUG: Custom examples text: {custom_examples_text[:200]}...")
        
        # For reading passages, we need to parse the entire passage with all questions as one example
        if question_type == "reading":
            return self._parse_reading_passage_example(custom_examples_text)
        
        # For other question types, parse individual questions
        examples = []
        lines = custom_examples_text.strip().split('\n')
        current_example = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                # Empty line indicates end of current example
                if current_example:
                    if self._validate_example_format(current_example, question_type):
                        logger.info(f"🔍 DEBUG: Valid example parsed: {current_example.get('question', '')[:50]}...")
                        examples.append(current_example.copy())
                    else:
                        logger.warning(f"🔍 DEBUG: Invalid example skipped: {current_example}")
                    current_example = {}
                continue
            
            # Parse different question types
            if question_type in ["quantitative", "analogy", "synonym"]:
                current_example = self._parse_verbal_question_line(line, current_example)
            elif question_type == "writing":
                current_example = self._parse_writing_line(line, current_example)
        
        # Don't forget the last example
        if current_example and self._validate_example_format(current_example, question_type):
            logger.info(f"🔍 DEBUG: Valid final example parsed: {current_example.get('question', '')[:50]}...")
            examples.append(current_example)
        
        logger.info(f"🔍 DEBUG: Parsed {len(examples)} custom training examples for {question_type}")
        for i, example in enumerate(examples):
            logger.info(f"🔍 DEBUG: Example {i+1}: question='{example.get('question', '')[:50]}...', answer={example.get('answer')}, choices={example.get('choices')}")
        
        return examples
    
    def _parse_verbal_question_line(self, line: str, current_example: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a line for verbal questions (quantitative, analogy, synonym)."""
        line_lower = line.lower()
        
        if line_lower.startswith('question:'):
            current_example['question'] = line[9:].strip()
        elif line_lower.startswith('choices:'):
            choices_text = line[8:].strip()
            # Parse choices like "A) 40; B) 42; C) 43; D) 44" or "A) 40, B) 42, C) 43, D) 44"
            choices = []
            # Try semicolon first, then fall back to comma
            if ';' in choices_text:
                choice_parts = choices_text.split(';')
            else:
                choice_parts = choices_text.split(',')
            
            for choice in choice_parts:
                choice = choice.strip()
                if ')' in choice:
                    letter, text = choice.split(')', 1)
                    choices.append(text.strip())
                else:
                    choices.append(choice)
            current_example['choices'] = choices
        elif line_lower.startswith('correct answer:'):
            answer_text = line[15:].strip().upper()
            # Convert A,B,C,D to 0,1,2,3
            answer_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
            current_example['answer'] = answer_map.get(answer_text, 0)
        elif line_lower.startswith('explanation:'):
            current_example['explanation'] = line[12:].strip()
        elif line_lower.startswith('difficulty:'):
            current_example['difficulty'] = line[11:].strip()
        elif line_lower.startswith('subsection:'):
            current_example['subsection'] = line[11:].strip()
        elif line_lower.startswith('visual description:'):
            current_example['visual_description'] = line[19:].strip()
        
        return current_example
    
    def _parse_reading_line(self, line: str, current_example: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a line for reading passages."""
        line_lower = line.lower()
        
        if line_lower.startswith('passage:'):
            # Start new passage
            if current_example.get('passage'):
                # Previous passage is complete, start new one
                current_example = {}
            current_example['passage'] = line[8:].strip()
        elif line_lower.startswith('question:'):
            current_example['question'] = line[9:].strip()
        elif line_lower.startswith('choices:'):
            choices_text = line[8:].strip()
            choices = []
            # Try semicolon first, then fall back to comma
            if ';' in choices_text:
                choice_parts = choices_text.split(';')
            else:
                choice_parts = choices_text.split(',')
            
            for choice in choice_parts:
                choice = choice.strip()
                if ')' in choice:
                    letter, text = choice.split(')', 1)
                    choices.append(text.strip())
                else:
                    choices.append(choice)
            current_example['choices'] = choices
        elif line_lower.startswith('correct answer:'):
            answer_text = line[15:].strip().upper()
            answer_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
            current_example['answer'] = answer_map.get(answer_text, 0)
        elif line_lower.startswith('explanation:'):
            current_example['explanation'] = line[12:].strip()
        elif line_lower.startswith('passage type:'):
            current_example['passage_type'] = line[13:].strip()
        
        return current_example
    
    def _parse_reading_passage_example(self, text: str) -> List[Dict[str, Any]]:
        """Parse a complete reading passage with all its questions as one example."""
        lines = text.strip().split('\n')
        passage_data = {}
        questions = []
        current_question = {}
        in_passage = True
        passage_difficulty = 'Medium'  # Default difficulty
        passage_text_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if we're starting a new question (indicates end of passage)
            if line.lower().startswith('question:'):
                # Save any accumulated passage text
                if passage_text_lines and not passage_data.get('passage'):
                    passage_data['passage'] = '\n'.join(passage_text_lines)
                in_passage = False
                
                # Process the question
                if current_question:
                    if self._validate_reading_question(current_question):
                        questions.append(current_question.copy())
                    current_question = {}
                
                # Start new question
                current_question['question'] = line[9:].strip()
                continue
            
            if in_passage:
                if line.lower().startswith('passage:'):
                    # Start collecting passage text
                    passage_text_lines = [line[8:].strip()]
                elif line.lower().startswith('passage type:'):
                    passage_data['passage_type'] = line[13:].strip()
                elif line.lower().startswith('difficulty:'):
                    passage_difficulty = line[11:].strip()
                elif line.lower().startswith('tags:'):
                    tags_text = line[5:].strip()
                    passage_data['tags'] = [tag.strip() for tag in tags_text.split(',')]
                elif passage_text_lines:
                    # Continue adding to passage text
                    passage_text_lines.append(line)
                elif not passage_data.get('passage'):
                    # If no "Passage:" label, treat the first non-empty line as passage
                    passage_text_lines = [line]
            else:
                # Parse questions
                if line.lower().startswith('choices:'):
                    choices_text = line[8:].strip()
                    choices = []
                    # Try semicolon first, then fall back to comma
                    if ';' in choices_text:
                        choice_parts = choices_text.split(';')
                    else:
                        choice_parts = choices_text.split(',')
                    
                    for choice in choice_parts:
                        choice = choice.strip()
                        if ')' in choice:
                            letter, text = choice.split(')', 1)
                            choices.append(text.strip())
                        else:
                            choices.append(choice)
                    current_question['choices'] = choices
                elif line.lower().startswith('correct answer:'):
                    answer_text = line[15:].strip().upper()
                    answer_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
                    current_question['answer'] = answer_map.get(answer_text, 0)
                elif line.lower().startswith('explanation:'):
                    current_question['explanation'] = line[12:].strip()
        
        # Don't forget the last question
        if current_question and self._validate_reading_question(current_question):
            questions.append(current_question)
        
        # Apply passage difficulty to all questions
        for question in questions:
            question['difficulty'] = passage_difficulty
        
        # Ensure we have both passage and questions
        if not passage_data.get('passage'):
            logger.warning("🔍 DEBUG: No passage text found")
            return []
        if not questions:
            logger.warning("🔍 DEBUG: No questions found")
            return []
        
        # Return as a single example with passage and all questions
        example = {
            'passage': passage_data['passage'],
            'passage_type': passage_data.get('passage_type', 'General'),
            'difficulty': passage_difficulty,
            'questions': questions
        }
        
        logger.info(f"🔍 DEBUG: Parsed reading passage with {len(questions)} questions")
        return [example]
    
    def _validate_reading_question(self, question: Dict[str, Any]) -> bool:
        """Validate reading question has required fields."""
        required = ['question', 'choices', 'answer']
        if not all(field in question for field in required):
            return False
        if not isinstance(question.get('choices'), list) or len(question['choices']) != 4:
            return False
        if question.get('answer') not in [0, 1, 2, 3]:
            return False
        return True
    
    def _parse_writing_line(self, line: str, current_example: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a line for writing prompts."""
        line_lower = line.lower()
        
        if line_lower.startswith('prompt:'):
            current_example['prompt'] = line[7:].strip()
        elif line_lower.startswith('visual description:'):
            current_example['visual_description'] = line[19:].strip()
        elif line_lower.startswith('grade level:'):
            current_example['grade_level'] = line[12:].strip()
        elif line_lower.startswith('prompt type:'):
            current_example['prompt_type'] = line[12:].strip()
        elif line_lower.startswith('subsection:'):
            current_example['subsection'] = line[11:].strip()
        elif line_lower.startswith('tags:'):
            tags_text = line[5:].strip()
            # Parse tags like "teamwork-themes, problem-solving-process, character-interaction"
            current_example['tags'] = [tag.strip() for tag in tags_text.split(',')]
        
        return current_example
    
    def _validate_example_format(self, example: Dict[str, Any], question_type: str) -> bool:
        """Validate that an example has the required fields for its type."""
        if question_type in ["quantitative", "analogy", "synonym"]:
            required_fields = ['question', 'choices', 'answer']
            if not all(field in example for field in required_fields):
                return False
            # Ensure choices is a list and answer is valid
            if not isinstance(example.get('choices'), list) or len(example['choices']) != 4:
                return False
            if example.get('answer') not in [0, 1, 2, 3]:
                return False
        elif question_type == "reading":
            # For reading, we expect a complete passage with questions
            required_fields = ['passage', 'questions']
            if not all(field in example for field in required_fields):
                return False
            # Validate that we have at least one question
            if not isinstance(example.get('questions'), list) or len(example['questions']) == 0:
                return False
        elif question_type == "writing":
            required_fields = ['prompt']
            if not all(field in example for field in required_fields):
                return False
        
        return True

    def get_training_examples(self, request: QuestionRequest, custom_examples: Optional[str] = None, count: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get training examples - either from database or custom examples."""
        # If custom examples are provided, parse and use them
        if custom_examples and custom_examples.strip():
            logger.info(f"Using custom training examples for {request.question_type.value}")
            return self.parse_custom_examples(custom_examples, request.question_type.value)
        
        # Otherwise, use database examples with unified hybrid approach
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
            
            # Determine example count based on question type
            if request.question_type.value == "quantitative" and count is not None:
                # For quantitative: use dynamic count (1-10)
                target_count = min(max(count, 1), 10)  # Cap at 10
                logger.info(f"📚 Using dynamic count for quantitative: {target_count} examples")
            else:
                # For analogy/synonym: keep current fixed count (5)
                target_count = 5
                logger.info(f"📚 Using fixed count for {request.question_type.value}: {target_count} examples")
            
            # Generate embedding if topic is provided
            query_embedding = None
            if request.topic:
                topic_query = f"{request.topic} {request.question_type.value}"
                query_embedding = self.generate_embedding(topic_query)
                if query_embedding:
                    logger.info(f"Generated embedding for topic query: '{topic_query}'")
                else:
                    logger.warning(f"Failed to generate embedding for topic query: '{topic_query}'")
            
            # Use unified hybrid function for all cases
            response = self.supabase.rpc('get_training_examples_hybrid', {
                'topic_filter': request.topic,
                'section_filter': section_filter,
                'subsection_filter': subsection_filter,
                'difficulty_filter': request.difficulty.value.title(),
                'query_embedding': query_embedding,
                'limit_count': target_count
            }).execute()
            
            if response.data:
                training_examples = response.data
                logger.info(f"Found {len(training_examples)} training examples for {request.question_type.value} "
                          f"(topic: {request.topic or 'none'}, method: {training_examples[0].get('search_method', 'unknown')})")
                
                # For quantitative questions without specific topic, ensure diversity across subsections
                if request.question_type.value == "quantitative" and not request.topic:
                    # Try to select examples from different subsections
                    diverse_examples = []
                    used_subsections = set()
                    
                    # First pass: try to get one example from each subsection
                    from app.specifications import QUANTITATIVE_SUBSECTIONS
                    for subsection in QUANTITATIVE_SUBSECTIONS:
                        for candidate in training_examples:
                            if candidate.get('subsection') == subsection and subsection not in used_subsections:
                                diverse_examples.append(candidate)
                                used_subsections.add(subsection)
                                break
                    
                    # If we don't have enough diverse examples, fill with random ones
                    if len(diverse_examples) < target_count:
                        remaining_candidates = [c for c in training_examples if c not in diverse_examples]
                        if remaining_candidates:
                            additional_needed = target_count - len(diverse_examples)
                            additional_examples = random.sample(remaining_candidates, min(additional_needed, len(remaining_candidates)))
                            diverse_examples.extend(additional_examples)
                    
                    # Return diverse examples (or fall back to original if not enough)
                    if diverse_examples:
                        logger.info(f"📚 Selected {len(diverse_examples)} diverse training examples across {len(used_subsections)} subsections")
                        return diverse_examples[:target_count]
                
                # Return the examples (remove search_method field for compatibility)
                for example in training_examples:
                    example.pop('search_method', None)
                
                return training_examples
            
            logger.warning(f"No training examples found for {request.question_type.value} (topic: {request.topic or 'none'})")
            return []
                
        except Exception as e:
            logger.warning(f"Failed to get training examples: {e}")
            # Return empty list to fall back to generic prompts
            return []
    
    def get_reading_training_examples(self, passage_type: Optional[str] = None, topic: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get reading comprehension training examples using unified hybrid approach."""
        try:
            # Generate embedding if topic is provided
            query_embedding = None
            if topic:
                topic_query = f"{topic} reading comprehension"
                query_embedding = self.generate_embedding(topic_query)
                if query_embedding:
                    logger.info(f"Generated embedding for reading topic query: '{topic_query}'")
                else:
                    logger.warning(f"Failed to generate embedding for reading topic query: '{topic_query}'")
            
            # Use unified hybrid function for all cases
            response = self.supabase.rpc('get_reading_training_examples_hybrid', {
                'topic_filter': topic,
                'passage_type_filter': passage_type,
                'query_embedding': query_embedding,
                'limit_count': 3
            }).execute()
            
            if response.data:
                training_examples = response.data
                logger.info(f"Found {len(training_examples)} reading training examples "
                          f"(topic: {topic or 'none'}, method: {training_examples[0].get('search_method', 'unknown')})")
                
                # Remove search_method field for compatibility
                for example in training_examples:
                    example.pop('search_method', None)
                
                return training_examples
            
            logger.warning(f"No reading training examples found (topic: {topic or 'none'})")
            return []
            
        except Exception as e:
            logger.warning(f"Failed to get reading training examples: {e}")
            return []
    
    def get_writing_training_examples(self, topic: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get writing prompt training examples using unified hybrid approach."""
        try:
            # Generate embedding if topic is provided
            query_embedding = None
            if topic:
                topic_query = f"{topic} writing prompt"
                query_embedding = self.generate_embedding(topic_query)
                if query_embedding:
                    logger.info(f"Generated embedding for writing topic query: '{topic_query}'")
                else:
                    logger.warning(f"Failed to generate embedding for writing topic query: '{topic_query}'")
            
            # Use unified hybrid function for all cases
            response = self.supabase.rpc('get_writing_training_examples_hybrid', {
                'topic_filter': topic,
                'query_embedding': query_embedding,
                'limit_count': 3
            }).execute()
            
            if response.data:
                training_examples = response.data
                logger.info(f"Found {len(training_examples)} writing training examples "
                          f"(topic: {topic or 'none'}, method: {training_examples[0].get('search_method', 'unknown')})")
                
                # Remove search_method field for compatibility
                for example in training_examples:
                    example.pop('search_method', None)
                
                return training_examples
            
            logger.warning(f"No writing training examples found (topic: {topic or 'none'})")
            return []
            
        except Exception as e:
            logger.warning(f"Failed to get writing training examples: {e}")
            return []
    
    def build_writing_few_shot_prompt(self, request: QuestionRequest, training_examples: List[Dict[str, Any]]) -> str:
        """Build few-shot prompt by extending base writing prompt with examples."""
        
        if not training_examples:
            # Use base writing prompt without examples
            logger.info(f"📚 No writing training examples available, using base writing prompt")
            return self.build_base_writing_prompt(request)
        
        examples_text = ""
        valid_examples = 0
        
        for i, example in enumerate(training_examples, 1):
            if not example.get('prompt'):
                continue
                
            valid_examples += 1
            example_text = f"""
REAL SSAT WRITING EXAMPLE {valid_examples}:
Prompt: {example['prompt']}
Visual Description: {example.get('visual_description', 'N/A')}
Grade Level: {example.get('grade_level', 'N/A')}
Prompt Type: {example.get('prompt_type', 'N/A')}
Subsection: {example.get('subsection', 'N/A')}
Tags: {example.get('tags', [])}

"""
            examples_text += example_text
        
        logger.info(f"📚 WRITING TRAINING SUMMARY: Using {valid_examples} real SSAT writing examples")
        
        # SIMPLIFIED WRITING PROMPT: Examples first, minimal instructions
        complete_prompt = f"""You are an expert SSAT Elementary writing prompt generator.

STUDY THESE REAL WRITING PROMPTS FROM OFFICIAL SSAT TESTS:

{examples_text}

GENERATE {request.count} NEW WRITING PROMPTS about the SAME TOPIC/THEME as these examples.

{self._get_difficulty_specific_instructions(request.difficulty.value)}

CRITICAL REQUIREMENTS:
- Generate prompts about the SAME TOPIC/THEME as the examples (e.g., if example is about friendship, generate more friendship-related prompts)
- Follow the EXACT prompt structure and style from the examples
- Create elementary-appropriate prompts (grades 5-7)
- Include clear, engaging visual descriptions for picture prompts
- Focus on creative storytelling with beginning, middle, and end
- Use age-appropriate language and concepts for grades 5-7
- Generate DIFFERENT types of prompts - vary themes, settings, scenarios
{f"- Focus specifically on the topic: {request.topic}" if request.topic else ""}

COMPLEXITY GUIDELINES:
{self._get_complexity_guidelines(request.difficulty.value, request.question_type.value)}

CRITICAL CATEGORIZATION REQUIREMENTS:

1. SUBSECTION: Create a SPECIFIC subsection that captures both the writing task type AND the skills it develops. Be specific, not generic (avoid "Picture Story", "Creative Writing" alone).

2. WRITING TAGS: Create 2-4 specific tags that capture different aspects of the writing skills:
- Writing Skills: ["character-development", "dialogue-writing", "descriptive-language", "narrative-structure", "plot-development"]
- Creative Elements: ["visual-inspiration", "imaginative-thinking", "creative-problem-solving", "world-building", "sensory-details"]
- Themes/Content: ["friendship-themes", "adventure-elements", "family-relationships", "overcoming-challenges", "discovery-learning"]

3. PROMPT TYPE: Choose from ["picture_story", "creative_narrative", "descriptive_writing", "character_driven"]

OUTPUT FORMAT - Return ONLY a JSON object:
{{
  "prompts": [
    {{
      "prompt": "Complete writing prompt text here (JUST the creative prompt, NO instructions)",
      "visual_description": "Description of the picture that would accompany this prompt",
      "grade_level": "4-5",
      "prompt_type": "picture_story",
      "subsection": "Specific subsection name",
      "tags": ["tag1", "tag2", "tag3"]
    }}
  ]
}}"""
        
        # Calculate approximate token count (rough estimate: 1 token ≈ 4 characters)
        estimated_tokens = len(complete_prompt) // 4
        logger.info(f"🔍 DEBUG: Complete prompt length: {len(complete_prompt)} characters")
        logger.info(f"🔍 DEBUG: Examples text length: {len(examples_text)} characters")
        logger.info(f"🔍 DEBUG: Estimated tokens: {estimated_tokens}")
        
        # Check if we're approaching token limits
        if estimated_tokens > 6000:
            logger.warning(f"⚠️ WARNING: Prompt is very long ({estimated_tokens} estimated tokens). Consider reducing example count.")
        elif estimated_tokens > 4000:
            logger.info(f"ℹ️ INFO: Prompt is moderately long ({estimated_tokens} estimated tokens).")
        else:
            logger.info(f"✅ INFO: Prompt length is good ({estimated_tokens} estimated tokens).")
        
        return complete_prompt
    
    def build_generic_writing_prompt(self, request: QuestionRequest) -> str:
        """Build generic writing prompt when no training examples are available."""
        topic_guidance = f" related to {request.topic}" if request.topic else ""
        
        system_prompt = f"""You are an expert SSAT Elementary writing prompt generator. Create {request.count} engaging writing prompts for grades 5-7 students{topic_guidance}.

REQUIREMENTS:
1. Age-appropriate language and concepts for grades 5-7
2. Each prompt should inspire creative storytelling with beginning, middle, and end
3. Include visual descriptions for picture-based prompts
4. Focus on themes like friendship, adventure, family, animals, or everyday experiences
5. Prompts should be clear and specific enough to guide student writing

"""
        
        topic_instruction_number = 6
        if request.topic:
            system_prompt += f"{topic_instruction_number}. Focus specifically on the topic: {request.topic}\n"
            topic_instruction_number += 1
        
        system_prompt += f"""

CRITICAL CATEGORIZATION REQUIREMENTS:

{topic_instruction_number}. SUBSECTION ANALYSIS: Create a SPECIFIC subsection that captures both the writing task type AND the skills it develops.

SUBSECTION CREATION RULES:
- Be SPECIFIC about the writing task and skills (NEVER use "Picture Story", "Creative Writing" alone)
- Capture what makes this prompt unique for writing instruction
- Consider the specific narrative/writing skills this prompt develops

GOOD SUBSECTION EXAMPLES:
- "Character-Driven Visual Narratives" (for picture prompts focusing on character development)
- "Problem-Solution Adventure Stories" (for prompts with clear conflict resolution)
- "Descriptive Setting-Based Writing" (for prompts emphasizing scene and atmosphere)
- "Dialogue-Rich Character Interaction" (for prompts emphasizing conversation and relationships)
- "Sequential Event Storytelling" (for prompts with clear beginning-middle-end structure)

{topic_instruction_number + 1}. WRITING TAGS ANALYSIS: Create 2-4 specific tags that capture different aspects of the writing skills and elements this prompt encourages.

TAG CATEGORIES (choose from different categories):
- Writing Skills: ["character-development", "dialogue-writing", "descriptive-language", "narrative-structure", "plot-development"]
- Creative Elements: ["visual-inspiration", "imaginative-thinking", "creative-problem-solving", "world-building", "sensory-details"]
- Themes/Content: ["friendship-themes", "adventure-elements", "family-relationships", "overcoming-challenges", "discovery-learning"]
- Cognitive Processes: ["sequential-thinking", "cause-effect-reasoning", "perspective-taking", "emotional-expression", "conflict-resolution"]

OUTPUT FORMAT - Return ONLY a JSON object:
{{
  "prompts": [
    {{
      "prompt": "Complete writing prompt text here (JUST the creative prompt, NO instructions)",
      "visual_description": "Description of the picture that would accompany this prompt",
      "grade_level": "4-5",
      "prompt_type": "picture_story",
      "subsection": "Character-Driven Visual Narratives",
      "tags": ["character-development", "visual-inspiration", "emotional-expression", "narrative-structure"]
    }}
  ]
}}

CRITICAL VALIDATION REQUIREMENTS:
- subsection: MUST be specific and educationally useful (NO generic "Picture Story", "Creative Writing")
- tags: MUST be exactly 2-4 specific writing skill/element descriptors
- prompt: MUST NOT include instructions like "Write a story..." - those are added separately
- EVERY prompt MUST have specific, educational categorizations - NOT optional

QUALITY CHECK: Before finalizing, ask yourself:
1. Would a writing teacher find this subsection useful for lesson planning?
2. Do the tags clearly identify what writing skills this prompt develops?
3. Could someone search for these specific writing elements?
If any answer is NO, improve your categorization.

IMPORTANT: Generate ONLY the creative writing prompt. Do NOT include instructions like "Write a story with beginning, middle, and end" - those will be added separately."""
        
        return system_prompt
    
    def build_few_shot_prompt(self, request: QuestionRequest, training_examples: List[Dict[str, Any]]) -> str:
        """Build few-shot prompt by extending base prompt with examples."""
        
        logger.info(f"🔍 DEBUG: Building few-shot prompt with {len(training_examples)} training examples")
        
        if not training_examples:
            # Use appropriate base prompt based on question type
            if request.question_type.value == "quantitative":
                # Check if this is for official format (no specific topic means official section)
                if not request.topic or request.topic == "":
                    logger.info(f"📚 No training examples available for {request.question_type.value}, using official quantitative prompt")
                    return self.build_official_quantitative_prompt(request)
                else:
                    logger.info(f"📚 No training examples available for {request.question_type.value}, using base quantitative prompt")
                    return self.build_base_quantitative_prompt(request)
            else:
                logger.info(f"📚 No training examples available for {request.question_type.value}, using base verbal prompt")
                return self.build_base_verbal_prompt(request)
        
        examples_text = ""
        valid_examples = 0
        
        for i, example in enumerate(training_examples, 1):
            logger.info(f"🔍 DEBUG: Processing example {i}: {example.get('question', '')[:50]}...")
            
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
Correct Answer: {chr(65 + example['answer'])}
Explanation: {example['explanation']}
Difficulty: {example['difficulty']}
Subsection: {example['subsection']}

"""
            examples_text += example_text
            
            # Log training example summary (not full details)
            logger.debug(f"Training example {valid_examples}: {example['question'][:50]}...")
        
        logger.info(f"📚 TRAINING SUMMARY: Using {valid_examples} real SSAT examples for {request.question_type.value} questions")
        
        # SIMPLIFIED PROMPT: Focus on examples first, minimal instructions
        from app.specifications import QUANTITATIVE_SUBSECTIONS
        
        # For quantitative questions, use dynamic example count in prompt
        if request.question_type.value == "quantitative":
            example_count_text = f"{valid_examples} REAL SSAT EXAMPLES"
        else:
            example_count_text = "REAL SSAT EXAMPLES"
        
        # Specialized prompt for analogy questions to ensure diversity
        if request.question_type.value == "analogy":
            complete_prompt = f"""You are an expert SSAT analogy question generator.

STUDY THESE {example_count_text} FROM OFFICIAL TESTS:

{examples_text}

GENERATE {request.count} NEW ANALOGY QUESTIONS with DIVERSE RELATIONSHIP TYPES.

{self._get_difficulty_specific_instructions(request.difficulty.value)}

CRITICAL DIVERSITY REQUIREMENTS:
- AVOID repetitive patterns (e.g., don't generate multiple "young animal to adult animal" questions)
- Use DIFFERENT relationship types for each question:
  * Part-to-whole (wheel : car :: page : book)
  * Function (teacher : educate :: doctor : heal)
  * Degree (warm : hot :: cool : cold)
  * Cause-effect (rain : wet :: fire : burn)
  * Tool-user (hammer : carpenter :: stethoscope : doctor)
  * Material-product (wood : chair :: flour : bread)
  * Synonym (happy : joyful :: sad : sorrowful)
  * Antonym (big : small :: fast : slow)
  * Time sequence (morning : noon :: spring : summer)
  * Location (kitchen : cooking :: bedroom : sleeping)

COMPLEXITY GUIDELINES:
{self._get_complexity_guidelines(request.difficulty.value, request.question_type.value)}

DIFFICULTY MATCHING REQUIREMENTS:
- MATCH the difficulty level of the provided examples EXACTLY
- If examples use sophisticated vocabulary (ephemeral, turbulent, catalyst, democracy), use similar advanced vocabulary
- If examples use simple vocabulary (dog, cat, big, small), use similar simple vocabulary
- For HARD examples: Use complex words, abstract concepts, multiple-step relationships
- For MEDIUM examples: Use moderate vocabulary, clear relationships
- For EASY examples: Use simple vocabulary, direct relationships

QUALITY REQUIREMENTS:
- Match the difficulty level: {request.difficulty.value}
- Use the same answer choice format (A, B, C, D)
- Provide detailed explanations of the relationship
- Suitable for grades 5-7 students
- Each question should have exactly 4 options
- Ensure all answer choices are plausible distractors
- Use vocabulary complexity that matches the training examples

CATEGORIZATION REQUIREMENTS:

1. SUBSECTION: Use "Analogies" as the subsection for ALL questions.

2. TAGS: Create 2-4 descriptive tags from these categories:
   - Content: ["verbal-reasoning", "vocabulary", "conceptual-understanding", "pattern-recognition"]
   - Problem Type: ["relationship-analysis", "word-association", "logical-thinking"]
   - Cognitive Demand: ["requires-analysis", "conceptual-mapping", "abstract-thinking"]

3. COGNITIVE LEVEL: **MANDATORY** - For {request.difficulty.value} questions, you MUST use "{self._get_cognitive_level_by_difficulty(request.difficulty.value)}" as the cognitive_level. Do NOT use any other cognitive level.

OUTPUT FORMAT - Return ONLY a JSON object:
{{
  "questions": [
    {{
      "text": "question text",
      "options": [{{"letter": "A", "text": "option"}}, {{"letter": "B", "text": "option"}}, {{"letter": "C", "text": "option"}}, {{"letter": "D", "text": "option"}}],
      "correct_answer": "A",
      "explanation": "detailed explanation of the relationship",
      "cognitive_level": "{self._get_cognitive_level_by_difficulty(request.difficulty.value)}",
      "tags": ["tag1", "tag2", "tag3"],
      "subsection": "Analogies",
      "visual_description": "None"
    }}
  ]
}}"""
        else:
            complete_prompt = f"""You are an expert SSAT {request.question_type.value} question generator.

STUDY THESE {example_count_text} FROM OFFICIAL TESTS:

{examples_text}

GENERATE {request.count} NEW QUESTIONS about the SAME TOPIC/CONCEPT as these examples.

{self._get_difficulty_specific_instructions(request.difficulty.value)}

CRITICAL REQUIREMENTS:
- Generate questions about the SAME mathematical concept as the examples (e.g., if example is about factors, generate more factor questions)
- Match the difficulty level: {request.difficulty.value}
- Use the same answer choice format (A, B, C, D)
- Provide detailed explanations
- Suitable for grades 5-7 students
- Each question should have exactly 4 options
{f"- Focus on topic: {request.topic}" if request.topic else ""}

COMPLEXITY GUIDELINES:
{self._get_complexity_guidelines(request.difficulty.value, request.question_type.value)}

CATEGORIZATION REQUIREMENTS:

1. SUBSECTION: {f'Use "{request.topic}" as the subsection for ALL questions. This is the specific mathematical concept you are generating.' if request.topic else 'Use appropriate subsection names from: Number Sense, Arithmetic, Fractions, Decimals, Percentages, Patterns, Sequences, Algebra, Variables, Area, Perimeter, Shapes, Spatial, Measurement, Time, Money, Probability, Data, Graphs'}

2. TAGS: Create 2-4 descriptive tags from these categories:
   - Content: ["algebraic-thinking", "geometric-reasoning", "number-sense", "measurement-concepts", "data-analysis", "fraction-concepts", "decimal-operations"]
   - Problem Type: ["word-problem", "computational-fluency", "conceptual-understanding", "application-problem"]
   - Cognitive Demand: ["multi-step-solution", "single-step-direct", "requires-strategy", "pattern-recognition"]

3. COGNITIVE LEVEL: **MANDATORY** - For {request.difficulty.value} questions, you MUST use "{self._get_cognitive_level_by_difficulty(request.difficulty.value)}" as the cognitive_level. Do NOT use any other cognitive level.

OUTPUT FORMAT - Return ONLY a JSON object:
{{
  "questions": [
    {{
      "text": "question text",
      "options": [{{"letter": "A", "text": "option"}}, {{"letter": "B", "text": "option"}}, {{"letter": "C", "text": "option"}}, {{"letter": "D", "text": "option"}}],
      "correct_answer": "A",
      "explanation": "detailed explanation",
      "cognitive_level": "{self._get_cognitive_level_by_difficulty(request.difficulty.value)}",
      "tags": ["tag1", "tag2", "tag3"],
      "subsection": "{request.topic if request.topic else 'Choose from: Number Sense, Arithmetic, Fractions, Decimals, Percentages, Patterns, Sequences, Algebra, Variables, Area, Perimeter, Shapes, Spatial, Measurement, Time, Money, Probability, Data, Graphs'}",
      "visual_description": "Description of any visual elements (if applicable)"
    }}
  ]
}}"""
        
        return complete_prompt
    
    def build_reading_few_shot_prompt(self, request: QuestionRequest, training_examples: List[Dict[str, Any]]) -> str:
        """Build few-shot prompt by extending base reading prompt with examples."""
        
        if not training_examples:
            # Use base reading prompt without examples
            logger.info(f"📚 No reading training examples available, using base reading prompt")
            return self.build_base_reading_prompt(request)
        
        examples_text = ""
        valid_examples = 0
        
        for i, example in enumerate(training_examples, 1):
            # Handle new reading passage format (complete passage with multiple questions)
            if example.get('questions'):
                # New format: complete passage with questions
                if not example.get('passage'):
                    logger.warning(f"Skipping reading example {i} - missing passage")
                    continue
                
                valid_examples += 1
                example_text = f"""
REAL SSAT READING EXAMPLE {valid_examples}:

PASSAGE:
{example['passage']}

PASSAGE TYPE: {example.get('passage_type', 'General')}
DIFFICULTY: {example.get('difficulty', 'Medium')}

"""
                # Add all questions from this passage
                for j, question in enumerate(example['questions'], 1):
                    example_text += f"""
QUESTION {j}: {question['question']}
CHOICES: {question['choices']}
CORRECT ANSWER: {chr(65 + question['answer'])}
EXPLANATION: {question.get('explanation', 'N/A')}

"""
                examples_text += example_text
            else:
                # Old format: individual questions (for backward compatibility)
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
        
        # SIMPLIFIED READING PROMPT: Examples first, minimal instructions
        complete_prompt = f"""You are an expert SSAT reading comprehension question generator.

STUDY THESE REAL SSAT READING EXAMPLES FROM OFFICIAL TESTS:

{examples_text}

GENERATE {request.count} NEW READING PASSAGES with 4 COMPREHENSION QUESTIONS each about the SAME TOPIC/THEME as these examples.

{self._get_difficulty_specific_instructions(request.difficulty.value)}

CRITICAL REQUIREMENTS:
- Generate {request.count} passages and {request.count * 4} questions about the SAME TOPIC/THEME as the examples (e.g., if example is about animals, generate more animal-related passages and questions)
- Create a reading passage first with SPECIFIC LENGTH REQUIREMENT for each passage:
  * Target: 450 words
  * Must be substantial enough for 4 comprehension questions
- Match the difficulty level: {request.difficulty.value}
- Use the same answer choice format (A, B, C, D) for all questions
- Questions must test reading comprehension skills
- Suitable for grades 5-7 students
- Each question should have exactly 4 options
- **IMPORTANT: Generate CHALLENGING questions that require critical thinking, not just basic recall**
{f"- Focus the passage topic on: {request.topic}" if request.topic else ""}

COMPLEXITY GUIDELINES:
{self._get_complexity_guidelines(request.difficulty.value, request.question_type.value)}

QUESTION DIFFICULTY GUIDELINES:
- **Easy**: Basic facts, main idea, simple vocabulary, direct questions
- **Medium**: Supporting details, simple inference, context clues, moderate vocabulary
- **Hard**: Complex inference, author's purpose, character motivation, cause-effect relationships, advanced vocabulary, multiple-step reasoning, evaluation and synthesis
- **Very Hard**: Multiple-step reasoning, evaluation, synthesis, complex vocabulary, sophisticated analysis

CRITICAL CATEGORIZATION REQUIREMENTS:

1. PASSAGE TYPE: Create a SPECIFIC, descriptive passage type that captures both content and genre. Be specific, not generic (avoid "Fiction", "Non-fiction" alone).

2. READING TAGS: Create 2-4 specific tags that capture the reading comprehension skills being tested:
- Comprehension Skills: ["main-idea-identification", "supporting-details", "inference-making", "conclusion-drawing", "author-purpose"]
- Text Analysis: ["character-analysis", "plot-development", "cause-and-effect", "compare-contrast", "sequence-understanding"]  
- Vocabulary Skills: ["context-clues", "word-meaning", "vocabulary-development", "technical-terms", "figurative-language"]
- Critical Thinking: ["evidence-evaluation", "perspective-analysis", "prediction-making", "connection-building", "interpretation-skills"]

3. COGNITIVE LEVEL: **MANDATORY** - For {request.difficulty.value} questions, you MUST use "{self._get_cognitive_level_by_difficulty(request.difficulty.value)}" as the cognitive_level. Do NOT use any other cognitive level. AVOID "REMEMBER" level questions as they are too basic. Focus on higher-order thinking skills.

OUTPUT FORMAT - Return ONLY a JSON object:
{{
  "passages": [
    {{
      "passage": "Complete reading passage text",
      "questions": [
        {{
          "text": "question text",
          "options": [{{"letter": "A", "text": "option"}}, {{"letter": "B", "text": "option"}}, {{"letter": "C", "text": "option"}}, {{"letter": "D", "text": "option"}}],
          "correct_answer": "A",
          "explanation": "detailed explanation",
          "cognitive_level": "{self._get_cognitive_level_by_difficulty(request.difficulty.value)}",
          "tags": ["tag1", "tag2", "tag3"]
        }}
      ],
      "passage_type": "Specific passage type",
      "visual_description": "Description of any visual elements (if applicable)"
    }}
  ]
}}"""
        
        return complete_prompt
    
    def build_generic_prompt(self, request: QuestionRequest) -> str:
        """Fallback generic prompt when no training examples available."""
        
        type_specific_rules = {
            "quantitative": "Focus on arithmetic, fractions, basic geometry, and word problems suitable for grades 5-7 students.",
            "verbal": "Focus on vocabulary appropriate for grades 5-7 students, including synonyms and analogies.",
            "analogy": "Create analogies with clear relationships that grades 5-7 students can understand.",
            "synonym": "Use vocabulary words appropriate for grades 5-7.",
            "reading": "Create passages and questions appropriate for grades 5-7 reading level.",
            "writing": "Create clear, focused writing prompts for grades 5-7 students."
        }
        
        rules = type_specific_rules.get(request.question_type.value, "Generate appropriate grades 5-7 level questions.")
        
        return f"""You are an expert SSAT question designer for grades 5-7.

Generate {request.count} high-quality {request.question_type.value} questions with {request.difficulty.value} difficulty.

{self._get_difficulty_specific_instructions(request.difficulty.value)}

REQUIREMENTS:
1. Each question has exactly 4 options (A, B, C, D)
2. Include detailed explanations
3. Suitable for grades 5-7 students
4. {rules}
{f"5. Focus on topic: {request.topic}" if request.topic else ""}

COMPLEXITY GUIDELINES:
{self._get_complexity_guidelines(request.difficulty.value, request.question_type.value)}

Return JSON format:
{{
  "questions": [
    {{
      "text": "question text",
      "options": [{{"letter": "A", "text": "option"}}, ...],
      "correct_answer": "A",
      "explanation": "explanation",
      "cognitive_level": "{self._get_cognitive_level_by_difficulty(request.difficulty.value)}",
      "tags": ["tag1", "tag2"],
      "visual_description": "Description of any visual elements (if applicable)"
    }}
  ]
}}"""

    def build_official_quantitative_prompt(self, request: QuestionRequest) -> str:
        """Build prompt for official quantitative section that generates questions across all subsections."""
        from app.specifications import QUANTITATIVE_SUBSECTIONS
        
        system_prompt = f"""You are an expert SSAT quantitative question generator for OFFICIAL test format.

Generate {request.count} NEW quantitative questions that represent a complete SSAT Elementary quantitative section.

{self._get_difficulty_specific_instructions(request.difficulty.value)}

CRITICAL REQUIREMENTS:
- Match difficulty level: {request.difficulty.value}
- Use answer choice format (A, B, C, D)
- Provide detailed explanations
- Suitable for grades 5-7 students
- Each question must have exactly 4 options
- Generate questions across ALL mathematical subsections to create a balanced test
{f"- Focus on topic: {request.topic}" if request.topic else ""}

COMPLEXITY GUIDELINES:
{self._get_complexity_guidelines(request.difficulty.value, request.question_type.value)}

OFFICIAL SSAT QUANTITATIVE SUBSECTIONS - Generate questions from these categories:
{QUANTITATIVE_SUBSECTIONS}

DISTRIBUTION GUIDELINES:
- Number Operations (40%): Fractions, Arithmetic, Number Sense, Decimals, Percentages
- Algebra Functions (20%): Algebra, Variables, Patterns, Sequences  
- Geometry Spatial (25%): Area, Perimeter, Shapes, Spatial
- Measurement (10%): Measurement, Time, Money
- Probability Data (5%): Probability, Data, Graphs

CRITICAL CATEGORIZATION:

1. SUBSECTION: Use the EXACT subsection names from the list above. Each question must be categorized into one of these specific subsections.{f" If a topic is specified ({request.topic}), ensure questions relate to that topic while still covering diverse subsections." if request.topic else ""}

2. TAGS: Create 2-4 descriptive tags from these categories:
   - Content: ["algebraic-thinking", "geometric-reasoning", "number-sense", "measurement-concepts", "data-analysis", "fraction-concepts", "decimal-operations"]
   - Problem Type: ["word-problem", "computational-fluency", "conceptual-understanding", "application-problem"]
   - Cognitive Demand: ["multi-step-solution", "single-step-direct", "requires-strategy", "pattern-recognition"]

3. COGNITIVE LEVEL: **MANDATORY** - For {request.difficulty.value} questions, you MUST use "{self._get_cognitive_level_by_difficulty(request.difficulty.value)}" as the cognitive_level. Do NOT use any other cognitive level.

IMPORTANT: Ensure variety across all subsections. Do NOT focus on just one topic{f" unless specifically requested ({request.topic})" if request.topic else ""}.

OUTPUT FORMAT - Return ONLY a JSON object:
{{
  "questions": [
    {{
      "text": "question text",
      "options": [{{"letter": "A", "text": "option"}}, {{"letter": "B", "text": "option"}}, {{"letter": "C", "text": "option"}}, {{"letter": "D", "text": "option"}}],
      "correct_answer": "A",
      "explanation": "detailed explanation",
      "cognitive_level": "{self._get_cognitive_level_by_difficulty(request.difficulty.value)}",
      "tags": ["tag1", "tag2", "tag3"],
      "subsection": "Exact subsection name from the list",
      "visual_description": "Description of any visual elements (if applicable)"
    }}
  ]
}}"""
        
        return system_prompt

    def build_base_quantitative_prompt(self, request: QuestionRequest) -> str:
        """Build base prompt for quantitative questions with all instructions and requirements."""
        from app.specifications import QUANTITATIVE_SUBSECTIONS
        
        system_prompt = f"""You are an expert SSAT quantitative question generator.

Generate {request.count} NEW quantitative questions that match SSAT Elementary style and format.

{self._get_difficulty_specific_instructions(request.difficulty.value)}

REQUIREMENTS:
- Match difficulty level: {request.difficulty.value}
- Use answer choice format (A, B, C, D)
- Provide detailed explanations
- Suitable for grades 5-7 students
- Each question must have exactly 4 options
{f"- Focus on topic: {request.topic}" if request.topic else ""}

COMPLEXITY GUIDELINES:
{self._get_complexity_guidelines(request.difficulty.value, request.question_type.value)}

CRITICAL CATEGORIZATION:

1. SUBSECTION: {f'Use "{request.topic}" as the subsection for ALL questions. This is the specific mathematical concept you are generating.' if request.topic else 'Use appropriate subsection names from: Number Sense, Arithmetic, Fractions, Decimals, Percentages, Patterns, Sequences, Algebra, Variables, Area, Perimeter, Shapes, Spatial, Measurement, Time, Money, Probability, Data, Graphs'}

2. TAGS: Create 2-4 descriptive tags from these categories:
   - Content: ["algebraic-thinking", "geometric-reasoning", "number-sense", "measurement-concepts", "data-analysis", "fraction-concepts", "decimal-operations"]
   - Problem Type: ["word-problem", "computational-fluency", "conceptual-understanding", "application-problem"]
   - Cognitive Demand: ["multi-step-solution", "single-step-direct", "requires-strategy", "pattern-recognition"]

3. COGNITIVE LEVEL: **MANDATORY** - For {request.difficulty.value} questions, you MUST use "{self._get_cognitive_level_by_difficulty(request.difficulty.value)}" as the cognitive_level. Do NOT use any other cognitive level.

OUTPUT FORMAT - Return ONLY a JSON object:
{{
  "questions": [
    {{
      "text": "question text",
      "options": [{{"letter": "A", "text": "option"}}, {{"letter": "B", "text": "option"}}, {{"letter": "C", "text": "option"}}, {{"letter": "D", "text": "option"}}],
      "correct_answer": "A",
      "explanation": "detailed explanation",
      "cognitive_level": "{self._get_cognitive_level_by_difficulty(request.difficulty.value)}",
      "tags": ["tag1", "tag2", "tag3"],
      "subsection": "{request.topic if request.topic else 'Choose from: Number Sense, Arithmetic, Fractions, Decimals, Percentages, Patterns, Sequences, Algebra, Variables, Area, Perimeter, Shapes, Spatial, Measurement, Time, Money, Probability, Data, Graphs'}",
      "visual_description": "Description of any visual elements (if applicable)"
    }}
  ]
}}"""
        
        return system_prompt

    def build_base_verbal_prompt(self, request: QuestionRequest) -> str:
        """Build base prompt for verbal questions (analogy/synonym) with all instructions and requirements."""
        
        system_prompt = f"""You are an expert SSAT verbal question generator.

Generate {request.count} NEW {request.question_type.value} questions that match SSAT Elementary style and format.

{self._get_difficulty_specific_instructions(request.difficulty.value)}

REQUIREMENTS:
- Match difficulty level: {request.difficulty.value}
- Use answer choice format (A, B, C, D)
- Provide detailed explanations
- Suitable for grades 5-7 students
- Each question must have exactly 4 options
- NO visual elements required (text-only questions)
{f"- Focus on topic: {request.topic}" if request.topic else ""}

COMPLEXITY GUIDELINES:
{self._get_complexity_guidelines(request.difficulty.value, request.question_type.value)}

CRITICAL CATEGORIZATION:

1. SUBSECTION: Create a SPECIFIC subsection that captures the vocabulary skill and relationship type. Be specific, not generic (avoid "Vocabulary", "Verbal" alone).

2. TAGS: Create 2-4 descriptive tags from these categories:
- Vocabulary Skills: ["context-clues", "word-relationships", "synonym-recognition", "analogy-mapping", "vocabulary-building"]
- Cognitive Skills: ["logical-reasoning", "pattern-recognition", "inference-making", "comparison-analysis"]
- Content Areas: ["academic-vocabulary", "everyday-language", "descriptive-words", "action-words"]

3. COGNITIVE LEVEL: **MANDATORY** - For {request.difficulty.value} questions, you MUST use "{self._get_cognitive_level_by_difficulty(request.difficulty.value)}" as the cognitive_level. Do NOT use any other cognitive level.

OUTPUT FORMAT - Return ONLY a JSON object:
{{
  "questions": [
    {{
      "text": "question text",
      "options": [{{"letter": "A", "text": "option"}}, {{"letter": "B", "text": "option"}}, {{"letter": "C", "text": "option"}}, {{"letter": "D", "text": "option"}}],
      "correct_answer": "A",
      "explanation": "detailed explanation",
      "cognitive_level": "{self._get_cognitive_level_by_difficulty(request.difficulty.value)}",
      "tags": ["tag1", "tag2", "tag3"],
      "subsection": "Specific subsection name",
      "visual_description": "None"
    }}
  ]
}}"""
        
        return system_prompt

    def build_base_reading_prompt(self, request: QuestionRequest) -> str:
        """Build base prompt for reading comprehension with all instructions and requirements."""
        
        system_prompt = f"""You are an expert SSAT reading comprehension question generator.

Generate 1 NEW reading passage with 4 comprehension questions that match SSAT Elementary style and format.

{self._get_difficulty_specific_instructions(request.difficulty.value)}

REQUIREMENTS:
- Create a reading passage first with SPECIFIC LENGTH REQUIREMENT:
  * Target: 450 words
  * Must be substantial enough for 4 comprehension questions
- Match difficulty level: {request.difficulty.value}
- Use answer choice format (A, B, C, D)
- Questions must test reading comprehension skills
- Suitable for grades 5-7 students
- Each question must have exactly 4 options
- Passage should be engaging and age-appropriate
{f"- Focus the passage topic on: {request.topic}" if request.topic else ""}

COMPLEXITY GUIDELINES:
{self._get_complexity_guidelines(request.difficulty.value, request.question_type.value)}

CRITICAL CATEGORIZATION:

1. PASSAGE TYPE: Create a SPECIFIC, descriptive passage type that captures both content and genre. Be specific, not generic (avoid "Fiction", "Non-fiction" alone).

2. READING TAGS: Create 2-4 specific tags that capture the reading comprehension skills being tested:
- Comprehension Skills: ["main-idea-identification", "supporting-details", "inference-making", "conclusion-drawing", "author-purpose"]
- Text Analysis: ["character-analysis", "plot-development", "cause-and-effect", "compare-contrast", "sequence-understanding"]  
- Vocabulary Skills: ["context-clues", "word-meaning", "vocabulary-development", "technical-terms", "figurative-language"]

3. COGNITIVE LEVEL: **MANDATORY** - For {request.difficulty.value} questions, you MUST use "{self._get_cognitive_level_by_difficulty(request.difficulty.value)}" as the cognitive_level. Do NOT use any other cognitive level.

OUTPUT FORMAT - Return ONLY a JSON object:
{{
  "passage": "Complete reading passage text",
  "questions": [
    {{
      "text": "question text",
      "options": [{{"letter": "A", "text": "option"}}, {{"letter": "B", "text": "option"}}, {{"letter": "C", "text": "option"}}, {{"letter": "D", "text": "option"}}],
      "correct_answer": "A",
      "explanation": "detailed explanation",
      "cognitive_level": "{self._get_cognitive_level_by_difficulty(request.difficulty.value)}",
      "tags": ["tag1", "tag2", "tag3"]
    }}
  ],
  "passage_type": "Specific passage type",
  "visual_description": "Description of any visual elements (if applicable)"
}}"""
        
        return system_prompt

    def build_base_writing_prompt(self, request: QuestionRequest) -> str:
        """Build base prompt for writing prompts with all instructions and requirements."""
        
        system_prompt = f"""You are an expert SSAT Elementary writing prompt generator.

Generate {request.count} NEW writing prompts that match SSAT Elementary style and format.

{self._get_difficulty_specific_instructions(request.difficulty.value)}

REQUIREMENTS:
- Follow SSAT Elementary prompt structure and style
- Create elementary-appropriate prompts (grades 5-7)
- Include clear, engaging visual descriptions for picture prompts
- Focus on creative storytelling with beginning, middle, and end
- Use age-appropriate language and concepts for grades 5-7
- Prompts should be engaging and inspire creativity
{f"- Focus specifically on the topic: {request.topic}" if request.topic else ""}

COMPLEXITY GUIDELINES:
{self._get_complexity_guidelines(request.difficulty.value, request.question_type.value)}

CRITICAL CATEGORIZATION:

1. SUBSECTION: Create a SPECIFIC subsection that captures both the writing task type AND the skills it develops. Be specific, not generic (avoid "Picture Story", "Creative Writing" alone).

2. WRITING TAGS: Create 2-4 specific tags that capture different aspects of the writing skills:
- Writing Skills: ["character-development", "dialogue-writing", "descriptive-language", "narrative-structure", "plot-development"]
- Creative Elements: ["visual-inspiration", "imaginative-thinking", "creative-problem-solving", "world-building", "sensory-details"]
- Themes/Content: ["friendship-themes", "adventure-elements", "family-relationships", "overcoming-challenges", "discovery-learning"]

3. PROMPT TYPE: Choose from ["picture_story", "creative_narrative", "descriptive_writing", "character_driven"]

OUTPUT FORMAT - Return ONLY a JSON object:
{{
  "prompts": [
    {{
      "prompt": "Complete writing prompt text here (JUST the creative prompt, NO instructions)",
      "visual_description": "Description of the picture that would accompany this prompt",
      "grade_level": "4-5",
      "prompt_type": "picture_story",
      "subsection": "Specific subsection name",
      "tags": ["tag1", "tag2", "tag3"]
    }}
  ]
}}"""
        
        return system_prompt

    # REMOVED: build_multiple_reading_few_shot_prompt method
    # This has been replaced by the unified build_reading_few_shot_prompt() method

    def _get_difficulty_specific_instructions(self, difficulty: str) -> str:
        """Generate difficulty-specific instructions for all question types."""
        
        difficulty_instructions = {
            "Easy": """
EASY DIFFICULTY REQUIREMENTS (Grades 5-6):
- Use moderate complexity and clear relationships
- Vocabulary appropriate for grades 5-6
- Single-step problems or straightforward questions with some complexity
- Clear, plausible answer choices
- Focus on fundamental understanding and basic application
- Cognitive Level: UNDERSTAND or APPLY
- Include some reasoning and conceptual understanding
- May require basic problem-solving strategies
""",
            "Medium": """
MEDIUM DIFFICULTY REQUIREMENTS (Grades 6-7):
- Use complex, multi-step problems requiring critical thinking
- Advanced vocabulary appropriate for grades 6-7
- Require 2-3 steps of reasoning or moderate inference
- Abstract concepts and sophisticated relationships
- Answer choices should be challenging but fair
- Focus on application, analysis, and synthesis
- Cognitive Level: APPLY or ANALYZE
- Must require strategic thinking and problem-solving
- Include complex word problems, abstract reasoning, and sophisticated analysis
""",
            "Hard": """
HARD DIFFICULTY REQUIREMENTS (Grades 7+):
- Use highly complex, multi-step problems requiring advanced critical thinking
- Sophisticated vocabulary appropriate for grades 7+
- Require 4+ steps of reasoning or complex inference
- Advanced abstract concepts and sophisticated relationships
- Answer choices should be very challenging but fair
- Focus on analysis, evaluation, and synthesis
- Cognitive Level: ANALYZE or EVALUATE
- Must require advanced strategic thinking and sophisticated problem-solving
- Include complex word problems, abstract reasoning, advanced geometry, probability, statistics, and sophisticated analysis
- May involve multiple mathematical concepts combined
- Should challenge even advanced students
"""
        }
        
        return difficulty_instructions.get(difficulty, difficulty_instructions["Medium"])
    
    def _get_cognitive_level_by_difficulty(self, difficulty: str) -> str:
        """Get appropriate cognitive level based on difficulty."""
        
        cognitive_mapping = {
            "Easy": "APPLY",      # Upgraded from UNDERSTAND to APPLY for grades 5-6
            "Medium": "ANALYZE",  # Upgraded from APPLY to ANALYZE for grades 6-7
            "Hard": "EVALUATE"    # Upgraded from ANALYZE to EVALUATE for grades 7+
        }
        
        return cognitive_mapping.get(difficulty, "APPLY")
    
    def _get_complexity_guidelines(self, difficulty: str, question_type: str) -> str:
        """Get complexity guidelines specific to question type and difficulty."""
        
        guidelines = {
            "quantitative": {
                "Easy": "- Multi-step calculations (2-3 steps), moderate arithmetic, complex word problems, basic algebra concepts, fractions and decimals, basic geometry",
                "Medium": "- Multi-step problems (3-4 steps), complex word problems, advanced geometry, algebra with variables, percentages and ratios, patterns and sequences, probability concepts",
                "Hard": "- Highly complex multi-step problems (4+ steps), advanced word problems, abstract concepts, advanced algebra, complex geometry, probability and statistics, data analysis, mathematical reasoning, multiple concept integration"
            },
            "reading": {
                "Easy": "- Supporting details, inference-making, context clues, moderate vocabulary, character analysis, plot development",
                "Medium": "- Complex inference, author's purpose, character motivation, cause-effect relationships, advanced vocabulary, multiple-step reasoning, evaluation and synthesis",
                "Hard": "- Sophisticated analysis, complex inference, author's purpose and bias, character development, theme analysis, literary devices, advanced vocabulary, multiple-step reasoning, evaluation, synthesis, and critical analysis"
            },
            "analogy": {
                "Easy": "- Moderate relationships, clear vocabulary, some inference, conceptual mapping",
                "Medium": "- Complex relationships, advanced vocabulary, abstract concepts, multiple-step reasoning, sophisticated word relationships",
                "Hard": "- Highly complex relationships, sophisticated vocabulary, abstract concepts, multiple-step reasoning, sophisticated word relationships, conceptual analysis, pattern recognition"
            },
            "synonym": {
                "Easy": "- Moderate vocabulary, context clues, some inference, word relationships",
                "Medium": "- Advanced vocabulary, complex word meanings, sophisticated synonyms, abstract concepts",
                "Hard": "- Sophisticated vocabulary, complex word meanings, advanced synonyms, abstract concepts, nuanced understanding, contextual analysis"
            },
            "writing": {
                "Easy": "- Moderate themes, character development, engaging prompts, narrative structure",
                "Medium": "- Complex themes, sophisticated storytelling, advanced character development, multi-layered narratives",
                "Hard": "- Highly complex themes, sophisticated storytelling, advanced character development, multi-layered narratives, literary techniques, advanced writing skills"
            }
        }
        
        return guidelines.get(question_type, {}).get(difficulty, "- Standard complexity for the question type")

    def _validate_question_quality(self, question: Dict[str, Any], difficulty: str, question_type: str) -> bool:
        """Validate that a generated question meets the quality requirements for its difficulty level."""
        
        # Basic validation
        if not question.get('text') or not question.get('options') or len(question.get('options', [])) != 4:
            return False
        
        # Difficulty-specific validation
        if difficulty == "Hard":
            # Check for complex vocabulary or multi-step reasoning indicators
            text = question.get('text', '').lower()
            explanation = question.get('explanation', '').lower()
            
            # Hard questions should have indicators of complexity
            complexity_indicators = [
                'if', 'when', 'because', 'therefore', 'however', 'although', 'while',
                'multiple', 'several', 'various', 'different', 'complex', 'advanced',
                'calculate', 'determine', 'analyze', 'evaluate', 'compare', 'contrast'
            ]
            
            has_complexity = any(indicator in text or indicator in explanation for indicator in complexity_indicators)
            
            # For quantitative, check for multi-step indicators
            if question_type == "quantitative":
                step_indicators = ['first', 'then', 'next', 'finally', 'step', 'calculate', 'solve']
                has_multi_step = any(indicator in text or indicator in explanation for indicator in step_indicators)
                return has_complexity and has_multi_step
            
            # For reading, check for inference indicators
            elif question_type == "reading":
                inference_indicators = ['infer', 'conclude', 'suggest', 'imply', 'author', 'purpose', 'character']
                has_inference = any(indicator in text or indicator in explanation for indicator in inference_indicators)
                return has_complexity and has_inference
            
            # For verbal, check for advanced vocabulary
            elif question_type in ["analogy", "synonym"]:
                advanced_vocab_indicators = ['sophisticated', 'advanced', 'complex', 'abstract', 'relationship']
                has_advanced_vocab = any(indicator in text or indicator in explanation for indicator in advanced_vocab_indicators)
                return has_complexity and has_advanced_vocab
            
            return has_complexity
        
        elif difficulty == "Medium":
            # Medium questions should have moderate complexity
            text = question.get('text', '').lower()
            explanation = question.get('explanation', '').lower()
            
            moderate_indicators = ['because', 'when', 'if', 'then', 'explain', 'describe', 'compare']
            has_moderate_complexity = any(indicator in text or indicator in explanation for indicator in moderate_indicators)
            
            return has_moderate_complexity
        
        else:  # Easy
            # Easy questions should be straightforward
            text = question.get('text', '').lower()
            explanation = question.get('explanation', '').lower()
            
            simple_indicators = ['what', 'which', 'who', 'where', 'when', 'how many']
            has_simple_structure = any(indicator in text for indicator in simple_indicators)
            
            return has_simple_structure

def generate_questions(request: QuestionRequest, llm: Optional[str] = "deepseek", custom_examples: Optional[str] = None, training_examples: Optional[List[Dict[str, Any]]] = None) -> List[Question]:
    """Generate standalone questions (non-reading) using AI with real SSAT training examples.
    
    Args:
        request: QuestionRequest with count and other parameters
        llm: LLM provider to use
        custom_examples: Custom training examples text
        training_examples: Pre-fetched training examples (to avoid double fetching)
    """
    logger.info(f"Generating {request.count} standalone {request.question_type.value} questions")
    
    if request.question_type.value == "reading":
        raise ValueError("Reading comprehension questions should use generate_reading_passages() function instead of generate_questions()")
    
    # Use provided training examples if available, otherwise fetch them
    if training_examples is None:
        generator = SSATGenerator()
        training_examples = generator.get_training_examples(request, custom_examples, request.count if request.question_type.value == "quantitative" else None)
        logger.info(f"📚 Fetched {len(training_examples)} training examples for {request.question_type.value}")
    else:
        logger.info(f"📚 Using {len(training_examples)} pre-fetched training examples for {request.question_type.value}")
    
    # Build few-shot prompt with training examples
    generator = SSATGenerator()
    system_message = generator.build_few_shot_prompt(request, training_examples)
    
    # Log training info
    if training_examples:
        if custom_examples:
            logger.info(f"Using {len(training_examples)} custom training examples")
        else:
            logger.info(f"Using {len(training_examples)} real SSAT examples for training")
    else:
        logger.info("No training examples found, using generic prompt")
    
    # Get available LLM providers
    provider = _select_llm_provider(llm)
    
    # Calculate appropriate max_tokens based on question count
    # Each question with options, explanations, etc. can be ~200-300 tokens
    # Add buffer for JSON structure and metadata
    estimated_tokens_per_question = 300
    base_tokens = 1000  # For JSON structure, metadata, etc.
    required_tokens = base_tokens + (request.count * estimated_tokens_per_question)
    max_tokens = min(required_tokens, 8000)  # Cap at 8000 to avoid hitting provider limits
    
    logger.info(f"Generating {request.count} questions, using max_tokens={max_tokens}")
    
    # Generate questions using LLM
    content = llm_client.call_llm(
        provider=provider,
        system_message=system_message,
        prompt="Generate the questions as specified.",
        max_tokens=max_tokens,
        temperature=0.8  # Higher temperature for more variety in verbal questions
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
            visual_description=q_data.get("visual_description"),
            subsection=q_data.get("subsection")  # Extract AI-determined subsection
        )
        questions.append(question)
    
    logger.info(f"Successfully generated {len(questions)} questions using {'custom examples' if custom_examples else 'real SSAT examples' if training_examples else 'generic prompt'}")
    if len(questions) != request.count:
        logger.warning(f"⚠️ Expected {request.count} questions but got {len(questions)} questions")
    return questions

def _generate_synonym_questions_from_words(request: QuestionRequest, words_text: str, llm: str) -> List[Question]:
    """Generate synonym questions from a list of words."""
    logger.info(f"Generating synonym questions from word list: {words_text}")
    
    # Parse words from the input
    words = [word.strip() for word in words_text.split(',') if word.strip()]
    
    if not words:
        raise ValueError("No valid words found in the word list")
    
    # Use all words since the count is already set to the word count
    words_to_generate = words
    
    try:
        # Build prompt for word-to-question generation
        system_message = f"""You are an expert SSAT synonym question generator.

Generate {len(words_to_generate)} synonym questions for these words: {', '.join(words_to_generate)}

REQUIREMENTS:
- Create one question per word
- Question text should be just the word (e.g., "happy")
- Provide 4 choices (A, B, C, D) where one is the correct synonym
- Include detailed explanations
- Use elementary-appropriate vocabulary
- Add appropriate tags and subsections

OUTPUT FORMAT - Return ONLY a JSON object:
{{
  "questions": [
    {{
      "text": "[WORD]",
      "options": [{{"letter": "A", "text": "option"}}, {{"letter": "B", "text": "option"}}, {{"letter": "C", "text": "option"}}, {{"letter": "D", "text": "option"}}],
      "correct_answer": "A",
      "explanation": "detailed explanation",
      "cognitive_level": "UNDERSTAND",
      "tags": ["tag1", "tag2", "tag3"],
      "subsection": "Synonyms",
      "visual_description": "None"
    }}
  ]
}}"""
        
        # Get available LLM providers
        provider = _select_llm_provider(llm)
        
        # Call LLM to generate questions
        content = llm_client.call_llm(
            provider=provider,
            system_message=system_message,
            prompt="Generate the synonym questions as specified.",
            max_tokens=4000,
            temperature=0.7
        )
        
        if not content:
            raise ValueError("LLM failed to generate questions")
        
        # Parse the response
        data = extract_json_from_text(content)
        
        if data is None:
            raise ValueError("Failed to extract JSON from LLM response")
        
        # Convert to our internal format
        questions = []
        for q_data in data.get("questions", []):
            options = [Option(letter=opt["letter"], text=opt["text"]) for opt in q_data["options"]]
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
                visual_description=q_data.get("visual_description"),
                subsection=q_data.get("subsection", "Synonyms")
            )
            questions.append(question)
        
        logger.info(f"Successfully generated {len(questions)} synonym questions from {len(words_to_generate)} words")
        return questions
        
    except Exception as e:
        logger.error(f"Failed to generate synonym questions from words: {e}")
        raise

# REMOVED: generate_reading_passage and generate_reading_passage_async functions
# These have been replaced by the unified generate_reading_passages() function

async def generate_questions_async(request: QuestionRequest, llm: Optional[str] = "deepseek", custom_examples: Optional[str] = None, training_examples: Optional[List[Dict[str, Any]]] = None) -> List[Question]:
    """Generate standalone questions (non-reading) using AI with real SSAT training examples - async version.
    
    Args:
        request: QuestionRequest with count and other parameters
        llm: LLM provider to use
        custom_examples: Custom training examples text
        training_examples: Pre-fetched training examples (to avoid double fetching)
    """
    logger.info(f"Generating {request.count} standalone {request.question_type.value} questions async")
    
    if request.question_type.value == "reading":
        raise ValueError("Reading comprehension questions should use generate_reading_passages_async() function instead of generate_questions_async()")
    
    # Handle simple word list format for synonyms
    if request.question_type.value == "synonym" and hasattr(request, 'input_format') and request.input_format == "simple":
        if not custom_examples:
            raise ValueError("Word list is required for simple word list format")
        return _generate_synonym_questions_from_words(request, custom_examples, llm)
    
    # Use provided training examples if available, otherwise fetch them
    if training_examples is None:
        generator = SSATGenerator()
        training_examples = generator.get_training_examples(request, custom_examples, request.count if request.question_type.value == "quantitative" else None)
        logger.info(f"📚 Fetched {len(training_examples)} training examples for {request.question_type.value}")
    else:
        logger.info(f"📚 Using {len(training_examples)} pre-fetched training examples for {request.question_type.value}")
    
    # Build few-shot prompt with training examples
    generator = SSATGenerator()
    system_message = generator.build_few_shot_prompt(request, training_examples)
    
    # Log training info
    if training_examples:
        if custom_examples:
            logger.info(f"Using {len(training_examples)} custom training examples")
        else:
            logger.info(f"Using {len(training_examples)} real SSAT examples for training")
    else:
        logger.info("No training examples found, using generic prompt")
    
    # Get available LLM providers
    provider = _select_llm_provider(llm)
    
    # Calculate appropriate max_tokens based on question count
    # Each question with options, explanations, etc. can be ~200-300 tokens
    # Add buffer for JSON structure and metadata
    estimated_tokens_per_question = 300
    base_tokens = 1000  # For JSON structure, metadata, etc.
    required_tokens = base_tokens + (request.count * estimated_tokens_per_question)
    max_tokens = min(required_tokens, 8000)  # Cap at 8000 to avoid hitting provider limits
    
    logger.info(f"Generating {request.count} questions, using max_tokens={max_tokens}")
    
    # Generate questions using async LLM call for true parallelism
    content = await llm_client.call_llm_async(
        provider=provider,
        system_message=system_message,
        prompt="Generate the questions as specified.",
        max_tokens=max_tokens,
        temperature=0.8  # Higher temperature for more variety in verbal questions
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
            visual_description=q_data.get("visual_description"),
            subsection=q_data.get("subsection")  # Extract AI-determined subsection
        )
        questions.append(question)
    
    logger.info(f"Successfully generated {len(questions)} questions async using {'custom examples' if custom_examples else 'real SSAT examples' if training_examples else 'generic prompt'}")
    if len(questions) != request.count:
        logger.warning(f"⚠️ Expected {request.count} questions but got {len(questions)} questions")
    return questions

# REMOVED: generate_multiple_reading_passages function
# This has been replaced by the unified generate_reading_passages() function

# REMOVED: generate_multiple_reading_passages_async function
# This has been replaced by the unified generate_reading_passages_async() function

def generate_reading_passages(request: QuestionRequest, llm: Optional[str] = "deepseek", custom_examples: Optional[str] = None, use_single_call: bool = False, training_examples: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Generate reading passages - unified function with hybrid approach.
    
    Args:
        request: QuestionRequest with count and other parameters
        llm: LLM provider to use
        custom_examples: Custom training examples text
        use_single_call: If True, generate all passages in one call (for admin/custom)
                        If False, generate passages one by one (for full test)
        training_examples: Pre-fetched training examples (to avoid double fetching)
    """
    logger.info(f"Generating {request.count} reading passages for request: {request} (single_call={use_single_call})")
    
    if use_single_call:
        return _generate_reading_passages_single_call(request, llm, custom_examples, training_examples)
    else:
        return _generate_reading_passages_multiple_calls(request, llm, custom_examples, training_examples)

def _generate_reading_passages_single_call(request: QuestionRequest, llm: str, custom_examples: Optional[str], training_examples: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Generate reading passages in a single LLM call."""
    generator = SSATGenerator()
    # Use pre-fetched training examples if provided, otherwise fetch them
    if training_examples is not None:
        # Use pre-fetched training examples
        logger.info(f"Using {len(training_examples)} pre-fetched training examples")
    elif custom_examples:
        training_examples = generator.parse_custom_examples(custom_examples, "reading")
        logger.info(f"Using {len(training_examples)} custom training examples")
    else:
        training_examples = generator.get_reading_training_examples(topic=request.topic)
        logger.info(f"Using {len(training_examples)} database training examples")
    
    system_message = generator.build_reading_few_shot_prompt(request, training_examples)
    
    provider = _select_llm_provider(llm)
    
    passage_tokens = 800
    question_tokens = 4 * 300
    base_tokens = 1000
    required_tokens = base_tokens + (request.count * (passage_tokens + question_tokens))
    max_tokens = min(required_tokens, 8000)
    
    content = llm_client.call_llm(
        provider=provider,
        system_message=system_message,
        prompt="Generate the reading passages and questions as specified.",
        max_tokens=max_tokens,
        temperature=0.8
    )

    if content is None:
        raise ValueError(f"LLM call to {provider.value} failed - no content returned")

    data = extract_json_from_text(content)
    
    if data is None:
        raise ValueError("Failed to extract JSON from LLM response")
    
    passages_data = []
    if "passages" in data:
        passages_data = data["passages"]
    elif "passage" in data and "questions" in data:
        passages_data = [data]
    else:
        raise ValueError("LLM response missing passage structure")
    
    results = []
    for i, passage_data in enumerate(passages_data):
        if "passage" not in passage_data or "questions" not in passage_data:
            logger.warning(f"Skipping passage {i+1} - missing passage or questions")
            continue
            
        passage_text = passage_data["passage"]
        questions_data = passage_data["questions"]
        
        questions = []
        for q_data in questions_data:
            options = [Option(letter=opt["letter"], text=opt["text"]) for opt in q_data["options"]]
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
        
        results.append({
            "passage": passage_text,
            "questions": questions,
            "passage_type": passage_data.get("passage_type", "General")
        })
    
    logger.info(f"Successfully generated {len(results)} reading passages with {'real SSAT examples' if training_examples else 'generic prompt'}")
    return results

def _generate_reading_passages_multiple_calls(request: QuestionRequest, llm: str, custom_examples: Optional[str], training_examples: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Generate reading passages in multiple LLM calls."""
    generator = SSATGenerator()
    results = []
    
    for i in range(request.count):
        # Get a single passage and its questions
        passage_data = _generate_single_reading_passage(request, llm, custom_examples, training_examples)
        if passage_data:
            results.append(passage_data)
        else:
            logger.warning(f"Failed to generate passage {i+1}, stopping.")
            break # Stop if one generation fails
    
    logger.info(f"Successfully generated {len(results)} reading passages with {'real SSAT examples' if training_examples else 'generic prompt'}")
    return results

def _generate_single_reading_passage(request: QuestionRequest, llm: str, custom_examples: Optional[str], training_examples: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
    """Generate a single reading passage and its questions."""
    generator = SSATGenerator()
    # Use pre-fetched training examples if provided, otherwise fetch them
    if training_examples is not None:
        # Use pre-fetched training examples
        logger.info(f"Using {len(training_examples)} pre-fetched training examples")
    elif custom_examples:
        training_examples = generator.parse_custom_examples(custom_examples, "reading")
        logger.info(f"Using {len(training_examples)} custom training examples")
    else:
        training_examples = generator.get_reading_training_examples(topic=request.topic)
        logger.info(f"Using {len(training_examples)} database training examples")
    
    system_message = generator.build_reading_few_shot_prompt(request, training_examples)
    
    provider = _select_llm_provider(llm)
    
    passage_tokens = 800
    question_tokens = 4 * 300
    base_tokens = 1000
    required_tokens = base_tokens + (passage_tokens + question_tokens)
    max_tokens = min(required_tokens, 8000)
    
    content = llm_client.call_llm(
        provider=provider,
        system_message=system_message,
        prompt="Generate the reading passage and its 4 comprehension questions as specified.",
        max_tokens=max_tokens,
        temperature=0.8
    )

    if content is None:
        logger.warning(f"LLM call to {provider.value} failed for single passage generation.")
        return None

    data = extract_json_from_text(content)
    
    if data is None:
        logger.warning(f"Failed to extract JSON from LLM response for single passage.")
        return None
    
    if "passage" not in data or "questions" not in data:
        logger.warning(f"LLM response missing passage or questions for single passage.")
        return None
    
    passage_text = data["passage"]
    questions_data = data["questions"]
    
    questions = []
    for q_data in questions_data:
        options = [Option(letter=opt["letter"], text=opt["text"]) for opt in q_data["options"]]
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
    
    return {
        "passage": passage_text,
        "questions": questions,
        "passage_type": data.get("passage_type", "General")
    }

async def generate_reading_passages_async(request: QuestionRequest, llm: Optional[str] = "deepseek", custom_examples: Optional[str] = None, use_single_call: bool = False, training_examples: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Generate reading passages asynchronously - unified function with hybrid approach.
    
    Args:
        request: QuestionRequest with count and other parameters
        llm: LLM provider to use
        custom_examples: Custom training examples text
        use_single_call: If True, generate all passages in one call (for admin/custom)
                        If False, generate passages one by one (for full test)
        training_examples: Pre-fetched training examples (to avoid double fetching)
    """
    logger.info(f"Generating {request.count} reading passages async for request: {request} (single_call={use_single_call})")
    
    if use_single_call:
        return await _generate_reading_passages_single_call_async(request, llm, custom_examples, training_examples)
    else:
        return await _generate_reading_passages_multiple_calls_async(request, llm, custom_examples, training_examples)

async def _generate_reading_passages_single_call_async(request: QuestionRequest, llm: str, custom_examples: Optional[str], training_examples: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Generate reading passages in a single async LLM call."""
    generator = SSATGenerator()
    # Use pre-fetched training examples if provided, otherwise fetch them
    if training_examples is not None:
        # Use pre-fetched training examples
        logger.info(f"Using {len(training_examples)} pre-fetched training examples")
    elif custom_examples:
        training_examples = generator.parse_custom_examples(custom_examples, "reading")
        logger.info(f"Using {len(training_examples)} custom training examples")
    else:
        training_examples = generator.get_reading_training_examples(topic=request.topic)
        logger.info(f"Using {len(training_examples)} database training examples")
    
    system_message = generator.build_reading_few_shot_prompt(request, training_examples)
    
    provider = _select_llm_provider(llm)
    
    passage_tokens = 800
    question_tokens = 4 * 300
    base_tokens = 1000
    required_tokens = base_tokens + (request.count * (passage_tokens + question_tokens))
    max_tokens = min(required_tokens, 8000)
    
    content = await llm_client.call_llm_async(
        provider=provider,
        system_message=system_message,
        prompt="Generate the reading passages and questions as specified.",
        max_tokens=max_tokens,
        temperature=0.8
    )

    if content is None:
        raise ValueError(f"Async LLM call to {provider.value} failed - no content returned")

    data = extract_json_from_text(content)
    
    if data is None:
        raise ValueError("Failed to extract JSON from async LLM response")
    
    passages_data = []
    if "passages" in data:
        passages_data = data["passages"]
    elif "passage" in data and "questions" in data:
        passages_data = [data]
    else:
        raise ValueError("Async LLM response missing passage structure")
    
    results = []
    for i, passage_data in enumerate(passages_data):
        if "passage" not in passage_data or "questions" not in passage_data:
            logger.warning(f"Skipping passage {i+1} - missing passage or questions")
            continue
            
        passage_text = passage_data["passage"]
        questions_data = passage_data["questions"]
        
        questions = []
        for q_data in questions_data:
            options = [Option(letter=opt["letter"], text=opt["text"]) for opt in q_data["options"]]
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
        
        results.append({
            "passage": passage_text,
            "questions": questions,
            "passage_type": passage_data.get("passage_type", "General")
        })
    
    logger.info(f"Successfully generated {len(results)} reading passages async with {'real SSAT examples' if training_examples else 'generic prompt'}")
    
    return results

async def _generate_reading_passages_multiple_calls_async(request: QuestionRequest, llm: str, custom_examples: Optional[str], training_examples: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Generate reading passages in multiple async LLM calls."""
    generator = SSATGenerator()
    results = []
    
    # Create tasks for parallel execution
    tasks = []
    for i in range(request.count):
        task = _generate_single_reading_passage_async(request, llm, custom_examples, training_examples)
        tasks.append(task)
    
    # Execute all tasks concurrently
    passage_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    for i, result in enumerate(passage_results):
        if isinstance(result, Exception):
            logger.warning(f"Failed to generate passage {i+1}: {result}")
            continue
        if result:
            results.append(result)
        else:
            logger.warning(f"Failed to generate passage {i+1}, result was None")
    
    logger.info(f"Successfully generated {len(results)} reading passages async with {'real SSAT examples' if custom_examples else 'generic prompt'}")
    return results

async def _generate_single_reading_passage_async(request: QuestionRequest, llm: str, custom_examples: Optional[str], training_examples: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
    """Generate a single reading passage and its questions asynchronously."""
    generator = SSATGenerator()
    # Use pre-fetched training examples if provided, otherwise fetch them
    if training_examples is not None:
        # Use pre-fetched training examples
        logger.info(f"Using {len(training_examples)} pre-fetched training examples")
    elif custom_examples:
        training_examples = generator.parse_custom_examples(custom_examples, "reading")
        logger.info(f"Using {len(training_examples)} custom training examples")
    else:
        training_examples = generator.get_reading_training_examples(topic=request.topic)
        logger.info(f"Using {len(training_examples)} database training examples")
    
    system_message = generator.build_reading_few_shot_prompt(request, training_examples)
    
    provider = _select_llm_provider(llm)
    
    passage_tokens = 800
    question_tokens = 4 * 300
    base_tokens = 1000
    required_tokens = base_tokens + (passage_tokens + question_tokens)
    max_tokens = min(required_tokens, 8000)
    
    content = await llm_client.call_llm_async(
        provider=provider,
        system_message=system_message,
        prompt="Generate the reading passage and its 4 comprehension questions as specified.",
        max_tokens=max_tokens,
        temperature=0.8
    )

    if content is None:
        logger.warning(f"Async LLM call to {provider.value} failed for single passage generation.")
        return None

    data = extract_json_from_text(content)
    
    if data is None:
        logger.warning(f"Failed to extract JSON from async LLM response for single passage.")
        return None
    
    if "passage" not in data or "questions" not in data:
        logger.warning(f"Async LLM response missing passage or questions for single passage.")
        return None
    
    passage_text = data["passage"]
    questions_data = data["questions"]
    
    questions = []
    for q_data in questions_data:
        options = [Option(letter=opt["letter"], text=opt["text"]) for opt in q_data["options"]]
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
    
    return {
        "passage": passage_text,
        "questions": questions,
        "passage_type": data.get("passage_type", "General")
    }