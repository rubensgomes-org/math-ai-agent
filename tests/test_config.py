"""Unit tests for :mod:`math_ai_agent.config.config`."""

# Tests exercise the private config path resolver directly.
# pylint: disable=protected-access

import logging

import pytest
import yaml
from pydantic import ValidationError

from math_ai_agent.config import config


@pytest.fixture(autouse=True)
def _clear_config_cache():
    """Isolate each test from the cached ``get_config()`` result."""
    config.get_config.cache_clear()
    yield
    config.get_config.cache_clear()


@pytest.fixture(autouse=True)
def _local_mode(monkeypatch):
    """Run in local mode unless a test opts into Azure mode."""
    monkeypatch.delenv("APP_CONFIG_ENDPOINT", raising=False)


@pytest.fixture()
def cfg():
    """Return a minimal config.yaml mapping."""
    return {
        "server": {
            "calculator_mcp": {
                "url": "http://localhost:9000/mcp",
                "is_oauth": False,
                "token_dir": "/tmp/tokens",
                "callback_port": 12345,
            }
        },
        "llm": {
            "model_base_url": "http://localhost:11434/v1",
            "model": "test-model",
            "api_key_env": "TEST_LLM_KEY",
            "system_instructions": "Test instructions.",
        },
        "logging": {
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stderr",
                }
            },
            "root": {"level": "WARNING", "handlers": ["console"]},
        },
    }


def _write(tmp_path, mapping):
    """Write ``mapping`` as YAML and return the file path."""
    path = tmp_path / "config.yaml"
    path.write_text(yaml.dump(mapping))
    return path


@pytest.fixture()
def env_config(tmp_path, monkeypatch, cfg):
    """Point ``MATHAIAGENT_CONFIG`` at a written copy of ``cfg``."""
    monkeypatch.setenv("MATHAIAGENT_CONFIG", str(_write(tmp_path, cfg)))
    return cfg


# ---------------------------------------------------------------------------
# _resolve_config_path
# ---------------------------------------------------------------------------


def test_resolve_config_path_uses_env_var(tmp_path, monkeypatch):
    custom = tmp_path / "custom.yaml"
    custom.touch()
    monkeypatch.setenv("MATHAIAGENT_CONFIG", str(custom))
    assert config._resolve_config_path() == custom


def test_resolve_config_path_ignores_cwd(tmp_path, monkeypatch):
    """A config.yaml in the cwd does not override the packaged default."""
    monkeypatch.delenv("MATHAIAGENT_CONFIG", raising=False)
    cwd_cfg = tmp_path / "config.yaml"
    cwd_cfg.touch()
    monkeypatch.chdir(tmp_path)
    assert config._resolve_config_path() != cwd_cfg


def test_resolve_config_path_falls_back_to_package(tmp_path, monkeypatch):
    """With no env var, the packaged default is used."""
    monkeypatch.delenv("MATHAIAGENT_CONFIG", raising=False)
    monkeypatch.chdir(tmp_path)
    result = config._resolve_config_path()
    assert result.name == "config.yaml"
    assert "math_ai_agent" in str(result)


def test_resolve_config_path_default(monkeypatch):
    monkeypatch.delenv("MATHAIAGENT_CONFIG", raising=False)
    result = config._resolve_config_path()
    assert result.name == "config.yaml"


# ---------------------------------------------------------------------------
# _load_config
# ---------------------------------------------------------------------------


def test_load_config_parses_values(tmp_path, cfg):
    result = config._load_config(_write(tmp_path, cfg))
    assert result.llm.model == "test-model"
    assert result.llm.model_base_url == "http://localhost:11434/v1"
    assert result.llm.system_instructions == "Test instructions."
    assert result.server.calculator_mcp.url == "http://localhost:9000/mcp"
    assert result.server.calculator_mcp.token_dir == "/tmp/tokens"
    assert result.server.calculator_mcp.callback_port == 12345
    assert result.logging["version"] == 1


def test_load_config_api_style_defaults_to_chat(tmp_path, cfg):
    assert config._load_config(_write(tmp_path, cfg)).llm.api_style == "chat"


def test_load_config_api_style_responses(tmp_path, cfg):
    cfg["llm"]["api_style"] = "responses"
    result = config._load_config(_write(tmp_path, cfg))
    assert result.llm.api_style == "responses"


def test_load_config_unknown_api_style_raises(tmp_path, cfg):
    cfg["llm"]["api_style"] = "wat"
    with pytest.raises(ValidationError, match="api_style"):
        config._load_config(_write(tmp_path, cfg))


@pytest.mark.parametrize("key", ["model_base_url", "model"])
def test_load_config_empty_llm_value_raises(tmp_path, cfg, key):
    cfg["llm"][key] = ""
    with pytest.raises(ValidationError, match=key):
        config._load_config(_write(tmp_path, cfg))


