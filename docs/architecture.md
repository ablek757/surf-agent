# Architecture

High-level design notes for `surf-agent`.

## Components

```
src/surf_agent/
├── __init__.py          # public re-exports (SurfAgent, Config)
├── config.py            # env-driven runtime config
├── actions.py           # Pydantic action schema + grammar text
├── dom.py               # DOM snapshot extractor (runs JS in the page)
├── browser.py           # Playwright wrapper; executes Action
├── agent.py             # observe → decide → act loop
├── cli.py               # typer-based CLI
└── providers/
    ├── base.py          # abstract LLMProvider, system prompt, JSON parser
    ├── factory.py       # provider chooser
    ├── anthropic_provider.py
    ├── openai_provider.py
    └── ollama_provider.py
```

## Data flow per step

1. `agent.SurfAgent._loop` calls `BrowserController.refresh_snapshot()`.
2. `dom.snapshot_page()` injects JS that returns visible interactable elements
   in DOM order (links, buttons, inputs, role-based clickables).
3. The Python side wraps each element in `InteractableElement(target_id=i,
   ...)` — `target_id` is the index into the same selector that built the
   snapshot, so it round-trips back to a Playwright locator.
4. Every fourth step (and on step 1) we also capture a PNG screenshot.
5. `Observation` (task + DOM text + optional image + truncated history) goes
   to the LLM.
6. LLM returns a single JSON object. `providers.base.parse_step` extracts and
   validates it as `AgentStep`.
7. `BrowserController.execute(action)` runs it; the result string ("clicked
   element 5", "scrolled down 600px", ...) becomes `last_action_result` for
   the next observation.
8. Loop until `DoneAction` or `max_steps`.

## Why this shape

- **Discriminated-union actions** (Pydantic v2 `Field(discriminator="type")`)
  give us clean, validated actions and fast pattern-matching on the executor
  side. Mistakes from the LLM (bad type, missing field) get caught before
  Playwright is touched.
- **Numbered DOM elements** keep the prompt size bounded — we don't ship
  HTML; the LLM only ever sees ~80 lines like `[3] <button> Sign in`. Numeric
  ids are also more reliable for the LLM than free-text selectors.
- **Hybrid mode** — DOM is the source of truth for clicks, screenshots are
  for visual reasoning. Sending screenshots only every 4 turns trades a bit
  of perception fidelity for ~3-4× lower vision-token cost.
- **Provider abstraction** keeps the agent loop unaware of which LLM is
  driving. Adding a new backend is one file under `providers/`.

## Trade-offs / known gaps

- Snapshot is **viewport-bound** (elements outside the visible area are
  skipped). The agent has to scroll to see more.
- We don't currently follow `iframe`s.
- No persistent storage of cookies/login between runs (see roadmap).
- Anthropic provider doesn't yet wire up `cache_control` on the system prompt
  — easy win for production cost savings.

See `docs/` for additional notes as the project grows.
