import json
import logging
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text, select, func

from app.core.config import settings
from app.core.logging import log_event

# Configure async engine with connection pooling and pre-ping
engine_kwargs = {
    "pool_pre_ping": True,
    "echo": False,
}

if "sqlite" in settings.DATABASE_URL:
    engine_kwargs = {"echo": False}

async_engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)


class Base(DeclarativeBase):
    pass


async def get_db():
    """FastAPI dependency yielding an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            log_event("DB", f"Database transaction rollback due to error: {e}", level=logging.ERROR)
            raise
        finally:
            await session.close()


async def auto_seed_if_empty(db: AsyncSession):
    """If database is empty, seed foundational episodes from pre-computed bundle."""
    from app.db.models import EpisodeModel, TranscriptChunkModel
    
    ep_count_stmt = select(func.count(EpisodeModel.id))
    res = await db.execute(ep_count_stmt)
    count = res.scalar() or 0
    if count > 0:
        return

    seed_file = Path("data/seed_data/seed_episodes.json")
    if not seed_file.exists():
        log_event("DB", "No pre-computed seed file found at data/seed_data/seed_episodes.json. Ingestion can be triggered via CLI.")
        return

    log_event("DB", "Database is empty. Seeding foundational episodes from seed bundle...")
    try:
        data = json.loads(seed_file.read_text(encoding="utf-8"))
        total_chunks = 0
        for ep_dict in data:
            chunks = ep_dict.pop("chunks", [])
            ep = EpisodeModel(**ep_dict)
            db.add(ep)
            await db.flush()

            chunk_objs = []
            for c in chunks:
                chunk_objs.append(TranscriptChunkModel(
                    episode_id=ep.id,
                    chunk_index=c["chunk_index"],
                    speaker=c["speaker"],
                    start_timestamp=c["start_timestamp"],
                    start_seconds=c["start_seconds"],
                    text=c["text"],
                    token_count=c.get("token_count", len(c["text"]) // 4),
                    embedding=c["embedding"]
                ))
            db.add_all(chunk_objs)
            total_chunks += len(chunk_objs)

        await db.commit()
        log_event("DB", f"Auto-seeding complete: inserted {len(data)} episodes and {total_chunks} chunks.")
    except Exception as e:
        await db.rollback()
        log_event("DB", f"Auto-seeding failed: {e}", level=logging.ERROR)


async def init_db():
    """Initializes database tables, pgvector extension, and seeds foundational episodes."""
    async with async_engine.begin() as conn:
        if "postgresql" in settings.DATABASE_URL:
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                log_event("DB", "pgvector extension verified/created.")
            except Exception as e:
                log_event("DB", f"Could not create vector extension: {e}", level=logging.WARNING)
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        log_event("DB", "Database schema initialized successfully.")

    # Check and perform auto-seed if needed
    async with AsyncSessionLocal() as session:
        await auto_seed_if_empty(session)
