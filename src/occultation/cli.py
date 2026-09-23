"""Command-line interface for the ``occultation`` package.

This module is a thin presentation layer and contains no astronomy. It parses
arguments, hands them to :mod:`occultation.io` to become domain values, calls
either the custom core or the reference engine, and formats the answer. That
separation is what lets the element *source* change later — from a
hand-transcribed file to elements this project calculates itself — without the
command line changing at all.

Exit codes:

- ``0`` success;
- ``1`` the calculation ran but a published value did not match (``verify``);
- ``2`` bad usage or bad input (argparse, missing file, malformed document,
  rejected value);
- ``3`` the reference engine was requested but is not available.
"""

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path
from typing import Any

from occultation.core.local_circumstances import (
    calculate_star_local_circumstances,
)
from occultation.core.observer_coordinates import calculate_geocentric_observer
from occultation.domain.observer import ObserverLocation
from occultation.domain.occultation import (
    FundamentalPlanePolynomial,
    StarOccultationElements,
    StarOccultationResult,
)
from occultation.io.elements_file import (
    ElementsFileError,
    load_star_elements,
    star_elements_from_mapping,
)
from occultation.io.location_file import (
    LocationFileError,
    load_observer_location,
    observer_from_mapping,
)
from occultation.reference import ReferenceEngineUnavailable, SkyfieldEngine

EXIT_OK = 0
EXIT_MISMATCH = 1
EXIT_USAGE = 2
EXIT_REFERENCE_UNAVAILABLE = 3

#: Default shadow radius for a star occultation (Meeus, printed p. 225).
DEFAULT_MOON_SHADOW_RADIUS_EARTH_RADII = 0.272495

#: The textbook case ``verify meeus-example-5`` reproduces. The expected values
#: live in the fixture itself, so the command and the regression test cannot
#: disagree about what the book printed.
MEEUS_EXAMPLE_5_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "fixtures"
    / "meeus_regulus_1999.json"
)

