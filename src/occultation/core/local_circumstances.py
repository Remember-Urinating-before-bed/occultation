"""Calculate local circumstances for a lunar occultation of a star.

This is a Python implementation of the star branch of the "Local
Circumstances" section on printed pages 224-226 of Jean Meeus's
*Astronomical Tables* (PDF pages 6-8). Besselian elements are supplied as
inputs; generating them belongs to a later milestone.

Time scale: the solver works in hours of Dynamical Time (TD) measured from
the tabular reference instant ``To``. Coordinate frame: the fundamental
plane, in units of Earth equatorial radii. See
``docs/algorithms/meeus-star-local-circumstances.md`` for the derivation and
for the printed-page citation of every constant.
"""

import math
from dataclasses import dataclass

from occultation.core.observer_coordinates import (
    GeocentricObserverCoordinates,
    calculate_geocentric_observer,
)
from occultation.domain.observer import ObserverLocation
from occultation.domain.occultation import (
    StarOccultationElements,
    StarOccultationResult,
)

# Meeus, printed p. 225: the hourly rates of the topocentric coordinates
# carry the pi/180 conversion from degrees to radians; the book prints
# 0.01745329.
DEGREES_TO_RADIANS = math.pi / 180.0

# Meeus, printed p. 224: Delta T (TD - UT, in seconds of time) shifts the
# local hour angle by Delta T / 239.345 degrees.
DELTA_T_SECONDS_PER_DEGREE_OF_HOUR_ANGLE = 239.345


@dataclass(frozen=True, slots=True)
class RelativeMotion:
    """Star-Moon relative position and velocity in the fundamental plane.

    ``x_distance`` and ``y_distance`` correspond to Meeus's ``u`` and ``v``.
    Their rates correspond to ``u'`` and ``v'``.
    """

    local_hour_angle_deg: float
    x_distance: float
    y_distance: float
    x_rate_per_hour: float
    y_rate_per_hour: float

    @property
    def speed_per_hour(self) -> float:
        return math.hypot(self.x_rate_per_hour, self.y_rate_per_hour)


def calculate_star_local_circumstances(
    elements: StarOccultationElements,
    observer: ObserverLocation,
    delta_t_seconds: float,
    *,
    convergence_tolerance_hours: float = 1e-6,
    max_iterations: int = 20,
) -> StarOccultationResult:
    """Calculate the closest topocentric approach of a star to the Moon.

    ``delta_t_seconds`` is TD minus UT, matching Meeus's terminology.

    The returned separation is measured in apparent lunar radii: an absolute
    value greater than one means the star is not occulted at closest
    approach.
    """
    _validate_solver_options(
        delta_t_seconds=delta_t_seconds,
        convergence_tolerance_hours=convergence_tolerance_hours,
        max_iterations=max_iterations,
    )

    geocentric_observer = calculate_geocentric_observer(observer)

    # Meeus, printed p. 224: "For an assumed value of t (take t = 0 as a
    # first approximation)".
    hours_after_reference = 0.0
    relative_motion: RelativeMotion | None = None
    iteration_count = 0
    for iteration_count in range(1, max_iterations + 1):
        relative_motion = _relative_motion_at(
            hours_after_reference=hours_after_reference,
            elements=elements,
            observer=observer,
            geocentric_observer=geocentric_observer,
            delta_t_seconds=delta_t_seconds,
        )
        correction_hours = _closest_approach_correction(relative_motion)
        hours_after_reference += correction_hours
        if abs(correction_hours) < convergence_tolerance_hours:
            break
    else:
        raise RuntimeError(
            "closest-approach calculation did not converge "
            f"within {max_iterations} iterations"
        )

    if relative_motion is None:  # pragma: no cover - max_iterations is >= 1
        raise RuntimeError("closest-approach calculation produced no result")

    separation_in_moon_radii = _normalized_separation(
        relative_motion,
        moon_shadow_radius=elements.moon_shadow_radius_earth_radii,
    )
    dynamical_time_hour = elements.reference_hour_td + hours_after_reference
    return StarOccultationResult(
        hours_after_reference=hours_after_reference,
        dynamical_time_hour=dynamical_time_hour,
        universal_time_hour=dynamical_time_hour - delta_t_seconds / 3600.0,
        separation_in_moon_radii=separation_in_moon_radii,
        position_angle_deg=_position_angle_deg(relative_motion),
        altitude_deg=_star_altitude_deg(
            star_declination_deg=elements.star_declination_deg,
            observer_latitude_deg=observer.latitude_deg,
            local_hour_angle_deg=relative_motion.local_hour_angle_deg,
        ),
        is_occultation=abs(separation_in_moon_radii) <= 1.0,
        iteration_count=iteration_count,
    )


