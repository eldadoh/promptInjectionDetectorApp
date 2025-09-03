from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    """Application settings."""
    APP_NAME: str = "Prompt Injection Detector"
    APP_VERSION: str = "0.1.0"
    
    # LLM Provider settings
    DEFAULT_LLM_PROVIDER: str = "openai"
    
    # OpenAI settings
    OPENAI_API_KEY: str
    DEFAULT_MODEL: str = "gpt-4.1-nano"
    DEFAULT_MODEL_VERSION: str = "v1"
    
    # Database settings
    DB_HOST: str = "db"
    DB_NAME: str = "prompt_security"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_PORT: int = 5432
    
    # Default prompt version
    DEFAULT_PROMPT_VERSION: str = "v1"
    
    @property
    def DATABASE_URL(self) -> str:
        """Get the database URL."""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

# Load settings from environment variables
settings = Settings()
