"""Agreement between this repository's solver and an independent ephemeris.

This is the module that makes the reference engine earn its keep. Every other
test in ``tests/reference_cases`` compares the custom solver against numbers that
either the book printed or the solver itself produced; only here is the custom
answer checked against a calculation that shares no code and almost no data with
it. Meeus's Besselian elements go in one side; a JPL DE440s kernel goes in the
other; the two are expected to land on the same instant and the same separation.

Why this is a test and not a script
-----------------------------------

``scripts/verify_reference_data.py`` is a script because its oracle (a saved NAOJ
page) is external data a human had to fetch. The ephemeris is different: it is a
pinned, checksummed file recorded in ``data/manifest.json``, so the CI ``data``
job can fetch it deterministically and this comparison can be a hard gate. The
tolerances below are the point of the exercise — a regression in the custom
solver that moves any of these events would fail here even though the
"expected" blocks, being derived from the same solver, would happily agree with
it.

How to add a case
-----------------

A fixture with ``metadata.body`` set to a body name is picked up automatically;
nothing in this module needs editing. To add one:

1. Put the body in ``metadata.body`` and a note about the date convention in
   ``metadata.event_keys_are``.
2. Make sure each event key's first six characters are a calendar date, so the
   epoch can be derived from ``To`` and ``delta_t_seconds``.
3. Run ``uv run pytest tests/reference_cases/test_skyfield_agreement.py -v``.

When the ephemeris is absent the whole module skips, so a fresh clone with no
``data/external/`` still runs the rest of the suite. CI sets
``REQUIRE_EPHEMERIS=1`` to turn that skip into a failure, so the comparison
cannot quietly stop running.
"""

from __future__ import annotations

import datetime as dt
import math
import os
import tomllib
from pathlib import Path
from typing import Any

import pytest

from occultation.core.local_circumstances import calculate_star_local_circumstances
from occultation.domain.observer import ObserverLocation
from occultation.domain.occultation import (
    FundamentalPlanePolynomial,
    StarOccultationElements,
)
from occultation.reference import (
    DEFAULT_EPHEMERIS_PATH,
    BodyCircumstances,
    SkyfieldEngine,
)

FIXTURES_DIR = Path(__file__).parents[1] / "fixtures"

#: Fixtures carrying ``metadata.body``, i.e. those this module can check.
BODY_FIXTURES = (
    FIXTURES_DIR / "meeus_jupiter_2019_2020.toml",
    FIXTURES_DIR / "meeus_saturn_2024_2025.toml",
)

#: When set (CI does), a missing ephemeris fails rather than skips. Without it a
#: developer who has not fetched the kernel still gets a green local run.
REQUIRE_EPHEMERIS = os.environ.get("REQUIRE_EPHEMERIS", "").strip() not in ("", "0")

#: The one place the two engines are allowed to disagree, expressed as the
#: largest difference this test will accept. These are *not* "the last printed
#: digit" tolerances: see the module docstring of
#: :mod:`occultation.reference.skyfield_engine` for why the Moon's radius is
#: defined differently on the two sides.
#:
#: Each bound is roughly twice the worst agreement measured across the eight
#: events in the two fixtures on 2026-10-20, which is written here so that
#: loosening one is a visible decision rather than an escape hatch:
#:
#:     quantity                     worst measured    bound
#:     |Delta| difference            0.00199 radii     0.003
#:     closest-approach time        16.5 s            36 s
#:     position angle               0.25 deg          0.5 deg
#:     Moon altitude                1.18 deg          1.5 deg
#:
#: The time and altitude differences are largest for the events that miss the
#: Moon by several radii, where the separation curve is shallow and a small
#: geometry difference moves the minimum a long way.
MAX_SEPARATION_DIFFERENCE_MOON_RADII = 0.003
MAX_TIME_DIFFERENCE_HOURS = 36.0 / 3600.0
MAX_POSITION_ANGLE_DIFFERENCE_DEG = 0.5
MAX_ALTITUDE_DIFFERENCE_DEG = 1.5


def _engine_or_skip() -> SkyfieldEngine:
    engine = SkyfieldEngine()
    if not engine.is_available():
        if REQUIRE_EPHEMERIS:
            pytest.fail(
                f"REQUIRE_EPHEMERIS is set but {DEFAULT_EPHEMERIS_PATH} is not "
                "usable; fetch it with "
                "'uv run python scripts/fetch_reference_data.py fetch --download'"
            )
        pytest.skip(
            f"no reference ephemeris at {DEFAULT_EPHEMERIS_PATH}; fetch it with "
            "'uv run python scripts/fetch_reference_data.py fetch --download'"
        )
    return engine


