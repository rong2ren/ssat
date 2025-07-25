"""SSAT question generator using real SSAT examples for training."""

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
            
            if training_examples:
                logger.info(f"📚 READING TRAINING SUMMARY: Using {len(training_examples)} real SSAT reading examples")
            
            return training_examples
            
        except Exception as e:
            logger.warning(f"Failed to get reading training examples: {e}")
            return []
    
    def get_writing_training_examples(self, topic: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get writing prompt training examples from database."""
        try:
            if topic:
                # Use topic-filtered search for specific topics
                response = self.supabase.rpc('get_writing_training_examples', {
                    'topic_filter': topic,
                    'limit_count': 3
                }).execute()
                
                if response.data:
                    logger.info(f"Found {len(response.data)} writing training examples for topic '{topic}'")
                    return response.data
            
            # Fallback: get random examples
            response = self.supabase.rpc('get_writing_training_examples', {
                'limit_count': 3
            }).execute()
            
            training_examples = response.data if response.data else []
            
            if training_examples:
                logger.info(f"📚 WRITING TRAINING SUMMARY: Using {len(training_examples)} real SSAT writing examples")
            else:
                logger.warning("No writing training examples found in database")
            
            return training_examples
            
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

TAGS QUALITY RULES:
- Each tag should capture a DIFFERENT aspect of the writing task
- Make tags specific enough for writing curriculum planning
- Include both skills and content/theme elements

EXAMPLE ANALYSIS:
Prompt: "Picture showing children working together to build something"
SUBSECTION: "Collaborative Problem-Solving Narratives"
TAGS: ["teamwork-themes", "problem-solving-process", "character-interaction", "descriptive-language"]

OUTPUT FORMAT - Return ONLY a JSON object:
{{
  "prompts": [
    {{
      "prompt": "Complete writing prompt text here (JUST the creative prompt, NO instructions)",
      "visual_description": "Description of the picture that would accompany this prompt",
      "grade_level": "3-4",
      "story_elements": ["element1", "element2", "element3"],
      "prompt_type": "picture_story",
      "subsection": "Collaborative Problem-Solving Narratives",
      "tags": ["teamwork-themes", "problem-solving-process", "character-interaction", "descriptive-language"]
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
      "grade_level": "3-4",
      "story_elements": ["element1", "element2", "element3"],
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
        
        if not training_examples:
            # Use appropriate base prompt based on question type
            if request.question_type.value == "quantitative":
                logger.info(f"📚 No training examples available for {request.question_type.value}, using base quantitative prompt")
                return self.build_base_quantitative_prompt(request)
            else:
                logger.info(f"📚 No training examples available for {request.question_type.value}, using base verbal prompt")
                return self.build_base_verbal_prompt(request)
        
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
            
            # Log training example summary (not full details)
            logger.debug(f"Training example {valid_examples}: {example['question'][:50]}...")
        
        logger.info(f"📚 TRAINING SUMMARY: Using {valid_examples} real SSAT examples for {request.question_type.value} questions")
        
        # Get appropriate base prompt based on question type
        if request.question_type.value == "quantitative":
            base_prompt = self.build_base_quantitative_prompt(request)
        else:
            base_prompt = self.build_base_verbal_prompt(request)
        
        # Extend base prompt with examples
        complete_prompt = f"""{base_prompt}

STUDY THESE REAL SSAT EXAMPLES FROM OFFICIAL TESTS:

{examples_text}

Generate questions that match the EXACT style, difficulty, and format of these examples."""
        
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
        
        topic_instruction_number = 8 
        if request.topic:
            system_prompt += f"{topic_instruction_number}. Focus the passage topic on: {request.topic}\n"
            topic_instruction_number += 1
        
        system_prompt += f"""

CRITICAL CATEGORIZATION REQUIREMENTS:

{topic_instruction_number}. PASSAGE TYPE ANALYSIS: Create a SPECIFIC, descriptive passage type that captures both content and genre.

PASSAGE TYPE RULES:
- Be SPECIFIC about both content and genre (NEVER use "Fiction", "Non-fiction" alone)
- Capture what makes this passage unique for reading instruction
- Consider the specific skills this passage type develops

GOOD PASSAGE TYPE EXAMPLES:
- "Character-Driven Adventure Fiction" (for stories focusing on character development through adventure)
- "Scientific Process Informational" (for science texts explaining how things work)
- "Historical Biography Narrative" (for life stories with historical context)
- "Animal Behavior Science Text" (for factual texts about animal characteristics)
- "Problem-Solution Social Studies" (for texts about social issues and solutions)

{topic_instruction_number + 1}. READING TAGS ANALYSIS: For each question, create 2-4 specific tags that capture the EXACT reading comprehension skills being tested.

TAG CATEGORIES (choose from different categories):
- Comprehension Skills: ["main-idea-identification", "supporting-details", "inference-making", "conclusion-drawing", "author-purpose"]
- Text Analysis: ["character-analysis", "plot-development", "cause-and-effect", "compare-contrast", "sequence-understanding"]  
- Vocabulary Skills: ["context-clues", "word-meaning", "vocabulary-development", "technical-terms", "figurative-language"]
- Critical Thinking: ["evidence-evaluation", "perspective-analysis", "prediction-making", "connection-building", "interpretation-skills"]

TAGS QUALITY RULES:
- Each tag should specify the EXACT skill being tested
- Make tags specific enough for reading assessment planning
- Include both comprehension level and skill type

EXAMPLE ANALYSIS:
Passage: Character-driven story about overcoming challenges
Question: "What motivated Sarah to continue despite the difficulties?"
SUBSECTION: "Character-Driven Adventure Fiction"
TAGS: ["character-motivation", "inference-making", "text-analysis", "emotional-understanding"]

OUTPUT FORMAT - Return ONLY a JSON object with SEPARATE passage and questions:
{{
  "passage": {{
    "text": "The complete reading passage goes here (similar length to examples)",
    "title": "Optional passage title", 
    "passage_type": "Character-Driven Adventure Fiction",
    "grade_level": "3-4",
    "topic": "passage topic"
  }},
  "questions": [
    {{
      "text": "Question about the passage (without repeating the passage)",
      "options": [
        {{"letter": "A", "text": "option text"}},
        {{"letter": "B", "text": "option text"}},
        {{"letter": "C", "text": "option text"}},
        {{"letter": "D", "text": "option text"}}
      ],
      "correct_answer": "A",
      "explanation": "detailed explanation",
      "cognitive_level": "UNDERSTAND",
      "tags": ["character-motivation", "inference-making", "text-analysis", "emotional-understanding"],
      "subsection": "Character-Driven Adventure Fiction",
      "visual_description": "Description of any visual elements in the passage"
    }}
  ]
}}

CRITICAL VALIDATION REQUIREMENTS:
- passage_type: MUST be specific and descriptive (NO generic "Fiction", "Non-fiction")
- All questions.subsection: MUST match the passage_type exactly
- tags: MUST be exactly 2-4 specific reading skill descriptors
- cognitive_level: MUST be one of: REMEMBER, UNDERSTAND, APPLY, ANALYZE
- EVERY question MUST have specific, educational tags - NOT optional

QUALITY CHECK: Before finalizing, ask yourself:
1. Would a reading teacher find this passage type useful for lesson planning?
2. Do the tags clearly identify what reading skills are being assessed?
3. Could someone search for these specific comprehension skills?
If any answer is NO, improve your categorization."""
        
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

    def build_base_quantitative_prompt(self, request: QuestionRequest) -> str:
        """Build base prompt for quantitative questions with all instructions and requirements."""
        
        system_prompt = f"""You are an expert SSAT quantitative question generator.

Your task: Generate {request.count} NEW quantitative questions that match SSAT Elementary style and format.

CRITICAL REQUIREMENTS:
1. Follow the EXACT question structure and phrasing style from SSAT Elementary tests
2. Match the difficulty level: {request.difficulty.value}
3. Use the same answer choice format (A, B, C, D)
4. Provide detailed explanations like real SSAT questions
5. Questions must be suitable for elementary level students
6. Each question should have exactly 4 options

"""
        
        topic_instruction_number = 7
        if request.topic:
            system_prompt += f"{topic_instruction_number}. Focus specifically on the topic: {request.topic}\n"
            topic_instruction_number += 1
        
        system_prompt += f"""

CRITICAL CATEGORIZATION REQUIREMENTS:

{topic_instruction_number}. SUBSECTION ANALYSIS: After generating each question, analyze its mathematical content deeply and create a SPECIFIC subsection name that captures the core mathematical concept and approach. 

SUBSECTION CREATION RULES:
- Be SPECIFIC, not generic (NEVER use "General Math", "Basic Math", "Arithmetic")
- Capture the MAIN mathematical skill being tested
- Include complexity level when relevant
- Consider the problem-solving approach required

GOOD SUBSECTION EXAMPLES:
- "Multi-Step Algebraic Word Problems" (for problems requiring variable setup and equation solving)
- "Fraction Operations with Visual Models" (for fraction problems with diagrams)
- "Geometry with Measurement Applications" (for shape problems involving area/perimeter)
- "Data Analysis and Interpretation" (for problems involving charts, graphs, statistics)
- "Money and Decimal Calculations" (for real-world money problems)
- "Ratio and Proportion Reasoning" (for problems involving relationships between quantities)

{topic_instruction_number + 1}. TAGS ANALYSIS: Create 2-4 highly descriptive tags that capture DIFFERENT aspects of the question:

TAG CATEGORIES (choose from different categories):
- Mathematical Content: ["algebraic-thinking", "geometric-reasoning", "number-sense", "measurement-concepts", "data-analysis", "fraction-concepts", "decimal-operations"]
- Problem Type: ["word-problem", "computational-fluency", "conceptual-understanding", "application-problem", "reasoning-proof"]
- Context/Setting: ["real-world-application", "abstract-mathematical", "visual-representation", "practical-scenario", "academic-context"]
- Cognitive Demand: ["multi-step-solution", "single-step-direct", "requires-strategy", "pattern-recognition", "logical-reasoning"]
- Skills Required: ["equation-setup", "diagram-interpretation", "unit-conversion", "estimation", "mental-math", "calculator-appropriate"]

TAGS QUALITY RULES:
- Each tag should describe a DIFFERENT aspect of the question
- Be specific enough that a teacher could search by tag and find relevant questions
- Include at least one content tag and one skill/process tag
- Make tags useful for curriculum planning and assessment

OUTPUT FORMAT - Return ONLY a JSON object:
{{
  "questions": [
    {{
      "text": "question text",
      "options": [{{"letter": "A", "text": "option"}}, {{"letter": "B", "text": "option"}}, {{"letter": "C", "text": "option"}}, {{"letter": "D", "text": "option"}}],
      "correct_answer": "A",
      "explanation": "detailed explanation",
      "cognitive_level": "UNDERSTAND",
      "tags": ["tag1", "tag2", "tag3"],
      "subsection": "Specific subsection name",
      "visual_description": "Description of any visual elements (if applicable)"
    }}
  ]
}}"""
        
        return system_prompt

    def build_base_verbal_prompt(self, request: QuestionRequest) -> str:
        """Build base prompt for verbal questions (analogy/synonym) with all instructions and requirements."""
        
        system_prompt = f"""You are an expert SSAT verbal question generator.

Your task: Generate {request.count} NEW {request.question_type.value} questions that match SSAT Elementary style and format.

CRITICAL REQUIREMENTS:
1. Follow the EXACT question structure and phrasing style from SSAT Elementary tests
2. Match the difficulty level: {request.difficulty.value}
3. Use the same answer choice format (A, B, C, D)
4. Provide detailed explanations like real SSAT questions
5. Questions must be suitable for elementary level students
6. Each question should have exactly 4 options
7. NO visual elements are required for verbal questions - these are text-only questions

"""
        
        topic_instruction_number = 8
        if request.topic:
            system_prompt += f"{topic_instruction_number}. Focus specifically on the topic: {request.topic}\n"
            topic_instruction_number += 1
        
        system_prompt += f"""

CRITICAL CATEGORIZATION REQUIREMENTS:

{topic_instruction_number}. SUBSECTION ANALYSIS: Create a SPECIFIC subsection that captures the vocabulary skill and relationship type being tested.

SUBSECTION CREATION RULES:
- Be SPECIFIC about the vocabulary skill (NEVER use "Vocabulary", "Verbal" alone)
- Capture the specific relationship or skill being tested
- Consider the cognitive level required

GOOD SUBSECTION EXAMPLES:
- "Synonym Recognition with Context Clues" (for synonym questions requiring context)
- "Analogy Relationship Mapping" (for analogy questions testing logical relationships)
- "Vocabulary in Context" (for questions requiring context understanding)
- "Word Association Patterns" (for questions testing word relationships)

{topic_instruction_number + 1}. TAGS ANALYSIS: Create 2-4 specific tags that capture different aspects of the vocabulary skill:

TAG CATEGORIES (choose from different categories):
- Vocabulary Skills: ["context-clues", "word-relationships", "synonym-recognition", "analogy-mapping", "vocabulary-building"]
- Cognitive Skills: ["logical-reasoning", "pattern-recognition", "inference-making", "comparison-analysis"]
- Content Areas: ["academic-vocabulary", "everyday-language", "descriptive-words", "action-words"]

TAGS QUALITY RULES:
- Each tag should capture a DIFFERENT aspect of the vocabulary skill
- Make tags specific enough for vocabulary assessment planning
- Include both skill type and content area

OUTPUT FORMAT - Return ONLY a JSON object:
{{
  "questions": [
    {{
      "text": "question text",
      "options": [{{"letter": "A", "text": "option"}}, {{"letter": "B", "text": "option"}}, {{"letter": "C", "text": "option"}}, {{"letter": "D", "text": "option"}}],
      "correct_answer": "A",
      "explanation": "detailed explanation",
      "cognitive_level": "UNDERSTAND",
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

Your task: Generate {request.count} NEW reading comprehension questions that match SSAT Elementary style and format.

CRITICAL REQUIREMENTS:
1. Create a reading passage first (appropriate length and style for elementary students)
2. Follow SSAT Elementary question structure and phrasing style
3. Match the difficulty level: {request.difficulty.value}
4. Use the same answer choice format (A, B, C, D)
5. Questions must test reading comprehension skills
6. Suitable for elementary level students (grades 3-4)
7. Each question should have exactly 4 options
8. Passage should be engaging and age-appropriate

"""
        
        topic_instruction_number = 9
        if request.topic:
            system_prompt += f"{topic_instruction_number}. Focus the passage topic on: {request.topic}\n"
            topic_instruction_number += 1
        
        system_prompt += f"""

CRITICAL CATEGORIZATION REQUIREMENTS:

{topic_instruction_number}. PASSAGE TYPE ANALYSIS: Create a SPECIFIC, descriptive passage type that captures both content and genre.

PASSAGE TYPE RULES:
- Be SPECIFIC about both content and genre (NEVER use "Fiction", "Non-fiction" alone)
- Capture what makes this passage unique for reading instruction
- Consider the specific skills this passage type develops

GOOD PASSAGE TYPE EXAMPLES:
- "Character-Driven Adventure Fiction" (for stories focusing on character development through adventure)
- "Scientific Process Informational" (for science texts explaining how things work)
- "Historical Biography Narrative" (for life stories with historical context)
- "Animal Behavior Science Text" (for factual texts about animal characteristics)
- "Problem-Solution Social Studies" (for texts about social issues and solutions)

{topic_instruction_number + 1}. READING TAGS ANALYSIS: For each question, create 2-4 specific tags that capture the EXACT reading comprehension skills being tested.

TAG CATEGORIES (choose from different categories):
- Comprehension Skills: ["main-idea-identification", "supporting-details", "inference-making", "conclusion-drawing", "author-purpose"]
- Text Analysis: ["character-analysis", "plot-development", "cause-and-effect", "compare-contrast", "sequence-understanding"]  
- Vocabulary Skills: ["context-clues", "word-meaning", "vocabulary-development", "technical-terms", "figurative-language"]
- Critical Thinking: ["evidence-evaluation", "perspective-analysis", "prediction-making", "connection-building", "interpretation-skills"]

TAGS QUALITY RULES:
- Each tag should specify the EXACT skill being tested
- Make tags specific enough for reading assessment planning
- Include both comprehension level and skill type

OUTPUT FORMAT - Return ONLY a JSON object:
{{
  "passage": {{
    "text": "Complete reading passage text here",
    "title": "Passage title",
    "passage_type": "Specific passage type",
    "grade_level": "3-4",
    "topic": "Passage topic"
  }},
  "questions": [
    {{
      "text": "Question text",
      "options": [{{"letter": "A", "text": "option"}}, {{"letter": "B", "text": "option"}}, {{"letter": "C", "text": "option"}}, {{"letter": "D", "text": "option"}}],
      "correct_answer": "A",
      "explanation": "Detailed explanation",
      "cognitive_level": "UNDERSTAND",
      "tags": ["tag1", "tag2"],
      "subsection": "Passage type"
    }}
  ]
}}"""
        
        return system_prompt

    def build_base_writing_prompt(self, request: QuestionRequest) -> str:
        """Build base prompt for writing prompts with all instructions and requirements."""
        
        system_prompt = f"""You are an expert SSAT Elementary writing prompt generator.

Your task: Generate {request.count} NEW writing prompts that match SSAT Elementary style and format.

CRITICAL REQUIREMENTS:
1. Follow SSAT Elementary prompt structure and style
2. Create elementary-appropriate prompts (grades 3-4)
3. Include clear, engaging visual descriptions for picture prompts
4. Focus on creative storytelling with beginning, middle, and end
5. Use simple, age-appropriate language and concepts
6. Prompts should be engaging and inspire creativity

"""
        
        topic_instruction_number = 7
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

TAGS QUALITY RULES:
- Each tag should capture a DIFFERENT aspect of the writing task
- Make tags specific enough for writing curriculum planning
- Include both skills and content/theme elements

OUTPUT FORMAT - Return ONLY a JSON object:
{{
  "prompts": [
    {{
      "prompt": "Complete writing prompt text here (JUST the creative prompt, NO instructions)",
      "visual_description": "Description of the picture that would accompany this prompt",
      "grade_level": "3-4",
      "story_elements": ["element1", "element2", "element3"],
      "prompt_type": "picture_story",
      "subsection": "Specific subsection name",
      "tags": ["tag1", "tag2", "tag3", "tag4"]
    }}
  ]
}}"""
        
        return system_prompt

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
        provider = _select_llm_provider(llm)
        
        # Calculate appropriate max_tokens based on question count
        # Each question with options, explanations, etc. can be ~200-300 tokens
        # Add buffer for JSON structure and metadata
        estimated_tokens_per_question = 300
        base_tokens = 1000  # For JSON structure, metadata, etc.
        required_tokens = base_tokens + (request.count * estimated_tokens_per_question)
        max_tokens = min(required_tokens, 8000)  # Cap at 8000 to avoid hitting provider limits
        
        logger.debug(f"Generating {request.count} questions, using max_tokens={max_tokens}")
        
        # Generate questions using LLM
        content = llm_client.call_llm(
            provider=provider,
            system_message=system_message,
            prompt="Generate the questions as specified.",
            max_tokens=max_tokens
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
        
        logger.info(f"Successfully generated {len(questions)} questions using {'real SSAT examples' if training_examples else 'generic prompt'}")
        if len(questions) != request.count:
            logger.warning(f"⚠️ Expected {request.count} questions but got {len(questions)} questions")
        
        # Add provider information to each question's metadata
        for question in questions:
            if not hasattr(question, 'metadata'):
                question.metadata = {}
            question.metadata['provider_used'] = provider.value
        
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
        provider = _select_llm_provider(llm)
        
        # Calculate appropriate max_tokens for reading passage + questions
        # Reading passages can be long (~500-800 tokens) + 4 questions (~1200 tokens)
        passage_tokens = 800
        question_tokens = 4 * 300  # 4 questions
        base_tokens = 1000  # For JSON structure, metadata, etc.
        required_tokens = base_tokens + passage_tokens + question_tokens
        max_tokens = min(required_tokens, 8000)  # Cap at 8000 to avoid hitting provider limits
        
        logger.debug(f"Generating reading passage with 4 questions, using max_tokens={max_tokens}")
        
        # Generate passage and questions using LLM
        content = llm_client.call_llm(
            provider=provider,
            system_message=system_message,
            prompt="Generate the reading passage and questions as specified.",
            max_tokens=max_tokens
        )

        if content is None:
            raise ValueError(f"LLM call to {provider.value} failed - no content returned")

        data = extract_json_from_text(content)
        
        if data is None:
            raise ValueError("Failed to extract JSON from LLM response")
        
        # Validate response has both passage and questions
        if "passage" not in data or "questions" not in data:
            raise ValueError("LLM response missing passage or questions structure")
        
        passage_data = data["passage"]
        questions_data = data["questions"]
        
        # Parse questions into proper format
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
        provider = _select_llm_provider(llm)
        
        # Calculate appropriate max_tokens for reading passage + questions
        # Reading passages can be long (~500-800 tokens) + 4 questions (~1200 tokens)
        passage_tokens = 800
        question_tokens = 4 * 300  # 4 questions
        base_tokens = 1000  # For JSON structure, metadata, etc.
        required_tokens = base_tokens + passage_tokens + question_tokens
        max_tokens = min(required_tokens, 8000)  # Cap at 8000 to avoid hitting provider limits
        
        logger.info(f"Generating reading passage with 4 questions, using max_tokens={max_tokens}")
        
        # Generate passage and questions using async LLM call
        content = await llm_client.call_llm_async(
            provider=provider,
            system_message=system_message,
            prompt="Generate the reading passage and questions as specified.",
            max_tokens=max_tokens
        )

        if content is None:
            raise ValueError(f"LLM call to {provider.value} failed - no content returned")

        data = extract_json_from_text(content)
        
        if data is None:
            raise ValueError("Failed to extract JSON from LLM response")
        
        # Validate response has both passage and questions
        if "passage" not in data or "questions" not in data:
            raise ValueError("LLM response missing passage or questions structure")
        
        passage_data = data["passage"]
        questions_data = data["questions"]
        
        # Parse questions into proper format
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
            max_tokens=max_tokens
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
        
        logger.info(f"Successfully generated {len(questions)} questions async using {'real SSAT examples' if training_examples else 'generic prompt'}")
        if len(questions) != request.count:
            logger.warning(f"⚠️ Expected {request.count} questions but got {len(questions)} questions")
        return questions
        
    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Failed to parse AI response: {e}")
    except Exception as e:
        logger.error(f"Error in async question generation: {e}")
        raise