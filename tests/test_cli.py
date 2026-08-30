# Sample test case
from occultation.cli import build_parser


def test_cli_program_name() -> None:
    parser = build_parser()

    assert parser.prog == "occultation"
