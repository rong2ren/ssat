"""Service for generating embeddings for AI content."""

import threading
from typing import List, Optional
import numpy as np
from loguru import logger

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("Sentence transformers not available. Install with: pip install sentence-transformers")

class EmbeddingService:
    """Service for generating embeddings for text content."""
    
    # Backup models with SAME dimensions (384) for consistency
    # All models are 384-dimensional to ensure database compatibility
    BACKUP_MODELS = [
        "all-MiniLM-L12-v2",        # 120MB, 384 dimensions - Better quality, same dimensions
        "paraphrase-MiniLM-L6-v2",  # 90MB, 384 dimensions - Good for paraphrasing, same dimensions
    ]
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self._lock = threading.Lock()  # Thread safety for embedding generation
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the embedding model with fallback options."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.warning("Sentence transformers not available. Embeddings will not be generated.")
            return
        
        # Create list of models to try: primary model first, then ALL backup models
        # This ensures we try all available models regardless of which one is primary
        models_to_try = [self.model_name]
        models_to_try.extend(self.BACKUP_MODELS)
        
        # Remove duplicates while preserving order (primary model first)
        seen = set()
        unique_models_to_try = []
        for model in models_to_try:
            if model not in seen:
                seen.add(model)
                unique_models_to_try.append(model)
        
        # Track if we've seen network errors to avoid trying all models
        network_error_seen = False
        
        for model_name in unique_models_to_try:
            try:
                logger.info(f"Attempting to initialize embedding model: {model_name}")
                
                # Add timeout and retry for model initialization
                import socket
                # Set a reasonable timeout for model downloading
                original_timeout = socket.getdefaulttimeout()
                socket.setdefaulttimeout(30)  # 30 second timeout
                
                try:
                    self.model = SentenceTransformer(model_name)
                    logger.info(f"✅ Successfully initialized embedding model: {model_name}")
                    self.model_name = model_name  # Update to the actual model that worked
                    return  # Success, exit the loop
                finally:
                    # Restore original timeout
                    socket.setdefaulttimeout(original_timeout)
                    
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Failed to initialize embedding model '{model_name}': {e}")
                
                # Check if this is a network error
                if "Connection reset" in error_msg or "couldn't connect" in error_msg or "huggingface.co" in error_msg:
                    network_error_seen = True
                    logger.warning(f"Network error detected. This will likely affect all models.")
                    # If we've seen a network error, don't waste time trying more models
                    if network_error_seen and len(unique_models_to_try) > 1:
                        logger.error("❌ Network connectivity issue detected. Skipping remaining models.")
                        break
                
                continue  # Try the next model
        
        # If we get here, all models failed
        logger.error("❌ All embedding models failed to initialize")
        logger.warning("Continuing without embeddings - they will be set to None")
        self.model = None
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text (thread-safe)."""
        if not self.model or not text.strip():
            return None
        
        try:
            # Use lock to ensure thread safety for model.encode()
            with self._lock:
                embedding = self.model.encode(text)
                return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding for text: {e}")
            return None
    
    def generate_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for a list of texts (thread-safe)."""
        if not self.model or not texts:
            return [None] * len(texts)
        
        try:
            # Filter out empty texts but keep track of indices
            valid_texts: List[str] = []
            valid_indices: List[int] = []
            
            for i, text in enumerate(texts):
                if text and text.strip():
                    valid_texts.append(text)
                    valid_indices.append(i)
            
            if not valid_texts:
                return [None] * len(texts)
            
            # Use lock to ensure thread safety for model.encode()
            with self._lock:
                # Generate embeddings for valid texts
                embeddings = self.model.encode(valid_texts)
            
            # Map back to original indices
            result: List[Optional[List[float]]] = [None] * len(texts)
            for i, embedding in enumerate(embeddings):
                original_index = valid_indices[i]
                result[original_index] = embedding.tolist()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            return [None] * len(texts)
    
    def generate_question_embedding(self, question: str, choices: Optional[List[str]] = None) -> Optional[List[float]]:
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
    
    def get_available_models(self) -> List[str]:
        """Get list of models that might be available (cached locally)."""
        import os
        from pathlib import Path
        
        # Check if sentence-transformers cache directory exists
        cache_dir = Path.home() / ".cache" / "torch" / "sentence_transformers"
        if not cache_dir.exists():
            return []
        
        # Look for cached models
        available_models = []
        for model_name in [self.model_name] + self.BACKUP_MODELS:
            model_dir = cache_dir / model_name
            if model_dir.exists():
                available_models.append(model_name)
        
        return available_models
    
    def get_model_info(self) -> dict:
        """Get information about the current embedding model."""
        if not self.model:
            return {
                "status": "unavailable",
                "model_name": None,
                "dimensions": None,
                "error": "No model loaded"
            }
        
        try:
            # Get embedding dimensions without running the model
            # All our models are 384-dimensional for consistency
            if any(name in self.model_name for name in ["all-MiniLM-L6", "all-MiniLM-L12", "paraphrase-MiniLM-L6"]):
                dimensions = 384
            else:
                # Fallback: try to get from model config if available
                try:
                    dimensions = self.model.get_sentence_embedding_dimension()
                except:
                    dimensions = "unknown"
            
            # Check if model is compatible with database (384 dimensions expected)
            is_compatible = dimensions == 384
            
            return {
                "status": "available",
                "model_name": self.model_name,
                "dimensions": dimensions,
                "model_type": "sentence-transformers",
                "database_compatible": is_compatible,
                "compatibility_note": "Database expects 384-dimensional embeddings" if not is_compatible else "Fully compatible"
            }
        except Exception as e:
            return {
                "status": "error",
                "model_name": self.model_name,
                "dimensions": None,
                "error": str(e)
            }


# Thread-safe singleton implementation
_embedding_service_instance: Optional[EmbeddingService] = None
_embedding_service_lock = threading.Lock()

def get_embedding_service() -> EmbeddingService:
    """Get the global singleton instance of EmbeddingService (thread-safe)."""
    global _embedding_service_instance
    if _embedding_service_instance is None:
        with _embedding_service_lock:
            # Double-check pattern to prevent race conditions
            if _embedding_service_instance is None:
                _embedding_service_instance = EmbeddingService()
    return _embedding_service_instance