import json
import time
import httpx
from typing import List, Dict, Any, Optional, AsyncGenerator
from app.core.config import settings
from app.agent.providers.base import BaseLLMProvider, LLMResponse, ToolCall, ProviderHealth


class OllamaProvider(BaseLLMProvider):
    """
    Local Ollama provider using Ollama's OpenAI-compatible /v1 endpoints.
    Allows tool-calling and token streaming against local models like llama3.1:8b.
    """

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL

    async def check_health(self) -> ProviderHealth:
        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                latency_ms = (time.time() - start_time) * 1000
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name") for m in data.get("models", [])]
                    model_loaded = any(self.model in m for m in models)
                    detail = f"Model '{self.model}' is available." if model_loaded else f"Ollama is running, but '{self.model}' is not pulled yet. Available: {models}"
                    return ProviderHealth(
                        provider="ollama",
                        model=self.model,
                        status="reachable",
                        latency_ms=round(latency_ms, 2),
                        detail=detail
                    )
                return ProviderHealth(
                    provider="ollama",
                    model=self.model,
                    status="unreachable",
                    latency_ms=round(latency_ms, 2),
                    detail=f"Ollama returned HTTP {res.status_code}"
                )
        except Exception as e:
            return ProviderHealth(
                provider="ollama",
                model=self.model,
                status="unreachable",
                detail=f"Cannot connect to Ollama at {self.base_url}: {str(e)}. Run 'ollama serve' to start."
            )

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False
    ) -> LLMResponse:
        payload_messages = []
        if system:
            payload_messages.append({"role": "system", "content": system})
        payload_messages.extend(messages)

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": payload_messages,
            "stream": False,
            "temperature": 0.2
        }
        if tools:
            payload["tools"] = tools

        url = f"{self.base_url}/v1/chat/completions"
        async with httpx.AsyncClient(timeout=120.0) as client:
            res = await client.post(url, json=payload)
            if res.status_code != 200:
                raise RuntimeError(f"Ollama error ({res.status_code}): {res.text}")
            data = res.json()
            choice = data["choices"][0]
            msg = choice.get("message", {})
            content = msg.get("content", "") or ""

            parsed_tool_calls: List[ToolCall] = []
            if "tool_calls" in msg and msg["tool_calls"]:
                for tc in msg["tool_calls"]:
                    func = tc.get("function", {})
                    name = func.get("name", "")
                    try:
                        args = json.loads(func.get("arguments", "{}"))
                    except Exception:
                        args = {}
                    parsed_tool_calls.append(ToolCall(
                        id=tc.get("id", f"call_{int(time.time()*1000)}"),
                        name=name,
                        arguments=args
                    ))

            return LLMResponse(
                content=content,
                tool_calls=parsed_tool_calls,
                finish_reason=choice.get("finish_reason")
            )

    async def stream_generate(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        payload_messages = []
        if system:
            payload_messages.append({"role": "system", "content": system})
        payload_messages.extend(messages)

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": payload_messages,
            "stream": True,
            "temperature": 0.2
        }
        if tools:
            payload["tools"] = tools

        url = f"{self.base_url}/v1/chat/completions"
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    err_text = await response.aread()
                    yield {"type": "error", "error": f"Ollama error ({response.status_code}): {err_text.decode('utf-8')}"}
                    return

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data: "):
                        continue
                    if line == "data: [DONE]":
                        break
                    json_str = line[6:]
                    try:
                        chunk = json.loads(json_str)
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta and delta["content"]:
                            yield {"type": "token", "token": delta["content"]}
                        if "tool_calls" in delta and delta["tool_calls"]:
                            yield {"type": "tool_call_delta", "tool_calls": delta["tool_calls"]}
                    except Exception:
                        continue
