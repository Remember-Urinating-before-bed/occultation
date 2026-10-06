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
"""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path
from typing import Any

from occultation.core.local_circumstances import calculate_star_local_circumstances
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
    del argv
    snapshot = _load_json(SNAPSHOT_PATH)
    with FIXTURE_PATH.open("rb") as fixture_file:
        fixture = tomllib.load(fixture_file)

    observer = ObserverLocation(**fixture["observer"])
    delta_t_seconds = fixture["event"]["delta_t_seconds"]

    exit_code = 0
    for event in snapshot["events"]:
        date = event["date"]
        naoj_visible = bool(event["is_visible"])
        result = calculate_star_local_circumstances(
            elements=_elements(fixture, date),
            observer=observer,
            delta_t_seconds=delta_t_seconds,
        )
        agrees = result.is_visible == naoj_visible
        verdict = "ok" if agrees else "MISMATCH"
        print(
            f"{date}  NAOJ is_visible={naoj_visible!s:5}  "
            f"custom is_visible={result.is_visible!s:5}  {verdict}"
        )
        if not agrees:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