def _fixture_cases() -> list[tuple[Path, str]]:
    """Every (fixture, event key) pair in a body-tagged fixture."""
    cases: list[tuple[Path, str]] = []
    for path in BODY_FIXTURES:
        with path.open("rb") as fixture_file:
            document = tomllib.load(fixture_file)
        if "body" not in document.get("metadata", {}):
            continue
        cases.extend((path, date) for date in document["events"])
    return cases


CASES = _fixture_cases()
CASE_IDS = [f"{path.stem}:{date}" for path, date in CASES]


def _elements(document: dict[str, Any], date: str) -> StarOccultationElements:
    event = document["events"][date]
    data = event["elements"]
    return StarOccultationElements(
        reference_hour_td=event["reference_hour_td"],
        star_declination_deg=data["star_declination_deg"],
        greenwich_hour_angle_at_reference_deg=(
            data["greenwich_hour_angle_at_reference_deg"]
        ),
        greenwich_hour_angle_rate_deg_per_hour=(
            data["greenwich_hour_angle_rate_deg_per_hour"]
        ),
        declination_rate_deg_per_hour=data["declination_rate_deg_per_hour"],
        aberration_term=data["aberration_term"],
        moon_shadow_x=FundamentalPlanePolynomial(**data["moon_shadow_x"]),
        moon_shadow_y=FundamentalPlanePolynomial(**data["moon_shadow_y"]),
        moon_shadow_radius_earth_radii=data["moon_shadow_radius_earth_radii"],
    )


def _epoch_ut(document: dict[str, Any], date: str) -> dt.datetime:
    """The UT instant of the custom solver's closest approach, as a seed.

    ``To`` is in Dynamical Time and ``delta_t_seconds`` is TD minus UT, so the
    instant in UT is ``To + t - Delta T``. The reference engine is given this as
    a seed and allowed to move from it, but seeding it here rather than at
    midnight keeps its search window unambiguous around the event.
    """
    event = document["events"][date]
    delta_t_seconds = document["event"]["delta_t_seconds"]
    return dt.datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=dt.UTC) + (
        dt.timedelta(hours=event["reference_hour_td"])
        - dt.timedelta(seconds=delta_t_seconds)
    )


def _custom_minimum_hours(document: dict[str, Any], date: str) -> float:
    """The custom solver's ``t``, in hours after ``To``."""
    calculated = calculate_star_local_circumstances(
        elements=_elements(document, date),
        observer=ObserverLocation(**document["observer"]),
        delta_t_seconds=document["event"]["delta_t_seconds"],
    )
    return calculated.hours_after_reference


def _reference_at_custom_minimum(
    engine: SkyfieldEngine,
    document: dict[str, Any],
    date: str,
    custom_hours: float,
) -> BodyCircumstances:
    """Ask the reference engine about the exact instant the custom solver chose.

    Sampling at the custom solver's own instant, rather than comparing each
    engine's minimum with the other's, separates two questions that a bare
    "do the minima agree" check would tangle: whether the two engines compute
    the same geometry at a given instant, and whether they find the same instant.
    Both matter, so the caller checks both.
    """
    instant = _epoch_ut(document, date) + dt.timedelta(hours=custom_hours)
    return engine.body_local_circumstances(
        document["metadata"]["body"],
        instant,
        ObserverLocation(**document["observer"]),
        # A few seconds wide: this call is a measurement at an instant, not a
        # search, and a wide window would let the referee drift off the instant
        # it is supposed to be reporting on.
        search_half_window_hours=0.01,
        coarse_step_seconds=1.0,
    )


@pytest.mark.skipif(not CASES, reason="no body-tagged fixture to compare")
@pytest.mark.parametrize(("fixture_path", "date"), CASES, ids=CASE_IDS)
def test_the_two_engines_agree_on_the_closest_approach(
    fixture_path: Path, date: str
) -> None:
    engine = _engine_or_skip()
    with fixture_path.open("rb") as fixture_file:
        document = tomllib.load(fixture_file)

    custom = calculate_star_local_circumstances(
        elements=_elements(document, date),
        observer=ObserverLocation(**document["observer"]),
        delta_t_seconds=document["event"]["delta_t_seconds"],
    )

    # Seed the reference search with the custom answer only as a starting point;
    # the minimum it finds is its own.
    seed = _epoch_ut(document, date) + dt.timedelta(hours=custom.hours_after_reference)
    reference = engine.body_local_circumstances(
        document["metadata"]["body"],
        seed,
        ObserverLocation(**document["observer"]),
    )

    separation_difference = abs(reference.separation_in_moon_radii) - abs(
        custom.separation_in_moon_radii
    )
    time_difference_hours = (reference.universal_time - seed).total_seconds() / 3600.0
    position_angle_difference = (
        reference.position_angle_deg - custom.position_angle_deg + 180.0
    ) % 360.0 - 180.0

    assert abs(separation_difference) <= MAX_SEPARATION_DIFFERENCE_MOON_RADII, (
        f"{path_label(fixture_path, date)}: separation {custom.separation_in_moon_radii:+.6f} "
        f"vs {reference.separation_in_moon_radii:+.6f} Moon radii "
        f"(difference {separation_difference:+.6f})"
    )
    assert abs(time_difference_hours) <= MAX_TIME_DIFFERENCE_HOURS, (
        f"{path_label(fixture_path, date)}: closest approach differs by "
        f"{time_difference_hours * 3600.0:+.1f} s"
    )
    assert abs(position_angle_difference) <= MAX_POSITION_ANGLE_DIFFERENCE_DEG, (
        f"{path_label(fixture_path, date)}: position angle differs by "
        f"{position_angle_difference:+.3f} deg"
    )
    assert (
        abs(reference.moon_altitude_deg - custom.altitude_deg)
        <= MAX_ALTITUDE_DIFFERENCE_DEG
    ), (
        f"{path_label(fixture_path, date)}: altitude differs by "
        f"{reference.moon_altitude_deg - custom.altitude_deg:+.3f} deg"
    )


