"""Unit tests for :mod:`math_ai_agent.llm.llm_client`."""

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
