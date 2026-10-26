"""Reference cases for the Mars (2031-2032) and Venus (2027-2028) rows.

Both fixtures come from a hand transcription by the project owner of their own
copy of Meeus's Table III, and both are structurally the same as the Jupiter and
Saturn cases: three events, one observer, a per-event ``expected`` block derived
from this repository's own solver. The differences that matter are in the
fixtures' headers and are repeated here because they decide what these tests can
and cannot claim:

- **``To`` is reconstructed, not transcribed.** Table III's ``To`` is an integer
  hour of Dynamical Time; the transcription did not carry it, so it was recovered
  by fitting the transcribed ``D0``/``H0``/``X0``/``Y0`` against the JPL
  ephemeris. Every row landed on an integer hour, which is the check that the
  reconstruction is the right kind of answer.
- **Two transcriptions were corrected, both forced by the ephemeris.** The Venus
  2027-08-02 ``Y1``/``Y2`` signs were flipped, and the Venus 2028-03-30 ``H0``
  and ``H1`` had been written into each other's places. The fixture header
  records exactly what changed and what the solver would have said otherwise.
- **The observer is Hong Kong**, not the site the printed elements were prepared
  for, so every one of the six events misses the Moon from Hong Kong. These
  fixtures therefore exercise the plumbing, the regression lock and the
  custom-vs-ephemeris agreement; they are not predictions for Hong Kong.

Nothing here checks an independent number: the ``expected`` block is derived from
the same solver, so it locks current behaviour. The independent statement about
these rows is ``test_skyfield_agreement.py``, which this module deliberately does
not duplicate.
"""

import tomllib
from pathlib import Path
from typing import Any

import pytest

from occultation.core.local_circumstances import (
    calculate_planet_local_circumstances,
    calculate_star_local_circumstances,
)
from occultation.domain.observer import ObserverLocation
from occultation.domain.occultation import (
    FundamentalPlanePolynomial,
    StarOccultationElements,
)

FIXTURES_DIR = Path(__file__).parents[1] / "fixtures"

#: (fixture stem, event keys). Kept explicit so a rename in one file is caught
#: by a missing-file error rather than by silently collecting nothing.
CASES = (
    (
        FIXTURES_DIR / "meeus_mars_2031_2032.toml",
        ("2031-07-28", "2032-03-14", "2032-04-12"),
    ),
    (
        FIXTURES_DIR / "meeus_venus_2027_2028.toml",
        ("2027-08-02", "2027-11-30", "2028-03-30"),
    ),
)

PARAMETERS = [
    pytest.param(fixture, date, id=f"{fixture.stem}:{date}")
    for fixture, dates in CASES
    for date in dates
]


def _load(fixture_path: Path) -> dict[str, Any]:
    with fixture_path.open("rb") as fixture_file:
        return tomllib.load(fixture_file)


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


@pytest.mark.parametrize(("fixture_path", "date"), PARAMETERS)
def test_the_closest_approach_matches_the_regression_lock(
    fixture_path: Path, date: str
) -> None:
    document = _load(fixture_path)
    observer = ObserverLocation(**document["observer"])
    tolerances = document["metadata"]["tolerances"]
    expected = document["events"][date]["expected"]

    closest = calculate_star_local_circumstances(
        elements=_elements(document, date),
        observer=observer,
        delta_t_seconds=document["event"]["delta_t_seconds"],
    )

    assert closest.hours_after_reference == pytest.approx(
        expected["hours_after_reference"], abs=tolerances["hours_after_reference"]
    )
    assert closest.separation_in_moon_radii == pytest.approx(
        expected["separation_in_moon_radii"],
        abs=tolerances["separation_in_moon_radii"],
    )
    assert closest.position_angle_deg == pytest.approx(
        expected["position_angle_deg"], abs=tolerances["position_angle_deg"]
    )
    assert closest.altitude_deg == pytest.approx(
        expected["altitude_deg"], abs=tolerances["altitude_deg"]
    )
    assert closest.is_occultation is expected["is_occultation"]
    assert closest.is_visible is expected["is_visible"]


@pytest.mark.parametrize(("fixture_path", "date"), PARAMETERS)
def test_a_missing_row_still_refuses_contacts(fixture_path: Path, date: str) -> None:
    """Every one of these six events misses the Moon from Hong Kong.

    A miss must raise rather than invent contacts, and the fixture has to agree
    with that. If a future correction ever turns one of these into a real Hong
    Kong occultation, this test fails and says so — which is the point.
    """
    document = _load(fixture_path)
    expected = document["events"][date]["expected"]

    assert expected["is_occultation"] is False
    assert expected["is_visible"] is False
    assert abs(expected["separation_in_moon_radii"]) > 1.0

    with pytest.raises(ValueError, match="not occulted at closest approach"):
        calculate_planet_local_circumstances(
            elements=_elements(document, date),
            observer=ObserverLocation(**document["observer"]),
            delta_t_seconds=document["event"]["delta_t_seconds"],
        )


def test_each_fixture_declares_its_body() -> None:
    """``metadata.body`` is what opts a fixture into the Skyfield comparison."""
    for fixture_path, _ in CASES:
        metadata = _load(fixture_path)["metadata"]
        assert metadata["body"] in ("Mars", "Venus")
        # The event key must be a calendar date, because the comparison builds
        # the reference epoch from it.
        assert metadata["event_keys_are"].startswith("universal-time dates")
