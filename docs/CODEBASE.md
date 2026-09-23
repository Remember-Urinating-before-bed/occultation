# Code base tour

Companion to [`explainer.html`](explainer.html) (Part 1: the astronomy, with
pictures). This file is Part 2: **what the code is, where it lives, and how to
run it.**

Verified against the working tree on 2026-09-15, branch
`feat/meeus-star-local-circumstances`, commit `b5dd853`.

## 1. What the repository is

`occultation` is a learning project that will eventually generate a Hong Kong
astronomical almanac. The **active work-package** is much narrower: compute the
*local circumstances* of a lunar occultation of a star from Jean Meeus's
*Astronomical Tables*, and prove the result against the book's own worked
example.

Three things are true at once, and mixing them up causes most confusion:

| Layer | What it is | State today |
| --- | --- | --- |
| **Reference engine** | Trusted third-party calculation used to get a first working answer and expected values (planned: Skyfield + a local JPL ephemeris) | **A placeholder only.** `reference/skyfield_engine.py` raises `ReferenceEngineUnavailable`; nothing imports Skyfield |
| **Custom core** | Textbook/standards formulas implemented in this repository | `core/observer_coordinates.py`, `core/local_circumstances.py` |
| **Comparison layer** | Runs both engines on identical inputs and reports differences | `--engine compare` reports the reference engine's availability; it cannot yet report a difference |

The custom core must never import from `occultation.reference`. The rule is now
tested: `tests/unit/test_reference_engine.py` asserts that importing the
reference package does not pull Skyfield in, and the CLI exits `3` rather than
present a custom-core number under a reference label.

The current work-package deliberately needs **no ephemeris and no Skyfield**:
Meeus's method takes the Moon's Besselian elements as *inputs* copied from the
printed tables.

## 2. The single calculation this project performs

```text
inputs                                  output
------                                  ------
star occultation elements  ──┐
                             ├──►  calculate_star_local_circumstances  ──►  StarOccultationResult
observer location          ──┘
Delta T (seconds)          ──┘
```

It answers: *at what instant is the star closest to the Moon's centre as seen
from this observer, how far apart are they, where on the lunar limb would the
star disappear, and is the event above the horizon?*

The algorithm is documented formula by formula, with printed-page citations, in
[`algorithms/meeus-star-local-circumstances.md`](algorithms/meeus-star-local-circumstances.md).
Read that before changing any number in `core/`.


## 3. Directory map

```text
occultation/
├── AGENTS.md                     # entry instruction for AI assistants
├── README.md                     # project stack one-liner
├── pyproject.toml                # uv_build backend, deps, console script
├── uv.lock                       # locked dependency graph (CI uses --locked)
├── dataflow.mmd                  # ASPIRATIONAL pipeline sketch — not implemented
├── .github/workflows/ci.yml      # primary CI: lint, format, types, tests
├── .gitlab-ci.yml                # mirror CI: the same gate, one pipeline per change
├── config/locations/
│   └── hong_kong.toml            # HK site, east-positive longitude, WGS84
├── data/
│   ├── README.md                 # external-data policy (no silent downloads)
│   └── manifest.json             # currently zero datasets
├── docs/
│   ├── AGENT_HANDOFF.md          # authoritative engineering handoff (1600+ lines)
│   ├── FOR_REVIEW.md             # short review note: what the CLI does, and the proof
│   ├── explainer.html            # Part 1: the topic, for beginners
│   ├── CODEBASE.md               # Part 2: this file
│   └── algorithms/
│       └── meeus-star-local-circumstances.md
├── src/occultation/
│   ├── __init__.py               # docstring only; no logic
│   ├── cli.py                    # local-circumstances + verify subcommands
│   ├── io/                       # files in, domain values out; no astronomy
│   │   ├── elements_file.py      # JSON elements document → StarOccultationElements
│   │   └── location_file.py      # .json/.toml site → ObserverLocation
│   ├── reference/                # may import core; core may never import this
│   │   └── skyfield_engine.py    # placeholder that raises, not a calculation
│   ├── domain/                   # pure data + validation, no maths
│   │   ├── observer.py           # ObserverLocation
│   │   └── occultation.py        # FundamentalPlanePolynomial, StarOccultationElements,
│   │                             #   StarOccultationResult
│   └── core/                     # custom maths (may not import occultation.reference)
│       ├── observer_coordinates.py   # geographical → geocentric observer
│       └── local_circumstances.py    # the iterative closest-approach solver
└── tests/
    ├── test_cli.py               # subcommands, exit codes, JSON shape
    ├── unit/test_observer_coordinates.py
    ├── unit/test_elements_file.py
    ├── unit/test_location_file.py
    ├── unit/test_reference_engine.py
    ├── reference_cases/test_meeus_regulus.py   # the textbook regression
    └── fixtures/
        ├── meeus_regulus_1999.toml   # Example 5 inputs and expected values
        └── meeus_regulus_1999.json   # the same, for the CLI; a test asserts equality
```

