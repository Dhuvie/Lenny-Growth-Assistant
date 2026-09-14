from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class Citation(BaseModel):
    guest: str
    episode_title: str
    episode_slug: str
    start_timestamp: str
    start_seconds: int
    youtube_url: str
    snippet: str
    similarity: float = 0.0


class Artifact(BaseModel):
    id: str
    title: str
    type: str  # 'markdown', 'html', 'react'
    content: str
    word_count: int
    created_at: Optional[datetime] = None


class MessageCreate(BaseModel):
    role: str
    content: str
    sources: List[Citation] = []
    artifacts: List[Artifact] = []
    model_provider: str = "ollama"


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    role: str
    content: str
    sources: List[Citation] = []
    artifacts: List[Artifact] = []
    model_provider: str
    created_at: datetime
