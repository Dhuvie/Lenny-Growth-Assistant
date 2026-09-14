from typing import List, Optional
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.core.config import settings
from app.core.logging import log_event
from app.rag.embeddings import EmbeddingService
from app.schemas.message import Citation
from app.db.models import EpisodeModel, TranscriptChunkModel


def build_youtube_timestamp_url(base_url: str, start_seconds: int) -> str:
    """
    Constructs a clickable YouTube URL with the exact start second.
    E.g. https://www.youtube.com/watch?v=IHwS2By9UKM&t=26s
    """
    if not base_url:
        return ""
    clean_url = base_url.split("&t=")[0].split("?t=")[0]
    separator = "&" if "?" in clean_url else "?"
    return f"{clean_url}{separator}t={start_seconds}s"


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Computes cosine similarity between two float vectors."""
    vec_a = np.array(a, dtype=np.float32)
    vec_b = np.array(b, dtype=np.float32)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))


class TranscriptRetriever:
    """
    Executes vector cosine similarity search over transcript chunks.
    Supports native pgvector HNSW search on PostgreSQL, with a NumPy
    in-memory fallback for local SQLite testing.
    """

    @classmethod
    async def search(
        cls,
        query: str,
        db: AsyncSession,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None
    ) -> List[Citation]:
        top_k = top_k or settings.TOP_K_RESULTS
        threshold = threshold or settings.SIMILARITY_THRESHOLD

        query_vec = EmbeddingService.embed_query(query)
        if not query_vec:
            log_event("RETRIEVAL", "Empty embedding generated for query", query=query)
            return []

        citations: List[Citation] = []
        is_postgres = "postgresql" in settings.DATABASE_URL

        if is_postgres:
            # Query using native pgvector cosine distance operator (<=>)
            query_str = text("""
                SELECT 
                    c.id,
                    c.speaker,
                    c.start_timestamp,
                    c.start_seconds,
                    c.text,
                    e.title AS episode_title,
                    e.guest,
                    e.slug AS episode_slug,
                    e.youtube_url,
                    1 - (c.embedding <=> :query_vec::vector) AS similarity
                FROM transcript_chunks c
                JOIN episodes e ON c.episode_id = e.id
                WHERE 1 - (c.embedding <=> :query_vec::vector) >= :threshold
                ORDER BY c.embedding <=> :query_vec::vector ASC
                LIMIT :top_k
            """)
            try:
                # Format vector literal for pgvector: '[0.1,0.2,...]'
                vec_literal = "[" + ",".join(str(x) for x in query_vec) + "]"
                result = await db.execute(query_str, {
                    "query_vec": vec_literal,
                    "threshold": threshold,
                    "top_k": top_k
                })
                rows = result.fetchall()
                for row in rows:
                    yt_url = build_youtube_timestamp_url(row.youtube_url, row.start_seconds)
                    citations.append(Citation(
                        guest=row.guest,
                        episode_title=row.episode_title,
                        episode_slug=row.episode_slug,
                        start_timestamp=row.start_timestamp,
                        start_seconds=row.start_seconds,
                        youtube_url=yt_url,
                        snippet=row.text[:300] + "..." if len(row.text) > 300 else row.text,
                        similarity=float(row.similarity)
                    ))
            except Exception as e:
                await db.rollback()
                log_event("RETRIEVAL", f"PostgreSQL vector query failed, falling back to ORM: {e}")
                citations = []

        if not is_postgres or not citations:
            # Fallback for SQLite / non-pgvector environments
            stmt = select(
                TranscriptChunkModel,
                EpisodeModel.title,
                EpisodeModel.guest,
                EpisodeModel.slug,
                EpisodeModel.youtube_url
            ).join(EpisodeModel, TranscriptChunkModel.episode_id == EpisodeModel.id)

            result = await db.execute(stmt)
            rows = result.all()

            scored = []
            for chunk, ep_title, guest, slug, yt_url in rows:
                if chunk.embedding:
                    sim = cosine_similarity(query_vec, chunk.embedding)
                    if sim >= threshold:
                        scored.append((sim, chunk, ep_title, guest, slug, yt_url))

            scored.sort(key=lambda x: x[0], reverse=True)
            for sim, chunk, ep_title, guest, slug, base_yt_url in scored[:top_k]:
                full_yt_url = build_youtube_timestamp_url(base_yt_url, chunk.start_seconds)
                citations.append(Citation(
                    guest=guest,
                    episode_title=ep_title,
                    episode_slug=slug,
                    start_timestamp=chunk.start_timestamp,
                    start_seconds=chunk.start_seconds,
                    youtube_url=full_yt_url,
                    snippet=chunk.text[:300] + "..." if len(chunk.text) > 300 else chunk.text,
                    similarity=float(sim)
                ))

        log_event(
            "RETRIEVAL",
            f"Retrieved {len(citations)} citations for query",
            query=query[:60],
            top_similarity=citations[0].similarity if citations else 0.0
        )
        return citations
