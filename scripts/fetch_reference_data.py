"""Fetch or verify the external datasets recorded in ``data/manifest.json``.

The project handoff (§3.3) requires that external scientific data is downloaded
deliberately, stored locally, recorded in a manifest, and *never* fetched at
application runtime. This script is the deliberate, offline step: it is run by a
human (or a dedicated CI ``data`` job), not by the almanac calculation.

Two subcommands:

``fetch``
    Print, for every manifest entry that has a ``source`` URL, the exact
    ``curl`` command that would download it. Nothing is downloaded unless the
    entry is a plain URL dataset; a ``reference-validation`` entry is a
    human-saved snapshot and is only reported, never fetched. Pass ``--download``
    to actually run the downloads into ``data/external/``.

``verify``
    Recompute the SHA-256 of every dataset that has a real checksum and compare
    it with the manifest. A ``PLACEHOLDER`` checksum is reported as
    ``unrecorded`` and is a failure unless ``--allow-unrecorded`` is given, so a
    missing checksum cannot pass silently.

Run it with::

    uv run python scripts/fetch_reference_data.py verify
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPOSITORY_ROOT / "data" / "manifest.json"
EXTERNAL_DIR = REPOSITORY_ROOT / "data" / "external"

PLACEHOLDER_CHECKSUM = "PLACEHOLDER"


def _load_manifest(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise TypeError(f"{path}: the top level of the manifest must be an object")
    datasets = document.get("datasets")
    if not isinstance(datasets, list):
        raise TypeError(f"{path}: 'datasets' must be a list")
    return document


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fetch(datasets: list[dict[str, Any]], *, download: bool) -> int:
    exit_code = 0
    for dataset in datasets:
        name = dataset.get("name", "<unnamed>")
        source = dataset.get("source")
        kind = dataset.get("kind", "url")
        if kind == "reference-validation":
            print(
                f"{name}: human-saved snapshot, not fetched (see {dataset.get('path')})"
            )
            continue
        if not source:
            print(f"{name}: no source URL recorded", file=sys.stderr)
            exit_code = 1
            continue
        destination = EXTERNAL_DIR / Path(str(dataset.get("path", name))).name
        command = [
            "curl",
            "--fail",
            "--location",
            "--output",
            str(destination),
            str(source),
        ]
        print(" ".join(command))
        if download:
            destination.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(command, check=True)
            print(f"{name}: downloaded {_sha256(destination)}")
    return exit_code


def _verify(datasets: list[dict[str, Any]], *, allow_unrecorded: bool) -> int:
    exit_code = 0
    for dataset in datasets:
        name = dataset.get("name", "<unnamed>")
        recorded = str(dataset.get("sha256", PLACEHOLDER_CHECKSUM))
        path_value = dataset.get("path")
        if not path_value:
            print(f"{name}: no path recorded", file=sys.stderr)
            exit_code = 1
            continue
        path = REPOSITORY_ROOT / str(path_value)
        if not path.exists():
            print(f"{name}: missing file {path}", file=sys.stderr)
            exit_code = 1
            continue
        actual = _sha256(path)
        if recorded == PLACEHOLDER_CHECKSUM:
            print(f"{name}: unrecorded checksum (actual {actual})")
            if not allow_unrecorded:
                exit_code = 1
            continue
        if actual == recorded:
            print(f"{name}: ok {actual}")
        else:
            print(
                f"{name}: MISMATCH recorded {recorded} actual {actual}",
                file=sys.stderr,
            )
            exit_code = 1
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    subparsers = parser.add_subparsers(dest="command", required=True)
    fetch_parser = subparsers.add_parser("fetch", help="show or run the downloads")
    fetch_parser.add_argument(
        "--download", action="store_true", help="actually download into data/external/"
    )
    verify_parser = subparsers.add_parser(
        "verify", help="check every recorded checksum"
    )
    verify_parser.add_argument(
        "--allow-unrecorded",
        action="store_true",
        help="treat a PLACEHOLDER checksum as a warning rather than a failure",
    )
    arguments = parser.parse_args(argv)

    document = _load_manifest(arguments.manifest)
    datasets = document["datasets"]
    if arguments.command == "fetch":
        return _fetch(datasets, download=arguments.download)
    return _verify(datasets, allow_unrecorded=arguments.allow_unrecorded)


if __name__ == "__main__":
    sys.exit(main())
