"""Runtime configuration for surf-agent.

Loaded from environment variables (and optionally a `.env` file).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from dotenv import load_dotenv

ProviderName = Literal["anthropic", "openai", "ollama"]
BrowserName = Literal["chromium", "firefox", "webkit"]

_DEFAULT_MODELS: dict[str, str] = {
    "anthropic": "claude-opus-4-7",
    "openai": "gpt-4o",
    "ollama": "qwen2.5:7b",
}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Config:
    provider: ProviderName = "anthropic"
    model: str | None = None
    headless: bool = False
    browser: BrowserName = "chromium"
    max_steps: int = 25
    viewport_width: int = 1280
    viewport_height: int = 800

    @classmethod
    def from_env(cls, *, load_dotenv_file: bool = True) -> "Config":
        if load_dotenv_file:
            load_dotenv()

        provider = (os.getenv("SURF_AGENT_PROVIDER") or "anthropic").lower()
        if provider not in _DEFAULT_MODELS:
            raise ValueError(
                f"Unknown SURF_AGENT_PROVIDER={provider!r}. "
                f"Expected one of: {', '.join(_DEFAULT_MODELS)}"
            )

        browser = (os.getenv("SURF_AGENT_BROWSER") or "chromium").lower()
        if browser not in {"chromium", "firefox", "webkit"}:
            raise ValueError(f"Unknown SURF_AGENT_BROWSER={browser!r}")

        return cls(
            provider=provider,  # type: ignore[arg-type]
            model=os.getenv("SURF_AGENT_MODEL"),
            headless=_env_bool("SURF_AGENT_HEADLESS", False),
            browser=browser,  # type: ignore[arg-type]
            max_steps=int(os.getenv("SURF_AGENT_MAX_STEPS", "25")),
        )

    def resolved_model(self) -> str:
        return self.model or _DEFAULT_MODELS[self.provider]