def test_load_config_load_limits_default(tmp_path, cfg):
    result = config._load_config(_write(tmp_path, cfg))
    assert result.llm.timeout_seconds == config.DEFAULT_LLM_TIMEOUT_SECONDS
    assert result.llm.max_concurrent_prompts == 10


def test_load_config_is_stateful(tmp_path, cfg):
    assert config._load_config(_write(tmp_path, cfg)).llm.is_stateful is False
    cfg["llm"]["is_stateful"] = True
    assert config._load_config(_write(tmp_path, cfg)).llm.is_stateful is True


def test_load_config_temperature_defaults_to_none(tmp_path, cfg):
    assert config._load_config(_write(tmp_path, cfg)).llm.temperature is None


@pytest.mark.parametrize("value", [0, 0.2, 2])
def test_load_config_temperature_in_range(tmp_path, cfg, value):
    cfg["llm"]["temperature"] = value
    assert config._load_config(_write(tmp_path, cfg)).llm.temperature == value


@pytest.mark.parametrize("value", [-0.1, 2.1])
def test_load_config_temperature_out_of_range_raises(tmp_path, cfg, value):
    cfg["llm"]["temperature"] = value
    with pytest.raises(ValidationError, match="temperature"):
        config._load_config(_write(tmp_path, cfg))


def test_load_config_load_limits_custom(tmp_path, cfg):
    cfg["llm"]["timeout_seconds"] = 30
    cfg["llm"]["max_concurrent_prompts"] = 3
    result = config._load_config(_write(tmp_path, cfg))
    assert result.llm.timeout_seconds == 30
    assert result.llm.max_concurrent_prompts == 3


@pytest.mark.parametrize("key", ["timeout_seconds", "max_concurrent_prompts"])
@pytest.mark.parametrize("value", [0, -1])
def test_load_config_non_positive_load_limit_raises(tmp_path, cfg, key, value):
    cfg["llm"][key] = value
    with pytest.raises(ValidationError, match=key):
        config._load_config(_write(tmp_path, cfg))


def test_load_config_is_oauth_true(tmp_path, cfg):
    cfg["server"]["calculator_mcp"]["is_oauth"] = True
    result = config._load_config(_write(tmp_path, cfg))
    assert result.server.calculator_mcp.is_oauth is True


def test_load_config_is_oauth_missing_defaults_false(tmp_path, cfg):
    del cfg["server"]["calculator_mcp"]["is_oauth"]
    result = config._load_config(_write(tmp_path, cfg))
    assert result.server.calculator_mcp.is_oauth is False


def test_load_config_missing_section_raises(tmp_path, cfg):
    del cfg["llm"]
    with pytest.raises(ValidationError, match="llm"):
        config._load_config(_write(tmp_path, cfg))


# ---------------------------------------------------------------------------
# get_config
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("env_config")
def test_get_config_reads_env_path():
    assert config.get_config().llm.model == "test-model"


@pytest.mark.usefixtures("env_config")
def test_get_config_is_cached(monkeypatch):
    first = config.get_config()
    monkeypatch.delenv("MATHAIAGENT_CONFIG")
    assert config.get_config() is first


# ---------------------------------------------------------------------------
# configure_logging
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("env_config")
def test_configure_logging_applies_config():
    config.configure_logging()
    assert logging.getLogger().level == logging.WARNING


@pytest.fixture()
def httpx_logger(monkeypatch):
    """Yield the ``httpx`` logger at WARNING; restore its level after."""
    monkeypatch.delenv(config.HTTPX_LOG_LEVEL_ENV, raising=False)
    httpx = logging.getLogger(config.HTTPX_LOGGER_NAME)
    original_level = httpx.level
    httpx.setLevel(logging.WARNING)
    yield httpx
    httpx.setLevel(original_level)


@pytest.mark.usefixtures("env_config")
@pytest.mark.parametrize("value", ["debug", "DEBUG"])
def test_configure_logging_applies_httpx_log_level(
    monkeypatch, httpx_logger, value
):
    monkeypatch.setenv(config.HTTPX_LOG_LEVEL_ENV, value)
    config.configure_logging()
    assert httpx_logger.level == logging.DEBUG


@pytest.mark.usefixtures("env_config")
def test_configure_logging_keeps_httpx_level_when_unset(httpx_logger):
    config.configure_logging()
    assert httpx_logger.level == logging.WARNING


@pytest.mark.usefixtures("env_config", "httpx_logger")
def test_configure_logging_invalid_httpx_log_level_raises(monkeypatch):
    monkeypatch.setenv(config.HTTPX_LOG_LEVEL_ENV, "chatty")
    with pytest.raises(ValueError, match="CHATTY"):
        config.configure_logging()


# ---------------------------------------------------------------------------
# LLMConfig.api_key
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("env_config")
def test_api_key_read_from_env(monkeypatch):
    monkeypatch.setenv("TEST_LLM_KEY", "secret-key")
    assert config.get_config().llm.api_key == "secret-key"


