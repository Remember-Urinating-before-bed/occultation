# Meeus local circumstances for a lunar occultation of a star

Implementation: `src/occultation/core/local_circumstances.py`
(`calculate_star_local_circumstances`), with the observer conversion in
`src/occultation/core/observer_coordinates.py`.

Regression case: `tests/reference_cases/test_meeus_regulus.py` plus
`tests/fixtures/meeus_regulus_1999.toml`.

## 1. Source and provenance

- Jean Meeus, *Astronomical Tables* (Willmann-Bell), Occultations chapter.
- Section "Local Circumstances": printed pp. 224-226 = PDF pp. 6-8 of the
  working copy's scan. The page offset in that scan is exact:
  `printed page = PDF page + 218`.
- Worked example used as the regression target: **Example 5, occultation of
  Regulus, 1999 March 1, Palomar Mountain Observatory**, printed pp. 228-229
  (PDF pp. 10-11).
- Cross-check: the BASIC listing printed on p. 236 (PDF p. 18), lines 1400-1422.

Every constant below was read off the scan by eye. Per the project handoff,
OCR text is a search index into the scan, never a source of truth.

## 2. What the algorithm does

Besselian elements describe the Moon's shadow axis geometrically. For a given
observer we want the *local circumstances*: the instant of least topocentric
distance between star and Moon centre, how far apart they are, where on the
lunar disk the star would disappear, and whether the event is above the
horizon.

Coordinate frame: the **fundamental plane**, which passes through Earth's
centre perpendicular to the shadow axis. Distances are in Earth equatorial
radii. Time variable: `t`, hours of Dynamical Time (TD) measured from the
tabular reference instant `To`.

The procedure is iterative: guess `t`, compute the star-Moon relative position
`u, v` and velocity `u', v'` in the fundamental plane, jump to the instant of
closest approach along that straight-line velocity, and repeat until the jump
is negligible.

## 3. Inputs

```text
To   reference instant, Dynamical Time (hours)      - Table II column "To"
d0   star declination, degrees                      - Table II column "d"
H0   Greenwich hour angle at To, degrees            - Table II column "HO"
H1   hourly rate of H, deg/hour                     - Table II column "HI"
X0 X1 X2   Besselian x coefficients, Earth radii    - x = X0 + X1 t + X2 t^2
Y0 Y1 Y2   Besselian y coefficients, Earth radii    - y = Y0 + Y1 t + Y2 t^2
k    = 0.272495   Moon's relative radius (shadow radius) for a star
DT   = TD - UT, seconds of time
lambda  observer longitude, degrees (west-positive in the book)
phi     observer latitude, degrees, north-positive
z       observer height above sea level, metres
```

For a **star** three simplifications apply, all stated by Meeus:

- `H1 = +15.04107` deg/hour (printed p. 224) — the star's hour angle advances
  at the sidereal rate, so the star's own motion is negligible;
- `D1 = 0`, i.e. the declination is constant, so `d = d0`;
- `L = k = 0.272495`, i.e. the planetary aberration term `F` is unused;
- the observer coordinate `zeta` is "not needed" (printed p. 224).

Domain mapping onto the project model:

| Meeus | Code |
| --- | --- |
| `To` | `StarOccultationElements.reference_hour_td` |
| `d0` | `.star_declination_deg` |
| `H0` | `.greenwich_hour_angle_at_reference_deg` |
| `H1` | `.greenwich_hour_angle_rate_deg_per_hour` |
| `X0 X1 X2` | `.moon_shadow_x` (`FundamentalPlanePolynomial`) |
| `Y0 Y1 Y2` | `.moon_shadow_y` |
| `k` | `.moon_shadow_radius_earth_radii` |
| `lambda` (west +) | `ObserverLocation.longitude_deg_east` (east +) |
| `phi`, `z` | `ObserverLocation.latitude_deg`, `.elevation_m` |

## 4. Step 1 — geocentric coordinates of the observer (printed p. 224)

