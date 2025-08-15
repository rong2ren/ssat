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
            level=request.level,
            is_official_format=getattr(request, 'is_official_format', False)
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
            difficulty=difficulty,  # Use the provided difficulty for admin generation
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
    
    async def _generate_quantitative_section_official_5_calls(self, difficulty: DifficultyLevel, total_count: int, provider: Optional[Any], use_async: bool = False) -> QuantitativeSection:
        """Generate quantitative section using 5 parallel calls for token efficiency - ADMIN COMPLETE TEST ONLY."""
        import random
        import asyncio
        from app.specifications import QUANTITATIVE_SUBSECTIONS
        
        logger.info(f"🎯 ADMIN 5-CALL: Starting OFFICIAL quantitative generation for {total_count} questions using 5 parallel calls")
        
        # Define the 5 domain groups using ACTUAL database subsections
        domain_groups = [
            {
                "group_name": "Number Operations",
                "question_count": 12,
                "subsections": {
                    "Number Properties": 3,    # 32 available - number relationships, place value
                    "Fractions": 3,           # 21 available - fraction operations  
                    "Arithmetic": 3,          # 18 available - basic operations
                    "Word Problems": 2,       # 16 available - problem solving contexts
                    "Decimals": 1             # 2 available - decimal operations
                },
                "mathematical_focus": "Number properties, fractions, arithmetic operations, decimals"
            },
            {
                "group_name": "Algebra & Functions", 
                "question_count": 6,
                "subsections": {
                    "Algebra": 4,             # 16 available - equations, expressions
                    "Number Sequences": 2     # 2 available - patterns and sequences
                },
                "mathematical_focus": "Algebraic expressions, equations, number patterns, sequences"
            },
            {
                "group_name": "Geometry & Spatial",
                "question_count": 7, 
                "subsections": {
                    "Geometry": 7             # 25 available - shapes, area, perimeter, angles, spatial reasoning
                },
                "mathematical_focus": "Geometric shapes, area, perimeter, angles, spatial reasoning"
            },
            {
                "group_name": "Measurement", 
                "question_count": 3,
                "subsections": {
                    "Measurement": 2,         # 10 available - units, conversions
                    "Money": 1                # 4 available - money calculations
                },
                "mathematical_focus": "Units of measurement, conversions, money problems"
            },
            {
                "group_name": "Data & Probability",
                "question_count": 2,
                "subsections": {
                    "Data Interpretation": 1,  # 9 available - reading graphs, tables
                    "Probability": 1          # 1 available - basic probability
                },
                "mathematical_focus": "Data interpretation, probability concepts"
            }
        ]
        
        # Verify total count
        total_questions_check = sum(group["question_count"] for group in domain_groups)
        if total_questions_check != total_count:
            logger.warning(f"🎯 ADMIN 5-CALL: Domain groups total {total_questions_check} != requested {total_count}")
        
        logger.info(f"🎯 ADMIN 5-CALL: Generating {len(domain_groups)} domain groups in parallel")
        
        # Create 5 parallel LLM calls
        call_tasks = []
        for i, group in enumerate(domain_groups):
            logger.info(f"🎯 ADMIN 5-CALL: Group {i+1}: {group['group_name']} ({group['question_count']} questions)")
            task = asyncio.create_task(
                self._generate_domain_group(group, difficulty, provider, use_async)
            )
            call_tasks.append(task)
        
        # Execute all calls in parallel
        logger.info(f"🎯 ADMIN 5-CALL: Executing {len(call_tasks)} parallel LLM calls")
        results = await asyncio.gather(*call_tasks, return_exceptions=True)
        
        # Combine results and handle errors
        all_questions = []
        successful_groups = 0
        for i, result in enumerate(results):
            group_name = domain_groups[i]["group_name"]
            if isinstance(result, Exception):
                logger.error(f"🎯 ADMIN 5-CALL: Group {group_name} failed: {result}")
            elif isinstance(result, list):
                all_questions.extend(result)
                successful_groups += 1
                logger.info(f"🎯 ADMIN 5-CALL: Group {group_name} completed: {len(result)} questions")
            else:
                logger.warning(f"🎯 ADMIN 5-CALL: Group {group_name} returned unexpected format: {type(result)}")
        
        logger.info(f"🎯 ADMIN 5-CALL: Completed {successful_groups}/{len(domain_groups)} groups, total questions: {len(all_questions)}")
        
        # Validate subsection distribution
        subsection_counts = {}
        for question in all_questions:
            if hasattr(question, 'subsection') and question.subsection:
                subsection = question.subsection
                subsection_counts[subsection] = subsection_counts.get(subsection, 0) + 1
        
        logger.info(f"🎯 ADMIN 5-CALL: Actual subsection distribution: {subsection_counts}")
        
        # Convert to API format if needed
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
                    "subsection": question.subsection,  # Include subsection in API format for 5-call strategy
                    "cognitive_level": question.cognitive_level,
                    "tags": question.tags,
                    "metadata": question.metadata
                }
                
                # Only include visual_description if it has meaningful content
                if question.visual_description and question.visual_description.strip() and \
                   question.visual_description.lower() not in ["none", "no visual elements", "no visual elements required"]:
                    api_question["visual_description"] = question.visual_description
            
            api_questions.append(api_question)
        
        # Shuffle to mix topic types (like real SSAT) and ensure exact count
        random.shuffle(api_questions)
        api_questions = api_questions[:total_count]  # Ensure exactly right count
        
        logger.info(f"🎯 ADMIN 5-CALL: Final result: {len(api_questions)} questions, shuffled and trimmed")
        
        # Get section instructions
        instructions = self._get_section_instructions(QuestionType.QUANTITATIVE)
        
        return QuantitativeSection(
            questions=api_questions,
            instructions=instructions
        )
    
    async def _generate_domain_group(self, group: dict, difficulty: DifficultyLevel, provider: Optional[Any], use_async: bool) -> List[Any]:
        """Generate questions for a specific mathematical domain group."""
        try:
            group_name = group["group_name"]
            question_count = group["question_count"]
            subsections = group["subsections"]
            
            logger.info(f"🔧 ADMIN 5-CALL: Generating {group_name} ({question_count} questions)")
            logger.info(f"🔧 ADMIN 5-CALL: Required subsections: {subsections}")
            
            # Create specialized request for this domain
            domain_request = QuestionGenerationRequest(
                question_type=QuestionType.QUANTITATIVE,
                difficulty=difficulty,
                count=question_count,
                provider=provider,
                is_official_format=True,
                topic=""  # Empty topic - we'll use specialized prompts instead
            )
            
            # Convert to SSAT request for direct LLM call with specialized prompt
            ssat_request = self._convert_to_ssat_request(domain_request)
            
            # Define training example counts per subsection (optimized for each domain)
            training_examples_map = self._get_domain_training_examples_map(group_name, subsections)
            
            # Get subsection-specific training examples for this domain
            training_examples = self.get_domain_training_examples(
                training_examples_map, 
                difficulty.value
            )
            
            # Build specialized prompt for this domain group
            specialized_prompt = self._build_domain_specific_prompt(
                ssat_request, group, training_examples
            )
            
            # Generate questions using specialized prompt
            if use_async:
                from app.generator import generate_questions_async
                # Override the normal prompt with our specialized one
                provider_name = provider.value if provider else None
                
                # Make direct LLM call with specialized prompt
                from app.generator import _select_llm_provider
                from app.llm import llm_client  # Correct import - llm_client is the global instance
                
                llm_provider = _select_llm_provider(provider_name)
                
                # Calculate appropriate max_tokens for this domain
                estimated_tokens_per_question = 300
                base_tokens = 1000
                required_tokens = base_tokens + (question_count * estimated_tokens_per_question)
                max_tokens = min(required_tokens, 6000)  # Conservative limit per domain
                
                logger.info(f"🔧 ADMIN 5-CALL: Using max_tokens={max_tokens} for {question_count} questions")
                
                # Call LLM with specialized prompt (higher temperature for more creative scenarios)
                content = await llm_client.call_llm_async(
                    provider=llm_provider,
                    system_message=specialized_prompt,
                    prompt="Generate the questions as specified with correct subsections.",
                    max_tokens=max_tokens,
                    temperature=0.9  # Increased creativity for more diverse problem scenarios
                )
                
                if content is None:
                    raise ValueError(f"LLM call failed for domain {group_name}")
                
                # Parse the LLM response
                from app.generator import extract_json_from_text
                data = extract_json_from_text(content)
                
                if data is None:
                    raise ValueError(f"Failed to extract JSON from LLM response for domain {group_name}")
                
                # Parse questions and validate subsections
                questions = []
                from app.models.base import Question, Option
                
                for q_data in data.get("questions", []):
                    # Validate that subsection is one of the expected ones for this domain
                    question_subsection = q_data.get("subsection")
                    if question_subsection not in subsections:
                        logger.warning(f"🔧 ADMIN 5-CALL: Question has invalid subsection '{question_subsection}', expected one of {list(subsections.keys())}")
                        # Use the first subsection as fallback
                        question_subsection = list(subsections.keys())[0]
                    
                    options = [Option(letter=opt["letter"], text=opt["text"]) for opt in q_data["options"]]
                    cognitive_level = q_data.get("cognitive_level", "UNDERSTAND").upper()
                    
                    question = Question(
                        question_type=QuestionType.QUANTITATIVE,
                        difficulty=difficulty,
                        text=q_data["text"],
                        options=options,
                        correct_answer=q_data["correct_answer"],
                        explanation=q_data["explanation"],
                        cognitive_level=cognitive_level,
                        tags=q_data.get("tags", []),
                        visual_description=q_data.get("visual_description"),
                        subsection=question_subsection  # Ensure correct subsection
                    )
                    questions.append(question)
                
                # Validate we got the right number of questions
                if len(questions) != question_count:
                    logger.warning(f"🔧 ADMIN 5-CALL: {group_name} generated {len(questions)} questions, expected {question_count}")
                
                # Log subsection distribution for this domain
                domain_subsection_counts = {}
                for question in questions:
                    subsection = question.subsection
                    domain_subsection_counts[subsection] = domain_subsection_counts.get(subsection, 0) + 1
                
                logger.info(f"🔧 ADMIN 5-CALL: {group_name} subsection distribution: {domain_subsection_counts}")
                
                return questions
            else:
                # Fallback to sync generation (shouldn't be used but kept for safety)
                generation_result = await self.generate_questions(domain_request)
                questions = generation_result["questions"]
                logger.info(f"🔧 ADMIN 5-CALL: {group_name} generated {len(questions)} questions (sync)")
                return questions
                
        except Exception as e:
            logger.error(f"🔧 ADMIN 5-CALL: Failed to generate {group.get('group_name', 'unknown')} group: {e}")
            return []
    
    def _build_domain_specific_prompt(self, request, group: dict, training_examples: List[Dict[str, Any]]) -> str:
        """Build a specialized prompt for a specific mathematical domain group."""
        group_name = group["group_name"]
        
        # Route to specialized prompt builder based on domain
        if group_name == "Number Operations":
            return self._build_number_operations_prompt(request, group, training_examples)
        elif group_name == "Algebra & Functions":
            return self._build_algebra_functions_prompt(request, group, training_examples)
        elif group_name == "Geometry & Spatial":
            return self._build_geometry_spatial_prompt(request, group, training_examples)
        elif group_name == "Measurement":
            return self._build_measurement_prompt(request, group, training_examples)
        elif group_name == "Data & Probability":
            return self._build_data_probability_prompt(request, group, training_examples)
        else:
            # Fallback to generic prompt
            return self._build_generic_domain_prompt(request, group, training_examples)
    
    def _build_number_operations_prompt(self, request, group: dict, training_examples: List[Dict[str, Any]]) -> str:
        """Specialized prompt for Number Operations domain."""
        subsections = group["subsections"]
        question_count = group["question_count"]
        
        # Build subsection requirements
        subsection_requirements = []
        for subsection, count in subsections.items():
            subsection_requirements.append(f"- {subsection}: exactly {count} question{'s' if count != 1 else ''}")
        subsection_text = "\n".join(subsection_requirements)
        
        # Add training examples
        examples_text = self._build_training_examples_text(training_examples, max_examples=3)
        
        return f"""You are an expert SSAT Elementary quantitative question generator specializing in NUMBER OPERATIONS.

Generate {question_count} NEW questions focused on fundamental number operations and concepts.

{self._get_difficulty_specific_instructions(request.difficulty.value)}

{examples_text}

SUBSECTION REQUIREMENTS:
{subsection_text}

NUMBER OPERATIONS FOCUS:
- **Number Properties**: Place value, number relationships, ordering, rounding, prime/composite, divisibility
- **Fractions**: Operations, equivalents, mixed numbers, comparisons, decimal conversions  
- **Arithmetic**: Multi-step calculations (3-5 digits), order of operations, estimation, mental math
- **Word Problems**: Multi-step real-world problems requiring mathematical reasoning
- **Decimals**: Operations with multiple places, conversions, comparisons, patterns

AVOID TOO-EASY EXAMPLES:
❌ Basic division: "If a train travels 300 miles in 5 hours, what is its average speed?" 
❌ Simple division: "A bookstore has 1,248 books to arrange equally on 24 shelves. How many books per shelf?"

APPROPRIATE COMPLEXITY FOR MEDIUM DIFFICULTY:
✅ Multi-concept: "A rectangular swimming pool is 3 times as long as it is wide. If the perimeter is 96 feet and the depth is 4 feet, how many cubic feet of water can it hold?"
✅ Strategic reasoning: "Sarah saves $15 each week. After 8 weeks, she spends 2/5 of her savings on a gift and then saves for 6 more weeks. If she needs $180 total, how much more does she need?"

{self._get_shared_critical_requirements(subsections, request.difficulty.value)}

{self._get_shared_output_format()}"""

    def _build_algebra_functions_prompt(self, request, group: dict, training_examples: List[Dict[str, Any]]) -> str:
        """Specialized prompt for Algebra & Functions domain."""
        subsections = group["subsections"]
        question_count = group["question_count"]
        
        subsection_requirements = []
        for subsection, count in subsections.items():
            subsection_requirements.append(f"- {subsection}: exactly {count} question{'s' if count != 1 else ''}")
        subsection_text = "\n".join(subsection_requirements)
        
        examples_text = self._build_training_examples_text(training_examples, max_examples=3)
        
        return f"""You are an expert SSAT Elementary quantitative question generator specializing in ALGEBRA & FUNCTIONS.

Generate {question_count} NEW questions focused on algebraic thinking and functional relationships.

{self._get_difficulty_specific_instructions(request.difficulty.value)}

{examples_text}

SUBSECTION REQUIREMENTS:
{subsection_text}

ALGEBRA & FUNCTIONS FOCUS:
- **Algebra**: Multi-step equations, complex substitution, algebraic expressions, variable problem-solving
- **Number Sequences**: Complex patterns, algebraic sequence rules, pattern recognition with variables

AVOID TOO-EASY EXAMPLES:
❌ "If x = 5, what is x + 3?" ❌ "What comes next: 2, 4, 6, 8, ___?"

APPROPRIATE COMPLEXITY FOR MEDIUM DIFFICULTY:
✅ "If 2(x + 3) - 5 = 3x - 7, and y = x + 4, what is the value of y?"
✅ "In a sequence, the first term is 5 and each term after is 3 more than twice the previous term. What is the 4th term?"

{self._get_shared_critical_requirements(subsections, request.difficulty.value)}

{self._get_shared_output_format()}"""

    def _build_geometry_spatial_prompt(self, request, group: dict, training_examples: List[Dict[str, Any]]) -> str:
        """Specialized prompt for Geometry & Spatial domain."""
        subsections = group["subsections"]
        question_count = group["question_count"]
        
        subsection_requirements = []
        for subsection, count in subsections.items():
            subsection_requirements.append(f"- {subsection}: exactly {count} question{'s' if count != 1 else ''}")
        subsection_text = "\n".join(subsection_requirements)
        
        examples_text = self._build_training_examples_text(training_examples, max_examples=3)
        
        return f"""You are an expert SSAT Elementary quantitative question generator specializing in GEOMETRY & SPATIAL REASONING.

Generate {question_count} NEW questions focused on geometric concepts and spatial thinking.

{self._get_difficulty_specific_instructions(request.difficulty.value)}

{examples_text}

SUBSECTION REQUIREMENTS:
{subsection_text}

GEOMETRY & SPATIAL FOCUS:
- **Geometry**: Multi-step area/perimeter, composite shapes, angle relationships, coordinate geometry, transformations

AVOID TOO-EASY EXAMPLES:
❌ "A rectangle has length 8 units and width 3 units. What is the perimeter?" ❌ "What is the area of a square with side 5?"

APPROPRIATE COMPLEXITY FOR MEDIUM DIFFICULTY:
✅ "A parallelogram has sides of 8 cm and 12 cm with a height of 6 cm to the 12 cm base. If a similar parallelogram has a 9 cm height to the longer base, what is its area?"
✅ "A right triangle has legs in the ratio 3:4. If the hypotenuse is 15 units, what is the area of the triangle?"

{self._get_shared_critical_requirements(subsections, request.difficulty.value)}

{self._get_shared_output_format()}"""

    def _build_measurement_prompt(self, request, group: dict, training_examples: List[Dict[str, Any]]) -> str:
        """Specialized prompt for Measurement domain."""
        subsections = group["subsections"]
        question_count = group["question_count"]
        
        subsection_requirements = []
        for subsection, count in subsections.items():
            subsection_requirements.append(f"- {subsection}: exactly {count} question{'s' if count != 1 else ''}")
        subsection_text = "\n".join(subsection_requirements)
        
        examples_text = self._build_training_examples_text(training_examples, max_examples=3)
        
        return f"""You are an expert SSAT Elementary quantitative question generator specializing in MEASUREMENT.

Generate {question_count} NEW questions focused on measurement concepts and unit conversions.

{self._get_difficulty_specific_instructions(request.difficulty.value)}

{examples_text}

SUBSECTION REQUIREMENTS:
{subsection_text}

MEASUREMENT FOCUS:
- **Measurement**: Complex unit conversions across systems, multi-step problems, precision and estimation
- **Money**: Multi-step financial calculations, percentage discounts, tax calculations, unit rate comparisons

AVOID TOO-EASY EXAMPLES:
❌ "How many inches are in 2 feet?" ❌ "What is the cost of 3 apples at $0.50 each?"

APPROPRIATE COMPLEXITY FOR MEDIUM DIFFICULTY:
✅ "A rectangular room is 18 feet by 12 feet. If carpet costs $3.75 per square foot and installation is $2.50 per square foot, what is the total cost including 7% tax?"
✅ "A water tank holds 450 gallons. If it drains at 2.5 gallons per minute and is refilled at 1.8 gallons per minute, how long until it's empty?"

{self._get_shared_critical_requirements(subsections, request.difficulty.value)}

{self._get_shared_output_format()}"""

    def _build_data_probability_prompt(self, request, group: dict, training_examples: List[Dict[str, Any]]) -> str:
        """Specialized prompt for Data & Probability domain."""
        subsections = group["subsections"]
        question_count = group["question_count"]
        
        subsection_requirements = []
        for subsection, count in subsections.items():
            subsection_requirements.append(f"- {subsection}: exactly {count} question{'s' if count != 1 else ''}")
        subsection_text = "\n".join(subsection_requirements)
        
        examples_text = self._build_training_examples_text(training_examples, max_examples=2)
        
        return f"""You are an expert SSAT Elementary quantitative question generator specializing in DATA ANALYSIS & PROBABILITY.

Generate {question_count} NEW questions focused on interpreting data and basic probability concepts.

{self._get_difficulty_specific_instructions(request.difficulty.value)}

{examples_text}

SUBSECTION REQUIREMENTS:
{subsection_text}

DATA & PROBABILITY FOCUS:
- **Data Interpretation**: Multi-step analysis of graphs, interpreting trends, comparing data sets, derived statistics
- **Probability**: Compound probability, conditional probability, multiple events, theoretical vs. experimental

AVOID TOO-EASY EXAMPLES:
❌ "What is the probability of getting heads on a coin flip?" ❌ "How many students chose vanilla ice cream?"

APPROPRIATE COMPLEXITY:
✅ "A bag contains 12 red, 8 blue, and 4 green marbles. If you draw 2 marbles without replacement, what is the probability both are red?"
✅ "A survey of 240 students shows: 60% like math, 45% like science, and 25% like both. How many students like neither subject?"

{self._get_shared_critical_requirements(subsections, request.difficulty.value)}

{self._get_shared_output_format()}"""

    def _build_training_examples_text(self, training_examples: List[Dict[str, Any]], max_examples: int = 3) -> str:
        """Helper to build training examples text for prompts."""
        examples_text = ""
        valid_examples = 0
        
        for i, example in enumerate(training_examples[:max_examples], 1):
            if example.get('answer') is None:
                continue
                
            valid_examples += 1
            example_text = f"""
REAL SSAT EXAMPLE {valid_examples}:
Question: {example['question']}
Choices: {example['choices']}
Correct Answer: {chr(65 + example['answer'])}
Explanation: {example['explanation']}
Difficulty: {example['difficulty']}
Subsection: {example['subsection']}

"""
            examples_text += example_text
        
        return examples_text if examples_text else "No training examples available for this domain."
    
    def _build_generic_domain_prompt(self, request, group: dict, training_examples: List[Dict[str, Any]]) -> str:
        """Fallback generic prompt for unknown domains."""
        subsections = group["subsections"]
        question_count = group["question_count"]
        mathematical_focus = group["mathematical_focus"]
        
        # Build subsection requirements text
        subsection_requirements = []
        for subsection, count in subsections.items():
            subsection_requirements.append(f"- {subsection}: exactly {count} question{'s' if count != 1 else ''}")
        
        subsection_text = "\n".join(subsection_requirements)
        examples_text = self._build_training_examples_text(training_examples, max_examples=3)
        
        return f"""You are an expert SSAT quantitative question generator.

Generate {question_count} NEW quantitative questions focused on {mathematical_focus}.

{self._get_difficulty_specific_instructions(request.difficulty.value)}

{examples_text}

CRITICAL SUBSECTION REQUIREMENTS:
You must generate questions with these EXACT subsections and counts:
{subsection_text}

{self._get_shared_critical_requirements(subsections, request.difficulty.value)}

OUTPUT FORMAT - Return ONLY a JSON object:
{{
  "questions": [
    {{
      "text": "Question text here",
      "options": [
        {{"letter": "A", "text": "Option A"}},
        {{"letter": "B", "text": "Option B"}},
        {{"letter": "C", "text": "Option C"}},
        {{"letter": "D", "text": "Option D"}}
      ],
      "correct_answer": "A",
      "explanation": "Detailed step-by-step explanation",
      "subsection": "SubsectionName",
      "tags": ["relevant-tags"],
      "cognitive_level": "APPLY"
    }}
  ]
}}

REMEMBER: Use the EXACT subsection names listed above and generate the EXACT number of questions for each subsection as specified."""
    
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
        # For admin complete tests (is_official_format), use diverse examples; otherwise use pre-fetched
        if is_official_format:
            # Admin complete test: Don't pass pre-fetched examples to ensure diverse content
            results = await generate_reading_passages_async(ssat_request, llm=provider_name, use_single_call=use_single_call, training_examples=None)
        else:
            # Regular generation: Use pre-fetched examples for consistency
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
    
    def _get_complexity_guidelines(self, difficulty: str, question_type: str) -> str:
        """Get complexity guidelines specific to question type and difficulty."""
        
        guidelines = {
            "quantitative": {
                "Easy": "- Multi-step calculations (2-3 steps), moderate arithmetic, complex word problems, basic algebra concepts, fractions and decimals, basic geometry",
                "Medium": "- Multi-step problems (3-4 steps), complex word problems, advanced geometry, algebra with variables, percentages and ratios, patterns and sequences, probability concepts",
                "Hard": "- Highly complex multi-step problems (4+ steps), advanced word problems, abstract concepts, advanced algebra, complex geometry, probability and statistics, data analysis, mathematical reasoning, multiple concept integration"
            }
        }
        
        return guidelines.get(question_type, {}).get(difficulty, "- Use appropriate complexity for the specified difficulty level")
    
    def _get_cognitive_level_by_difficulty(self, difficulty: str) -> str:
        """Get the required cognitive level for a given difficulty."""
        cognitive_mapping = {
            "Easy": "APPLY",
            "Medium": "ANALYZE", 
            "Hard": "EVALUATE"
        }
        
        return cognitive_mapping.get(difficulty, "APPLY")
    
    def _get_domain_training_examples_map(self, group_name: str, subsections: dict) -> dict:
        """Get optimized training example counts using actual database subsections."""
        
        # Define training example strategy based on ACTUAL database subsections and their availability
        training_strategies = {
            "Number Operations": {
                # Target: 6 examples total - use high-availability subsections
                "Number Properties": 2,    # 32 available - excellent coverage
                "Fractions": 2,           # 21 available - good coverage
                "Arithmetic": 1,          # 18 available - good coverage
                "Word Problems": 1,       # 16 available - problem-solving contexts
                "Decimals": 0,            # 2 available - too few, skip
                "Ratios": 0               # 5 available - but not in domain groups
            },
            "Algebra & Functions": {
                # Target: 4 examples total - focus on available subsections
                "Algebra": 3,             # 16 available - good coverage
                "Number Sequences": 1     # 2 available - minimal but relevant
            },
            "Geometry & Spatial": {
                # Target: 4 examples total - focus on geometry only
                "Geometry": 4             # 25 available - excellent coverage, no overlap with Measurement domain
            },
            "Measurement": {
                # Target: 3 examples total - use measurement and money
                "Measurement": 2,         # 10 available - good coverage
                "Money": 1                # 4 available - adequate for money problems
            },
            "Data & Probability": {
                # Target: 2 examples total - use available data subsections
                "Data Interpretation": 1,  # 9 available - good coverage
                "Probability": 1          # 1 available - minimal but relevant
            }
        }
        
        # Get the strategy for this domain
        strategy = training_strategies.get(group_name, {})
        
        # Build the final mapping using actual database subsections
        training_map = {}
        for db_subsection, count in strategy.items():
            if count > 0:
                training_map[db_subsection] = count
        
        total_examples = sum(training_map.values())
        logger.info(f"🔍 TRAINING STRATEGY: {group_name} will use {total_examples} training examples from database subsections: {training_map}")
        
        return training_map
    
    def get_domain_training_examples(self, domain_subsections: dict, difficulty: str) -> List[Dict[str, Any]]:
        """Get subsection-specific training examples for a domain group."""
        try:
            from app.generator import SSATGenerator
            
            generator = SSATGenerator()
            examples = []
            
            logger.info(f"🔍 DOMAIN EXAMPLES: Fetching training examples for subsections: {domain_subsections}")
            
            # Fetch examples for each subsection in the domain
            for subsection, count in domain_subsections.items():
                if count > 0:
                    logger.info(f"🔍 DOMAIN EXAMPLES: Getting {count} examples for {subsection}")
                    
                    # Query database for subsection-specific examples with extra buffer for diversity
                    buffer_count = min(count * 3, 10)  # Request 3x more for diversity, cap at 10
                    
                    subsection_examples = generator.supabase.rpc('get_training_examples_hybrid', {
                        'section_filter': 'Quantitative',
                        'subsection_filter': subsection,
                        'difficulty_filter': difficulty,
                        'query_embedding': None,
                        'limit_count': buffer_count  # Get more examples than needed
                    }).execute()
                    
                    if subsection_examples.data:
                        # Randomly select the needed count from available examples for diversity
                        import random
                        available_examples = subsection_examples.data
                        if len(available_examples) >= count:
                            selected_examples = random.sample(available_examples, count)
                        else:
                            selected_examples = available_examples
                        
                        examples.extend(selected_examples)
                        logger.info(f"🔍 DOMAIN EXAMPLES: Selected {len(selected_examples)} examples from {len(available_examples)} available for {subsection}")
                    else:
                        logger.warning(f"🔍 DOMAIN EXAMPLES: No examples found for {subsection}")
            
            # Remove search_method field for compatibility
            for example in examples:
                example.pop('search_method', None)
            
            logger.info(f"🔍 DOMAIN EXAMPLES: Total examples collected: {len(examples)}")
            
            # If we don't have enough subsection-specific examples, add generic quantitative examples
            target_count = sum(count for count in domain_subsections.values() if count > 0)
            if len(examples) < target_count:
                remaining_needed = target_count - len(examples)
                logger.info(f"🔍 DOMAIN EXAMPLES: Need {remaining_needed} more examples, fetching generic quantitative")
                
                fallback_examples = generator.supabase.rpc('get_training_examples_hybrid', {
                    'section_filter': 'Quantitative',
                    'subsection_filter': None,
                    'difficulty_filter': difficulty,
                    'query_embedding': None,
                    'limit_count': remaining_needed * 2  # Get extra for diversity
                }).execute()
                
                if fallback_examples.data:
                    # Remove search_method and avoid duplicates
                    available_fallback = []
                    for example in fallback_examples.data:
                        example.pop('search_method', None)
                        if example not in examples:
                            available_fallback.append(example)
                    
                    # Randomly select needed count for diversity
                    if len(available_fallback) >= remaining_needed:
                        import random
                        selected_fallback = random.sample(available_fallback, remaining_needed)
                    else:
                        selected_fallback = available_fallback
                    
                    examples.extend(selected_fallback)
                    logger.info(f"🔍 DOMAIN EXAMPLES: Added {len(selected_fallback)} diverse fallback examples")
            
            return examples[:target_count]
            
        except Exception as e:
            logger.error(f"🔍 DOMAIN EXAMPLES: Error fetching domain examples: {e}")
            # Fallback to empty list - prompts will work without examples
            return []

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
                "Easy": "- Multi-step calculations, basic word problems, fundamental operations with moderate complexity, simple geometric concepts",
                "Medium": "- Complex multi-step problems, advanced word problems, sophisticated calculations, intermediate algebra, advanced geometry",
                "Hard": "- Highly complex multi-step problems, sophisticated word problems, advanced calculations requiring strategic thinking, complex geometry, probability, statistics"
            },
            "reading": {
                "Easy": "- Moderate complexity passages, clear main ideas, basic inference, moderate vocabulary",
                "Medium": "- Complex passages, sophisticated themes, advanced inference, complex vocabulary, literary analysis",
                "Hard": "- Highly complex passages, sophisticated themes, advanced inference, complex vocabulary, literary analysis, nuanced understanding"
            },
            "analogy": {
                "Easy": "- Clear relationships, moderate vocabulary, straightforward analogies, basic reasoning",
                "Medium": "- Complex relationships, advanced vocabulary, sophisticated analogies, abstract reasoning",
                "Hard": "- Highly complex relationships, sophisticated vocabulary, advanced analogies, abstract reasoning, nuanced understanding"
            },
            "synonym": {
                "Easy": "- Moderate vocabulary, clear word meanings, straightforward synonyms, basic understanding",
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

    def _get_shared_critical_requirements(self, subsections: dict, difficulty: str) -> str:
        """Get shared critical requirements for all domain prompts."""
        return f"""CRITICAL REQUIREMENTS:
- Each question MUST use one of these EXACT subsection names: {list(subsections.keys())}
- Generate exactly the specified number for each subsection
- Use answer choice format (A, B, C, D)
- **DIFFICULTY LEVEL: {difficulty}** - Questions MUST match this difficulty level exactly. Do NOT generate easier questions.
- MANDATORY COGNITIVE LEVEL: For {difficulty} questions, you MUST use "{self._get_cognitive_level_by_difficulty(difficulty)}" as the cognitive_level"""

    def _get_shared_output_format(self) -> str:
        """Get shared output format for all domain prompts."""
        return """OUTPUT FORMAT - Return ONLY a JSON object:
{
  "questions": [
    {
      "text": "Question text here",
      "options": [
        {"letter": "A", "text": "Option A"},
        {"letter": "B", "text": "Option B"},
        {"letter": "C", "text": "Option C"},
        {"letter": "D", "text": "Option D"}
      ],
      "correct_answer": "A",
      "explanation": "Clear step-by-step explanation",
      "subsection": "SubsectionName",
      "tags": ["tag1", "tag2"],
      "cognitive_level": "APPLY"
    }
  ]
}

REMEMBER: Use EXACTLY the subsection names listed above and generate the EXACT count for each."""
