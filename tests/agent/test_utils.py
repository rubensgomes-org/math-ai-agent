"""Unit tests for the agent loop helpers."""

import pytest
from openai.types.responses import (
    Response,
    ResponseOutputMessage,
    ResponseOutputText,
    ResponseReasoningItem,
)
from openai.types.responses.response_reasoning_item import Content, Summary

from math_ai_agent.agent.utils import (
    join_reasoning,
    reasoning_texts,
    replay_input,
)


def _reasoning(summaries=(), texts=None):
    return ResponseReasoningItem(
        id="rs-1",
        summary=[Summary(text=text, type="summary_text") for text in summaries],
        content=(
            None
            if texts is None
            else [Content(text=text, type="reasoning_text") for text in texts]
        ),
        type="reasoning",
    )


def _message(text):
    return ResponseOutputMessage(
        id="msg-1",
        content=[
            ResponseOutputText(text=text, type="output_text", annotations=[])
        ],
        role="assistant",
        status="completed",
        type="message",
    )


def _response(output):
    return Response(
        id="resp-1",
        created_at=0,
        model="m",
        object="response",
        output=output,
        parallel_tool_calls=True,
        tool_choice="auto",
        tools=[],
    )


@pytest.mark.parametrize(
    "item, expected",
    [
        (_reasoning(["summary"], ["content"]), ["content"]),
        (_reasoning(["summary"], []), ["summary"]),
        (_reasoning(["summary"]), ["summary"]),
        (_reasoning(), []),
    ],
    ids=["content", "empty-content", "summary-only", "no-text"],
)
def test_reasoning_texts_prefers_content_over_summary(item, expected):
    assert reasoning_texts(_response([item])) == expected


def test_reasoning_texts_ignores_non_reasoning_items():
    assert reasoning_texts(_response([_message("answer")])) == []


def test_replay_input_appends_outputs_then_tool_outputs():
    history = [{"role": "user", "content": "4+4?"}]
    tool_output = {
        "type": "function_call_output",
        "call_id": "c",
        "output": "8",
    }
    reasoning = _reasoning(["plan"])

    result = replay_input(history, [reasoning], [tool_output])

    assert result == [
        history[0],
        reasoning.model_dump(exclude_none=True),
        tool_output,
    ]
    assert history == [{"role": "user", "content": "4+4?"}]


@pytest.mark.parametrize(
    "reasoning, expected",
    [
        (["a", "b"], "a\nb"),
        ([" a \n", "  "], "a"),
        ([], None),
        (["  "], None),
    ],
    ids=["joined", "strips-whitespace", "empty", "blank"],
)
def test_join_reasoning(reasoning, expected):
    assert join_reasoning(reasoning) == expected
