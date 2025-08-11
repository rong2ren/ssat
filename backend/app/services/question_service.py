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
            logger.error(f"AI writing prompt generation failed: {e}")
            raise ValueError(f"Failed to generate writing prompt: {e}")
    
    async def _generate_quantitative_section_official(self, difficulty: DifficultyLevel, total_count: int, provider: Optional[Any], use_async: bool = False) -> QuantitativeSection:
        """Generate quantitative section with simplified subsection-based distribution."""
        import random
        from app.specifications import QUANTITATIVE_SUBSECTIONS
        
        logger.info(f"🎯 DEBUG: Starting OFFICIAL quantitative generation for {total_count} questions")
        
        # Simplified subsection distribution based on official SSAT breakdown
        # Number Operations (40%): Fractions, Arithmetic, Number Sense, Decimals, Percentages
        # Algebra Functions (20%): Algebra, Variables, Patterns, Sequences  
        # Geometry Spatial (25%): Area, Perimeter, Shapes, Spatial
        # Measurement (10%): Measurement, Time, Money
        # Probability Data (5%): Probability, Data, Graphs
        
        # Calculate percentages and use better rounding
        percentages = [
            ("Fractions", 0.15),      # 15% - most common
            ("Arithmetic", 0.12),     # 12%
            ("Number Sense", 0.08),   # 8%
            ("Decimals", 0.03),       # 3%
            ("Percentages", 0.02),    # 2%
            ("Algebra", 0.08),        # 8%
            ("Variables", 0.05),      # 5%
            ("Patterns", 0.04),       # 4%
            ("Sequences", 0.03),      # 3%
            ("Area", 0.08),           # 8%
            ("Perimeter", 0.06),      # 6%
            ("Shapes", 0.06),         # 6%
            ("Spatial", 0.05),        # 5%
            ("Measurement", 0.04),    # 4%
            ("Time", 0.03),           # 3%
            ("Money", 0.03),          # 3%
            ("Probability", 0.02),    # 2%
            ("Data", 0.02),           # 2%
            ("Graphs", 0.01)          # 1%
        ]
        
        # Use better rounding to minimize shortfall
        subsections_distribution = []
        total_allocated = 0
        
        for i, (subsection, percentage) in enumerate(percentages):
            if i == len(percentages) - 1:
                # For the last item, use remaining count to ensure exact total
                count = max(0, total_count - total_allocated)  # Ensure non-negative
            else:
                # Use round() instead of int() for better distribution
                count = round(total_count * percentage)
                total_allocated += count
            
            subsections_distribution.append((subsection, count))
        
        # Ensure we have exactly the target count
        actual_total = sum(count for _, count in subsections_distribution)
        if actual_total != total_count:
            # Adjust the first non-zero count to match target
            for i, (subsection, count) in enumerate(subsections_distribution):
                if count > 0:
                    subsections_distribution[i] = (subsection, count + (total_count - actual_total))
                    break
        
        logger.info(f"📋 DEBUG: Subsection distribution: {subsections_distribution}")
        logger.info(f"📊 DEBUG: Total allocated: {sum(count for _, count in subsections_distribution)}, target: {total_count}")
        
        # Generate all questions in a single LLM call for efficiency
        logger.info(f"🔧 DEBUG: Generating {total_count} questions in single LLM call")
        
        # Create a single request for all questions
        all_questions_request = QuestionGenerationRequest(
            question_type=QuestionType.QUANTITATIVE,
            difficulty=difficulty,
            count=total_count,  # Generate all questions at once
            provider=provider,
            is_official_format=True,
            topic=""  # Empty topic means generate across all subsections
        )
        
        logger.info(f"✅ DEBUG: Created single request with count={total_count}, is_official_format=True")
        
        if use_async:
            # Single async LLM call for all questions
            logger.info(f"⚡ DEBUG: Using single async generation for all {total_count} questions")
            ssat_request = self._convert_to_ssat_request(all_questions_request)
            provider_name = provider.value if provider else None
            all_questions = await generate_questions_async(ssat_request, llm=provider_name)
        else:
            # Single sync LLM call for all questions
            logger.info(f"🔄 DEBUG: Using single sync generation for all {total_count} questions")
            all_questions_result = await self.generate_questions(all_questions_request)
            all_questions = all_questions_result["questions"]
        
        # Convert questions to API format
        api_questions = []
        for question in all_questions:
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
            
            api_questions.append(api_question)
        
        logger.info(f"📦 DEBUG: Generated {len(api_questions)} total questions")
        
        # Shuffle to mix topic types (like real SSAT)
        random.shuffle(api_questions)
        api_questions = api_questions[:total_count]  # Ensure exactly right count
        
        logger.info(f"🎲 DEBUG: Shuffled and trimmed to {len(api_questions)} questions")
        
        # Get section instructions
        instructions = self._get_section_instructions(QuestionType.QUANTITATIVE)
        
        logger.info(f"✅ DEBUG: OFFICIAL quantitative section complete with {len(api_questions)} questions")
        
        return QuantitativeSection(
            questions=api_questions,
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
    
    async def _generate_reading_section(self, difficulty: DifficultyLevel, num_passages: int, provider: Optional[Any], use_async: bool = False, is_official_format: bool = False, topic: Optional[str] = None) -> ReadingSection:
        """Generate a reading section with passages and questions."""
        # num_passages is now the direct input (no calculation needed)
        
        # Get training examples metadata first
        from app.generator import SSATGenerator
        generator = SSATGenerator()
        training_examples = generator.get_reading_training_examples(topic=topic)
        training_example_ids = [ex.get('question_id', '') for ex in training_examples if ex.get('question_id')]
        
        logger.info(f"📚 DEBUG: Reading section will use {len(training_example_ids)} training examples: {training_example_ids}")
        
        # Create request for all passages at once
        section_request = QuestionGenerationRequest(
            question_type=QuestionType.READING,
            difficulty=difficulty,
            count=num_passages,  # Generate all passages in one call
            provider=provider,
            is_official_format=is_official_format,
            topic=topic
        )
        
        # Convert to SSAT request format
        ssat_request = self._convert_to_ssat_request(section_request)
        provider_name = provider.value if provider else None
        
        # Generate all passages using unified function
        from app.generator import generate_reading_passages_async
        # Use multiple calls for full test generation (quality over efficiency)
        use_single_call = False
        # Pass pre-fetched training examples to avoid double fetching
        results = await generate_reading_passages_async(ssat_request, llm=provider_name, use_single_call=use_single_call, training_examples=training_examples)
        
        # Convert results to ReadingPassage objects
        passages = []
        for i, result in enumerate(results):
            passage_data = result["passage"]
            questions = result["questions"]
            
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
            
            # Create ReadingPassage object
            import uuid
            from app.specifications import OFFICIAL_ELEMENTARY_SPECS
            import random
            
            # Select passage type and topic
            passage_types = OFFICIAL_ELEMENTARY_SPECS["reading_structure"]["passage_types"]
            passage_type = random.choice(passage_types)
            
            passage_id = str(uuid.uuid4())
            passage = ReadingPassage(
                id=passage_id,
                title=f"Passage {i+1}",
                text=passage_data,
                passage_type=result.get("passage_type", passage_type),
                grade_level="3-4",
                topic=f"Elementary Reading - {passage_type}",
                questions=api_questions,
                metadata={
                    "passage_number": i+1, 
                    "difficulty": difficulty.value,
                    "training_examples_used": training_example_ids
                }
            )
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
