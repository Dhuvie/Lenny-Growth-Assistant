import re
import yaml
from pathlib import Path
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, field


def parse_timestamp_to_seconds(ts: str) -> int:
    """
    Converts timestamp string (HH:MM:SS or MM:SS or H:MM:SS or M:SS) to total seconds.
    Handles sub-seconds, brackets, parentheses, and trailing punctuation.
    
    Examples:
      '00:05:04'      -> 304
      '01:13:28'      -> 4408
      '1:13:28'       -> 4408
      '05:20'         -> 320
      '5:20'          -> 320
      '[00:05:04]'    -> 304
      '(00:05:04.12)' -> 304
    """
    if not ts:
        return 0

    # Clean brackets, parentheses, colons, and whitespace
    clean_ts = ts.strip().strip("()[]: ").strip()
    
    # Strip sub-second milliseconds if present (e.g., "00:05:04.120" or "00:05:04,120")
    clean_ts = re.split(r"[\.,]", clean_ts)[0]

    parts = clean_ts.split(":")
    try:
        if len(parts) == 3:
            h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
            return h * 3600 + m * 60 + s
        elif len(parts) == 2:
            m, s = int(parts[0]), int(parts[1])
            return m * 60 + s
        elif len(parts) == 1 and parts[0].isdigit():
            return int(parts[0])
        return 0
    except Exception:
        return 0


def seconds_to_timestamp(seconds: int) -> str:
    """
    Converts total integer seconds into formatted HH:MM:SS string.
    Example: 304 -> '00:05:04', 4408 -> '01:13:28'
    """
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


# Common sponsor signature phrases in Lenny's Podcast
SPONSOR_PATTERNS = [
    re.compile(r"this episode(?:'?s)?\s+(?:is\s+)?brought to you by", re.IGNORECASE),
    re.compile(r"a (?:short|quick) word from our sponsors", re.IGNORECASE),
    re.compile(r"thank you to our sponsors", re.IGNORECASE),
    re.compile(r"(?:visit|check out)\s+([a-z0-9\-\.]+)\.com/lenny", re.IGNORECASE),
    re.compile(r"(?:visit|check out)\s+([a-z0-9\-\.]+)\.app/lenny", re.IGNORECASE),
    re.compile(r"jump the growing wait list.*visit\s+[a-z0-9\-\.]+/lenny", re.IGNORECASE),
]


def is_sponsor_segment(text: str) -> bool:
    """Detects whether a spoken turn is a sponsor read or advertisement."""
    for pattern in SPONSOR_PATTERNS:
        if pattern.search(text):
            return True
    return False


@dataclass
class TranscriptTurn:
    speaker: str
    raw_speaker: str
    timestamp: str
    seconds: int
    text: str
    is_sponsor: bool = False
    is_estimated_timestamp: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "speaker": self.speaker,
            "raw_speaker": self.raw_speaker,
            "timestamp": self.timestamp,
            "seconds": self.seconds,
            "text": self.text,
            "is_sponsor": self.is_sponsor,
            "is_estimated_timestamp": self.is_estimated_timestamp,
        }


@dataclass
class ParsedTranscript:
    metadata: Dict[str, Any]
    turns: List[Dict[str, Any]]
    turn_objects: List[TranscriptTurn] = field(default_factory=list)

    def __iter__(self):
        """Permits direct tuple unpacking: metadata, turns = TranscriptParser.parse_file(...)"""
        return iter((self.metadata, self.turns))

    @property
    def total_words(self) -> int:
        return sum(len(re.findall(r"\b\w+\b", t["text"])) for t in self.turns)

    @property
    def non_sponsor_turns(self) -> List[Dict[str, Any]]:
        return [t for t in self.turns if not t.get("is_sponsor", False)]

    @property
    def speaker_distribution(self) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for t in self.turns:
            sp = t.get("speaker", "Unknown")
            dist[sp] = dist.get(sp, 0) + 1
        return dist


