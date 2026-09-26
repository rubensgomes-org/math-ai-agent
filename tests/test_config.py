# General Disclaimer
#
# **AI Generated Content**
#
# This project's source code and documentation were generated predominantly
# by an Artificial Intelligence Large Language Model (AI LLM). The project
# lead, [Rubens Gomes](https://rubensgomes.com), provided initial prompts,
# reviewed, and made refinements to the generated output. While human review and
# refinement have occurred, users should be aware that the output may contain
# inaccuracies, errors, or security vulnerabilities
#
# **Third-Party Content Notice**
#
# This software may include components or snippets derived from third-party
# sources. The software's users and distributors are responsible for ensuring
# compliance with any underlying licenses applicable to such components.
#
# **Copyright Status Statement**
#
# Copyright protection, if any, is limited to the original
# human contributions and modifications made to this project.
# The AI-generated portions of the code and
# documentation are not subject to copyright and are considered to be in the
# public domain.
#
# **Limitation of liability**
#
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES, OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR
# OTHERWISE, ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.
#
# **No-Warranty Disclaimer**
#
# THIS SOFTWARE IS PROVIDED 'AS IS,' WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT.

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
# load_config
# ---------------------------------------------------------------------------


def test_load_config_parses_values(tmp_path, cfg):
    result = config.load_config(_write(tmp_path, cfg))
    assert result.llm.model == "test-model"
    assert result.llm.model_base_url == "http://localhost:11434/v1"
    assert result.llm.system_instructions == "Test instructions."
    assert result.server.calculator_mcp.url == "http://localhost:9000/mcp"
    assert result.server.calculator_mcp.token_dir == "/tmp/tokens"
    assert result.server.calculator_mcp.callback_port == 12345
    assert result.logging["version"] == 1


def test_load_config_api_style_defaults_to_chat(tmp_path, cfg):
    assert config.load_config(_write(tmp_path, cfg)).llm.api_style == "chat"


def test_load_config_api_style_responses(tmp_path, cfg):
    cfg["llm"]["api_style"] = "responses"
    result = config.load_config(_write(tmp_path, cfg))
    assert result.llm.api_style == "responses"


def test_load_config_unknown_api_style_raises(tmp_path, cfg):
    cfg["llm"]["api_style"] = "wat"
    with pytest.raises(ValidationError, match="api_style"):
        config.load_config(_write(tmp_path, cfg))


def test_load_config_load_limits_default(tmp_path, cfg):
    result = config.load_config(_write(tmp_path, cfg))
    assert result.llm.timeout_seconds == config.DEFAULT_LLM_TIMEOUT_SECONDS
    assert result.llm.max_concurrent_prompts == 10


def test_load_config_load_limits_custom(tmp_path, cfg):
    cfg["llm"]["timeout_seconds"] = 30
    cfg["llm"]["max_concurrent_prompts"] = 3
    result = config.load_config(_write(tmp_path, cfg))
    assert result.llm.timeout_seconds == 30
    assert result.llm.max_concurrent_prompts == 3


@pytest.mark.parametrize("key", ["timeout_seconds", "max_concurrent_prompts"])
@pytest.mark.parametrize("value", [0, -1])
def test_load_config_non_positive_load_limit_raises(tmp_path, cfg, key, value):
    cfg["llm"][key] = value
    with pytest.raises(ValidationError, match=key):
        config.load_config(_write(tmp_path, cfg))


def test_load_config_is_oauth_true(tmp_path, cfg):
    cfg["server"]["calculator_mcp"]["is_oauth"] = True
    result = config.load_config(_write(tmp_path, cfg))
    assert result.server.calculator_mcp.is_oauth is True


def test_load_config_is_oauth_missing_defaults_false(tmp_path, cfg):
    del cfg["server"]["calculator_mcp"]["is_oauth"]
    result = config.load_config(_write(tmp_path, cfg))
    assert result.server.calculator_mcp.is_oauth is False


def test_load_config_missing_section_raises(tmp_path, cfg):
    del cfg["llm"]
    with pytest.raises(ValidationError, match="llm"):
        config.load_config(_write(tmp_path, cfg))


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


# ---------------------------------------------------------------------------
# get_api_key
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("env_config")
def test_get_api_key(monkeypatch):
    monkeypatch.setenv("TEST_LLM_KEY", "secret-key")
    assert config.get_api_key() == "secret-key"


@pytest.mark.usefixtures("env_config")
def test_get_api_key_missing_raises(monkeypatch):
    monkeypatch.delenv("TEST_LLM_KEY", raising=False)
    with pytest.raises(RuntimeError, match="TEST_LLM_KEY"):
        config.get_api_key()


@pytest.mark.usefixtures("env_config")
def test_get_api_key_empty_raises(monkeypatch):
    monkeypatch.setenv("TEST_LLM_KEY", "")
    with pytest.raises(RuntimeError, match="TEST_LLM_KEY"):
        config.get_api_key()
