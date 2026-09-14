import uuid
import re
from typing import List, Dict, Any, Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.logging import log_event
from app.db.models import MessageModel
from app.schemas.message import Artifact, Citation
from app.rag.retriever import TranscriptRetriever
from app.agent.providers.factory import get_llm_provider
from app.agent.tools.ship30_tool import Ship30WritingEngine


SYSTEM_PROMPT = """You are The Lenny Growth Assistant, a technical advisor grounded exclusively in transcripts from Lenny's Podcast (interviews with world-class product, engineering, and growth operators).

CORE OPERATIONAL RULES:
1. CITATION REQUIREMENT: Every factual claim, framework, or tactic you explain MUST be attributed to the specific guest and episode from the retrieved transcript context. Use clickable markdown citations in this exact format:
   [[Guest Name] - "[Episode Title]" ([Timestamp])]([YouTube URL])
2. CONVERSATIONAL ELABORATION & FOLLOW-UPS:
   - When a user asks a follow-up such as 'elaborate', 'tell me more', 'give an example', or asks to expand on a topic from the conversation, provide a detailed, substantive explanation expanding on the guests, frameworks, and insights from the retrieved excerpts and conversation history.
   - NEVER refuse or claim a topic is missing when the user is asking to elaborate, clarify, or continue on a topic already active in the conversation.
3. NEGATIVE RETRIEVAL:
   - Only if a brand-new topic query has zero relevant excerpts in the transcripts and has never been discussed in the session, state:
     "I searched the podcast transcripts archive, but this topic is not discussed in the available episodes. I cannot answer based on Lenny's Podcast transcripts."
4. IMPECCABLE WRITING TONE:
   - Plain, direct technical language.
   - Vary sentence length. Mix short declarative statements with longer explanatory ones.
   - Never use banned buzzwords: 'leverage', 'seamless', 'in today's fast-paced world', 'game-changer', 'revolutionize', 'robust solution', 'in conclusion'.
   - State trade-offs plainly, including drawbacks and counter-examples.
5. ARTIFACTS & ESSAYS:
   - When asked to draft an essay, memo, guide, or Ship 30 article, synthesize a comprehensive piece (~1,250 words) adhering to the Ship 30 framework (hook, problem, 3-5 pillars with bold anchors, and tactical checklist).
   - When asked to generate interactive web pages, calculators, dashboards, or React components:
     Write a self-contained, functional React component using standard hooks (useState, useEffect, useMemo) and Tailwind CSS classes.
     Format as :::artifact{title="Descriptive Title", type="react"} or using standard ```tsx / ```jsx code blocks.
   - When generating standalone HTML pages, use type="html" or ```html code blocks.
   - Both React and HTML artifacts are automatically compiled and rendered in the live side-by-side Artifact Viewer.
"""

FOLLOWUP_TRIGGERS = {
    "elaborate", "elaborate please", "can you elaborate", "please elaborate",
    "tell me more", "more details", "expand", "expand on this", "expand on that",
    "continue", "go on", "explain further", "explain more", "give an example",
    "give me an example", "give examples", "what else", "anything else",
    "why", "how so", "what do you mean", "can you clarify", "clarify",
    "more", "details", "keep going"
}

PRONOUN_OR_ANAPHORA_PATTERNS = [
    r"\b(he|she|they|it|that|this|those|these|him|her|them)\b",
    r"\b(the guest|the speaker|the host|the second|the first|the third)\b",
    r"\b(what about|how about|what did (he|she|they) say)\b"
]


def is_followup_query(text: str) -> bool:
    """Detects if a user message is a conversational follow-up or elaboration."""
    clean = text.strip().lower()
    if clean in FOLLOWUP_TRIGGERS:
        return True
    if any(clean.startswith(prefix) for prefix in [
        "elaborate", "tell me more", "expand on", "explain more", "explain further",
        "give me an example", "give an example", "continue"
    ]):
        return True
    words = clean.split()
    if len(words) <= 4:
        if any(re.search(pat, clean) for pat in PRONOUN_OR_ANAPHORA_PATTERNS) or any(w in FOLLOWUP_TRIGGERS for w in words):
            return True
    if any(re.search(pat, clean) for pat in PRONOUN_OR_ANAPHORA_PATTERNS):
        return True
    return False


def resolve_retrieval_query(user_message: str, past_messages: List[Any]) -> str:
    """
    Synthesizes a standalone retrieval query for multi-turn conversations.
    If the user message is a follow-up or contextual reference, combines it
    with the previous user topic so vector search retrieves relevant transcript chunks.
    """
    if not past_messages:
        return user_message

    if not is_followup_query(user_message):
        return user_message

    last_user_msg = ""
    for m in reversed(past_messages):
        role = m.role if hasattr(m, "role") else m.get("role")
        if role == "user":
            last_user_msg = m.content if hasattr(m, "content") else m.get("content", "")
            break

    if not last_user_msg:
        return user_message

    cleaned_last = re.sub(r"[?!.,;]+", "", last_user_msg).strip()
    clean_user = user_message.strip()

    if clean_user.lower() in FOLLOWUP_TRIGGERS:
        return f"{cleaned_last} elaborate details"

    return f"{cleaned_last} {clean_user}"


