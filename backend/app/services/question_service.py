"""Service for question generation logic."""

import time
import uuid
from typing import List, Dict, Any, Optional, Union
from loguru import logger

# Import SSAT modules (now local)
from app.models import QuestionRequest
from app.models.enums import QuestionType, DifficultyLevel
from app.generator import generate_questions, generate_questions_async, SSATGenerator
from app.settings import settings
from app.models.requests import QuestionGenerationRequest, CompleteTestRequest
from app.models.responses import QuantitativeSection, SynonymSection, AnalogySection, ReadingSection, WritingSection, ReadingPassage, WritingPrompt

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
                question_type=QuestionType.QUANTITATIVE,
                difficulty=DifficultyLevel.MEDIUM,
                count=1
            )
            examples = self.generator.get_training_examples(test_request)
            return True  # If no exception, connection is healthy
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def _convert_to_ssat_request(self, request: QuestionGenerationRequest) -> QuestionRequest:
        """Convert API request to internal SSAT request format."""
        # Map API enums to internal enums (now using same enum directly)
        question_type_mapping = {
            QuestionType.QUANTITATIVE: QuestionType.QUANTITATIVE,
            QuestionType.READING: QuestionType.READING,
            QuestionType.VERBAL: QuestionType.VERBAL,
            QuestionType.ANALOGY: QuestionType.ANALOGY,
            QuestionType.SYNONYM: QuestionType.SYNONYM,
            QuestionType.WRITING: QuestionType.WRITING,
        }
        
        difficulty_mapping = {
            DifficultyLevel.EASY: DifficultyLevel.EASY,
            DifficultyLevel.MEDIUM: DifficultyLevel.MEDIUM,
            DifficultyLevel.HARD: DifficultyLevel.HARD,
        }
        
        return QuestionRequest(
            question_type=question_type_mapping[request.question_type],
            difficulty=difficulty_mapping[request.difficulty],
            topic=request.topic,
            count=request.count,
            level=request.level
        )
    
    async def generate_questions(self, request: QuestionGenerationRequest) -> Dict[str, Any]:
        """Generate questions based on the request (non-reading questions)."""
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
    
    

    
    def _get_section_instructions(self, section_type: QuestionType) -> str:
        """Get instructions for a specific test section."""
        instructions = {
            QuestionType.QUANTITATIVE: "Solve each problem and choose the best answer. You may use scratch paper for calculations.",
            QuestionType.VERBAL: "Choose the word that best completes each sentence or answers each question.",
            QuestionType.READING: "Read each passage carefully and answer the questions that follow.",
            QuestionType.WRITING: "Write a short essay in response to the prompt. Use proper grammar and organization.",
            QuestionType.ANALOGY: "Choose the pair of words that has the same relationship as the given pair.",
            QuestionType.SYNONYM: "Choose the word that means the same or nearly the same as the given word."
        }
        return instructions.get(section_type, "Answer all questions to the best of your ability.")
    

    
    async def get_topic_suggestions(self, question_type: str) -> List[str]:
        """Get suggested topics for a given question type."""
        # Define common topics for each question type
        topic_suggestions = {
            "quantitative": [
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
        """Generate a writing prompt using AI with real SSAT training examples."""
        from app.models import QuestionRequest
        from app.content_generators import generate_writing_prompts_with_metadata
        
        # Create request for AI generation (same as individual writing generation)
        ssat_request = QuestionRequest(
            question_type=QuestionType.WRITING,
            difficulty=DifficultyLevel.MEDIUM if difficulty == DifficultyLevel.MEDIUM else DifficultyLevel.EASY,
            topic=None,  # No specific topic for complete tests
            count=1      # Generate one prompt
        )
        
        try:
            # Use the same AI generation logic as individual writing generation
            generation_result = generate_writing_prompts_with_metadata(ssat_request, llm=None)
            
            if generation_result.content and len(generation_result.content) > 0:
                # Convert WritingPrompt object to dict format
                writing_prompt = generation_result.content[0]  # type: ignore[attr-defined]
                return {
                    "prompt_text": writing_prompt.prompt_text,  # type: ignore[attr-defined]
                    "instructions": writing_prompt.instructions,  # type: ignore[attr-defined]
                    "visual_description": writing_prompt.visual_description,  # type: ignore[attr-defined]
                    "grade_level": writing_prompt.grade_level,  # type: ignore[attr-defined]
    
                    "prompt_type": writing_prompt.prompt_type,  # type: ignore[attr-defined]
                    "subsection": writing_prompt.subsection,  # type: ignore[attr-defined]
                    "tags": writing_prompt.tags,  # type: ignore[attr-defined]
                    "training_examples_used": generation_result.training_example_ids,
                    "provider_used": generation_result.provider_used
                }
            else:
                raise ValueError("AI generation returned no writing prompts")
                
        except Exception as e:
            logger.warning(f"AI writing prompt generation failed: {e}, falling back to static prompts")
            
            # Fallback to static prompts if AI generation fails
            from app.specifications import ELEMENTARY_WRITING_PROMPTS
            import random
            
            prompt_data = random.choice(ELEMENTARY_WRITING_PROMPTS)
            return {
                "prompt_text": prompt_data["prompt"],
                "instructions": "Write a story based on the prompt. Use proper grammar, punctuation, and spelling. Your story should have a clear beginning, middle, and end.",
                "visual_description": prompt_data.get("visual_description", ""),
                "grade_level": prompt_data.get("grade_level", "3-4"),

                "training_examples_used": [],
                "provider_used": "static"
            }
    
    async def _generate_quantitative_section_official(self, difficulty: DifficultyLevel, total_count: int, provider: Optional[Any], use_async: bool = False) -> QuantitativeSection:
        """Generate quantitative section with official SSAT topic distribution."""
        import random
        from app.specifications import OFFICIAL_ELEMENTARY_SPECS
        
        logger.info(f"🎯 DEBUG: Starting OFFICIAL quantitative generation for {total_count} questions")
        
        # Official distribution for quantitative questions
        distribution = OFFICIAL_ELEMENTARY_SPECS["quantitative_distribution"]
        logger.info(f"📊 DEBUG: Official distribution: {distribution}")
        
        # Calculate question counts based on official distribution
        topics_counts = [
            ("number operations", int(total_count * distribution["number_operations"])),      # ~40%
            ("algebra functions", int(total_count * distribution["algebra_functions"])),      # ~20%
            ("geometry spatial", int(total_count * distribution["geometry_spatial"])),        # ~25%
            ("measurement", int(total_count * distribution["measurement"])),                  # ~10%
            ("probability data", int(total_count * distribution["probability_data"]))         # ~5%
        ]
        
        logger.info(f"📋 DEBUG: Initial topic counts: {topics_counts}")
        
        # Ensure we have the right number of questions
        total_allocated = sum(count for _, count in topics_counts)
        logger.info(f"📊 DEBUG: Total allocated: {total_allocated}, target: {total_count}")
        
        if total_allocated < total_count:
            # Add remaining questions to geometry (largest flexible category)
            topics_counts[2] = (topics_counts[2][0], topics_counts[2][1] + (total_count - total_allocated))
            logger.info(f"➕ DEBUG: Added {total_count - total_allocated} questions to geometry")
        elif total_allocated > total_count:
            # Remove from geometry if we have too many
            excess = total_allocated - total_count
            topics_counts[2] = (topics_counts[2][0], max(1, topics_counts[2][1] - excess))
            logger.info(f"➖ DEBUG: Removed {excess} questions from geometry")
        
        logger.info(f"📋 DEBUG: Final topic counts: {topics_counts}")
        
        # Generate questions by topic
        all_questions = []
        for topic, count in topics_counts:
            if count > 0:
                logger.info(f"🔧 DEBUG: Generating {count} questions for topic: {topic}")
                
                topic_request = QuestionGenerationRequest(
                    question_type=QuestionType.QUANTITATIVE,
                    difficulty=difficulty,
                    topic=topic,
                    count=count,
                    provider=provider,
                    is_official_format=True  # This is the official method, so always True
                )
                
                logger.info(f"✅ DEBUG: Created topic request with count={count}, is_official_format=True")
                
                if use_async:
                    # For progressive generation - use async LLM calls
                    logger.info(f"⚡ DEBUG: Using async generation for {topic}")
                    ssat_request = self._convert_to_ssat_request(topic_request)
                    provider_name = provider.value if provider else None
                    topic_questions = await generate_questions_async(ssat_request, llm=provider_name)
                else:
                    # For synchronous generation
                    logger.info(f"🔄 DEBUG: Using sync generation for {topic}")
                    topic_result = await self.generate_questions(topic_request)
                    topic_questions = topic_result["questions"]
                
                # Convert questions to API format
                for question in topic_questions:
                    if isinstance(question, dict):
                        # Already in API format
                        api_question = question
                    else:
                        # Convert from internal format
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
                    
                    all_questions.append(api_question)
        
        logger.info(f"📦 DEBUG: Generated {len(all_questions)} total questions")
        
        # Shuffle to mix topic types (like real SSAT)
        random.shuffle(all_questions)
        all_questions = all_questions[:total_count]  # Ensure exactly right count
        
        logger.info(f"🎲 DEBUG: Shuffled and trimmed to {len(all_questions)} questions")
        
        # Get section instructions
        instructions = self._get_section_instructions(QuestionType.QUANTITATIVE)
        
        logger.info(f"✅ DEBUG: OFFICIAL quantitative section complete with {len(all_questions)} questions")
        
        return QuantitativeSection(
            questions=all_questions,
            instructions=instructions
        )
    
    async def _generate_standalone_section(self, section_type: QuestionType, difficulty: DifficultyLevel, count: int, provider: Optional[Any], use_async: bool = False, is_official_format: bool = False) -> Union[QuantitativeSection, SynonymSection, AnalogySection]:
        """Generate a section for individual question types (quantitative, synonym, analogy)."""
        # Create request for this section
        section_request = QuestionGenerationRequest(
            question_type=section_type,
            difficulty=difficulty,
            count=count,
            provider=provider,
            is_official_format=is_official_format
        )
        
        if use_async:
            # For progressive generation - use async LLM calls
            ssat_request = self._convert_to_ssat_request(section_request)
            provider_name = provider.value if provider else None
            questions = await generate_questions_async(ssat_request, llm=provider_name)
            
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
        else:
            # For synchronous generation - use existing method
            section_result = await self.generate_questions(section_request)
            api_questions = section_result["questions"]
        
        # Get section instructions
        instructions = self._get_section_instructions(section_type)
        
        # Route to appropriate section type based on question type
        if section_type == QuestionType.QUANTITATIVE:
            return QuantitativeSection(
                questions=api_questions,
                instructions=instructions
            )
        elif section_type == QuestionType.SYNONYM:
            return SynonymSection(
                questions=api_questions,
                instructions=instructions
            )
        elif section_type == QuestionType.ANALOGY:
            return AnalogySection(
                questions=api_questions,
                instructions=instructions
            )
        else:
            raise ValueError(f"Unsupported section type for standalone generation: {section_type}")
    
    async def _generate_reading_section(self, difficulty: DifficultyLevel, num_passages: int, provider: Optional[Any], use_async: bool = False) -> ReadingSection:
        """Generate a reading section with passages and questions."""
        # num_passages is now the direct input (no calculation needed)
        
        # Get training examples metadata first
        from app.generator import SSATGenerator
        generator = SSATGenerator()
        training_examples = generator.get_reading_training_examples()
        training_example_ids = [ex.get('question_id', '') for ex in training_examples if ex.get('question_id')]
        
        logger.info(f"📚 DEBUG: Reading section will use {len(training_example_ids)} training examples: {training_example_ids}")
        
        passages = []
        for i in range(num_passages):
            passage = await self._generate_reading_passage(difficulty, provider, i + 1, use_async)
            # Add training examples metadata to the passage
            passage.metadata["training_examples_used"] = training_example_ids
            passages.append(passage)
        
        instructions = self._get_section_instructions(QuestionType.READING)
        
        return ReadingSection(
            section_type=QuestionType.READING,
            passages=passages,
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
            prompt_type=prompt_data.get("prompt_type", "picture_story"),
            tags=prompt_data.get("tags", []),
            metadata={
                "training_examples_used": prompt_data.get("training_examples_used", []),
                "provider_used": prompt_data.get("provider_used", "unknown")
            }
        )
        
        instructions = self._get_section_instructions(QuestionType.WRITING)
        
        return WritingSection(
            section_type=QuestionType.WRITING,
            prompt=writing_prompt,
            instructions=instructions
        )
    
    async def _generate_reading_passage(self, difficulty: DifficultyLevel, provider: Optional[Any], passage_number: int, use_async: bool = False) -> ReadingPassage:
        """Generate a single reading passage with 4 questions."""
        import uuid
        from app.specifications import OFFICIAL_ELEMENTARY_SPECS
        import random
        
        # Select passage type and topic
        passage_types = OFFICIAL_ELEMENTARY_SPECS["reading_structure"]["passage_types"]
        passage_type = random.choice(passage_types)
        
        # Generate passage and questions
        section_request = QuestionGenerationRequest(
            question_type=QuestionType.READING,
            difficulty=difficulty,
            count=4,  # Always 4 questions per passage
            provider=provider
        )
        
        # Generate reading passage using dedicated function
        ssat_request = self._convert_to_ssat_request(section_request)
        provider_name = provider.value if provider else None
        
        if use_async:
            # For progressive generation - use async LLM calls
            from app.generator import generate_reading_passage_async
            passage_result = await generate_reading_passage_async(ssat_request, llm=provider_name)
        else:
            # For synchronous generation
            from app.generator import generate_reading_passage
            passage_result = generate_reading_passage(ssat_request, llm=provider_name)
        
        # Extract passage data and questions from result
        passage_data = passage_result["passage"]
        questions = passage_result["questions"]
        
        # Convert questions to API format
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
            
            if question.visual_description and question.visual_description.strip() and \
               question.visual_description.lower() not in ["none", "no visual elements", "no visual elements required"]:
                api_question["visual_description"] = question.visual_description
            api_questions.append(api_question)
        
        # Use passage text from the dedicated passage data
        passage_text = passage_data.get("text", "Sample passage text")
        
        # Create passage ID and metadata
        passage_id = str(uuid.uuid4())
        
        return ReadingPassage(
            id=passage_id,
            title=passage_data.get("title") or f"Passage {passage_number}",
            text=passage_text,
            passage_type=passage_data.get("passage_type", passage_type),
            grade_level=passage_data.get("grade_level", "3-4"),
            topic=passage_data.get("topic", f"Elementary Reading - {passage_type}"),
            questions=api_questions,
            metadata={"passage_number": passage_number, "difficulty": difficulty.value}
        )
