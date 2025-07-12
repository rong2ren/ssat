"""Service for question generation logic."""

import time
import uuid
from typing import List, Dict, Any, Optional
from loguru import logger

# Import SSAT modules (now local)
from app.core_models import QuestionRequest, QuestionType as SSATQuestionType, DifficultyLevel as SSATDifficultyLevel
from app.generator import generate_questions, SSATGenerator
from app.settings import settings
from app.models.requests import QuestionGenerationRequest, CompleteTestRequest, QuestionType, DifficultyLevel
from app.models.responses import StandaloneSection, ReadingSection, WritingSection, ReadingPassage, WritingPrompt

# Loguru logger imported above

class QuestionService:
    """Service class for handling question generation logic."""
    
    def __init__(self):
        """Initialize the question service."""
        self.generator = None
        self._init_generator()
    
    def _init_generator(self):
        """Initialize SSAT generator with database connection."""
        try:
            self.generator = SSATGenerator()
            logger.info("SSAT Generator initialized")
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
                question_type=SSATQuestionType.MATH,
                difficulty=SSATDifficultyLevel.MEDIUM,
                count=1
            )
            examples = self.generator.get_training_examples(test_request)
            return True  # If no exception, connection is healthy
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def _convert_to_ssat_request(self, request: QuestionGenerationRequest) -> QuestionRequest:
        """Convert API request to internal SSAT request format."""
        # Map API enums to internal enums
        question_type_mapping = {
            QuestionType.MATH: SSATQuestionType.MATH,
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
    
    async def generate_questions(self, request: QuestionGenerationRequest) -> Dict[str, Any]:
        """Generate questions based on the request."""
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        try:
            # Convert to internal request format
            ssat_request = self._convert_to_ssat_request(request)
            
            # Generate questions using existing logic
            provider = request.provider.value if request.provider else None
            questions = generate_questions(ssat_request, llm=provider)
            
            generation_time = time.time() - start_time
            
            # Convert questions to API response format
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
            
            # Get provider info (you'll need to implement this)
            provider_used = provider or "auto-selected"
            
            return {
                "questions": api_questions,
                "metadata": {
                    "generation_time": generation_time,
                    "provider_used": provider_used,
                    "training_examples_count": 5,  # Default, you can get actual count
                    "request_id": request_id
                },
                "status": "success",
                "count": len(api_questions)
            }
            
        except Exception as e:
            logger.error(f"Question generation failed: {e}")
            raise e
    
    async def generate_complete_test(self, request: CompleteTestRequest) -> Dict[str, Any]:
        """Generate a complete SSAT practice test."""
        start_time = time.time()
        test_id = str(uuid.uuid4())
        
        try:
            # Define default question counts for each section
            default_counts = {
                QuestionType.MATH: 25,
                QuestionType.VERBAL: 30,
                QuestionType.READING: 7,  # Usually fewer reading passages with multiple questions each
                QuestionType.WRITING: 1   # Usually one writing prompt
            }
            
            # Use custom counts if provided, otherwise use defaults
            section_counts = {}
            for section in request.include_sections:
                if request.custom_counts and section.value in request.custom_counts:
                    section_counts[section] = request.custom_counts[section.value]
                else:
                    section_counts[section] = default_counts.get(section, 10)
            
            # Generate questions for each section
            sections = []
            total_questions = 0
            
            for section_type, count in section_counts.items():
                logger.info(f"Generating {section_type.value} section")
                
                # Generate different content types based on section
                if section_type == QuestionType.WRITING:
                    section = await self._generate_writing_section(request.difficulty)
                    total_questions += 1  # Writing counts as 1 "item"
                elif section_type == QuestionType.READING:
                    section = await self._generate_reading_section(request.difficulty, count, request.provider)
                    total_questions += len(section.passages) * 4  # 4 questions per passage
                else:
                    # Standalone sections (math, verbal, analogy, synonym)
                    section = await self._generate_standalone_section(section_type, request.difficulty, count, request.provider)
                    total_questions += len(section.questions)
                
                sections.append(section)
            
            generation_time = time.time() - start_time
            estimated_time = sum(section.time_limit_minutes for section in sections)
            
            return {
                "test_id": test_id,
                "sections": sections,
                "metadata": {
                    "generation_time": generation_time,
                    "provider_used": request.provider.value if request.provider else "auto-selected",
                    "training_examples_count": 5 * len(sections),  # Approximate
                    "request_id": test_id
                },
                "status": "success",
                "total_questions": total_questions,
                "estimated_time_minutes": estimated_time
            }
            
        except Exception as e:
            logger.error(f"Complete test generation failed: {e}")
            raise e
    
    def _get_section_instructions(self, section_type: QuestionType) -> str:
        """Get instructions for a specific test section."""
        instructions = {
            QuestionType.MATH: "Solve each problem and choose the best answer. You may use scratch paper for calculations.",
            QuestionType.VERBAL: "Choose the word that best completes each sentence or answers each question.",
            QuestionType.READING: "Read each passage carefully and answer the questions that follow.",
            QuestionType.WRITING: "Write a short essay in response to the prompt. Use proper grammar and organization.",
            QuestionType.ANALOGY: "Choose the pair of words that has the same relationship as the given pair.",
            QuestionType.SYNONYM: "Choose the word that means the same or nearly the same as the given word."
        }
        return instructions.get(section_type, "Answer all questions to the best of your ability.")
    
    def _get_section_time_limit(self, section_type: QuestionType, question_count: int) -> int:
        """Get recommended time limit for a section based on type and question count."""
        # Time per question in minutes (approximate)
        time_per_question = {
            QuestionType.MATH: 1.5,
            QuestionType.VERBAL: 0.8,
            QuestionType.READING: 2.0,  # Reading takes longer
            QuestionType.WRITING: 15.0,  # Writing prompts take much longer
            QuestionType.ANALOGY: 1.0,
            QuestionType.SYNONYM: 0.5
        }
        
        base_time = time_per_question.get(section_type, 1.0)
        return int(base_time * question_count)
    
    async def get_topic_suggestions(self, question_type: str) -> List[str]:
        """Get suggested topics for a given question type."""
        # Define common topics for each question type
        topic_suggestions = {
            "math": [
                "addition", "subtraction", "multiplication", "division",
                "fractions", "decimals", "geometry", "measurement",
                "word problems", "patterns", "time", "money"
            ],
            "verbal": [
                "vocabulary", "synonyms", "antonyms", "analogies",
                "word relationships", "definitions"
            ],
            "reading": [
                "fiction", "non-fiction", "poetry", "biography",
                "science", "history", "main idea", "details",
                "inference", "vocabulary in context"
            ],
            "writing": [
                "narrative", "descriptive", "persuasive", "personal experience",
                "opinion", "compare and contrast"
            ]
        }
        
        return topic_suggestions.get(question_type, [])
    
    async def _generate_writing_prompt(self, difficulty: DifficultyLevel) -> Dict[str, Any]:
        """Generate a writing prompt for the writing section."""
        from app.specifications import ELEMENTARY_WRITING_PROMPTS
        import random
        
        # Select a random prompt appropriate for elementary level
        prompt_data = random.choice(ELEMENTARY_WRITING_PROMPTS)
        
        # Create writing prompt response
        writing_prompt = {
            "prompt_text": prompt_data["prompt"],
            "instructions": "Write a story based on the prompt. Use proper grammar, punctuation, and spelling. Your story should have a clear beginning, middle, and end.",
            "time_limit_minutes": 15,
            "visual_description": prompt_data.get("visual_description", ""),
            "grade_level": prompt_data.get("grade_level", "3-4"),
            "story_elements": prompt_data.get("story_elements", [])
        }
        
        return writing_prompt
    
    async def _generate_standalone_section(self, section_type: QuestionType, difficulty: DifficultyLevel, count: int, provider: Optional[Any]) -> StandaloneSection:
        """Generate a standalone section (math, verbal, analogy, synonym)."""
        # Create request for this section
        section_request = QuestionGenerationRequest(
            question_type=section_type,
            difficulty=difficulty,
            count=count,
            provider=provider
        )
        
        # Generate questions for this section
        section_result = await self.generate_questions(section_request)
        
        # Get section instructions and time limit
        instructions = self._get_section_instructions(section_type)
        time_limit = self._get_section_time_limit(section_type, count)
        
        return StandaloneSection(
            section_type=section_type.value,
            questions=section_result["questions"],
            time_limit_minutes=time_limit,
            instructions=instructions
        )
    
    async def _generate_reading_section(self, difficulty: DifficultyLevel, total_questions: int, provider: Optional[Any]) -> ReadingSection:
        """Generate a reading section with passages and questions."""
        # Calculate number of passages needed (4 questions per passage)
        num_passages = max(1, total_questions // 4)
        
        passages = []
        for i in range(num_passages):
            passage = await self._generate_reading_passage(difficulty, provider, i + 1)
            passages.append(passage)
        
        instructions = self._get_section_instructions(QuestionType.READING)
        time_limit = self._get_section_time_limit(QuestionType.READING, total_questions)
        
        return ReadingSection(
            section_type="reading",
            passages=passages,
            time_limit_minutes=time_limit,
            instructions=instructions
        )
    
    async def _generate_writing_section(self, difficulty: DifficultyLevel) -> WritingSection:
        """Generate a writing section with a prompt."""
        prompt_data = await self._generate_writing_prompt(difficulty)
        
        # Convert dict to WritingPrompt model
        writing_prompt = WritingPrompt(
            prompt_text=prompt_data["prompt_text"],
            instructions=prompt_data["instructions"],
            visual_description=prompt_data.get("visual_description"),
            grade_level=prompt_data.get("grade_level", "3-4"),
            story_elements=prompt_data.get("story_elements", []),
            prompt_type=prompt_data.get("prompt_type", "picture_story")
        )
        
        instructions = self._get_section_instructions(QuestionType.WRITING)
        time_limit = self._get_section_time_limit(QuestionType.WRITING, 1)
        
        return WritingSection(
            section_type="writing",
            prompt=writing_prompt,
            time_limit_minutes=time_limit,
            instructions=instructions
        )
    
    async def _generate_reading_passage(self, difficulty: DifficultyLevel, provider: Optional[Any], passage_number: int) -> ReadingPassage:
        """Generate a single reading passage with 4 questions."""
        import uuid
        from app.specifications import OFFICIAL_ELEMENTARY_SPECS
        import random
        
        # Select passage type and topic
        passage_types = OFFICIAL_ELEMENTARY_SPECS["reading_structure"]["passage_types"]
        passage_type = random.choice(passage_types)
        
        # Generate passage and questions using existing question generation
        section_request = QuestionGenerationRequest(
            question_type=QuestionType.READING,
            difficulty=difficulty,
            count=4,  # Always 4 questions per passage
            provider=provider
        )
        
        # For now, use existing generation but we'll need to enhance this to generate 
        # passage-based questions properly
        section_result = await self.generate_questions(section_request)
        
        # Extract passage text from first question (temporary - needs proper passage generation)
        first_question = section_result["questions"][0]
        passage_text = first_question.get("text", "Sample passage text would go here...")
        
        # Create passage ID and metadata
        passage_id = str(uuid.uuid4())
        
        return ReadingPassage(
            id=passage_id,
            title=f"Passage {passage_number}",
            text=passage_text,
            passage_type=passage_type,
            grade_level="3-4",
            topic=f"Elementary Reading - {passage_type}",
            questions=section_result["questions"],
            metadata={"passage_number": passage_number, "difficulty": difficulty.value}
        )