`local/` also exists but is **git-ignored** (`local/.gitignore` contains `*`). It
holds the scanned textbook, OCR artefacts and scratch notes. Nothing there is
part of the repository.

## 4. File-by-file

### `src/occultation/domain/observer.py`

`ObserverLocation(longitude_deg_east, latitude_deg, elevation_m)`. Frozen
dataclass; validates finite values, longitude in [-180, 180], latitude in
[-90, 90], elevation ≥ -500 m. **Longitude is east-positive** — Meeus prints
west-positive, so every fixture flips the sign.

### `src/occultation/domain/occultation.py`

- `FundamentalPlanePolynomial` — one quadratic Besselian coordinate,
  `X0 + X1 t + X2 t²`, with `value_at(t)` and `rate_at(t)`.
- `StarOccultationElements` — the event inputs: reference hour in Dynamical
  Time, star declination, Greenwich hour angle and its hourly rate, the two
  shadow polynomials, and the shadow radius (`k = 0.272495` for a star).
  The declination rate `D1` and aberration term `F` are deliberately absent:
  both vanish for a star.
- `StarOccultationResult` — the answer: hours after reference, TD and UT hours,
  separation in Moon radii, position angle, altitude, `is_occultation`, and
  `iteration_count`. `limb_clearance_in_moon_radii` is a derived property
  (`|separation| - 1`, negative when occulted).

### `src/occultation/core/observer_coordinates.py`

`calculate_geocentric_observer(ObserverLocation) -> GeocentricObserverCoordinates`
implementing Meeus printed p. 224 with `k' = 0.99664719` and
`a = 6378140 m`. Returns `rho sin φ'` and `rho cos φ'`; the geocentric latitude
itself is never needed on its own.

### `src/occultation/core/local_circumstances.py`

The solver. `calculate_star_local_circumstances(elements, observer, delta_t_seconds, *, convergence_tolerance_hours=1e-6, max_iterations=20)`
starts from Meeus's prescribed `t = 0`, evaluates the star–Moon relative
position and velocity in the fundamental plane, jumps to the instant of closest
approach (`τ = -(u u' + v v') / n²`), and repeats until `|τ|` is below tolerance.
For the textbook example that is **four** iterations.

Private helpers, each one formula: `_relative_motion_at`, `_local_hour_angle_deg`,
`_closest_approach_correction` (τ), `_normalized_separation` (Δ),
`_position_angle_deg` (P, via `atan2(-u, -v)` for the quadrant rule),
`_star_altitude_deg` (h), `_validate_solver_options`.

### `src/occultation/cli.py`

Two subcommands, and no astronomy in the file at all: it parses arguments, hands
them to `io/` to become domain values, calls the custom core (or the reference
placeholder), and formats the answer.

```bash
uv run occultation local-circumstances \
  --elements tests/fixtures/meeus_regulus_1999.json \
  --location config/locations/hong_kong.toml \
  --delta-t-seconds 65
uv run occultation verify meeus-example-5
```

