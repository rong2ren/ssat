"""PDF processing utilities for SSAT questions."""

# Standard library imports
import logging
import re
from typing import Any, Dict, List

# Third-party imports
import fitz  # PyMuPDF
import supabase
from sentence_transformers import SentenceTransformer
from transformers import pipeline

# Local imports
from .config import settings
from .models import QuestionType, DifficultyLevel

logger = logging.getLogger(__name__)

class PDFProcessor:
    """Process SSAT PDFs to extract and classify questions."""
    
    def __init__(self):
        """Initialize the PDF processor with required models and clients."""
        try:
            self.client = supabase.create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            self.embedder = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
            self.classifier = pipeline("zero-shot-classification", 
                                    model="facebook/bart-large-mnli")
        except Exception as e:
            logger.error(f"Failed to initialize PDFProcessor: {e}")
            raise
            
        # SSAT-specific labels
        self.labels = {
            "type": [qt.value for qt in QuestionType],
            "difficulty": [dl.value for dl in DifficultyLevel],
            "topic": ["arithmetic", "geometry", "vocabulary", "comprehension", "algebra"]
        }

    def extract_text(self, pdf_path: str) -> List[Dict]:
        """Extract questions with page numbers from PDF.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of dictionaries containing question text and metadata
        """
        try:
            doc = fitz.open(pdf_path)
            questions = []
            
            for page_num, page in enumerate(doc):
                text = page.get_text()
                questions += self._parse_questions(text, page_num)
                
            return questions
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            raise

    def _parse_questions(self, text: str, page_num: int) -> List[Dict]:
        """Parse SSAT questions from text.
        
        Args:
            text: Raw text from PDF
            page_num: Page number
            
        Returns:
            List of parsed questions
        """
        questions = []
        # Split by common question patterns
        raw_questions = re.split(r'(Question\s\d+:|\(\d+\)\s)', text)
        
        for i in range(1, len(raw_questions), 2):
            question = {
                "number": raw_questions[i].strip(),
                "text": self._clean_text(raw_questions[i+1]),
                "page": page_num + 1
            }
            questions.append(question)
            
        return questions

    def _clean_text(self, text: str) -> str:
        """Clean SSAT question text.
        
        Args:
            text: Raw question text
            
        Returns:
            Cleaned text
        """
        # Remove headers/footers
        text = re.sub(r'SSAT\s*Elementary\s*Level\s*Practice\s*Test.*', '', text)
        # Fix common OCR errors
        text = re.sub(r'([a-z])(\d)', r'\1 \2', text)  # Add space between letters and numbers
        return text.strip()

    def classify_question(self, text: str) -> Dict:
        """Classify question using SSAT-specific taxonomy.
        
        Args:
            text: Question text
            
        Returns:
            Dictionary with classification results
        """
        try:
            return {
                "type": self._predict_label(text, "type"),
                "difficulty": self._predict_label(text, "difficulty"),
                "topic": self._predict_label(text, "topic"),
                "embedding": self.embedder.encode(text).tolist()
            }
        except Exception as e:
            logger.error(f"Failed to classify question: {e}")
            raise

    def _predict_label(self, text: str, label_type: str) -> str:
        """Perform zero-shot classification.
        
        Args:
            text: Text to classify
            label_type: Type of label to predict
            
        Returns:
            Predicted label
        """
        try:
            result = self.classifier(text, self.labels[label_type])
            return result["labels"][0]
        except Exception as e:
            logger.error(f"Failed to predict label: {e}")
            raise

    def upload_to_supabase(self, questions: List[Dict], pdf_name: str) -> None:
        """Upload questions to Supabase.
        
        Args:
            questions: List of question dictionaries
            pdf_name: Name of the source PDF
        """
        try:
            records = []
            for q in questions:
                records.append({
                    "raw_text": q["text"],
                    "metadata": {
                        "type": q["type"],
                        "difficulty": q["difficulty"],
                        "topic": q["topic"],
                        "page": q["page"]
                    },
                    "embedding": q["embedding"],
                    "source_pdf": pdf_name
                })
                
            self.client.table("ssat_questions").insert(records).execute()
            logger.info(f"Successfully uploaded {len(questions)} questions to Supabase")
        except Exception as e:
            logger.error(f"Failed to upload to Supabase: {e}")
            raise

# Usage
processor = PDFProcessor()

# 1. Process PDF
questions = processor.extract_text("your_ssat.pdf")

# 2. Classify and add embeddings
for q in questions:
    q.update(processor.classify_question(q["text"]))

# 3. Upload to Supabase
processor.upload_to_supabase(questions, "sample_test.pdf")