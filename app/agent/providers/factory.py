from typing import Optional
from app.core.config import settings
from app.agent.providers.base import BaseLLMProvider
from app.agent.providers.ollama import OllamaProvider
from app.agent.providers.gemini import GeminiProvider
from app.agent.providers.anthropic import AnthropicProvider
from app.agent.providers.openai import OpenAIProvider


def get_llm_provider(
    override_provider: Optional[str] = None,
    override_model: Optional[str] = None
) -> BaseLLMProvider:
    """
    Factory function returning the active LLM provider.
    Defaults to settings.LLM_PROVIDER ('ollama', 'gemini', 'claude', or 'openai').
    """
    provider_name = (override_provider or settings.LLM_PROVIDER).lower().strip()

    if provider_name == "ollama":
        return OllamaProvider(model=override_model)
    elif provider_name == "gemini":
        return GeminiProvider(model=override_model)
    elif provider_name == "claude":
        return AnthropicProvider(model=override_model)
    elif provider_name == "openai":
        return OpenAIProvider(model=override_model)
    else:
        # Fallback to Ollama
        return OllamaProvider(model=override_model)
