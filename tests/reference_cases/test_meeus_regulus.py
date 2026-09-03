"""Regression test for Meeus Example 5, Regulus on 1999 March 1."""

import tomllib
from pathlib import Path
from typing import Any

import pytest

from occultation.core.local_circumstances import (
    calculate_star_local_circumstances,
)
from occultation.domain.observer import ObserverLocation
from occultation.domain.occultation import (
    FundamentalPlanePolynomial,
    StarOccultationElements,
)

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "meeus_regulus_1999.toml"


def _load_fixture() -> dict[str, Any]:
    with FIXTURE_PATH.open("rb") as fixture_file:
        return tomllib.load(fixture_file)


def test_regulus_local_circumstances_match_meeus() -> None:
    fixture = _load_fixture()
    observer_data = fixture["observer"]
    event_data = fixture["event"]
    elements_data = fixture["elements"]
    expected = fixture["expected"]

    observer = ObserverLocation(**observer_data)
    elements = StarOccultationElements(
        reference_hour_td=event_data["reference_hour_td"],
        star_declination_deg=elements_data["star_declination_deg"],
        greenwich_hour_angle_at_reference_deg=(
            elements_data["greenwich_hour_angle_at_reference_deg"]
        ),
        greenwich_hour_angle_rate_deg_per_hour=(
            elements_data["greenwich_hour_angle_rate_deg_per_hour"]
        ),
        moon_shadow_x=FundamentalPlanePolynomial(**elements_data["moon_shadow_x"]),
        moon_shadow_y=FundamentalPlanePolynomial(**elements_data["moon_shadow_y"]),
        moon_shadow_radius_earth_radii=(
            elements_data["moon_shadow_radius_earth_radii"]
        ),
    )

    result = calculate_star_local_circumstances(
        elements=elements,
        observer=observer,
        delta_t_seconds=event_data["delta_t_seconds"],
    )

    # Published inputs and results are rounded, so tolerances follow the
    # precision displayed in the book rather than demanding exact equality.
    assert result.hours_after_reference == pytest.approx(
        expected["hours_after_reference"],
        abs=5e-6,
    )
    assert result.dynamical_time_hour == pytest.approx(
        expected["dynamical_time_hour"],
        abs=5e-6,
    )
    assert result.universal_time_hour == pytest.approx(
        expected["universal_time_hour"],
        abs=2e-4,
    )
    assert result.separation_in_moon_radii == pytest.approx(
        expected["separation_in_moon_radii"],
        abs=5e-4,
    )
    assert result.limb_clearance_in_moon_radii == pytest.approx(
        expected["limb_clearance_in_moon_radii"],
        abs=5e-4,
    )
    assert result.position_angle_deg == pytest.approx(
        expected["position_angle_deg"],
        abs=0.02,
    )
    # Meeus prints the Regulus altitude only to the nearest whole degree.
    assert result.altitude_deg == pytest.approx(
        expected["altitude_deg"],
        abs=0.5,
    )
    assert result.is_occultation is expected["is_occultation"]
    # Not a book value: the number of tau iterations the solver performs when
    # it starts from Meeus's first approximation t = 0 (printed p. 224) and
    # stops once |tau| < 1e-6 h. Re-derive it whenever the starting guess or
    # the tolerance changes.
    assert result.iteration_count == 4