def extract_artifact_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Extracts an artifact block if the response generated one, e.g.:
    :::artifact{title="...", type="markdown"}
    ...
    :::
    or standard markdown headers if an essay was produced.
    """
    artifact_regex = re.compile(
        r":::artifact\{title=[\"\'](?P<title>[^\"\']+)[\"\'](?:\s*,?\s*type=[\"\'](?P<type>markdown|html|react)[\"\'])?\}\s*\n(?P<content>.*?)\n:::",
        re.DOTALL
    )
    match = artifact_regex.search(text)
    if match:
        title = match.group("title")
        art_type = match.group("type") or "markdown"
        content = match.group("content").strip()
        word_count = len(re.findall(r"\b\w+\b", content))
        return {
            "id": str(uuid.uuid4()),
            "title": title,
            "type": art_type,
            "content": content,
            "word_count": word_count
        }

    # Check for markdown code fence with React TSX / JSX component
    react_block_regex = re.compile(r"```(?:tsx|jsx|react)\s*\n(?P<content>.*?)\n```", re.DOTALL | re.IGNORECASE)
    react_match = react_block_regex.search(text)
    if react_match:
        content = react_match.group("content").strip()
        if len(content) >= 50:
            words = len(re.findall(r"\b\w+\b", content))
            comp_match = re.search(r"(?:export\s+default\s+function|function|const)\s+([A-Z][A-Za-z0-9_]*)", content)
            title = f"{comp_match.group(1)} Component" if comp_match else "Interactive React Web Page"
            return {
                "id": str(uuid.uuid4()),
                "title": title[:50],
                "type": "react",
                "content": content,
                "word_count": words
            }

    # Check for markdown code fence with complete HTML/CSS snippet
    html_block_regex = re.compile(r"```(?:html|htm)\s*\n(?P<content>.*?)\n```", re.DOTALL | re.IGNORECASE)
    html_match = html_block_regex.search(text)
    if html_match:
        content = html_match.group("content").strip()
        if len(content) >= 50:
            words = len(re.findall(r"\b\w+\b", content))
            title_match = re.search(r"<(?:title|h1)[^>]*>(.*?)</(?:title|h1)>", content, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else "Rendered HTML Snippet"
            return {
                "id": str(uuid.uuid4()),
                "title": title[:50],
                "type": "html",
                "content": content,
                "word_count": words
            }

    # Check for markdown code fence with markdown document
    md_block_regex = re.compile(r"```(?:markdown|md)\s*\n(?P<content>#+ .*?)\n```", re.DOTALL | re.IGNORECASE)
    md_match = md_block_regex.search(text)
    if md_match:
        content = md_match.group("content").strip()
        words = len(re.findall(r"\b\w+\b", content))
        if words >= 150:
            lines = content.splitlines()
            first_line = lines[0].lstrip("# ").strip()
            return {
                "id": str(uuid.uuid4()),
                "title": first_line[:50],
                "type": "markdown",
                "content": content,
                "word_count": words
            }

    # If text is a full-length essay starting with # and > 400 words, automatically wrap as artifact
    words = len(re.findall(r"\b\w+\b", text))
    if text.strip().startswith("# ") and words >= 400:
        lines = text.strip().splitlines()
        first_line = lines[0].lstrip("# ").strip()
        return {
            "id": str(uuid.uuid4()),
            "title": first_line,
            "type": "markdown",
            "content": text.strip(),
            "word_count": words
        }

    return None


class AgentOrchestrator:
    """
    Implements the Anthropic Agent pattern (Think -> Act -> Observe -> Synthesize)
    with persistent conversation context, grounded vector retrieval, and artifact generation.
    """

    @classmethod
    async def run(
        cls,
        session_id: str,
        user_message: str,
        db: AsyncSession,
        stream: bool = True,
        override_provider: Optional[str] = None,
        override_model: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        active_provider_name = (override_provider or settings.LLM_PROVIDER).lower()
        log_event(
            "API",
            f"Agent execution started for session: {session_id}",
            query=user_message[:60],
            provider=active_provider_name,
            model=override_model or settings.active_model
        )

        # 1. Fetch previous session history
        stmt = select(MessageModel).where(MessageModel.session_id == session_id).order_by(MessageModel.created_at)
        res = await db.execute(stmt)
        past_messages = res.scalars().all()

        # Build detached history records before commit to prevent lazy-load expiration issues in async sessions
        past_messages_data: List[Dict[str, Any]] = []
        for msg in past_messages:
            past_messages_data.append({
                "role": msg.role,
                "content": msg.content,
                "sources": list(msg.sources) if msg.sources else []
            })

        # Build message history for provider
        formatted_messages: List[Dict[str, Any]] = []
        for msg in past_messages_data:
            formatted_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        formatted_messages.append({"role": "user", "content": user_message})

        # Persist user message immediately
        user_msg_record = MessageModel(
            session_id=session_id,
            role="user",
            content=user_message,
            sources=[],
            artifacts=[],
            model_provider=active_provider_name
        )
        db.add(user_msg_record)
        await db.commit()

        # 2. Check for Ship 30 essay intent or general query
        is_ship30_intent = any(keyword in user_message.lower() for keyword in [
            "ship 30", "atomic essay", "write an essay", "draft an essay", "publishable essay", "write a post"
        ])

        yield {"type": "status", "message": "Searching transcript archive for relevant episodes..."}

        # Retrieve relevant transcript chunks with contextual follow-up resolution
        retrieval_query = resolve_retrieval_query(user_message, past_messages_data)
        citations = await TranscriptRetriever.search(retrieval_query, db, top_k=settings.TOP_K_RESULTS)

        # In conversational follow-ups (e.g. 'elaborate'), also retain grounded sources from previous turn
        if is_followup_query(user_message) and past_messages_data:
            last_assistant_msg = next((m for m in reversed(past_messages_data) if m.get("role") == "assistant"), None)
            if last_assistant_msg and last_assistant_msg.get("sources"):
                seen_sources = {(c.episode_slug, c.start_seconds) for c in citations}
                for s in last_assistant_msg["sources"]:
                    if isinstance(s, dict):
                        try:
                            prev_c = Citation(**s)
                            if (prev_c.episode_slug, prev_c.start_seconds) not in seen_sources:
                                citations.append(prev_c)
                                seen_sources.add((prev_c.episode_slug, prev_c.start_seconds))
                        except Exception:
                            pass

        if citations:
            yield {
                "type": "citations",
                "citations": [c.model_dump() for c in citations]
            }

        # 3. Formulate augmented prompt
        if not citations:
            yield {
                "type": "token",
                "token": "I searched the podcast transcripts archive, but this topic is not discussed in the available episodes. I cannot answer based on Lenny's Podcast transcripts."
            }
            assistant_content = "I searched the podcast transcripts archive, but this topic is not discussed in the available episodes. I cannot answer based on Lenny's Podcast transcripts."
            assistant_record = MessageModel(
                session_id=session_id,
                role="assistant",
                content=assistant_content,
                sources=[],
                artifacts=[],
                model_provider=settings.LLM_PROVIDER
            )
            db.add(assistant_record)
            await db.commit()
            yield {"type": "done", "session_id": session_id}
            return

        # Prepare context injection
        context_block = "\n\n=== RELEVANT TRANSCRIPT EXCERPTS ===\n"
        for i, c in enumerate(citations, 1):
            context_block += (
                f"\n[Source {i}]\n"
                f"Guest: {c.guest}\n"
                f"Episode: {c.episode_title} (slug: {c.episode_slug})\n"
                f"Start Timestamp: {c.start_timestamp} (seconds: {c.start_seconds})\n"
                f"YouTube URL: {c.youtube_url}\n"
                f"Excerpt:\n{c.snippet}\n"
            )
        context_block += "\n=== END TRANSCRIPT EXCERPTS ===\n"

        augmented_system = SYSTEM_PROMPT + "\n" + context_block

        if is_ship30_intent:
            augmented_system += "\n" + Ship30WritingEngine.SYSTEM_INSTRUCTIONS
            yield {"type": "status", "message": "Applying Ship 30 for 30 essay framework..."}
        else:
            yield {"type": "status", "message": "Synthesizing grounded response with citations..."}

        # 4. Stream completion from active LLM provider
        provider = get_llm_provider(override_provider, override_model)
        accumulated_tokens: List[str] = []

        try:
            async for event in provider.stream_generate(
                messages=formatted_messages,
                system=augmented_system
            ):
                if event.get("type") == "token":
                    token = event.get("token", "")
                    accumulated_tokens.append(token)
                    yield {"type": "token", "token": token}
                elif event.get("type") == "error":
                    err_msg = event.get("error", "Unknown provider error")
                    yield {"type": "error", "error": err_msg}
                    return
        except Exception as e:
            err_str = str(e)
            log_event("LLM", f"LLM stream error: {err_str}")
            yield {
                "type": "error",
                "error": f"Model error ({active_provider_name}): {err_str}"
            }
            return

        full_content = "".join(accumulated_tokens).strip()

        # 5. Extract artifacts if created
        artifacts_to_save: List[Artifact] = []
        extracted_art = extract_artifact_from_text(full_content)
        if extracted_art:
            art_obj = Artifact(**extracted_art)
            artifacts_to_save.append(art_obj)
            yield {"type": "artifact", "artifact": art_obj.model_dump()}

        # 6. Persist assistant message in database
        assistant_record = MessageModel(
            session_id=session_id,
            role="assistant",
            content=full_content,
            sources=[c.model_dump() for c in citations],
            artifacts=[a.model_dump() for a in artifacts_to_save],
            model_provider=active_provider_name
        )
        db.add(assistant_record)
        await db.commit()

        log_event(
            "API",
            f"Agent completed response for session {session_id}",
            tokens=len(full_content) // 4,
            citations=len(citations),
            artifacts=len(artifacts_to_save)
        )
        yield {"type": "done", "session_id": session_id}
