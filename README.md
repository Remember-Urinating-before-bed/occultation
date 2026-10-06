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

## Check against an independent source

Meeus's Table III rows carry no printed results, so the only independent,
machine-readable statement about them is NAOJ's per-event visibility status.
Re-run the solver for each event and compare it with that saved snapshot:

```bash
uv run python scripts/verify_reference_data.py --trace
```

`--trace` prints the intermediate value of every step of the calculation after
each event's verdict — the geocentric observer coordinates, the local hour
angle `H`, the fundamental-plane `u`/`v` and their rates, the closest-approach
correction, the effective shadow radius `L`, the separation `Delta`, the
position angle `P` and the altitude `h` — so you can see *how* the verdict was
reached. The trace calls the same helper functions the solver uses, so it
cannot drift from the solver's own arithmetic. Drop `--trace` for the
one-line-per-event summary.

### When is an event "not visible"?

An event is reported **not visible** when either of two independent conditions
holds (both must pass for it to be visible):

| Condition | Meaning |
| --- | --- |
| `abs(Delta) > 1` | The body **misses** the Moon — no occultation happens at all |
| `h <= 0` | The body **is** behind the Moon but **below the horizon** — you cannot see it |

In other words `is_visible = is_occultation and h > 0`, where `Delta` (in lunar
radii) decides `is_occultation` and `h` (altitude in degrees) decides whether
the observer can actually see it. For the four Jupiter events at Uccle only
**2019-11-28** is visible: `Delta = +0.0715` (within one lunar radius) and
`h = +2.04 deg` (just above the horizon). The other three fail on both counts
(`Delta = +1.6950`, `+3.2480`, `+5.3095` and `h = -17.69`, `-47.18`, `-59.14`).

## Project Stack

Python 3.12
uv
pyproject.toml
uv.lock
pytest
ruff
mypy or pyright

