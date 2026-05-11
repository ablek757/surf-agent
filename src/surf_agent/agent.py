"""Agent loop: observe -> decide -> act, until `done` or max_steps."""

from __future__ import annotations

import json
from dataclasses import dataclass

from rich.console import Console

from .actions import (
    AgentStep,
    ClickAction,
    DoneAction,
    GotoAction,
    ScreenshotAction,
    ScrollAction,
    TypeAction,
)
from .browser import BrowserController, open_browser
from .config import Config
from .providers import Observation, get_provider


@dataclass
class AgentResult:
    answer: str
    steps_taken: int
    history: list[dict]


class SurfAgent:
    """High-level orchestrator. Holds a config and an LLM provider."""

    def __init__(self, config: Config | None = None, *, console: Console | None = None) -> None:
        self.config = config or Config.from_env()
        self.provider = get_provider(self.config)
        self.console = console or Console()

    async def run(self, task: str, *, start_url: str | None = None) -> AgentResult:
        async with open_browser(self.config) as ctrl:
            if start_url:
                await ctrl.page.goto(start_url, wait_until="domcontentloaded")
            return await self._loop(ctrl, task)

    async def _loop(self, ctrl: BrowserController, task: str) -> AgentResult:
        history: list[dict] = []
        last_result: str | None = None
        force_screenshot = False

        for step_idx in range(1, self.config.max_steps + 1):
            snapshot = await ctrl.refresh_snapshot()

            include_screenshot = force_screenshot or (step_idx == 1) or (step_idx % 4 == 0)
            screenshot_b64 = await ctrl.screenshot_b64() if include_screenshot else None
            force_screenshot = False

            observation = Observation(
                task=task,
                dom_text=snapshot.to_prompt(),
                last_action_result=last_result,
                screenshot_b64=screenshot_b64,
                include_screenshot=include_screenshot,
                history=history,
            )

            self.console.rule(f"[bold cyan]Step {step_idx}[/]")
            self.console.print(f"[dim]URL:[/] {snapshot.url}")

            try:
                step = await self.provider.next_step(observation)
            except ValueError as e:
                self.console.print(f"[red]LLM parse error:[/] {e}")
                last_result = f"error: {e}. Re-emit valid JSON."
                continue

            self.console.print(f"[yellow]thought:[/] {step.thought}")
            self.console.print(f"[green]action:[/] {step.action.model_dump()}")

            history.append({"role": "user", "content": _summarize_observation(observation)})
            history.append({"role": "assistant", "content": _summarize_step(step)})
            history[:] = history[-12:]  # cap context

            if isinstance(step.action, DoneAction):
                self.console.rule("[bold green]Done[/]")
                self.console.print(step.action.answer)
                return AgentResult(
                    answer=step.action.answer, steps_taken=step_idx, history=history
                )

            if isinstance(step.action, ScreenshotAction):
                force_screenshot = True
                last_result = "screenshot will be included next turn"
                continue

            try:
                last_result = await ctrl.execute(step.action)
            except Exception as e:  # noqa: BLE001 — surface error to LLM, don't crash
                last_result = f"action failed: {type(e).__name__}: {e}"
                self.console.print(f"[red]{last_result}[/]")

        return AgentResult(
            answer="(max_steps reached without `done`)",
            steps_taken=self.config.max_steps,
            history=history,
        )


def _summarize_observation(obs: Observation) -> str:
    head = obs.dom_text.splitlines()[:3]
    return "OBSERVATION:\n" + "\n".join(head)


def _summarize_step(step: AgentStep) -> str:
    action = step.action
    if isinstance(action, (ClickAction, TypeAction)):
        return json.dumps({"thought": step.thought, "action": action.model_dump()})
    if isinstance(action, (GotoAction, ScrollAction, DoneAction)):
        return json.dumps({"thought": step.thought, "action": action.model_dump()})
    return json.dumps({"thought": step.thought, "action": action.model_dump()})
