"""Validate the saved NAOJ reference snapshot against this project's solver.

The Jupiter rows of Meeus Table III carry no printed results, so their fixture
``expected`` block is a regression lock derived from this repository's own code
(see ``docs/algorithms/meeus-planet-local-circumstances.md`` §9). The one
independent statement about those events that *is* machine-readable is NAOJ's
per-event visibility status, saved under ``data/validation/naoj/``.

This script reads that snapshot, re-runs the solver for each event, and checks
that this project agrees with NAOJ about which events are visible from Uccle.
It is deliberately a script, not a pytest test: the snapshot is external data
and the CI ``data`` job runs it explicitly.

By default it prints one line per event (the NAOJ/custom verdict). Pass
``--trace`` to also print the intermediate value produced by each step of the
calculation -- the geocentric observer coordinates, the local hour angle, the
fundamental-plane u/v and their rates, the closest-approach correction, the
effective shadow radius L, the separation Delta, the position angle P and the
altitude h -- so a reader can see *how* the final verdict was reached. The
trace calls the very same helper functions the solver uses, so it cannot drift
from the solver's own arithmetic.
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path
from typing import Any

from occultation.core.local_circumstances import (
    _body_altitude_deg,
    _closest_approach_correction,
    _effective_shadow_radius,
    _normalized_separation,
    _position_angle_deg,
    _relative_motion_at,
    calculate_star_local_circumstances,
)
from occultation.core.observer_coordinates import calculate_geocentric_observer
from occultation.domain.observer import ObserverLocation
from occultation.domain.occultation import (
    FundamentalPlanePolynomial,
    StarOccultationElements,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = (
    REPOSITORY_ROOT / "data" / "validation" / "naoj" / "naoj_jupiter_2019_2020.json"
)
FIXTURE_PATH = REPOSITORY_ROOT / "tests" / "fixtures" / "meeus_jupiter_2019_2020.toml"


def _trace(
    *,
    date: str,
    elements: StarOccultationElements,
    observer: ObserverLocation,
    delta_t_seconds: float,
    result: Any,
) -> None:
    """Print each intermediate value the solver produced for one event.

    Every line is produced by calling the same helper the solver calls, so the
    printed numbers are the solver's own arithmetic, not a re-derivation.
    """
    geocentric_observer = calculate_geocentric_observer(observer)
    t = result.hours_after_reference
    relative_motion = _relative_motion_at(
        hours_after_reference=t,
        elements=elements,
        observer=observer,
        geocentric_observer=geocentric_observer,
        delta_t_seconds=delta_t_seconds,
    )
    effective_radius = _effective_shadow_radius(
        relative_motion=relative_motion,
        elements=elements,
    )
    separation = _normalized_separation(
        relative_motion,
        moon_shadow_radius=effective_radius,
    )
    position_angle = _position_angle_deg(relative_motion)
    altitude = _body_altitude_deg(
        declination_deg=relative_motion.declination_deg,
        observer_latitude_deg=observer.latitude_deg,
        local_hour_angle_deg=relative_motion.local_hour_angle_deg,
    )
    correction = _closest_approach_correction(relative_motion)

    print(f"  trace {date}:")
    print(
        f"    rho sin phi'                {geocentric_observer.rho_sin_geocentric_latitude:+.6f}"
    )
    print(
        f"    rho cos phi'                {geocentric_observer.rho_cos_geocentric_latitude:+.6f}"
    )
    print(f"    t (hours after To)          {t:+.6f}")
    print(
        f"    H (local hour angle, deg)   {relative_motion.local_hour_angle_deg:+.6f}"
    )
    print(f"    d (declination, deg)        {relative_motion.declination_deg:+.6f}")
    print(f"    u (x_distance)              {relative_motion.x_distance:+.6f}")
    print(f"    v (y_distance)              {relative_motion.y_distance:+.6f}")
    print(f"    u' (x_rate_per_hour)        {relative_motion.x_rate_per_hour:+.6f}")
    print(f"    v' (y_rate_per_hour)        {relative_motion.y_rate_per_hour:+.6f}")
    print(f"    n (speed per hour)          {relative_motion.speed_per_hour:+.6f}")
    print(f"    tau (last correction, h)    {correction:+.8f}")
    print(f"    L (effective radius)        {effective_radius:+.6f}")
    print(f"    Delta (separation, radii)   {separation:+.6f}")
    print(f"    P (position angle, deg)     {position_angle:+.4f}")
    print(f"    h (altitude, deg)           {altitude:+.4f}")
    print(f"    iterations                  {result.iteration_count}")


def _load_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise TypeError(f"{path}: the top level must be an object")
    return document


def _elements(fixture: dict[str, Any], date: str) -> StarOccultationElements:
    event = fixture["events"][date]
    data = event["elements"]
    return StarOccultationElements(
        reference_hour_td=event["reference_hour_td"],
        star_declination_deg=data["star_declination_deg"],
        greenwich_hour_angle_at_reference_deg=(
            data["greenwich_hour_angle_at_reference_deg"]
        ),
        greenwich_hour_angle_rate_deg_per_hour=(
            data["greenwich_hour_angle_rate_deg_per_hour"]
        ),
        declination_rate_deg_per_hour=data["declination_rate_deg_per_hour"],
        aberration_term=data["aberration_term"],
        moon_shadow_x=FundamentalPlanePolynomial(**data["moon_shadow_x"]),
        moon_shadow_y=FundamentalPlanePolynomial(**data["moon_shadow_y"]),
        moon_shadow_radius_earth_radii=data["moon_shadow_radius_earth_radii"],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--trace",
        action="store_true",
        help="also print each intermediate value of the calculation",
    )
    arguments = parser.parse_args(argv)

    snapshot = _load_json(SNAPSHOT_PATH)
    with FIXTURE_PATH.open("rb") as fixture_file:
        fixture = tomllib.load(fixture_file)

    observer = ObserverLocation(**fixture["observer"])
    delta_t_seconds = fixture["event"]["delta_t_seconds"]

    exit_code = 0
    for event in snapshot["events"]:
        date = event["date"]
        naoj_visible = bool(event["is_visible"])
        elements = _elements(fixture, date)
        result = calculate_star_local_circumstances(
            elements=elements,
            observer=observer,
            delta_t_seconds=delta_t_seconds,
        )
        agrees = result.is_visible == naoj_visible
        verdict = "ok" if agrees else "MISMATCH"
        print(
            f"{date}  NAOJ is_visible={naoj_visible!s:5}  "
            f"custom is_visible={result.is_visible!s:5}  {verdict}"
        )
        if arguments.trace:
            _trace(
                date=date,
                elements=elements,
                observer=observer,
                delta_t_seconds=delta_t_seconds,
                result=result,
            )
        if not agrees:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
