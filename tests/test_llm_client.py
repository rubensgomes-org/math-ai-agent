"""Unit tests for :mod:`math_ai_agent.llm.llm_client`."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from math_ai_agent.llm import llm_client
from math_ai_agent.llm.llm_client import LLMClient


def test_llm_client_is_abstract(app_config):
    """LLMClient cannot be instantiated without its abstract methods."""
    with pytest.raises(TypeError):
        # pylint: disable-next=abstract-class-instantiated
        LLMClient(app_config.llm, [{"type": "x"}])


@pytest.mark.parametrize(
    ("secret", "masked"),
    [
        ("sk-abcdef123456", "****3456"),
        ("12345", "****2345"),
        ("1234", "****"),
        ("", "****"),
    ],
)
def test_mask_secret_shows_only_last_four_characters(secret, masked):
    # pylint: disable-next=protected-access
    assert llm_client._mask_secret(secret) == masked


class _StubClient(LLMClient):
    """Concrete ``LLMClient`` for exercising the base class."""

    async def prompt(self, history):
        raise NotImplementedError

    @staticmethod
    def log_token_usage(response):
        raise NotImplementedError


async def test_is_azure_uses_entra_id_token_provider(app_config, monkeypatch):
    credential = MagicMock()
    credential.close = AsyncMock()
    monkeypatch.setattr(
        llm_client, "DefaultAzureCredential", MagicMock(return_value=credential)
    )
    llm = app_config.llm.model_copy(update={"is_azure": True})
    async with _StubClient(llm, [{"type": "x"}]) as client:
        # pylint: disable-next=protected-access
        assert callable(client.openai_client._api_key_provider)
    credential.close.assert_awaited_once()


async def test_api_key_used_without_is_azure(app_config, monkeypatch):
    credential_class = MagicMock()
    monkeypatch.setattr(llm_client, "DefaultAzureCredential", credential_class)
    async with _StubClient(app_config.llm, [{"type": "x"}]) as client:
        assert client.openai_client.api_key == app_config.llm.api_key
    credential_class.assert_not_called()
