"""surf-agent: Natural-language-driven browser automation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .config import Config

__version__ = "0.1.0"
__all__ = ["SurfAgent", "Config", "__version__"]

if TYPE_CHECKING:
    from .agent import SurfAgent  # noqa: F401


def __getattr__(name: str) -> Any:
    # Lazy import: keep `from surf_agent import Config` and
    # `import surf_agent.actions` working without requiring Playwright.
    if name == "SurfAgent":
        from .agent import SurfAgent

        return SurfAgent
    raise AttributeError(f"module 'surf_agent' has no attribute {name!r}")
