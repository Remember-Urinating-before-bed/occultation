"""Tests for the command-line entry point."""

import json
from importlib.metadata import entry_points
from pathlib import Path

import pytest

from occultation.cli import (
    EXIT_MISMATCH,
    EXIT_OK,
    EXIT_REFERENCE_UNAVAILABLE,
    EXIT_USAGE,
    build_parser,
    main,
)

REPOSITORY_ROOT = Path(__file__).parents[1]
ELEMENTS_FIXTURE = REPOSITORY_ROOT / "tests" / "fixtures" / "meeus_regulus_1999.json"
HONG_KONG_LOCATION = REPOSITORY_ROOT / "config" / "locations" / "hong_kong.toml"


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


def test_main_without_a_command_prints_help(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """No arguments is a usage request, not an error: exit 0 and print help."""
    exit_code = main([])

    captured = capsys.readouterr()
    assert exit_code == EXIT_OK
    assert captured.out.startswith("usage: occultation")
    assert "local-circumstances" in captured.out
    assert "verify" in captured.out


def test_local_circumstances_reads_elements_and_location_files(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The two file inputs are enough; the run must be reproducible."""
    exit_code = main(
        [
            "local-circumstances",
            "--elements",
            str(ELEMENTS_FIXTURE),
            "--location",
            str(HONG_KONG_LOCATION),
            "--delta-t-seconds",
            "65",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == EXIT_OK
    assert "custom core" in captured.out
    assert "iterations            4" in captured.out
    assert captured.err == ""


def test_local_circumstances_json_matches_the_documented_schema(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(
        [
            "local-circumstances",
            "--elements",
            str(ELEMENTS_FIXTURE),
            "--location",
            str(HONG_KONG_LOCATION),
            "--delta-t-seconds",
            "65",
            "--format",
            "json",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == EXIT_OK
    document = json.loads(captured.out)
    assert document["engine"] == "custom"
    assert document["inputs"]["delta_t_seconds"] == 65.0
    assert document["inputs"]["observer"]["longitude_deg_east"] == pytest.approx(
        114.1743
    )
    assert document["result"]["is_occultation"] is True
    assert document["result"]["iteration_count"] == 4
    # The derived geocentric observer values are reported, not hidden.
    assert document["derived"]["rho_sin_geocentric_latitude"] == pytest.approx(
        0.377130, abs=1e-6
    )
    # No comparison block is claimed when only the custom engine ran.
    assert "comparison" not in document


def test_local_circumstances_accepts_inline_parameters(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The inline path must agree with the file path, value for value."""
    file_exit = main(
        [
            "local-circumstances",
            "--elements",
            str(ELEMENTS_FIXTURE),
            "--location",
            str(HONG_KONG_LOCATION),
            "--delta-t-seconds",
            "65",
            "--format",
            "json",
        ]
    )
    file_document = json.loads(capsys.readouterr().out)

    inline_exit = main(
        [
            "local-circumstances",
            "--reference-hour-td",
            "10.0",
            "--star-declination-deg",
            "11.9694",
            "--greenwich-hour-angle-deg",
            "156.6836",
            "--greenwich-hour-angle-rate-deg-per-hour",
            "15.04107",
            "--shadow-x0",
            "0.22151",
            "--shadow-x1",
            "0.55549",
            "--shadow-x2",
            "0.0",
            "--shadow-y0",
            "0.19947",
            "--shadow-y1",
            "-0.15258",
            "--shadow-y2",
            "-0.00001",
            "--longitude-deg-east",
            "114.1743",
            "--latitude-deg",
            "22.3020",
            "--delta-t-seconds",
            "65",
            "--format",
            "json",
        ]
    )
    inline_document = json.loads(capsys.readouterr().out)

    assert file_exit == inline_exit == EXIT_OK
    assert file_document["inputs"]["elements"] == inline_document["inputs"]["elements"]
    assert file_document["inputs"]["observer"] == inline_document["inputs"]["observer"]
    assert file_document["result"] == inline_document["result"]


def test_local_circumstances_compare_reports_the_missing_reference_engine(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``--engine compare`` must not invent a reference number (decision Q13b)."""
    exit_code = main(
        [
            "local-circumstances",
            "--elements",
            str(ELEMENTS_FIXTURE),
            "--location",
            str(HONG_KONG_LOCATION),
            "--delta-t-seconds",
            "65",
            "--engine",
            "compare",
            "--format",
            "json",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == EXIT_OK
    document = json.loads(captured.out)
    assert document["result"]["iteration_count"] == 4
    assert document["comparison"]["reference_engine"] == "skyfield"
    assert document["comparison"]["status"] == "unavailable"
    assert "not implemented" in document["comparison"]["reason"]


def test_local_circumstances_skyfield_exits_three(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Requesting the reference engine fails loudly instead of faking a result."""
    exit_code = main(
        [
            "local-circumstances",
            "--elements",
            str(ELEMENTS_FIXTURE),
            "--location",
            str(HONG_KONG_LOCATION),
            "--delta-t-seconds",
            "65",
            "--engine",
            "skyfield",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == EXIT_REFERENCE_UNAVAILABLE
    assert captured.out == ""
    assert "not implemented" in captured.err


def test_local_circumstances_skyfield_prints_nothing_even_as_json(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """No partial document is printed before exiting 3 (decision Q13a).

    ``--format json`` is the dangerous case: a half-built document on stdout
    would be consumed as a successful result by whatever script called us.
    """
    exit_code = main(
        [
            "local-circumstances",
            "--elements",
            str(ELEMENTS_FIXTURE),
            "--location",
            str(HONG_KONG_LOCATION),
            "--delta-t-seconds",
            "65",
            "--engine",
            "skyfield",
            "--format",
            "json",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == EXIT_REFERENCE_UNAVAILABLE
    assert captured.out == ""
    assert "not implemented" in captured.err


def test_local_circumstances_rejects_mixing_file_and_inline_inputs(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(
        [
            "local-circumstances",
            "--elements",
            str(ELEMENTS_FIXTURE),
            "--star-declination-deg",
            "11.9694",
            "--location",
            str(HONG_KONG_LOCATION),
            "--delta-t-seconds",
            "65",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == EXIT_USAGE
    assert "cannot be combined" in captured.err


def test_local_circumstances_reports_a_missing_file_without_a_traceback(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(
        [
            "local-circumstances",
            "--elements",
            "/nonexistent/elements.json",
            "--location",
            str(HONG_KONG_LOCATION),
            "--delta-t-seconds",
            "65",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == EXIT_USAGE
    assert "no such file" in captured.err
    assert "Traceback" not in captured.err


def test_local_circumstances_reports_malformed_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")

    exit_code = main(
        [
            "local-circumstances",
            "--elements",
            str(broken),
            "--location",
            str(HONG_KONG_LOCATION),
            "--delta-t-seconds",
            "65",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == EXIT_USAGE
    assert "not valid JSON" in captured.err


def test_local_circumstances_requires_delta_t(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Delta T is never guessed: the option is required."""
    with pytest.raises(SystemExit) as exit_info:
        main(
            [
                "local-circumstances",
                "--elements",
                str(ELEMENTS_FIXTURE),
                "--location",
                str(HONG_KONG_LOCATION),
            ]
        )

    assert exit_info.value.code == EXIT_USAGE
    assert "--delta-t-seconds" in capsys.readouterr().err


def test_verify_meeus_example_5_matches(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["verify", "meeus-example-5"])

    captured = capsys.readouterr()
    assert exit_code == EXIT_OK
    assert "VERDICT: matches" in captured.out
    assert "printed 228-229" in captured.out


def test_verify_meeus_example_5_json_lists_every_printed_value(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["verify", "meeus-example-5", "--format", "json"])

    captured = capsys.readouterr()
    assert exit_code == EXIT_OK
    document = json.loads(captured.out)
    assert document["verdict"] == "match"
    assert document["provenance"]["printed_pages"] == "228-229"
    quantities = {check["quantity"] for check in document["checks"]}
    assert quantities == {
        "rho_sin_geocentric_latitude",
        "rho_cos_geocentric_latitude",
        "hours_after_reference",
        "dynamical_time_hour",
        "universal_time_hour",
        "separation_in_moon_radii",
        "limb_clearance_in_moon_radii",
        "position_angle_deg",
        "altitude_deg",
        "is_occultation",
    }


def test_verify_exits_one_when_a_printed_value_is_wrong(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A corrupted expectation must produce exit 1, not a crash or a pass."""
    document = json.loads(ELEMENTS_FIXTURE.read_text(encoding="utf-8"))
    document["expected"]["position_angle_deg"] = 25.67
    corrupted = tmp_path / "corrupted.json"
    corrupted.write_text(json.dumps(document), encoding="utf-8")

    exit_code = main(["verify", "meeus-example-5", "--fixture", str(corrupted)])

    captured = capsys.readouterr()
    assert exit_code == EXIT_MISMATCH
    assert "VERDICT: MISMATCH" in captured.out


def test_verify_without_an_example_is_a_usage_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["verify"])

    captured = capsys.readouterr()
    assert exit_code == EXIT_USAGE
    assert "meeus-example-5" in captured.err
