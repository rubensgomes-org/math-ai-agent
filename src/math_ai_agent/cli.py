"""Command-line entry point."""

import argparse
from importlib.metadata import version

_DISTRIBUTION_NAME = "math-ai-agent"


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse the command-line arguments; ``--version`` prints and exits."""
    parser = argparse.ArgumentParser(
        prog=_DISTRIBUTION_NAME,
        description="A simple Math AI Agent web application",
    )
    parser.add_argument(
        "--version",
        action="version",
        help="show the installed version",
        version=f"%(prog)s {version(_DISTRIBUTION_NAME)}",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Parse the arguments, then run the web app."""
    _parse_args(argv)
    # Import the app only after parsing so --help and --version stay fast.
    # pylint: disable-next=import-outside-toplevel
    from math_ai_agent.app import run

    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
