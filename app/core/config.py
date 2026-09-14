from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # LLM Configuration
    LLM_PROVIDER: str = Field(default="ollama", description="Active LLM provider: ollama, gemini, claude, or openai")
    
    # Ollama settings
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", description="Ollama API base URL")
    OLLAMA_MODEL: str = Field(default="llama3.1:8b", description="Ollama model name")
    
    # Google Gemini cloud provider
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Google Gemini API Key")
    GEMINI_MODEL: str = Field(default="gemini-3.5-flash-lite", description="Gemini model: gemini-3.5-flash-lite, gemini-3.8-flash, gemini-3.7-flash, gemini-2.5-flash, gemini-2.5-pro")

    # Cloud providers (Anthropic & OpenAI)
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Anthropic API Key")
    ANTHROPIC_MODEL: str = Field(default="claude-3-5-sonnet-20241022", description="Claude model identifier")
    
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API Key")
    OPENAI_MODEL: str = Field(default="gpt-4o", description="OpenAI model identifier")

    # Database & pgvector
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/lenny_assistant",
        description="Async database connection URL"
    )
    
    # Embedding and RAG
    EMBEDDING_MODEL: str = Field(default="BAAI/bge-small-en-v1.5", description="FastEmbed embedding model")
    SIMILARITY_THRESHOLD: float = Field(default=0.45, description="Minimum cosine similarity for RAG retrieval")
    TOP_K_RESULTS: int = Field(default=5, description="Number of transcript chunks to retrieve")

    # App & Networking
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def active_model(self) -> str:
        provider = self.LLM_PROVIDER.lower()
        if provider == "ollama":
            return self.OLLAMA_MODEL
        elif provider == "gemini":
            return self.GEMINI_MODEL
        elif provider == "claude":
            return self.ANTHROPIC_MODEL
        elif provider == "openai":
            return self.OPENAI_MODEL
        return "unknown"

    @field_validator("LLM_PROVIDER")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        allowed = {"ollama", "gemini", "claude", "openai"}
        v_clean = v.lower().strip()
        if v_clean not in allowed:
            raise ValueError(f"Invalid LLM_PROVIDER '{v}'. Allowed providers are: {allowed}")
        return v_clean


settings = Settings()
