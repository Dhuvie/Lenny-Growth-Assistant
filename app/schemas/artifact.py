from pydantic import BaseModel, Field
from datetime import datetime


class ArtifactCreate(BaseModel):
    session_id: str
    title: str = Field(..., min_length=1)
    type: str = Field(default="markdown", description="'markdown' or 'html'")
    content: str = Field(..., min_length=1)


class ArtifactResponse(BaseModel):
    id: str
    session_id: str
    title: str
    type: str
    content: str
    word_count: int
    created_at: datetime
