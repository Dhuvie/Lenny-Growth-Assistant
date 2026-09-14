from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class LLMProviderStatus(BaseModel):
    provider: str
    model: str
    status: str  # 'reachable', 'unreachable', 'misconfigured'
    latency_ms: Optional[float] = None
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: str  # 'healthy', 'degraded', 'unhealthy'
    database: str  # 'connected', 'error'
    llm_provider: LLMProviderStatus
    indexed_episodes: int
    indexed_chunks: int
    timestamp: datetime