`local-circumstances` accepts either a file or the equivalent inline options for
both the elements and the observer. It refuses to mix the two, and
`--delta-t-seconds` is required because ΔT is never guessed. `--format json`
emits `{engine, algorithm, inputs, derived, result[, comparison]}`; `--engine
skyfield` exits `3`; `--engine compare` adds the comparison block. `verify`
re-runs a published example from the fixture the regression test also reads and
exits `1` on a mismatch. Exit codes: `0` success, `1` mismatch, `2` bad
usage/input, `3` reference engine unavailable.

### `src/occultation/io/`

`elements_file.py` reads the JSON elements document (validating and naming
anything missing) and `location_file.py` reads a site from `.json` or `.toml` —
the first code in the repository that actually reads
`config/locations/hong_kong.toml`. Neither performs astronomy, and neither may
import `occultation.reference`.

### `src/occultation/reference/`

`skyfield_engine.py` exists so the command line can offer `--engine skyfield`
and `--engine compare` with a stable interface. It raises
`ReferenceEngineUnavailable` rather than returning a number; milestone 1
replaces the body with a real Skyfield calculation against a local ephemeris.

### `tests/`

- `test_cli.py` — program name, the declared console-script target is
  `occultation.cli:main`, `--help` prints real usage, `--version` prints `0.1.0`,
  plus the subcommands: exit codes, both input styles, JSON shape, the mismatch
  path, and the missing-file and malformed-JSON messages.
- `unit/test_observer_coordinates.py` — Palomar geocentric values from the book,
  southern-hemisphere signs, latitude validation.
- `unit/test_elements_file.py` — the elements loader, including that the JSON
  fixture and the TOML fixture agree field by field.
- `unit/test_location_file.py` — the site loader, JSON and TOML paths.
- `unit/test_reference_engine.py` — the placeholder refuses to answer, and
  importing `occultation.reference` does not import Skyfield.
- `reference_cases/test_meeus_regulus.py` + `tests/fixtures/meeus_regulus_1999.toml`
  — the regression that pins the whole calculation to Meeus Example 5.


## 5. The regression that proves it works

Meeus Example 5: occultation of Regulus, 1 March 1999, Palomar Mountain
Observatory. The book prints both the inputs and the results, so the test can
assert every published digit.

```text
                     book        code
rho sin phi'       +0.546862    0.546862
rho cos phi'       +0.836338    0.836338
t                  +0.455608    0.455608
Delta              +1.1526      1.152556
|Delta| - 1         0.1526      0.152556
P (formula 4)      24.67 deg    24.6654
h (formula 8)      +43 deg      42.6499
occulted?          no           no
```

Tolerances follow the number of digits the book prints (`abs=5e-6` on `t`,
`abs=2e-4` on the UT hour, `abs=5e-4` on Δ, `abs=0.02` on P, `abs=0.5` on h).
**Never tighten a tolerance below what the source supports.**

Two traps this code base has already paid for, both documented in
`docs/algorithms/` §6 and Appendix B of the handoff:

1. `η'` multiplies **ξ**, not ζ. With the wrong Greek letter the example
   converges to `t = 0.449736` instead of `0.455608`. The disambiguating
   evidence is Meeus's own BASIC listing on printed p. 236.
2. The solver starts at `t = 0` (printed p. 224) and needs four iterations at
   `|τ| < 1e-6` h. The test asserts that derived count; change the starting
   guess or the tolerance and you must re-derive it.

## 6. Run it

```bash
uv sync --locked --dev          # create/refresh the environment (Python 3.12)
uv run occultation --help       # usage for both subcommands
uv run occultation --version    # 0.1.0

uv run occultation verify meeus-example-5          # re-run the book's example
uv run occultation verify meeus-example-5 --format json
uv run occultation local-circumstances \
  --elements tests/fixtures/meeus_regulus_1999.json \
  --location config/locations/hong_kong.toml \
  --delta-t-seconds 65

uv run pytest -q                # 40 tests
uv run pytest tests/reference_cases/test_meeus_regulus.py -q
uv run pytest --cov=occultation --cov-report=term-missing   # 90% coverage today

uv run ruff check .             # lint
uv run ruff format --check .    # formatting
uv run mypy src                 # type check
```

