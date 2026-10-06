"""Unit tests for :mod:`math_ai_agent.llm.llm_client`."""

import pytest

from math_ai_agent.llm.llm_client import LLMClient


def test_llm_client_is_abstract(app_config):
    """LLMClient cannot be instantiated without its abstract methods."""
    with pytest.raises(TypeError):
        # pylint: disable-next=abstract-class-instantiated
        LLMClient(app_config.llm, [{"type": "x"}])
