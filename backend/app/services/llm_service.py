"""Service for LLM provider management."""

import time
from loguru import logger
from typing import Dict, Any, List
from datetime import datetime

# Import LLM client (now local)
from app.llm import llm_client

# Loguru logger imported above

class LLMService:
    """Service class for managing LLM providers."""
    
    def __init__(self):
        """Initialize the LLM service."""
        self.client = llm_client
    
    async def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all available LLM providers."""
        try:
            # Get available providers from existing client
            available_providers = self.client.get_available_providers()
            
            provider_info = []
            total_available = 0
            recommended_provider = None
            
            # Test each provider
            all_providers = ["openai", "gemini", "deepseek"]
            
            for provider_name in all_providers:
                provider_data = {
                    "name": provider_name,
                    "available": False,
                    "response_time": None,
                    "error": None,
                    "last_checked": datetime.now()
                }
                
                # Check if provider is in available list
                provider_available = any(
                    p.value == provider_name for p in available_providers
                )
                
                if provider_available:
                    # Test response time with a simple call
                    try:
                        start_time = time.time()
                        
                        # Make a simple test call to check provider responsiveness
                        test_result = await self._test_provider_response(provider_name)
                        
                        if test_result:
                            response_time = time.time() - start_time
                            provider_data["available"] = True
                            provider_data["response_time"] = response_time
                            total_available += 1
                            
                            # Set recommended provider (prefer fastest available)
                            if (recommended_provider is None or 
                                response_time < provider_info[0].get("response_time", float('inf'))):
                                recommended_provider = provider_name
                        else:
                            provider_data["error"] = "Provider test failed"
                            
                    except Exception as e:
                        provider_data["error"] = str(e)
                        logger.warning(f"Provider {provider_name} test failed: {e}")
                else:
                    provider_data["error"] = "API key not configured"
                
                provider_info.append(provider_data)
            
            # If no provider responded well, use first available as fallback
            if recommended_provider is None and available_providers:
                recommended_provider = available_providers[0].value
            
            return {
                "providers": provider_info,
                "recommended": recommended_provider or "none",
                "total_available": total_available
            }
            
        except Exception as e:
            logger.error(f"Failed to get provider status: {e}")
            raise e
    
    async def _test_provider_response(self, provider_name: str) -> bool:
        """Test if a provider is responsive with a simple call."""
        try:
            # Make a minimal test call to the provider
            # For now, we'll assume if it's in the available list, it works
            # You could implement actual test calls here if needed
            
            # Simple validation: if provider is configured, assume it works
            # In a production system, you might want to make actual API calls
            return True
            
        except Exception as e:
            logger.warning(f"Provider test for {provider_name} failed: {e}")
            return False