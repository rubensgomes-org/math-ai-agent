"""Shared pytest fixtures."""

import pytest
from ai_utils_lib.config.models import MCP, AppConfig, Model

TEST_LLM_KEY_ENV = "TEST_LLM_KEY"
TEST_LLM_KEY = "test-llm-key"


@pytest.fixture(autouse=True)
def _llm_key_env(monkeypatch):
    """Set the API key variable named by the test ``api_key_env``."""
    monkeypatch.setenv(TEST_LLM_KEY_ENV, TEST_LLM_KEY)


@pytest.fixture()
def app_config() -> AppConfig:
    """Return a minimal ``AppConfig`` with test values."""
    return AppConfig.model_validate(
        {
            "azure": {
                "app_config_prefix": "test/",
                "secret_prefix": "test",
            },
            "foundry": {"project_endpoint": "https://foundry.test/api"},
            "mcp": {
                "calculator": {
                    "url": "http://localhost:9000/mcp",
                    "is_oauth": False,
                    "token_dir": "/tmp/test-tokens",
                    "callback_port": 10000,
                }
            },
            "model": {
                "api_style": "chat",
                "base_url": "http://localhost:11434/v1",
                "name": "test-model",
                "api_key_env": TEST_LLM_KEY_ENV,
                "instructions": "Test instructions.",
            },
            "logging": {
                "version": 1,
                "disable_existing_loggers": False,
                "root": {"level": "WARNING"},
            },
        }
    )


@pytest.fixture()
def update_model(app_config):
    """Return a function building the test ``Model`` with ``updates``."""

    def _update(**fields) -> Model:
        return app_config.model.model_copy(update=fields)

    return _update


@pytest.fixture()
def update_calculator_mcp(app_config):
    """Return a function building the test calculator ``MCP`` config."""

    def _update(**fields) -> MCP:
        return app_config.mcp["calculator"].model_copy(update=fields)

    return _update
