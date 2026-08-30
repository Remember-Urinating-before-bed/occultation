import argparse
from importlib.metadata import version


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="occultation", description="Generic astronomical data for HK"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=version("occultation"),
    )
    return parser


def main() -> None:
    parser = build_parser()
    parser.parse_args()


if __name__ == "__main__":
    main()
