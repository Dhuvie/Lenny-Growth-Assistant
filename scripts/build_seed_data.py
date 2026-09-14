import json
from pathlib import Path
from app.rag.parser import TranscriptParser
from app.rag.chunker import TranscriptChunker
from app.rag.embeddings import EmbeddingService
from app.ingest import SEED_EPISODE_SLUGS

SOURCE_DIR = Path("data/transcripts_source/episodes")
OUTPUT_FILE = Path("data/seed_data/seed_episodes.json")


def build_seed():
    print(f"Building seed data for {len(SEED_EPISODE_SLUGS)} episodes...")
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    chunker = TranscriptChunker()
    seed_episodes = []

    for i, slug in enumerate(SEED_EPISODE_SLUGS, 1):
        ep_dir = SOURCE_DIR / slug
        transcript_file = ep_dir / "transcript.md"
        if not transcript_file.exists():
            print(f"Skipping {slug}, transcript file not found.")
            continue

        metadata, turns = TranscriptParser.parse_file(transcript_file)
        if not turns:
            continue

        raw_chunks = chunker.chunk_turns(metadata, turns)
        if not raw_chunks:
            continue

        texts = [c["text"] for c in raw_chunks]
        embeddings = EmbeddingService.embed_texts(texts)

        chunks_data = []
        for c, emb in zip(raw_chunks, embeddings):
            c_copy = dict(c)
            c_copy["embedding"] = emb
            chunks_data.append(c_copy)

        ep_data = {
            "slug": slug,
            "title": metadata.get("title", slug.replace("-", " ").title()),
            "guest": metadata.get("guest", slug.replace("-", " ").title()),
            "youtube_url": metadata.get("youtube_url", ""),
            "video_id": metadata.get("video_id", ""),
            "publish_date": str(metadata.get("publish_date", "")),
            "duration_seconds": float(metadata.get("duration_seconds", 0.0) or 0.0),
            "duration": str(metadata.get("duration", "")),
            "view_count": int(metadata.get("view_count", 0) or 0),
            "channel": metadata.get("channel", "Lenny's Podcast"),
            "keywords": metadata.get("keywords", []),
            "chunks": chunks_data
        }
        seed_episodes.append(ep_data)
        print(f"[{i}/{len(SEED_EPISODE_SLUGS)}] Processed {slug} ({len(chunks_data)} chunks)")

    OUTPUT_FILE.write_text(json.dumps(seed_episodes, indent=2), encoding="utf-8")
    print(f"Successfully generated seed data at {OUTPUT_FILE} with {len(seed_episodes)} episodes.")


if __name__ == "__main__":
    build_seed()