@pytest.mark.usefixtures("env_config")
def test_api_key_missing_raises(monkeypatch):
    monkeypatch.delenv("TEST_LLM_KEY", raising=False)
    with pytest.raises(ValidationError, match="TEST_LLM_KEY"):
        config.get_config()


@pytest.mark.usefixtures("env_config")
def test_api_key_empty_raises(monkeypatch):
    monkeypatch.setenv("TEST_LLM_KEY", "")
    with pytest.raises(ValidationError, match="TEST_LLM_KEY"):
        config.get_config()


@pytest.mark.usefixtures("env_config")
def test_api_key_not_exposed(monkeypatch):
    monkeypatch.setenv("TEST_LLM_KEY", "secret-key")
    llm = config.get_config().llm
    assert "secret-key" not in repr(llm)
    assert "api_key" not in llm.model_dump()


# ---------------------------------------------------------------------------
# Azure mode
# ---------------------------------------------------------------------------

AZURE_ENV = {
    "APP_CONFIG_ENDPOINT": "https://appcs.azconfig.io",
    "KEY_VAULT_URI": "https://kv.vault.azure.net/",
    "CONTAINER_APP_NAME": "ca-mathagent-lab",
}


@pytest.fixture()
def store_mapping():
    """Return App Configuration settings as the store loader yields them."""
    return {
        "llm": {
            "api_style": "responses",
            "model_base_url": "https://aif.openai.azure.com/openai/v1",
            "model": "store-model",
            "api_key_env": "FOUNDRY_API_KEY",
            "system_instructions": "Store instructions.",
            "timeout_seconds": "30",
            "is_stateful": "false",
        },
        "server": {
            "calculator_mcp": {
                "url": "http://ca-mathmcp-lab/mcp",
                "is_oauth": "false",
                "token_dir": "",
                "callback_port": "0",
            }
        },
        "web": {"host": "0.0.0.0", "port": "8080"},
    }


@pytest.fixture()
def azure(
    monkeypatch, env_config, store_mapping
):  # pylint: disable=unused-argument
    """Set Azure mode; return the recorded store and vault calls."""
    calls = {"store": [], "vault": []}

    def fake_store(endpoint, label):
        calls["store"].append((endpoint, label))
        return store_mapping

    def fake_vault(vault_uri, name):
        calls["vault"].append((vault_uri, name))
        return "vault-key"

    for name, value in AZURE_ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("TEST_LLM_KEY", raising=False)
    monkeypatch.setattr(config, "load_app_configuration", fake_store)
    monkeypatch.setattr(config.key_vault, "read_secret", fake_vault)
    return calls


def test_get_config_azure_reads_store_with_app_label(azure):
    result = config.get_config()
    assert azure["store"] == [("https://appcs.azconfig.io", "lab")]
    assert result.llm.model == "store-model"
    assert result.llm.timeout_seconds == 30
    assert result.llm.is_stateful is False
    assert result.web.port == 8080


def test_get_config_azure_reads_api_key_from_vault(azure):
    assert config.get_config().llm.api_key == "vault-key"
    assert azure["vault"] == [
        ("https://kv.vault.azure.net/", "ca-mathagent--FOUNDRY-API-KEY")
    ]


@pytest.mark.usefixtures("azure")
def test_get_config_azure_ignores_yaml_settings():
    mcp = config.get_config().server.calculator_mcp
    assert mcp.url == "http://ca-mathmcp-lab/mcp"
    assert mcp.token_dir == ""


@pytest.mark.usefixtures("azure")
def test_get_config_azure_takes_logging_from_yaml():
    assert config.get_config().logging["version"] == 1


@pytest.mark.usefixtures("azure")
def test_get_config_azure_missing_setting_raises(store_mapping):
    del store_mapping["llm"]["model"]
    with pytest.raises(ValidationError, match="model"):
        config.get_config()


@pytest.mark.parametrize("name", ["KEY_VAULT_URI", "CONTAINER_APP_NAME"])
@pytest.mark.usefixtures("azure")
def test_get_config_azure_missing_env_raises(monkeypatch, name):
    monkeypatch.delenv(name)
    with pytest.raises(ValueError, match=name):
        config.get_config()


@pytest.mark.parametrize("app_name", ["mathagent", "ca-mathagent-"])
@pytest.mark.usefixtures("azure")
def test_get_config_azure_app_name_without_label_raises(monkeypatch, app_name):
    monkeypatch.setenv("CONTAINER_APP_NAME", app_name)
    with pytest.raises(ValueError, match="environment suffix"):
        config.get_config()


@pytest.mark.parametrize("value", [None, ""])
@pytest.mark.usefixtures("env_config")
def test_get_config_without_endpoint_uses_yaml(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("APP_CONFIG_ENDPOINT", raising=False)
    else:
        monkeypatch.setenv("APP_CONFIG_ENDPOINT", value)
    assert config.get_config().llm.model == "test-model"