With the book's Earth model, `k' = 0.99664719` (= 1 - flattening) and
`a = 6378140 m`:

```text
tan w        = k' tan phi
rho sin phi' = k' sin w + (z / a) sin phi
rho cos phi' =      cos w + (z / a) cos phi
```

`rho sin phi'` and `rho cos phi'` are what the rest of the method needs; the
geocentric latitude `phi'` itself never appears on its own. Implemented by
`calculate_geocentric_observer`, which returns a
`GeocentricObserverCoordinates(rho_sin_geocentric_latitude,
rho_cos_geocentric_latitude)`.

## 5. Step 2 — one iteration (printed pp. 224-225)

For a trial `t` (start from `t = 0`, per printed p. 224: "take t = 0 as a
first approximation"):

```text
d   = d0                                    (D1 = 0 for a star)
H   = H0 + H1 t - lambda_west - DT / 239.345
x   = X0 + X1 t + X2 t^2            x' = X1 + 2 X2 t
y   = Y0 + Y1 t + Y2 t^2            y' = Y1 + 2 Y2 t
xi  = rho cos phi' sin H
eta = rho sin phi' cos d - rho cos phi' cos H sin d
xi'  = 0.01745329 H1 rho cos phi' cos H
eta' = 0.01745329 H1 xi sin d              (star case; see section 6)
u  = x - xi            v  = y - eta
u' = x' - xi'          v' = y' - eta'
n^2 = u'^2 + v'^2
tau = -(u u' + v v') / n^2                 # correction to t, in hours
```

Then `t <- t + tau` and repeat "until t no longer varies", the book's cutoff
being `|tau| < 0.000001` hours (printed p. 225), about 3.6 ms. The book adds
"two or three iterations will suffice"; see section 9 for what this
implementation actually needs.

`0.01745329` is pi/180 to eight decimals as printed — it converts the
degree-valued `H1` into radians so that `xi'` and `eta'` come out in Earth
radii per hour. In code it is `DEGREES_TO_RADIANS = math.pi / 180.0`, the same
number to double precision.

The instant of least topocentric distance is `To + t` in **TD**; subtract
`DT` to express it in **UT**.

## 6. The xi-vs-zeta transcription correction

The printed formula for `eta'` on p. 225 is damaged in the scan and in every
machine transcription of it, because Greek letters OCR to `«`, `§`, `¿`, `&`
or vanish. Read off the paper it is

```text
eta' = 0.01745329 (H1 xi sin d - zeta D1)      (star case: D1 = 0)
```

The disambiguating evidence is the author's own BASIC listing on printed
p. 236 (PDF p. 18), where the variables are ASCII:

```basic
1408 KO = C8 * SIN(H): E0 = S8 * C9 - C8 * S9 * COS(H)   ' xi, eta
1410 Z  = S8 * S9 + C8 * C9 * COS(H)                     ' zeta
1412 K1 = C8 * H1 * R * COS(H)                           ' xi'
1414 E1 = R * (KO * S9 * H1 - Z * D1)                    ' eta'
1416 U = X - KO: V = Y - EO: U1 = X4 - K1: V1 = Y4 - E1  ' u, v, u', v'
```

`KO` is `xi`, `Z` is `zeta`, `S9` is `sin d`, `E1` is `eta'`. So the
`H1 sin d` factor multiplies **xi**, and **zeta** multiplies the planet-only
`D1`. For a star, `D1 = 0` kills the zeta term entirely, which is exactly why
Meeus says `zeta` "is not needed" in the star case.

This matters numerically. With `zeta` wrongly in the first term, the Regulus
case converges to `t = 0.449736`, `v' = -0.18953`; with `xi` it converges to
`t = 0.455608`, `v' = -0.18556`, matching the printed results on p. 229. The
`xi` form is implemented and is what the regression test pins down.

## 7. Step 3 — derived quantities (printed pp. 225-226)

```text
tan P = u / v                          (4)  position angle of the star on the disk
L     = k = 0.272495                   for a star; for a planet L = k - zeta F / 1e6
Delta = (u v' - v u') / (n L)          (6)  least separation, lunar radii, north-positive
limb clearance = |Delta| - 1
sin h = sin d sin phi + cos d cos phi cos H   (8)  altitude at that instant
```

Sign conventions that are easy to get wrong:

- `P` needs a quadrant test: Meeus's rule is that `cos P` carries the sign
  **opposite** to `v`. The code uses `atan2(-u, -v) % 360`, which encodes that
  and reproduces `P = 24°.67` from `u = -0.13107`, `v = -0.28541`. `P` is
  measured from the North Point of the lunar disc towards East, South, West.
- `Delta`'s sign comes from the cross product `u v' - v u'`, **not** from `v`.
  Positive means the star passes north of the Moon's disc centre.
- `|Delta| > 1` means no occultation at that site.
- `H` uses `DT / 239.345` (seconds of DT per degree of hour angle), not
  `DT / 3600`.
- The book's `lambda` is **west-positive**; the project stores
  `longitude_deg_east`, so the `- lambda` term becomes `+ longitude_deg_east`.
- The event is not visible when `h` is negative.

Not implemented yet (later milestone): the exact immersion and emersion times,
which start from `t -/+ sqrt(1 - Delta^2) / n` (printed p. 226) and re-run the
iteration from that guess, separately for each contact.

## 8. Example 5 as the regression target (printed pp. 228-229)

Palomar Mountain Observatory, Regulus, 1999 March 1, `To = 10h` TD, `DT = 65s`:

```text
lambda = +116°.8640 west  ->  longitude_deg_east = -116.8640
phi    = +33°.3562        ->  latitude_deg       = 33.3562
z      = 1706 m           ->  elevation_m        = 1706.0
d = +11°.9694   H0 = 156°.6836   H1 = 15°.04107
X0 = +0.22151   X1 = +0.55549   X2 = -0.00000
Y0 = +0.19947   Y1 = -0.15258   Y2 = -0.00001
k  =  0.272495
```

Printed results versus this implementation:

```text
                     book        code
rho sin phi'      +0.546862    0.546862
rho cos phi'      +0.836338    0.836338
t                 +0.455608    0.455608
To + t (TD)       10h.455608   10.455608
     (UT)         10h26m15s    10.437552 h
Delta             +1.1526      1.152556
|Delta| - 1        0.1526      0.152556
u (last iter)     -0.13107    -0.131070
v (last iter)     -0.28541    -0.285410
u' (last iter)    +0.40408    +0.404082
v' (last iter)    -0.18556    -0.185558
H  (last iter)    +46°.4009    46.4009
n  (last iter)     0.444655    0.444655
P (formula 4)      24°.67      24.6654
h (formula 8)      +43°        42.6499
```

Because `Delta > 1`, Regulus is **not** occulted at Palomar; it passes about
0.15 lunar radii — roughly 2 arcminutes, the Moon's apparent radius being
about a quarter of a degree — north of the limb. The conjunction is visible
because `h` is positive.

The test tolerances follow the number of digits the book prints: `abs=5e-6` on
`t` and on the TD hour, `abs=2e-4` on the UT hour (the book rounds it to the
nearest second), `abs=5e-4` on `Delta` and on the limb clearance, `abs=0.02`
on `P`, and `abs=0.5` on `h` because the Regulus altitude is printed only to
the nearest whole degree. Never tighten a tolerance below what the source
supports.

## 9. Iteration count

The book's "two or three iterations will suffice" is a rule of thumb for hand
calculation from a good guess. Starting from Meeus's prescribed `t = 0` with
the `|tau| < 1e-6` h stopping rule, this implementation needs **four**
iterations for Example 5, with `tau` = +0.458369, -0.002717, -0.000043,
-0.000001. The regression test asserts that count as a diagnostic of the
chosen starting guess and tolerance: change either one and re-derive the
number, rather than tuning the guess to match a magic constant.

## 10. Reproduce

```bash
uv run pytest tests/reference_cases/test_meeus_regulus.py -q
uv run pytest tests/unit/test_observer_coordinates.py -q
```

The iteration trace behind sections 5, 9 and the table in section 8 can be
regenerated with a short scratch script that calls the private helpers
`_relative_motion_at` and `_closest_approach_correction` directly; keep such a
script outside the repository so the committed tests stay the only source of
assertions.



