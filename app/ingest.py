import asyncio
import argparse
import sys
from pathlib import Path
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.logging import setup_logging, log_event
from app.db.session import AsyncSessionLocal, init_db
from app.db.models import EpisodeModel, TranscriptChunkModel
from app.rag.parser import TranscriptParser
from app.rag.chunker import TranscriptChunker
from app.rag.embeddings import EmbeddingService

# Curated foundational episodes representing key growth and product frameworks
SEED_EPISODE_SLUGS = [
    "brian-chesky",
    "elena-verna",
    "shreyas-doshi",
    "casey-winters",
    "marty-cagan",
    "brian-balfour",
    "gustaf-alstromer",
    "sean-ellis",
    "rahul-vohra",
    "tobi-lutke",
    "dylan-field",
    "melanie-perkins",
    "dan-hockenmaier",
    "april-dunford",
    "bob-moesta",
    "hila-qu",
    "nikita-bier",
    "claire-vo",
    "bangaly-kaba",
    "madhavan-ramanujam"
]


async def ingest_single_episode(
    episode_dir: Path,
    db: AsyncSession,
    chunker: TranscriptChunker,
    reindex: bool = False
) -> int:
    """
    Ingests a single episode folder.
    Returns the count of chunks created.
    """
    transcript_file = episode_dir / "transcript.md"
    if not transcript_file.exists():
        return 0

    slug = episode_dir.name

    # Check if episode is already indexed
    stmt = select(EpisodeModel).where(EpisodeModel.slug == slug)
    res = await db.execute(stmt)
    existing_ep = res.scalar_one_or_none()

    if existing_ep and not reindex:
        return 0

    # Parse metadata and dialogue turns
    metadata, turns = TranscriptParser.parse_file(transcript_file)
    if not turns:
        log_event("INGEST", f"No dialogue turns parsed for episode: {slug}")
        return 0

    # Chunk turns
    raw_chunks = chunker.chunk_turns(metadata, turns)
    if not raw_chunks:
        return 0

    # Generate embeddings in batch
    texts_to_embed = [c["text"] for c in raw_chunks]
    embeddings = EmbeddingService.embed_texts(texts_to_embed)

    # Delete existing if re-indexing
    if existing_ep:
        await db.delete(existing_ep)
        await db.flush()

    # Create Episode record
    ep = EpisodeModel(
        slug=slug,
        title=metadata.get("title", slug.replace("-", " ").title()),
        guest=metadata.get("guest", slug.replace("-", " ").title()),
        youtube_url=metadata.get("youtube_url", ""),
        video_id=metadata.get("video_id", ""),
        publish_date=str(metadata.get("publish_date", "")),
        duration_seconds=float(metadata.get("duration_seconds", 0.0) or 0.0),
        duration=str(metadata.get("duration", "")),
        view_count=int(metadata.get("view_count", 0) or 0),
        channel=metadata.get("channel", "Lenny's Podcast"),
        keywords=metadata.get("keywords", [])
    )
    db.add(ep)
    await db.flush()

    # Add chunk records
    chunk_models = []
    for c_data, emb in zip(raw_chunks, embeddings):
        chunk_models.append(
            TranscriptChunkModel(
                episode_id=ep.id,
                chunk_index=c_data["chunk_index"],
                speaker=c_data["speaker"],
                start_timestamp=c_data["start_timestamp"],
                start_seconds=c_data["start_seconds"],
                text=c_data["text"],
                token_count=c_data["token_count"],
                embedding=emb
            )
        )
    db.add_all(chunk_models)
    await db.commit()

    log_event("INGEST", f"Indexed '{metadata.get('title')}' ({len(chunk_models)} chunks)")
    return len(chunk_models)


async def run_ingestion(
    source_dir: Path,
    episodes: Optional[List[str]] = None,
    seed_mode: bool = False,
    all_mode: bool = False,
    reindex: bool = False
):
    setup_logging()
    await init_db()

    if not source_dir.exists():
        log_event("INGEST", f"Source directory {source_dir} not found. Please pull transcripts first.")
        sys.exit(1)

    chunker = TranscriptChunker()

    target_slugs = None
    if episodes:
        target_slugs = set(episodes)
    elif seed_mode:
        target_slugs = set(SEED_EPISODE_SLUGS)

    candidate_dirs = [p for p in source_dir.iterdir() if p.is_dir() and (p / "transcript.md").exists()]
    if target_slugs is not None:
        candidate_dirs = [d for d in candidate_dirs if d.name in target_slugs]

    log_event("INGEST", f"Starting ingestion for {len(candidate_dirs)} episodes...")
    total_chunks = 0
    episodes_indexed = 0

    async with AsyncSessionLocal() as db:
        for i, ep_dir in enumerate(candidate_dirs, 1):
            try:
                count = await ingest_single_episode(ep_dir, db, chunker, reindex=reindex)
                if count > 0:
                    episodes_indexed += 1
                    total_chunks += count
                print(f"[{i}/{len(candidate_dirs)}] Processed {ep_dir.name} (+{count} chunks)")
            except Exception as e:
                log_event("INGEST", f"Failed to ingest {ep_dir.name}: {e}")

    log_event("INGEST", f"Completed. Indexed {episodes_indexed} episodes ({total_chunks} total chunks).")


def main():
    parser = argparse.ArgumentParser(description="Ingest Lenny's Podcast transcripts into database with embeddings.")
    parser.add_argument("--source-dir", type=str, default="data/transcripts_source/episodes", help="Path to episodes directory")
    parser.add_argument("--episodes", type=str, help="Comma-separated list of episode slugs to ingest")
    parser.add_argument("--seed", action="store_true", help="Ingest foundational seed episodes (20 core growth episodes)")
    parser.add_argument("--all", action="store_true", help="Ingest all available episodes")
    parser.add_argument("--reindex", action="store_true", help="Re-index existing episodes")

    args = parser.parse_args()

    slugs = [s.strip() for s in args.episodes.split(",")] if args.episodes else None
    source_path = Path(args.source_dir)

    # Default to seed mode if no explicit arguments provided
    seed_flag = args.seed or (not args.all and not args.episodes)

    asyncio.run(run_ingestion(
        source_dir=source_path,
        episodes=slugs,
        seed_mode=seed_flag,
        all_mode=args.all,
        reindex=args.reindex
    ))


if __name__ == "__main__":
    main()
