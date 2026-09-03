"""Domain values used by lunar-occultation calculations."""

import math
from dataclasses import dataclass


def _require_finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


@dataclass(frozen=True, slots=True)
class FundamentalPlanePolynomial:
    """One quadratic Besselian coordinate as a function of hours from To.

    This represents Meeus's ``X0 + X1 * t + X2 * t^2`` or the corresponding
    expression for Y. Values are in Earth-equatorial-radius units.
    """

    at_reference: float
    linear_rate_per_hour: float
    quadratic_term_per_hour_squared: float

    def __post_init__(self) -> None:
        _require_finite("at_reference", self.at_reference)
        _require_finite("linear_rate_per_hour", self.linear_rate_per_hour)
        _require_finite(
            "quadratic_term_per_hour_squared",
            self.quadratic_term_per_hour_squared,
        )

    def value_at(self, hours_after_reference: float) -> float:
        """Evaluate the coordinate at ``To + hours_after_reference``."""
        return (
            self.at_reference
            + self.linear_rate_per_hour * hours_after_reference
            + self.quadratic_term_per_hour_squared * hours_after_reference**2
        )

    def rate_at(self, hours_after_reference: float) -> float:
        """Evaluate the coordinate's hourly rate at the requested time."""
        return (
            self.linear_rate_per_hour
            + 2.0 * self.quadratic_term_per_hour_squared * hours_after_reference
        )


@dataclass(frozen=True, slots=True)
class StarOccultationElements:
    """Besselian elements for one lunar occultation of a star.

    Transcribed from Meeus, *Astronomical Tables*, printed pp. 224-226
    (see ``docs/algorithms/meeus-star-local-circumstances.md``). The
    declination rate ``D1`` and the planetary aberration term ``F`` are
    deliberately absent: both vanish for a star, whose declination is
    constant over the event and whose shadow radius is ``L = k = 0.272495``.
    """

    reference_hour_td: float
    star_declination_deg: float
    greenwich_hour_angle_at_reference_deg: float
    greenwich_hour_angle_rate_deg_per_hour: float
    moon_shadow_x: FundamentalPlanePolynomial
    moon_shadow_y: FundamentalPlanePolynomial
    moon_shadow_radius_earth_radii: float = 0.272495

    def __post_init__(self) -> None:
        _require_finite("reference_hour_td", self.reference_hour_td)
        _require_finite("star_declination_deg", self.star_declination_deg)
        _require_finite(
            "greenwich_hour_angle_at_reference_deg",
            self.greenwich_hour_angle_at_reference_deg,
        )
        _require_finite(
            "greenwich_hour_angle_rate_deg_per_hour",
            self.greenwich_hour_angle_rate_deg_per_hour,
        )
        _require_finite(
            "moon_shadow_radius_earth_radii",
            self.moon_shadow_radius_earth_radii,
        )
        if not -90.0 <= self.star_declination_deg <= 90.0:
            raise ValueError("star_declination_deg must be between -90 and 90")
        if self.moon_shadow_radius_earth_radii <= 0.0:
            raise ValueError("moon_shadow_radius_earth_radii must be positive")


@dataclass(frozen=True, slots=True)
class StarOccultationResult:
    """Closest local approach of a star to the Moon."""

    hours_after_reference: float
    dynamical_time_hour: float
    universal_time_hour: float
    separation_in_moon_radii: float
    position_angle_deg: float
    altitude_deg: float
    is_occultation: bool
    iteration_count: int

    @property
    def limb_clearance_in_moon_radii(self) -> float:
        """Signed distance from the lunar limb; negative means occulted."""
        return abs(self.separation_in_moon_radii) - 1.0
