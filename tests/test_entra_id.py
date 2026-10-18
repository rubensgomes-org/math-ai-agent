"""Unit tests for :mod:`math_ai_agent.config.ms.entra_id`."""

from unittest.mock import MagicMock

from math_ai_agent.config.ms import entra_id


def test_token_provider_uses_cognitive_services_scope(monkeypatch):
    get_provider = MagicMock()
    monkeypatch.setattr(entra_id, "get_bearer_token_provider", get_provider)
    credential = MagicMock()
    assert entra_id.token_provider(credential) is get_provider.return_value
    get_provider.assert_called_once_with(
        credential, entra_id.COGNITIVE_SERVICES_SCOPE
    )
