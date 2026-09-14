from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.schemas.message import MessageRead


class SessionCreate(BaseModel):
    title: Optional[str] = "New Growth Conversation"
    session_metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionUpdate(BaseModel):
    title: Optional[str] = None
    session_metadata: Optional[Dict[str, Any]] = None


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    session_metadata: Dict[str, Any] = Field(default_factory=dict)
    message_count: int = 0


class SessionDetailRead(SessionRead):
    messages: List[MessageRead] = []
