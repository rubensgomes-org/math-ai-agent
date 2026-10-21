"""Unit tests for :mod:`math_ai_agent.cli`."""

from importlib.metadata import version
from unittest.mock import MagicMock, call, patch

import pytest

from math_ai_agent.cli import main

_DISTRIBUTION_NAME = "math-ai-agent"


@pytest.fixture()
def startup():
    """Patch config loading, logging setup, and ``run``; record call order."""
    calls = MagicMock()
    with (
        patch("ai_utils_lib.config.config.load_config", calls.load_config),
        patch(
            "ai_utils_lib.config.file_load_config.configure_logging",
            calls.configure_logging,
        ),
        patch("math_ai_agent.app.run", calls.run),
    ):
        yield calls


def test_main_configures_logging_then_runs_app(startup):
    startup.run.return_value = 0
    assert main([]) == 0
    app_config = startup.load_config.return_value
    assert startup.mock_calls == [
        call.load_config("math_ai_agent"),
        call.configure_logging(app_config),
        call.run(app_config),
    ]


def test_main_returns_run_exit_code(startup):
    startup.run.return_value = 1
    assert main([]) == 1


def test_main_version_prints_version_and_exits(startup, capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == (
        f"{_DISTRIBUTION_NAME} {version(_DISTRIBUTION_NAME)}"
    )
    assert not startup.mock_calls


def test_main_rejects_unknown_argument(startup):
    with pytest.raises(SystemExit) as exit_info:
        main(["--bogus"])
    assert exit_info.value.code == 2
    assert not startup.mock_calls
