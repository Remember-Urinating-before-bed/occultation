# Meeus local circumstances for a lunar occultation of a planet

Implementation: `src/occultation/core/local_circumstances.py`
(`calculate_planet_local_circumstances`, plus the planet terms inside
`_relative_motion_at` and `_effective_shadow_radius`).

Regression case: `tests/reference_cases/test_meeus_mars.py` plus
`tests/fixtures/meeus_mars_1997.toml`.

This is the companion to
[`meeus-star-local-circumstances.md`](meeus-star-local-circumstances.md). Read
that one first: everything here is the same solver with two extra terms and one
extra output.

## 1. Source and provenance

- Jean Meeus, *Astronomical Tables* (Willmann-Bell), Occultations chapter.
- Section "Local Circumstances": printed pp. 224-226 = PDF pp. 6-8 of the
  working copy's scan. The page offset in that scan is exact:
  `printed page = PDF page + 218`.
- Worked example used as the regression target: **Example 3, occultation of
  Mars, 1997 November 12, Uccle**, restated on printed pp. 224-226.
- The planet-only inputs come from **Table III** of the same chapter.

Every constant below was read off the scan by eye. Per the project handoff,
OCR text is a search index into the scan, never a source of truth.

## 2. What changes for a planet

A star is a point at infinity. A planet is not, and that shows up in exactly
two places:

1. **Its declination is not constant.** Over the few hours of the event the
   planet moves along its orbit, so the declination is a linear function of
   time, `d = D0 + D1 t`, where `D1` is the hourly rate (Table III). For a star
   `D1 = 0`.
2. **The Moon's shadow is a cone, not a cylinder.** Because the planet is at a
   finite distance, the Moon's shadow narrows as you move away from the Moon
   along the shadow axis. Meeus models this with an aberration term `F`
   (Table III) that shrinks the effective shadow radius from `k` to
   `L = k − ζ F / 1e6`, where `ζ` is the observer's coordinate along the shadow
   axis. For a star `F = 0` and `L = k`.

Both terms default to `0.0` in `StarOccultationElements`, so a star element set
is exactly the planet element set with `D1 = F = 0`, and the star regression
(Regulus) is the `D1 = F = 0` special case of this code.

A planet occultation also has two **contacts** — the moment the planet's disk
first touches the Moon's limb (immersion) and the moment it leaves (emersion) —
whereas the star case reports only the instant of closest approach.


## 3. Inputs

All of the star inputs, plus:

```text
D1   hourly rate of the planet's declination, deg/hour   - Table III column "D1"
F    planetary aberration term                           - Table III column "F"
k    Moon's relative radius for this event               - Table III column "k"
```

`k` for a planet is slightly larger than the star value `0.272495` because the
shadow is a cone: the tabulated `k` is the value at the observer's `ζ`. In the
domain model `k` lives in
`StarOccultationElements.moon_shadow_radius_earth_radii`, `D1` in
`.declination_rate_deg_per_hour`, and `F` in `.aberration_term`.

## 4. The two extra formulas

### 4.1 Declination rate `D1` (printed p. 222, p. 225)

```text
d = D0 + D1 t
```

This replaces the star's constant `d = d0`. The rate enters the topocentric
`η'` through the `ζ D1` term (see §4.2), so it is not merely a cosmetic change
to `d`; it moves the relative velocity of the planet against the Moon.

### 4.2 The `ζ` term in `η'` (printed p. 225; BASIC line 1414)

The star document explains that the printed `η'` formula is

```text
eta' = 0.01745329 (H1 xi sin d - zeta D1)
```

For a star `D1 = 0`, so the `zeta D1` term vanishes and `zeta` "is not needed".
For a planet it is live: `zeta` is the observer coordinate along the shadow
axis,

```text
zeta = rho sin phi' sin d + rho cos phi' cos H cos d
```

and the code computes it in `_relative_motion_at` (`observer_z`). The
`- zeta D1` term is what makes the planet's own declination drift matter.

