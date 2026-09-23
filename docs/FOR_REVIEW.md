# For review — a runnable occultation CLI, and proof that it matches the book

**Audience:** anyone who wants to check the work without reading Python.
**Branch:** `feat/cli-local-circumstances`, merged into `develop`.
**Date:** 2026-09-23.

---

## 1. The one-paragraph version

The repository already contained a working calculation: given the Moon's
Besselian elements, it finds the moment a star passes closest to the Moon for
one observer, and reports how far apart they were. Until now that calculation
was only reachable from inside the test suite — there was no way to run it from
a terminal. This change adds a real command line in front of it, adds the two
file loaders it needs, adds an explicitly *empty* reference-engine seam, and
adds a `verify` command that re-runs the textbook's own worked example
(Jean Meeus, *Astronomical Tables*, Example 5: occultation of Regulus,
1999 March 1, Palomar) and prints every printed value next to this code's
value. The command exits `0` when the numbers agree and `1` when they do not,
so it can be used as a check rather than as a claim.

## 2. What you can run in two minutes

```bash
cd /Users/workworkwork/Documents/repo/occultation
uv sync --locked --dev

# 1. Re-run the book's worked example and compare every printed digit.
uv run occultation verify meeus-example-5

# 2. Run the calculation for Hong Kong from the two files in the repository.
uv run occultation local-circumstances \
  --elements tests/fixtures/meeus_regulus_1999.json \
  --location config/locations/hong_kong.toml \
  --delta-t-seconds 65

# 3. The same run, machine-readable.
uv run occultation local-circumstances \
  --elements tests/fixtures/meeus_regulus_1999.json \
  --location config/locations/hong_kong.toml \
  --delta-t-seconds 65 --format json

# 4. The whole quality gate.
uv run pytest -q
uv run ruff check . && uv run ruff format --check . && uv run mypy src
```

Command 1 currently prints `VERDICT: matches ...` and exits `0`. Command 4
currently prints `41 passed`, `All checks passed!`, `26 files already
formatted`, and `Success: no issues found in 13 source files`.

## 3. The actual output of `verify meeus-example-5`

```text
Example 5 - Occultation of Regulus, 1999 March 1
source   : Jean Meeus, Astronomical Tables, Occultations
pages    : printed 228-229 (PDF 10-11)
fixture  : .../tests/fixtures/meeus_regulus_1999.json

quantity                               this code       printed    difference
----------------------------------------------------------------------------
rho_sin_geocentric_latitude             0.546862      0.546862     +0.000000
rho_cos_geocentric_latitude             0.836338      0.836338     +0.000000
hours_after_reference                   0.455608      0.455608     +0.000000
dynamical_time_hour                    10.455608     10.455608     +0.000000
universal_time_hour                    10.437552     10.437500     +0.000052
separation_in_moon_radii                1.152556      1.152600     -0.000044
limb_clearance_in_moon_radii            0.152556      0.152600     -0.000044
position_angle_deg                     24.665401     24.670000     -0.004599
altitude_deg                           42.649869     43.000000     -0.350131
is_occultation                          0.000000      0.000000     +0.000000

iterations: 4
VERDICT: matches the printed example within the tolerance its printed precision supports.
```

Read it as: the left column is what this repository calculates, the middle
column is what the book prints, and the right column is the difference. The
differences are all at or below the last digit the book prints, which is the
only honest tolerance available: Meeus rounds his intermediate results, so his
printed answer and an unrounded re-computation cannot be expected to agree
beyond the printed digits.

The one number that needs explaining is `altitude_deg`, where the difference is
0.35 degrees. Meeus prints the Regulus altitude as `43` — to the nearest whole
degree, not to a decimal place — so the tolerance is ±0.5 degrees and this
code's 42.65 is inside it. That tolerance is asserted in the existing
regression test with a comment saying exactly this.

## 4. How the calculation works, step by step

This section follows one run of `local-circumstances` from the two input files
to the printed answer, in the order the program actually evaluates things. Every
formula is Meeus's, and every intermediate number below was produced by running
the code, not by reading it. The unit tests in `tests/unit/` assert the same
steps in isolation, so the arithmetic on this page is pinned down twice.

### 4.1 What the two input files supply

