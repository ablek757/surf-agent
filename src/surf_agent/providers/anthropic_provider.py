"""Anthropic Claude provider.

The system prompt is constant across every turn within a run, so we mark it
with `cache_control: ephemeral`. Caveat: today's prompt (~500 tokens) is
below Anthropic's minimum cacheable prefix (4096 tokens on Opus, 2048 on
Sonnet/Haiku 4.5), so the marker silently no-ops. It's wired up so caching
"just works" once the prompt grows past the threshold — e.g. when we add
few-shot exemplars, per-site instructions, or a tool catalog.

To see real numbers from your run, set SURF_AGENT_CACHE_DEBUG=1.
"""

from __future__ import annotations

import os

from ..actions import AgentStep
from .base import SYSTEM_PROMPT, LLMProvider, Observation, parse_step


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, model: str) -> None:
        super().__init__(model)
        try:
            import anthropic
        except ImportError as e:
            raise ImportError(
                "anthropic not installed. Run: pip install 'surf-agent[anthropic]' "
                "or pip install anthropic"
            ) from e
        self._client = anthropic.AsyncAnthropic()
        # Surface cache stats once per process if SURF_AGENT_CACHE_DEBUG is set.
        self._debug_cache = os.getenv("SURF_AGENT_CACHE_DEBUG", "").lower() in {
            "1",
            "true",
            "yes",
        }

    async def next_step(self, observation: Observation) -> AgentStep:
        user_text = self._build_user_text(observation)

        content: list[dict] = []
        if observation.include_screenshot and observation.screenshot_b64:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": observation.screenshot_b64,
                    },
                }
            )
        content.append({"type": "text", "text": user_text})

        messages = [*observation.history, {"role": "user", "content": content}]

        response = await self._client.messages.create(
            model=self.model,
            max_tokens=1024,
            # Structured system: a single text block carrying the cache breakpoint.
            # Tools (none today) + system render before messages, so this marker
            # caches the entire stable prefix.
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                },
            ],
            messages=messages,
        )

        if self._debug_cache and getattr(response, "usage", None):
            u = response.usage
            print(
                f"[cache] read={getattr(u, 'cache_read_input_tokens', 0)} "
                f"write={getattr(u, 'cache_creation_input_tokens', 0)} "
                f"input={u.input_tokens}"
            )

        text_parts = [b.text for b in response.content if getattr(b, "type", None) == "text"]
        raw = "\n".join(text_parts).strip()
        return parse_step(raw)
