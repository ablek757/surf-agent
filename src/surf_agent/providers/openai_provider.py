"""OpenAI (and OpenAI-compatible) provider."""

from __future__ import annotations

import os

from ..actions import AgentStep
from .base import SYSTEM_PROMPT, LLMProvider, Observation, parse_step


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, model: str) -> None:
        super().__init__(model)
        try:
            from openai import AsyncOpenAI
        except ImportError as e:
            raise ImportError(
                "openai not installed. Run: pip install 'surf-agent[openai]' "
                "or pip install openai"
            ) from e
        base_url = os.getenv("OPENAI_BASE_URL")
        self._client = AsyncOpenAI(base_url=base_url) if base_url else AsyncOpenAI()

    async def next_step(self, observation: Observation) -> AgentStep:
        user_text = self._build_user_text(observation)

        user_content: list[dict] = [{"type": "text", "text": user_text}]
        if observation.include_screenshot and observation.screenshot_b64:
            user_content.insert(
                0,
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{observation.screenshot_b64}"
                    },
                },
            )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *observation.history,
            {"role": "user", "content": user_content},
        ]

        response = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
            max_tokens=1024,
        )
        raw = response.choices[0].message.content or ""
        return parse_step(raw)
