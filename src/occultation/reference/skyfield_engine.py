"""The Skyfield reference engine: an independent lunar-occultation calculation.

This module is the *reference* half of the project's verification discipline. The
custom core in :mod:`occultation.core` reduces Meeus's hand-transcribed Besselian
elements to a local answer; this engine ignores those elements entirely and
computes the same geometry from a JPL planetary ephemeris. When the two agree,
the agreement is evidence, because they share no code and almost no data.

Three design rules are load-bearing, and tests enforce each:

- **Skyfield is imported lazily.** Importing this package must not require
  Skyfield to be installed, so the custom engine keeps working in an environment
  with no reference dependencies.
- **The ephemeris is read from an explicit local path.** Nothing here downloads
  anything, ever. A missing or corrupt file is an error naming the path, not a
  silent fetch (``docs/AGENT_HANDOFF.md`` section 3.3).
- **A reference answer is a different type from a custom answer.** See
  :class:`BodyCircumstances`.

Why the element-based entry point cannot exist
---------------------------------------------

Meeus's Table II and Table III elements carry ``To`` as an abstract *hour of
Dynamical Time* with no calendar date attached. An ephemeris can only be asked
about a real instant, so there is no way to reduce an element set through
Skyfield: the date is not in the data. What the reference engine needs instead is
the body and the epoch, which is what a fixture keyed to a real event already
has. :meth:`SkyfieldEngine.body_local_circumstances` takes those.

The one modelling difference you must expect
--------------------------------------------

Meeus's ``k`` (0.272495 for a star, a tabulated value for a planet) is the Moon's
radius as a *fixed ratio* to the Earth's equatorial radius. This engine instead
uses the Moon's mean radius of 1737.4 km against the Moon's *actual* distance at
the event. The two conventions differ at roughly the 0.1% level. That is why the
comparison test's tolerance is quoted in thousandths of a Moon radius rather than
in the last printed digit — the two answers are independent calculations that
should agree closely, not two implementations of one formula.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from occultation.domain.observer import ObserverLocation
from occultation.domain.occultation import (
    StarOccultationElements,
    StarOccultationResult,
)

#: The Moon's mean radius in kilometres (IAU mean value). See the module
#: docstring for how this differs from Meeus's tabulated ``k``.
MOON_MEAN_RADIUS_KM = 1737.4

#: Default location of the fetched ephemeris, matching ``data/manifest.json``.
DEFAULT_EPHEMERIS_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "external" / "de440s.bsp"
)

#: Fixture body name -> SPICE target in the kernel. ``de440s.bsp`` carries only
#: barycentres for the outer planets; a planet's offset from its system
#: barycentre is far below the arcsecond that matters here, and Table III's own
#: ``F`` term exists precisely to absorb the body's finite distance.
#:
#: The Moon is deliberately absent: the Moon cannot occult itself, so asking for
#: it would give a separation that is identically zero and a position angle that
#: is undefined. The Sun is present because a solar eclipse is exactly this
#: geometry.
BODY_TARGETS: dict[str, str] = {
    "mercury": "mercury barycenter",
    "venus": "venus barycenter",
    "mars": "mars barycenter",
    "jupiter": "jupiter barycenter",
    "saturn": "saturn barycenter",
    "uranus": "uranus barycenter",
    "neptune": "neptune barycenter",
    "pluto": "pluto barycenter",
    "sun": "sun",
}


class ReferenceEngineUnavailable(RuntimeError):
    """Raised when a reference calculation cannot be performed at all."""


class ReferenceEngineError(RuntimeError):
    """Raised when the engine is usable in principle but a request fails.

    Today's causes are a missing ephemeris file, a corrupt one, and a body the
    kernel does not carry. All three are conditions a caller can act on, and
    none of them is "Skyfield is not installed".
    """


#: Message shared by the CLI and the tests, so the wording cannot drift.
#:
#: The element-based entry point cannot work, and that is a property of Meeus's
#: data rather than an unfinished task: a Table II/III element set carries ``To``
#: as an abstract "hour of Dynamical Time" with no date attached, so it cannot be
#: turned back into an instant an ephemeris could be asked about. The reference
#: calculation therefore takes a body and an epoch — see
#: :meth:`SkyfieldEngine.body_local_circumstances` — and the command line reaches
#: it with ``--reference-body`` and ``--epoch-ut``.
UNAVAILABLE_REASON = (
    "a Meeus element set carries no calendar date, so it cannot be handed to an "
    "ephemeris; pass --reference-body and --epoch-ut for the Skyfield "
    "comparison - see SkyfieldEngine.body_local_circumstances"
)


@dataclass(frozen=True, slots=True)
class BodyCircumstances:
    """The reference engine's answer for one body, in the custom code's units.

    Deliberately *not* a
    :class:`~occultation.domain.occultation.StarOccultationResult`. That type
    carries ``iteration_count`` and a ``reference_hour_td``-relative hour, both
    artifacts of Besselian iteration that mean nothing here. A separate type
    makes it impossible to pass a reference answer off as a custom one by
    accident — the two must be compared field by field, on purpose.
    """

    body: str
    universal_time: datetime
    separation_in_moon_radii: float
    angular_separation_deg: float
    moon_angular_radius_deg: float
    position_angle_deg: float
    moon_altitude_deg: float
    moon_distance_km: float

    @property
    def is_occultation(self) -> bool:
        """True when the body's centre is inside the Moon's apparent disk."""
        return bool(abs(self.separation_in_moon_radii) <= 1.0)

    @property
    def is_visible(self) -> bool:
        """True when the event is real and the Moon is above the horizon."""
        return self.is_occultation and bool(self.moon_altitude_deg > 0.0)


@dataclass(frozen=True, slots=True)
class _Sample:
    """One instant's geometry, before the minimum is found."""

    separation_rad: float
    moon_radius_rad: float
    moon_altitude_deg: float


