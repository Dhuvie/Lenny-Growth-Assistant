import time
from typing import List, Dict, Any, Optional, AsyncGenerator
from openai import AsyncOpenAI
import httpx

from app.core.config import settings
from app.agent.providers.base import BaseLLMProvider, LLMResponse, ToolCall, ProviderHealth


class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini cloud provider using Google's OpenAI-compatible API endpoint.
    Supports multiple Gemini models:
    - gemini-3.5-flash-lite (cost-optimized high-volume inference)
    - gemini-3.8-flash (state of the art fast reasoning)
    - gemini-3.7-flash (hybrid reasoning and multimodal orchestration)
    - gemini-2.5-flash (fast efficient cloud tier)
    - gemini-2.5-pro (deep reasoning flagship tier)
    - gemini-2.0-flash (stable multimodal tier)
    """

    AVAILABLE_MODELS = [
        "gemini-3.5-flash-lite",
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.0-flash",
    ]

    GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self.client = AsyncOpenAI(
            api_key=self.api_key or "missing-key",
            base_url=self.GEMINI_BASE_URL
        ) if self.api_key else None

    async def check_health(self) -> ProviderHealth:
        if not self.api_key:
            return ProviderHealth(
                provider="gemini",
                model=self.model,
                status="misconfigured",
                detail="GEMINI_API_KEY is not configured in environment. Add GEMINI_API_KEY to .env."
            )

        start_time = time.time()
        try:
            # Probe Google Gemini models endpoint
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
                )
                latency_ms = (time.time() - start_time) * 1000

                if res.status_code == 200:
                    return ProviderHealth(
                        provider="gemini",
                        model=self.model,
                        status="reachable",
                        latency_ms=round(latency_ms, 2),
                        detail=f"Google Gemini authenticated successfully. Active model: {self.model}"
                    )
                elif res.status_code == 400 or res.status_code == 403:
                    return ProviderHealth(
                        provider="gemini",
                        model=self.model,
                        status="unreachable",
                        latency_ms=round(latency_ms, 2),
                        detail=f"Google Gemini authentication failed (HTTP {res.status_code}). Please verify GEMINI_API_KEY."
                    )
                else:
                    return ProviderHealth(
                        provider="gemini",
                        model=self.model,
                        status="degraded",
                        latency_ms=round(latency_ms, 2),
                        detail=f"Google Gemini returned HTTP {res.status_code}."
                    )
        except Exception as e:
            return ProviderHealth(
                provider="gemini",
                model=self.model,
                status="unreachable",
                detail=f"Google Gemini connection failed: {str(e)}"
            )

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False
    ) -> LLMResponse:
        if not self.client:
            raise RuntimeError("Gemini provider cannot generate: GEMINI_API_KEY is missing.")

        payload_messages = []
        if system:
            payload_messages.append({"role": "system", "content": system})
        payload_messages.extend(messages)

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": payload_messages,
            "temperature": 0.2
        }
        if tools:
            kwargs["tools"] = tools

        response = await self.client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        msg = choice.message
        content = msg.content or ""

        tool_calls: List[ToolCall] = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                import json
                try:
                    args = json.loads(tc.function.arguments)
                except Exception:
                    args = {}
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=args
                ))

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason
        )

    async def stream_generate(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        if not self.client:
            yield {"type": "error", "error": "GEMINI_API_KEY is missing. Please set it in .env to use Google Gemini."}
            return

        payload_messages = []
        if system:
            payload_messages.append({"role": "system", "content": system})
        payload_messages.extend(messages)

        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=payload_messages,
                temperature=0.2,
                stream=True
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield {"type": "token", "token": chunk.choices[0].delta.content}
        except Exception as e:
            yield {"type": "error", "error": f"Google Gemini API error ({self.model}): {str(e)}"}