`--elements tests/fixtures/meeus_regulus_1999.json` (the book's Example 5 data):

| Symbol | Meaning | Value used |
| --- | --- | --- |
| `To` | tabular reference instant, in Dynamical Time | 10.0 h TD |
| `d0` | star declination | +11.9694° |
| `H0` | Greenwich hour angle of the star at `To` | 156.6836° |
| `H1` | hourly rate of that hour angle | 15.04107°/h |
| `X0 X1 X2` | Moon's shadow X in the fundamental plane | +0.22151, +0.55549, −0.00000 |
| `Y0 Y1 Y2` | Moon's shadow Y in the fundamental plane | +0.19947, −0.15258, −0.00001 |
| `k` | Moon's shadow radius, in Earth radii | 0.272495 |

`--location config/locations/hong_kong.toml` (or the Palomar site inside the
fixture) supplies `φ = 22.3020° N`, `λ = 114.1743° E`, elevation 0 m. Note the
sign convention: the project stores **east-positive** longitude, while the book
prints **west-positive** values, so the fixture carries −116.8640 for Palomar.

`--delta-t-seconds 65` supplies ΔT, the difference between uniform Dynamical
Time and the uneven UT that clocks follow. It is a required argument: the
program never guesses it.

### 4.2 Step 1 — where the observer is, as seen from the Earth's centre

The observer is on a flattened, spinning Earth, but the fundamental plane is
geocentric. Meeus's printed p. 224 gives the conversion with
`k' = 0.99664719` (= 1 − flattening) and `a = 6378140 m`:

```text
tan w        = k' tan φ
ρ sin φ'     = k' sin w + (z / a) sin φ
ρ cos φ'     =      cos w + (z / a) cos φ
```

For Hong Kong (`φ = 22.3020°`, `z = 0`):

```text
w            = atan(0.99664719 × tan 22.3020°) = 22.23304°
ρ sin φ'     = 0.99664719 × sin w              = +0.3771298489289325
ρ cos φ'     =                cos w            = +0.9256427709186403
```

For Palomar (`φ = 33.3562°`, `z = 1706 m`, so `z/a = 0.00026748`) the same two
lines give `ρ sin φ' = +0.5468621184509352` and
`ρ cos φ' = +0.8363383814272883` — the book's `+0.546862` and `+0.836338`.

These two numbers are the only things the rest of the method needs from the
observer; the geocentric latitude `φ'` never appears on its own. They are
printed in the run's output as `rho sin phi'` and `rho cos phi'` and echoed in
the JSON under `derived`, because a coordinate-convention mistake shows up here
first.

### 4.3 Step 2 — iterate to the instant of closest approach

The Moon's shadow moves across the fundamental plane; the observer's own
position in that plane moves too, because the Earth turns. The star is occulted
if the two ever come within one lunar radius. So the program looks for the
instant `t` (in hours after `To`) at which the *topocentric* distance between
star and Moon is smallest.

It starts from the book's prescribed first guess `t = 0` and then repeats the
same block. With `t` the trial instant, `λ` the observer's west-positive
longitude and `ΔT` in seconds:

```text
d   = d0                                  (D1 = 0 for a star)
H   = H0 + H1 t − λ − ΔT / 239.345        local hour angle of the star
x   = X0 + X1 t + X2 t²       x' = X1 + 2 X2 t        Moon's shadow
y   = Y0 + Y1 t + Y2 t²       y' = Y1 + 2 Y2 t
ξ   = ρ cos φ' sin H                                  observer, from 4.2
η   = ρ sin φ' cos d − ρ cos φ' cos H sin d
ξ'  = 0.01745329 H1 ρ cos φ' cos H
η'  = 0.01745329 H1 ξ sin d               (star case; see §6)
u   = x − ξ        v  = y − η             star relative to Moon
u'  = x' − ξ'      v' = y' − η'
n²  = u'² + v'²                           squared relative speed
τ   = −(u u' + v v') / n²                 how far to move t, in hours
```

Then `t ← t + τ` and the whole block is evaluated again, until `|τ| < 0.000001`
hours — the book's own cutoff, about 3.6 ms. The divisor `239.345` is Meeus's
conversion from seconds of ΔT to degrees of hour angle; it is *not* 3600. The
factor `0.01745329` is π/180 to the eight decimals the book prints, converting
the degree-valued `H1` into radians so that `ξ'` and `η'` come out in Earth
radii per hour.

For Palomar the four iterations come out as:

```text
iteration  t at start        H            u            v            τ
1          0.000000000       39.548025    −0.311007    −0.201759    +0.458368810
2          0.458368810       46.442383    −0.129950    −0.285923    −0.002716953
3          0.455651857       46.401517    −0.131048    −0.285418    −0.000043138
4          0.455608719       46.400868    −0.131065    −0.285410    −0.000000679
```

`τ` is the whole point of the iteration: it is the amount by which the current
guess misses the closest approach, computed from the dot product of the relative
position `(u, v)` with the relative velocity `(u', v')`. When that dot product is
zero the two are perpendicular, which is exactly the definition of closest
approach. The last `τ` is below the cutoff, so the loop stops and reports
`t = 0.45560804016498896` hours after `To`. The book prints `+0.455608`.

The run prints `iterations 4`. Four, not the book's "two or three", because the
book's remark assumes a good hand-computed first guess while this code starts
from the prescribed `t = 0`. The count is asserted by the regression test, so
changing the starting guess or the tolerance is a visible change rather than a
silent one.

### 4.4 Step 3 — the numbers the observer actually wants

At the converged instant the same block is evaluated one last time, and four
quantities are derived from it (printed pp. 225–226):

```text
tan P = u / v                    (4)  position angle of the star on the disc
L     = k = 0.272495             star case
Δ     = (u v' − v u') / (n L)    (6)  least separation, in lunar radii
|Δ| − 1                          limb clearance, negative when occulted
sin h = sin d sin φ + cos d cos φ cos H   (8)  altitude of the star
```

For Palomar:

```text
u = −0.131065374   v = −0.285410419   u' = +0.404084804   v' = −0.185563163
n = 0.444655166    H = 46.40085791926337°
Δ = (−0.131065374 × −0.185563163 − (−0.285410419) × 0.404084804) / (0.444655166 × 0.272495)
  = +1.1525556852636376
limb clearance = 1.1525556852636376 − 1 = +0.1525556852636376
P = atan2(−u, −v) mod 360 = 24.66545623923445°
h = 42.64987704325327°
```

Three sign conventions live in those four lines, and all three are easy to get
wrong:

- **`Δ` takes its sign from the cross product `u v' − v u'`, not from `v`.**
  Positive means the star passes north of the Moon's centre. `|Δ| > 1` means no
  occultation at that site — which is the case here, so the program answers
  `occulted? no`.
- **`P` needs a quadrant rule.** Meeus requires `cos P` to carry the sign
  *opposite* to `v`; the code encodes that as `atan2(−u, −v) mod 360`, which
  reproduces the book's `24°.67`. `P` is measured from the Moon's North Point
  towards East, South, West.
- **`h` uses the local hour angle `H`, not the Greenwich one**, and a negative
  `h` means the event is below the horizon and cannot be seen.

### 4.5 Step 4 — the answer, in the two time scales

The instant of closest approach is `To + t` in **Dynamical Time**; subtracting
ΔT expresses it in **UT**, which is what a clock shows:

```text
TD = 10.0 + 0.45560804016498896 = 10.45560804016498896 h
UT = 10.45560804016498896 − 65 / 3600 = 10.437552484609434 h
```

The book prints `10h.455608` TD and `10h26m15s` UT. The program prints
`10.437552` UT, i.e. `10h 26m 15.2s`: the book rounds UT to the nearest second,
which is why that one comparison gets a wider tolerance than the others.

### 4.6 The same four steps for a different observer

Nothing above is specific to Palomar. Re-running the identical command with
`--location config/locations/hong_kong.toml` keeps the machinery of Steps 1–3
and changes only the inputs:

```text
ρ sin φ' = +0.377130   ρ cos φ' = +0.925643      (Step 1, Hong Kong)
t        = −1.868723 h after To                  (Step 2, converged in 4 iterations)
To + t   = 08h 07m 53s TD = 08h 06m 48s UT
Δ        = −0.1001 lunar radii                   (Step 3)
limb clearance = −0.8999
P        = 189.17°       h = −19.85°             (Step 3)
occulted? yes                                    (|Δ| ≤ 1)
```

Read the two runs side by side and the method becomes visible: Regulus *misses*
the Moon as seen from Palomar (`Δ = +1.15`, about 0.15 lunar radii — roughly two
arcminutes — north of the limb), while from Hong Kong the same star passes
*inside* the disc (`Δ = −0.1001`). The negative `Δ` is not an error: it is the
cross product telling the program that the star now passes south of the Moon's
centre. But `h = −19.85°` says the Moon is 20° below the Hong Kong horizon at
that instant, so the occultation, while geometrically real, is not visible from
there. This second run is a sanity check, not a validated prediction: the
elements are the book's Palomar example, reused for a site 11 000 km away.

## 5. What changed, file by file

| File | Status | What it is |
| --- | --- | --- |
| `src/occultation/cli.py` | rewritten | The command line: two subcommands, argument handling, text and JSON output, exit codes. Contains no astronomy. |
| `src/occultation/io/__init__.py` | new | Marks the new input/output package and states its boundary rule. |
| `src/occultation/io/elements_file.py` | new | Reads a JSON elements document into the domain objects; validates and names anything missing. |
| `src/occultation/io/location_file.py` | new | Reads an observer site from `.json` or `.toml`. This is the first code that actually reads `config/locations/hong_kong.toml`. |
| `src/occultation/reference/__init__.py` | new | Declares the reference-engine package and its one-way dependency rule. |
| `src/occultation/reference/skyfield_engine.py` | new | The reference engine's placeholder. It raises instead of returning a number. |
| `tests/fixtures/meeus_regulus_1999.json` | new | A JSON twin of the existing TOML fixture, carrying the book's printed values and the tolerances they justify. |
| `tests/test_cli.py` | extended | 4 tests before, 17 now: exit codes, both input styles, JSON shape, the mismatch path. |
| `tests/unit/test_elements_file.py` | new | 8 tests for the elements loader. |
| `tests/unit/test_location_file.py` | new | 7 tests for the site loader. |
| `tests/unit/test_reference_engine.py` | new | 3 tests that the reference engine refuses to answer. |
| `src/occultation/core/__init__.py`, `src/occultation/domain/__init__.py` | docstrings only | Each now states its boundary rule in the file where a future contributor will read it. |
| `.gitlab-ci.yml` | new | The GitLab pipeline, kept in step with the GitHub Actions workflow. |

Nothing under `src/occultation/core/` changed. The astronomy is untouched; this
change only makes it reachable.

## 6. The commands, and what each one is for

### `occultation local-circumstances`

```text
--elements FILE            JSON elements document
  or the inline equivalents:
--reference-hour-td HOUR   the tabular reference instant To
--star-declination-deg     the star's declination d0
--greenwich-hour-angle-deg H0 at To
--greenwich-hour-angle-rate-deg-per-hour  H1 (15.04107 for a star)
--shadow-x0 --shadow-x1 --shadow-x2       the Moon's X polynomial
--shadow-y0 --shadow-y1 --shadow-y2       the Moon's Y polynomial
--shadow-radius-earth-radii               the Moon's radius k (default 0.272495)

--location FILE            observer site (.json or .toml)
  or the inline equivalents:
--longitude-deg-east       east-positive longitude
--latitude-deg             north-positive latitude
--elevation-m              metres above sea level (default 0)

--delta-t-seconds SECONDS  required, always
--engine custom|skyfield|compare
--format text|json
--tolerance-hours HOURS    iteration stopping rule (default 1e-6)
--max-iterations N         safety limit (default 20)
```

Two deliberate design points:

- **The element source is swappable.** Today the elements come from a
  hand-transcribed file or from the command line. Later, when this project
  calculates its own Besselian elements, only the loader changes — the command
  line and the calculation stay as they are.
- **Delta T is required.** Delta T (the difference between uniform Dynamical
  Time and the uneven UT that civil clocks follow) is a number this code must
  be *told*, never guess. Making the option mandatory means a run can never
  silently use a wrong value.

### `occultation verify meeus-example-5`

Re-runs the book's example and compares every printed quantity. It reads both
the inputs and the expected values from the same fixture file that the
regression test uses, so the command and the test cannot disagree about what
the book printed. `--fixture FILE` points it at a different document, which is
how the mismatch path is tested.

## 7. Exit codes, and why they matter

| Code | Meaning |
| --- | --- |
| `0` | Success. For `verify`, every printed value matched. |
| `1` | The calculation ran, but a printed value did not match. |
| `2` | Bad usage or bad input: missing file, malformed JSON, a value the domain rejects, mutually exclusive options. |
| `3` | The reference engine was requested but is not available. |

Code `1` is the important one: it makes `verify` usable inside a script or a CI
job as a genuine check. Code `3` exists so that a request for the reference
engine fails honestly instead of quietly returning the custom engine's number
under a reference label.

## 8. The reference engine is deliberately empty

`src/occultation/reference/skyfield_engine.py` does not calculate anything. It
raises:

> the Skyfield reference engine is not implemented yet: milestone 1 needs a
> local JPL ephemeris (`data/manifest.json` currently declares zero datasets)

There is a reason to add a file that does nothing. The project's plan is to
have two independent engines — this repository's own textbook maths (the
"custom core") and a trusted third-party calculation (Skyfield with a local JPL
ephemeris, the "reference engine") — and to compare them. The rule that keeps
that honest is that the custom core must never import the reference package. By
creating the reference package now with a placeholder that refuses to answer,
the command line can already offer `--engine skyfield` and `--engine compare`,
the failure mode is visible and tested, and no future contributor can
accidentally wire the custom engine to the reference engine to make a number
appear.

