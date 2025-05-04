"""OpenAI LLM client utilities for generating SSAT questions."""

from typing import Any, Dict, Optional
import time

import openai
from .config import settings
from loguru import logger

client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

def call_openai_chat(
    system_message: str,
    prompt: str,
    model: str = "gpt-3.5-turbo",
    response_format: Dict[str, Any] = {"type": "json_object"},
    temperature: float = 0.4,
    max_tokens: int = 2000,
    max_retries: int = 3,
    retry_delay: float = 1.0,
) -> Optional[str]:
    """
    Generic helper to call OpenAI Chat API and return the assistant's message.
    """
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
                response_format=response_format
            )
            content = response.choices[0].message.content.strip()
            logger.debug(f"OpenAI response: {content}")
            return content
        except openai.RateLimitError as e:
            logger.warning(f"Rate limit hit (attempt {attempt+1}/{max_retries}): {str(e)}")
        except openai.APIError as e:
            logger.warning(f"API error (attempt {attempt+1}/{max_retries}): {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return None

        # If exception occurred and retry is allowed
        if attempt < max_retries - 1:
            time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
        else:
            logger.error(f"Failed after {max_retries} attempts.")
            return None


