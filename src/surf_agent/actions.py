"""Action schema — the structured commands the LLM can emit each step.

The LLM returns a JSON object matching `AgentStep`. The agent loop executes
the action against the live browser, captures a fresh observation, and feeds
it back to the LLM until the action is `done` or `max_steps` is reached.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ClickAction(BaseModel):
    type: Literal["click"] = "click"
    target_id: int = Field(description="Numeric id from the labeled DOM snapshot.")


class TypeAction(BaseModel):
    type: Literal["type"] = "type"
    target_id: int
    text: str
    submit: bool = Field(
        default=False,
        description="If true, press Enter after typing (useful for search boxes).",
    )


class GotoAction(BaseModel):
    type: Literal["goto"] = "goto"
    url: str


class ScrollAction(BaseModel):
    type: Literal["scroll"] = "scroll"
    direction: Literal["up", "down"] = "down"
    amount: int = Field(default=600, description="Pixels to scroll.")


class WaitAction(BaseModel):
    type: Literal["wait"] = "wait"
    seconds: float = Field(default=1.0, ge=0, le=30)


class BackAction(BaseModel):
    type: Literal["back"] = "back"


class ScreenshotAction(BaseModel):
    """Force the next observation to include a fresh screenshot."""

    type: Literal["screenshot"] = "screenshot"


class DoneAction(BaseModel):
    type: Literal["done"] = "done"
    answer: str = Field(description="Final answer or summary for the user.")


Action = (
    ClickAction
    | TypeAction
    | GotoAction
    | ScrollAction
    | WaitAction
    | BackAction
    | ScreenshotAction
    | DoneAction
)


class AgentStep(BaseModel):
    """Single LLM turn: reasoning + one action."""

    thought: str = Field(description="Brief reasoning about what to do next.")
    action: Action = Field(discriminator="type")


# JSON-schema-style description of the action union, formatted for the LLM
# system prompt. Kept as a hand-written string (rather than emitting from
# pydantic) so it stays compact and stable for prompt caching.
ACTION_GRAMMAR = """\
Each turn you must reply with a JSON object of the shape:
  {"thought": "<short reasoning>", "action": <one of the actions below>}

Available actions:
  {"type": "click",      "target_id": <int>}
  {"type": "type",       "target_id": <int>, "text": "<string>", "submit": <bool>}
  {"type": "goto",       "url": "<https://...>"}
  {"type": "scroll",     "direction": "down"|"up", "amount": <int pixels>}
  {"type": "wait",       "seconds": <float, 0-30>}
  {"type": "back"}
  {"type": "screenshot"}
  {"type": "done",       "answer": "<final answer or summary>"}

Rules:
- `target_id` refers to the numeric id shown in brackets in the DOM snapshot.
- Only one action per turn.
- Use `done` as soon as the task is finished.
- Do NOT include any prose outside the JSON object.
"""
