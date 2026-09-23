"""Load an observer location from a stored or supplied representation.

Two on-disk formats are accepted, chosen by file suffix:

- ``.json`` — the canonical project format;
- ``.toml`` — kept because ``config/locations/hong_kong.toml`` already exists
  in that format and is the documented Hong Kong site.

Both carry the same three keys the domain model needs. Extra keys that the
configuration files legitimately hold (``name``, ``timezone``, ``datum``) are
ignored rather than rejected.
"""

import json
import tomllib
from pathlib import Path
from typing import Any

from occultation.domain.observer import ObserverLocation


class LocationFileError(ValueError):
    """Raised when a location document is missing or malformed."""


def load_observer_location(path: Path) -> ObserverLocation:
    """Read an observer location from ``path``, dispatching on the suffix."""
    suffix = path.suffix.lower()
    if suffix == ".json":
        document = _load_json(path)
    elif suffix == ".toml":
        document = _load_toml(path)
    else:
        raise LocationFileError(
            f"{path}: unsupported location format '{suffix or path.name}'; "
            "use .json or .toml"
        )
    if not isinstance(document, dict):
        raise LocationFileError(
            f"{path}: the top level of the document must be an object"
        )
    return observer_from_mapping(document)


def observer_from_mapping(data: dict[str, Any]) -> ObserverLocation:
    """Build an :class:`ObserverLocation` from a mapping of three numbers."""
    return ObserverLocation(
        longitude_deg_east=_number(data, "longitude_deg_east"),
        latitude_deg=_number(data, "latitude_deg"),
        elevation_m=_number(data, "elevation_m", default=0.0),
    )


def _load_json(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise LocationFileError(f"{path}: no such file") from error
    except OSError as error:
        raise LocationFileError(f"{path}: cannot be read ({error})") from error
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise LocationFileError(
            f"{path}: not valid JSON (line {error.lineno}, column {error.colno}: {error.msg})"
        ) from error


def _load_toml(path: Path) -> Any:
    try:
        with path.open("rb") as toml_file:
            return tomllib.load(toml_file)
    except FileNotFoundError as error:
        raise LocationFileError(f"{path}: no such file") from error
    except OSError as error:
        raise LocationFileError(f"{path}: cannot be read ({error})") from error
    except tomllib.TOMLDecodeError as error:
        raise LocationFileError(f"{path}: not valid TOML ({error})") from error


def _number(section: Any, key: str, *, default: float | None = None) -> float:
    if not isinstance(section, dict):
        raise LocationFileError("expected an object")
    if key not in section:
        if default is None:
            raise LocationFileError(f"'{key}' is missing")
        return default
    value = section[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LocationFileError(f"'{key}' must be a number, not {type(value).__name__}")
    return float(value)
