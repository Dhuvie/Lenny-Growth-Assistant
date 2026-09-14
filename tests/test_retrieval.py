import pytest
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.parser import (
    TranscriptParser,
    parse_timestamp_to_seconds,
    seconds_to_timestamp,
    is_sponsor_segment
)
from app.rag.chunker import TranscriptChunker
from app.rag.embeddings import EmbeddingService
from app.rag.retriever import TranscriptRetriever, build_youtube_timestamp_url
from app.db.models import EpisodeModel, TranscriptChunkModel


def test_timestamp_parser():
    assert parse_timestamp_to_seconds("00:05:04") == 304
    assert parse_timestamp_to_seconds("01:13:28") == 4408
    assert parse_timestamp_to_seconds("1:13:28") == 4408
    assert parse_timestamp_to_seconds("02:30") == 150
    assert parse_timestamp_to_seconds("5:20") == 320
    assert parse_timestamp_to_seconds("[00:05:04]") == 304
    assert parse_timestamp_to_seconds("(00:05:04.12)") == 304
    assert parse_timestamp_to_seconds("invalid") == 0

    assert seconds_to_timestamp(304) == "00:05:04"
    assert seconds_to_timestamp(4408) == "01:13:28"


def test_youtube_timestamp_url_builder():
    base = "https://www.youtube.com/watch?v=4ef0juAMqoE"
    url = build_youtube_timestamp_url(base, 304)
    assert url == "https://www.youtube.com/watch?v=4ef0juAMqoE&t=304s"


def test_real_transcript_parsing():
    sample_file = Path("data/transcripts_source/episodes/brian-chesky/transcript.md")
    assert sample_file.exists()

    metadata, turns = TranscriptParser.parse_file(sample_file)
    assert metadata["guest"] == "Brian Chesky"
    assert metadata["video_id"] == "4ef0juAMqoE"
    assert len(turns) > 10

    first_turn = turns[0]
    assert first_turn["speaker"] == "Brian Chesky"
    assert first_turn["timestamp"] == "00:00:00"
    assert first_turn["seconds"] == 0
    assert "founders apologize" in first_turn["text"]


def test_square_bracket_transcript_parsing():
    sample_file = Path("data/transcripts_source/episodes/ryan-hoover/transcript.md")
    assert sample_file.exists()

    metadata, turns = TranscriptParser.parse_file(sample_file)
    assert metadata["guest"] == "Ryan Hoover"
    assert len(turns) >= 100

    # Speaker should be normalized to full guest name
    assert turns[0]["speaker"] == "Ryan Hoover"
    assert turns[0]["seconds"] == 0
    assert turns[1]["speaker"] == "Lenny Rachitsky"
    assert turns[1]["seconds"] == 28


def test_untimestamped_turn_interpolation():
    sample_file = Path("data/transcripts_source/episodes/adriel-frederick/transcript.md")
    assert sample_file.exists()

    parsed = TranscriptParser.parse_file(sample_file)
    assert len(parsed.turns) >= 100
    assert parsed.turns[0]["seconds"] == 0
    # Last turn should have an interpolated timestamp near the episode duration (4046s / 1h 07m)
    assert parsed.turns[-1]["seconds"] > 3000
    assert parsed.turns[-1]["is_estimated_timestamp"] is True


def test_sponsor_detection():
    ad_text = "This episode is brought to you by Sidebar. Are you looking to land your next big career move?"
    normal_text = "Brian Chesky: Way too many founders apologize for how they want to run the company."
    
    assert is_sponsor_segment(ad_text) is True
    assert is_sponsor_segment(normal_text) is False


def test_transcript_chunker():
    chunker = TranscriptChunker(min_chunk_chars=300, max_chunk_chars=800, overlap_chars=50)
    mock_turns = [
        {"speaker": "Lenny", "timestamp": "00:01:00", "seconds": 60, "text": "What is the key to growth?"},
        {"speaker": "Elena", "timestamp": "00:01:20", "seconds": 80, "text": "Do not hire a growth team before product-market fit. It fails every time." * 5},
        {"speaker": "Lenny", "timestamp": "00:02:00", "seconds": 120, "text": "What should founders do instead?"},
    ]
    chunks = chunker.chunk_turns({}, mock_turns)
    assert len(chunks) >= 1
    assert chunks[0]["start_timestamp"] == "00:01:00"
    assert chunks[0]["start_seconds"] == 60
    assert "Elena" in chunks[0]["text"]


def test_embedding_generation():
    vec = EmbeddingService.embed_query("product market fit and retention")
    assert len(vec) == 384
    assert isinstance(vec[0], float)


@pytest.mark.asyncio
async def test_retriever_positive_and_negative(db_session: AsyncSession):
    # Insert test episode and chunk
    ep = EpisodeModel(
        slug="test-retrieval-ep",
        title="Test Growth Strategy",
        guest="Elena Verna",
        youtube_url="https://www.youtube.com/watch?v=TEST1234",
        video_id="TEST1234",
        publish_date="2025-01-01"
    )
    db_session.add(ep)
    await db_session.flush()

    chunk_text = "Elena Verna: The number one mistake is hiring a growth team before product-market fit. You cannot outsource distribution."
    chunk_emb = EmbeddingService.embed_query(chunk_text)

    chunk = TranscriptChunkModel(
        episode_id=ep.id,
        chunk_index=0,
        speaker="Elena Verna",
        start_timestamp="00:02:15",
        start_seconds=135,
        text=chunk_text,
        token_count=30,
        embedding=chunk_emb
    )
    db_session.add(chunk)
    await db_session.commit()

    # 1. Positive retrieval query
    res_pos = await TranscriptRetriever.search("hiring growth team before product market fit", db_session, top_k=1, threshold=0.40)
    assert len(res_pos) == 1
    assert res_pos[0].guest == "Elena Verna"
    assert res_pos[0].start_timestamp == "00:02:15"
    assert res_pos[0].youtube_url == "https://www.youtube.com/watch?v=TEST1234&t=135s"

    # 2. Negative retrieval query (completely unrelated domain)
    res_neg = await TranscriptRetriever.search("quantum thermodynamics astrophysical black holes", db_session, top_k=1, threshold=0.55)
    assert len(res_neg) == 0  # Rejection guardrail triggered