def _relative_motion_at(
    hours_after_reference: float,
    elements: StarOccultationElements,
    observer: ObserverLocation,
    geocentric_observer: GeocentricObserverCoordinates,
    delta_t_seconds: float,
) -> RelativeMotion:
    """Evaluate u, v, u' and v' at one trial instant (Meeus pp. 224-225)."""
    local_hour_angle_deg = _local_hour_angle_deg(
        hours_after_reference=hours_after_reference,
        elements=elements,
        longitude_deg_east=observer.longitude_deg_east,
        delta_t_seconds=delta_t_seconds,
    )
    hour_angle_rad = math.radians(local_hour_angle_deg)
    declination_rad = math.radians(elements.star_declination_deg)

    observer_x = geocentric_observer.rho_cos_geocentric_latitude * math.sin(
        hour_angle_rad
    )
    observer_y = geocentric_observer.rho_sin_geocentric_latitude * math.cos(
        declination_rad
    ) - geocentric_observer.rho_cos_geocentric_latitude * math.cos(
        hour_angle_rad
    ) * math.sin(declination_rad)
    # xi' and eta' keep only the terms that survive for a star: Meeus's
    # planet-only D1 term is zero because a star's declination is treated as
    # constant during the event.
    observer_x_rate = (
        DEGREES_TO_RADIANS
        * elements.greenwich_hour_angle_rate_deg_per_hour
        * geocentric_observer.rho_cos_geocentric_latitude
        * math.cos(hour_angle_rad)
    )
    observer_y_rate = (
        DEGREES_TO_RADIANS
        * elements.greenwich_hour_angle_rate_deg_per_hour
        * observer_x
        * math.sin(declination_rad)
    )

    moon_shadow_x = elements.moon_shadow_x.value_at(hours_after_reference)
    moon_shadow_y = elements.moon_shadow_y.value_at(hours_after_reference)
    moon_shadow_x_rate = elements.moon_shadow_x.rate_at(hours_after_reference)
    moon_shadow_y_rate = elements.moon_shadow_y.rate_at(hours_after_reference)

    return RelativeMotion(
        local_hour_angle_deg=local_hour_angle_deg,
        x_distance=moon_shadow_x - observer_x,
        y_distance=moon_shadow_y - observer_y,
        x_rate_per_hour=moon_shadow_x_rate - observer_x_rate,
        y_rate_per_hour=moon_shadow_y_rate - observer_y_rate,
    )


def _local_hour_angle_deg(
    hours_after_reference: float,
    elements: StarOccultationElements,
    longitude_deg_east: float,
    delta_t_seconds: float,
) -> float:
    """Return H = H0 + H1 t - lambda - Delta T / 239.345 in degrees.

    Meeus writes ``- lambda`` where lambda is the *west*-positive longitude;
    our domain uses the conventional east-positive longitude, so that term
    becomes ``+ longitude_deg_east``.
    """
    return (
        elements.greenwich_hour_angle_at_reference_deg
        + elements.greenwich_hour_angle_rate_deg_per_hour * hours_after_reference
        + longitude_deg_east
        - delta_t_seconds / DELTA_T_SECONDS_PER_DEGREE_OF_HOUR_ANGLE
    )


def _closest_approach_correction(relative_motion: RelativeMotion) -> float:
    """Return Meeus's tau = -(u u' + v v') / n^2, the correction to t."""
    speed_squared = relative_motion.speed_per_hour**2
    if speed_squared == 0.0:
        raise ValueError("relative star-Moon speed must not be zero")
    position_dot_velocity = (
        relative_motion.x_distance * relative_motion.x_rate_per_hour
        + relative_motion.y_distance * relative_motion.y_rate_per_hour
    )
    return -position_dot_velocity / speed_squared


def _normalized_separation(
    relative_motion: RelativeMotion,
    *,
    moon_shadow_radius: float,
) -> float:
    """Meeus formula (6): least separation in lunar radii, north-positive."""
    signed_cross_product = (
        relative_motion.x_distance * relative_motion.y_rate_per_hour
        - relative_motion.y_distance * relative_motion.x_rate_per_hour
    )
    return signed_cross_product / (relative_motion.speed_per_hour * moon_shadow_radius)


def _position_angle_deg(relative_motion: RelativeMotion) -> float:
    """Meeus formula (4): tan P = u / v, with cos P opposite in sign to v."""
    angle_deg = math.degrees(
        math.atan2(-relative_motion.x_distance, -relative_motion.y_distance)
    )
    return angle_deg % 360.0


def _star_altitude_deg(
    *,
    star_declination_deg: float,
    observer_latitude_deg: float,
    local_hour_angle_deg: float,
) -> float:
    """Meeus formula (8): sin h = sin d sin phi + cos d cos phi cos H."""
    declination_rad = math.radians(star_declination_deg)
    latitude_rad = math.radians(observer_latitude_deg)
    hour_angle_rad = math.radians(local_hour_angle_deg)
    sin_altitude = math.sin(declination_rad) * math.sin(latitude_rad) + math.cos(
        declination_rad
    ) * math.cos(latitude_rad) * math.cos(hour_angle_rad)
    return math.degrees(math.asin(max(-1.0, min(1.0, sin_altitude))))


def _validate_solver_options(
    *,
    delta_t_seconds: float,
    convergence_tolerance_hours: float,
    max_iterations: int,
) -> None:
    """Reject solver inputs that cannot produce a meaningful iteration."""
    if not math.isfinite(delta_t_seconds):
        raise ValueError("delta_t_seconds must be finite")
    if not math.isfinite(convergence_tolerance_hours):
        raise ValueError("convergence_tolerance_hours must be finite")
    if convergence_tolerance_hours <= 0.0:
        raise ValueError("convergence_tolerance_hours must be positive")
    if max_iterations < 1:
        raise ValueError("max_iterations must be at least 1")
