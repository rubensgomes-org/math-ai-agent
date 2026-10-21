"""Unit tests for :mod:`math_ai_agent.mcp.calc_client`."""

# pylint: disable=protected-access

import stat
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from fastmcp import Client

from math_ai_agent.mcp import calc_client
from math_ai_agent.mcp.calc_client import CalcMCPClient

_URL = "http://localhost:9000/mcp"


@pytest.fixture()
def client_init():
    """Stub ``Client.__init__`` and return its mock."""
    with patch.object(Client, "__init__", return_value=None) as mock_init:
        yield mock_init


@pytest.fixture()
def oauth_config(monkeypatch, update_calculator_mcp, tmp_path):
    """An OAuth-enabled config with a valid encryption key set."""
    monkeypatch.setenv(
        calc_client._ENCRYPTION_KEY_ENV, Fernet.generate_key().decode()
    )
    return update_calculator_mcp(
        is_oauth=True, token_dir=str(tmp_path / "tokens")
    )


def test_init_without_oauth_sets_url_and_timeouts(app_config, client_init):
    calc = CalcMCPClient(app_config.mcp["calculator"])
    assert isinstance(calc, Client)
    client_init.assert_called_once_with(
        _URL,
        auth=None,
        timeout=calc_client._TIMEOUT_SECONDS,
        init_timeout=calc_client._INIT_TIMEOUT_SECONDS,
    )


def test_init_with_oauth_uses_encrypted_token_storage(
    oauth_config, client_init
):
    with (
        patch.object(calc_client, "OAuth") as oauth_class,
        patch.object(calc_client, "FernetEncryptionWrapper") as wrapper,
    ):
        CalcMCPClient(oauth_config)
    assert client_init.call_args.kwargs["auth"] is oauth_class.return_value
    oauth_kwargs = oauth_class.call_args.kwargs
    assert oauth_kwargs["token_storage"] is wrapper.return_value
    assert oauth_kwargs["callback_port"] == oauth_config.callback_port
    assert isinstance(wrapper.call_args.kwargs["fernet"], Fernet)


@pytest.mark.parametrize(
    "key, message", [(None, "must be set"), ("not-a-key", "not a valid")]
)
def test_init_with_oauth_rejects_missing_or_invalid_key(
    monkeypatch, oauth_config, client_init, key, message
):
    if key is None:
        monkeypatch.delenv(calc_client._ENCRYPTION_KEY_ENV)
    else:
        monkeypatch.setenv(calc_client._ENCRYPTION_KEY_ENV, key)
    with pytest.raises(ValueError, match=message):
        CalcMCPClient(oauth_config)
    client_init.assert_not_called()


def test_create_token_store_expands_home_and_creates_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    CalcMCPClient._create_token_store("~/tokens")
    assert (tmp_path / "tokens").is_dir()


def test_create_token_store_makes_dir_owner_only(tmp_path):
    directory = tmp_path / "tokens"
    directory.mkdir(mode=0o755)
    CalcMCPClient._create_token_store(str(directory))
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700


@pytest.mark.usefixtures("client_init")
async def test_exit_closes_the_client(app_config):
    calc = CalcMCPClient(app_config.mcp["calculator"])
    calc._server_url = _URL
    with patch.object(Client, "__aexit__", return_value=None) as client_exit:
        await calc.__aexit__(None, None, None)
    client_exit.assert_awaited_once_with(None, None, None)
