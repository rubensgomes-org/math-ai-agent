"""Run main() parsing any user CLI arguments."""

import argparse
import logging
from importlib.metadata import metadata, version

from math_ai_agent.config.config import configure_logging

_DISTRIBUTION_NAME = "math-ai-agent"


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
    #  when argparse gets None, it defaults/reads sys.argv[1:] tself
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _parse_args(argv)
    # Import the app only after parsing so --help and --version stay fast.
    # pylint: disable-next=import-outside-toplevel
    from math_ai_agent.app import run

    configure_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting %s", _DISTRIBUTION_NAME)
    # app:run starts uvicorn web server, and returns None
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
