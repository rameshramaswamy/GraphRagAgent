from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from knowledge_engine.core.config import settings

# Define the Header Key
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    """
    Validates the API Key from the request header.
    In production, check against a DB or Key Vault.
    """
    # For demo, we check against an env var or a hardcoded fallback
    # In 'config.py', add API_SECRET or use a default
    EXPECTED_KEY = getattr(settings, "API_SECRET", "enterprise-secret-key")
    
    if api_key_header == EXPECTED_KEY:
        return api_key_header
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate credentials"
    )