Concretely:

```bash
# Fails with exit code 3 and an explanation. Does not print a result.
uv run occultation local-circumstances --engine skyfield ...

# Prints the custom result, plus a comparison block that says the reference
# engine is unavailable and why. Exit code 0.
uv run occultation local-circumstances --engine compare ...
```

The `compare` output contains:

```json
"comparison": {
  "reference_engine": "skyfield",
  "status": "unavailable",
  "reason": "the Skyfield reference engine is not implemented yet: ...",
  "note": "no difference is reported because the reference engine has not been implemented; the custom result above stands on its own"
}
```

That is the honest version of a comparison report. A comparison block that
reported a difference of zero because both sides were the same code would be
worse than no comparison block at all.

## 9. What the JSON output looks like

`local-circumstances --format json`:

```json
{
  "engine": "custom",
  "algorithm": "Meeus, Astronomical Tables, printed pp. 224-226",
  "inputs": {
    "elements": { "reference_hour_td": 10.0, "...": "..." },
    "observer": { "longitude_deg_east": 114.1743, "latitude_deg": 22.302, "elevation_m": 0.0 },
    "delta_t_seconds": 65.0
  },
  "derived": {
    "rho_sin_geocentric_latitude": 0.3771298489289325,
    "rho_cos_geocentric_latitude": 0.9256427709186403
  },
  "result": {
    "hours_after_reference": -1.8687231579299848,
    "dynamical_time_hour": 8.131276842070015,
    "universal_time_hour": 8.11322128651446,
    "separation_in_moon_radii": -0.10010830250005484,
    "position_angle_deg": 189.17396505694555,
    "altitude_deg": -19.847406925899747,
    "is_occultation": true,
    "iteration_count": 4,
    "limb_clearance_in_moon_radii": -0.8998916974999451
  }
}
```

