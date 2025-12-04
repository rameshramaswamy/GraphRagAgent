from pydantic import BaseModel, Field
from typing import List, Optional

class ChatRequest(BaseModel):
    message: str
    thread_id: str = Field(default_factory=lambda: "default_thread")

class IngestResponse(BaseModel):
    task_id: str
    status: str
    message: str