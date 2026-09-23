"""Tests for the reference-engine seam.

The placeholder must fail loudly. These tests exist so that milestone 1 cannot
quietly turn a custom-core answer into a "reference" answer.
"""

import pytest

from occultation.domain.observer import ObserverLocation
from occultation.domain.occultation import (
    FundamentalPlanePolynomial,
    StarOccultationElements,
)
from occultation.reference import ReferenceEngineUnavailable, SkyfieldEngine


def _elements() -> StarOccultationElements:
    return StarOccultationElements(
        reference_hour_td=10.0,
        star_declination_deg=11.9694,
        greenwich_hour_angle_at_reference_deg=156.6836,
        greenwich_hour_angle_rate_deg_per_hour=15.04107,
        moon_shadow_x=FundamentalPlanePolynomial(
            at_reference=0.22151,
            linear_rate_per_hour=0.55549,
            quadratic_term_per_hour_squared=0.0,
        ),
        moon_shadow_y=FundamentalPlanePolynomial(
            at_reference=0.19947,
            linear_rate_per_hour=-0.15258,
            quadratic_term_per_hour_squared=-1e-5,
        ),
        moon_shadow_radius_earth_radii=0.272495,
    )


def test_the_engine_refuses_to_return_a_number() -> None:
    with pytest.raises(ReferenceEngineUnavailable) as error:
        SkyfieldEngine().star_local_circumstances(
            elements=_elements(),
            observer=ObserverLocation(
                longitude_deg_east=114.1743,
                latitude_deg=22.3020,
                elevation_m=0.0,
            ),
            delta_t_seconds=65.0,
        )

    assert "not implemented" in str(error.value)


def test_the_unavailable_reason_is_shared_with_the_command_line() -> None:
    """One string, two callers: the CLI and the tests cannot drift apart."""
    from occultation.reference.skyfield_engine import UNAVAILABLE_REASON

    assert "data/manifest.json" in UNAVAILABLE_REASON


def test_importing_the_reference_package_does_not_import_skyfield() -> None:
    """The custom engine must keep working with no reference dependencies."""
    import sys

    assert "skyfield" not in sys.modules
