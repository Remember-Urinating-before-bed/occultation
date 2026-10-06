"""Regression test for the four Jupiter events of Table III, 2019-2020.

This is the second planet-branch reference case, after Mars. Unlike Example 3
its rows carry **no printed results**: Meeus's Table III lists the elements
only. The ``expected`` block in the fixture is therefore *derived* from this
repository's own solver and is a regression lock on current behaviour, not an
independent oracle. The independent check for these rows is the NAOJ saved
result page (see ``data/validation/naoj/``).

Event 1 (2019 November 28) is a genuine occultation at Uccle and exercises the
immersion/emersion contacts. Events 2-4 miss the Moon, so they pin the
``is_occultation = false`` path and the absence of contacts.
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

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "meeus_jupiter_2019_2020.toml"

EVENTS = ("2019-11-28", "2019-12-26", "2020-01-23", "2020-02-19")


def _load_fixture() -> dict[str, Any]:
    with FIXTURE_PATH.open("rb") as fixture_file:
        return tomllib.load(fixture_file)


def _elements_for(fixture: dict[str, Any], date: str) -> StarOccultationElements:
    event = fixture["events"][date]
    elements_data = event["elements"]
    return StarOccultationElements(
        reference_hour_td=event["reference_hour_td"],
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


@pytest.mark.parametrize("date", EVENTS)
def test_jupiter_closest_approach_matches_the_regression_lock(date: str) -> None:
    fixture = _load_fixture()
    observer = ObserverLocation(**fixture["observer"])
    delta_t_seconds = fixture["event"]["delta_t_seconds"]
    tolerances = fixture["metadata"]["tolerances"]
    expected = fixture["events"][date]["expected"]
    elements = _elements_for(fixture, date)

    # The closest approach is the star-shaped answer and needs no contacts, so
    # it is available even when the body misses the Moon.
    closest = calculate_star_local_circumstances(
        elements=elements,
        observer=observer,
        delta_t_seconds=delta_t_seconds,
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


def test_the_2019_11_28_event_reports_contacts() -> None:
    """The one genuinely occulting row: contacts, with per-contact visibility."""
    fixture = _load_fixture()
    observer = ObserverLocation(**fixture["observer"])
    expected = fixture["events"]["2019-11-28"]["expected"]
    elements = _elements_for(fixture, "2019-11-28")

    result = calculate_planet_local_circumstances(
        elements=elements,
        observer=observer,
        delta_t_seconds=fixture["event"]["delta_t_seconds"],
    )

    for contact_name in ("immersion", "emersion"):
        contact = getattr(result, contact_name)
        contact_expected = expected[contact_name]
        assert contact.name == contact_name
        assert contact.hours_after_reference == pytest.approx(
            contact_expected["hours_after_reference"], abs=1e-6
        )
        assert contact.position_angle_deg == pytest.approx(
            contact_expected["position_angle_deg"], abs=0.01
        )
        assert contact.altitude_deg == pytest.approx(
            contact_expected["altitude_deg"], abs=0.01
        )
        assert contact.is_visible is contact_expected["is_visible"]


@pytest.mark.parametrize("date", ("2019-12-26", "2020-01-23", "2020-02-19"))
def test_a_non_occulting_row_has_no_contacts(date: str) -> None:
    """A miss must raise rather than invent contacts (Meeus printed pp. 226)."""
    fixture = _load_fixture()
    observer = ObserverLocation(**fixture["observer"])
    elements = _elements_for(fixture, date)

    with pytest.raises(ValueError, match="not occulted at closest approach"):
        calculate_planet_local_circumstances(
            elements=elements,
            observer=observer,
            delta_t_seconds=fixture["event"]["delta_t_seconds"],
        )
