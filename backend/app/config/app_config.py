"""
Centralized application configuration management.

This module provides a clean interface for accessing configuration values
with proper validation and environment-specific handling.
"""

import os
from typing import Optional
from loguru import logger
from app.settings import settings
import threading


class AppConfig:
    """Centralized configuration management for the SSAT application."""
    
    def __init__(self):
        """Initialize the application configuration."""
        self._settings = settings
        self._validate_required_settings()
        logger.info("Application configuration initialized")
    
    def _validate_required_settings(self):
        """Validate that required configuration values are present."""
        required_settings = [
            ("SUPABASE_URL", self._settings.SUPABASE_URL),
            ("SUPABASE_KEY", self._settings.SUPABASE_KEY),
        ]
        
        missing_settings = []
        for name, value in required_settings:
            if not value or value.strip() == "":
                missing_settings.append(name)
        
        if missing_settings:
            raise ValueError(f"Missing required configuration: {', '.join(missing_settings)}")
        
        # Validate that at least one LLM provider is configured
        llm_providers = [
            ("OPENAI_API_KEY", self._settings.OPENAI_API_KEY),
            ("GEMINI_API_KEY", self._settings.GEMINI_API_KEY),
            ("DEEPSEEK_API_KEY", self._settings.DEEPSEEK_API_KEY),
        ]
        
        configured_providers = [name for name, value in llm_providers if value and value.strip()]
        if not configured_providers:
            logger.warning("No LLM providers configured - content generation may not work")
        else:
            logger.info(f"Configured LLM providers: {configured_providers}")
    
    # Database Configuration
    @property
    def supabase_url(self) -> str:
        """Get Supabase URL."""
        return self._settings.SUPABASE_URL
    
    @property
    def supabase_key(self) -> str:
        """Get Supabase service key."""
        return self._settings.SUPABASE_KEY
    
    @property
    def supabase_service_role_key(self) -> str:
        """Get Supabase service role key for admin operations."""
        return self._settings.SUPABASE_SERVICE_ROLE_KEY
    
    # LLM Provider Configuration
    @property
    def openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key."""
        return self._settings.OPENAI_API_KEY if self._settings.OPENAI_API_KEY.strip() else None
    
    @property
    def gemini_api_key(self) -> Optional[str]:
        """Get Gemini API key."""
        return self._settings.GEMINI_API_KEY if self._settings.GEMINI_API_KEY.strip() else None
    
    @property
    def deepseek_api_key(self) -> Optional[str]:
        """Get DeepSeek API key."""
        return self._settings.DEEPSEEK_API_KEY if self._settings.DEEPSEEK_API_KEY.strip() else None
    
    # Application Configuration
    @property
    def app_env(self) -> str:
        """Get application environment."""
        return self._settings.APP_ENV
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_env.lower() in ['dev', 'development', 'local']
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env.lower() in ['prod', 'production']
    
    # Email Configuration
    @property
    def resend_api_key(self) -> Optional[str]:
        """Get Resend API key for email services."""
        return self._settings.RESEND_API if self._settings.RESEND_API.strip() else None
    
    def get_cors_origins(self) -> list[str]:
        """Get CORS allowed origins based on environment."""
        if self.is_production:
            # In production, this should be configured properly
            return [
                "https://yourdomain.com",
                "https://www.yourdomain.com"
            ]
        else:
            # In development, allow all origins
            return ["*"]
    
    def get_database_connection_params(self) -> dict:
        """Get database connection parameters."""
        return {
            "url": self.supabase_url,
            "key": self.supabase_key
        }
    
    def get_admin_database_connection_params(self) -> dict:
        """Get admin database connection parameters."""
        if not self.supabase_service_role_key:
            raise ValueError("Service role key not configured for admin operations")
        
        return {
            "url": self.supabase_url,
            "key": self.supabase_service_role_key
        }
    
    def get_available_llm_providers(self) -> list[str]:
        """Get list of configured LLM providers."""
        providers = []
        
        if self.openai_api_key:
            providers.append("openai")
        if self.gemini_api_key:
            providers.append("gemini")
        if self.deepseek_api_key:
            providers.append("deepseek")
        
        return providers
    
    def __str__(self) -> str:
        """String representation of configuration (safe for logging)."""
        return f"AppConfig(env={self.app_env}, providers={len(self.get_available_llm_providers())})"


# Thread-safe singleton implementation
_app_config_instance: Optional[AppConfig] = None
_app_config_lock = threading.Lock()

def get_app_config() -> AppConfig:
    """Get the global singleton instance of AppConfig (thread-safe)."""
    global _app_config_instance
    if _app_config_instance is None:
        with _app_config_lock:
            # Double-check pattern to prevent race conditions
            if _app_config_instance is None:
                _app_config_instance = AppConfig()
    return _app_config_instance

# Configuration instance removed to prevent duplicate initialization during reloads