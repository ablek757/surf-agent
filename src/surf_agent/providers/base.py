"""Common LLM provider interface.

All providers take the same `Observation` (task + current DOM snapshot text +
optional screenshot + history) and return a parsed `AgentStep` (thought +
action). Hybrid DOM+screenshot mode is driven by the `include_screenshot` flag
on the observation; providers that don't support vision just ignore it.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from pydantic import ValidationError

from ..actions import ACTION_GRAMMAR, AgentStep


SYSTEM_PROMPT = f"""\
You are surf-agent, a careful web-browsing agent. A user describes a task in
natural language; you drive a real browser to accomplish it.

You perceive the page through two channels:
  1. A DOM snapshot listing interactable elements with numeric ids: [0], [1], ...
  2. (Sometimes) a screenshot of the current viewport.

Use the DOM snapshot as the source of truth for `target_id` values. Use the
screenshot to disambiguate layout, read charts/images, or recover when the
DOM looks ambiguous.

{ACTION_GRAMMAR}
Be decisive: one action per turn, no more than 25 turns total. If a page is
still loading, use `wait`. If you're lost, use `back` or `goto`. When the
task is complete, emit `done` with a concise answer.
"""


@dataclass
class Observation:
    task: str
    dom_text: str
    last_action_result: str | None = None
    screenshot_b64: str | None = None
    include_screenshot: bool = False
    history: list[dict] = field(default_factory=list)  # [{role, content}, ...]


def parse_step(raw_text: str) -> AgentStep:
    """Parse an LLM response into an `AgentStep`.

    Accepts raw JSON, or JSON wrapped in a ```json ... ``` fence.
    """
    text = raw_text.strip()

    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if fence:
        text = fence.group(1)
    else:
        # Fall back to the first balanced-looking JSON object.
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            text = text[start : end + 1]

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM response was not valid JSON: {e}\n---\n{raw_text[:500]}") from e

    try:
        return AgentStep.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"LLM response did not match action schema: {e}") from e


class LLMProvider(ABC):
    """Abstract base. One `next_step()` call == one agent turn."""

    name: str = "base"

    def __init__(self, model: str) -> None:
        self.model = model

    @abstractmethod
    async def next_step(self, observation: Observation) -> AgentStep:
        """Return the LLM's decision for the next action."""

    def _build_user_text(self, observation: Observation) -> str:
        parts = [f"TASK: {observation.task}", "", observation.dom_text]
        if observation.last_action_result:
            parts.append("")
            parts.append(f"PREVIOUS ACTION RESULT: {observation.last_action_result}")
        parts.append("")
        parts.append("Respond with a single JSON object: {\"thought\": ..., \"action\": ...}")
        return "\n".join(parts)