Three things to notice:

- **Every key carries its unit and time scale**: `_deg_east`, `_deg`, `_m`,
  `_seconds`, `_hour`, `_in_moon_radii`, `_earth_radii`. A number whose unit
  you have to remember is a number that will eventually be used wrongly.
- **`inputs` echoes what was actually used**, including the observer and
  Delta T, so a stored output is self-describing.
- **`derived` shows the intermediate geocentric observer values** rather than
  hiding them, because that is where a coordinate-convention mistake would show
  up first.

## 10. How this was verified

Every claim above was produced by running the command, not by reading the code:

```text
$ uv run occultation verify meeus-example-5          -> exit 0, VERDICT: matches
$ uv run occultation verify meeus-example-5 --format json
                                                     -> verdict "match", 10 checks
$ uv run occultation local-circumstances --elements ... --location ... --delta-t-seconds 65
                                                     -> exit 0, 4 iterations
$ uv run occultation local-circumstances ... --engine compare
                                                     -> exit 0, comparison: unavailable
$ uv run occultation local-circumstances ... --engine skyfield
                                                     -> exit 3, no result printed
$ uv run pytest -q                                   -> 41 passed
$ uv run ruff check .                                -> All checks passed!
$ uv run ruff format --check .                       -> 26 files already formatted
$ uv run mypy src                                    -> Success: no issues found in 13 source files
$ uv run pytest --cov=occultation --cov-report=term-missing
                                                     -> TOTAL 90%
```

