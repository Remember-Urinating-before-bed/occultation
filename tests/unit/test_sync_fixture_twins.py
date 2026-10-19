"""Tests for the JSON/TOML twin-sync tool.

The tool exists so a fixture's two representations can be reconciled in one
command, in either direction, without hand-editing the same numbers twice. The
tests cover the two properties that matter: a JSON-sourced rewrite preserves the
provenance header comment, and ``--check`` reports rather than writes.
"""

import importlib.util
import json
import tomllib
from pathlib import Path
from types import ModuleType

import pytest

REPOSITORY_ROOT = Path(__file__).parents[2]


def _load_sync_module() -> ModuleType:
    """Import ``scripts/sync_fixture_twins.py`` without a ``scripts`` package.

    ``scripts/`` is a plain directory of tools, not an installed package, so it
    is loaded by path rather than added to ``sys.path``.
    """
    module_path = REPOSITORY_ROOT / "scripts" / "sync_fixture_twins.py"
    spec = importlib.util.spec_from_file_location("sync_fixture_twins", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_sync = _load_sync_module()
_format_scalar = _sync._format_scalar
_preserved_header = _sync._preserved_header
_toml_text = _sync._toml_text
sync_one = _sync.sync_one


def _write_pair(tmp_path: Path, document: dict) -> tuple[Path, Path]:
    json_path = tmp_path / "sample.json"
    toml_path = tmp_path / "sample.toml"
    json_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    toml_path.write_text(
        "# provenance header\n\n[metadata]\nscaffold = true\n", encoding="utf-8"
    )
    return toml_path, json_path


def test_a_json_sourced_rewrite_preserves_the_header_comment(tmp_path: Path) -> None:
    document = {
        "metadata": {"scaffold": True, "note": "kept"},
        "events": {"2024-01-01": {"reference_hour_td": 3, "elements": {"d": 1.5}}},
    }
    toml_path, json_path = _write_pair(tmp_path, document)

    changed, message = sync_one(toml_path, json_path, direction="json", check=False)

    assert changed is True
    assert "wrote" in message
    text = toml_path.read_text(encoding="utf-8")
    assert text.startswith("# provenance header\n")
    # The numbers arrive unchanged.
    assert tomllib.loads(text) == document


def test_a_toml_sourced_rewrite_updates_the_json(tmp_path: Path) -> None:
    document = {"metadata": {"scaffold": False}, "events": {}}
    toml_path, json_path = _write_pair(tmp_path, document)
    toml_path.write_text(
        "[metadata]\nscaffold = false\n\n[events.2024-01-01]\nreference_hour_td = 5\n",
        encoding="utf-8",
    )

    changed, _ = sync_one(toml_path, json_path, direction="toml", check=False)

    assert changed is True
    assert json.loads(json_path.read_text(encoding="utf-8")) == {
        "metadata": {"scaffold": False},
        "events": {"2024-01-01": {"reference_hour_td": 5}},
    }


def test_check_reports_a_difference_without_writing(tmp_path: Path) -> None:
    document = {"metadata": {"scaffold": True}, "events": {}}
    toml_path, json_path = _write_pair(tmp_path, document)
    before = toml_path.read_text(encoding="utf-8")

    changed, message = sync_one(toml_path, json_path, direction="json", check=True)

    assert changed is True
    assert "DIFFER" in message
    assert toml_path.read_text(encoding="utf-8") == before


def test_check_on_an_already_in_step_pair_is_a_no_op(tmp_path: Path) -> None:
    document = {"metadata": {"scaffold": True}, "events": {}}
    toml_path, json_path = _write_pair(tmp_path, document)
    sync_one(toml_path, json_path, direction="json", check=False)

    changed, message = sync_one(toml_path, json_path, direction="json", check=True)

    assert changed is False
    assert "agree" in message


def test_non_finite_scalars_are_refused() -> None:
    """A NaN or infinity is not a value the CLI would read back, so refuse it."""
    with pytest.raises(ValueError):
        _format_scalar(float("nan"))


def test_preserved_header_ignores_leading_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "x.toml"
    path.write_text("\n\n# one\n# two\nkey = 1\n", encoding="utf-8")

    assert _preserved_header(path) == "# one\n# two\n"


def test_toml_text_round_trips_nested_tables() -> None:
    document = {
        "metadata": {"scaffold": False},
        "events": {"d": {"elements": {"x": 0.5}, "expected": {"is_visible": True}}},
    }

    text = _toml_text(document, "# header\n")

    assert tomllib.loads(text) == document
