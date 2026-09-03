"""Domain model for an observer on Earth."""

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ObserverLocation:
    """Geographical observer location using project-wide conventions.

    Longitude is positive east and negative west. Latitude is positive north.
    Elevation is metres above sea level.
    """

    longitude_deg_east: float
    latitude_deg: float
    elevation_m: float

    def __post_init__(self) -> None:
        values = {
            "longitude_deg_east": self.longitude_deg_east,
            "latitude_deg": self.latitude_deg,
            "elevation_m": self.elevation_m,
        }
        for name, value in values.items():
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if not -180.0 <= self.longitude_deg_east <= 180.0:
            raise ValueError("longitude_deg_east must be between -180 and 180")
        if not -90.0 <= self.latitude_deg <= 90.0:
            raise ValueError("latitude_deg must be between -90 and 90")
        if self.elevation_m < -500.0:
            raise ValueError("elevation_m must be at least -500 metres")
