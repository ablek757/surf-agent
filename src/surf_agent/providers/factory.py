"""Provider factory."""

from __future__ import annotations

from ..config import Config
from .base import LLMProvider


def get_provider(config: Config) -> LLMProvider:
    model = config.resolved_model()
    if config.provider == "anthropic":
        from .anthropic_provider import AnthropicProvider

        return AnthropicProvider(model)
    if config.provider == "openai":
        from .openai_provider import OpenAIProvider

        return OpenAIProvider(model)
    if config.provider == "ollama":
        from .ollama_provider import OllamaProvider

        return OllamaProvider(model)
    raise ValueError(f"Unknown provider: {config.provider}")
