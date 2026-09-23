"""Tests for the observer-location loader."""

import json
from pathlib import Path

import pytest

from occultation.io.location_file import (
    LocationFileError,
    load_observer_location,
    observer_from_mapping,
)

REPOSITORY_ROOT = Path(__file__).parents[2]
HONG_KONG_TOML = REPOSITORY_ROOT / "config" / "locations" / "hong_kong.toml"


def test_loads_the_hong_kong_toml_site() -> None:
    """The configuration file that already existed must now actually be read."""
    observer = load_observer_location(HONG_KONG_TOML)

    assert observer.latitude_deg == 22.3020
    assert observer.longitude_deg_east == 114.1743
    assert observer.elevation_m == 0.0


def test_loads_the_same_site_from_json(tmp_path: Path) -> None:
    document = {
        "name": "Hong Kong",
        "latitude_deg": 22.3020,
        "longitude_deg_east": 114.1743,
        "elevation_m": 0.0,
    }
    json_path = tmp_path / "hong_kong.json"
    json_path.write_text(json.dumps(document), encoding="utf-8")

    assert load_observer_location(json_path) == load_observer_location(HONG_KONG_TOML)


def test_an_unsupported_suffix_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "site.yaml"
    path.write_text("latitude_deg: 22.3", encoding="utf-8")

    with pytest.raises(LocationFileError) as error:
        load_observer_location(path)

    assert "unsupported location format" in str(error.value)


def test_missing_file_is_reported_with_its_path() -> None:
    with pytest.raises(LocationFileError) as error:
        load_observer_location(Path("/nonexistent/site.toml"))

    assert "no such file" in str(error.value)


def test_malformed_toml_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "site.toml"
    path.write_text("latitude_deg = ", encoding="utf-8")

    with pytest.raises(LocationFileError) as error:
        load_observer_location(path)

    assert "not valid TOML" in str(error.value)


def test_a_missing_key_is_named() -> None:
    with pytest.raises(LocationFileError) as error:
        observer_from_mapping({"latitude_deg": 22.302})

    assert "longitude_deg_east" in str(error.value)


def test_elevation_defaults_to_sea_level() -> None:
    observer = observer_from_mapping(
        {"latitude_deg": 22.302, "longitude_deg_east": 114.1743}
    )

    assert observer.elevation_m == 0.0
