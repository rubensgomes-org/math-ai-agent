"""Unit tests for :mod:`math_ai_agent.config.key_vault`.

This project's source code and documentation were generated with the
assistance of Artificial Intelligence (AI). For more information, please
refer to the `AI_DISCLAIMER.md` document located in the project's root
directory.
"""

from unittest.mock import MagicMock

import pytest

from math_ai_agent.config import key_vault

VAULT_URI = "https://kv-test.vault.azure.net/"


@pytest.fixture()
def client(monkeypatch):
    """Patch the credential and ``SecretClient``; return the client mock."""
    client = MagicMock()
    secret_client = MagicMock()
    secret_client.return_value.__enter__.return_value = client
    monkeypatch.setattr(key_vault, "DefaultAzureCredential", MagicMock())
    monkeypatch.setattr(key_vault, "SecretClient", secret_client)
    return client


@pytest.mark.parametrize(
    ("env_var", "expected"),
    [
        ("FOUNDRY_API_KEY", "ca-mathagent--FOUNDRY-API-KEY"),
        ("OPENAI-API-KEY", "ca-mathagent--OPENAI-API-KEY"),
    ],
)
def test_secret_name(env_var, expected):
    assert key_vault.secret_name(env_var) == expected


def test_read_secret_returns_value(client):
    client.get_secret.return_value.value = "secret-value"
    assert key_vault.read_secret(VAULT_URI, "name") == "secret-value"
    client.get_secret.assert_called_once_with("name")


@pytest.mark.parametrize("value", [None, ""])
def test_read_secret_empty_raises(client, value):
    client.get_secret.return_value.value = value
    with pytest.raises(ValueError, match="name"):
        key_vault.read_secret(VAULT_URI, "name")


def test_read_secret_propagates_errors(client):
    client.get_secret.side_effect = RuntimeError("forbidden")
    with pytest.raises(RuntimeError, match="forbidden"):
        key_vault.read_secret(VAULT_URI, "name")
