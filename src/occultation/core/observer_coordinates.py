"""Geographical-to-geocentric observer conversion from Meeus page 224."""

import math
from dataclasses import dataclass

from occultation.domain.observer import ObserverLocation

# Meeus, Astronomical Tables, printed p. 224 (PDF p. 6): the factor for the
# observer's geocentric coordinates is k = 0.99664719 = 1 - flattening, and
# the Earth equatorial radius used to scale the elevation is 6378140 metres.
MEEUS_EARTH_FLATTENING_FACTOR = 0.99664719
MEEUS_EARTH_EQUATORIAL_RADIUS_M = 6_378_140.0


@dataclass(frozen=True, slots=True)
class GeocentricObserverCoordinates:
    """Observer coordinates required by the fundamental-plane projection.

    The fields correspond to Meeus's ``rho sin(phi')`` and ``rho cos(phi')``.
    """

    rho_sin_geocentric_latitude: float
    rho_cos_geocentric_latitude: float


def calculate_geocentric_observer(
    observer: ObserverLocation,
) -> GeocentricObserverCoordinates:
    """Convert a geographical observer location using Meeus's Earth model."""
    geographic_latitude_rad = math.radians(observer.latitude_deg)
    auxiliary_angle_rad = math.atan(
        MEEUS_EARTH_FLATTENING_FACTOR * math.tan(geographic_latitude_rad)
    )
    elevation_in_earth_radii = observer.elevation_m / MEEUS_EARTH_EQUATORIAL_RADIUS_M
    rho_sin_geocentric_latitude = MEEUS_EARTH_FLATTENING_FACTOR * math.sin(
        auxiliary_angle_rad
    ) + elevation_in_earth_radii * math.sin(geographic_latitude_rad)
    rho_cos_geocentric_latitude = math.cos(
        auxiliary_angle_rad
    ) + elevation_in_earth_radii * math.cos(geographic_latitude_rad)
    return GeocentricObserverCoordinates(
        rho_sin_geocentric_latitude=rho_sin_geocentric_latitude,
        rho_cos_geocentric_latitude=rho_cos_geocentric_latitude,
    )
