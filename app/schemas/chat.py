from pydantic import BaseModel, Field
from typing import List, Optional
from app.schemas.message import Citation, Artifact


class ChatRequest(BaseModel):
    session_id: str
    content: str = Field(..., min_length=1, description="User prompt or question")
    stream: bool = Field(default=True, description="Whether to stream the response via SSE")
    provider: Optional[str] = Field(default=None, description="Optional override provider: ollama, gemini, claude, openai")
    model: Optional[str] = Field(default=None, description="Optional override model identifier")


class ChatResponse(BaseModel):
    id: str
    session_id: str
    role: str = "assistant"
    content: str
    sources: List[Citation] = []
    artifacts: List[Artifact] = []
    model_provider: str