class SkyfieldEngine:
    """Lunar-occultation reference calculations from a local SPK kernel.

    Constructing the engine never touches the filesystem; the kernel is opened
    on first use and cached, so a batch of comparisons pays the load once.
    """

    name = "skyfield"

    def __init__(
        self,
        ephemeris_path: Path | str | None = None,
        *,
        moon_radius_km: float = MOON_MEAN_RADIUS_KM,
    ) -> None:
        self._ephemeris_path = Path(ephemeris_path or DEFAULT_EPHEMERIS_PATH)
        self._moon_radius_km = moon_radius_km
        self._ephemeris: Any = None
        self._timescale: Any = None

    # -- state ---------------------------------------------------------------

    @property
    def ephemeris_path(self) -> Path:
        return self._ephemeris_path

    def is_available(self) -> bool:
        """True when the kernel file is present and Skyfield is importable."""
        if not self._ephemeris_path.exists():
            return False
        try:
            import skyfield  # noqa: F401
        except ImportError:  # pragma: no cover - environment dependent
            return False
        return True

    def _load(self) -> tuple[Any, Any]:
        """Open the kernel and timescale once, or explain why not."""
        if self._ephemeris is not None and self._timescale is not None:
            return self._ephemeris, self._timescale
        try:
            from skyfield.api import load, load_file
        except ImportError as error:  # pragma: no cover - environment dependent
            raise ReferenceEngineUnavailable(
                "Skyfield is not installed in this environment; install the "
                "reference dependencies or skip the comparison"
            ) from error
        if not self._ephemeris_path.exists():
            raise ReferenceEngineError(
                f"no ephemeris at {self._ephemeris_path}; fetch it with "
                "'uv run python scripts/fetch_reference_data.py fetch --download'"
            )
        self._timescale = load.timescale()
        try:
            self._ephemeris = load_file(str(self._ephemeris_path))
        except Exception as error:
            self._timescale = None
            raise ReferenceEngineError(
                f"{self._ephemeris_path}: cannot be opened as an SPK kernel ({error})"
            ) from error
        return self._ephemeris, self._timescale

    def _target(self, body: str) -> str:
        try:
            return BODY_TARGETS[body.strip().lower()]
        except KeyError as error:
            known = ", ".join(sorted(BODY_TARGETS))
            raise ReferenceEngineError(
                f"unknown body {body!r}; known bodies are {known}"
            ) from error

    # -- the calculation -----------------------------------------------------

    def body_local_circumstances(
        self,
        body: str,
        epoch_ut: datetime,
        observer: ObserverLocation,
        *,
        search_half_window_hours: float = 6.0,
        coarse_step_seconds: float = 60.0,
    ) -> BodyCircumstances:
        """Least apparent separation of ``body`` from the Moon near ``epoch_ut``.

        ``epoch_ut`` seeds the search; the returned instant is the minimum found,
        which is not ``epoch_ut``. A Meeus element set's ``To`` is the natural
        seed, because the minimum always lies within a few hours of it.
        """
        sample = self._sampler(body, observer)
        _, minimum = self._minimise_separation(
            sample,
            epoch_ut,
            half_window_hours=search_half_window_hours,
            coarse_step_seconds=coarse_step_seconds,
        )
        at_minimum = sample(minimum)
        return BodyCircumstances(
            body=body,
            universal_time=minimum,
            separation_in_moon_radii=(
                at_minimum.separation_rad / at_minimum.moon_radius_rad
            ),
            angular_separation_deg=math.degrees(at_minimum.separation_rad),
            moon_angular_radius_deg=math.degrees(at_minimum.moon_radius_rad),
            position_angle_deg=self._position_angle_deg(body, minimum, observer),
            moon_altitude_deg=at_minimum.moon_altitude_deg,
            moon_distance_km=self._moon_distance_km(minimum, observer),
        )

    def _sampler(
        self, body: str, observer: ObserverLocation
    ) -> Callable[[datetime], _Sample]:
        """Build the closure that samples the geometry at one instant.

        The engine's two positions of interest — the observer's site and the
        ephemeris — are captured once here, so the search below does not rebuild
        them at every trial instant.
        """
        from skyfield.api import wgs84

        # Validate the body name before touching the filesystem, so a typo is
        # reported as a typo whether or not the ephemeris happens to be present.
        target = self._target(body)
        ephemeris, timescale = self._load()
        try:
            body_position = ephemeris[target]
        except KeyError as error:
            raise ReferenceEngineError(
                f"the ephemeris at {self._ephemeris_path} does not carry "
                f"{target!r}: {error}"
            ) from error
        earth_topocentric_origin = ephemeris["earth"]
        moon = ephemeris["moon"]
        site = wgs84.latlon(
            observer.latitude_deg,
            observer.longitude_deg_east,
            elevation_m=observer.elevation_m,
        )

        def sample(when: datetime) -> _Sample:
            skyfield_time = timescale.from_datetime(_as_utc(when))
            topocentric = (earth_topocentric_origin + site).at(skyfield_time)
            moon_observed = topocentric.observe(moon)
            moon_apparent = moon_observed.apparent()
            body_apparent = topocentric.observe(body_position).apparent()
            return _Sample(
                separation_rad=moon_apparent.separation_from(body_apparent).radians,
                moon_radius_rad=math.asin(
                    self._moon_radius_km / moon_observed.distance().km
                ),
                moon_altitude_deg=moon_apparent.altaz()[0].degrees,
            )

        return sample

    def _minimise_separation(
        self,
        sample: Callable[[datetime], _Sample],
        epoch_ut: datetime,
        *,
        half_window_hours: float,
        coarse_step_seconds: float,
    ) -> tuple[float, datetime]:
        """Coarse scan for the deepest minimum, then a ternary refinement.

        A scan rather than a root-find, because the separation is not monotonic
        across the window and a fast body can dip more than once. The scan finds
        the deepest dip; ternary search then narrows it, which is valid because
        the separation is unimodal on the bracketing interval around a sampled
        minimum.
        """
        epoch_ut = _as_utc(epoch_ut)
        step = timedelta(seconds=coarse_step_seconds)
        count = int(half_window_hours * 3600 // coarse_step_seconds)
        best_separation = math.inf
        best_time = epoch_ut
        for index in range(-count, count + 1):
            when = epoch_ut + step * index
            separation = sample(when).separation_rad
            if separation < best_separation:
                best_separation, best_time = separation, when

        low = best_time - step
        high = best_time + step
        for _ in range(80):
            third = (high - low) / 3
            left = low + third
            right = high - third
            if sample(left).separation_rad < sample(right).separation_rad:
                high = right
            else:
                low = left
            if (high - low).total_seconds() < 1e-3:
                break
        candidate = low + (high - low) / 2
        candidate_separation = sample(candidate).separation_rad
        if candidate_separation < best_separation:
            best_separation, best_time = candidate_separation, candidate
        return best_separation, best_time

    def _position_angle_deg(
        self, body: str, when: datetime, observer: ObserverLocation
    ) -> float:
        """Position angle of the body's centre from the Moon's north point.

        Measured on the apparent topocentric sky from north towards east, which
        is Meeus's formula (4) convention ("from the North Point of the Moon's
        disk, towards the East, South and West").
        """
        from skyfield.api import wgs84

        ephemeris, timescale = self._load()
        site = wgs84.latlon(
            observer.latitude_deg,
            observer.longitude_deg_east,
            elevation_m=observer.elevation_m,
        )
        skyfield_time = timescale.from_datetime(_as_utc(when))
        topocentric = (ephemeris["earth"] + site).at(skyfield_time)
        moon_ra, moon_dec, _ = topocentric.observe(ephemeris["moon"]).apparent().radec()
        body_ra, body_dec, _ = (
            topocentric.observe(ephemeris[self._target(body)]).apparent().radec()
        )
        return _position_angle_from_radec(
            moon_ra.radians,
            moon_dec.radians,
            body_ra.radians,
            body_dec.radians,
        )

    def _moon_distance_km(self, when: datetime, observer: ObserverLocation) -> float:
        from skyfield.api import wgs84

        ephemeris, timescale = self._load()
        site = wgs84.latlon(
            observer.latitude_deg,
            observer.longitude_deg_east,
            elevation_m=observer.elevation_m,
        )
        skyfield_time = timescale.from_datetime(_as_utc(when))
        topocentric = (ephemeris["earth"] + site).at(skyfield_time)
        return topocentric.observe(ephemeris["moon"]).distance().km

    # -- the element-based entry point ---------------------------------------

    def star_local_circumstances(
        self,
        elements: StarOccultationElements,
        observer: ObserverLocation,
        delta_t_seconds: float,
    ) -> StarOccultationResult:
        """Refuse, and say why, rather than inventing a number.

        Kept so that the interface the CLI and the year-1 tests rely on does not
        move. The working reference calculation is
        :meth:`body_local_circumstances`, which needs a date.
        """
        del elements, observer, delta_t_seconds
        raise ReferenceEngineUnavailable(UNAVAILABLE_REASON)


def _as_utc(when: datetime) -> datetime:
    """Attach UTC to a naive datetime; leave an aware one alone."""
    return when if when.tzinfo else when.replace(tzinfo=UTC)


def _position_angle_from_radec(
    moon_ra_rad: float,
    moon_dec_rad: float,
    body_ra_rad: float,
    body_dec_rad: float,
) -> float:
    """North-through-east position angle of one point about another."""
    delta_ra = body_ra_rad - moon_ra_rad
    north = math.cos(moon_dec_rad) * math.sin(body_dec_rad) - math.sin(
        moon_dec_rad
    ) * math.cos(body_dec_rad) * math.cos(delta_ra)
    east = math.cos(body_dec_rad) * math.sin(delta_ra)
    return math.degrees(math.atan2(east, north)) % 360.0
