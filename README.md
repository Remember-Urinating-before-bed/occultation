# occultation

A learning project that will grow into a Hong Kong astronomical almanac. The
active work-package is **lunar occultation local circumstances** from Jean
Meeus's *Astronomical Tables* — reproduced against the book's own worked
example (Regulus, 1999 March 1, Palomar).

## Start here

| If you want... | Read |
| --- | --- |
| The astronomy, explained with pictures and no jargon | [`docs/explainer.html`](docs/explainer.html) |
| The textbook chapter itself, drawn picture by picture | [`docs/meeus-pictures.html`](docs/meeus-pictures.html) |
| The code base: files, conventions, commands | [`docs/CODEBASE.md`](docs/CODEBASE.md) |
| Python, uv, pytest, Git, CI — assuming no background | [`docs/tooling.html`](docs/tooling.html) |
| Answers to the seven questions the code raised (core/domain, longitude signs, `__init__.py`, uv, mypy, `data/`, `reference/`) | [`docs/tooling.html#questions`](docs/tooling.html#questions) |
| The formulas and their printed-page provenance | [`docs/algorithms/meeus-star-local-circumstances.md`](docs/algorithms/meeus-star-local-circumstances.md) |
| Constraints, defect history, and the milestone roadmap | [`docs/AGENT_HANDOFF.md`](docs/AGENT_HANDOFF.md) |

## Quick start

```bash
uv sync --locked --dev
uv run occultation --help
uv run pytest -q
uv run ruff check . && uv run ruff format --check . && uv run mypy src
```

## Project Stack

Python 3.12
uv
pyproject.toml
uv.lock
pytest
ruff
mypy or pyright

