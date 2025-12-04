from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    APP_NAME: str = "Enterprise GraphRAG"
    ENVIRONMENT: str = Field(default="dev", description="dev, staging, or prod")

    # OpenAI
    OPENAI_API_KEY: str = Field(..., description="Required OpenAI Key")
    OPENAI_MODEL: str = "gpt-4o"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    
    # Resiliency
    MAX_RETRIES: int = 3
    CONNECTION_TIMEOUT: int = 30

    # Optimization: Chunking Strategy
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50

    # Optimization: Ingestion Concurrency
    # Limit parallel LLM requests to avoid RateLimits (429 Errors)
    INGESTION_CONCURRENCY: int = 5 

    ALLOWED_ENTITY_TYPES: List[str] = ["Person", "Organization", "Project", "Location", "Topic", "Document"]
    ALLOWED_RELATION_TYPES: List[str] = ["MANAGES", "REPORTS_TO", "WORKS_ON", "LOCATED_AT", "MENTIONS", "HAS_TOPIC"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()