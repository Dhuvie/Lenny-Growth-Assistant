import uuid
from datetime import datetime, timezone
import json
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator
from app.db.session import Base


class VectorType(TypeDecorator):
    """
    Custom type decorator: uses native pgvector Vector on PostgreSQL,
    and falls back to JSON-serialized Text on SQLite for local test suites.
    """
    impl = Text
    cache_ok = True

    def __init__(self, dim: int = 384, **kwargs):
        super().__init__(**kwargs)
        self.dim = dim

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            try:
                from pgvector.sqlalchemy import Vector
                return dialect.type_descriptor(Vector(self.dim))
            except ImportError:
                return dialect.type_descriptor(Text())
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        if isinstance(value, (list, tuple)):
            return json.dumps(list(value))
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return value
        return value


class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False, default="New Growth Conversation")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    session_metadata = Column(JSON, default=dict, nullable=False)

    messages = relationship("MessageModel", back_populates="session", cascade="all, delete-orphan", order_by="MessageModel.created_at")


class MessageModel(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(32), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    sources = Column(JSON, default=list, nullable=False)
    artifacts = Column(JSON, default=list, nullable=False)
    model_provider = Column(String(64), nullable=False, default="ollama")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    session = relationship("SessionModel", back_populates="messages")


class EpisodeModel(Base):
    __tablename__ = "episodes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slug = Column(String(255), unique=True, nullable=False, index=True)
    title = Column(String(512), nullable=False)
    guest = Column(String(255), nullable=False, index=True)
    youtube_url = Column(String(512), nullable=False)
    video_id = Column(String(64), nullable=False)
    publish_date = Column(String(32), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    duration = Column(String(32), nullable=True)
    view_count = Column(Integer, nullable=True)
    channel = Column(String(128), default="Lenny's Podcast")
    keywords = Column(JSON, default=list, nullable=False)
    indexed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    chunks = relationship("TranscriptChunkModel", back_populates="episode", cascade="all, delete-orphan")


class TranscriptChunkModel(Base):
    __tablename__ = "transcript_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    episode_id = Column(String(36), ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    speaker = Column(String(255), nullable=False)
    start_timestamp = Column(String(32), nullable=False)  # e.g., "00:05:04"
    start_seconds = Column(Integer, nullable=False)       # e.g., 304
    text = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=False, default=0)
    embedding = Column(VectorType(384), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    episode = relationship("EpisodeModel", back_populates="chunks")


# Compound index for chunk ordering
Index("idx_chunk_episode_order", TranscriptChunkModel.episode_id, TranscriptChunkModel.chunk_index)
