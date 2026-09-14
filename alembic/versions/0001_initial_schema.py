"""Initial schema for Lenny Growth Assistant

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-14 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from app.db.models import VectorType

revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pgvector extension if on PostgreSQL
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Sessions table
    op.create_table(
        'sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('session_metadata', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. Messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('sources', sa.JSON(), nullable=False),
        sa.Column('artifacts', sa.JSON(), nullable=False),
        sa.Column('model_provider', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_messages_session_id', 'messages', ['session_id'], unique=False)

    # 4. Episodes table
    op.create_table(
        'episodes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=512), nullable=False),
        sa.Column('guest', sa.String(length=255), nullable=False),
        sa.Column('youtube_url', sa.String(length=512), nullable=False),
        sa.Column('video_id', sa.String(length=64), nullable=False),
        sa.Column('publish_date', sa.String(length=32), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('duration', sa.String(length=32), nullable=True),
        sa.Column('view_count', sa.Integer(), nullable=True),
        sa.Column('channel', sa.String(length=128), nullable=True),
        sa.Column('keywords', sa.JSON(), nullable=False),
        sa.Column('indexed_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_episodes_slug', 'episodes', ['slug'], unique=True)
    op.create_index('idx_episodes_guest', 'episodes', ['guest'], unique=False)

    # 5. Transcript chunks table
    op.create_table(
        'transcript_chunks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('episode_id', sa.String(length=36), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('speaker', sa.String(length=255), nullable=False),
        sa.Column('start_timestamp', sa.String(length=32), nullable=False),
        sa.Column('start_seconds', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=False),
        sa.Column('embedding', VectorType(384), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['episode_id'], ['episodes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_chunks_episode_id', 'transcript_chunks', ['episode_id'], unique=False)
    op.create_index('idx_chunk_episode_order', 'transcript_chunks', ['episode_id', 'chunk_index'], unique=False)

    # 6. HNSW index for pgvector
    if conn.dialect.name == "postgresql":
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw 
            ON transcript_chunks 
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
        """)


def downgrade() -> None:
    op.drop_table('transcript_chunks')
    op.drop_table('episodes')
    op.drop_table('messages')
    op.drop_table('sessions')
