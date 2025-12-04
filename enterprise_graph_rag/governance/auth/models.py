from pydantic import BaseModel, Field
from typing import List, Optional

class UserIdentity(BaseModel):
    """Represents an authenticated user's context."""
    user_id: str
    email: str
    department: str = Field(default="general")
    roles: List[str] = Field(default_factory=list)
    
    class Config:
        frozen = True # Immutable