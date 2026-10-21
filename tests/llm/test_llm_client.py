"""Unit tests for :mod:`math_ai_agent.llm.llm_client`."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from math_ai_agent.llm import llm_client
from math_ai_agent.llm.llm_client import LLMClient


def test_llm_client_is_abstract(app_config):
    """LLMClient cannot be instantiated without its abstract methods."""
    with pytest.raises(TypeError):
        # pylint: disable-next=abstract-class-instantiated
        LLMClient(app_config.model, [{"type": "x"}])


@pytest.mark.parametrize(
    ("secret", "masked"),
    [
        ("sk-abcdef123456", "****3456"),
        ("abcdefgh1234", "****1234"),
        ("abcdefg1234", "****"),
        ("", "****"),
    ],
)
def test_mask_secret_shows_suffix_only_for_long_secrets(secret, masked):
    # pylint: disable-next=protected-access
    assert llm_client._mask_secret(secret) == masked


class _StubClient(LLMClient):
    """Concrete ``LLMClient`` for exercising the base class."""

    @staticmethod
    def _token_usage(response):
        raise NotImplementedError


def test_empty_tools_raises(app_config):
    with pytest.raises(ValueError, match="tools must not be empty"):
        _StubClient(app_config.model, [])


def test_unset_api_key_env_variable_raises(app_config, monkeypatch):
    """A configured api_key_env without a value fails, not Entra ID."""
    credential_class = MagicMock()
    monkeypatch.setattr(llm_client, "DefaultAzureCredential", credential_class)
    model = app_config.model.model_copy(update={"api_key": None})
    with pytest.raises(ValueError, match=model.api_key_env):
        _StubClient(model, [{"type": "x"}])
    credential_class.assert_not_called()


@pytest.mark.parametrize("api_key_env", [None, ""], ids=["none", "empty"])
async def test_no_api_key_env_uses_entra_id_token_provider(
    app_config, monkeypatch, api_key_env
):
    credential = MagicMock()
    credential.close = AsyncMock()
    monkeypatch.setattr(
        llm_client, "DefaultAzureCredential", MagicMock(return_value=credential)
    )
    llm = app_config.model.model_copy(
        update={"api_key": None, "api_key_env": api_key_env}
    )
    async with _StubClient(llm, [{"type": "x"}]) as client:
        # pylint: disable-next=protected-access
        assert callable(client.openai_client._api_key_provider)
    credential.close.assert_awaited_once()


async def test_api_key_skips_azure_credential(app_config, monkeypatch):
    credential_class = MagicMock()
    monkeypatch.setattr(llm_client, "DefaultAzureCredential", credential_class)
    async with _StubClient(app_config.model, [{"type": "x"}]) as client:
        assert client.openai_client.api_key == app_config.model.api_key
    credential_class.assert_not_called()


async def test_exit_closes_credential_when_client_close_fails(
    app_config, monkeypatch
):
    credential = MagicMock()
    credential.close = AsyncMock()
    monkeypatch.setattr(
        llm_client, "DefaultAzureCredential", MagicMock(return_value=credential)
    )
    llm = app_config.model.model_copy(
        update={"api_key": None, "api_key_env": None}
    )
    client = _StubClient(llm, [{"type": "x"}])
    client.openai_client.close = AsyncMock(side_effect=RuntimeError("boom"))
    with pytest.raises(RuntimeError, match="boom"):
        async with client:
            pass
    credential.close.assert_awaited_once()


def test_client_sets_max_retries(app_config):
    client = _StubClient(app_config.model, [{"type": "x"}])
    # pylint: disable-next=protected-access
    assert client.openai_client.max_retries == llm_client._MAX_RETRIES
