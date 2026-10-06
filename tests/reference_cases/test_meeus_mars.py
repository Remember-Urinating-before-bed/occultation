"""Regression test for Meeus Example 3, Mars on 1997 November 12.

This is the planet-branch reference case. Unlike the Regulus star fixture it
exercises a non-zero declination rate ``D1``, the aberration term ``F`` that
turns the Moon's shadow into a cone, and both immersion and emersion contacts.
"""

import tomllib
from pathlib import Path
from typing import Any

import pytest

from occultation.core.local_circumstances import (
    calculate_planet_local_circumstances,
)
from occultation.domain.observer import ObserverLocation
from occultation.domain.occultation import (
    FundamentalPlanePolynomial,
    StarOccultationElements,
)

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "meeus_mars_1997.toml"


def _load_fixture() -> dict[str, Any]:
    with FIXTURE_PATH.open("rb") as fixture_file:
        return tomllib.load(fixture_file)


def test_mars_local_circumstances_match_meeus() -> None:
    fixture = _load_fixture()
    observer = ObserverLocation(**fixture["observer"])
    event_data = fixture["event"]
    elements_data = fixture["elements"]
    expected = fixture["expected"]

    elements = StarOccultationElements(
        reference_hour_td=event_data["reference_hour_td"],
        star_declination_deg=elements_data["star_declination_deg"],
        greenwich_hour_angle_at_reference_deg=(
            elements_data["greenwich_hour_angle_at_reference_deg"]
        ),
        greenwich_hour_angle_rate_deg_per_hour=(
            elements_data["greenwich_hour_angle_rate_deg_per_hour"]
        ),
        declination_rate_deg_per_hour=elements_data["declination_rate_deg_per_hour"],
        aberration_term=elements_data["aberration_term"],
        moon_shadow_x=FundamentalPlanePolynomial(**elements_data["moon_shadow_x"]),
        moon_shadow_y=FundamentalPlanePolynomial(**elements_data["moon_shadow_y"]),
        moon_shadow_radius_earth_radii=(
            elements_data["moon_shadow_radius_earth_radii"]
        ),
    )

    result = calculate_planet_local_circumstances(
        elements=elements,
        observer=observer,
        delta_t_seconds=event_data["delta_t_seconds"],
    )
    closest = result.closest_approach

    # Published inputs and results are rounded, so tolerances follow the
    # precision displayed in the book rather than demanding exact equality.
    assert closest.hours_after_reference == pytest.approx(
        expected["hours_after_reference"], abs=5e-6
    )
    assert closest.separation_in_moon_radii == pytest.approx(
        expected["separation_in_moon_radii"], abs=5e-4
    )
    assert closest.position_angle_deg == pytest.approx(
        expected["position_angle_deg"], abs=0.02
    )
    # Meeus prints the Mars altitude only to the nearest tenth of a degree.
    assert closest.altitude_deg == pytest.approx(expected["altitude_deg"], abs=0.5)
    assert closest.is_occultation is expected["is_occultation"]
    assert closest.is_visible is expected["is_visible"]

    for contact_name in ("immersion", "emersion"):
        contact = getattr(result, contact_name)
        contact_expected = expected[contact_name]
        assert contact.name == contact_name
        assert contact.hours_after_reference == pytest.approx(
            contact_expected["hours_after_reference"], abs=5e-6
        )
        assert contact.position_angle_deg == pytest.approx(
            contact_expected["position_angle_deg"], abs=0.02
        )
        assert contact.altitude_deg == pytest.approx(
            contact_expected["altitude_deg"], abs=0.5
        )
        # Immersion happens high in the sky (h = +66 deg); emersion happens
        # below the horizon (h = -15 deg), so only the immersion is visible.
        # This pins the per-contact occulted-AND-above-horizon definition.
        assert contact.is_visible is contact_expected["is_visible"]
