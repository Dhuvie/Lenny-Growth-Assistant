import time
from typing import List, Dict, Any, Optional, AsyncGenerator
from anthropic import AsyncAnthropic
from app.core.config import settings
from app.agent.providers.base import BaseLLMProvider, LLMResponse, ToolCall, ProviderHealth


class AnthropicProvider(BaseLLMProvider):
    """
    Anthropic Claude provider using official AsyncAnthropic client.
    Maps tools and system prompts to the Claude Messages API format.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or settings.ANTHROPIC_MODEL
        self.client = AsyncAnthropic(api_key=self.api_key) if self.api_key else None

    async def check_health(self) -> ProviderHealth:
        if not self.api_key:
            return ProviderHealth(
                provider="claude",
                model=self.model,
                status="misconfigured",
                detail="ANTHROPIC_API_KEY is not set in environment."
            )
        start_time = time.time()
        try:
            # Send minimal validation request
            res = await self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}]
            )
            latency_ms = (time.time() - start_time) * 1000
            return ProviderHealth(
                provider="claude",
                model=self.model,
                status="reachable",
                latency_ms=round(latency_ms, 2),
                detail=f"Anthropic API authenticated successfully with model {self.model}"
            )
        except Exception as e:
            return ProviderHealth(
                provider="claude",
                model=self.model,
                status="unreachable",
                detail=f"Anthropic API call failed: {str(e)}"
            )

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False
    ) -> LLMResponse:
        if not self.client:
            raise RuntimeError("Anthropic provider cannot generate: ANTHROPIC_API_KEY is missing.")

        claude_tools = []
        if tools:
            for t in tools:
                func = t.get("function", t)
                claude_tools.append({
                    "name": func.get("name"),
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {"type": "object", "properties": {}})
                })

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        if claude_tools:
            kwargs["tools"] = claude_tools

        response = await self.client.messages.create(**kwargs)
        
        content = ""
        tool_calls: List[ToolCall] = []
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input
                ))

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=response.stop_reason
        )

    async def stream_generate(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        if not self.client:
            yield {"type": "error", "error": "ANTHROPIC_API_KEY is missing."}
            return

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system

        async with self.client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield {"type": "token", "token": text}
