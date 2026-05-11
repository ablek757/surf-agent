"""Local Ollama provider (no API key needed)."""

from __future__ import annotations

import os

from ..actions import AgentStep
from .base import SYSTEM_PROMPT, LLMProvider, Observation, parse_step


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, model: str) -> None:
        super().__init__(model)
        try:
            import ollama
        except ImportError as e:
            raise ImportError(
                "ollama not installed. Run: pip install 'surf-agent[ollama]' "
                "or pip install ollama"
            ) from e
        host = os.getenv("OLLAMA_HOST")
        self._client = ollama.AsyncClient(host=host) if host else ollama.AsyncClient()

    async def next_step(self, observation: Observation) -> AgentStep:
        user_text = self._build_user_text(observation)

        message: dict = {"role": "user", "content": user_text}
        if observation.include_screenshot and observation.screenshot_b64:
            # Ollama accepts base64 image strings via the `images` field.
            message["images"] = [observation.screenshot_b64]

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *observation.history,
            message,
        ]

        response = await self._client.chat(
            model=self.model,
            messages=messages,
            format="json",
            options={"temperature": 0.2},
        )
        raw = response["message"]["content"]
        return parse_step(raw)