All of the above are green as of the verification date. Two pipelines run exactly
this set:

- `.github/workflows/ci.yml` — on pushes to `main`/`develop` and on every pull
  request.
- `.gitlab-ci.yml` — on **every** branch push and on every merge request, with a
  `workflow:rules` block that guarantees **one** pipeline per change: a branch
  with an open merge request gets the merge-request pipeline and its branch
  pipeline is suppressed.

## 7. Conventions you must follow

- **Time scale, frame, and units are explicit** in every public name:
  `reference_hour_td`, `longitude_deg_east`, `separation_in_moon_radii`.
- **East-positive longitude** everywhere in code; convert at the boundary.
- **ΔT is always caller-supplied.** Never default it to zero silently.
- **Provenance in comments.** Every constant cites the printed page it came
  from, e.g. `# Meeus, printed p. 224`.
- **No OCR text in source, fixtures, or docs.** Transcribe by hand from the
  scan, one value at a time, recording printed page *and* PDF page
  (`printed page = PDF page + 218` in the working copy's scan).
- **No runtime downloads.** Any external dataset gets a `data/manifest.json`
  entry with source, version, coverage, SHA-256, and retrieval date, fetched by
  a separate deliberate step.
- **`core/` stays small and cited.** Until the shared primitives exist
  (astronomical time, coordinate transforms, a general event solver), `core/`
  holds narrow, well-documented copies and must not grow into a second full
  implementation.
- **Keep the reference/custom boundary.** `core/` never imports
  `occultation.reference`; compare, then replace, never the other way round.

## 8. What is not implemented yet

- The reference engine's actual calculation (Skyfield + local JPL ephemeris) and
  therefore any real comparison difference. The package and the CLI seam exist;
  the engine raises.
- Generation of the Besselian elements — they are inputs today.
- Immersion and emersion (contact) times; the method starts from
  `t ∓ sqrt(1 - Δ²)/n` on printed p. 226.
- Lunar limb profile, grazing occultations, regional visibility.
- Everything else in the almanac: Sun/Moon positions and events, twilight,
  phases, the 24 solar terms, planets, the batch pipeline, storage, and an API.
- Packaging the `verify` fixture as package data, so an installed wheel can run
  `occultation verify meeus-example-5` without `--fixture`.

## 9. Where the project is going

The roadmap is milestones 0–15 in
[`AGENT_HANDOFF.md`](AGENT_HANDOFF.md) §9. Milestone 0 (repository and Python
foundation) is **closed**; the occultation work is milestone 14 pulled forward.
The next increments, in order:

1. Commit the CLI work on `feat/cli-local-circumstances` and open a pull request.
2. Select and verify a local JPL ephemeris (`de440s.bsp` is the documented
   candidate) with a manifest entry and a separate fetch command.
3. Milestone 1: one Hong Kong Sun position through a `SkyfieldEngine`.
4. Milestone 2: one month of Sun events compared against the Hong Kong
   Observatory, with an error report in seconds.

## 10. Reading order

1. [`explainer.html`](explainer.html) — the astronomy, in pictures.
2. This file — the code base.
3. [`tooling.html`](tooling.html) — the Python, uv, pytest, Git and CI
   machinery, for readers with no tooling background.
4. [`algorithms/meeus-star-local-circumstances.md`](algorithms/meeus-star-local-circumstances.md)
   — the formulas and their provenance.
5. [`FOR_REVIEW.md`](FOR_REVIEW.md) — what the CLI does, the proof it matches
   the book, and what is deliberately unfinished.
6. [`AGENT_HANDOFF.md`](AGENT_HANDOFF.md) — constraints, defect history,
   roadmap, and the rules for contributing.
