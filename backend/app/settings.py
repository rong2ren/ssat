from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # BaseSettings is a class that helps manage application settings.
    # It loads environment variables and provides a convenient way to access them.
    # create a subclass called Settings that inherits from BaseSettings
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    
    # LLM Provider API Keys
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"  # optional
    APP_ENV: str = "dev"  # optional, tracks environment (dev/staging/prod)

    class Config:
        # Find .env file relative to this config file (backend/.env)
        # This works regardless of the current working directory
        env_file = Path(__file__).parent.parent / ".env"

settings = Settings()
# instantiate the settings