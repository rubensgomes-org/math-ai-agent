"""Unit tests for :mod:`math_ai_agent.llm.utils`."""

import json
from datetime import date

import pytest
from openai import omit
from openai.types.chat import ChatCompletionMessage

from math_ai_agent.llm import utils
from math_ai_agent.llm.utils import json_for_log, omit_if_none


def test_json_for_log_dumps_sdk_objects_and_falls_back_to_str():
    """SDK objects use model_dump; other unencodable values use str."""
    message = ChatCompletionMessage(role="assistant", content="4 + 4 = 8")
    history = [{"role": "user", "content": "4+4?"}, message, date(2026, 9, 26)]
    assert json.loads(json_for_log(history)) == [
        {"role": "user", "content": "4+4?"},
        {"role": "assistant", "content": "4 + 4 = 8"},
        "2026-09-26",
    ]


def test_json_for_log_truncates_long_output(monkeypatch):
    monkeypatch.setattr(utils, "_MAX_LOG_JSON_CHARS", 10)
    assert json_for_log("a" * 20) == '"aaaaaaaaa... (12 characters truncated)'


def test_json_for_log_keeps_output_at_the_limit(monkeypatch):
    monkeypatch.setattr(utils, "_MAX_LOG_JSON_CHARS", 22)
    assert json_for_log("a" * 20) == '"' + "a" * 20 + '"'


def test_omit_if_none_omits_none():
    assert omit_if_none(None) is omit


@pytest.mark.parametrize("value", [0, 0.0, "", False, 0.7])
def test_omit_if_none_keeps_falsy_and_other_values(value):
    assert omit_if_none(value) == value
