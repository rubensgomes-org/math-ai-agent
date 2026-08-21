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

import logging
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from math_ai_agent.config import config


@pytest.fixture()
def tmp_config(tmp_path):
    """Write a minimal config.yaml and patch _CONFIG_PATH to point at it."""
    cfg = {
        "server": {
            "calculator_mcp": {
                "url": "http://localhost:9000/mcp",
                "is_oauth": False,
                "token_dir": "/tmp/tokens",
                "callback_port": 12345,
                "timeout": 30,
            }
        },
        "llm": {
            "model_base_url": "http://localhost:11434/v1",
            "model": "test-model",
            "api_key_env": "TEST_LLM_KEY",
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
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.dump(cfg))
    with patch.object(config, "_CONFIG_PATH", cfg_path):
        yield cfg


# ---------------------------------------------------------------------------
# _resolve_config_path
# ---------------------------------------------------------------------------


def test_resolve_config_path_uses_env_var(tmp_path, monkeypatch):
    custom = tmp_path / "custom.yaml"
    custom.touch()
    monkeypatch.setenv("CALCULATOR_MCP_CONFIG", str(custom))
    assert config._resolve_config_path() == custom


def test_resolve_config_path_uses_cwd(tmp_path, monkeypatch):
    """A config.yaml in the cwd wins over the packaged default."""
    monkeypatch.delenv("CALCULATOR_MCP_CONFIG", raising=False)
    cwd_cfg = tmp_path / "config.yaml"
    cwd_cfg.touch()
    monkeypatch.chdir(tmp_path)
    assert config._resolve_config_path() == cwd_cfg


def test_resolve_config_path_falls_back_to_package(tmp_path, monkeypatch):
    """With no env var and no cwd config, the packaged default is used."""
    monkeypatch.delenv("CALCULATOR_MCP_CONFIG", raising=False)
    monkeypatch.chdir(tmp_path)  # empty dir -- no config.yaml
    result = config._resolve_config_path()
    assert result.name == "config.yaml"
    assert "math_ai_agent" in str(result)


def test_resolve_config_path_default(monkeypatch):
    monkeypatch.delenv("CALCULATOR_MCP_CONFIG", raising=False)
    result = config._resolve_config_path()
    assert result.name == "config.yaml"


# ---------------------------------------------------------------------------
# _load_config
# ---------------------------------------------------------------------------


def test_load_config_returns_dict(tmp_config):
    result = config._load_config()
    assert isinstance(result, dict)
    assert "server" in result
    assert "logging" in result


# ---------------------------------------------------------------------------
# configure_logging
# ---------------------------------------------------------------------------


def test_configure_logging_applies_config(tmp_config):
    config.configure_logging()
    root = logging.getLogger()
    assert root.level == logging.WARNING


# ---------------------------------------------------------------------------
# get_timeout
# ---------------------------------------------------------------------------


def test_get_timeout(tmp_config):
    assert config.get_timeout() == 30


# ---------------------------------------------------------------------------
# is_oauth
# ---------------------------------------------------------------------------


def test_is_oauth_false(tmp_config):
    assert config.is_oauth() is False


def test_is_oauth_true(tmp_path):
    cfg = {
        "server": {
            "calculator_mcp": {
                "url": "http://localhost/mcp",
                "is_oauth": True,
                "token_dir": "/tmp/tokens",
                "callback_port": 10000,
                "timeout": 10,
            }
        },
        "logging": {
            "version": 1,
            "disable_existing_loggers": False,
            "root": {"level": "WARNING"},
        },
    }
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.dump(cfg))
    with patch.object(config, "_CONFIG_PATH", cfg_path):
        assert config.is_oauth() is True


def test_is_oauth_missing_defaults_false(tmp_path):
    cfg = {
        "server": {
            "calculator_mcp": {
                "url": "http://localhost/mcp",
                "token_dir": "/tmp/tokens",
                "callback_port": 10000,
                "timeout": 10,
            }
        },
        "logging": {
            "version": 1,
            "disable_existing_loggers": False,
            "root": {"level": "WARNING"},
        },
    }
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.dump(cfg))
    with patch.object(config, "_CONFIG_PATH", cfg_path):
        assert config.is_oauth() is False


# ---------------------------------------------------------------------------
# get_url
# ---------------------------------------------------------------------------


def test_get_url(tmp_config):
    assert config.get_url() == "http://localhost:9000/mcp"


# ---------------------------------------------------------------------------
# get_token_dir
# ---------------------------------------------------------------------------


def test_get_token_dir(tmp_config):
    assert config.get_token_dir() == "/tmp/tokens"


# ---------------------------------------------------------------------------
# get_callback_port
# ---------------------------------------------------------------------------


def test_get_callback_port(tmp_config):
    assert config.get_callback_port() == 12345


# ---------------------------------------------------------------------------
# get_model_base_url
# ---------------------------------------------------------------------------


def test_get_model_base_url(tmp_config):
    assert config.get_model_base_url() == "http://localhost:11434/v1"


# ---------------------------------------------------------------------------
# get_model
# ---------------------------------------------------------------------------


def test_get_model(tmp_config):
    assert config.get_model() == "test-model"


# ---------------------------------------------------------------------------
# get_api_style
# ---------------------------------------------------------------------------


def _rewrite_config(cfg):
    """Rewrite the patched config.yaml with the given mapping."""
    config._CONFIG_PATH.write_text(yaml.dump(cfg))


def test_get_api_style_defaults_to_chat(tmp_config):
    """A config without llm.api_style falls back to "chat"."""
    assert "api_style" not in tmp_config["llm"]
    assert config.get_api_style() == "chat"


def test_get_api_style_responses(tmp_config):
    """An explicit "responses" style is returned as-is."""
    tmp_config["llm"]["api_style"] = "responses"
    _rewrite_config(tmp_config)
    assert config.get_api_style() == "responses"


def test_get_api_style_chat(tmp_config):
    """An explicit "chat" style is returned as-is."""
    tmp_config["llm"]["api_style"] = "chat"
    _rewrite_config(tmp_config)
    assert config.get_api_style() == "chat"


def test_get_api_style_unknown_raises(tmp_config):
    """An unrecognised style raises ValueError."""
    tmp_config["llm"]["api_style"] = "wat"
    _rewrite_config(tmp_config)
    with pytest.raises(ValueError, match="Unknown llm.api_style: wat"):
        config.get_api_style()


# ---------------------------------------------------------------------------
# get_api_key
# ---------------------------------------------------------------------------


def test_get_api_key(tmp_config, monkeypatch):
    monkeypatch.setenv("TEST_LLM_KEY", "secret-key")
    assert config.get_api_key() == "secret-key"


def test_get_api_key_missing_raises(tmp_config, monkeypatch):
    monkeypatch.delenv("TEST_LLM_KEY", raising=False)
    with pytest.raises(RuntimeError, match="TEST_LLM_KEY"):
        config.get_api_key()


def test_get_api_key_empty_raises(tmp_config, monkeypatch):
    monkeypatch.setenv("TEST_LLM_KEY", "")
    with pytest.raises(RuntimeError, match="TEST_LLM_KEY"):
        config.get_api_key()
