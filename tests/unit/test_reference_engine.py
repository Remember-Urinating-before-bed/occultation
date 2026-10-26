"""Tests for the reference-engine seam.

Two properties are load-bearing and are checked here rather than in the
comparison test, because they must hold even when the ephemeris is absent:

- importing the reference package must not import Skyfield, so the custom engine
  keeps working with no reference dependencies installed;
- the element-based entry point must refuse loudly rather than invent a number.

The comparison itself is exercised by
``tests/reference_cases/test_skyfield_agreement.py``, which needs the ephemeris
and therefore skips when the file is missing.
"""

import datetime as dt
import subprocess
import sys

import pytest

from occultation.domain.observer import ObserverLocation
from occultation.domain.occultation import (
    FundamentalPlanePolynomial,
    StarOccultationElements,
)
from occultation.reference import (
    ReferenceEngineError,
    ReferenceEngineUnavailable,
    SkyfieldEngine,
)

HONG_KONG = ObserverLocation(
    longitude_deg_east=114.1743,
    latitude_deg=22.3020,
    elevation_m=0.0,
)


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


def test_the_element_entry_point_refuses_to_return_a_number() -> None:
    """A Meeus element set has no date, so there is nothing to ask an ephemeris."""
    with pytest.raises(ReferenceEngineUnavailable) as error:
        SkyfieldEngine().star_local_circumstances(
            elements=_elements(),
            observer=HONG_KONG,
            delta_t_seconds=65.0,
        )

    assert "no calendar date" in str(error.value)


def test_the_unavailable_reason_names_the_working_entry_point() -> None:
    """One string, two callers: the CLI and the tests cannot drift apart."""
    from occultation.reference.skyfield_engine import UNAVAILABLE_REASON

    assert "body_local_circumstances" in UNAVAILABLE_REASON
    assert "--reference-body" in UNAVAILABLE_REASON


def test_importing_the_reference_package_does_not_import_skyfield() -> None:
    """The custom engine must keep working with no reference dependencies.

    Run in a subprocess: by the time the whole suite has run, another test has
    legitimately imported Skyfield into this interpreter, and checking
    ``sys.modules`` here would then be checking test ordering rather than the
    import graph.
    """
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import occultation.reference, sys; print('skyfield' in sys.modules)",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    assert completed.stdout.strip() == "False"


def test_constructing_the_engine_does_not_touch_the_filesystem(tmp_path) -> None:
    """The engine must be constructible even when the ephemeris is absent."""
    engine = SkyfieldEngine(tmp_path / "absent.bsp")

    assert engine.ephemeris_path == tmp_path / "absent.bsp"
    assert engine.is_available() is False


def test_a_missing_ephemeris_names_the_path_and_the_fetch_command(tmp_path) -> None:
    """No silent download: absence is an error that says what to run."""
    engine = SkyfieldEngine(tmp_path / "absent.bsp")

    with pytest.raises(ReferenceEngineError) as error:
        engine.body_local_circumstances(
            "saturn", dt.datetime(2024, 12, 8, 9, 0, 0, tzinfo=dt.UTC), HONG_KONG
        )

    message = str(error.value)
    assert str(tmp_path / "absent.bsp") in message
    assert "fetch_reference_data.py" in message


def test_an_unreadable_ephemeris_is_reported_as_such(tmp_path) -> None:
    """A truncated file is a distinct failure from a missing one."""
    broken = tmp_path / "broken.bsp"
    broken.write_bytes(b"not an SPK kernel")

    with pytest.raises(ReferenceEngineError) as error:
        SkyfieldEngine(broken).body_local_circumstances(
            "saturn", dt.datetime(2024, 12, 8, 9, 0, 0, tzinfo=dt.UTC), HONG_KONG
        )

    assert "SPK kernel" in str(error.value)


def test_an_unknown_body_is_refused_before_the_ephemeris_is_opened(tmp_path) -> None:
    """The body name is validated against the known set, with the set printed."""
    with pytest.raises(ReferenceEngineError) as error:
        SkyfieldEngine(tmp_path / "absent.bsp").body_local_circumstances(
            "vulcan", dt.datetime(2024, 12, 8, 9, 0, 0, tzinfo=dt.UTC), HONG_KONG
        )

    assert "unknown body" in str(error.value)
    assert "saturn" in str(error.value)
