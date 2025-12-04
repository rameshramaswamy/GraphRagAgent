from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class AgentSettings(BaseSettings):
    # Model Config
    OPENAI_API_KEY: str = Field(..., description="Required for LLM")
    AGENT_MODEL: str = "gpt-4o"
    
    # Persistence (Postgres)
    POSTGRES_DB: str = "agent_state"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    
    # Observability (LangSmith)
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str = "enterprise-graph-agent"

    # Business Logic
    MAX_RETRIES: int = 2
    CONTEXT_WINDOW_SIZE: int = 10 
    
    # Optimization: Parallelization
    MAX_CONCURRENCY: int = 5

    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 3600  # 1 hour
    
    @property
    def POSTGRES_URI(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

agent_settings = AgentSettings()