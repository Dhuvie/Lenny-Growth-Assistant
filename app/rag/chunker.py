from typing import List, Dict, Any


class TranscriptChunker:
    """
    Chunks dialogue turns into coherent semantic windows while preserving:
    - Speaker identity and turn boundaries
    - Starting timestamp and second offset for exact YouTube citations
    - Target chunk window: ~1,200 - 1,800 characters (~250-350 words)
    - Sliding overlap of ~150 characters to prevent loss of context across boundaries
    """

    def __init__(
        self,
        min_chunk_chars: int = 800,
        max_chunk_chars: int = 1600,
        overlap_chars: int = 150
    ):
        self.min_chunk_chars = min_chunk_chars
        self.max_chunk_chars = max_chunk_chars
        self.overlap_chars = overlap_chars

    def chunk_turns(
        self,
        metadata: Dict[str, Any],
        turns: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        if not turns:
            return []

        chunks: List[Dict[str, Any]] = []
        current_text_parts: List[str] = []
        current_speaker = turns[0]["speaker"]
        start_timestamp = turns[0]["timestamp"]
        start_seconds = turns[0]["seconds"]
        current_char_count = 0
        chunk_index = 0

        for turn in turns:
            speaker = turn["speaker"]
            text = turn["text"]
            formatted_turn = f"{speaker}: {text}"
            turn_len = len(formatted_turn)

            # If adding this turn exceeds max_chunk_chars and we already have enough content
            if current_char_count + turn_len > self.max_chunk_chars and current_char_count >= self.min_chunk_chars:
                chunk_text = "\n\n".join(current_text_parts).strip()
                chunks.append({
                    "chunk_index": chunk_index,
                    "speaker": current_speaker,
                    "start_timestamp": start_timestamp,
                    "start_seconds": start_seconds,
                    "text": chunk_text,
                    "token_count": len(chunk_text) // 4
                })
                chunk_index += 1

                # Start new chunk with overlap if feasible
                if self.overlap_chars > 0 and current_text_parts:
                    last_part = current_text_parts[-1]
                    overlap_snippet = last_part[-self.overlap_chars:]
                    current_text_parts = [f"...{overlap_snippet}", formatted_turn]
                    current_char_count = len(overlap_snippet) + turn_len
                else:
                    current_text_parts = [formatted_turn]
                    current_char_count = turn_len

                current_speaker = speaker
                start_timestamp = turn["timestamp"]
                start_seconds = turn["seconds"]
            else:
                current_text_parts.append(formatted_turn)
                current_char_count += turn_len

        # Flush remaining buffer
        if current_text_parts:
            chunk_text = "\n\n".join(current_text_parts).strip()
            if chunk_text:
                chunks.append({
                    "chunk_index": chunk_index,
                    "speaker": current_speaker,
                    "start_timestamp": start_timestamp,
                    "start_seconds": start_seconds,
                    "text": chunk_text,
                    "token_count": len(chunk_text) // 4
                })

        return chunks
