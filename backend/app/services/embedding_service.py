"""Service for generating embeddings for AI content."""

from typing import List, Optional
import numpy as np
from loguru import logger

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not available. Embedding generation will be skipped.")


class EmbeddingService:
    """Service for generating embeddings for text content."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the embedding model."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.warning("Sentence transformers not available. Embeddings will not be generated.")
            return
        
        try:
            # Add timeout and retry for model initialization
            import socket
            # Set a reasonable timeout for model downloading
            original_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(30)  # 30 second timeout
            
            try:
                self.model = SentenceTransformer(self.model_name)
                logger.info(f"Initialized embedding model: {self.model_name}")
            finally:
                # Restore original timeout
                socket.setdefaulttimeout(original_timeout)
                
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            logger.warning("Continuing without embeddings - they will be set to None")
            self.model = None
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text."""
        if not self.model or not text.strip():
            return None
        
        try:
            embedding = self.model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding for text: {e}")
            return None
    
    def generate_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for a list of texts."""
        if not self.model or not texts:
            return [None] * len(texts)
        
        try:
            # Filter out empty texts but keep track of indices
            valid_texts = []
            valid_indices = []
            
            for i, text in enumerate(texts):
                if text and text.strip():
                    valid_texts.append(text)
                    valid_indices.append(i)
            
            if not valid_texts:
                return [None] * len(texts)
            
            # Generate embeddings for valid texts
            embeddings = self.model.encode(valid_texts)
            
            # Map back to original indices
            result = [None] * len(texts)
            for i, embedding in enumerate(embeddings):
                original_index = valid_indices[i]
                result[original_index] = embedding.tolist()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            return [None] * len(texts)
    
    def generate_question_embedding(self, question: str, choices: List[str] = None) -> Optional[List[float]]:
        """Generate embedding for a question, optionally including choices."""
        if not question.strip():
            return None
        
        # Combine question with choices for better semantic representation
        combined_text = question
        if choices:
            choices_text = " ".join([f"({chr(65+i)}) {choice}" for i, choice in enumerate(choices)])
            combined_text = f"{question} {choices_text}"
        
        return self.generate_embedding(combined_text)
    
    def is_available(self) -> bool:
        """Check if embedding generation is available."""
        return self.model is not None


# Global embedding service instance
embedding_service = EmbeddingService()