The tests that existed before this change still pass, unchanged in substance.
The JSON fixture was checked against the existing TOML fixture field by field —
`observer`, `event`, `elements` and `expected` are equal — and that equality is
itself a test, so a transcription slip in either file fails the suite.

## 11. What is *not* done (so nobody is misled)

- **No reference engine.** Skyfield is declared as a dependency but is not
  imported anywhere, and `data/manifest.json` still lists zero datasets. There
  is no ephemeris file in the repository. Milestone 1 is where that changes.
- **The elements are still supplied, not calculated.** This code does not yet
  compute the Moon's Besselian elements from an ephemeris; it starts from
  elements someone else produced. That is the whole point of the current
  milestone — the trigonometry is self-contained and checkable against the
  book — but it means the program cannot yet answer "will there be an
  occultation next month?" on its own.
- **The numbers are not observation-grade.** They reproduce a textbook example
  to the precision the textbook prints. Nothing here has been compared with
  real observations or with the Hong Kong Observatory's published almanac.
- **The packaged wheel does not contain the fixture.** `uv build` produces a
  wheel containing only the `occultation` package (checked with `unzip -l`), so
  `occultation verify meeus-example-5` works from a source checkout, where the
  default fixture path exists, but not from an installed wheel without
  `--fixture`. The default path is derived from the module location
  (`src/occultation/cli.py` → repository root → `tests/fixtures/`), which is
  correct for this repository and wrong for an installed distribution. Fixing
  it properly means packaging the fixture as package data, which changes the
  build configuration and therefore deserves its own change.
