import time
from typing import List, Dict, Any, Optional, AsyncGenerator
from openai import AsyncOpenAI
from app.core.config import settings
from app.agent.providers.base import BaseLLMProvider, LLMResponse, ToolCall, ProviderHealth


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI provider using official AsyncOpenAI client.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None

    async def check_health(self) -> ProviderHealth:
        if not self.api_key:
            return ProviderHealth(
                provider="openai",
                model=self.model,
                status="misconfigured",
                detail="OPENAI_API_KEY is not set in environment."
            )
        start_time = time.time()
        try:
            res = await self.client.models.list()
            latency_ms = (time.time() - start_time) * 1000
            return ProviderHealth(
                provider="openai",
                model=self.model,
                status="reachable",
                latency_ms=round(latency_ms, 2),
                detail=f"OpenAI API authenticated successfully with model {self.model}"
            )
        except Exception as e:
            return ProviderHealth(
                provider="openai",
                model=self.model,
                status="unreachable",
                detail=f"OpenAI API call failed: {str(e)}"
            )

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False
    ) -> LLMResponse:
        if not self.client:
            raise RuntimeError("OpenAI provider cannot generate: OPENAI_API_KEY is missing.")

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
            yield {"type": "error", "error": "OPENAI_API_KEY is missing."}
            return

        payload_messages = []
        if system:
            payload_messages.append({"role": "system", "content": system})
        payload_messages.extend(messages)

        stream = await self.client.chat.completions.stream(
            model=self.model,
            messages=payload_messages,
            temperature=0.2
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield {"type": "token", "token": chunk.choices[0].delta.content}