class TranscriptParser:
    """
    Parses an episode transcript.md file from ChatPRD/lennys-podcast-transcripts.
    
    Extracts YAML frontmatter and parses turn-by-turn dialogue, supporting all five
    common transcript formatting variants in the Lenny's Podcast archive:
      1. Speaker (HH:MM:SS): text
      2. (HH:MM:SS): text  [continuation]
      3. [HH:MM:SS] Speaker: text  (e.g., Ryan Hoover episode)
      4. [HH:MM:SS] text  (timestamp continuation with brackets)
      5. Speaker Name: text  (e.g., Adriel Frederick episode)

    Features:
      - Normalizes speaker names (e.g. 'Lenny' -> 'Lenny Rachitsky', guest first name -> full guest name)
      - Proportional timestamp interpolation for episodes without explicit per-turn timestamps
      - Automatic sponsor read detection (is_sponsor flag)
      - Robust YouTube URL / video ID recovery
    """

    # Comprehensive multi-variant turn header regex
    TURN_REGEX = re.compile(
        r"^(?:"
        # Variant A: [00:05:04] Speaker: inline text OR [00:05:04] inline text
        r"\[(?P<ts_square>\d{1,2}:\d{2}(?::\d{2})?)\]\s*(?:(?P<sp_square>[A-Za-z0-9\s\.\'\-]+?):\s*)?(?P<inline_square>.*)|"
        # Variant B: Speaker (00:05:04): inline text OR (00:05:04): inline text
        r"(?:(?P<sp_paren>[A-Za-z0-9\s\.\'\-]+?)\s+)?\((?P<ts_paren>\d{1,2}:\d{2}(?::\d{2})?)\):?\s*(?P<inline_paren>.*)|"
        # Variant C: Standalone speaker line (Lenny: or Guest Name:)
        r"(?P<sp_colon>[A-Za-z0-9\s\.\'\-]+?):\s*(?P<inline_colon>.*)"
        r")$"
    )

    @classmethod
    def _normalize_speaker(
        cls,
        raw_speaker: str,
        guest_name: str
    ) -> Tuple[str, str]:
        """
        Normalizes short or variant speaker names to canonical full names.
        Examples:
          'Lenny' -> ('Lenny Rachitsky', 'Lenny')
          'Ryan'  -> ('Ryan Hoover', 'Ryan')
        """
        raw_clean = raw_speaker.strip().strip(":")
        if not raw_clean:
            return guest_name, raw_speaker

        lower_raw = raw_clean.lower()
        
        # Host normalization
        if lower_raw in {"lenny", "lenny r", "lenny rachitsky", "host"}:
            return "Lenny Rachitsky", raw_clean

        # Guest normalization
        if guest_name:
            guest_first = guest_name.split()[0].lower()
            if lower_raw == guest_first or lower_raw == guest_name.lower():
                return guest_name, raw_clean

        return raw_clean, raw_clean

    @classmethod
    def parse_file(cls, filepath: Path) -> ParsedTranscript:
        """
        Parses a transcript file into a ParsedTranscript container.
        Supports tuple unpacking: metadata, turns = TranscriptParser.parse_file(...)
        """
        content = filepath.read_text(encoding="utf-8")
        
        # 1. Parse frontmatter
        metadata: Dict[str, Any] = {}
        body = content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    metadata = yaml.safe_load(parts[1]) or {}
                except Exception:
                    metadata = {}
                body = parts[2]

        slug = filepath.parent.name
        metadata["slug"] = slug

        # Ensure title & guest
        if "title" not in metadata or not metadata["title"]:
            metadata["title"] = slug.replace("-", " ").title()
        if "guest" not in metadata or not metadata["guest"]:
            metadata["guest"] = metadata["title"]

        guest_name = str(metadata["guest"]).strip()

        # YouTube URL & Video ID normalization
        if "youtube_url" not in metadata:
            metadata["youtube_url"] = ""
        if "video_id" not in metadata or not metadata["video_id"]:
            url = metadata.get("youtube_url", "")
            match = re.search(r"(?:v=|youtu\.be/|embed/)([A-Za-z0-9_\-]+)", url)
            metadata["video_id"] = match.group(1) if match else ""

        if not metadata["youtube_url"] and metadata["video_id"]:
            metadata["youtube_url"] = f"https://www.youtube.com/watch?v={metadata['video_id']}"

        # Duration normalization
        duration_seconds = float(metadata.get("duration_seconds") or 0.0)

        # 2. Parse turns from markdown body
        raw_turns_data: List[Dict[str, Any]] = []
        lines = body.splitlines()

        current_speaker, current_raw_speaker = cls._normalize_speaker(guest_name, guest_name)
        current_timestamp = "00:00:00"
        current_seconds = 0
        has_explicit_timestamps = False
        current_buffer: List[str] = []

        in_transcript = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            if stripped == "## Transcript":
                in_transcript = True
                continue

            # Skip episode title headers if before transcript section
            if not in_transcript and stripped.startswith("#"):
                continue

            match = cls.TURN_REGEX.match(stripped)
            if match:
                # Flush previous turn buffer if non-empty
                if current_buffer:
                    turn_text = " ".join(current_buffer).strip()
                    if turn_text:
                        raw_turns_data.append({
                            "speaker": current_speaker,
                            "raw_speaker": current_raw_speaker,
                            "timestamp": current_timestamp,
                            "seconds": current_seconds,
                            "text": turn_text,
                            "has_explicit_ts": has_explicit_timestamps
                        })
                    current_buffer = []

                # Determine which regex variant matched
                ts_str = match.group("ts_square") or match.group("ts_paren")
                sp_str = match.group("sp_square") or match.group("sp_paren") or match.group("sp_colon")
                inline_text = match.group("inline_square") or match.group("inline_paren") or match.group("inline_colon")

                # If timestamp was captured
                if ts_str:
                    has_explicit_timestamps = True
                    current_timestamp = ts_str
                    current_seconds = parse_timestamp_to_seconds(ts_str)

                # If speaker was captured
                if sp_str:
                    current_speaker, current_raw_speaker = cls._normalize_speaker(sp_str, guest_name)

                # Append any inline text directly to buffer
                if inline_text and inline_text.strip():
                    current_buffer.append(inline_text.strip())
            else:
                if stripped and not stripped.startswith("#"):
                    current_buffer.append(stripped)

        # Flush final turn buffer
        if current_buffer:
            turn_text = " ".join(current_buffer).strip()
            if turn_text:
                raw_turns_data.append({
                    "speaker": current_speaker,
                    "raw_speaker": current_raw_speaker,
                    "timestamp": current_timestamp,
                    "seconds": current_seconds,
                    "text": turn_text,
                    "has_explicit_ts": has_explicit_timestamps
                })

        # 3. Handle Proportional Timestamp Interpolation for turns without timestamps
        # (e.g. Adriel Frederick episode where turns have speakers but no timestamps)
        turns_with_explicit_ts = sum(1 for t in raw_turns_data if t["has_explicit_ts"])
        needs_interpolation = (turns_with_explicit_ts == 0 and len(raw_turns_data) > 1)

        total_words = sum(len(re.findall(r"\b\w+\b", t["text"])) for t in raw_turns_data)
        effective_duration = duration_seconds if duration_seconds > 0 else (total_words / 2.3)  # ~140 wpm fallback

        cumulative_words = 0
        final_turn_objects: List[TranscriptTurn] = []
        final_turns_dicts: List[Dict[str, Any]] = []

        for t_data in raw_turns_data:
            text = t_data["text"]
            words = len(re.findall(r"\b\w+\b", text))
            is_sponsor = is_sponsor_segment(text)

            if needs_interpolation:
                interpolated_sec = int((cumulative_words / max(total_words, 1)) * effective_duration)
                ts_str = seconds_to_timestamp(interpolated_sec)
                sec_val = interpolated_sec
                is_est = True
            else:
                ts_str = t_data["timestamp"]
                sec_val = t_data["seconds"]
                is_est = not t_data["has_explicit_ts"]

            turn_obj = TranscriptTurn(
                speaker=t_data["speaker"],
                raw_speaker=t_data["raw_speaker"],
                timestamp=ts_str,
                seconds=sec_val,
                text=text,
                is_sponsor=is_sponsor,
                is_estimated_timestamp=is_est
            )
            final_turn_objects.append(turn_obj)
            final_turns_dicts.append(turn_obj.to_dict())

            cumulative_words += words

        return ParsedTranscript(
            metadata=metadata,
            turns=final_turns_dicts,
            turn_objects=final_turn_objects
        )
