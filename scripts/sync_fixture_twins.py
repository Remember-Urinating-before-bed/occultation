"""Keep a fixture's JSON and TOML twins in step, in either direction.

Several fixtures in this repository exist twice: a ``.toml`` twin that the
regression tests read (via :mod:`tomllib`) and a ``.json`` twin that is the
canonical on-disk format for the command line (see
``occultation.io.elements_file``). A transcription slip in either file is caught
by ``tests/unit/test_elements_file.py``, but fixing such a slip by hand means
editing the same numbers in two places. This script does the copying instead.

``scripts`` never run at application runtime, and neither does this one.

Usage::

    # JSON is the source of truth: rewrite the .toml twin from it
    uv run python scripts/sync_fixture_twins.py tests/fixtures/meeus_saturn_2024_2025 --from json

    # TOML is the source of truth
    uv run python scripts/sync_fixture_twins.py tests/fixtures/meeus_saturn_2024_2025 --from toml

    # Whichever twin was saved most recently wins (the default)
    uv run python scripts/sync_fixture_twins.py tests/fixtures/meeus_saturn_2024_2025

    # Write nothing; just report whether the twins agree (an exit code for CI)
    uv run python scripts/sync_fixture_twins.py tests/fixtures/meeus_saturn_2024_2025 --check

    # Every pair in tests/fixtures/
    uv run python scripts/sync_fixture_twins.py --all --check

Pass ``--stem`` instead of a path to name a pair by its shared stem, e.g.
``--stem meeus_saturn_2024_2025``; the twins are looked up in
``tests/fixtures/``.

The TOML writer is deliberately small and self-contained (no ``tomli-w``
dependency): it emits nested tables and scalar values, which is all these
fixtures contain. Any leading ``#`` comment block already at the top of the
target ``.toml`` is preserved, so provenance notes are not lost on a rewrite.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import tomllib
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = REPOSITORY_ROOT / "tests" / "fixtures"

TOML_SUFFIX = ".toml"
JSON_SUFFIX = ".json"


class TwinSyncError(RuntimeError):
    """Raised when a twin pair cannot be found or cannot be reconciled."""


def _toml_document(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _json_document(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


# --- TOML writing ------------------------------------------------------------


def _format_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value)  # a TOML basic string is JSON-string-compatible
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"cannot write a non-finite float to TOML: {value!r}")
        return repr(value)
    raise TwinSyncError(f"cannot write a {type(value).__name__} to TOML: {value!r}")


def _is_table(value: Any) -> bool:
    return isinstance(value, dict)


def _emit_table(lines: list[str], prefix: str, table: dict[str, Any]) -> None:
    """Emit ``table`` as TOML, scalars before sub-tables.

    A table that holds only sub-tables gets no header of its own: ``[a.b]``
    already creates ``a``, and the hand-written fixtures in ``tests/fixtures``
    are spelled that way, so emitting the extra ``[a]`` line would put a diff in
    every sync that says nothing about the data.
    """
    scalars = {key: value for key, value in table.items() if not _is_table(value)}
    sub_tables = {key: value for key, value in table.items() if _is_table(value)}

    if prefix and (scalars or not sub_tables):
        lines.append(f"[{prefix}]")
    for key, value in scalars.items():
        lines.append(f"{key} = {_format_scalar(value)}")
    if prefix and scalars:
        lines.append("")

    for key, value in sub_tables.items():
        child = f"{prefix}.{key}" if prefix else key
        _emit_table(lines, child, value)


def _preserved_header(path: Path) -> str:
    """Return the leading ``#`` comment block of ``path``, or ``''``."""
    if not path.exists():
        return ""
    header_lines: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            header_lines.append(line)
        elif line.strip() == "" and not header_lines:
            continue
        else:
            break
    if not header_lines:
        return ""
    return "\n".join(header_lines) + "\n"


def _toml_text(document: dict[str, Any], header: str) -> str:
    lines: list[str] = []
    if header:
        lines.append(header)
    # Top-level scalars first, then each top-level table.
    top_scalars = {k: v for k, v in document.items() if not _is_table(v)}
    for key, value in top_scalars.items():
        lines.append(f"{key} = {_format_scalar(value)}")
    if top_scalars:
        lines.append("")
    for key, value in document.items():
        if _is_table(value):
            _emit_table(lines, key, value)
    text = "\n".join(lines).rstrip("\n") + "\n"
    return text


# --- reconciliation ----------------------------------------------------------


