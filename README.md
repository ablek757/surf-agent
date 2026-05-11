# surf-agent 🏄

> **English** · [中文](./README.zh.md)

> **Drive a real browser with natural language.** Tell `surf-agent` what you
> want done — *"find the cheapest flight from SFO to NRT next Tuesday"*,
> *"register me for the talk"*, *"summarize my GitHub notifications"* — and an
> LLM agent perceives the page, decides the next click, and executes it
> through Playwright until the task is complete.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

---

## ✨ Features

- **Natural-language tasks.** No selectors, no XPath, no CSS. Describe the goal.
- **Hybrid perception.** A labeled DOM snapshot (token-frugal) **plus** periodic
  screenshots (for layout / visual reasoning) gives the LLM both worlds.
- **Multiple LLM backends.** Anthropic Claude, OpenAI (and OpenAI-compatible
  endpoints), or fully local **Ollama** — picked at runtime.
- **Playwright-powered.** Chromium / Firefox / WebKit, headless or headed.
- **Structured actions.** The LLM emits a typed JSON action each turn —
  `click`, `type`, `goto`, `scroll`, `wait`, `back`, `screenshot`, `done`.
  Validated by Pydantic before it touches the browser.
- **Composable.** Use the CLI, or import `SurfAgent` from Python.
- **Safety rails.** Hard cap on steps, snapshot truncation, structured logs.

## 🎯 Architecture at a glance

```
                        ┌───────────────────────────┐
   user task ──────────▶│        SurfAgent          │
                        │  (observe → decide → act) │
                        └─────────────┬─────────────┘
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            ▼                         ▼                         ▼
    ┌───────────────┐         ┌───────────────┐         ┌───────────────┐
    │ DOM snapshot  │         │  LLM provider │         │   Playwright  │
    │ + screenshot  │ ───────▶│  (Claude /    │ ───────▶│   browser     │
    │ (perception)  │         │   OpenAI /    │         │   (actuation) │
    │               │◀─────── │   Ollama)     │◀─────── │               │
    └───────────────┘         └───────────────┘         └───────────────┘
                                      ▲
                              structured JSON
                              action schema
```

Each turn, the agent:

1. Snapshots the page into a numbered list of interactable elements
   (`[0] <button> Sign in`, `[1] <input:text> Search ...`).
2. Sends DOM + (every few turns) a screenshot to the LLM.
3. Receives `{"thought": "...", "action": {"type": "click", "target_id": 0}}`.
4. Validates the action and runs it via Playwright.
5. Repeats until the LLM emits `{"type": "done", "answer": "..."}` or
   `max_steps` is reached.

## 🚀 Quickstart

### 1. Install

```bash
git clone https://github.com/ablek757/surf-agent.git
cd surf-agent
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate

pip install -e ".[anthropic]"   # or [openai], [ollama], or [all]
playwright install chromium
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY (or set SURF_AGENT_PROVIDER=ollama)
```

### 3. Run

```bash
surf-agent run "Search Wikipedia for 'Playwright (software)' and tell me who maintains it." \
    --url https://www.wikipedia.org
```

You'll see the browser open, the agent narrate each step, and a final answer
like:

```
✔ Done
Playwright is maintained by Microsoft.
(7 steps)
```

## 🐍 Python API

```python
import asyncio
from surf_agent import SurfAgent, Config

async def main():
    agent = SurfAgent(Config(provider="anthropic", headless=False))
    result = await agent.run(
        task="Find the latest release of Playwright on GitHub and tell me the version.",
        start_url="https://github.com/microsoft/playwright/releases",
    )
    print(result.answer)
    print(f"steps: {result.steps_taken}")

asyncio.run(main())
```

## ⚙️ Configuration

All settings have env-var equivalents (see [`.env.example`](.env.example)):

| Setting          | Env var                  | Default            | Notes                                  |
| ---------------- | ------------------------ | ------------------ | -------------------------------------- |
| Provider         | `SURF_AGENT_PROVIDER`    | `anthropic`        | `anthropic`, `openai`, `ollama`        |
| Model            | `SURF_AGENT_MODEL`       | per-provider       | e.g. `claude-opus-4-7`, `gpt-4o`       |
| Browser          | `SURF_AGENT_BROWSER`     | `chromium`         | `chromium` / `firefox` / `webkit`      |
| Headless         | `SURF_AGENT_HEADLESS`    | `false`            | Set `true` for CI                      |
| Max steps        | `SURF_AGENT_MAX_STEPS`   | `25`               | Hard safety cap                        |
| Anthropic key    | `ANTHROPIC_API_KEY`      | —                  | Required for Claude                    |
| OpenAI key       | `OPENAI_API_KEY`         | —                  | Required for OpenAI                    |
| Ollama host      | `OLLAMA_HOST`            | `localhost:11434`  | For local models                       |

CLI flags override env vars: `--provider`, `--model`, `--headless/--headed`,
`--max-steps`, `--url`.

## 🧠 The action schema

The LLM is constrained to a small, typed action vocabulary — defined in
[`actions.py`](src/surf_agent/actions.py) and validated with Pydantic. Adding
a new action is a three-line change: define a Pydantic model, add it to the
`Action` union, and document it in `ACTION_GRAMMAR`.

```jsonc
// Example responses the agent might receive from the LLM
{"thought": "I need to log in first.", "action": {"type": "click", "target_id": 4}}
{"thought": "Search for the topic.",   "action": {"type": "type", "target_id": 0, "text": "playwright", "submit": true}}
{"thought": "Got the answer.",         "action": {"type": "done", "answer": "Maintained by Microsoft."}}
```

## 🔬 Why hybrid perception?

Pure-screenshot agents are flexible but expensive (vision tokens) and brittle
on tiny / dense UIs. Pure-DOM agents are cheap and precise but blind to
layout, charts, captchas, and visual context. **surf-agent does both:**

- The DOM snapshot is **always** included — that's where `target_id`s come
  from, so clicks are deterministic.
- A screenshot is included on **step 1** (initial orientation) and every
  **4 steps** thereafter. The LLM can also explicitly request one with
  `{"type": "screenshot"}`.

Tune the cadence by editing `_loop` in [`agent.py`](src/surf_agent/agent.py).

## 🧪 Tests

```bash
pip install -e ".[dev]"
pytest -q
```

The included tests cover action-schema parsing and don't need a browser or
API key. Real browser tests are out of scope for now — contributions welcome.

## 🗺️ Roadmap

- [ ] Trace + replay (export every `(snapshot, action)` pair)
- [ ] Cookie / login-state persistence between runs
- [ ] Multi-tab support
- [ ] Parallel agents over a queue of tasks
- [ ] Real prompt caching for the Anthropic provider (the system prompt is
      already constant — wire up `cache_control`)
- [ ] More tools: `download_file`, `extract_table`, `select_option`

## ⚠️ Safety & ethics

- **The agent will do what you tell it.** Don't aim it at sites you don't
  control without understanding the consequences (purchases, account
  changes, ToS violations).
- **Keep API keys out of git.** `.env` is gitignored; use `.env.example` as
  the template.
- **Respect robots.txt and rate limits.** This is a research-grade tool, not
  a stealth scraper.

## 🤝 Contributing

PRs welcome. Please:

1. Open an issue describing the change.
2. Add tests for parser/agent logic where practical.
3. Run `ruff check .` before submitting.

## 📄 License

[MIT](LICENSE) © surf-agent contributors.
