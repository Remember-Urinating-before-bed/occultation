"""Tests for the elements-file loader."""

import json
from pathlib import Path

import pytest

from occultation.io.elements_file import (
    ElementsFileError,
    load_star_elements,
    star_elements_from_mapping,
)

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "meeus_regulus_1999.json"


def test_loads_the_meeus_regulus_fixture() -> None:
    elements = load_star_elements(FIXTURE_PATH)

    assert elements.reference_hour_td == 10.0
    assert elements.star_declination_deg == 11.9694
    assert elements.greenwich_hour_angle_at_reference_deg == 156.6836
    assert elements.greenwich_hour_angle_rate_deg_per_hour == 15.04107
    assert elements.moon_shadow_x.at_reference == 0.22151
    assert elements.moon_shadow_x.linear_rate_per_hour == 0.55549
    assert elements.moon_shadow_x.quadratic_term_per_hour_squared == 0.0
    assert elements.moon_shadow_y.at_reference == 0.19947
    assert elements.moon_shadow_y.linear_rate_per_hour == -0.15258
    assert elements.moon_shadow_y.quadratic_term_per_hour_squared == -1e-5
    assert elements.moon_shadow_radius_earth_radii == 0.272495


def test_the_json_fixture_agrees_with_the_toml_fixture() -> None:
    """The two fixtures are twins; a transcription slip in either one must fail."""
    import tomllib

    toml_path = FIXTURE_PATH.with_suffix(".toml")
    with toml_path.open("rb") as toml_file:
        toml_document = tomllib.load(toml_file)
    json_document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert json_document["observer"] == toml_document["observer"]
    assert json_document["event"] == toml_document["event"]
    assert json_document["elements"] == toml_document["elements"]
    assert json_document["expected"] == toml_document["expected"]


def test_missing_file_is_reported_with_its_path() -> None:
    with pytest.raises(ElementsFileError) as error:
        load_star_elements(Path("/nonexistent/elements.json"))

    assert "no such file" in str(error.value)


def test_malformed_json_is_reported_with_its_position(tmp_path: Path) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text('{"elements": }', encoding="utf-8")

    with pytest.raises(ElementsFileError) as error:
        load_star_elements(broken)

    assert "not valid JSON" in str(error.value)
    assert "line 1" in str(error.value)


def test_a_missing_element_key_is_named(tmp_path: Path) -> None:
    document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    del document["elements"]["moon_shadow_y"]
    incomplete = tmp_path / "incomplete.json"
    incomplete.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ElementsFileError) as error:
        load_star_elements(incomplete)

    assert "moon_shadow_y" in str(error.value)


def test_a_missing_event_section_is_reported() -> None:
    document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    del document["event"]

    with pytest.raises(ElementsFileError) as error:
        star_elements_from_mapping(document)

    assert "'event' is missing" in str(error.value)


def test_a_non_numeric_value_is_rejected() -> None:
    document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    document["elements"]["star_declination_deg"] = "11.9694"

    with pytest.raises(ElementsFileError) as error:
        star_elements_from_mapping(document)

    assert "must be a number" in str(error.value)


def test_an_elements_mapping_is_accepted_on_its_own() -> None:
    """The inline command-line path passes an ``elements`` object directly."""
    document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    elements = star_elements_from_mapping(
        {"elements": document["elements"], "event": document["event"]}
    )

    assert elements.moon_shadow_y.linear_rate_per_hour == -0.15258