### 4.3 The cone-shaped shadow `L = k − ζ F / 1e6` (printed p. 226)

```text
L = k - zeta F / 1e6
```

`F` is tabulated as `sin(f) × 1e6`, hence the `1e6` divisor; in code it is
`ABERRATION_TERM_SCALE = 1_000_000.0`. `L` replaces `k` everywhere the shadow
radius is used, in particular in the least-separation formula

```text
Delta = (u v' - v u') / (n L)          (6)
```

`_effective_shadow_radius` implements this and short-circuits to `k` when

## 5. Contacts (printed p. 226)

The approximate contact instants start from the closest-approach instant `t`
and the half-duration `sqrt(1 - Delta^2) / n`:

```text
immersion  t_i = t - sqrt(1 - Delta^2) / n
emersion   t_e = t + sqrt(1 - Delta^2) / n
```

Each is then refined by re-running the iteration from that guess, re-evaluating
`d` and `L` at every trial instant — which is precisely what makes a planet
occultation more than the star case. `calculate_planet_local_circumstances`
computes the closest approach first (and refuses to proceed if `|Delta| > 1`,
because then there is nothing to occult), then solves each contact in
`_solve_contact`.

Each contact reports its own position angle, altitude, and `is_visible`
(`altitude_deg > 0`). In Example 3 the immersion happens at `h = +66°` (visible)
and the emersion at `h = −15°` (below the horizon), so the two contacts differ
in visibility — which is why visibility is a per-contact property, not one flag
for the whole event.

## 6. The `is_visible` flag

`is_visible` is defined identically for the star and the planet closest
approach:

```text
is_visible = is_occultation and altitude_deg > HORIZON_ALTITUDE_DEG
```

with `HORIZON_ALTITUDE_DEG = 0.0` (geometric horizon). The body must be *both*
hidden by the Moon's disk *and* above the horizon. Atmospheric refraction
(about 0.57° at the horizon) is deliberately not applied yet; it belongs with
the shared coordinate primitives of a later milestone, and the constant exists
so that decision is recorded in one place rather than scattered as `> 0.0`.

## 7. Example 3 as the regression target (printed pp. 224-226)

Uccle, Mars, 1997 November 12, `To = 4h` TD, `DT = 72s`:

```text
lambda = +2°.3372 west   ->  longitude_deg_east = -2.3372
phi    = +48°.8364       ->  latitude_deg       = 48.8364
z      = 67 m            ->  elevation_m        = 67.0
d0 = +24°.99235   H0 = 62°.22691   H1 = 15°.06158
D1 = -0.00057     F  = 21.25       k  = 0.273828
X0 = -0.248914   X1 = +0.568162   X2 = -0.000001
Y0 = +0.553450   Y1 = +0.101246   Y2 = +0.000062
```

Printed results versus this implementation:

```text
                     book        code
rho sin phi'      +0.749224    0.749224
rho cos phi'      +0.659470    0.659470
t                 +1.585130    1.585130
Delta             -0.244054   -0.244054
P (formula 4)      177.01 deg   177.01
h (formula 8)      +22.7 deg     22.70
immersion t       -3.868491    -3.868491
emersion  t       +8.818967     8.818967
```

The test tolerances follow the number of digits the book prints: `abs=5e-6` on
`t`, `abs=5e-4` on `Delta`, `abs=0.02` on `P`, and `abs=0.5` on `h` (Meeus
prints the altitude only to the nearest tenth of a degree). **Never tighten a
tolerance below what the source supports.**

## 8. Reproduce

```bash
uv run pytest tests/reference_cases/test_meeus_mars.py -q
uv run occultation local-circumstances \
  --elements tests/fixtures/meeus_mars_1997.json \
  --location config/locations/hong_kong.toml \
  --delta-t-seconds 72 --body planet
```

The second command reuses the book's Uccle elements for a Hong Kong observer.
That is a sanity check of the plumbing, not a validated prediction: the elements
belong to a site 11 000 km away.

