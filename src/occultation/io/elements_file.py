"""Load lunar-occultation elements from a stored or supplied representation.

The canonical on-disk format is JSON. It is deliberately project-native rather
than a published standard: every key carries its unit and time scale in its
name, exactly as the domain model does. The schema is::

    {
      "metadata": { ... provenance, free-form ... },
      "event":    { "reference_hour_td": 10.0, "delta_t_seconds": 65.0 },
      "elements": {
        "star_declination_deg": 11.9694,
        "greenwich_hour_angle_at_reference_deg": 156.6836,
        "greenwich_hour_angle_rate_deg_per_hour": 15.04107,
        "moon_shadow_radius_earth_radii": 0.272495,
        "moon_shadow_x": { "at_reference": ..., "linear_rate_per_hour": ...,
                           "quadratic_term_per_hour_squared": ... },
        "moon_shadow_y": { ... }
      },
      "observer": { "longitude_deg_east": ..., "latitude_deg": ...,
                    "elevation_m": ... },
      "expected": { ... optional published values, used by ``verify`` ... }
    }

``event`` and ``observer`` are optional here because the command line may supply
them instead; :func:`star_elements_from_mapping` reads only ``elements``.
"""

import json
from pathlib import Path
from typing import Any

from occultation.domain.occultation import (
    FundamentalPlanePolynomial,
    StarOccultationElements,
)

#: Keys of the ``elements`` object, in the order they are reported when missing.
_ELEMENT_KEYS = (
    "star_declination_deg",
    "greenwich_hour_angle_at_reference_deg",
    "greenwich_hour_angle_rate_deg_per_hour",
    "moon_shadow_x",
    "moon_shadow_y",
)

_POLYNOMIAL_KEYS = (
    "at_reference",
    "linear_rate_per_hour",
    "quadratic_term_per_hour_squared",
)


class ElementsFileError(ValueError):
    """Raised when an elements document is missing or malformed."""


def load_star_elements(path: Path) -> StarOccultationElements:
    """Read a JSON elements document from ``path``.

    Only the ``elements`` object is required; ``metadata``, ``event``,
    ``observer`` and ``expected`` are ignored by this function.
    """
    document = _load_json_document(path)
    if not isinstance(document, dict):
        raise ElementsFileError(
            f"{path}: the top level of the document must be an object"
        )
    return star_elements_from_mapping(document)


def star_elements_from_mapping(data: dict[str, Any]) -> StarOccultationElements:
    """Build elements from a mapping that has an ``elements`` object.

    Accepts either a whole document or an ``elements`` object directly, so the
    same validator serves the file path and the inline-parameter path.
    """
    elements = data.get("elements", data)
    if not isinstance(elements, dict):
        raise ElementsFileError("'elements' must be an object")
    missing = [key for key in _ELEMENT_KEYS if key not in elements]
    if missing:
        raise ElementsFileError(
            "'elements' is missing required key(s): " + ", ".join(missing)
        )
    return StarOccultationElements(
        reference_hour_td=_required_number(data, "event", "reference_hour_td"),
        star_declination_deg=_number(elements, "star_declination_deg"),
        greenwich_hour_angle_at_reference_deg=_number(
            elements, "greenwich_hour_angle_at_reference_deg"
        ),
        greenwich_hour_angle_rate_deg_per_hour=_number(
            elements, "greenwich_hour_angle_rate_deg_per_hour"
        ),
        moon_shadow_x=_polynomial(elements, "moon_shadow_x"),
        moon_shadow_y=_polynomial(elements, "moon_shadow_y"),
        moon_shadow_radius_earth_radii=_number(
            elements, "moon_shadow_radius_earth_radii", default=0.272495
        ),
    )


def _load_json_document(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise ElementsFileError(f"{path}: no such file") from error
    except OSError as error:
        raise ElementsFileError(f"{path}: cannot be read ({error})") from error
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise ElementsFileError(
            f"{path}: not valid JSON (line {error.lineno}, column {error.colno}: {error.msg})"
        ) from error


def _required_number(data: dict[str, Any], section: str, key: str) -> float:
    """Read a number that must be present in ``data[section]``."""
    if section not in data:
        raise ElementsFileError(f"'{section}' is missing")
    return _number(data[section], key)


def _number(section: Any, key: str, *, default: float | None = None) -> float:
    if not isinstance(section, dict):
        raise ElementsFileError("expected an object")
    if key not in section:
        if default is None:
            raise ElementsFileError(f"'{key}' is missing")
        return default
    value = section[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ElementsFileError(f"'{key}' must be a number, not {type(value).__name__}")
    return float(value)


def _polynomial(elements: dict[str, Any], key: str) -> FundamentalPlanePolynomial:
    section = elements[key]
    if not isinstance(section, dict):
        raise ElementsFileError(f"'{key}' must be an object")
    missing = [name for name in _POLYNOMIAL_KEYS if name not in section]
    if missing:
        raise ElementsFileError(
            f"'{key}' is missing required key(s): " + ", ".join(missing)
        )
    return FundamentalPlanePolynomial(
        at_reference=_number(section, "at_reference"),
        linear_rate_per_hour=_number(section, "linear_rate_per_hour"),
        quadratic_term_per_hour_squared=_number(
            section, "quadratic_term_per_hour_squared"
        ),
    )