def _twin_paths(stem_or_path: str, *, fixtures_dir: Path) -> tuple[Path, Path]:
    """Resolve a stem or a path to the ``(toml_path, json_path)`` pair.

    A bare stem is looked up under ``fixtures_dir``; a path with a directory
    component (or an absolute path), with or without a ``.toml``/``.json``
    suffix, is used as given.
    """
    candidate = Path(stem_or_path)
    has_directory = candidate.is_absolute() or candidate.parent != Path(".")
    base = (
        candidate.with_suffix("")
        if candidate.suffix in (TOML_SUFFIX, JSON_SUFFIX)
        else candidate
    )
    if not has_directory:
        base = fixtures_dir / base.name
    return base.with_suffix(TOML_SUFFIX), base.with_suffix(JSON_SUFFIX)


def _all_stems(fixtures_dir: Path) -> list[str]:
    stems = {
        path.stem
        for path in fixtures_dir.glob(f"*{JSON_SUFFIX}")
        if path.with_suffix(TOML_SUFFIX).exists()
    }
    return sorted(stems)


def _resolve_source(toml_path: Path, json_path: Path, direction: str) -> str:
    if direction in ("json", "toml"):
        return direction
    if not toml_path.exists():
        return "json"
    if not json_path.exists():
        return "toml"
    return "json" if json_path.stat().st_mtime >= toml_path.stat().st_mtime else "toml"


def _documents_agree(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return left == right


def sync_one(
    toml_path: Path,
    json_path: Path,
    *,
    direction: str,
    check: bool,
) -> tuple[bool, str]:
    """Reconcile one twin pair. Returns ``(changed_or_would_change, message)``.

    The two files are compared as *parsed documents*, never as text: a TOML twin
    and a JSON twin can never be textually equal, so the question is always
    whether they carry the same data.
    """
    if not toml_path.exists() and not json_path.exists():
        raise TwinSyncError(f"neither {toml_path.name} nor {json_path.name} exists")

    source = _resolve_source(toml_path, json_path, direction)
    if source == "json":
        if not json_path.exists():
            raise TwinSyncError(f"source {json_path.name} does not exist")
        document = _json_document(json_path)
        target = toml_path
        text = _toml_text(document, _preserved_header(toml_path))
    else:
        if not toml_path.exists():
            raise TwinSyncError(f"source {toml_path.name} does not exist")
        document = _toml_document(toml_path)
        target = json_path
        text = json.dumps(document, indent=2) + "\n"

    if check:
        if not target.exists():
            return True, f"{toml_path.stem}: {target.name} is MISSING (from {source})"
        target_document = (
            _toml_document(toml_path)
            if target == toml_path
            else _json_document(json_path)
        )
        if _documents_agree(document, target_document):
            return False, f"{toml_path.stem}: twins agree"
        return (
            True,
            f"{toml_path.stem}: twins DIFFER (would rewrite {target.name} from {source})",
        )

    if target.exists() and target.read_text(encoding="utf-8") == text:
        return False, f"{toml_path.stem}: {target.name} already matches {source}"
    target.write_text(text, encoding="utf-8")
    return True, f"{toml_path.stem}: wrote {target.name} from {source}"


def _verify_pair_agrees(toml_path: Path, json_path: Path) -> bool:
    """True when both existing twins parse to the same data."""
    if not (toml_path.exists() and json_path.exists()):
        return False
    return _documents_agree(_toml_document(toml_path), _json_document(json_path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "stem",
        nargs="?",
        help="fixture stem or .toml/.json path (e.g. tests/fixtures/meeus_saturn_2024_2025)",
    )
    parser.add_argument(
        "--stem",
        dest="stem_option",
        help="fixture stem, resolved under tests/fixtures/",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="operate on every JSON/TOML pair in tests/fixtures/",
    )
    parser.add_argument(
        "--from",
        dest="direction",
        choices=("auto", "json", "toml"),
        default="auto",
        help="which twin is the source of truth (default: the newer file)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="report only; write nothing and exit non-zero if a pair is out of step",
    )
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        default=FIXTURES_DIR,
        help=f"directory for stem lookups (default: {FIXTURES_DIR})",
    )
    arguments = parser.parse_args(argv)

    name = arguments.stem_option or arguments.stem
    if arguments.all:
        stems = _all_stems(arguments.fixtures_dir)
        if not stems:
            print("no twin pairs found", file=sys.stderr)
            return 1
    elif name:
        stems = [name]
    else:
        parser.error("give a fixture stem, or --all")

    exit_code = 0
    for stem in stems:
        toml_path, json_path = _twin_paths(stem, fixtures_dir=arguments.fixtures_dir)
        try:
            would_change, message = sync_one(
                toml_path,
                json_path,
                direction=arguments.direction,
                check=arguments.check,
            )
        except TwinSyncError as error:
            print(f"{stem}: {error}", file=sys.stderr)
            exit_code = 1
            continue
        print(message)
        if arguments.check:
            if would_change:
                exit_code = 1
            elif not _verify_pair_agrees(toml_path, json_path):
                print(
                    f"{stem}: textually in step but the parsed data differs",
                    file=sys.stderr,
                )
                exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
