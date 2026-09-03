"""Unit tests for converting an observer to geocentric coordinates."""

import pytest

from occultation.core.observer_coordinates import calculate_geocentric_observer
from occultation.domain.observer import ObserverLocation


def test_palomar_observer_coordinates_match_meeus() -> None:
    # Meeus, printed p. 228: rho sin(phi') = +0.546862,
    # rho cos(phi') = +0.836338 for Palomar Mountain Observatory.
    palomar = ObserverLocation(
        longitude_deg_east=-116.8640,
        latitude_deg=33.3562,
        elevation_m=1706.0,
    )
    coordinates = calculate_geocentric_observer(palomar)
    assert coordinates.rho_sin_geocentric_latitude == pytest.approx(
        0.546862,
        abs=5e-7,
    )
    assert coordinates.rho_cos_geocentric_latitude == pytest.approx(
        0.836338,
        abs=5e-7,
    )


def test_southern_latitude_has_negative_geocentric_sine() -> None:
    southern_observer = ObserverLocation(
        longitude_deg_east=0.0,
        latitude_deg=-33.3562,
        elevation_m=0.0,
    )

    coordinates = calculate_geocentric_observer(southern_observer)

    assert coordinates.rho_sin_geocentric_latitude < 0.0
    assert coordinates.rho_cos_geocentric_latitude > 0.0


def test_observer_rejects_invalid_latitude() -> None:
    with pytest.raises(ValueError, match="latitude_deg"):
        ObserverLocation(
            longitude_deg_east=0.0,
            latitude_deg=91.0,
            elevation_m=0.0,
        )
