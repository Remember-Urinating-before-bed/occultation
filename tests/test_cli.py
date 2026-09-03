"""Tests for the command-line entry point."""

from importlib.metadata import entry_points

import pytest

from occultation.cli import build_parser, main


def test_cli_program_name() -> None:
    parser = build_parser()

    assert parser.prog == "occultation"


def console_script_target() -> str | None:
    """Return the ``module:attr`` the installed ``occultation`` script points at."""
    for entry_point in entry_points(group="console_scripts"):
        if entry_point.name == "occultation":
            return entry_point.value
    return None


def test_console_script_resolves_to_cli_main() -> None:
    """Regression guard for defect D1.

    The scaffold declared ``occultation = "occultation:main"``, which resolved to the
    hello-world stub in the package ``__init__`` instead of the real CLI. That stub is
    gone, so this assertion is backed by ``test_main_prints_usage`` below.
    """
    assert console_script_target() == "occultation.cli:main"


def test_main_prints_usage(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--help`` must reach the real parser, not the deleted hello stub."""
    monkeypatch.setattr("sys.argv", ["occultation", "--help"])

    with pytest.raises(SystemExit) as exit_info:
        main()

    captured = capsys.readouterr()
    assert exit_info.value.code == 0
    assert captured.out.startswith("usage: occultation")
    assert "Hello from occultation!" not in captured.out


def test_main_reports_version(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["occultation", "--version"])

    with pytest.raises(SystemExit) as exit_info:
        main()

    captured = capsys.readouterr()
    assert exit_info.value.code == 0
    assert captured.out.strip() == "0.1.0"