## 9. The Jupiter rows of Table III (2019-2020) as a second case

`tests/reference_cases/test_meeus_jupiter.py` plus the twin fixtures
`tests/fixtures/meeus_jupiter_2019_2020.{toml,json}` add a second planet case,
four consecutive rows of **Table III** of the Occultations chapter:

```text
2019 Nov 28   To = 11h   D0 = -23.28992   D1 = -0.00012   F = 1.9    k = 0.272608
2019 Dec 26   To =  8h   D0 = -23.23011   D1 = +0.00033   F = 1.87   k = 0.272608
2020 Jan 23   To =  3h   D0 = -22.86588   D1 = +0.00075   F = 1.9    k = 0.272611
2020 Feb 19   To = 20h   D0 = -22.26838   D1 = +0.00100   F = 1.97   k = 0.272617
```

The observer is Uccle, the same site as Example 3
(`longitude_deg_east = -2.3372`, `latitude_deg = 48.8364`, `elevation_m = 67`),
and `DT = 69 s` (the value for 2019-2020; Example 3's 1997 event used 72 s).

**These rows carry no printed results.** Table III lists the elements only, so
the `expected` block in the fixture is *derived* from this repository's own
solver and is a **regression lock on current behaviour, not an independent
oracle**. The independent check for these rows is the NAOJ saved result page
under `data/validation/naoj/` (see `data/README.md`), which records whether the
event was visible from a reference site. Never cite the derived block as if
Meeus had printed it, and never tighten its tolerances as if a printed digit
supported them.

At Uccle only the first row is a genuine occultation; the other three miss the
Moon, so they pin the `is_occultation = false` path and the
`calculate_planet_local_circumstances` refusal:

```text
                     Delta     occulted?   contacts
2019-11-28          +0.0715      yes       immersion / emersion
2019-12-26          +1.6950      no        none (|Delta| > 1)
2020-01-23          +3.2480      no        none (|Delta| > 1)
2020-02-19          +5.3095      no        none (|Delta| > 1)
```

## 10. Reproduce the Jupiter case

```bash
uv run pytest tests/reference_cases/test_meeus_jupiter.py -q
uv run occultation local-circumstances \
  --star-declination-deg -23.28992 --reference-hour-td 11.0 \
  --greenwich-hour-angle-deg 323.09492 \
  --greenwich-hour-angle-rate-deg-per-hour 15.03134 \
  --shadow-x0 0.092336 --shadow-x1 0.571548 --shadow-x2 -0.000024 \
  --shadow-y0 0.749714 --shadow-y1 -0.055842 --shadow-y2 0.000003 \
  --shadow-radius-earth-radii 0.272608 \
  --declination-rate-deg-per-hour -0.00012 --aberration-term 1.9 \
  --longitude-deg-east -2.3372 --latitude-deg 48.8364 --elevation-m 67 \
  --delta-t-seconds 69 --body planet
```

## 11. CLI guards added with this case (FOR_REVIEW 13.3, 13.4)

- `--body` must agree with the numbers. `--body planet` with `D1 = F = 0`, or
  `--body star` with a non-zero `D1`/`F`, is now a usage error (exit 2) rather
  than a mislabelled run. The check lives in
  `occultation.cli._validate_body_against_elements`.
- A non-occulting `--body planet` run is no longer silent: the JSON gains a
  `note` field and the text output a `note:` line saying contacts were not
  computed because the body is not occulted at closest approach.
## 9. Still to come

The planet branch and `is_visible` are proved against Meeus Example 3. A Hong
Kong visibility sweep over the eight planets (Jupiter first) still needs a
hand-transcribed Table III row per event, cross-checked **by hand** against
NAOJ; that is the next increment, and it is recorded as not-done in
`docs/CODEBASE.md` §8. The NAOJ service is an interactive form whose output is a
rendered figure, not a data table, so the check cannot be scripted — see
`docs/FOR_REVIEW.md` §13.10.

`F == 0.0`, so the star path is bit-for-bit unchanged.
