"""Shared pytest fixtures."""

import os
from unittest.mock import patch

import pytest
import yaml

from math_ai_agent.agent import agent
from math_ai_agent.config import config
from math_ai_agent.config.config import AppConfig

TEST_LLM_KEY_ENV = "TEST_LLM_KEY"
TEST_LLM_KEY = "test-llm-key"


def _set_bundled_api_key_env() -> None:
    """Give the bundled config's API key variable a dummy value.

    ``math_ai_agent.app`` loads the config at import, which fails when
    the key variable is unset (e.g., in CI).
    """
    # pylint: disable-next=protected-access
    with open(config._resolve_config_path(), encoding="utf-8") as f:
        api_key_env = yaml.safe_load(f)["llm"]["api_key_env"]
    os.environ.setdefault(api_key_env, TEST_LLM_KEY)


_set_bundled_api_key_env()


@pytest.fixture(autouse=True)
def _llm_key_env(monkeypatch):
    """Set the API key variable named by the test ``api_key_env``."""
    monkeypatch.setenv(TEST_LLM_KEY_ENV, TEST_LLM_KEY)


@pytest.fixture()
def app_config() -> AppConfig:
    """Return a minimal ``AppConfig`` with test values."""
    return AppConfig.model_validate(
        {
            "llm": {
                "api_style": "chat",
                "model_base_url": "http://localhost:11434/v1",
                "model": "test-model",
                "api_key_env": TEST_LLM_KEY_ENV,
                "system_instructions": "Test instructions.",
            },
            "server": {
                "calculator_mcp": {
                    "url": "http://localhost:9000/mcp",
                    "is_oauth": False,
                    "token_dir": "/tmp/test-tokens",
                    "callback_port": 10000,
                }
            },
            "logging": {
                "version": 1,
                "disable_existing_loggers": False,
                "root": {"level": "WARNING"},
            },
        }
    )


@pytest.fixture(autouse=True)
def _patch_config(app_config):
    """Serve the shared test ``AppConfig`` to the agent."""
    with patch.object(agent, "get_config", return_value=app_config):
        yield
