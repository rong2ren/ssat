"""Service for parsing and saving training examples to existing database tables."""

import re
import uuid
from typing import List, Dict, Any, Tuple
from loguru import logger
from supabase import Client

from app.models.requests import TrainingExamplesRequest
from app.services.embedding_service import EmbeddingService


class TrainingExamplesService:
    """Service for parsing and saving training examples."""
    
    def __init__(self, supabase_client: Client, embedding_service: EmbeddingService):
        self.supabase = supabase_client
        self.embedding_service = embedding_service
    
    async def save_training_examples(self, request: TrainingExamplesRequest, user_id: str) -> Dict[str, Any]:
        """Parse and save training examples to appropriate database tables."""
        try:
            # Handle simple word list format for synonyms
            if request.section_type == "synonym" and request.input_format == "simple":
                return await self._save_synonym_word_list(request, user_id)
            elif request.section_type in ["quantitative", "analogy", "synonym"]:
                return await self._save_ssat_questions(request, user_id)
            elif request.section_type == "reading":
                return await self._save_reading_examples(request, user_id)
            elif request.section_type == "writing":
                return await self._save_writing_prompts(request, user_id)
            else:
                raise ValueError(f"Unsupported section type: {request.section_type}")
                
        except Exception as e:
            logger.error(f"Failed to save training examples: {e}")
            raise
    
    async def _save_ssat_questions(self, request: TrainingExamplesRequest, user_id: str) -> Dict[str, Any]:
        """Save quantitative, analogy, or synonym questions to ssat_questions table."""
        questions = self._parse_ssat_questions(request.examples_text, request.section_type)
        
        if not questions:
            raise ValueError("No valid questions found in the provided text")
        
        # Map section type to database section/subsection
        section_mapping = {
            "quantitative": ("Quantitative", "General Math"),
            "analogy": ("Verbal", "Analogies"),
            "synonym": ("Verbal", "Synonyms")
        }
        
        section, subsection = section_mapping[request.section_type]
        
        saved_count = 0
        for question in questions:
            try:
                # Generate embedding
                question_text = question.get('question', '')
                embedding = self.embedding_service.generate_embedding(question_text)
                
                # Use subsection from question if available, otherwise use default based on section type
                if question.get('subsection'):
                    question_subsection = question.get('subsection')
                    # Validate quantitative subsections
                    if request.section_type == "quantitative":
                        from app.specifications import validate_quantitative_subsection
                        if not validate_quantitative_subsection(question_subsection):
                            logger.warning(f"Invalid subsection '{question_subsection}' for quantitative question, using default")
                            question_subsection = "Arithmetic"
                elif request.section_type == "quantitative":
                    question_subsection = "Arithmetic"  # Default for quantitative
                elif request.section_type == "analogy":
                    question_subsection = "Analogies"
                elif request.section_type == "synonym":
                    question_subsection = "Synonyms"
                else:
                    question_subsection = "Arithmetic"
                
                # Prepare data for database
                question_data = {
                    "id": f"CUSTOM-{uuid.uuid4().hex[:8].upper()}",
                    "source_file": "custom_training_examples",
                    "section": section,
                    "subsection": question_subsection,
                    "question": question_text,
                    "choices": question.get('choices', []),
                    "answer": question.get('answer', 0),
                    "explanation": question.get('explanation', ''),
                    "difficulty": question.get('difficulty', 'Medium'),
                    "tags": question.get('tags', []),
                    "visual_description": question.get('visual_description', ''),
                    "embedding": embedding
                }
                
                # Insert into database
                response = self.supabase.table("ssat_questions").insert(question_data).execute()
                
                if response.data:
                    saved_count += 1
                    logger.info(f"Saved question: {question_data['id']}")
                
            except Exception as e:
                logger.warning(f"Failed to save question: {e}")
                continue
        
        return {
            "saved_count": saved_count,
            "total_parsed": len(questions),
            "section_type": request.section_type
        }
    
    async def _save_synonym_word_list(self, request: TrainingExamplesRequest, user_id: str) -> Dict[str, Any]:
        """Save synonym questions generated from a word list."""
        # Parse words from the input
        words = [word.strip() for word in request.examples_text.split(',') if word.strip()]
        
        if not words:
            raise ValueError("No valid words found in the word list")
        
        # Generate synonym questions for each word using LLM
        questions = await self._generate_synonym_questions_from_words(words)
        
        if not questions:
            raise ValueError("Failed to generate synonym questions from word list")
        
        # Save the generated questions
        saved_count = 0
        for question in questions:
            try:
                # Generate embedding
                question_text = question.get('question', '')
                embedding = self.embedding_service.generate_embedding(question_text)
                
                # Prepare data for database
                question_data = {
                    "id": f"CUSTOM-{uuid.uuid4().hex[:8].upper()}",
                    "source_file": "custom_training_examples",
                    "section": "Verbal",
                    "subsection": "Synonyms",
                    "question": question_text,
                    "choices": question.get('choices', []),
                    "answer": question.get('answer', 0),
                    "explanation": question.get('explanation', ''),
                    "difficulty": question.get('difficulty', 'Medium'),
                    "tags": question.get('tags', []),
                    "visual_description": question.get('visual_description', ''),
                    "embedding": embedding
                }
                
                # Insert into database
                response = self.supabase.table("ssat_questions").insert(question_data).execute()
                
                if response.data:
                    saved_count += 1
                    logger.info(f"Saved synonym question: {question_data['id']}")
                
            except Exception as e:
                logger.warning(f"Failed to save synonym question: {e}")
                continue
        
        return {
            "saved_count": saved_count,
            "total_parsed": len(words),
            "section_type": request.section_type
        }
    
    async def _generate_synonym_questions_from_words(self, words: List[str]) -> List[Dict[str, Any]]:
        """Generate synonym questions from a list of words using LLM."""
        try:
            from app.llm import llm_client
            from app.generator import SSATGenerator
            
            # Create a request for synonym generation
            from app.models.requests import QuestionRequest
            from app.models.enums import QuestionType, DifficultyLevel
            
            request = QuestionRequest(
                question_type=QuestionType.SYNONYM,
                difficulty=DifficultyLevel.MEDIUM,
                count=len(words)
            )
            
            # Initialize generator and get training examples
            generator = SSATGenerator()
            training_examples = generator.get_training_examples(request)
            
            # Build prompt for word-to-question generation
            system_message = f"""You are an expert SSAT synonym question generator.

Generate {len(words)} synonym questions for these words: {', '.join(words)}

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
            
            # Call LLM to generate questions
            content = await llm_client.call_llm_async(
                provider="deepseek",
                system_message=system_message,
                prompt="Generate the synonym questions as specified.",
                max_tokens=4000,
                temperature=0.7
            )
            
            if not content:
                raise ValueError("LLM failed to generate questions")
            
            # Parse the response
            import json
            import re
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON found in LLM response")
            
            data = json.loads(json_match.group())
            
            # Convert to our internal format
            questions = []
            for q_data in data.get("questions", []):
                question = {
                    "question": q_data["text"],
                    "choices": [opt["text"] for opt in q_data["options"]],
                    "answer": ord(q_data["correct_answer"]) - ord('A'),  # Convert A->0, B->1, etc.
                    "explanation": q_data["explanation"],
                    "difficulty": "Medium",
                    "subsection": q_data.get("subsection", "Synonyms"),
                    "tags": q_data.get("tags", []),
                    "visual_description": q_data.get("visual_description", "")
                }
                questions.append(question)
            
            return questions
            
        except Exception as e:
            logger.error(f"Failed to generate synonym questions from words: {e}")
            raise
    
    async def _save_reading_examples(self, request: TrainingExamplesRequest, user_id: str) -> Dict[str, Any]:
        """Save reading passage and questions to reading_passages and reading_questions tables."""
        passage_data, questions = self._parse_reading_examples(request.examples_text)
        
        if not passage_data or not questions:
            raise ValueError("No valid reading passage and questions found")
        
        try:
            # Generate embedding for passage
            passage_text = passage_data.get('passage', '')
            passage_embedding = self.embedding_service.generate_embedding(passage_text)
            
            # Save passage
            passage_id = f"CUSTOM-READING-{uuid.uuid4().hex[:8].upper()}"
            passage_data_to_save = {
                "id": passage_id,
                "source_file": "custom_training_examples",
                "passage": passage_text,
                "passage_type": passage_data.get('passage_type', 'Non-Fiction'),
                "embedding": passage_embedding,
                "tags": passage_data.get('tags', [])
            }
            
            passage_response = self.supabase.table("reading_passages").insert(passage_data_to_save).execute()
            
            if not passage_response.data:
                raise ValueError("Failed to save reading passage")
            
            # Save questions
            saved_questions = 0
            for i, question in enumerate(questions):
                try:
                    question_text = question.get('question', '')
                    question_embedding = self.embedding_service.generate_embedding(question_text)
                    
                    question_data = {
                        "id": f"CUSTOM-READING-Q-{uuid.uuid4().hex[:8].upper()}",
                        "passage_id": passage_id,
                        "question": question_text,
                        "choices": question.get('choices', []),
                        "answer": question.get('answer', 0),
                        "explanation": question.get('explanation', ''),
                        "difficulty": question.get('difficulty', 'Medium'),
                        "tags": question.get('tags', []),
                        "visual_description": question.get('visual_description', ''),
                        "embedding": question_embedding
                    }
                    
                    question_response = self.supabase.table("reading_questions").insert(question_data).execute()
                    
                    if question_response.data:
                        saved_questions += 1
                        logger.info(f"Saved reading question: {question_data['id']}")
                
                except Exception as e:
                    logger.warning(f"Failed to save reading question: {e}")
                    continue
            
            return {
                "saved_count": saved_questions,
                "total_parsed": len(questions),
                "section_type": request.section_type,
                "passage_saved": True
            }
            
        except Exception as e:
            logger.error(f"Failed to save reading examples: {e}")
            raise
    
    async def _save_writing_prompts(self, request: TrainingExamplesRequest, user_id: str) -> Dict[str, Any]:
        """Save writing prompts to writing_prompts table."""
        prompts = self._parse_writing_prompts(request.examples_text)
        
        if not prompts:
            raise ValueError("No valid writing prompts found")
        
        saved_count = 0
        for prompt in prompts:
            try:
                prompt_text = prompt.get('prompt', '')
                embedding = self.embedding_service.generate_embedding(prompt_text)
                
                prompt_data = {
                    "id": f"CUSTOM-WRITING-{uuid.uuid4().hex[:8].upper()}",
                    "source_file": "custom_training_examples",
                    "prompt": prompt_text,
                    "tags": prompt.get('tags', []),
                    "visual_description": prompt.get('visual_description', ''),
                    "image_path": prompt.get('image_path', ''),  # Add image_path field
                    "embedding": embedding
                }
                
                response = self.supabase.table("writing_prompts").insert(prompt_data).execute()
                
                if response.data:
                    saved_count += 1
                    logger.info(f"Saved writing prompt: {prompt_data['id']}")
            
            except Exception as e:
                logger.warning(f"Failed to save writing prompt: {e}")
                continue
        
        return {
            "saved_count": saved_count,
            "total_parsed": len(prompts),
            "section_type": request.section_type
        }
    
    def _parse_ssat_questions(self, text: str, section_type: str) -> List[Dict[str, Any]]:
        """Parse SSAT questions (quantitative, analogy, synonym) from text."""
        questions = []
        lines = text.strip().split('\n')
        current_question = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_question:
                    if self._validate_ssat_question(current_question):
                        questions.append(current_question.copy())
                    current_question = {}
                continue
            
            if line.lower().startswith('question:'):
                current_question['question'] = line[9:].strip()
            elif line.lower().startswith('choices:'):
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
            elif line.lower().startswith('difficulty:'):
                current_question['difficulty'] = line[11:].strip()
            elif line.lower().startswith('subsection:'):
                current_question['subsection'] = line[11:].strip()
            elif line.lower().startswith('tags:'):
                tags_text = line[5:].strip()
                current_question['tags'] = [tag.strip() for tag in tags_text.split(',')]
        
        # Don't forget the last question
        if current_question and self._validate_ssat_question(current_question):
            questions.append(current_question)
        
        return questions
    
    def _parse_reading_examples(self, text: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Parse reading passage and questions from text."""
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
            raise ValueError("No passage text found")
        if not questions:
            raise ValueError("No questions found")
        
        return passage_data, questions
    
    def _parse_writing_prompts(self, text: str) -> List[Dict[str, Any]]:
        """Parse writing prompts from text."""
        prompts = []
        lines = text.strip().split('\n')
        current_prompt = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_prompt:
                    if self._validate_writing_prompt(current_prompt):
                        prompts.append(current_prompt.copy())
                    current_prompt = {}
                continue
            
            if line.lower().startswith('prompt:'):
                current_prompt['prompt'] = line[7:].strip()
            elif line.lower().startswith('tags:'):
                tags_text = line[5:].strip()
                current_prompt['tags'] = [tag.strip() for tag in tags_text.split(',')]
            elif line.lower().startswith('visual description:'):
                current_prompt['visual_description'] = line[19:].strip()
            elif line.lower().startswith('image path:'):
                current_prompt['image_path'] = line[11:].strip()
            elif not current_prompt.get('prompt'):
                # If no "Prompt:" label, treat the first non-empty line as prompt
                current_prompt['prompt'] = line
        
        # Don't forget the last prompt
        if current_prompt and self._validate_writing_prompt(current_prompt):
            prompts.append(current_prompt)
        
        return prompts
    
    def _validate_ssat_question(self, question: Dict[str, Any]) -> bool:
        """Validate SSAT question has required fields."""
        required = ['question', 'choices', 'answer']
        if not all(field in question for field in required):
            return False
        if not isinstance(question.get('choices'), list) or len(question['choices']) != 4:
            return False
        if question.get('answer') not in [0, 1, 2, 3]:
            return False
        return True
    
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
    
    def _validate_writing_prompt(self, prompt: Dict[str, Any]) -> bool:
        """Validate writing prompt has required fields."""
        return 'prompt' in prompt and prompt['prompt'].strip() 