"""
Pool Response Converter
Helper service to convert pool data to API response format
"""

import logging
from typing import List, Dict, Any
from app.models.requests import QuestionGenerationRequest
from app.models.responses import (
    QuestionGenerationResponse, 
    ReadingGenerationResponse, 
    WritingGenerationResponse, 
    GeneratedQuestion, 
    ReadingPassage, 
    WritingPrompt,
    GenerationMetadata
)
from app.models.base import Option

logger = logging.getLogger(__name__)

class PoolResponseConverter:
    """Convert pool data to API response format."""
    
    @staticmethod
    def convert_questions_to_response(
        pool_questions: List[Dict[str, Any]], 
        request: QuestionGenerationRequest
    ) -> QuestionGenerationResponse:
        """Convert pool questions to QuestionGenerationResponse."""
        
        questions = []
        for pool_question in pool_questions:
            # Convert choices to Option objects
            options = []
            for i, choice_text in enumerate(pool_question.get('choices', [])):
                options.append(Option(
                    letter=chr(65 + i),  # A, B, C, D
                    text=choice_text
                ))
            
            # Convert answer index to letter
            answer_index = pool_question.get('answer', 0)
            correct_answer = chr(65 + answer_index) if 0 <= answer_index < 4 else 'A'
            
            # Create GeneratedQuestion object
            question = GeneratedQuestion(
                id=pool_question.get('id'),
                question_type=request.question_type.value,
                difficulty=request.difficulty.value,
                text=pool_question.get('question', ''),
                options=options,
                correct_answer=correct_answer,
                explanation=pool_question.get('explanation', ''),
                cognitive_level='Application',  # Default
                tags=pool_question.get('tags', []),
                visual_description=pool_question.get('visual_description'),
                image_path=pool_question.get('image_path'),  # Add image_path field
                subsection=pool_question.get('subsection'),
                metadata={
                    'source': 'pool',
                    'generation_session_id': pool_question.get('generation_session_id'),
                    'created_at': pool_question.get('created_at')
                }
            )
            questions.append(question)
        
        return QuestionGenerationResponse(
            questions=questions,
            metadata=GenerationMetadata(
                generation_time=0.0,  # Pool retrieval is instant
                provider_used='pool',
                training_examples_count=0,
                training_example_ids=[],
                request_id=None
            ),
            count=len(questions)
        )
    
    @staticmethod
    def convert_reading_to_response(
        pool_passages: List[Dict[str, Any]], 
        request: QuestionGenerationRequest
    ) -> ReadingGenerationResponse:
        """Convert pool reading content to ReadingGenerationResponse."""
        
        passages = []
        for pool_passage in pool_passages:
            # Convert questions for this passage
            questions = []
            for pool_question in pool_passage.get('questions', []):
                # Convert choices to Option objects
                options = []
                for i, choice_text in enumerate(pool_question.get('choices', [])):
                    options.append(Option(
                        letter=chr(65 + i),  # A, B, C, D
                        text=choice_text
                    ))
                
                # Convert answer index to letter
                answer_index = pool_question.get('answer', 0)
                correct_answer = chr(65 + answer_index) if 0 <= answer_index < 4 else 'A'
                
                # Create GeneratedQuestion object for reading questions
                question = GeneratedQuestion(
                    id=pool_question.get('id'),
                    question_type="reading",
                    difficulty=request.difficulty.value if request.difficulty else "Medium",
                    text=pool_question.get('question', ''),
                    options=options,
                    correct_answer=correct_answer,
                    explanation=pool_question.get('explanation', ''),
                    cognitive_level='Application',  # Default
                    tags=pool_question.get('tags', []),
                    visual_description=pool_question.get('visual_description'),
                    image_path=pool_question.get('image_path'),  # Add image_path field
                    metadata={
                        'source': 'pool',
                        'passage_id': pool_passage.get('passage_id')
                    }
                )
                questions.append(question)
            
            # Create ReadingPassage object
            passage = ReadingPassage(
                id=str(pool_passage.get('passage_id', '')),  # Ensure string type
                text=pool_passage.get('passage', ''),
                passage_type=pool_passage.get('passage_type', 'General'),
                topic=pool_passage.get('topic', 'General'),  # Required field
                questions=questions,
                metadata={
                    'source': 'pool',
                    'generation_session_id': pool_passage.get('generation_session_id'),
                    'created_at': pool_passage.get('created_at')
                }
            )
            passages.append(passage)
        
        # Calculate total questions across all passages
        total_questions = sum(len(passage.questions) for passage in passages)
        
        return ReadingGenerationResponse(
            passages=passages,
            metadata=GenerationMetadata(
                generation_time=0.0,  # Pool retrieval is instant
                provider_used='pool',
                training_examples_count=0,
                training_example_ids=[],
                request_id=None
            ),
            count=len(passages),
            total_questions=total_questions
        )
    
    @staticmethod
    def convert_writing_to_response(
        pool_prompts: List[Dict[str, Any]], 
        request: QuestionGenerationRequest
    ) -> WritingGenerationResponse:
        """Convert pool writing prompts to WritingGenerationResponse."""
        
        prompts = []
        for pool_prompt in pool_prompts:
            # Create WritingPrompt object with correct field names
            prompt = WritingPrompt(
                prompt_text=pool_prompt.get('prompt_text', pool_prompt.get('prompt', '')),
                instructions="",  # Remove redundant instructions - section instructions will be used instead
                visual_description=pool_prompt.get('visual_description'),
                image_path=pool_prompt.get('image_path'),
                tags=pool_prompt.get('tags', []),
                metadata={
                    'source': 'pool',
                    'generation_session_id': pool_prompt.get('generation_session_id'),
                    'created_at': pool_prompt.get('created_at')
                }
            )
            prompts.append(prompt)
        
        return WritingGenerationResponse(
            prompts=prompts,
            metadata=GenerationMetadata(
                generation_time=0.0,  # Pool retrieval is instant
                provider_used='pool',
                training_examples_count=0,
                training_example_ids=[],
                request_id=None
            ),
            count=len(prompts)
        ) 

    # Section converters for full test generation
    @staticmethod
    def convert_questions_to_section(
        pool_questions: List[Dict[str, Any]], 
        section_type: str
    ):
        """Convert pool questions to appropriate section type for full test generation."""
        from app.models.responses import QuantitativeSection, SynonymSection, AnalogySection
        
        questions = []
        for pool_question in pool_questions:
            # Convert choices to Option objects
            options = []
            for i, choice_text in enumerate(pool_question.get('choices', [])):
                options.append(Option(
                    letter=chr(65 + i),  # A, B, C, D
                    text=choice_text
                ))
            
            # Convert answer index to letter
            answer_index = pool_question.get('answer', 0)
            correct_answer = chr(65 + answer_index) if 0 <= answer_index < 4 else 'A'
            
            # Create GeneratedQuestion object
            question = GeneratedQuestion(
                id=pool_question.get('id'),
                question_type=section_type,
                difficulty="Medium",  # Default for pool content
                text=pool_question.get('question', ''),
                options=options,
                correct_answer=correct_answer,
                explanation=pool_question.get('explanation', ''),
                cognitive_level='Application',  # Default
                tags=pool_question.get('tags', []),
                visual_description=pool_question.get('visual_description'),
                image_path=pool_question.get('image_path'),  # Add image_path field
                subsection=pool_question.get('subsection'),
                metadata={
                    'source': 'pool',
                    'generation_session_id': pool_question.get('generation_session_id'),
                    'created_at': pool_question.get('created_at')
                }
            )
            questions.append(question)
        
        # Return appropriate section type based on section_type
        if section_type == "quantitative":
            return QuantitativeSection(
                questions=questions,
                instructions="Complete the following math questions. Choose the best answer for each question."
            )
        elif section_type == "synonym":
            return SynonymSection(
                questions=questions,
                instructions="Choose the word that means the same as the given word."
            )
        elif section_type == "analogy":
            return AnalogySection(
                questions=questions,
                instructions="Complete each analogy by choosing the word that best fits the relationship."
            )
        else:
            # Fallback to QuantitativeSection
            return QuantitativeSection(
                questions=questions,
                instructions="Complete the following math questions. Choose the best answer for each question."
            )
    
    @staticmethod
    def convert_reading_to_section(
        pool_passages: List[Dict[str, Any]]
    ):
        """Convert pool reading content to ReadingSection for full test generation."""
        from app.models.responses import ReadingSection
        

        
        passages = []
        for pool_passage in pool_passages:
            # Convert questions for this passage
            questions = []
            for pool_question in pool_passage.get('questions', []):
                # Convert choices to Option objects
                options = []
                for i, choice_text in enumerate(pool_question.get('choices', [])):
                    options.append(Option(
                        letter=chr(65 + i),  # A, B, C, D
                        text=choice_text
                    ))
                
                # Convert answer index to letter
                answer_index = pool_question.get('answer', 0)
                correct_answer = chr(65 + answer_index) if 0 <= answer_index < 4 else 'A'
                
                # Create GeneratedQuestion object for reading questions
                question = GeneratedQuestion(
                    id=pool_question.get('id'),
                    question_type="reading",
                    difficulty="Medium",  # Default for pool content
                    text=pool_question.get('question', ''),
                    options=options,
                    correct_answer=correct_answer,
                    explanation=pool_question.get('explanation', ''),
                    cognitive_level='Application',  # Default
                    tags=pool_question.get('tags', []),
                    visual_description=pool_question.get('visual_description'),
                    image_path=pool_question.get('image_path'),  # Add image_path field
                    metadata={
                        'source': 'pool',
                        'passage_id': pool_passage.get('passage_id')
                    }
                )
                questions.append(question)
            
            # Create ReadingPassage object
            passage = ReadingPassage(
                id=str(pool_passage.get('passage_id', '')),  # Ensure string type
                text=pool_passage.get('passage', ''),
                passage_type=pool_passage.get('passage_type', 'General'),
                topic=pool_passage.get('topic', 'General'),  # Required field
                questions=questions,
                metadata={
                    'source': 'pool',
                    'generation_session_id': pool_passage.get('generation_session_id'),
                    'created_at': pool_passage.get('created_at')
                }
            )
            passages.append(passage)
        

        return ReadingSection(
            passages=passages,
            instructions="Read each passage carefully and answer the questions that follow."
        )
    
    @staticmethod
    def convert_writing_to_section(
        pool_prompts: List[Dict[str, Any]]
    ):
        """Convert pool writing prompts to WritingSection for full test generation."""
        from app.models.responses import WritingSection
        
        # For full test, we only need one prompt
        pool_prompt = pool_prompts[0] if pool_prompts else {}
        
        # Create WritingPrompt object with correct field names
        prompt = WritingPrompt(
            prompt_text=pool_prompt.get('prompt_text', pool_prompt.get('prompt', '')),
            instructions="",  # Remove redundant instructions - section instructions will be used instead
            visual_description=pool_prompt.get('visual_description'),
            tags=pool_prompt.get('tags', []),
            metadata={
                'source': 'pool',
                'generation_session_id': pool_prompt.get('generation_session_id'),
                'created_at': pool_prompt.get('created_at')
            }
        )
        
        return WritingSection(
            prompt=prompt,
            instructions="Look at the picture and tell a story about what happened. Make sure your story includes a beginning, a middle, and an end."
        ) 