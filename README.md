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
| A short review note: what the CLI does and the proof it matches the book | [`docs/FOR_REVIEW.md`](docs/FOR_REVIEW.md) |
| Constraints, defect history, and the milestone roadmap | [`docs/AGENT_HANDOFF.md`](docs/AGENT_HANDOFF.md) |

## Quick start

```bash
uv sync --locked --dev
uv run occultation --help
uv run pytest -q
uv run ruff check . && uv run ruff format --check . && uv run mypy src
```

## Run the calculation

Re-run the textbook's worked example (Meeus Example 5, Regulus, 1999 March 1)
and compare every printed value with this repository's own calculation:

```bash
uv run occultation verify meeus-example-5
```

Local circumstances for an observer, from an elements file and a site file:

```bash
uv run occultation local-circumstances \
  --elements tests/fixtures/meeus_regulus_1999.json \
  --location config/locations/hong_kong.toml \
  --delta-t-seconds 65
```

Add `--format json` for machine-readable output, `--engine compare` to see the
reference engine's availability, or `--help` for the inline-parameter form.
Exit codes: `0` success, `1` a printed value did not match, `2` bad usage or
input, `3` the reference engine is unavailable.

## Project Stack

Python 3.12
uv
pyproject.toml
uv.lock
pytest
ruff
mypy or pyright

