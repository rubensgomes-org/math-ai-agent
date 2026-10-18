"""Unit tests for :mod:`math_ai_agent.config.ms.app_configuration`."""

# Tests exercise the private store reader directly.
# pylint: disable=protected-access

from unittest.mock import MagicMock

import pytest

from math_ai_agent.config.ms import app_configuration

ENDPOINT = "https://appcs-test.azconfig.io"


@pytest.fixture()
def credential(monkeypatch):
    """Patch ``DefaultAzureCredential``; return the credential mock."""
    credential = MagicMock()
    monkeypatch.setattr(
        app_configuration,
        "DefaultAzureCredential",
        MagicMock(return_value=credential),
    )
    return credential


@pytest.fixture()
def mock_load(monkeypatch, credential):  # pylint: disable=unused-argument
    """Patch the SDK ``load``; return its mock."""
    load = MagicMock()
    load.return_value.__enter__.return_value = {}
    monkeypatch.setattr(app_configuration, "load", load)
    return load


def test_read_store_nests_keys(mock_load):
    mock_load.return_value.__enter__.return_value = {
        "llm/model": "gpt-5-nano",
        "server/calculator_mcp/url": "https://ca-mathmcp-dev/mcp",
        "web/port": "8080",
    }
    result = app_configuration._read_store(ENDPOINT, "dev")
    assert result == {
        "llm": {"model": "gpt-5-nano"},
        "server": {"calculator_mcp": {"url": "https://ca-mathmcp-dev/mcp"}},
        "web": {"port": "8080"},
    }


def test_read_store_passes_filters(mock_load):
    app_configuration._read_store(ENDPOINT, "lab")
    kwargs = mock_load.call_args.kwargs
    assert kwargs["endpoint"] == ENDPOINT
    assert kwargs["trim_prefixes"] == ["ca-mathagent/"]
    [selector] = kwargs["selects"]
    assert selector.key_filter == "ca-mathagent/*"
    assert selector.label_filter == "lab"


@pytest.mark.usefixtures("mock_load")
def test_read_store_empty_store():
    assert not app_configuration._read_store(ENDPOINT, "dev")


def test_read_store_propagates_errors(mock_load):
    mock_load.side_effect = RuntimeError("forbidden")
    with pytest.raises(RuntimeError, match="forbidden"):
        app_configuration._read_store(ENDPOINT, "dev")


@pytest.mark.usefixtures("mock_load")
def test_read_store_closes_credential(credential):
    app_configuration._read_store(ENDPOINT, "dev")
    credential.__exit__.assert_called_once()
