"""Run main() parsing any user CLI arguments."""

import argparse
import logging
from importlib.metadata import metadata, version

_DISTRIBUTION_NAME = "math-ai-agent"
_PACKAGE = "math_ai_agent"

logger = logging.getLogger(__name__)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog=_DISTRIBUTION_NAME,
        description=f"%(prog)s {metadata(_DISTRIBUTION_NAME)["Summary"]}",
    )
    parser.add_argument(
        "--version",
        action="version",
        help="show the installed version",
        version=f"%(prog)s {version(_DISTRIBUTION_NAME)}",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments and run the app."""
    _parse_args(argv)
    # Import config and app only after parsing so --help and --version stay
    # fast.
    # pylint: disable=import-outside-toplevel
    from ai_utils_lib.config.config import load_config
    from ai_utils_lib.config.file_load_config import configure_logging

    app_config = load_config(_PACKAGE)
    configure_logging(app_config)
    from math_ai_agent.app import run

    logger.info("Starting %s", _DISTRIBUTION_NAME)
    return run(app_config)
