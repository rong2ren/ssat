"""Service for managing AI-generated content in the database."""

import uuid
from typing import List, Dict, Any, Optional
from loguru import logger
from datetime import datetime
import json


def convert_answer_letter_to_index(answer: str) -> int:
    """Convert A,B,C,D to 0,1,2,3 for database storage.
    
    Args:
        answer: Letter answer like "A", "B", "C", "D"
        
    Returns:
        0-based index (0,1,2,3)
    """
    if isinstance(answer, str) and len(answer) == 1:
        return ord(answer.upper()) - ord('A')
    return 0  # Default fallback


def convert_answer_index_to_letter(index: int) -> str:
    """Convert 0,1,2,3 to A,B,C,D for human-readable display.
    
    Args:
        index: 0-based index (0,1,2,3)
        
    Returns:
        Letter answer like "A", "B", "C", "D"
    """
    return chr(ord('A') + index) if 0 <= index < 4 else 'A'

from app.services.database import get_database_connection
from app.services.embedding_service import embedding_service
from app.models.responses import TestSection, QuestionGenerationResponse, ReadingGenerationResponse, WritingGenerationResponse


class AIContentService:
    """Service for storing and retrieving AI-generated content."""
    
    def __init__(self):
        self.supabase = get_database_connection()
    
    async def create_generation_session(self, job_id: str, request_params: Dict[str, Any]) -> str:
        """Create a new AI generation session."""
        try:
            session_data = {
                "id": job_id,
                "request_params": request_params,
                "total_questions_generated": 0,
                "providers_used": [],
                "generation_duration_ms": 0,
                "status": "running"
            }
            
            result = self.supabase.table("ai_generation_sessions").insert(session_data).execute()
            logger.info(f"Created AI generation session: {job_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to create AI generation session: {e}")
            raise
    
    async def update_session_status(self, session_id: str, status: str, 
                                   total_questions: int = 0, 
                                   providers_used: List[str] = None,
                                   duration_ms: int = 0):
        """Update the session status and metadata."""
        try:
            update_data = {
                "status": status,
                "total_questions_generated": total_questions,
                "generation_duration_ms": duration_ms
            }
            
            if providers_used:
                update_data["providers_used"] = providers_used
            
            result = self.supabase.table("ai_generation_sessions").update(update_data).eq("id", session_id).execute()
            logger.info(f"Updated session {session_id} status to {status}")
            
        except Exception as e:
            logger.error(f"Failed to update session status: {e}")
            raise
    
    async def save_generated_questions(self, session_id: str, questions: List[Any], 
                                     section: str, subsection: str = None,
                                     training_examples_used: List[str] = None) -> List[str]:
        """Save AI-generated questions to the database."""
        try:
            question_ids = []
            
            for question in questions:
                question_id = str(uuid.uuid4())
                question_ids.append(question_id)
                
                # Extract question data based on structure
                logger.info(f"Question type: {type(question)}, has 'text' attr: {hasattr(question, 'text')}, has 'question' attr: {hasattr(question, 'question')}")
                if hasattr(question, 'text'):
                    # GeneratedQuestion model format
                    question_text = question.text
                    choices = [opt.text for opt in question.options] if hasattr(question, 'options') else []
                    # Convert correct_answer (A,B,C,D) to index (0,1,2,3) using clean conversion
                    answer = convert_answer_letter_to_index(question.correct_answer) if hasattr(question, 'correct_answer') else 0
                    explanation = question.explanation if hasattr(question, 'explanation') else None
                    difficulty = question.difficulty if hasattr(question, 'difficulty') else None
                    visual_description = question.visual_description if hasattr(question, 'visual_description') else None
                    # Extract AI-generated categorization
                    question_subsection = question.subsection if hasattr(question, 'subsection') else None
                    question_tags = question.tags if hasattr(question, 'tags') else []
                elif hasattr(question, 'question'):
                    # Legacy format
                    question_text = question.question
                    choices = question.choices if hasattr(question, 'choices') else []
                    # Handle both string and integer answers
                    if hasattr(question, 'answer'):
                        if isinstance(question.answer, str):
                            answer = convert_answer_letter_to_index(question.answer)
                        else:
                            answer = question.answer  # Already an integer
                    else:
                        answer = 0
                    explanation = question.explanation if hasattr(question, 'explanation') else None
                    difficulty = question.difficulty if hasattr(question, 'difficulty') else None
                    visual_description = question.visual_description if hasattr(question, 'visual_description') else None
                    question_subsection = question.subsection if hasattr(question, 'subsection') else None
                    question_tags = question.tags if hasattr(question, 'tags') else []
                else:
                    # Handle dict format
                    question_text = question.get('text', question.get('question', ''))
                    if 'options' in question:
                        choices = [opt.get('text', opt) if isinstance(opt, dict) else str(opt) for opt in question.get('options', [])]
                    else:
                        choices = question.get('choices', [])
                    
                    # Handle answer conversion for dict format
                    if 'correct_answer' in question:
                        answer = convert_answer_letter_to_index(question.get('correct_answer', 'A'))
                    elif 'answer' in question:
                        answer_val = question.get('answer')
                        if isinstance(answer_val, str):
                            answer = convert_answer_letter_to_index(answer_val)
                        else:
                            answer = answer_val  # Already an integer
                    else:
                        answer = 0
                    
                    explanation = question.get('explanation')
                    difficulty = question.get('difficulty')
                    visual_description = question.get('visual_description')
                    # Extract AI-generated categorization from dict
                    question_subsection = question.get('subsection')
                    question_tags = question.get('tags', [])
                    
                    # Debug logging for dict format
                    logger.info(f"Dict question keys: {list(question.keys())}")
                    logger.info(f"Extracted subsection: '{question_subsection}', tags: {question_tags}")
                
                # Generate embedding for the question
                question_embedding = embedding_service.generate_question_embedding(question_text, choices)
                
                # Use AI-generated subsection and tags, with intelligent fallbacks
                final_subsection = question_subsection or subsection or "General"
                final_tags = question_tags if question_tags else []
                
                # Log what we're using for categorization with detailed breakdown
                logger.info(f"Subsection decision: question_subsection='{question_subsection}', passed_subsection='{subsection}', final='{final_subsection}'")
                logger.info(f"Tags: question_tags={question_tags}, final_tags={final_tags}")
                
                question_data = {
                    "id": question_id,
                    "generation_session_id": session_id,
                    "section": section,
                    "subsection": final_subsection,
                    "question": question_text,
                    "choices": choices,
                    "answer": answer,
                    "explanation": explanation,
                    "difficulty": difficulty,
                    "tags": final_tags,
                    "visual_description": visual_description,
                    "embedding": question_embedding,
                    "training_examples_used": training_examples_used or []
                }
                
                result = self.supabase.table("ai_generated_questions").insert(question_data).execute()
            
            logger.info(f"Saved {len(question_ids)} AI-generated questions for session {session_id}")
            return question_ids
            
        except Exception as e:
            logger.error(f"Failed to save AI-generated questions: {e}")
            raise
    
    async def save_reading_content(self, session_id: str, reading_data: Any,
                                 training_examples_used: List[str] = None, topic: str = None) -> Dict[str, List[str]]:
        """Save AI-generated reading passage and questions."""
        try:
            result_ids = {"passage_ids": [], "question_ids": []}
            
            # Extract reading data - handle different input formats
            if hasattr(reading_data, 'passages'):
                # ReadingSection object from complete test generation
                reading_sections = reading_data.passages
            elif hasattr(reading_data, 'reading_sections'):
                # Individual generation format
                reading_sections = reading_data.reading_sections
            elif isinstance(reading_data, dict):
                # Dictionary format from individual generation
                reading_sections = reading_data.get('reading_sections', [])
            else:
                # Fallback - assume it's a list of passages
                reading_sections = [reading_data] if reading_data else []
            
            logger.info(f"Processing {len(reading_sections)} reading sections for session {session_id}")
            for section in reading_sections:
                # Save passage
                passage_id = str(uuid.uuid4())
                result_ids["passage_ids"].append(passage_id)
                
                # Handle different data formats - extract passage text
                if hasattr(section, 'text'):
                    # ReadingPassage object format
                    passage_text = section.text
                elif isinstance(section, dict) and 'passage' in section:
                    # AI response format: {"passage": {"text": "..."}, "questions": [...]}
                    passage_text = section['passage'].get('text', '')
                else:
                    # Fallback
                    passage_text = getattr(section, 'passage', '')
                passage_embedding = embedding_service.generate_embedding(passage_text)
                
                # Build tags array with topic and any additional tags
                passage_tags = []
                
                # First try to get AI-generated topic from passage data, then fall back to parameter
                ai_generated_topic = None
                if hasattr(section, 'topic'):
                    ai_generated_topic = section.topic
                elif isinstance(section, dict):
                    # Check for topic at section level
                    if section.get('topic'):
                        ai_generated_topic = section['topic']
                    # Check for topic nested in passage data
                    elif 'passage' in section and isinstance(section['passage'], dict) and section['passage'].get('topic'):
                        ai_generated_topic = section['passage']['topic']
                
                # Use AI-generated topic if available, otherwise use passed topic parameter
                final_topic = ai_generated_topic or topic
                logger.info(f"Using topic for passage {passage_id}: '{final_topic}' (AI-generated: {bool(ai_generated_topic)}, Parameter: {bool(topic)})")
                if final_topic:
                    passage_tags.append(final_topic)
                
                # Add any additional tags from the generated content
                if hasattr(section, 'tags') and section.tags:
                    passage_tags.extend(section.tags)
                elif hasattr(section, 'metadata') and section.metadata and 'tags' in section.metadata:
                    passage_tags.extend(section.metadata['tags'])
                
                # Remove duplicates while preserving order
                passage_tags = list(dict.fromkeys(passage_tags))
                
                passage_data = {
                    "id": passage_id,
                    "generation_session_id": session_id,
                    "passage": passage_text,
                    "passage_type": section.passage_type if hasattr(section, 'passage_type') else getattr(section, 'passage_type', 'General'),
                    "tags": passage_tags,
                    "embedding": passage_embedding,
                    "training_examples_used": training_examples_used or []
                }
                
                self.supabase.table("ai_generated_reading_passages").insert(passage_data).execute()
                
                # Save questions for this passage - handle different formats
                if hasattr(section, 'questions'):
                    # ReadingPassage object format
                    questions = section.questions
                elif isinstance(section, dict) and 'questions' in section:
                    # AI response format: {"passage": {...}, "questions": [...]}
                    questions = section['questions']
                else:
                    # Fallback
                    questions = section.get('questions', []) if isinstance(section, dict) else []
                logger.info(f"Processing passage {passage_id}: found {len(questions)} questions to save")
                for question in questions:
                    question_id = str(uuid.uuid4())
                    result_ids["question_ids"].append(question_id)
                    
                    question_text = question.text if hasattr(question, 'text') else getattr(question, 'question', '')
                    choices = [opt.text for opt in question.options] if hasattr(question, 'options') else getattr(question, 'choices', [])
                    question_embedding = embedding_service.generate_question_embedding(question_text, choices)
                    
                    # Extract question-specific tags only (no topic inheritance)
                    tags = []
                    if hasattr(question, 'tags') and question.tags:
                        tags = question.tags
                    elif isinstance(question, dict) and question.get('tags'):
                        tags = question['tags']
                    
                    # Convert answer from letter to integer for database storage
                    if hasattr(question, 'correct_answer'):
                        answer = convert_answer_letter_to_index(question.correct_answer)
                    elif hasattr(question, 'answer'):
                        answer_val = getattr(question, 'answer', 'A')
                        if isinstance(answer_val, str):
                            answer = convert_answer_letter_to_index(answer_val)
                        else:
                            answer = answer_val  # Already an integer
                    elif isinstance(question, dict):
                        answer_val = question.get('correct_answer') or question.get('answer', 'A')
                        if isinstance(answer_val, str):
                            answer = convert_answer_letter_to_index(answer_val)
                        else:
                            answer = answer_val  # Already an integer
                    else:
                        answer = 0  # Default fallback
                    
                    # Reading questions don't have subsections - they're categorized by passage type
                    question_data = {
                        "id": question_id,
                        "passage_id": passage_id,
                        "generation_session_id": session_id,
                        "question": question_text,
                        "choices": choices,
                        "answer": answer,  # Now properly converted to integer
                        "explanation": question.explanation if hasattr(question, 'explanation') else getattr(question, 'explanation', ''),
                        "difficulty": question.difficulty if hasattr(question, 'difficulty') else getattr(question, 'difficulty', ''),
                        "tags": tags,
                        "visual_description": question.visual_description if hasattr(question, 'visual_description') else getattr(question, 'visual_description', None),
                        "embedding": question_embedding,
                        "training_examples_used": training_examples_used or []
                    }
                    
                    self.supabase.table("ai_generated_reading_questions").insert(question_data).execute()
                    logger.info(f"Successfully saved reading question {question_id} for passage {passage_id}")
            
            logger.info(f"Saved reading content for session {session_id}: {len(result_ids['passage_ids'])} passages, {len(result_ids['question_ids'])} questions")
            return result_ids
            
        except Exception as e:
            logger.error(f"Failed to save reading content: {e}")
            raise
    
    async def save_writing_prompts(self, session_id: str, writing_data: Any,
                                 training_examples_used: List[str] = None) -> List[str]:
        """Save AI-generated writing prompts."""
        try:
            prompt_ids = []
            
            # Extract writing prompts - handle different input formats
            if hasattr(writing_data, 'prompt'):
                # WritingSection object from complete test generation
                prompts = [writing_data.prompt]
            elif hasattr(writing_data, 'writing_prompts'):
                # Individual generation format
                prompts = writing_data.writing_prompts
            elif isinstance(writing_data, dict):
                # Dictionary format from individual generation
                prompts = writing_data.get('writing_prompts', [])
            else:
                # Fallback - assume it's a single prompt
                prompts = [writing_data] if writing_data else []
            
            for prompt in prompts:
                prompt_id = str(uuid.uuid4())
                prompt_ids.append(prompt_id)
                
                # WritingPrompt model uses 'prompt_text' not 'prompt'
                prompt_text = prompt.prompt_text if hasattr(prompt, 'prompt_text') else getattr(prompt, 'prompt', '')
                prompt_embedding = embedding_service.generate_embedding(prompt_text)
                
                # Extract subsection from prompt data if available
                subsection = "Picture Story"  # Default
                if hasattr(prompt, 'subsection') and prompt.subsection:
                    subsection = prompt.subsection
                elif isinstance(prompt, dict) and prompt.get('subsection'):
                    subsection = prompt['subsection']
                
                # Extract tags from prompt data if available
                tags = []
                if hasattr(prompt, 'tags') and prompt.tags:
                    tags = prompt.tags
                elif isinstance(prompt, dict) and prompt.get('tags'):
                    tags = prompt['tags']
                
                prompt_data = {
                    "id": prompt_id,
                    "generation_session_id": session_id,
                    "prompt": prompt_text,
                    "tags": tags,
                    "visual_description": prompt.visual_description if hasattr(prompt, 'visual_description') else getattr(prompt, 'visual_description', None),
                    "embedding": prompt_embedding,
                    "training_examples_used": training_examples_used or []
                }
                
                self.supabase.table("ai_generated_writing_prompts").insert(prompt_data).execute()
            
            logger.info(f"Saved {len(prompt_ids)} writing prompts for session {session_id}")
            return prompt_ids
            
        except Exception as e:
            logger.error(f"Failed to save writing prompts: {e}")
            raise
    
    async def save_test_section(self, session_id: str, section: TestSection,
                              training_examples_used: List[str] = None) -> Dict[str, Any]:
        """Save a complete test section with appropriate content type."""
        try:
            saved_ids = {}
            
            if section.section_type == "reading":
                # Extract topic from the first reading passage for tagging
                topic = None
                if hasattr(section, 'passages') and section.passages:
                    # Complete test format: section has passages attribute
                    first_passage = section.passages[0]
                    topic = getattr(first_passage, 'topic', None)
                elif hasattr(section, 'questions') and section.questions:
                    # Individual reading section format: extract from general reading content
                    topic = "Elementary Reading"  # Default for reading comprehension
                
                saved_ids = await self.save_reading_content(session_id, section, training_examples_used, topic=topic)
            elif section.section_type == "writing":
                saved_ids["prompt_ids"] = await self.save_writing_prompts(session_id, section, training_examples_used)
            else:
                # Regular questions (quantitative, analogy, synonym)
                section_name = {
                    "quantitative": "Quantitative",
                    "analogy": "Verbal",
                    "synonym": "Verbal"
                }.get(section.section_type, "General")
                
                subsection = {
                    "analogy": "Analogies",
                    "synonym": "Synonyms"
                }.get(section.section_type, None)  # Use None for quantitative to preserve AI-determined subsections
                
                questions = section.questions if hasattr(section, 'questions') else []
                saved_ids["question_ids"] = await self.save_generated_questions(
                    session_id, questions, section_name, subsection, training_examples_used
                )
            
            logger.info(f"Saved test section {section.section_type} for session {session_id}")
            return saved_ids
            
        except Exception as e:
            logger.error(f"Failed to save test section: {e}")
            raise
    
    async def get_session_statistics(self, session_id: str) -> Dict[str, Any]:
        """Get detailed statistics for a generation session."""
        try:
            result = self.supabase.rpc("get_session_statistics", {"session_id": session_id}).execute()
            
            if result.data:
                return result.data[0]
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Failed to get session statistics: {e}")
            raise
    
    async def generate_embeddings_for_content(self, content_ids: List[str], content_type: str):
        """Generate embeddings for saved AI content (placeholder for future implementation)."""
        try:
            # TODO: Implement embedding generation using sentence transformers
            # This would generate embeddings for the saved content and update the database
            logger.info(f"Embedding generation not yet implemented for {len(content_ids)} {content_type} items")
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise