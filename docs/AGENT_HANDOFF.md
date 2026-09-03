# Occultation — Hong Kong astronomical almanac learning project

> **STATUS 2026-03-09 (milestone 0): CLOSED — the quality gate is green.** Sections 0, 7 and 15
> below describe the *pre-fix* red state and are kept as the record of what was wrong; read
> **Appendix B** first for what has since been repaired, and re-run the §9 milestone-0 proof
> commands before trusting any statement that something is still broken. This file is the tracked
> copy (`docs/AGENT_HANDOFF.md`); `local/README_AI_HANDOFF.md` is the same text in the git-ignored
> working directory — edit the tracked one and re-copy.
>
> Project handoff and execution guide for AI assistants and human contributors.
>
> Rewritten 2026-03-09 against the actual working tree. The previous version of this
> file described a `hk_almanac` package on GitLab and contained large amounts of
> OCR damage (garbled sentences, broken URLs, `ImpLement`-style word corruption).
> Appendix A lists what changed. Everything in sections 0, 5, 6, 7, 8, 9, 13 and 15 was re-checked
> by running commands and reading files, not from memory.


## 0. Verified repository facts (read before anything else)

Checked on 2026-03-09 in `/Users/workworkwork/Documents/repo/occultation`:

| Fact | Reality |
| --- | --- |
| Package name / import name | `occultation` (`src/occultation/`) |
| Console script | `occultation` → `occultation.cli:main` (D1 fixed; was `occultation:main`) |
| Build backend | `uv_build>=0.12.7,<0.13.0` |
| Python | `.python-version` = `3.12` (uv-managed CPython 3.12.14) |
| Runtime dependency | `skyfield>=1.55` only |
| Dev dependencies | `mypy`, `pytest-cov`, `ruff` (pytest arrives transitively via `pytest-cov`) |
| Git remote | `https://github.com/Remember-Urinating-before-bed/occultation.git` |
| Branches | `main` (initial commit) and `develop` (HEAD, "Init python 3.12 project & gitlab ci" + 2 CI fixes) |
| CI | GitHub Actions: `.github/workflows/ci.yml`. **There is no `gitlab-ci.yml` in this repository.** |
| Textbook PDF | `local/meeus_ocr/MeeusTables_Occultation.pdf` — git-ignored, image-only, 128 pages (see §8). Moved out of `src/occultation/` on 2026-03-09 (defect D8, fixed) |
| `docs/` | Exists; `docs/AGENT_HANDOFF.md` (this file) and `docs/algorithms/meeus-star-local-circumstances.md` were added while closing milestone 0. It was empty before that |
| Working tree | Milestone-0 work is present but **uncommitted**: repaired/re-typed files under `src/occultation/`, `tests/`, `docs/`, plus modified `AGENTS.md`, `pyproject.toml`, `config/locations/hong_kong.toml`, `src/occultation/__init__.py`, `tests/test_cli.py`. See Appendix B |
| `local/` (this file) | **Git-ignored** — `local/.gitignore` contains a single `*`, so nothing under `local/` is ever reported by `git status` or committed |

The rows about the textbook PDF, `docs/`, and the working tree matter most: the repository is *not*
in a green state, and the untracked Meeus files are machine-transcription artefacts, not finished
code. §7 lists exactly what is broken, §15 records the current status, and §16 lists the smallest
next increments.

> Because `local/` is ignored, this handoff exists only in this working copy. If it should travel
> with the repository, copy it to a tracked path (a reasonable target is `docs/AGENT_HANDOFF.md`)
> and ask the user first — do not silently `git add -f` it. See also `local/COPY_INTO_REPO.md`, the
> stale Day 2 copy-instructions note discussed in §10.1.

### Contents

```text
0. Verified repository facts (read before anything else)
1. Read this first
2. Project goal
3. Binding constraints and decisions
   3.1 Language and environment        3.4 Own calculation versus reference calculation
   3.2 Revised implementation strategy 3.5 Scope discipline
   3.3 Runtime network and external data
4. Authoritative learning and validation sources
5. Architecture
   5.1 Intended high-level flow  5.2 What actually exists right now  5.3 Target structure
6. Domain conventions
7. Current repository state and known defects   <-- start here
   7.1 Verified command results  7.2 Defect inventory  7.3 Intended design
8. The Meeus textbook PDF and the OCR pipeline
   8.1 What the file is          8.4 Curated transcription (worked example)
   8.2 Where the PDF must live   8.5 Repository hygiene
   8.3 How the OCR was produced
9. Milestone roadmap (milestones 0-15)
10. Day 1 setup — SUPERSEDED      10.1 COPY_INTO_REPO.md — SUPERSEDED
11. Testing and validation policy
12. Data-pipeline and operational policy
13. Git and work-management conventions
14. Instructions for future AI assistants
15. Current status handoff
16. Immediate execution order     16.1 How to continue (checklist)
Appendix A — Changes in this rewrite (A.1 second-pass corrections, A.2 third-pass repository changes)
```


## 1. Read this first
This repository is a learning project for building a Hong Kong astronomical almanac in Python while practising production-quality software engineering, data pipelines, and DevOps skills relevant to trading-firm infrastructure roles. The current active work-package inside that project is lunar occultation calculation from Jean Meeus's *Astronomical Tables*.

The user is a DevOps engineer but a beginner in astronomy, numerical astronomy, and Python application development. Explanations must therefore introduce the astronomical concept before presenting an implementation. Do not assume the user already understands coordinate frames, astronomical time scales, numerical root-finding, or ephemerides.

Before making changes, every AI assistant must:

1. Read this document completely.
2. Inspect the current repository, Git status, existing files, open issues, and latest pipeline result.
3. Identify the current milestone and continue from it; do not restart completed work.
4. Preserve unrelated user changes in a dirty worktree.
5. Propose only the smallest next increment that produces a testable result.
6. Explain what the user is learning, what will be implemented, and how completion will be verified.
7. Never silently change the project constraints or architecture described below.

## 2. Project goal

Build a reproducible Python application that generates astronomical almanac information for Hong Kong, including eventually:

- apparent celestial positions;
- Sun and Moon altitude/azimuth;
- sunrise, transit, sunset, and twilight;
- moonrise, transit, and moonset;
- lunar phases;
- the 24 solar terms;
- planet and selected-star visibility;
- conjunctions and related events;
- lunar occultation predictions;
- machine-readable annual almanac output;
- validation reports, operational metrics, and a repeatable data pipeline.

The Long-term result should be able to calculate from local code and versioned local data without calling third-party astronomy websites or APIs at runtime.

## 3. Binding constraints and decisions

### 3.1 Language and environment

- All astronomical application logic must be written in Python.
- Target Python is 3.12, pinned in `.python-version` and `requires-python = ">=3.12"`.
- The user's Mac previously had system Python 3.9. Do not replace or modify macOS/system
  Python; the project now uses a uv-managed CPython 3.12.14 in `.venv/`.
- Use `uv` to obtain/manage Python 3.12, create the virtual environment, resolve
  dependencies, and maintain `uv.lock`.
- Use `pyproject.toml` with the `uv_build` backend. Do not introduce Conda, Pixi, Poetry,
  Pipenv, or Nix as the primary Python dependency manager.
- Nix may be added much later as an optional development shell, while `uv` remains
  responsible for Python dependencies.
- The package is `occultation` under `src/occultation/`. **`hk_almanac` no longer exists
  as a package name.** Any file, import, command, or note that says `hk_almanac` or
  `hk-almanac` is stale and must be corrected rather than obeyed. See defect D2 in §7.2.

### 3.2 Revised implementation strategy

The final educational goal is to understand and implement the calculations, but the user must
**not** begin by recreating the whole astronomical stack from scratch.

The user's boss advised starting with textbook formulas and existing calculations. Therefore:

1. First produce a working result with Skyfield and a local JPL ephemeris.
2. Put Skyfield behind a clearly named reference-engine adapter.
3. Learn one astronomical concept at a time.
4. Implement the corresponding textbook calculation in the custom core.
5. Compare the custom result with Skyfield and published Hong Kong results.
6. Replace reference-engine responsibilities incrementally.
7. Keep Skyfield available as an independent regression oracle.

The initial prototype is allowed to use Skyfield as its active calculation engine. Earlier guidance that Skyfield must be validation-only from Day 1 is superseded.

### 3.3 Runtime network and external data

- Core almanac generation must not call a remote astronomy API or website at runtime.
- External scientific data is allowed when it is downloaded deliberately, stored locally,
  versioned or content-addressed, and documented.
- Never let application startup silently download an ephemeris.
- Data bootstrap/update is a separate command or pipeline stage from almanac calculation.
- Every external data file must have a manifest entry containing its source, version/name,
  date obtained, coverage, checksum, and licence/provenance notes.
- Runtime calculations must use an explicit local path, such as `data/external/de440s.bsp`.
- Large scientific files should not be committed directly to normal Git history. Use a documented
  artifact store, Git LFS, release asset, or reproducible fetch step with checksum verification.

For the modern prototype, prefer a short ephemeris that covers the required period, such as
JPL `de440s.bsp` (1849-2150, 32 MB), unless the project requirements later justify another
file. Skyfield's "Planets and their moons: JPL ephemeris files" page documents `de440s.bsp`
as a compact modern option (verified 2026-03-09: it lists `de440s.bsp` 1849-2150 32 MB,
`de440.bsp` 1550-2650 114 MB, `de441.bsp` -13200 to 17191 3.1 GB, and notes that the short
DE430/DE440 files are more accurate than the long-term ones because they include the Moon's
liquid core). Skyfield also notes ephemeris files never change once downloaded, so
`load('de440s.bsp')` will not re-download if the file is already on disk — but the download
directory must still be pinned explicitly and the fetch must be a separate, deliberate step.

**No ephemeris file has been chosen or downloaded yet.** `data/manifest.json` is still
`{"$schema_version": 1, "datasets": []}` and `data/external/` does not exist. Note also that
the current Meeus occultation work (§8.4) does **not** need an ephemeris at all: Besselian
elements are supplied as inputs from the printed tables.

### 3.4 Own calculation versus reference calculation

Keep this boundary visible in both code and documentation:

```text
reference engine
    Existing trusted calculation used to get a working result and expected values.
    Initially: Skyfield + local JPL ephemeris.

custom core
    The user's progressively implemented textbook/standards-based calculations.

comparison layer
    Runs both engines with identical inputs and reports numerical differences.
```

The custom core must never import from `occultation.reference`. (The earlier wording said
`hk_almanac.reference`; the package rename makes that import impossible anyway.)

Today the boundary is only partially realised: `src/occultation/core/` (custom Meeus maths)
and `src/occultation/domain/` exist, but there is **no `reference/` package yet** and nothing
imports Skyfield. That is fine for the current work-package because the Meeus star-occultation
method takes Besselian elements as *inputs* rather than computing them from an ephemeris.

### 3.5 Scope discipline

- Do not add Kafka merely because this is called a data pipeline.
- Do not add Kubernetes before a containerized application exists and has a real deployment need.
- Do not add PostgreSQL or ClickHouse before useful queryable almanac output exists.
- Do not add FastAPI before the CLI and domain interfaces are stable.
- Do not optimize before correctness and benchmark baselines exist.
- Tide prediction is a separate oceanographic domain and out of scope for the initial astronomy project.
- Traditional Chinese calendar rules, star maps, meteor showers, and eclipses are later milestones, not version 1.

**Superseded rule (2026-03-09):** this document previously said "Do not begin with
occultations; they are an advanced capstone." That is no longer true. The user deliberately
started with the Meeus occultation chapter as a *star-occultation local-circumstances* exercise
because it is self-contained: it needs no ephemeris, no event solver, and no Sun/Moon theory —
just the printed Besselian elements plus trigonometry. Occultation remains the capstone of the
almanac roadmap (§9, milestone 14), but the narrow "local circumstances from supplied elements"
calculation is now an accepted early milestone. Do not treat the earlier prohibition as a reason
to delete or defer the existing occultation code; do not let it expand into a full occultation
prediction engine before the fundamentals in milestones 3-5 exist.

## 4. Authoritative learning and validation sources

Use sources for different purposes; do not treat them as interchangeable.

| Source | Purpose | Status of the link |
| --- | --- | --- |
| `local/meeus_ocr/MeeusTables_Occultation.pdf` — Jean Meeus, *Astronomical Tables* (Occultations chapter, printed pp. 219-346) | Primary beginner learning source; source of textbook algorithms, examples, and Besselian element tables | Local file only, git-ignored, image-only. See §8 |
| Skyfield, "Planets and their moons: JPL ephemeris files" — https://rhodesmill.org/skyfield/planets.html | Reference-engine behaviour, ephemeris selection, local (non-downloading) `load()` handling | Verified reachable 2026-03-09 |
| Skyfield, "Positions" — https://rhodesmill.org/skyfield/positions.html | Barycentric, astrometric, apparent, and topocentric position stages | Not re-verified this session |
| JPL SSD, "Planetary and Lunar Ephemerides — Export Information" — https://ssd.jpl.nasa.gov/planets/eph_export.html | Scientific provenance and coverage of DE440/DE441 (and DE421, DE430/431) | Verified reachable 2026-03-09. The older `ssd.jpl.nasa.gov/doc/de440_de441.html` form now 404s |
| Hong Kong Observatory astronomy portal — https://www.hko.gov.hk/en/gts/astronomy/astro_portal.html | Product-level validation for Hong Kong rise/set times, twilight, moon phase | Verified reachable 2026-03-09. Year-specific `almanac2026_index.htm` URLs 404; navigate from the portal instead |
| Occult v4 by David Herald (IOTA) — https://www.occultations.org/sw/occult/occult4.htm | Later comparison target for occultation functionality and scope | Verified reachable 2026-03-09 |

Two useful validated facts from the HKO portal, for §6:

- HKO calculates its astronomical information for **mean sea level at latitude 22°18′07.3″,
  longitude 114°10′27.6″** (the Observatory's own site), based on data from HM Nautical
  Almanac Office and USNO. That is 22.30203°N, 114.17433°E — which matches
  `config/locations/hong_kong.toml` to the printed precision, so the config file is
  consistent with the validation source.
- The portal publishes rise/set and astronomical-twilight times in **Hong Kong Time (UTC+8)**,
  so any comparison must convert TT/UT results to `Asia/Hong_Kong` explicitly.

If a formula is implemented from the textbook or a standard, record the exact
chapter/table/equation and the assumed validity/precision in `docs/algorithms/`.
**`docs/` is currently empty**, so this documentation obligation is outstanding — see
§8.5 for the transcription that already exists and where it must land.


## 5. Architecture

### 5.1 Intended high-level flow

```text
CLI / batch pipeline
        |
        v
application service
        |
        +---> reference engine (Skyfield + local JPL ephemeris; not yet implemented)
        |
        +---> custom core (occultation.core.* — Meeus maths, implemented progressively)
        |
        v
normalized domain result (occultation.domain.*)
        |
        +---> JSON / CSV / Parquet
        +---> comparison report
        +---> metrics and logs
```

### 5.2 What actually exists right now

Verified file map (excluding caches, `.venv`, and the PDF):

```text
.gitignore
.python-version                      # "3.12"
AGENTS.md                            # read this file first; edited 2026-03-09 to point at
                                     # local/README_AI_HANDOFF.md (edit is uncommitted — see D12)
README.md                            # 10-line stack note
dataflow.mmd                         # aspirational Mermaid pipeline sketch
pyproject.toml                       # name = "occultation", uv_build backend
uv.lock
.github/workflows/ci.yml             # GitHub Actions "quality" job
config/locations/hong_kong.toml
data/README.md
data/manifest.json                   # {"$schema_version": 1, "datasets": []}
docs/                                # EMPTY directory
local/                               # git-ignored scratch area (this file lives here)
local/meeus_ocr/                     # git-ignored: the scan, the OCR script and its output (§8.3)
src/occultation/__init__.py          # def main(): print("Hello from occultation!")
src/occultation/cli.py               # argparse parser: prog="occultation", --version
src/occultation/core/local_circumstances.py   # BROKEN — see §7
src/occultation/core/observer_coordinates.py  # BROKEN — see §7
src/occultation/domain/observer.py            # BROKEN — see §7
src/occultation/domain/occulation.py          # BROKEN + misspelled filename
tests/test_cli.py                    # PASSING (asserts parser.prog == "occultation")
tests/fixtures/meeus_regulus_1999.toml        # BROKEN — invalid TOML, see §7
tests/reference_cases/test_meeus_regulus.py   # BROKEN — SyntaxError
tests/unit/test_observer_coordinates.py       # BROKEN — SyntaxError
```

Conventions already established by the working code that new code must follow:

- `src/` layout, import package `occultation`.
- Frozen dataclasses with `slots=True` and a `__post_init__` that validates finiteness and
  ranges, raising `ValueError` messages that name the offending field.
- Explicit unit-bearing field names: `longitude_deg_east`, `latitude_deg`, `elevation_m`,
  `star_declination_deg`, `moon_shadow_radius_earth_radii`, `hours_after_reference`,
  `separation_in_moon_radii`, `position_angle_deg`, `altitude_deg`, `iteration_count`.
- East-positive longitude is the project convention; Meeus prints west-positive, and the
  fixture documents that conversion in a comment.
- Tests compare against published values with `pytest.approx(..., abs=...)` tolerances that
  match the number of digits the book actually prints — never exact equality.

### 5.3 Target structure (do not pre-create)

```text
.github/workflows/ci.yml             # current CI (GitLab was never wired up)
.python-version
README.md
pyproject.toml
uv.lock
config/locations/hong_kong.toml
data/README.md
data/manifest.json
data/external/                       # local ephemerides, checksummed, git-ignored
data/coefficients/                   # versioned textbook coefficient tables as data
data/validation/                     # HKO / Occult reference extracts for comparisons
docs/architecture.md
docs/roadmap.md
docs/sources.md
docs/decisions/                      # one file per ADR-style decision
docs/algorithms/                     # one file per formula, with page/table provenance
scripts/fetch_reference_data.py      # deliberate, offline-capable data bootstrap
scripts/verify_reference_data.py     # checksum verification against data/manifest.json
src/occultation/
    __init__.py
    cli.py
    domain/
        observer.py                  # exists
        occultation.py               # exists but is currently misnamed occulation.py
        events.py                    # add when the first AlmanacEvent exists
        positions.py
    application/
        almanac_service.py
    reference/
        skyfield_engine.py           # add at milestone 1
    core/                            # custom maths; may never import occultation.reference
        observer_coordinates.py      # exists
        local_circumstances.py       # exists
        angles.py
        time_scales.py
        vectors.py
        coordinates.py
        earth_rotation.py
        sun.py
        moon.py
        event_search.py
    comparison/
        compare_engines.py
    pipeline/
        generate_almanac.py
tests/
    unit/
    integration/
    comparison/
    reference_cases/
    fixtures/
```

This is a target structure. Do not create empty modules months before they are needed. Add each
directory/file when its first real responsibility is implemented. Note that `core/` and
`domain/` currently have no `__init__.py` (defect D7 in §7.2).

## 6. Domain conventions

Every public calculation must make the following explicit:

- time scale: UTC, TAI, TT, UT1, or TDB;
- coordinate origin: barycentric, heliocentric, geocentric, or topocentric;
- coordinate frame/equinox: for example ICRS/J2000 or equator/equinox of date;
- units: degrees, radians, hours, kilometres, Earth radii, astronomical units, or seconds;
- observer location and datum;
- atmospheric/refraction assumptions;
- model/algorithm name and version;
- expected precision or validation tolerance.

Avoid ambiguous names such as `time`, `angle`, or `position` when a more precise name is
possible. Prefer `jd_tt`, `longitude_rad`, `apparent_ra_hours`, `topocentric_altitude_deg`.

Hong Kong configuration must use an explicit documented WGS84 coordinate, an elevation
convention, and the IANA timezone `Asia/Hong_Kong`. Do not implement Hong Kong time by manually
adding eight hours.

`config/locations/hong_kong.toml` has three latent problems that must be fixed the first time
the file is touched (no code reads it yet, so nothing fails today):

```text
logitude_deg  -> longitude_deg        (typo; and inconsistent with longitude_deg_east in the domain model)
dataum        -> datum                (typo)
Data of retrival = "30 Aug"           -> record a full ISO date, e.g. 2025-08-30
```

Decide once and document whether the config key is `longitude_deg` (east-positive assumed) or
`longitude_deg_east` (explicit). The domain model in `occultation.domain.observer` already uses
`longitude_deg_east`; matching it removes a whole class of sign bugs.

## 7. Current repository state and known defects

> **Historical — this section records the red baseline that milestone 0 was opened against. It is
> now CLOSED; see Appendix B for the fix-by-fix status and the verified green gate.** Read §7.2 for
> *what was wrong* and §7.3 for the design that was kept; do not treat the command output in §7.1 or
> the "the repository is not green" framing below as current.

**At the time of writing, the repository was not green.**

The four `occultation` source files, the TOML fixture, and the two new test files were produced
by a machine transcription of a scanned book chapter (§8). That transcription never parsed: it
is full of OCR damage. `uv run pytest` fails during *collection*, `uv run mypy src` fails on a
syntax error, and `uv run ruff check .` reports **380 errors**. Only `tests/test_cli.py` passes.

### 7.1 Verified command results (2026-03-09)

```text
uv run python --version                       -> Python 3.12.14
uv run pytest                                 -> 2 collection errors, Interrupted
uv run ruff check .                           -> Found 380 errors (all invalid-syntax)
uv run ruff format --check .                  -> 6 files already formatted (rest unformattable)
uv run mypy src                               -> 1 error: Unterminated string literal
                                                (core/local_circumstances.py:1)
uv run occultation --help                     -> prints "Hello from occultation!", exit 0
uv run python -m occultation.cli --help       -> correct argparse usage text
uv run pytest tests/test_cli.py -q            -> 1 passed
```

The last two lines are defect D1: the installed console script and the module entry point behave
differently, and only the module one is the real CLI. A third check,
`uv run python -c "import tomllib; tomllib.load(open('tests/fixtures/meeus_regulus_1999.toml','rb'))"`,
raises `TOMLDecodeError: Expected '=' after a key in a key/value pair (at line 16, column 11)` —
defect D4.

All 380 Ruff errors are reported as `invalid-syntax`, concentrated in the OCR-derived files:

```text
230  src/occultation/core/local_circumstances.py
 80  tests/reference_cases/test_meeus_regulus.py
 35  src/occultation/domain/occulation.py
 26  src/occultation/core/observer_coordinates.py
  7  tests/unit/test_observer_coordinates.py
  2  src/occultation/domain/observer.py
```

Ruff cannot classify anything else until a file parses, so expect a *second* wave of findings
(`F821` undefined `hk_almanac`, `I001` unsorted imports, `E501`, `SIM*`) as each file is repaired.
Do not try to silence anything with `# noqa` or by loosening `pyproject.toml` — re-type the files.

### 7.2 Defect inventory

| ID | Defect | Evidence | Fix |
| --- | --- | --- | --- |
| D1 | `[project.scripts] occultation = "occultation:main"` resolves to `__init__.main`, which prints "Hello from occultation!" and ignores argv, so `--help`/`--version` never work | `uv run occultation --help` prints the hello text | Point it at `"occultation.cli:main"`; delete or repurpose `__init__.main`; add a test that runs the entry point |
| D2 | Every new source/test file imports the non-existent `hk_almanac` package — and the import lines themselves are OCR-mangled, in seven distinct ways: `from hk_almanac.core.observer_coordinates import` (`core/local_circumstances.py:5`), `from hk_almanac:domain:observer import ObserverLocation` (`core/local_circumstances.py:9`), `from dataclasses import dataclass from hk almanac:domain.observer import ...` (`core/observer_coordinates.py:3`), `from hk_almanac. core. observer_coordinates import ...` (`tests/unit/test_observer_coordinates.py:5`), `from hk_almanac.domain.observer import ObserverLocation` (`tests/unit/test_observer_coordinates.py:6`), `from hk almanac: coreolocal carcunstences import ...` (`tests/reference_cases/test_meeus_regulus.py:7`), `from hk almanas. domainecsultation import` (`tests/reference_cases/test_meeus_regulus.py:9`) | `grep -rniE 'hk.?almanac\|hk almanas' src tests` → 7 hits across 4 files (`core/local_circumstances.py`, `core/observer_coordinates.py`, `tests/unit/test_observer_coordinates.py`, `tests/reference_cases/test_meeus_regulus.py`) | Re-type each import as a plain `occultation...` import — only two of the seven are clean enough to fix with a search-and-replace |
| D3 | `src/occultation/core/local_circumstances.py` line 1 starts `p="Calculate ...` (mangled docstring) → file does not parse | mypy output above | Re-type the module from §8.4 |
| D4 | `tests/fixtures/meeus_regulus_1999.toml` is invalid TOML. Specifics: `printed_.pages` (line 4), keys containing spaces (`greenwich hour-angle at reference deg`, line 16; `greenwich hour angle rate deg perhour`, line 17), two mangled table headers `[elements. moon_shadow xl` (line 19 — stray space plus a stray `l`, should be `[elements.moon_shadow_x]`) and `[elements. moon_shadow_y]` (line 23), a case-mangled key `Linear_rate_per_hour` (line 25), a mangled `[expected]` header that swallowed its first key (`lexpected] rho_sin_geocentric_latitude`, line 27), and keys whose `=` or value sits on the following line (lines 28-41; lines 29-30, `rho_cos_geocentric_latitude` / `0.836338`, have no `=` at all) | `tomllib.load` raises `TOMLDecodeError: Expected '=' after a key in a key/value pair (at line 16, column 11)` | Rewrite as valid TOML with snake_case keys; the numeric values themselves are correct (§8.4) |
| D5 | Both new test files fail to parse, for two different reasons: `tests/reference_cases/test_meeus_regulus.py` line 8 raises `SyntaxError: unmatched ')'` (the OCR dropped the `def test_...(` opener), and `tests/unit/test_observer_coordinates.py` line 8 raises `SyntaxError: invalid character '→' (U+2192)` on `def test_palomar_observer_coordinates_natch_neeus()→ None:` — note the identifier is also mangled (`natch_neeus` for `match_meeus`). Beyond the two fatal lines, `test_observer_coordinates.py` also carries `Longitude_deg_east=-116,8640` (capital `L`, comma for decimal point), `assert coordinates, rho_sin_geocentric_latitude ==` (comma for a dot), `abs=Se-7` (`S` for `5`), `pytest, raises (ValueError, …)`, and `Latitude_deg=91.0` — so even after the syntax errors are removed it would still fail. Treat every line as untrusted | `uv run pytest` collection errors (see §7.1) | Re-type both tests from scratch; do not patch the glyphs in place |
| D6 | `src/occultation/domain/occulation.py` is misspelled | filename | Rename to `occultation.py` while doing D2/D3, before anything imports it widely. Note the file is **untracked**, so use plain `mv`, not `git mv` |
| D7 | `src/occultation/core/` and `src/occultation/domain/` have no `__init__.py` | `find src -name '__init__.py'` returns only the package root | Add them — `uv_build` may not ship the subpackages otherwise |
| D8 | ~~The 128-page scanned PDF sits inside `src/occultation/`, i.e. inside the package `uv_build` packages~~ **FIXED 2026-03-09** | `uv build && unzip -l dist/*.whl` now lists 14 entries and **no PDF**; the file is at `local/meeus_ocr/MeeusTables_Occultation.pdf`, confirmed ignored by `git check-ignore -v` | Done — plain `mv` (the file was untracked). SHA-256 `c5d58affe71aabcf384b3ccf12d2c0e04297cab481742e7809e681fcba886d3c` if a copy must be identified |
| D9 | `.coverage` (binary) is present in the worktree root although `.gitignore` lists it; all the Meeus files are untracked | `ls -la`, `git status --porcelain` | Decide what to commit (§15) |
| D10 | `data/manifest.json` declares zero datasets, and neither `scripts/fetch_reference_data.py` nor `scripts/verify_reference_data.py` exists | `cat data/manifest.json` | Expected for this milestone; required before milestone 1 |
| D11 | Cosmetic but user-visible typos in tracked files: `pyproject.toml` says `description = "A playground astronomical occulation program for HK"` ("occulation"), and `config/locations/hong_kong.toml` has the three problems listed in §6 | `cat pyproject.toml`, `cat config/locations/hong_kong.toml` | Fix in the same small PR as D1, since both touch tracked scaffold files |
| D12 | ~~`AGENTS.md` (tracked) instructs every agent to "Read handoff.md file completely before modifying this repository", but **no `handoff.md` exists at the repository root**~~ **PART-FIXED 2026-03-09**: `AGENTS.md` now names `local/README_AI_HANDOFF.md` and warns that `local/` is git-ignored. The remaining half of the defect is that the target is still ignored, so a fresh clone or CI-run agent following `AGENTS.md` finds nothing | `git diff AGENTS.md`; `git check-ignore -v local/README_AI_HANDOFF.md` | Finish by open decision 5 in §15: copy this handoff to a tracked path (e.g. `docs/AGENT_HANDOFF.md`) and repoint `AGENTS.md` at it. The `AGENTS.md` edit is uncommitted — commit it with the milestone 0 PR |


### 7.3 What the broken code was *trying* to do (keep the design)

The intended design is sound and should be preserved rather than reinvented:

- `domain/observer.py` → `ObserverLocation(longitude_deg_east, latitude_deg, elevation_m)`,
  frozen, validated.
- `domain/occultation.py` → `FundamentalPlanePolynomial(at_reference, linear_rate_per_hour,
  quadratic_term_per_hour_squared)` with `value_at(hours)` and `rate_at(hours)`;
  `StarOccultationElements(reference_hour_td, star_declination_deg,
  greenwich_hour_angle_at_reference_deg, greenwich_hour_angle_rate_deg_per_hour,
  moon_shadow_x, moon_shadow_y, moon_shadow_radius_earth_radii=0.272495)`;
  `StarOccultationResult(...)` with a `limb_clearance_in_moon_radii` property returning
  `abs(separation) - 1`.
- `core/observer_coordinates.py` → `calculate_geocentric_observer(observer)` returning
  `GeocentricObserverCoordinates(rho_sin_geocentric_latitude, rho_cos_geocentric_latitude)`
  using Meeus's constants `k = 0.99664719` and `a = 6378140 m`. The unit test file holds three
  tests, not one: the Palomar values, `test_southern_latitude_has_negative_geocentric_sine`
  (`rho_sin < 0`, `rho_cos > 0` for latitude −33.3562 at longitude 0, elevation 0), and
  `test_observer_rejects_invalid_latitude` (`ValueError` naming `latitude_deg` for latitude 91.0).
  Preserve all three when re-typing — the latter two are the only coverage of the validation and
  the sign behaviour.
- `core/local_circumstances.py` → iterative closest-approach solver for a **star** occultation
  (so `D1 = 0`, `H1 = 15.04107`, `L = k = 0.272495`, and the aberration term `F` is unused),
  returning time of least distance, separation in lunar radii, position angle, altitude, and
  the iteration count.

The solver's starting guess and iteration count are the one genuinely inconsistent part of the
draft, and the numbers below are what you will find in the mangled text today:

```text
core/local_circumstances.py  hours_after_reference = 6.0     (first guess — not Meeus's advice)
core/local_circumstances.py  iteration_count = 8             (dead initialisation before the loop)
core/local_circumstances.py  convergence_tolerance_hours = 1e-6, max_iterations = 20  (keyword defaults)
reference test line 67       result.iteration_count == 5     (asserts a third value)
fixtures/meeus_regulus_1999.toml   (no iteration_count key at all)
```

Meeus says to start from `t = 0` (printed p. 224), so the fix is: begin at `t = 0`, count the
iterations the loop actually performs, and either assert that derived count in the test or drop the
assertion and record the count as diagnostic output. Do **not** "fix" the test by tuning the guess
to match a magic number, and do not add an `iteration_count` to the fixture until you have run the
re-typed solver and seen what it returns.

## 8. The Meeus textbook PDF and the OCR pipeline

### 8.1 What the file is

`local/meeus_ocr/MeeusTables_Occultation.pdf` is Jean Meeus, *Astronomical Tables* — the
Occultations chapter: 128 PDF pages, printed pages **219-346**. The page offset is exact and was
verified from the running headers and the printed page numbers recovered by OCR:

```text
printed page = PDF page + 218
```

It is a **scanned, image-only PDF with no usable text layer** — `pdftotext`/`pypdf` extraction
returns nothing meaningful, which is why an OCR step was needed at all.

Page map (all confirmed from the OCR output):

| PDF page | Printed | Content |
| --- | --- | --- |
| 1-5 | 219-223 | Chapter intro, general theory, planets vs. stars, immersion/emersion equations |
| 6-8 | 224-226 | **Local circumstances** — the algorithm transcribed in §8.4 |
| 8-11 | 226-229 | Example 3 (Saturn 1987, Uccle), Example 4 (Sofia), **Example 5: Regulus, 1999 Mar 1, Palomar** |
| 11-13 | 229-231 | Grazing occultations, northern/southern limits, visibility maps |
| 14-17 | 232-235 | Planetary-occultation refinements; tables of `k` and `F` |
| 18-19 | 236-237 | **BASIC program listing** — a compact machine-readable statement of the same algorithm |
| 19-65 | 237-283 | **Table I**: occultation list by year, star, magnitude, zone of visibility |
| 66-91 | 284-309 | **Table II**: Besselian elements for **star** occultations (columns `d`, `HO`, `HI`, `X0 X1 X2`, `Y0 Y1 Y2`, …) |
| 92-128 | 310-346 | **Table III**: Besselian elements for **planet** occultations (adds `DO DI`, `k`, `F`) |

The Regulus elements used by the fixture come from Table II, and Meeus's own worked example
(printed pp. 228-229) restates them — so those particular numbers appear twice in the book, which is
a useful cross-check even though the OCR of the tables in general is not. It is still not a licence
to trust the transcription: each value must be read off the scan by eye (§8.3, §11).

### 8.2 Where the PDF must live

It must **not** live inside `src/occultation/`: `uv_build` packages everything under the package
directory, and a scanned book is not importable data. As of 2026-03-09 it lives at
`local/meeus_ocr/MeeusTables_Occultation.pdf`, which is git-ignored (verified with
`git check-ignore -v`), so defect D8 is closed. The fix was confirmed the direct way — `uv build`
followed by `unzip -l dist/occultation-0.1.0-py3-none-any.whl` now lists 14 entries, none of them the
PDF, where before the move a 4.5 MB scan would have shipped inside the wheel. The book is copyrighted
— do not commit the scan to a public repository, and keep quoted extracts to the short validation
values already recorded in §8.4.

### 8.3 How the OCR was produced, and where the artefacts live

The tooling was built in the system temp directory and **copied into `local/meeus_ocr/` on
2026-03-09** so that it survives temp cleanup. Contents (all git-ignored):

```text
local/meeus_ocr/MeeusTables_Occultation.pdf   4,476,409 bytes  the 128-page scan (§8.1)
local/meeus_ocr/ocr.swift                         2,071 bytes  the Vision OCR script
local/meeus_ocr/all_pages.txt                   207,262 bytes  OCR of all 128 pages
local/meeus_ocr/p1.txt                              2,355 bytes  OCR of PDF page 1 only
local/meeus_ocr/build.log                             536 bytes  swiftc output (one warning, build_exit=0)
local/meeus_ocr/all_pages.err                            33 bytes  "# pdf pages: 128 ocr range 1-128"
local/meeus_ocr/p1.err                                     31 bytes  same header for the single-page run
local/meeus_ocr/README.md                                         new 2026-03-09: what each file is, the SHA-256, the re-run command, and the "never a source of truth" rule
```

`all_pages.err` is the confirmation that the dump covers the whole document: the PDF really has 128
pages and the run requested 1-128. The compiled `ocr` binary was deliberately **not** copied — the
one in the temp directory was 70,080 bytes and a fresh build is ~90 KB, so it is pure bulk; rebuild it
with `swiftc ocr.swift -o ocr`.

The pipeline itself:

1. Render each PDF page to a bitmap at ~220 dpi (`ocr.swift` uses `scale = 220.0 / 72.0` against the
   page's media box, drawn onto a white RGB `CGContext`).
2. Run Apple's Vision framework (`VNRecognizeTextRequest`, `.accurate`, `en-US`,
   `usesLanguageCorrection = true`) over each bitmap.
3. Emit per-page results to stdout with `===== PDF_PAGE <n> =====` markers, which is what
   `all_pages.txt` is.

Re-run it with:

```bash
cd local/meeus_ocr
swiftc ocr.swift -o ocr
./ocr MeeusTables_Occultation.pdf 1 128 accurate > all_pages.txt
```

This command pair was verified on 2026-03-09 against the copied files: `swiftc` succeeds (with the
one pre-existing conditional-downcast warning recorded in `build.log`), and a single-page run
reproduces the original output — `# pdf pages: 128 ocr range 1-1` on stderr, then
`===== PDF_PAGE 1 =====` followed by `Occultations 1990- 2020 / General Data`. Delete the `ocr`
binary afterwards; it is ~90 KB and rebuildable.

Known loss modes:

- prose is roughly 95% readable but has word-joining and `I`/`l`/`1` confusions;
- **multi-column numeric tables are scrambled** — Vision emits headers and digits in reading
  order, so `X0 X1 X2` values cannot be trusted positionally;
- superscripts, prime marks (`φ'`), Greek letters and the degree symbol frequently decode to `«`,
  `§`, `¿`, `°`, `&`, or disappear;
- printed page numbers survive as bare 3-digit lines, which is how the page map was built.

**Rule: OCR text is a search index into the scan, never a source of truth.** Any number that
enters code, a fixture, or a document must be read off the PDF page by eye and recorded with both
its printed page and its PDF page.

### 8.4 Curated transcription: local circumstances for a **star** occultation

This is the transcription that must land in
`docs/algorithms/meeus-star-local-circumstances.md` (the §4 documentation obligation). Sources:
printed pp. 224-226 (PDF 6-8), cross-checked against the BASIC listing on printed p. 236
(PDF 18) and against Example 5 on printed pp. 228-229.

Inputs (Table II for the star, plus the observer's site):

```text
To   reference instant, Dynamical Time (hours)
d0   star declination, degrees             (Table II column "d")
H0   Greenwich hour angle at To, degrees   (Table II column "HO")
H1   hourly rate of H, deg/hour            (Table II column "HI"; for a star H1 = 15.04107)
X0 X1 X2   Besselian x coefficients, Earth equatorial radii   x = X0 + X1 t + X2 t^2
Y0 Y1 Y2   Besselian y coefficients, Earth equatorial radii   y = Y0 + Y1 t + Y2 t^2
k    = 0.272495   Moon's relative radius / shadow radius, for a star
ΔT   = TT - UT, seconds
λ    observer longitude — west-positive in the book; the project stores east-positive
φ    observer latitude, north-positive
h    observer height, metres
```

Step 1 — geocentric observer coordinates (printed p. 224). With `k' = 0.99664719`
(= 1 − flattening) and `a = 6378140 m`:

```text
tan ω' = k' tan φ
ρ sin φ' = k' sin ω' + (h / 6378140) sin φ
ρ cos φ' =       cos ω' + (h / 6378140) cos φ
```

Step 2 — for a trial `t` (start with `t = 0`), at the instant `To + t` (printed pp. 224-225):

```text
d  = d0 + D1 t                       (D1 = 0 for a star)
H  = H0 + H1 t − λ_west − ΔT/239.345     # east-positive λ:  H = H0 + H1 t + λ_east − ΔT/239.345
x  = X0 + X1 t + X2 t²               x' = X1 + 2 X2 t
y  = Y0 + Y1 t + Y2 t²               y' = Y1 + 2 Y2 t
ξ  = ρ cos φ' sin H
η  = ρ sin φ' cos d − ρ cos φ' cos H sin d
ζ  = ρ sin φ' sin d + ρ cos φ' cos H cos d
ξ' = 0.01745329 H1 ρ cos φ' cos H
η' = 0.01745329 (H1 ξ sin d − ζ D1)     # D1 = 0 for a star  (see Appendix B correction 1)
u  = x − ξ            v = y − η
u' = x' − ξ'          v' = y' − η'
n² = u'² + v'²
τ  = −(u u' + v v') / n²             # correction to t, in hours
```

Iterate `t ← t + τ` until `|τ|` is below tolerance (the draft uses `1e-6` h ≈ 3.6 ms). The time of
least topocentric distance is `To + t` in Dynamical Time; subtract `ΔT` to express it in UT.

Step 3 — derived quantities (printed p. 225):

```text
tan P = u / v                                    (4)  position angle of the star on the lunar disk
L = k − ζ F / 1000000                            F is the planetary aberration/parallax term;
                                                     for a star L = k = 0.272495
Δ = (u v' − v u') / (n L)                        (6)  least separation, in lunar radii;
                                                     sign is north-positive, |Δ| < 1 ⇒ occulted
limb clearance = |Δ| − 1
sin h = sin d sin φ + cos d cos φ cos H          (8)  altitude of the star at that instant
```

Sign conventions that are easy to get wrong — re-check each one in the rewrite:

- `P` from `tan P = u/v` needs a quadrant test; Meeus's rule is that `cos P` carries the sign
  opposite to `v`. The draft's `atan2(−u, −v) % 360` encodes that and reproduces Example 5's
  `P = 24°.67` from `u = −0.13107`, `v = −0.28541`.
- `Δ`'s sign comes from the cross product `u v' − v u'`, **not** from `v`.
- `H` uses `ΔT/239.345` (hours of arc per second of ΔT), not `ΔT/3600`.
- Meeus's `λ` is west-positive; the project stores `longitude_deg_east`.

Step 4 — Example 5 worked values (printed pp. 228-229). This is the regression target and is what
`tests/fixtures/meeus_regulus_1999.toml` encodes:

```text
Occultation of Regulus, 1999 March 1 — Palomar Mountain Observatory
  λ = +116°.8640 (west)  ->  longitude_deg_east = -116.8640
  φ = +33°.3562          ->  latitude_deg       = 33.3562
  h = 1706 m             ->  elevation_m        = 1706.0
  ρ sin φ' = +0.546862      ρ cos φ' = +0.836338
  To = 10h TD
  d  = +11°.9694    H0 = 156°.6836    H1 = 15°.04107
  X0 = +0.22151     X1 = +0.55549     X2 = -0.00000
  Y0 = +0.19947     Y1 = -0.15258     Y2 = -0.00001
  k  = 0.272495     ΔT = +65 s
Results:
  t = +0.455608 h   ->  To + t = 10h.455608 TD = 10h 27m 20s TD = 10h 26m 15s UT
  Δ = +1.1526       ->  |Δ| > 1 ⇒ NOT occulted; Regulus passes north of the disk centre
  |Δ| − 1 = 0.1526 lunar radii ≈ 2 arcminutes of limb clearance
  final iteration:  u = -0.13107   v = -0.28541   u' = +0.40408   v' = -0.18556
                    H = +46°.4009  n = 0.444655
  P = 24°.67  (formula 4)
  h = +43°    (formula 8; the conjunction is visible from Palomar)
```

The draft regression test's tolerances — which the rewrite should keep, because they match the
number of digits the book prints — are `abs=5e-6` on `hours_after_reference` and
`dynamical_time_hour`, `abs=2e-4` on `universal_time_hour`, `abs=5e-4` on
`separation_in_moon_radii` and `limb_clearance_in_moon_radii`, `abs=0.02` on `position_angle_deg`,
and `abs=0.5` on `altitude_deg` (with a comment noting that Meeus prints the Regulus altitude only to
the nearest whole degree). The observer-coordinates unit test uses `abs=5e-7` on both
`rho_sin_geocentric_latitude` and `rho_cos_geocentric_latitude`. Never tighten a tolerance below
the precision the source actually supports, and never loosen one to make a failure go away.

### 8.5 Repository hygiene for the transcription

- Commit **curated** material only: `docs/algorithms/*.md` with printed-page provenance, plus
  machine-readable fixtures under `tests/fixtures/` carrying a provenance header comment.
- Do **not** commit raw OCR dumps (`all_pages.txt`) or the scan itself.
- The OCR script and its output now live in `local/meeus_ocr/` (§8.3), which is git-ignored by
  `local/.gitignore`, so they can never be committed by accident and no longer depend on the system
  temp directory. Nothing else in the repository may reference that path as a build or test input.

## 9. Milestone roadmap

Each milestone has three parts: learn, implement, and prove. Do not call a milestone complete
without its proof. **Milestones 0 and 14 are the ones currently in flight; everything else is the
longer-term almanac plan and is listed for continuity.**

### Milestone 0 — Repository and Python foundation

Status: **CLOSED 2026-03-09** — see Appendix B for what was repaired and the verified green output
of every command below. The text that follows is kept as the definition of done; the "today they do
not" line at the end of this subsection is now historical.

Learn:

- `pyproject.toml`, packages, virtual environments, dependency locking;
- Git branches and pull requests (the earlier draft said "merge requests" — that is GitLab
  vocabulary, and this repository is on GitHub with GitHub Actions);
- unit tests, linting, type checking, and CI.

Implement:

- Python 3.12 through `uv`;
- package under `src/occultation`;
- CLI entry point wired to the real parser (defect D1);
- pytest, Ruff, and mypy;
- the minimal CI pipeline that already exists in `.github/workflows/ci.yml`.

Prove (run these exactly; `uv run python version` in the earlier draft was a typo):

```bash
uv run python --version
uv run occultation --help
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

All commands and the CI pipeline must pass. Today they do not; closing §7.2 is the definition of
done for milestone 0.


### Milestone 1 — Working Skyfield reference result

Status: **not started.** Requires an ephemeris (`data/manifest.json` is still empty) and the
`reference/` package, neither of which exists.

Learn:

- what an ephemeris is;
- what an observer and apparent position are;
- the difference between UTC input and local display time;
- why runtime data downloads harm reproducibility.

Implement:

- explicit Hong Kong observer configuration (fix the typos in §6 first);
- ephemeris data manifest and verification;
- separate data-fetch/bootstrap command;
- `SkyfieldEngine` loading a local BSP file without downloading;
- Sun altitude/azimuth for a supplied UTC timestamp;
- JSON CLI output with algorithm and data metadata.

Prove (the console script is `occultation`, not `hk-almanac`; see defect D1):

```bash
uv run occultation sun-position \
  --location hong-kong \
  --time 2026-09-01T04:00:00Z \
  --engine skyfield \
  --format json
```

The command must succeed with networking disabled when the local data file is present.

### Milestone 2 — Skyfield daily Sun events

Status: **not started.** Note for the HKO comparison: HKO publishes its rise/set times for mean
sea level at 22°18′07.3″N, 114°10′27.6″E in Hong Kong Time (§4), so compare against that site, not
against the Observatory's 49 m elevation, and convert to `Asia/Hong_Kong` explicitly.

Learn:

- altitude, azimuth, horizon, transit, and twilight;
- the event thresholds used for sunrise and twilight;
- why refraction and solar semidiameter affect event time.

Implement:

- sunrise, transit, and sunset;
- civil, nautical, and astronomical twilight;
- one-day and date-range CLI output;
- normalized `AlmanacEvent` domain model.

Prove:

- generate one month for Hong Kong;
- compare with HKO;
- save a report of errors in seconds;
- document threshold/rounding differences.

This produces the first useful almanac before custom celestial mechanics begins.

### Milestone 3 — Mathematical primitives

Learn:

- degrees, radians, and hours;
- angle normalization;
- spherical and Cartesian coordinates;
- vectors and rotation matrices;
- floating-point error and tolerances.

Implement in the custom core:

- angle/unit conversions;
- angular separation;
- spherical/Cartesian conversion;
- X/Y/Z rotation matrices.

Prove:

- textbook example tests;
- round-trip/property tests;
- no dependency on Skyfield inside these custom modules.

### Milestone 4 — Astronomical time

Learn:

- Gregorian/Julian calendars;
- Julian Date and Modified Julian Date;
- UTC, TAI, TT, UT1, and TDB;
- leap seconds, DUT1, and Delta T;
- Julian centuries.

Implement:

- calendar-to-JD and JD-to-calendar conversion;
- explicit astronomical time model;
- versioned leap-second/Delta-T input data where required.

Prove:

- reproduce textbook examples;
- test leap-second boundaries and round trips;
- compare relevant values with Skyfield.

Note: the occultation code already leans on this — Meeus's tables give `To` in Dynamical Time and
require `ΔT` as an input (`ΔT/239.345` in the hour-angle formula). Until milestone 4 exists, `ΔT`
must stay an explicit caller-supplied value on the elements object, exactly as the draft fixture
does. Never default it to zero silently.

### Milestone 5 — Coordinate transformations and Earth rotation

Learn:

- ecliptic, equatorial, and horizontal coordinates;
- right ascension and declination;
- hour angle and local sidereal time;
- precession, nutation, and obliquity;
- geocentric versus topocentric coordinates.

Implement incrementally:

- ecliptic/equatorial transforms;
- equatorial/horizontal transforms;
- mean obliquity;
- Earth rotation/sidereal time;
- precession and nutation models selected from the textbook/standards.

Prove:

- inverse/round-trip tests;
- textbook examples;
- comparison against Skyfield with a documented tolerance.

The Meeus local-circumstances code is an early consumer of two of these: the `ρ sin φ'` /
`ρ cos φ'` geocentric-latitude conversion (§8.4 step 1) and the altitude formula (formula 8). When
milestone 5 lands, refactor `core/observer_coordinates.py` and the altitude calculation in
`core/local_circumstances.py` to call the shared primitives instead of keeping private copies — and
keep the Regulus test green through that refactor.

### Milestone 6 — Custom Sun position

Learn:

- mean longitude and anomaly;
- equation of centre;
- apparent solar longitude;
- distance and equatorial conversion.

Implement:

- textbook low/medium-precision solar position;
- custom geocentric ecliptic position;
- custom apparent RA/Dec;
- custom topocentric altitude/azimuth.

Prove:

- compare custom versus Skyfield across a full year;
- report maximum, median, and 95th-percentile angular error;
- document expected model accuracy.

### Milestone 7 — Custom event-search engine

Learn:

- sampling, sign changes, bracketing, bisection/Brent-style refinement;
- discontinuities and day-boundary handling;
- no-event and multiple-event cases.

Implement:

```text
scan interval → bracket crossing → refine root → classify event
```

Use it to calculate custom sunrise, sunset, transit, and twilight from the custom Sun position.

The occultation solver in `core/local_circumstances.py` is a hand-rolled Newton iteration of the
same family (`t ← t + τ`). When this milestone lands, express the occultation closest-approach
search through the shared solver so that convergence, tolerance, and iteration-count reporting are
consistent everywhere — this is also the cleanest way to settle the `iteration_count` question in
§7.3.

Prove:

- compare custom events with Skyfield and HKO;
- produce numerical error reports;
- include polar/no-event cases in unit tests even though Hong Kong normally has events.

### Milestone 8 — Moon position and daily events

Learn:

- lunar orbital arguments and periodic terms;
- lunar longitude, latitude, distance, and horizontal parallax;
- why the Moon is more sensitive to observer position and time.

Implement:

- textbook lunar coefficient tables as documented data;
- geocentric Moon position;
- topocentric correction;
- Moon altitude/azimuth;
- moonrise, transit, and moonset using the shared event solver.

Prove:

- support zero, one, or multiple events in a local calendar day;
- publish timing and angular error statistics.


### Milestone 9 — Lunar phases and 24 solar terms

Learn:

- Sun-Moon elongation and illumination;
- phase-angle conventions;
- apparent solar ecliptic longitude;
- 15-degree solar-term crossings.

Implement:

- new moon, first quarter, full moon, and last quarter;
- illumination fraction;
- all 24 solar terms for a selected year.

Prove:

- compare one complete year with HKO;
- document the time-scale, longitude, and rounding conventions that explain any residual difference.

### Milestone 10 — Planets and selected stars

Learn:

- heliocentric/geocentric positions, orbital elements, and Kepler's equation;
- light-time correction;
- star-catalogue epoch, proper motion, parallax, and aberration.

Implement:

- begin with one planet, preferably Mars;
- then add Mercury, Venus, Jupiter, and Saturn;
- add a small versioned catalogue of bright stars;
- reuse the event solver for rising, transit, and setting.

Prove:

- compare positions/events against Skyfield;
- do not download a multi-gigabyte star catalogue for the first implementation.

The bright-star catalogue matters for the occultation track: Meeus's Table I (printed pp. 237-283)
lists the occulted star by number/name, and predicting *which* star is occulted requires a star
position. For now the star's `d` and `H0` are read straight out of Table II, which sidesteps the
catalogue entirely.

### Milestone 11 — Batch pipeline and data product

Implement a deterministic command such as:

```bash
uv run occultation generate \
  --location hong-kong \
  --start 2027-01-01 \
  --end 2027-12-31 \
  --engine custom \
  --format parquet
```

Requirements:

- idempotent output;
- UTC and local timestamps stored explicitly;
- atomic writes;
- algorithm and data versions recorded;
- non-zero exit code on incomplete generation;
- JSON/CSV first, Parquet when tabular output is stable;
- reproducible output for identical code, inputs, and data.

Only after this milestone should a database be considered.

### Milestone 12 — Container, CI/CD, and observability

Add progressively:

- non-root multi-stage Docker image;
- CI stages for lint, type-check, tests, comparison, benchmark, build, and integration. **The
  existing pipeline is GitHub Actions (`.github/workflows/ci.yml`), not GitLab** — extend that
  workflow. GitLab remains a stated personal goal; treat it as a later mirror/second remote, and
  keep the committed CI in sync with whatever actually exists.
- dependency and container scanning;
- structured JSON logs;
- Prometheus metrics;
- Grafana dashboard;
- stale-output and validation-regression alerts;
- runbook and failure-recovery documentation.

Suggested metrics:

```text
almanac_calculation_duration_seconds
almanac_events_generated_total
almanac_validation_error_seconds
almanac_pipeline_failures_total
almanac_last_success_timestamp
```

### Milestone 13 — Performance and trading-infrastructure skills

Learn/use:

- `cProfile`, `py-spy`, `perf`, flame graphs, memory profiling;
- Linux processes, virtual memory, sockets, scheduling, and filesystems;
- TCP/UDP fundamentals and operational troubleshooting;
- deterministic benchmark datasets and regression thresholds.

Possible gates:

```text
10,000 position calculations under a measured target
one-year Hong Kong almanac under a measured target
pipeline fails on a performance regression greater than an agreed threshold
```

Do not invent performance targets before measuring a baseline.

### Milestone 14 — Lunar occultation capstone

**This is the milestone the current untracked work belongs to.** It has been pulled forward out of
roadmap order because the user chose to start from the textbook's occultation chapter (§1). That is
a legitimate deviation from "do not start with occultations" — but it must be recorded, because the
primitives milestone 14 depends on (astronomical time, coordinate transforms, the shared event
solver) do not exist yet. Until they do, `core/` keeps small, well-cited private copies and must not
grow into a second full implementation.

Learn:

- apparent topocentric Moon and star positions;
- lunar apparent semidiameter and limb profile;
- disappearance/reappearance contacts;
- position angle and grazing geometry;
- Besselian elements and the shadow-axis method — **already available** in the Meeus PDF (§8);
- limit magnitude and the light curve (Meeus printed pp. 315-317) — not yet attempted.

First simplified contact condition:

```text
angular separation (Moon, star) - apparent lunar radius = 0
```

Progress through:

1. spherical Moon;
2. one Hong Kong observer;
3. proper-motion-aware star;
4. refined contact times;
5. position angles;
6. lunar limb correction;
7. grazing occultation;
8. regional visibility.

Prove by comparing with Occult and explaining the remaining differences.

### Milestone 15 — Optional later work

- solar and lunar eclipses;
- traditional Chinese calendar;
- star maps and meteor-shower data;
- FastAPI service;
- PostgreSQL or ClickHouse storage;
- optional Nix development shell;
- Terraform/Kubernetes deployment if a real operational goal justifies them.


## 10. Day 1 setup — SUPERSEDED, kept for provenance

The original "Day 1: initial repository setup" section (uv bootstrap, dependency list, minimum
file list, GitLab job) has been **completed and is obsolete**, and its transcription was badly
OCR-damaged (commands such as `uv init`, `-package python 3.12`, `curl-LsSf https://astral.sh/u/
install.sh| sh`, `uv run hk-almanac —help`, and a file list referencing `src/hk_almanac/`). It is
replaced here by the verified state in §5.2 and the defect list in §7. Do not re-run any Day 1
bootstrap command; the project already exists and `uv sync` / the existing `.venv` are the
correct entry points.

What still stands from that section, restated accurately:

- Python must be 3.12 **managed by `uv`** (`.python-version` = `3.12`). The Mac's system Python
  must remain untouched.
- Dependencies are exactly `skyfield` (runtime) plus `pytest`, `pytest-cov`, `ruff`, `mypy`
  (dev). Do not add Astropy, pandas, FastAPI, database drivers, or infrastructure packages yet.
- The initial CLI only needs `--help` and `--version`, and the first test only verifies that the
  CLI parser imports — that test exists (`tests/test_cli.py`) and passes, but as originally written
  it did not catch defect D1 because it inspected `build_parser()` instead of the installed console
  script. An entry-point test was added when D1 was fixed: `tests/test_cli.py` now also asserts the
  declared console-script target is `occultation.cli:main` and that `main()` prints real usage for
  `--help` and the version for `--version`.
- CI must run `uv sync --locked`, Ruff, mypy, and pytest — which is what
  `.github/workflows/ci.yml` already does; see milestone 12 in §9 for the remaining
  CI/observability roadmap.

The first *astronomy* issue is still:

```text
feat: calculate Hong Kong Sun position with local Skyfield ephemeris
```

but it is now blocked behind closing §7.2, and the occultation work already under way (§8) is an
accepted parallel track rather than a violation of the old "do not start with occultations" rule.

### 10.1 `local/COPY_INTO_REPO.md` — also superseded, but its numbers are still useful

That note ("Copying the Meeus Day 2 files") is the instruction sheet that accompanied the
OCR-derived files. It is stale in the same ways: it tells the reader to preserve
`src/hk_almanac/domain/__init__.py` and to import from `hk_almanac.domain.occultation` — neither the
package nor that module exists, and `domain/` has no `__init__.py` at all (defect D7). Do not follow
its copy instructions literally.

What is worth keeping is its "Expected reference result" block, which independently corroborates
the Example 5 values transcribed in §8.4:

```text
hours after reference  0.455608 hours
TD                     10:27:20
UT                     10:26:15
separation             1.1526 lunar radii
limb clearance         0.1526 lunar radii
position angle         24.67 degrees
altitude               43 degrees (42.65 before rounding)
occultation            false
```

Treat that agreement as a *second* reason to trust these specific numbers — they appear both in the
book's worked example and in the earlier transcription note. It is **not** a substitute for reading
printed pp. 228-229 in the PDF before writing the fixture (§8.3). When the rewrite lands, move this
table into the fixture and the regression test, then delete `COPY_INTO_REPO.md` or mark it
superseded in place; leaving a second, contradictory instruction sheet in `local/` is how the next
agent gets misled.

Its suggested commit message is also misspelled ("reproduce Mees Regulus Local circumstances");
use the §13 conventions instead, e.g.

```text
feat(occultation): reproduce Meeus Regulus 1999 local circumstances
```

## 11. Testing and validation policy

Use five levels of evidence:

- **Unit tests:** textbook examples and isolated mathematical functions.
- **Property tests:** round trips, invariants, angle ranges, and event ordering.
- **Differential tests:** custom engine versus Skyfield with identical inputs.
- **Product tests:** final Hong Kong output versus HKO, and later versus Occult.
- **Transcription tests:** for the Meeus work specifically — a fixture value is admissible only
  after it has been read off the printed page by eye, and the fixture records both the printed page
  and the PDF page (§8.3). A test that encodes an OCR guess is worse than no test, because it
  launders a plausible-looking wrong number into a permanently green check.

Comparison output should be machine-readable:

```text
event_type,date,custom_time,reference_time,error_seconds
```

Reports should include:

- maximum error;
- median error;
- 95th percentile;
- missing expected events;
- unexpected events;
- input/algorithm/data versions;
- known reasons for differences.

Never require every astronomical result to match to one second without justifying that tolerance.
Accuracy targets must be defined per algorithm and event type.

## 12. Data-pipeline and operational policy

The production-style pipeline should eventually follow:

```text
validate local inputs
→ calculate events
→ validate results
→ write temporary output
→ atomically publish output
→ emit metrics/logs
```

`dataflow.mmd` in the repository root is a Mermaid sketch of this flow, including a Kafka/Redis
queue layer. It is **aspirational**: there is no queue, no scheduler, and no pipeline code in the
repository. Do not read it as a description of current behaviour, and do not build it out before
milestone 11.

Requirements:

- deterministic and idempotent;
- explicit data lineage;
- checksums for external inputs;
- no partial output marked successful;
- clear exit codes;
- safe reruns;
- last-known-good data snapshot;
- documented update and rollback procedure.

These characteristics are more valuable for the user's trading-firm portfolio than adding many
technologies without a real need.


## 13. Git and work-management conventions

Suggested labels:

```text
astro
math
python
validation
data
observability
performance
documentation
```

Prefer small pull requests (the repository is hosted on GitHub) that contain:

- one concept or feature;
- tests;
- algorithm/source documentation;
- a reproducible command showing the result;
- no unrelated refactoring.

Useful commit prefixes:

```text
chore:
docs:
test:
feat:
fix:
refactor:
perf:
```

## 14. Instructions for future AI assistants

### Always do

- Lead with the next concrete outcome.
- Explain the astronomy in beginner-friendly language.
- Connect each implementation step to a test or observable output.
- Keep reference and custom engines separate.
- Use local, pinned, verified scientific data.
- Record sources and assumptions beside the implementation.
- Reuse the same domain result shape across engines.
- Compare before replacing a reference calculation.
- Preserve user-written code and unrelated repository changes.
- Read `AGENTS.md` at the repository root, then follow its pointer to this file — it names
  `docs/AGENT_HANDOFF.md`, the tracked copy, as of 2026-03-09 (defect D12 closed).
- Verify locally before saying a step is complete.
- Keep the project runnable at the end of every milestone.

### Never do

- Do not tell the user to globally replace the macOS system Python.
- Do not switch the project away from `uv` without explicit user approval.
- Do not attempt the full almanac in one change.
- Do not hide frame/time-scale/unit conversions inside unexplained helper code.
- Do not use Skyfield throughout the custom core.
- Do not prohibit Skyfield from the initial prototype; it is intentionally the first working engine.
- Do not silently download data during runtime.
- Do not copy coefficient tables without provenance.
- Do not add infrastructure only to make the stack look larger.
- Do not treat HKO/Skyfield/Occult disagreement as automatically proving the custom result is
  wrong; investigate conventions and precision.
- Do not claim independent calculation while still routing the custom engine to Skyfield internally.
- Do not present generated occultation predictions as observation-grade until accuracy is validated.
- **Do not paste OCR output into source files, fixtures, or docs.** That is how the repository
  reached the state described in §7. Transcribe by hand from the scan, one value at a time, with a
  page reference.
- Do not assume the repository is empty, and do not re-run Day 1 bootstrap commands (§10).

### Ask the user before

- changing the target almanac scope;
- choosing a paid cloud deployment;
- committing or storing large ephemeris/catalogue files, or the copyrighted textbook scan;
- changing the primary ephemeris or supported date range;
- adding a database, API, Kafka, Kubernetes, or Nix;
- publishing predictions for operational astronomy use;
- loosening accuracy thresholds after a regression;
- deleting or moving the untracked Meeus files (§15).


## 15. Current status handoff

> **Superseded in part on 2026-03-09 (milestone 0 closed — see Appendix B).** The status table,
> the "untracked work in the tree" list, and open decisions 1, 2, 3 and 5 below describe the state
> *before* the repair pass. `docs/AGENT_HANDOFF.md` now exists (D12 closed), the seven Meeus files
> have been re-typed and are green, and `docs/algorithms/meeus-star-local-circumstances.md` has been
> written. Re-run the §16.1 checklist and the Appendix B quality gate rather than trusting the
> "CI is therefore red today" row.

Verified as of 2026-03-09. The items the previous version of this file listed as "unknown until the
repository is inspected" are now answered:

| Previously unknown | Answer |
| --- | --- |
| Has `uv init` been run? | Yes — `pyproject.toml`, `uv.lock`, `.python-version`, `.venv` all exist |
| Which files are committed? | Only the scaffold: `.gitignore`, `.python-version`, `README.md`, `AGENTS.md`, `dataflow.mmd`, `pyproject.toml`, `uv.lock`, `.github/workflows/ci.yml`, `config/locations/hong_kong.toml`, `data/README.md`, `data/manifest.json`, `src/occultation/__init__.py`, `src/occultation/cli.py`, `tests/test_cli.py` |
| Is a runner/pipeline configured? | Yes — GitHub Actions `.github/workflows/ci.yml`, single `quality` job, triggers `push` to `main`/`develop` plus `pull_request`: checkout@v7 → `astral-sh/setup-uv@v9.0.0` (pinned uv `0.12.7`, cache on) → `uv python install` → `uv sync --locked --dev` → `uv run python --version` → `ruff check .` → `ruff format --check .` → `mypy src` → `pytest --cov=occultation --cov-report=term-missing`. **Not GitLab.** CI is therefore red today. |
| Is the textbook PDF in the repository? | No — it was moved to `local/meeus_ocr/MeeusTables_Occultation.pdf` on 2026-03-09, which is git-ignored (defect D8 closed, §8.2) |
| Which ephemeris has been selected? | None. `data/manifest.json` has zero datasets; `data/external/` does not exist |
| Has reference data been downloaded? | No |

Untracked work in the tree — all seven files OCR-derived, all currently non-functional:

```text
src/occultation/core/local_circumstances.py
src/occultation/core/observer_coordinates.py
src/occultation/domain/observer.py
src/occultation/domain/occulation.py
tests/fixtures/meeus_regulus_1999.toml
tests/reference_cases/test_meeus_regulus.py
tests/unit/test_observer_coordinates.py
```

Modified but **uncommitted** tracked file: `AGENTS.md` (defect D12 part-fix — it now points at
`local/README_AI_HANDOFF.md`). Commit it with the milestone 0 PR.

Everything under `local/` — this handoff, `COPY_INTO_REPO.md`, the notes `best_project_stack` and
`dummy_ci.yml`, the directories `git_usage/`, `linux/`, `python/`, and `meeus_ocr/` (the scan plus
the OCR script and output, §8.3) — is **git-ignored** by `local/.gitignore` (a single `*`), so it
never appears in `git status`. That is why the file list above plus `AGENTS.md` is the complete set
of non-committed work.
`.coverage` is likewise ignored (root `.gitignore` line 43) but still sits in the worktree.

Branch state: `main` = "Initial commit"; `develop` is checked out (HEAD) and adds
"Init python 3.12 project & gitlab ci" plus two GitHub-Actions fixes
("pin install uv action to 9.0.0", "typo for Install Python task"). The message still says
"gitlab ci" although no `gitlab-ci.yml` was ever committed — the only CI in the repository is
GitHub Actions. Both branches track `origin`; the remote is
`https://github.com/Remember-Urinating-before-bed/occultation.git`.

Open decisions for the user — do not resolve these unilaterally:

1. **Repair or discard the untracked Meeus files?** Recommended: repair. The design and the numeric
   targets in §7.3 and §8.4 are sound; only the text is corrupted. Discarding is also defensible if
   the user would rather restart the transcription cleanly.
2. **Rename `domain/occulation.py` → `domain/occultation.py`?** Recommended: yes, now, while nothing
   depends on the misspelling (defect D6).
3. **Should curated transcription be committed?** Recommended: yes as `docs/algorithms/*.md` and
   `tests/fixtures/*.toml` with page provenance; **no** for raw OCR dumps or the scan itself (§8.5).
4. **Is GitLab still a target?** The repository is on GitHub with GitHub Actions CI, and no
   `.gitlab-ci.yml` has ever existed here. Milestone 12's "CI stages" wording should be read as
   GitHub Actions stages; mirror to GitLab only if the user actually asks for it.
5. **Should this handoff live in the repository?** It currently sits in the git-ignored `local/`
   directory, so it is invisible to other clones and to CI. Recommended: copy it to
   `docs/AGENT_HANDOFF.md` (a tracked path) once the defects are fixed, and mark
   `local/COPY_INTO_REPO.md` superseded (§10.1). Confirm with the user before adding tracked files
   under `local/`'s ignore rule. Half of this is already done: on 2026-03-09 `AGENTS.md` was edited
   to name `local/README_AI_HANDOFF.md` instead of the non-existent root `handoff.md`, so the
   dangling pointer is gone in *this* working copy. The decision that remains is the tracked path —
   until it exists, a fresh clone or CI-run agent following `AGENTS.md` still finds nothing, which is
   the open part of defect D12.

## 16. Immediate execution order

The roadmap in §9 is the long-term plan. The next increments, in order:

> **Status 2026-03-09: items 1 and 2 below are DONE** (Appendix B). The quality gate is green, the
> entry point is fixed and covered by `tests/test_cli.py`, the seven Meeus files are re-typed and
> passing, and the transcription exists as `docs/algorithms/meeus-star-local-circumstances.md`.
> Resume at item 3.

1. **Make the quality gate green** (milestone 0, §7.2): fix D1 (entry point), D2 (`hk_almanac` →
   `occultation` imports), D3/D5 (re-type the broken modules and tests), D4 (valid TOML fixture),
   D6 (rename), D7 (`__init__.py` files), the D11 typos in the tracked scaffold files, and the
   remaining half of D12 (copy this handoff to a tracked path and repoint `AGENTS.md` at it).
   D8 is already closed: the scan and the OCR artefacts moved to `local/meeus_ocr/` on 2026-03-09
   (§8.3). Acceptance: every
   command listed in §7.1 and in milestone 0 (§9) succeeds — including `uv run occultation --help`,
   which must print the argparse usage text rather than "Hello from occultation!", and `uv run pytest`
   must collect and pass with zero collection errors. Commit the pending `AGENTS.md` edit as part of
   this work.
2. **Land the transcription as documentation**: write
   `docs/algorithms/meeus-star-local-circumstances.md` from §8.4 with printed-page citations, and
   make the Regulus fixture a real regression test. Re-derive `iteration_count` from the chosen
   starting guess rather than asserting the stale value.
3. **Then, and only then, resume the almanac spine**: select and document the local JPL ephemeris
   with checksum verification (milestone 1 prerequisite), then one Hong Kong Sun position with
   Skyfield (milestone 1), then one month of Sun events with an HKO comparison report (milestone 2).
4. Begin custom learning with angles/vectors and astronomical time (milestones 3-4).
5. Implement the custom Sun position and event search (milestones 5-7).
6. Only then proceed to the Moon and the rest of the roadmap.

### 16.1 How to continue (checklist for the next agent)

1. `cat AGENTS.md` — it points at this file, `docs/AGENT_HANDOFF.md` (the tracked copy; D12 closed).
   Read this whole file, then do not skip §7 or Appendix B.
2. `git status --porcelain -uall` — as of the milestone-0 closure the tree holds the repaired files
   plus `AGENTS.md`, `pyproject.toml`, `config/locations/hong_kong.toml`,
   `src/occultation/__init__.py` and `tests/test_cli.py` as modified, all **uncommitted**; confirm
   before adding to them and preserve anything the user added.
3. Reproduce the quality gate (it is green — Appendix B — so a red result here means something
   changed since the last session, not that milestone 0 needs redoing):

   ```bash
   uv run python --version
   uv run occultation --help
   uv run python -m occultation.cli --help
   uv run pytest
   uv run ruff check .
   uv run ruff format --check .
   uv run mypy src
   ```

   If the results differ from Appendix B, work out why before trusting either list.
4. Commit the milestone-0 work (step 2's file set) once step 3 is green, then move to §16 item 3:
   the ephemeris selection / milestone 1.
5. For any Meeus number you type into code, a fixture, or a doc, open the PDF page first and cite
   printed page + PDF page in a comment. Never paste OCR output (§14). Where this file and the scan
   disagree — as they do for `eta'` (Appendix B) — the scan wins; record the reasoning in
   `docs/algorithms/`.
6. Re-run the commands in step 3 and record the new counts.
7. Report using the template below, and update §0/§7/§15/Appendix B of this file if reality has
   moved.

At the end of every AI session, report:

```text
Completed:
Verified by:
Current milestone:
Next smallest task:
Open questions / blockers:
```

## Appendix A — Changes in this rewrite (2026-03-09)

The previous version of this handoff was itself partly OCR-damaged and partly stale. Corrected:

| Was | Now |
| --- | --- |
| Described the package as `hk_almanac` with a `hk-almanac` console script | Package/import is `occultation`, console script `occultation` (§3.1, D1/D2) |
| Assumed a GitLab repository and `gitlab-ci.yml` pipeline | Repository is on GitHub; CI is `.github/workflows/ci.yml` (§0, §15, milestone 12) |
| Treated the project as an empty repository awaiting Day 1 bootstrap | Day 1 is complete; the section is now a superseded note (§10) and the real state is in §5.2/§7 |
| "Do not begin with occultations; they are an advanced capstone" | Superseded with the reason and the guardrails (§3.5); occultation local circumstances are an accepted early work-package, milestone 14 remains the capstone |
| Claimed a green/unknown quality state | Records the verified red state with command output (§7.1) and a defect inventory D1-D12 (§7.2) |
| No mention of the Meeus PDF | Full provenance: image-only scan, printed page = PDF page + 218, page map, OCR caveats, hygiene rules (§8) |
| No algorithm documentation | Curated, page-cited transcription of the star-occultation local-circumstances method plus the Regulus 1999 regression values (§8.4) |
| Four levels of validation evidence | Five, adding transcription tests (§11) |
| Garbled prose throughout (`ImpLement`, `Gratana`, `memroy`, `questiokns`, `Preduct`, broken URLs) | Re-typed and, where relevant, re-verified against live sources (§4) |

Unchanged in substance: the project goal (§2), the reference/custom boundary (§3.4), the no-runtime-download rule (§3.3), the scope discipline (§3.5), the milestone ordering beyond the occultation deviation (§9), and the "always/never/ask-first" rules (§14).

### A.1 Second-pass corrections (same day)

After the rewrite above, every command in §7.1 was re-run and every file reference re-checked. Fixes
made in that pass:

| Was | Now |
| --- | --- |
| D5 blamed both tests on the `→` glyph | `test_meeus_regulus.py` actually fails with `unmatched ')'` on line 8; only `test_observer_coordinates.py` has the `→` (and a mangled test name) |
| §7.1 omitted the interpreter version and the passing test | Adds `uv run python --version` → `Python 3.12.14` and `uv run pytest tests/test_cli.py -q` → `1 passed` |
| §7.3 listed three inconsistent iteration values | Adds the module's real keyword defaults, `convergence_tolerance_hours = 1e-6` and `max_iterations = 20`, so the mismatch is fully documented |
| Defect list stopped at D10 | Adds D11: the `occulation` typo in the tracked `pyproject.toml` description |
| D2 claimed 8 mangled import lines | `grep -rniE 'hk.?almanac\|hk almanas' src tests` returns **7** hits in 4 files; D2 now lists each one with its file and line number |
| D4 described the TOML damage only in general terms | Enumerates each malformed line (including the second stray-space table header on line 23 and the missing `=` on lines 29-30) |
| Nothing noticed that `AGENTS.md` points at a non-existent `handoff.md` | Added as defect D12 and linked to open decision 5 in §15 |
| §8.4 quoted invented tolerance values | Lists the tolerances that are actually in `test_meeus_regulus.py` and `test_observer_coordinates.py` (read from the files) |
| §7.3 implied the observer test file holds one test | Records all three tests, including the southern-hemisphere sign test and the invalid-latitude test, so none is lost in the rewrite |
| D5 stopped at the two fatal syntax errors | Adds the further damage in `test_observer_coordinates.py` (comma decimal separators, capitalised keyword arguments, `Se-7`) showing that a glyph patch would not rescue the file |
| §8.3 did not say whether the OCR output still exists | Confirms the `$TMPDIR/meeus_ocr/` contents present on 2026-03-09 and where to move them |
| §3.1 heading ran into its first bullet | Blank line added; same for the document title |
| §15 called `best_project_stack` a directory | It is a plain file; `git_usage/`, `linux/`, `python/` are the directories |
| §5.2 called `local/` "untracked" | It is git-**ignored**, which is a different thing and the one that matters here |
| §3.3 and §0 prose carried hard line breaks from the previous edit | Reflowed; no content change |

Verified in this pass, and unchanged: `git ls-files` matches the committed-scaffold list in §15;
`git status --porcelain -uall` matched the then-eight-file untracked list in §15 (seven code/fixture
files plus the PDF — that list has since changed, see A.2); the CI action pins in
§15 match `.github/workflows/ci.yml`; every `§` cross-reference in this file resolves to a heading
that exists; markdown fences balance and no table has mismatched columns.

### A.2 Third pass — the two repository changes made on 2026-03-09

Two user-directed changes were made after the second pass. They are the **first edits to anything
outside `local/`** in this whole exercise, so they are recorded here rather than folded into A.1.

| Change | Effect |
| --- | --- |
| `AGENTS.md` line 3 now reads "Read local/README_AI_HANDOFF.md completely…" and a note was added that no root `handoff.md` exists and that `local/` is git-ignored | Closes the dangling-pointer half of **D12**. The file is tracked, so this shows up as `M AGENTS.md` and still needs committing |
| The scan moved from `src/occultation/` to `local/meeus_ocr/MeeusTables_Occultation.pdf`, and `ocr.swift`, `all_pages.txt`, `p1.txt`, `build.log`, `all_pages.err`, `p1.err` copied from `$TMPDIR/meeus_ocr/` into the same directory | Closes **D8** (nothing scannable left inside the built package) and de-temporalises the OCR output. Verified git-ignored with `git check-ignore -v`. `git status --porcelain -uall` still prints eight lines, but their composition changed: the PDF left the untracked set (it is now ignored, not merely untracked), so the list is seven untracked files plus `M AGENTS.md` |

Consequential documentation edits: §0 PDF and working-tree rows, §4 source table, §5.2 tree
(`local/meeus_ocr/`, `AGENTS.md` annotation), §7.2 D8 and D12 marked fixed/partially fixed, §8.1,
§8.2, §8.3 (rewritten as "where the artefacts live", with the file list, the real 220 dpi scale
factor read off `ocr.swift`, and the re-run command), §8.5, §14 "always do", §15 status table and
file list, open decision 5, and §16/§16.1. A `local/meeus_ocr/README.md` was also added so the
provenance and the "never a source of truth" rule travel with the artefacts rather than only with
this handoff.

Corrections made while writing §8.3: the earlier draft said the pages were rendered at ~300 dpi with
`sips`/Quartz; `ocr.swift` actually renders in-process via `CGContext` at `scale = 220.0 / 72.0`
(≈220 dpi), and no `sips` step was involved. The compiled `ocr` binary was not copied — it is
rebuildable.

## Appendix B — Milestone 0 closure (2026-03-09, second session)

The seven OCR-damaged untracked files were **deleted and re-typed from the scan**, not patched in
place, per the §14 rule "do not paste OCR output into source files". Every defect in §7.2 that
milestone 0 covers is now closed.

| ID | Status | What was done |
| --- | --- | --- |
| D1 | closed | `pyproject.toml` now reads `occultation = "occultation.cli:main"`; `src/occultation/__init__.py` no longer defines `main()` (it is a docstring-only package init), so the hello text cannot come back |
| D2 | closed | Zero `hk_almanac` hits remain under `src/` or `tests/`; all imports are `occultation.*` |
| D3 | closed | `core/local_circumstances.py` re-typed from §8.4 — see the notes below on the two places the draft was wrong |
| D4 | closed | `tests/fixtures/meeus_regulus_1999.toml` re-typed as valid TOML with snake_case keys and a provenance header; `tomllib.load` accepts it |
| D5 | closed | Both test files re-typed from scratch. The three unit tests of §7.3 are all present (Palomar values, southern-hemisphere signs, `latitude_deg` validation error) |
| D6 | closed | The module is `src/occultation/domain/occultation.py`; the misspelled file is gone |
| D7 | closed | `src/occultation/core/__init__.py` and `src/occultation/domain/__init__.py` exist |
| D8 | closed earlier | See A.2 |
| D11 | closed | `pyproject.toml` description says "occultation"; `config/locations/hong_kong.toml` now has `longitude_deg_east`, `datum`, and a full ISO retrieval date |
| D12 | closed | This file is the tracked copy at `docs/AGENT_HANDOFF.md`; `AGENTS.md` points at it |

D9 (`.coverage` in the worktree) and D10 (empty data manifest) are out of scope for milestone 0 and
remain open.

### Two substantive corrections found while re-typing

1. **`eta'` uses xi, not zeta.** The §8.4 transcription as first written read
   `η' = 0.01745329 (H1 ζ sin d − ξ' D1)`. The `ζ` in the first term is an OCR artefact: the author's
   own BASIC listing on printed p. 236 (PDF p. 18) has
   `1414 E1 = R * (KO * S9 * H1 - Z * D1)` where `KO` is xi and `Z` is zeta, so the correct form is
   `η' = 0.01745329 (H1 ξ sin d − ζ D1)` — §8.4 has been corrected in place on that basis. The star
   case therefore reduces to `eta' = 0.01745329 H1 xi sin d`. Numerically the difference is
   decisive: with `zeta`
   the Regulus case converges to `t = 0.449736`, `v' = -0.18953`; with `xi` it converges to
   `t = 0.455608`, `v' = -0.18556`, which are the printed p. 229 values. The full argument, with the
   listing excerpt, is in `docs/algorithms/meeus-star-local-circumstances.md` §6.
2. **Starting guess and iteration count.** The draft solver began at `t = 6.0` h and the draft test
   asserted `iteration_count == 5` — a third, unrelated number, and neither reproducible. The
   re-typed solver follows printed p. 224 ("take t = 0 as a first approximation"), counts the
   iterations the loop actually performs, and needs **four** for Example 5 at the draft's own
   `|tau| < 1e-6` h tolerance. The test asserts that derived count with a comment explaining where it
   comes from. No `iteration_count` was added to the fixture, per §7.3's warning.

### Verified quality gate (all green)

```bash
uv run python --version            # Python 3.12.14
uv run occultation --help          # argparse usage text, not the hello message
uv run occultation --version       # 0.1.0
uv run pytest -q                   # 8 passed
uv run ruff check .                # All checks passed!
uv run ruff format --check .       # 16 files already formatted
uv run mypy src                    # Success: no issues found in 8 source files
```

`tests/test_cli.py` was extended in the same pass, so D1 is now covered automatically: it asserts
the declared console-script target is `occultation.cli:main` and that `main()` prints real usage for
`--help` and `0.1.0` for `--version`. The manual proof is still
`uv run occultation --help`, which prints the argparse usage rather than the old hello text.


