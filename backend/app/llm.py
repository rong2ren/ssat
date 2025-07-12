"""Multi-provider LLM client utilities for generating SSAT questions."""

from typing import Any, Dict, Optional, Union
import time
from enum import Enum

from loguru import logger
from .settings import settings

# Supported LLM providers
class LLMProvider(Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"

class LLMClient:
    """Unified LLM client supporting OpenAI, Gemini, and DeepSeek providers."""
    
    def __init__(self):
        self.clients = {}
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize available clients based on API keys."""
        
        # OpenAI
        if settings.OPENAI_API_KEY:
            try:
                import openai
                self.clients[LLMProvider.OPENAI] = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info("OpenAI client initialized")
            except ImportError:
                logger.warning("OpenAI package not installed. Run: pip install openai")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")
        
        # Google Gemini
        if settings.GEMINI_API_KEY:
            try:
                import google.generativeai as genai
                from google.generativeai.generative_models import GenerativeModel
                from google.generativeai.client import configure
                configure(api_key=settings.GEMINI_API_KEY)
                self.clients[LLMProvider.GEMINI] = GenerativeModel('gemini-1.5-pro')
                logger.info("Gemini client initialized")
            except ImportError:
                logger.warning("Google Generative AI package not installed. Run: pip install google-generativeai")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")
        
        # DeepSeek (uses OpenAI-compatible API)
        if settings.DEEPSEEK_API_KEY:
            try:
                import openai
                self.clients[LLMProvider.DEEPSEEK] = openai.OpenAI(
                    api_key=settings.DEEPSEEK_API_KEY,
                    base_url="https://api.deepseek.com"
                )
                logger.info("DeepSeek client initialized")
            except ImportError:
                logger.warning("OpenAI package not installed. Run: pip install openai")
            except Exception as e:
                logger.warning(f"Failed to initialize DeepSeek client: {e}")
    
    def get_available_providers(self) -> list[LLMProvider]:
        """Get list of available providers."""
        return list(self.clients.keys())
    
    def call_llm(
        self,
        provider: Union[LLMProvider, str],
        system_message: str,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.4,
        max_tokens: int = 2000,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> Optional[str]:
        """Call the specified LLM provider."""
        
        # Convert string to enum if needed
        if isinstance(provider, str):
            try:
                provider = LLMProvider(provider.lower())
            except ValueError:
                raise ValueError(f"Unsupported provider: {provider}")
        
        if provider not in self.clients:
            available = [p.value for p in self.get_available_providers()]
            raise ValueError(f"Provider {provider.value} not available. Available providers: {available}")
        
        logger.info(f"Calling {provider.value} LLM")
        
        # Route to appropriate provider
        if provider == LLMProvider.OPENAI:
            return self._call_openai(system_message, prompt, model, temperature, max_tokens, max_retries, retry_delay)
        elif provider == LLMProvider.GEMINI:
            return self._call_gemini(system_message, prompt, model, temperature, max_tokens, max_retries, retry_delay)
        elif provider == LLMProvider.DEEPSEEK:
            return self._call_deepseek(system_message, prompt, model, temperature, max_tokens, max_retries, retry_delay)
        else:
            raise ValueError(f"Provider {provider.value} not implemented")
    
    def _call_openai(self, system_message: str, prompt: str, model: Optional[str] = None, 
                    temperature: float = 0.4, max_tokens: int = 2000, max_retries: int = 3, retry_delay: float = 1.0) -> Optional[str]:
        """Call OpenAI API."""
        import openai
        client = self.clients[LLMProvider.OPENAI]
        
        # Set default model if none provided
        if model is None:
            model = "gpt-3.5-turbo"
        
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"}
                )
                content = response.choices[0].message.content.strip()
                logger.debug(f"OpenAI response: {content}")
                return content
            except openai.RateLimitError as e:
                logger.warning(f"OpenAI rate limit hit (attempt {attempt+1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    logger.error(f"OpenAI failed after {max_retries} rate limit attempts.")
                    return None
            except openai.APIError as e:
                logger.error(f"OpenAI API error (no retry): {str(e)}")
                return None
            except Exception as e:
                logger.error(f"OpenAI unexpected error: {str(e)}")
                return None
        
        return None
    
    def _call_gemini(self, system_message: str, prompt: str, model: Optional[str] = None, 
                    temperature: float = 0.4, max_tokens: int = 2000, max_retries: int = 3, retry_delay: float = 1.0) -> Optional[str]:
        """Call Google Gemini API."""
        # For Gemini, we need to create a new model instance if a different model is specified
        if model is None:
            model_instance = self.clients[LLMProvider.GEMINI]
        else:
            import google.generativeai as genai
            from google.generativeai.generative_models import GenerativeModel
            model_instance = GenerativeModel(model)
        
        # Combine system message and prompt for Gemini
        full_prompt = f"{system_message}\n\n{prompt}\n\nPlease respond with a valid JSON object only, no other text."
        
        for attempt in range(max_retries):
            try:
                response = model_instance.generate_content(
                    full_prompt,
                    generation_config={
                        "temperature": temperature,
                        "max_output_tokens": max_tokens,
                    }
                )
                content = response.text.strip()
                logger.debug(f"Gemini response: {content}")
                return content
            except Exception as e:
                error_str = str(e)
                if "quota" in error_str.lower() or "rate" in error_str.lower():
                    logger.warning(f"Gemini rate limit hit (attempt {attempt+1}/{max_retries}): {error_str}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                    else:
                        logger.error(f"Gemini failed after {max_retries} rate limit attempts.")
                        return None
                else:
                    logger.error(f"Gemini API error (no retry): {error_str}")
                    return None
        
        return None
    
    def _call_deepseek(self, system_message: str, prompt: str, model: Optional[str] = None, 
                      temperature: float = 0.4, max_tokens: int = 2000, max_retries: int = 3, retry_delay: float = 1.0) -> Optional[str]:
        """Call DeepSeek API (OpenAI-compatible)."""
        import openai
        client = self.clients[LLMProvider.DEEPSEEK]
        
        # Set default model if none provided
        if model is None:
            model = "deepseek-chat"
        
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"}
                )
                content = response.choices[0].message.content.strip()
                logger.debug(f"DeepSeek response: {content}")
                return content
            except openai.RateLimitError as e:
                logger.warning(f"DeepSeek rate limit hit (attempt {attempt+1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    logger.error(f"DeepSeek failed after {max_retries} rate limit attempts.")
                    return None
            except openai.APIError as e:
                logger.error(f"DeepSeek API error (no retry): {str(e)}")
                return None
            except Exception as e:
                logger.error(f"DeepSeek unexpected error: {str(e)}")
                return None
        
        return None

# Global LLM client instance
llm_client = LLMClient()



