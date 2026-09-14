import re
from typing import List
from app.schemas.message import Citation


class Ship30WritingEngine:
    """
    Encodes the Ship 30 for 30 framework (Nicolas Cole & Dickie Bush)
    and Impeccable design vocabulary into a structured generation engine.

    Enforces:
    - Specific, high-stakes headline
    - Contrarian hook (1-2 sentences)
    - Grounded problem definition using podcast citations
    - 3-5 tactical pillars formatted for skimmability (short paragraphs, bold anchors)
    - Operational checklist / Monday morning takeaway
    - Target length calibrated around ~1,250 words
    """

    SYSTEM_INSTRUCTIONS = """You are a seasoned growth operator and master digital writer combining the Ship 30 for 30 methodology with Impeccable tone principles.

CRITICAL WRITING PRINCIPLES:
1. PUNCHY HOOK: Start with 1-2 short, declarative sentences that challenge an established belief. Never start with "In today's fast-paced world", "Have you ever wondered", or filler throat-clearing.
2. HIGH SKIMMABILITY & RHYTHM: Alternate sentence lengths. Real technical writing mixes 5-word statements with 20-word explanatory sentences. Use bold key phrases at the start of paragraphs. Never write paragraphs longer than 3-4 sentences.
3. TRANSCRIPT GROUNDING: Every section must quote or reference specific tactics from the retrieved podcast transcripts. Mention the guest by name, their company context, and the specific failure mode or framework they described.
4. ZERO CORPORATE SLOP: Banned words: 'leverage', 'seamless', 'synergy', 'game-changer', 'revolutionize', 'in conclusion'. State trade-offs plainly.
5. LENGTH TARGET: Your essay must be comprehensive and land between 1,100 and 1,400 words (target: ~1,250 words). Provide real operational depth, not superficial bullet points.

STRUCTURE OF THE ESSAY:
- # [Clear, Specific Headline]
- **The Hook** (1-3 sentences)
- ## The Trap: [The common operational mistake teams make]
- ## The Core Shift: [What the guest discovered]
- ## The 3-5 Pillars:
  - ### 1. [First Tactical Pillar with bold anchors and transcript evidence]
  - ### 2. [Second Tactical Pillar]
  - ### 3. [Third Tactical Pillar]
  - ### 4. [Fourth Tactical Pillar / Anti-pattern to avoid]
- ## The Monday Morning Checklist: [Concrete actions a product lead can execute immediately]
- ## Source Footnotes: [Citations with guest name, episode title, and timestamp]
"""

    @classmethod
    def format_prompt(
        cls,
        topic: str,
        core_thesis: str,
        guest_source: str,
        citations: List[Citation]
    ) -> str:
        transcript_context = ""
        for i, c in enumerate(citations, 1):
            transcript_context += (
                f"\n--- Context Source {i} ---\n"
                f"Guest: {c.guest}\n"
                f"Episode: {c.episode_title}\n"
                f"Timestamp: {c.start_timestamp}\n"
                f"Transcript Text:\n{c.snippet}\n"
            )

        prompt = (
            f"Topic: {topic}\n"
            f"Core Thesis: {core_thesis}\n"
            f"Primary Guest: {guest_source}\n\n"
            f"Here is the verified transcript context from Lenny's Podcast archive:\n"
            f"{transcript_context}\n\n"
            f"Draft a complete, deep-dive Ship 30 for 30 essay (~1,250 words) adhering strictly "
            f"to the structure and Impeccable tone principles outlined in your instructions."
        )
        return prompt

    @classmethod
    def calculate_word_count(cls, text: str) -> int:
        words = re.findall(r"\b\w+\b", text)
        return len(words)
