from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
from pydantic import BaseModel


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any]


class LLMResponse(BaseModel):
    content: str
    tool_calls: List[ToolCall] = []
    finish_reason: Optional[str] = None


class ProviderHealth(BaseModel):
    provider: str
    model: str
    status: str  # 'reachable', 'unreachable', 'misconfigured'
    latency_ms: Optional[float] = None
    detail: Optional[str] = None


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False
    ) -> LLMResponse:
        """Execute non-streaming completion."""
        pass

    @abstractmethod
    async def stream_generate(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream completion tokens and tool calls."""
        pass

    @abstractmethod
    async def check_health(self) -> ProviderHealth:
        """Verify reachability of the model provider."""
        pass