- **`data/manifest.json` is still empty** (open defect D10 in the handoff), and
  `.coverage` still sits in the working tree (open defect D9).

## 12. Questions worth asking

1. **Is the tolerance honest?** Each tolerance in the fixture is justified by
   how many digits the book prints, and the reasoning is written next to it.
   The weakest one is the altitude (±0.5 degrees, because Meeus prints whole
   degrees). If you want a tighter claim, the book has to be consulted for a
   finer printed value.
2. **Why keep two fixtures (TOML and JSON) for the same example?** The TOML one
   is what the existing regression test reads and is not worth churning. The
   JSON one is the canonical on-disk format for the new command line. A test
   asserts they agree, so the duplication is checked rather than trusted.
3. **Why does `--engine compare` exit 0 when the reference engine is
   missing?** Because the custom result is real and complete; only the
   comparison is missing, and the output says so explicitly. `--engine
   skyfield` is the mode that must fail, and it exits 3.
4. **Why four iterations when the book says two or three?** §4.3: the book's
   remark assumes a good hand-computed first guess, while this code starts from
   the prescribed `t = 0`. The count is asserted by the regression test, so the
   starting guess and the tolerance cannot drift unnoticed.
5. **What would you change first?** Two candidates, in order: package the
   fixture so the wheel is self-contained, and then start milestone 1 so the
   comparison block can carry a real difference.

## 13. Where to read more

| If you want... | Read |
| --- | --- |
| The astronomy, in pictures | `docs/explainer.html` |
| The textbook chapter, drawn scenario by scenario | `docs/meeus-pictures.html` |
| The code base, file by file | `docs/CODEBASE.md` |
| The formulas and their printed-page provenance | `docs/algorithms/meeus-star-local-circumstances.md` |
| The tools used here (Python, uv, pytest, Git, CI), from zero | `docs/tooling.html` |
| Constraints, defect history, roadmap | `docs/AGENT_HANDOFF.md` |
