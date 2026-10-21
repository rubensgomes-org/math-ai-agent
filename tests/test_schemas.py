"""Unit tests for :mod:`math_ai_agent.schemas`."""

import pytest
from pydantic import ValidationError

from math_ai_agent.schemas import (
    MAX_PROMPT_CHARS,
    PromptRequest,
    PromptResponse,
)


def test_prompt_request_defaults_to_display_reasoning():
    request = PromptRequest(text="What is 5*3?")
    assert request.text == "What is 5*3?"
    assert request.display_reasoning is True


def test_prompt_request_requires_text():
    with pytest.raises(ValidationError):
        PromptRequest()  # type: ignore[call-arg]


def test_prompt_request_accepts_text_at_the_limit():
    text = "x" * MAX_PROMPT_CHARS
    assert PromptRequest(text=text).text == text


@pytest.mark.parametrize(
    "fields",
    [
        {"text": 123},
        {"text": "1+1?", "display_reasoning": "false"},
        {"text": "1+1?", "display_reasoning": 0},
        {"text": "1+1?", "unknown": True},
    ],
    ids=["text-not-string", "bool-as-string", "bool-as-int", "unknown-field"],
)
def test_prompt_request_rejects_invalid_fields(fields):
    with pytest.raises(ValidationError):
        PromptRequest.model_validate(fields)


def test_prompt_request_is_frozen():
    request = PromptRequest(text="1+1?")
    with pytest.raises(ValidationError):
        request.text = "changed"  # type: ignore[misc]


def test_prompt_response_is_frozen():
    response = PromptResponse(answer="2")
    with pytest.raises(ValidationError):
        response.answer = "changed"  # type: ignore[misc]


def test_prompt_response_reasoning_defaults_to_none():
    assert PromptResponse(answer="2").reasoning is None
