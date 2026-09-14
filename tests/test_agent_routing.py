from app.agent.tools.base import ALL_TOOLS
from app.agent.tools.ship30_tool import Ship30WritingEngine
from app.agent.orchestrator import extract_artifact_from_text, is_followup_query, resolve_retrieval_query
from app.db.models import MessageModel
from app.schemas.message import Citation
from app.agent.providers.factory import get_llm_provider
from app.agent.providers.gemini import GeminiProvider
import pytest


def test_agent_tool_schemas():
    assert len(ALL_TOOLS) == 3
    tool_names = [t["function"]["name"] for t in ALL_TOOLS]
    assert "retrieve_podcast_transcripts" in tool_names
    assert "generate_ship30_essay" in tool_names
    assert "create_artifact" in tool_names


def test_ship30_engine_principles():
    instructions = Ship30WritingEngine.SYSTEM_INSTRUCTIONS
    assert "PUNCHY HOOK" in instructions
    assert "SKIMMABILITY" in instructions
    assert "TRANSCRIPT GROUNDING" in instructions
    assert "ZERO CORPORATE SLOP" in instructions
    assert "1,250 words" in instructions

    # Test prompt formatting
    mock_citations = [
        Citation(
            guest="Brian Chesky",
            episode_title="Brian Chesky's new playbook",
            episode_slug="brian-chesky",
            start_timestamp="00:00:00",
            start_seconds=0,
            youtube_url="https://youtube.com/watch?v=4ef0juAMqoE",
            snippet="Leaders must be in the details rather than managing by spreadsheets."
        )
    ]
    prompt = Ship30WritingEngine.format_prompt(
        topic="Being in the details vs micromanagement",
        core_thesis="Leaders who detach from product details fail their teams",
        guest_source="Brian Chesky",
        citations=mock_citations
    )
    assert "Brian Chesky" in prompt
    assert "00:00:00" in prompt
    assert "Being in the details" in prompt


def test_ship30_word_count_calculation():
    sample_text = "Word count calculation should accurately count thirty individual words in this concise test string to verify the metric calibration without any regex boundary errors happening here."
    wc = Ship30WritingEngine.calculate_word_count(sample_text)
    assert wc == 26


def test_extract_artifact_from_explicit_block():
    text = """Here is the essay you requested:

:::artifact{title="Why Performance Marketing Stops Compounding", type="markdown"}
# Why Performance Marketing Stops Compounding

Brand marketing builds chandeliers; performance marketing is a laser.
:::

I hope this helps!"""
    art = extract_artifact_from_text(text)
    assert art is not None
    assert art["title"] == "Why Performance Marketing Stops Compounding"
    assert art["type"] == "markdown"
    assert "chandeliers" in art["content"]


def test_extract_artifact_from_long_essay():
    long_essay = "# The Operator's Guide to Product Roadmaps\n\n" + ("Brian Chesky runs Airbnb with a single company-wide roadmap. " * 60)
    art = extract_artifact_from_text(long_essay)
    assert art is not None
    assert art["title"] == "The Operator's Guide to Product Roadmaps"
    assert art["word_count"] >= 400


def test_extract_html_and_markdown_code_block_artifacts():
    html_text = """Here is the dashboard snippet:
```html
<div class="growth-card">
  <h1>Growth Velocity Dashboard</h1>
  <p>Metrics tracked across 500 active teams.</p>
</div>
```
"""
    art_html = extract_artifact_from_text(html_text)
    assert art_html is not None
    assert art_html["type"] == "html"
    assert "Growth Velocity Dashboard" in art_html["title"]
    assert "growth-card" in art_html["content"]

    md_text = """Here is the strategy document:
```markdown
# Product Strategy Framework
""" + ("We evaluate high agency product leaders across customer retention cohorts and activation benchmarks. " * 20) + """
```
"""
    art_md = extract_artifact_from_text(md_text)
    assert art_md is not None
    assert art_md["type"] == "markdown"
    assert "Product Strategy Framework" in art_md["title"]


def test_extract_react_artifacts():
    tsx_text = """Here is the interactive growth calculator component:
```tsx
import React, { useState } from 'react';

export default function GrowthSimulator() {
  const [mrr, setMrr] = useState(50000);
  const [churnRate, setChurnRate] = useState(0.03);

  return (
    <div className="p-6 bg-slate-900 text-white rounded-xl">
      <h2 className="text-xl font-bold">PLG Growth Simulator</h2>
      <p>Current MRR: ${mrr}</p>
    </div>
  );
}
```
"""
    art_react = extract_artifact_from_text(tsx_text)
    assert art_react is not None
    assert art_react["type"] == "react"
    assert "GrowthSimulator" in art_react["title"]
    assert "useState" in art_react["content"]

    custom_tag = """:::artifact{title="Churn Modeling Tool", type="react"}
function ChurnModel() {
  return <div>Model</div>;
}
:::
"""
    art_tag = extract_artifact_from_text(custom_tag)
    assert art_tag is not None
    assert art_tag["type"] == "react"
    assert art_tag["title"] == "Churn Modeling Tool"




@pytest.mark.asyncio
async def test_gemini_provider_factory_and_models():
    provider = get_llm_provider("gemini")
    assert isinstance(provider, GeminiProvider)
    assert provider.model == "gemini-3.5-flash-lite"
    assert "gemini-3.5-flash-lite" in GeminiProvider.AVAILABLE_MODELS
    assert "gemini-3.8-flash" in GeminiProvider.AVAILABLE_MODELS
    assert "gemini-3.7-flash" in GeminiProvider.AVAILABLE_MODELS
    assert "gemini-2.5-flash" in GeminiProvider.AVAILABLE_MODELS

    # Test model override
    pro_provider = get_llm_provider("gemini", override_model="gemini-3.8-flash")
    assert pro_provider.model == "gemini-3.8-flash"

    lite_provider = get_llm_provider("gemini", override_model="gemini-3.5-flash-lite")
    assert lite_provider.model == "gemini-3.5-flash-lite"

    # Test health check returns a valid status
    health = await provider.check_health()
    assert health.status in {"misconfigured", "unreachable", "reachable", "degraded"}


def test_contextual_followup_resolution():
    assert is_followup_query("elaborate") is True
    assert is_followup_query("can you elaborate") is True
    assert is_followup_query("tell me more") is True
    assert is_followup_query("what did he say about that?") is True
    assert is_followup_query("give me an example") is True
    assert is_followup_query("how to price a B2B SaaS product") is False

    past = [
        MessageModel(session_id="s1", role="user", content="who is lenny"),
        MessageModel(session_id="s1", role="assistant", content="Lenny Rachitsky is the host...")
    ]

    # Elaborate query should resolve with previous user topic
    q1 = resolve_retrieval_query("elaborate", past)
    assert "who is lenny" in q1
    assert "elaborate" in q1

    # Standalone query should remain unchanged
    q2 = resolve_retrieval_query("what is product market fit", past)
    assert q2 == "what is product market fit"

