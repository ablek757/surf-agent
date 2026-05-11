"""surf-agent CLI."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console

from .agent import SurfAgent
from .config import Config

app = typer.Typer(
    name="surf-agent",
    help="Drive a real browser with natural-language tasks.",
    add_completion=False,
)
console = Console()


@app.command()
def run(
    task: str = typer.Argument(..., help="Natural-language description of the task."),
    url: str | None = typer.Option(None, "--url", "-u", help="Optional starting URL."),
    provider: str | None = typer.Option(
        None, "--provider", "-p", help="Override provider: anthropic | openai | ollama."
    ),
    model: str | None = typer.Option(None, "--model", "-m", help="Override model id."),
    headless: bool = typer.Option(False, "--headless/--headed", help="Run browser headless."),
    max_steps: int = typer.Option(25, "--max-steps", help="Safety cap on agent iterations."),
) -> None:
    """Run a single task and exit."""
    config = Config.from_env()
    if provider:
        config.provider = provider  # type: ignore[assignment]
    if model:
        config.model = model
    config.headless = headless
    config.max_steps = max_steps

    console.print(
        f"[bold]surf-agent[/] · provider=[cyan]{config.provider}[/] "
        f"model=[cyan]{config.resolved_model()}[/] browser=[cyan]{config.browser}[/]"
    )

    agent = SurfAgent(config, console=console)
    result = asyncio.run(agent.run(task, start_url=url))

    console.rule("[bold]Result[/]")
    console.print(result.answer)
    console.print(f"[dim]({result.steps_taken} steps)[/]")


@app.command()
def version() -> None:
    """Print version."""
    from . import __version__

    console.print(f"surf-agent {__version__}")


if __name__ == "__main__":
    app()
