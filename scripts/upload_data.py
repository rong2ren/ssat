#!/usr/bin/env python3
"""Upload SSAT questions from JSON files to Supabase with training-focused schema."""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from loguru import logger
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import uuid

# Loguru is configured automatically

class SupabaseUploader:
    def __init__(self, supabase_url: str, supabase_key: str):
        """Initialize Supabase client and embedding model."""
        self.supabase: Client = create_client(supabase_url, supabase_key)
        # Initialize Sentence-Transformers model for 384-dim embeddings
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')  # 384 dimensions
        logger.info("Supabase uploader initialized with embedding model")
        
    def _get_short_file_prefix(self, filename: str) -> str:
        """Generate a short unique prefix from filename."""
        # Remove extension
        name = os.path.splitext(filename)[0]
        
        # Create abbreviations for common patterns
        abbreviations = {
            'SSAT_ElementaryTest4th_1-Gemini': 'T4G1',
            'SSAT_ElementaryTest4th_2-Gemini': 'T4G2', 
            'SSAT_ElementaryTest4th_3-Gemini': 'T4G3',
            'SSAT Math Arithmetic Practice Test-Gemini': 'MAPT',
            'SSAT Math Word Problems Practice Test-Gemini': 'MWPT',
            'SSAT Elementary Level Practice Test-Gemini': 'ELPT',
            'SSAT-L Pretest-Gemini': 'SLPT',
            '2023TOG ElementaryGrade3-Gemini': 'G3G',
            '2023TOG ElementaryGrade3-Deepseek': 'G3D',
            '2023TOG ElementaryGrade4-Gemini': 'G4G',
            '2023TOG ElementaryGrade4-Deepseek': 'G4D',
            'Elementary_Level_SSAT_Words_to_Know-Gemini': 'WORD'
        }
        
        # Return abbreviation if exists, otherwise create one
        if name in abbreviations:
            return abbreviations[name]
        
        # Fallback: use first 2 letters of each word, max 8 chars
        words = name.replace('-', ' ').replace('_', ' ').split()
        prefix = ''.join(word[:2].upper() for word in words[:4])
        return prefix[:8]
    
    def validate_math_verbal_question(self, question_data: Dict[str, Any]) -> bool:
        """Validate that a math/verbal question has all required fields."""
        required_fields = ['id', 'section', 'subsection', 'question', 'answer', 'difficulty']
        
        # Check required fields exist
        for field in required_fields:
            if field not in question_data or not question_data[field]:
                logger.warning(f"Question missing required field '{field}': {question_data.get('id', 'unknown')}")
                return False
        
        # Validate question text is meaningful
        question_text = question_data['question'].strip()
        if len(question_text) < 10:
            logger.warning(f"Question text too short ({len(question_text)} chars): {question_data.get('id', 'unknown')}")
            return False
        
        # Validate choices if they exist
        choices = question_data.get('choices', [])
        if choices and len(choices) < 2:
            logger.warning(f"Question has insufficient choices ({len(choices)}): {question_data.get('id', 'unknown')}")
            return False
        
        # Validate answer is valid
        answer = question_data['answer']
        if choices:
            # For multiple choice, answer should be valid choice number
            if not isinstance(answer, int) or answer < 1 or answer > len(choices):
                logger.warning(f"Invalid answer index {answer} for {len(choices)} choices: {question_data.get('id', 'unknown')}")
                return False
        
        # Validate explanation if present
        if 'explanation' in question_data and question_data['explanation']:
            explanation = question_data['explanation']
            if isinstance(explanation, dict):
                explanation_text = explanation.get('text', '')
            else:
                explanation_text = str(explanation)
            
            if len(explanation_text.strip()) < 5:
                logger.warning(f"Explanation too short: {question_data.get('id', 'unknown')}")
                return False
        
        # Validate difficulty is valid
        valid_difficulties = ['Easy', 'Medium', 'Hard']
        if question_data['difficulty'] not in valid_difficulties:
            logger.warning(f"Invalid difficulty '{question_data['difficulty']}': {question_data.get('id', 'unknown')}")
            return False
        
        return True
    
    def validate_reading_comprehension(self, reading_data: Dict[str, Any]) -> bool:
        """Validate that a reading comprehension item has all required fields."""
        required_fields = ['passage', 'questions']
        
        # Check required fields exist
        for field in required_fields:
            if field not in reading_data or not reading_data[field]:
                logger.warning(f"Reading comprehension missing required field '{field}'")
                return False
        
        # Validate passage is meaningful
        passage_text = reading_data['passage'].strip()
        if len(passage_text) < 50:  # Passages should be substantial
            logger.warning(f"Passage text too short ({len(passage_text)} chars)")
            return False
        
        # Validate questions
        questions = reading_data['questions']
        if not isinstance(questions, list) or len(questions) == 0:
            logger.warning("No questions found for reading passage")
            return False
        
        # Validate each question
        for i, question in enumerate(questions):
            if not self.validate_reading_question(question, i):
                return False
        
        return True
    
    def validate_reading_question(self, question_data: Dict[str, Any], index: int) -> bool:
        """Validate a single reading comprehension question."""
        required_fields = ['question', 'choices', 'answer']
        
        # Check required fields
        for field in required_fields:
            if field not in question_data or not question_data[field]:
                logger.warning(f"Reading question {index} missing required field '{field}'")
                return False
        
        # Validate question text
        question_text = question_data['question'].strip()
        if len(question_text) < 10:
            logger.warning(f"Reading question {index} text too short ({len(question_text)} chars)")
            return False
        
        # Validate choices
        choices = question_data.get('choices', [])
        if len(choices) < 2:
            logger.warning(f"Reading question {index} has insufficient choices ({len(choices)})")
            return False
        
        # Validate answer
        answer = question_data['answer']
        if not isinstance(answer, int) or answer < 1 or answer > len(choices):
            logger.warning(f"Reading question {index} invalid answer index {answer} for {len(choices)} choices")
            return False
        
        # Validate explanation if present
        if 'explanation' in question_data and question_data['explanation']:
            explanation_text = str(question_data['explanation']).strip()
            if len(explanation_text) < 5:
                logger.warning(f"Reading question {index} explanation too short")
                return False
        
        return True

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text using Sentence-Transformers."""
        try:
            # Use Sentence-Transformers for 384-dim embeddings
            embedding = self.embedding_model.encode(text).tolist()
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    def upload_math_verbal_question(self, question_data: Dict[str, Any], source_file: str, filename: str = None) -> str:
        """Upload a math or verbal question to ssat_questions table."""
        try:
            # Validate question data first
            if not self.validate_math_verbal_question(question_data):
                logger.error(f"Skipping invalid question: {question_data.get('id', 'unknown')}")
                return None
            
            # Prepare question text for embedding
            embedding_text = question_data['question']
            
            # Generate embedding
            embedding = self.generate_embedding(embedding_text)
            
            # Prepare question data for new schema
            # Make ID unique by adding short file prefix
            file_prefix = self._get_short_file_prefix(filename)
            unique_id = f"{file_prefix}_{question_data['id']}"
            
            question_insert_data = {
                'id': unique_id,
                'source_file': source_file,
                'section': question_data['section'],
                'subsection': question_data['subsection'],
                'question': question_data['question'],
                'choices': question_data.get('choices', []),
                'answer': question_data['answer'],
                'explanation': question_data['explanation']['text'] if isinstance(question_data['explanation'], dict) else question_data['explanation'],
                'difficulty': question_data['difficulty'],
                'tags': question_data.get('tags', []),
                'visual_description': question_data.get('visual_description'),
                'embedding': embedding
            }
            
            # Insert question (upsert to handle duplicates)
            response = self.supabase.table('ssat_questions').upsert(question_insert_data).execute()
            return unique_id
            
        except Exception as e:
            logger.error(f"Failed to upload math/verbal question {question_data.get('id', 'unknown')}: {e}")
            raise
    
    def upload_reading_passage_and_questions(self, reading_data: Dict[str, Any], source_file: str) -> List[str]:
        """Upload a reading passage and its questions to separate tables."""
        try:
            # Validate reading comprehension data first
            if not self.validate_reading_comprehension(reading_data):
                logger.error(f"Skipping invalid reading comprehension from {source_file}")
                return []
            
            uploaded_ids = []
            
            # Generate unique passage ID with short file prefix
            file_prefix = self._get_short_file_prefix(os.path.basename(source_file))
            passage_id = f"{file_prefix}_PASS-{str(uuid.uuid4())[:6]}"
            
            # Prepare passage text for embedding
            passage_text = reading_data['passage']
            passage_embedding = self.generate_embedding(passage_text)
            
            # Extract passage type from questions structure
            passage_type = reading_data.get('subsection', 'General')
            
            # Insert passage
            passage_data = {
                'id': passage_id,
                'source_file': source_file,
                'passage': passage_text,
                'passage_type': passage_type,
                'embedding': passage_embedding,
                'tags': reading_data.get('tags', [])
            }
            
            response = self.supabase.table('reading_passages').upsert(passage_data).execute()
            logger.info(f"Uploaded passage: {passage_id}")
            
            # Upload each question for this passage
            if 'questions' in reading_data:
                for i, question in enumerate(reading_data['questions']):
                    question_id = f"{passage_id}-Q{i+1}"
                    
                    # Generate embedding for question
                    question_embedding = self.generate_embedding(question['question'])
                    
                    question_data = {
                        'id': question_id,
                        'passage_id': passage_id,
                        'question': question['question'],
                        'choices': question.get('choices', []),
                        'answer': question['answer'],
                        'explanation': question.get('explanation', ''),
                        'difficulty': reading_data.get('difficulty', 'Medium'),
                        'tags': reading_data.get('tags', []),
                        'visual_description': question.get('visual_description'),
                        'embedding': question_embedding
                    }
                    
                    response = self.supabase.table('reading_questions').upsert(question_data).execute()
                    uploaded_ids.append(question_id)
            
            return uploaded_ids
            
        except Exception as e:
            logger.error(f"Failed to upload reading passage: {e}")
            raise
    
    def upload_writing_prompt(self, question_data: Dict[str, Any], source_file: str, filename: str = None) -> str:
        """Upload a writing prompt to the writing_prompts table."""
        try:
            # Prepare prompt text for embedding
            prompt_text = question_data.get('prompt', question_data.get('question', ''))
            embedding = self.generate_embedding(prompt_text)
            
            # Prepare writing prompt data with unique ID
            file_prefix = self._get_short_file_prefix(filename)
            unique_id = f"{file_prefix}_{question_data['id']}"
            
            prompt_insert_data = {
                'id': unique_id,
                'source_file': source_file,
                'prompt': prompt_text,
                'visual_description': question_data.get('visual_description'),
                'embedding': embedding,
                'tags': question_data.get('tags', [])
            }
            
            # Insert writing prompt (upsert to handle duplicates)
            response = self.supabase.table('writing_prompts').upsert(prompt_insert_data).execute()
            return unique_id
            
        except Exception as e:
            logger.error(f"Failed to upload writing prompt {question_data.get('id', 'unknown')}: {e}")
            raise
    
    def upload_json_file(self, json_file_path: str) -> Dict[str, Any]:
        """Upload all questions from a JSON file using the new schema."""
        try:
            logger.info(f"Processing file: {json_file_path}")
            
            # Load JSON data
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            filename = os.path.basename(json_file_path)
            file_basename = os.path.splitext(filename)[0]
            source_file = data['exam_info']['source']
            
            # Upload counters
            uploaded_math_verbal = 0
            uploaded_reading_questions = 0
            uploaded_writing_prompts = 0
            failed_count = 0
            
            for question in tqdm(data['questions'], desc=f"Uploading from {filename}"):
                try:
                    section = question.get('section', '')
                    
                    # Check if this is a reading comprehension question
                    if section == 'Reading' and 'passage' in question:
                        # This is a reading comprehension question with passage
                        uploaded_ids = self.upload_reading_passage_and_questions(question, source_file)
                        uploaded_reading_questions += len(uploaded_ids)
                        
                    elif section == 'Writing' or 'prompt' in question:
                        # This is a writing prompt
                        self.upload_writing_prompt(question, source_file, file_basename)
                        uploaded_writing_prompts += 1
                        
                    elif section in ['Quantitative', 'Verbal']:
                        # This is a math or verbal question
                        self.upload_math_verbal_question(question, source_file, file_basename)
                        uploaded_math_verbal += 1
                        
                    else:
                        logger.warning(f"Unknown question type: {section} for question {question.get('id', 'unknown')}")
                        failed_count += 1
                        
                except Exception as e:
                    logger.error(f"Failed to upload question {question.get('id', 'unknown')}: {e}")
                    failed_count += 1
            
            return {
                'file': filename,
                'uploaded_math_verbal': uploaded_math_verbal,
                'uploaded_reading_questions': uploaded_reading_questions,
                'uploaded_writing_prompts': uploaded_writing_prompts,
                'failed': failed_count,
                'total': len(data['questions'])
            }
            
        except Exception as e:
            logger.error(f"Failed to process file {json_file_path}: {e}")
            raise

def main():
    """Main function to upload all JSON files."""
    # Load environment variables  
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent / "src"))
    from ssat.config import settings
    
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env file")
        return
    
    print("Using local Sentence-Transformers model for embeddings")
    
    # Initialize uploader
    uploader = SupabaseUploader(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_KEY
    )
    
    # Find all JSON files
    extracted_dir = Path("data/extracted")
    json_files = list(extracted_dir.glob("*-Gemini.json")) + list(extracted_dir.glob("*-Deepseek.json")) + list(extracted_dir.glob("*-OpenAI.json"))
    
    if not json_files:
        print("No JSON files found in data/extracted directory")
        return
    
    print(f"Found {len(json_files)} JSON files to upload")
    
    # Upload each file
    results = []
    for json_file in json_files:
        try:
            result = uploader.upload_json_file(str(json_file))
            results.append(result)
            print(f"✓ {result['file']}: {result['uploaded_math_verbal']} math/verbal, {result['uploaded_reading_questions']} reading, {result['uploaded_writing_prompts']} writing, {result['failed']} failed")
        except Exception as e:
            print(f"✗ {json_file.name}: Failed - {e}")
            results.append({
                'file': json_file.name,
                'uploaded_math_verbal': 0,
                'uploaded_reading_questions': 0,
                'uploaded_writing_prompts': 0,
                'failed': 0,
                'total': 0,
                'error': str(e)
            })
    
    # Print summary
    print("\n=== UPLOAD SUMMARY ===")
    total_math_verbal = sum(r['uploaded_math_verbal'] for r in results)
    total_reading = sum(r['uploaded_reading_questions'] for r in results)
    total_writing_prompts = sum(r['uploaded_writing_prompts'] for r in results)
    total_failed = sum(r['failed'] for r in results)
    total_processed = sum(r['total'] for r in results)
    total_uploaded = total_math_verbal + total_reading + total_writing_prompts
    
    print(f"Total items processed: {total_processed}")
    print(f"Successfully uploaded Math/Verbal questions: {total_math_verbal}")
    print(f"Successfully uploaded Reading questions: {total_reading}")
    print(f"Successfully uploaded Writing prompts: {total_writing_prompts}")
    print(f"Total uploaded: {total_uploaded}")
    print(f"Failed: {total_failed}")
    print(f"Success rate: {(total_uploaded/total_processed*100):.1f}%" if total_processed > 0 else "N/A")
    
    # Print breakdown by file
    print(f"\n=== BREAKDOWN BY FILE ===")
    for result in results:
        if 'error' not in result:
            print(f"{result['file']}: {result['uploaded_math_verbal']} math/verbal, {result['uploaded_reading_questions']} reading, {result['uploaded_writing_prompts']} writing")
        else:
            print(f"{result['file']}: FAILED - {result['error']}")

if __name__ == "__main__":
    main()