@pytest.mark.skipif(not CASES, reason="no body-tagged fixture to compare")
@pytest.mark.parametrize(("fixture_path", "date"), CASES, ids=CASE_IDS)
def test_the_two_engines_agree_on_whether_the_body_is_occulted(
    fixture_path: Path, date: str
) -> None:
    """The visibility verdict must survive the change of oracle.

    Agreement to a thousandth of a Moon radius says nothing when the separation
    is 3 Moon radii; the verdict is what the saved NAOJ snapshot checks, and the
    two engines must reach it independently.
    """
    engine = _engine_or_skip()
    with fixture_path.open("rb") as fixture_file:
        document = tomllib.load(fixture_file)

    custom = calculate_star_local_circumstances(
        elements=_elements(document, date),
        observer=ObserverLocation(**document["observer"]),
        delta_t_seconds=document["event"]["delta_t_seconds"],
    )
    reference = _reference_at_custom_minimum(
        engine, document, date, custom.hours_after_reference
    )

    assert bool(custom.is_occultation) is bool(reference.is_occultation), (
        f"{path_label(fixture_path, date)}: custom says "
        f"is_occultation={custom.is_occultation} (Delta "
        f"{custom.separation_in_moon_radii:+.6f}) but the ephemeris says "
        f"{reference.is_occultation} (Delta "
        f"{reference.separation_in_moon_radii:+.6f})"
    )
    assert bool(custom.is_visible) is bool(reference.is_visible), (
        f"{path_label(fixture_path, date)}: custom says "
        f"is_visible={custom.is_visible} (altitude {custom.altitude_deg:+.3f}) "
        f"but the ephemeris says {reference.is_visible} (Moon altitude "
        f"{reference.moon_altitude_deg:+.3f})"
    )


def test_the_two_moon_radius_conventions_differ_by_a_known_amount() -> None:
    """State the one modelling difference this project accepts on purpose.

    Meeus's ``k`` is the Moon's radius as a fixed ratio to the Earth's
    equatorial radius; the reference engine uses the true radius at the Moon's
    true distance. The two differ by a known, small amount, and this test states
    that amount so a silent change to either convention shows up as a failure
    rather than being absorbed into a loosened tolerance elsewhere.
    """
    engine = _engine_or_skip()
    fixture_path = BODY_FIXTURES[0]
    with fixture_path.open("rb") as fixture_file:
        document = tomllib.load(fixture_file)
    date = next(iter(document["events"]))
    custom = calculate_star_local_circumstances(
        elements=_elements(document, date),
        observer=ObserverLocation(**document["observer"]),
        delta_t_seconds=document["event"]["delta_t_seconds"],
    )
    reference = _reference_at_custom_minimum(
        engine, document, date, custom.hours_after_reference
    )

    # What the custom code's k implies as an angular radius at this distance,
    # against what the reference engine actually measured.
    earth_equatorial_radius_km = 6378.137
    implied_custom_radius_deg = math.degrees(
        document["events"][date]["elements"]["moon_shadow_radius_earth_radii"]
        * earth_equatorial_radius_km
        / reference.moon_distance_km
    )
    difference_arcsec = (
        reference.moon_angular_radius_deg - implied_custom_radius_deg
    ) * 3600.0

    assert abs(difference_arcsec) < 15.0, (
        "the Moon-radius conventions should differ by well under 15 arcsec "
        "(about 0.4% of the Moon's radius); they differ by "
        f"{difference_arcsec:+.2f} arcsec"
    )


def path_label(fixture_path: Path, date: str) -> str:
    return f"{fixture_path.name}:{date}"
