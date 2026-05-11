# Contributing to surf-agent

Thanks for considering a contribution! A few guidelines:

## Development setup

```bash
python -m venv .venv
# activate it
pip install -e ".[all,dev]"
playwright install chromium
pytest -q
```

## Code style

- `ruff check .` must pass.
- Type hints on public functions.
- Keep new dependencies optional — slot them under `[project.optional-dependencies]`
  in `pyproject.toml` whenever possible.

## Pull requests

1. Open an issue first if the change is non-trivial.
2. Add tests for parser/agent logic where practical.
3. Update `README.md` if you add a user-visible feature.
4. Reference the issue number in your PR description.

## Adding an LLM provider

1. Subclass `LLMProvider` in `src/surf_agent/providers/`.
2. Implement `next_step(observation) -> AgentStep`.
3. Wire it into `providers/factory.py`.
4. Add an extra in `pyproject.toml` for its dependencies.

## Adding an action

1. Define a Pydantic model in `actions.py`.
2. Add it to the `Action` union (and `AgentStep.action` discriminator).
3. Document it in the `ACTION_GRAMMAR` string.
4. Handle it in `BrowserController.execute()`.
