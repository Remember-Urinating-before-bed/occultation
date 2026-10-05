"""Domain values used by lunar-occultation calculations."""

import math
from dataclasses import dataclass

#: Geometric horizon used by :attr:`StarOccultationResult.is_visible`.
#: Zero means "star centre above the geometric horizon". Atmospheric
#: refraction (about 0.57 deg at the horizon) is deliberately not applied yet;
#: it belongs with the shared coordinate primitives of a later milestone.
HORIZON_ALTITUDE_DEG = 0.0


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
    """Besselian elements for one lunar occultation of a star or planet.

    Transcribed from Meeus, *Astronomical Tables*, printed pp. 224-226
    (see ``docs/algorithms/meeus-star-local-circumstances.md`` and
    ``docs/algorithms/meeus-planet-local-circumstances.md``).

    For a **star** the declination rate ``D1`` and the planetary aberration
    term ``F`` vanish: a star is a point at infinity, so its declination is
    constant over the event (``D1 = 0``) and the Moon's shadow is a cylinder
    whose radius is ``L = k = 0.272495`` (``F`` unused). Both default to
    ``0.0``, so a star element set is exactly the planet element set with
    ``D1 = F = 0``.

    For a **planet** ``D1`` is the hourly variation of the declination and
    ``F`` is the tabulated aberration/finite-distance term (Table III);
    ``moon_shadow_radius_earth_radii`` then carries that event's ``k``, which
    is slightly larger than the star value, and the effective radius becomes
    ``L = k - zeta F / 1e6``.
    """

    reference_hour_td: float
    star_declination_deg: float
    greenwich_hour_angle_at_reference_deg: float
    greenwich_hour_angle_rate_deg_per_hour: float
    moon_shadow_x: FundamentalPlanePolynomial
    moon_shadow_y: FundamentalPlanePolynomial
    moon_shadow_radius_earth_radii: float = 0.272495
    declination_rate_deg_per_hour: float = 0.0
    aberration_term: float = 0.0

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
        _require_finite(
            "declination_rate_deg_per_hour", self.declination_rate_deg_per_hour
        )
        _require_finite("aberration_term", self.aberration_term)
        if not -90.0 <= self.star_declination_deg <= 90.0:
            raise ValueError("star_declination_deg must be between -90 and 90")
        if self.moon_shadow_radius_earth_radii <= 0.0:
            raise ValueError("moon_shadow_radius_earth_radii must be positive")

    @property
    def is_planet(self) -> bool:
        """True when the elements carry a non-zero planet-only term."""
        return self.declination_rate_deg_per_hour != 0.0 or self.aberration_term != 0.0


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

    @property
    def is_visible(self) -> bool:
        """True when the occultation is both geometrically real and observable.

        The star must be hidden by the Moon's disk (``is_occultation``) *and*
        above the geometric horizon at the instant of closest approach. A
        negative altitude means the whole event is below the horizon, so the
        observer cannot see it even though the star is behind the disk.
        """
        return self.is_occultation and self.altitude_deg > HORIZON_ALTITUDE_DEG


@dataclass(frozen=True, slots=True)
class OccultationContact:
    """One contact (immersion or emersion) of the occulted body.

    Meeus, printed p. 226: the approximate contact instants start from
    ``t -/+ sqrt(1 - Delta^2) / n`` and are then refined from that guess.
    """

    name: str
    hours_after_reference: float
    dynamical_time_hour: float
    universal_time_hour: float
    position_angle_deg: float
    altitude_deg: float
    is_visible: bool


@dataclass(frozen=True, slots=True)
class PlanetOccultationResult:
    """Closest approach plus the immersion and emersion contacts."""

    closest_approach: StarOccultationResult
    immersion: OccultationContact
    emersion: OccultationContact
