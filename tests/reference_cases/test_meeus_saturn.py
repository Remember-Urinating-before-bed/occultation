"""Reference case for Meeus Table III Saturn events, 2024-2025 (scaffold).

Structure mirrors :mod:`tests.reference_cases.test_meeus_jupiter`: four
consecutive Saturn rows, one observer site, and a per-event ``expected`` block.
Unlike Examples 3 and 5 these rows carry no printed results, so the ``expected``
block is derived from this repository's own solver -- a regression lock on
current behaviour, not an independent oracle. The independent statement about
these events is the saved NAOJ snapshot under ``data/validation/naoj/``, read by
``scripts/verify_reference_data.py --dataset saturn``.

WHILE ``metadata.scaffold`` IS TRUE the whole module is skipped: the fixture's
numbers are placeholders, so there is nothing yet to compare. Fill the fixture
in and set ``metadata.scaffold = false`` to activate these tests.
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

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "meeus_saturn_2024_2025.toml"

EVENTS = ("2024-11-11", "2024-12-08", "2025-01-04", "2025-02-01")


def _load_fixture() -> dict[str, Any]:
    with FIXTURE_PATH.open("rb") as fixture_file:
        return tomllib.load(fixture_file)


SCAFFOLD = bool(_load_fixture()["metadata"].get("scaffold", False))

pytestmark = pytest.mark.skipif(
    SCAFFOLD,
    reason=(
        "Saturn fixture is a scaffold; fill in the Table III elements and set "
        "metadata.scaffold = false to activate these tests"
    ),
)


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
def test_saturn_closest_approach_matches_the_regression_lock(date: str) -> None:
    fixture = _load_fixture()
    observer = ObserverLocation(**fixture["observer"])
    delta_t_seconds = fixture["event"]["delta_t_seconds"]
    tolerances = fixture["metadata"]["tolerances"]
    expected = fixture["events"][date]["expected"]
    elements = _elements_for(fixture, date)

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


@pytest.mark.parametrize("date", EVENTS)
def test_only_an_occulting_row_reports_contacts(date: str) -> None:
    """A visible row yields contacts; a miss must raise, never invent them."""
    fixture = _load_fixture()
    observer = ObserverLocation(**fixture["observer"])
    expected = fixture["events"][date]["expected"]
    elements = _elements_for(fixture, date)
    delta_t_seconds = fixture["event"]["delta_t_seconds"]

    if not expected["is_occultation"]:
        with pytest.raises(ValueError, match="not occulted at closest approach"):
            calculate_planet_local_circumstances(
                elements=elements,
                observer=observer,
                delta_t_seconds=delta_t_seconds,
            )
        return

    result = calculate_planet_local_circumstances(
        elements=elements,
        observer=observer,
        delta_t_seconds=delta_t_seconds,
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