#: Fallback tolerances, used only if a fixture carries no ``tolerances`` object.
#: They match the number of digits the sources print: the geocentric observer
#: values come from the unit test's ``abs=5e-7``, the rest from the regression
#: test's tolerances for Meeus Example 5 (printed pp. 228-229).
DEFAULT_TOLERANCES: dict[str, float] = {
    "rho_sin_geocentric_latitude": 5e-7,
    "rho_cos_geocentric_latitude": 5e-7,
    "hours_after_reference": 5e-6,
    "dynamical_time_hour": 5e-6,
    "universal_time_hour": 2e-4,
    "separation_in_moon_radii": 5e-4,
    "limb_clearance_in_moon_radii": 5e-4,
    "position_angle_deg": 0.02,
    "altitude_deg": 0.5,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="occultation", description="Generic astronomical data for HK"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=version("occultation"),
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    _add_local_circumstances_parser(subparsers)
    _add_verify_parser(subparsers)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line and return the process exit code."""
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if arguments.command is None:
        parser.print_help()
        return EXIT_OK
    try:
        if arguments.command == "local-circumstances":
            return _run_local_circumstances(arguments)
        return _run_verify(arguments)
    except ReferenceEngineUnavailable as error:
        print(f"occultation: error: {error}", file=sys.stderr)
        return EXIT_REFERENCE_UNAVAILABLE
    except (ElementsFileError, LocationFileError, ValueError, RuntimeError) as error:
        print(f"occultation: error: {error}", file=sys.stderr)
        return EXIT_USAGE


def _add_local_circumstances_parser(
    subparsers: Any,
) -> None:
    parser = subparsers.add_parser(
        "local-circumstances",
        help="closest approach of a star to the Moon for one observer",
        description=(
            "Calculate the local circumstances of a lunar occultation of a star "
            "from Besselian elements, using the custom core (Meeus, Astronomical "
            "Tables, printed pp. 224-226)."
        ),
    )
    _add_element_arguments(parser)
    _add_observer_arguments(parser)
    parser.add_argument(
        "--delta-t-seconds",
        type=float,
        required=True,
        metavar="SECONDS",
        help="TD minus UT in seconds; always supplied, never defaulted silently",
    )
    parser.add_argument(
        "--engine",
        choices=("custom", "skyfield", "compare"),
        default="custom",
        help=(
            "custom: this repository's own maths (default); "
            "skyfield: the reference engine, not implemented yet, exits 3; "
            "compare: run the custom engine and report the reference engine's "
            "availability"
        ),
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format (default: text)",
    )
    parser.add_argument(
        "--tolerance-hours",
        type=float,
        default=1e-6,
        metavar="HOURS",
        help="stop iterating once the time correction is below this (default: 1e-6)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=20,
        metavar="N",
        help="give up after this many iterations (default: 20)",
    )


def _add_element_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--elements",
        type=Path,
        metavar="FILE",
        help="JSON elements document; alternative to the inline element options",
    )
    parser.add_argument(
        "--reference-hour-td",
        type=float,
        metavar="HOUR",
        help="tabular reference instant To, hours of Dynamical Time",
    )
    parser.add_argument(
        "--star-declination-deg",
        type=float,
        metavar="DEG",
        help="star declination d0, degrees",
    )
    parser.add_argument(
        "--greenwich-hour-angle-deg",
        type=float,
        metavar="DEG",
        help="Greenwich hour angle H0 at To, degrees",
    )
    parser.add_argument(
        "--greenwich-hour-angle-rate-deg-per-hour",
        type=float,
        metavar="DEG",
        help="hourly rate H1 of the hour angle (15.04107 for a star)",
    )
    parser.add_argument(
        "--shadow-x0", type=float, metavar="EARTH_RADII", help="Besselian X0"
    )
    parser.add_argument(
        "--shadow-x1", type=float, metavar="EARTH_RADII", help="Besselian X1"
    )
    parser.add_argument(
        "--shadow-x2", type=float, metavar="EARTH_RADII", help="Besselian X2"
    )
    parser.add_argument(
        "--shadow-y0", type=float, metavar="EARTH_RADII", help="Besselian Y0"
    )
    parser.add_argument(
        "--shadow-y1", type=float, metavar="EARTH_RADII", help="Besselian Y1"
    )
    parser.add_argument(
        "--shadow-y2", type=float, metavar="EARTH_RADII", help="Besselian Y2"
    )
    parser.add_argument(
        "--shadow-radius-earth-radii",
        type=float,
        default=DEFAULT_MOON_SHADOW_RADIUS_EARTH_RADII,
        metavar="EARTH_RADII",
        help=(
            "Moon's relative radius k (default: "
            f"{DEFAULT_MOON_SHADOW_RADIUS_EARTH_RADII})"
        ),
    )


def _add_observer_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--location",
        type=Path,
        metavar="FILE",
        help="observer document (.json or .toml); alternative to the inline options",
    )
    parser.add_argument(
        "--longitude-deg-east",
        type=float,
        metavar="DEG",
        help="observer longitude, east-positive",
    )
    parser.add_argument(
        "--latitude-deg",
        type=float,
        metavar="DEG",
        help="observer latitude, north-positive",
    )
    parser.add_argument(
        "--elevation-m",
        type=float,
        default=0.0,
        metavar="METRES",
        help="observer elevation above sea level (default: 0)",
    )


def _add_verify_parser(
    subparsers: Any,
) -> None:
    parser = subparsers.add_parser(
        "verify",
        help="re-run a published worked example and compare every printed digit",
        description=(
            "Re-run a worked example from the project's sources and report the "
            "difference between the printed values and this repository's own "
            "calculation. Exits 1 if any value is outside the tolerance that the "
            "source's printed precision supports."
        ),
    )
    examples = parser.add_subparsers(dest="example", metavar="EXAMPLE")
    example_5 = examples.add_parser(
        "meeus-example-5",
        help="Meeus Example 5: occultation of Regulus, 1999 March 1, Palomar",
        description=(
            "Meeus, Astronomical Tables, printed pp. 228-229. Inputs and expected "
            "values are read from the fixture that the regression test also uses."
        ),
    )
    example_5.add_argument(
        "--fixture",
        type=Path,
        default=MEEUS_EXAMPLE_5_FIXTURE,
        metavar="FILE",
        help=f"fixture to use (default: {MEEUS_EXAMPLE_5_FIXTURE})",
    )
    example_5.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format (default: text)",
    )


def _run_local_circumstances(arguments: argparse.Namespace) -> int:
    elements = _resolve_elements(arguments)
    observer = _resolve_observer(arguments)
    if arguments.engine == "skyfield":
        # Fail loudly rather than print a custom-core answer under a reference
        # label: the handoff forbids presenting one engine's result as another's.
        # Nothing is printed, because there is no result to print and a partial
        # document would be mistaken for one.
        SkyfieldEngine().star_local_circumstances(
            elements=elements,
            observer=observer,
            delta_t_seconds=arguments.delta_t_seconds,
        )
    result = _calculate(
        elements=elements,
        observer=observer,
        delta_t_seconds=arguments.delta_t_seconds,
        tolerance_hours=arguments.tolerance_hours,
        max_iterations=arguments.max_iterations,
    )
    comparison = _comparison_block(
        arguments.engine, elements=elements, observer=observer
    )
    if arguments.format == "json":
        print(
            json.dumps(
                _result_document(
                    elements=elements,
                    observer=observer,
                    delta_t_seconds=arguments.delta_t_seconds,
                    result=result,
                    comparison=comparison,
                ),
                indent=2,
            )
        )
    else:
        print(_format_result(elements, observer, result, comparison))
    return EXIT_OK


def _run_verify(arguments: argparse.Namespace) -> int:
    if arguments.example != "meeus-example-5":
        raise ValueError("no example selected; try: occultation verify meeus-example-5")
    fixture_path: Path = arguments.fixture
    document = _load_fixture(fixture_path)
    elements = star_elements_from_mapping(document)
    observer = observer_from_mapping(_section(document, "observer", fixture_path))
    event = _section(document, "event", fixture_path)
    delta_t_seconds = _number(event, "delta_t_seconds", fixture_path)
    expected = _section(document, "expected", fixture_path)
    tolerances = _tolerances(document)

    result = calculate_star_local_circumstances(
        elements=elements,
        observer=observer,
        delta_t_seconds=delta_t_seconds,
    )
    checks = _compare_with_expected(result, observer, expected, tolerances)
    matched = all(check["matched"] for check in checks)

    if arguments.format == "json":
        print(
            json.dumps(
                {
                    "example": "meeus-example-5",
                    "fixture": str(fixture_path),
                    "provenance": document.get("metadata", {}),
                    "result": _result_payload(result),
                    "checks": checks,
                    "verdict": "match" if matched else "mismatch",
                },
                indent=2,
            )
        )
    else:
        print(_format_verification(fixture_path, document, result, checks, matched))
    return EXIT_OK if matched else EXIT_MISMATCH


def _resolve_elements(arguments: argparse.Namespace) -> StarOccultationElements:
    """Turn either ``--elements`` or the inline options into domain elements."""
    inline = {
        "--reference-hour-td": arguments.reference_hour_td,
        "--star-declination-deg": arguments.star_declination_deg,
        "--greenwich-hour-angle-deg": arguments.greenwich_hour_angle_deg,
        "--greenwich-hour-angle-rate-deg-per-hour": (
            arguments.greenwich_hour_angle_rate_deg_per_hour
        ),
        "--shadow-x0": arguments.shadow_x0,
        "--shadow-x1": arguments.shadow_x1,
        "--shadow-x2": arguments.shadow_x2,
        "--shadow-y0": arguments.shadow_y0,
        "--shadow-y1": arguments.shadow_y1,
        "--shadow-y2": arguments.shadow_y2,
    }
    supplied = [name for name, value in inline.items() if value is not None]
    if arguments.elements is not None and supplied:
        raise ValueError(
            "--elements cannot be combined with the inline element options; "
            "use one or the other"
        )
    if arguments.elements is not None:
        return load_star_elements(arguments.elements)
    if not supplied:
        raise ValueError(
            "no elements supplied; pass --elements FILE or the inline element "
            "options (see --help)"
        )
    missing = [name for name, value in inline.items() if value is None]
    if missing:
        raise ValueError(
            "inline elements are incomplete; missing " + ", ".join(missing)
        )
    return StarOccultationElements(
        reference_hour_td=arguments.reference_hour_td,
        star_declination_deg=arguments.star_declination_deg,
        greenwich_hour_angle_at_reference_deg=arguments.greenwich_hour_angle_deg,
        greenwich_hour_angle_rate_deg_per_hour=(
            arguments.greenwich_hour_angle_rate_deg_per_hour
        ),
        moon_shadow_x=FundamentalPlanePolynomial(
            at_reference=arguments.shadow_x0,
            linear_rate_per_hour=arguments.shadow_x1,
            quadratic_term_per_hour_squared=arguments.shadow_x2,
        ),
        moon_shadow_y=FundamentalPlanePolynomial(
            at_reference=arguments.shadow_y0,
            linear_rate_per_hour=arguments.shadow_y1,
            quadratic_term_per_hour_squared=arguments.shadow_y2,
        ),
        moon_shadow_radius_earth_radii=arguments.shadow_radius_earth_radii,
    )


def _resolve_observer(arguments: argparse.Namespace) -> ObserverLocation:
    """Turn either ``--location`` or the inline options into a domain observer."""
    inline_supplied = (
        arguments.longitude_deg_east is not None or arguments.latitude_deg is not None
    )
    if arguments.location is not None and inline_supplied:
        raise ValueError(
            "--location cannot be combined with --longitude-deg-east or "
            "--latitude-deg; use one or the other"
        )
    if arguments.location is not None:
        return load_observer_location(arguments.location)
    if arguments.longitude_deg_east is None or arguments.latitude_deg is None:
        raise ValueError(
            "no observer supplied; pass --location FILE or both "
            "--longitude-deg-east and --latitude-deg"
        )
    return ObserverLocation(
        longitude_deg_east=arguments.longitude_deg_east,
        latitude_deg=arguments.latitude_deg,
        elevation_m=arguments.elevation_m,
    )


def _calculate(
    *,
    elements: StarOccultationElements,
    observer: ObserverLocation,
    delta_t_seconds: float,
    tolerance_hours: float,
    max_iterations: int,
) -> StarOccultationResult:
    return calculate_star_local_circumstances(
        elements=elements,
        observer=observer,
        delta_t_seconds=delta_t_seconds,
        convergence_tolerance_hours=tolerance_hours,
        max_iterations=max_iterations,
    )


def _comparison_block(
    engine: str,
    *,
    elements: StarOccultationElements,
    observer: ObserverLocation,
) -> dict[str, Any] | None:
    """Report the reference engine's availability without inventing a number.

    The probe passes the real elements and observer, so that the day the engine
    starts working this function needs no change. ``delta_t_seconds`` is 0.0 on
    purpose: the probe must not depend on a caller-supplied value it does not
    have, and today's placeholder ignores every argument.
    """
    if engine == "custom":
        return None
    try:
        SkyfieldEngine().star_local_circumstances(
            elements=elements,
            observer=observer,
            delta_t_seconds=0.0,
        )
    except ReferenceEngineUnavailable as error:
        reason = str(error)
    else:  # pragma: no cover - the placeholder always raises today
        reason = "available"
    return {
        "reference_engine": "skyfield",
        "status": "unavailable" if reason != "available" else "available",
        "reason": reason,
        "note": (
            "no difference is reported because the reference engine has not been "
            "implemented; the custom result above stands on its own"
        ),
    }


def _result_payload(result: StarOccultationResult) -> dict[str, Any]:
    """The result as a JSON-ready mapping, with the derived property included."""
    payload = asdict(result)
    payload["limb_clearance_in_moon_radii"] = result.limb_clearance_in_moon_radii
    return payload


def _result_document(
    *,
    elements: StarOccultationElements,
    observer: ObserverLocation,
    delta_t_seconds: float,
    result: StarOccultationResult,
    comparison: dict[str, Any] | None,
) -> dict[str, Any]:
    geocentric = calculate_geocentric_observer(observer)
    document: dict[str, Any] = {
        "engine": "custom",
        "algorithm": "Meeus, Astronomical Tables, printed pp. 224-226",
        "inputs": {
            "elements": {
                "reference_hour_td": elements.reference_hour_td,
                "star_declination_deg": elements.star_declination_deg,
                "greenwich_hour_angle_at_reference_deg": (
                    elements.greenwich_hour_angle_at_reference_deg
                ),
                "greenwich_hour_angle_rate_deg_per_hour": (
                    elements.greenwich_hour_angle_rate_deg_per_hour
                ),
                "moon_shadow_x": asdict(elements.moon_shadow_x),
                "moon_shadow_y": asdict(elements.moon_shadow_y),
                "moon_shadow_radius_earth_radii": (
                    elements.moon_shadow_radius_earth_radii
                ),
            },
            "observer": asdict(observer),
            "delta_t_seconds": delta_t_seconds,
        },
        "derived": {
            "rho_sin_geocentric_latitude": geocentric.rho_sin_geocentric_latitude,
            "rho_cos_geocentric_latitude": geocentric.rho_cos_geocentric_latitude,
        },
        "result": _result_payload(result),
    }
    if comparison is not None:
        document["comparison"] = comparison
    return document


def _format_result(
    elements: StarOccultationElements,
    observer: ObserverLocation,
    result: StarOccultationResult,
    comparison: dict[str, Any] | None,
) -> str:
    geocentric = calculate_geocentric_observer(observer)
    lines = [
        "Local circumstances of a lunar occultation of a star",
        "algorithm: Meeus, Astronomical Tables, printed pp. 224-226 (custom core)",
        (
            f"observer : {observer.latitude_deg:+.4f} deg N, "
            f"{observer.longitude_deg_east:+.4f} deg E (east-positive), "
            f"{observer.elevation_m:.0f} m"
        ),
        (
            f"elements : To = {elements.reference_hour_td:.6f} h TD, "
            f"d0 = {elements.star_declination_deg:+.4f} deg, "
            f"H0 = {elements.greenwich_hour_angle_at_reference_deg:.4f} deg, "
            f"H1 = {elements.greenwich_hour_angle_rate_deg_per_hour:.5f} deg/h, "
            f"k = {elements.moon_shadow_radius_earth_radii:.6f}"
        ),
        "",
        f"rho sin phi'          {geocentric.rho_sin_geocentric_latitude:+.6f}",
        f"rho cos phi'          {geocentric.rho_cos_geocentric_latitude:+.6f}",
        f"t (hours after To)    {result.hours_after_reference:+.6f}",
        f"To + t   TD           {_format_hours(result.dynamical_time_hour)}",
        f"         UT           {_format_hours(result.universal_time_hour)}",
        f"Delta (lunar radii)   {result.separation_in_moon_radii:+.4f}",
        f"limb clearance        {result.limb_clearance_in_moon_radii:+.4f}",
        f"P (position angle)    {result.position_angle_deg:.2f} deg",
        f"h (altitude)          {result.altitude_deg:+.2f} deg",
        f"occulted?             {'yes' if result.is_occultation else 'no'}",
        f"iterations            {result.iteration_count}",
    ]
    if comparison is not None:
        lines += [
            "",
            (
                f"comparison: reference engine '{comparison['reference_engine']}' is "
                f"{comparison['status']}"
            ),
            f"            {comparison['reason']}",
        ]
    return "\n".join(lines)


def _format_verification(
    fixture_path: Path,
    document: dict[str, Any],
    result: StarOccultationResult,
    checks: list[dict[str, Any]],
    matched: bool,
) -> str:
    metadata = document.get("metadata", {})
    lines = [
        str(metadata.get("example", "worked example")),
        f"source   : {metadata.get('source', 'unknown')}",
        (
            f"pages    : printed {metadata.get('printed_pages', '?')} "
            f"(PDF {metadata.get('pdf_pages', '?')})"
        ),
        f"fixture  : {fixture_path}",
        "",
        f"{'quantity':<34}{'this code':>14}{'printed':>14}{'difference':>14}",
        f"{'-' * 34}{'-' * 14}{'-' * 14}{'-' * 14}",
    ]
    for check in checks:
        lines.append(
            f"{check['quantity']:<34}"
            f"{check['calculated']:>14.6f}"
            f"{check['printed']:>14.6f}"
            f"{check['difference']:>+14.6f}"
        )
    lines += [
        "",
        f"iterations: {result.iteration_count}",
        (
            "VERDICT: matches the printed example within the tolerance its printed "
            "precision supports."
            if matched
            else "VERDICT: MISMATCH - see the differences above."
        ),
    ]
    return "\n".join(lines)


def _compare_with_expected(
    result: StarOccultationResult,
    observer: ObserverLocation,
    expected: dict[str, Any],
    tolerances: dict[str, float],
) -> list[dict[str, Any]]:
    """Compare every published quantity against this run, using real tolerances."""
    geocentric = calculate_geocentric_observer(observer)
    calculated = {
        "rho_sin_geocentric_latitude": geocentric.rho_sin_geocentric_latitude,
        "rho_cos_geocentric_latitude": geocentric.rho_cos_geocentric_latitude,
        "hours_after_reference": result.hours_after_reference,
        "dynamical_time_hour": result.dynamical_time_hour,
        "universal_time_hour": result.universal_time_hour,
        "separation_in_moon_radii": result.separation_in_moon_radii,
        "limb_clearance_in_moon_radii": result.limb_clearance_in_moon_radii,
        "position_angle_deg": result.position_angle_deg,
        "altitude_deg": result.altitude_deg,
    }
    checks: list[dict[str, Any]] = []
    for quantity, printed in expected.items():
        if quantity not in calculated:
            continue
        value = calculated[quantity]
        tolerance = tolerances.get(quantity, 0.0)
        difference = value - float(printed)
        checks.append(
            {
                "quantity": quantity,
                "calculated": value,
                "printed": float(printed),
                "difference": difference,
                "tolerance": tolerance,
                # ``abs_tol`` alone is not enough: the default ``rel_tol`` of
                # 1e-9 would reject an exact match on a value of 10.455608.
                "matched": abs(difference) <= tolerance,
            }
        )
    printed_occulted = bool(expected.get("is_occultation"))
    checks.append(
        {
            "quantity": "is_occultation",
            "calculated": float(result.is_occultation),
            "printed": float(printed_occulted),
            "difference": 0.0,
            "tolerance": 0.0,
            "matched": result.is_occultation == printed_occulted,
        }
    )
    return checks


def _load_fixture(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise ElementsFileError(f"{path}: no such file") from error
    except OSError as error:
        raise ElementsFileError(f"{path}: cannot be read ({error})") from error
    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise ElementsFileError(
            f"{path}: not valid JSON (line {error.lineno}, column {error.colno}: "
            f"{error.msg})"
        ) from error
    if not isinstance(document, dict):
        raise ElementsFileError(
            f"{path}: the top level of the document must be an object"
        )
    return document


def _section(document: dict[str, Any], name: str, path: Path) -> dict[str, Any]:
    section = document.get(name)
    if not isinstance(section, dict):
        raise ElementsFileError(f"{path}: '{name}' is missing or is not an object")
    return section


def _number(section: dict[str, Any], key: str, path: Path) -> float:
    if key not in section:
        raise ElementsFileError(f"{path}: '{key}' is missing")
    value = section[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ElementsFileError(
            f"{path}: '{key}' must be a number, not {type(value).__name__}"
        )
    return float(value)


def _tolerances(document: dict[str, Any]) -> dict[str, float]:
    """Read the fixture's tolerances, falling back to the documented defaults."""
    metadata = document.get("metadata")
    if not isinstance(metadata, dict):
        return dict(DEFAULT_TOLERANCES)
    tolerances = metadata.get("tolerances")
    if not isinstance(tolerances, dict):
        return dict(DEFAULT_TOLERANCES)
    merged = dict(DEFAULT_TOLERANCES)
    for key, value in tolerances.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            merged[str(key)] = float(value)
    return merged


def _format_hours(hours: float) -> str:
    """Render hours as ``10h 27m 20s``, the way the book prints instants."""
    total_seconds = round(hours * 3600.0)
    whole_hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{whole_hours:02d}h {minutes:02d}m {seconds:02d}s"


if __name__ == "__main__":
    sys.exit(main())
