"""Unit tests for the ``Agent`` loop over the Chat Completions API."""

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import mcp_types
import pytest
from fastmcp.exceptions import ToolError
from openai.types.chat import ChatCompletionMessageCustomToolCall
from openai.types.chat.chat_completion_message_custom_tool_call import Custom

from math_ai_agent.agent.agent import Agent
from math_ai_agent.agent.errors import (
    ContentFilterError,
    MaxTurnsExceededError,
    TokenLimitError,
    UnexpectedResponseError,
)
from math_ai_agent.llm.chat_completions_client import ChatCompletionsClient

from tests.fakes.chat import make_chat_completion, make_tool_call
from tests.fakes.common import ADD_TOOL, TOOL_RESULT, llm_config


@pytest.fixture()
def agent_env(app_config):
    """Build an ``Agent`` with a fake MCP client and a patched LLM.

    Yields a ``SimpleNamespace`` whose ``responses`` list is consumed
    one entry per ``prompt`` call, whose ``histories`` list
    records a snapshot of the history sent on each call, and whose
    ``call_tool`` mock records every dispatched calculator tool call.
    """
    env = SimpleNamespace(
        responses=[],
        histories=[],
        call_tool=AsyncMock(return_value=TOOL_RESULT),
    )

    async def _next_response(history):
        env.histories.append(list(history))
        return env.responses.pop(0)

    env.agent = Agent(
        SimpleNamespace(call_tool=env.call_tool),
        app_config.model,
        ChatCompletionsClient(llm_config(), [ADD_TOOL]),
    )
    with patch.object(
        ChatCompletionsClient, "prompt", side_effect=_next_response
    ):
        yield env


async def test_agent_context_manager_closes_llm_client(agent_env):
    with patch.object(
        ChatCompletionsClient,
        "__aexit__",
        new_callable=AsyncMock,
        return_value=None,
    ) as mock_close:
        async with agent_env.agent as agent:
            assert agent is agent_env.agent
            mock_close.assert_not_awaited()
    mock_close.assert_awaited_once()


# ---------------------------------------------------------------------------
# Agent.run — terminal responses
# ---------------------------------------------------------------------------


async def test_agent_run_returns_content_on_stop(agent_env):
    """A "stop" finish_reason returns the assistant message content."""
    agent_env.responses = [make_chat_completion(content="The answer is 8")]
    assert (await agent_env.agent.run("4+4?")).answer == "The answer is 8"


async def test_agent_run_returns_empty_string_for_none_content(agent_env):
    """A "stop" with no content returns an empty string, not None."""
    agent_env.responses = [make_chat_completion(content=None)]
    assert (await agent_env.agent.run("4+4?")).answer == ""


async def test_agent_run_handles_missing_usage(agent_env):
    """A response without usage data is logged and does not raise."""
    agent_env.responses = [make_chat_completion(content="8", usage=None)]
    assert (await agent_env.agent.run("4+4?")).answer == "8"


# ---------------------------------------------------------------------------
# Agent.run — error finish reasons
# ---------------------------------------------------------------------------


async def test_agent_run_length_raises_token_limit_error(agent_env):
    """A "length" finish_reason raises TokenLimitError."""
    agent_env.responses = [make_chat_completion(finish_reason="length")]
    with pytest.raises(TokenLimitError, match="Token limit reached"):
        await agent_env.agent.run("4+4?")


async def test_agent_run_content_filter_raises_content_filter_error(
    agent_env,
):
    """A "content_filter" finish_reason raises ContentFilterError."""
    agent_env.responses = [make_chat_completion(finish_reason="content_filter")]
    with pytest.raises(ContentFilterError, match="blocked for safety"):
        await agent_env.agent.run("4+4?")


async def test_agent_run_unknown_reason_raises_unexpected_error(agent_env):
    """An unrecognised finish_reason raises UnexpectedResponseError."""
    agent_env.responses = [make_chat_completion(finish_reason="wat")]
    with pytest.raises(
        UnexpectedResponseError, match="Non-supported finish_reason: wat"
    ):
        await agent_env.agent.run("4+4?")


async def test_agent_run_none_reason_raises_unexpected_error(agent_env):
    """A missing finish_reason raises UnexpectedResponseError."""
    agent_env.responses = [make_chat_completion(finish_reason=None)]
    with pytest.raises(
        UnexpectedResponseError, match="Non-supported finish_reason: None"
    ):
        await agent_env.agent.run("4+4?")


async def test_agent_run_no_choices_raises_unexpected_error(agent_env):
    """A response without choices raises UnexpectedResponseError."""
    response = make_chat_completion()
    response.choices = []
    agent_env.responses = [response]
    with pytest.raises(UnexpectedResponseError, match="no choices"):
        await agent_env.agent.run("4+4?")


async def test_agent_run_custom_tool_call_raises_unexpected_error(agent_env):
    """A non-function tool call raises UnexpectedResponseError."""
    custom_call = ChatCompletionMessageCustomToolCall(
        id="call-1", type="custom", custom=Custom(name="add", input="4 4")
    )
    agent_env.responses = [
        make_chat_completion(
            content=None, tool_calls=[custom_call], finish_reason="tool_calls"
        )
    ]
    with pytest.raises(UnexpectedResponseError, match="type: custom"):
        await agent_env.agent.run("4+4?")
    agent_env.call_tool.assert_not_awaited()


async def test_agent_run_content_filter_omits_history(agent_env):
    """The content filter error names the turn, not the conversation."""
    agent_env.responses = [make_chat_completion(finish_reason="content_filter")]
    with pytest.raises(ContentFilterError) as error:
        await agent_env.agent.run("secret prompt")
    assert "secret prompt" not in str(error.value)
    assert "turn 1" in str(error.value)


async def test_agent_run_stops_at_turn_limit(app_config, agent_env):
    """An LLM that keeps calling tools fails after max_turns turns."""
    agent_env.agent = Agent(
        SimpleNamespace(call_tool=agent_env.call_tool),
        app_config.model,
        ChatCompletionsClient(llm_config(), [ADD_TOOL]),
        max_turns=2,
    )
    agent_env.responses = [
        make_chat_completion(
            content=None,
            tool_calls=[make_tool_call()],
            finish_reason="tool_calls",
        )
        for _ in range(3)
    ]
    with pytest.raises(MaxTurnsExceededError, match="after 2 turns"):
        await agent_env.agent.run("4+4?")
    assert len(agent_env.histories) == 2


async def test_agent_run_tool_calls_without_calls_raises(agent_env):
    """A "tool_calls" finish without tool calls raises an error."""
    agent_env.responses = [
        make_chat_completion(content=None, finish_reason="tool_calls")
    ]
    with pytest.raises(UnexpectedResponseError, match="no tool calls"):
        await agent_env.agent.run("4+4?")


async def test_agent_run_logs_history_at_debug(agent_env, caplog):
    """The history is logged only at DEBUG level."""
    caplog.set_level(logging.DEBUG, logger="math_ai_agent.agent.agent")
    agent_env.responses = [make_chat_completion(content="8")]
    await agent_env.agent.run("4+4?")
    assert "history:" in caplog.text


async def test_agent_run_sends_tool_text_when_no_structured_data(agent_env):
    """A tool result without data sends its text content to the LLM."""
    agent_env.call_tool.return_value = SimpleNamespace(
        data=None,
        structured_content=None,
        content=[mcp_types.TextContent(type="text", text="8")],
    )
    agent_env.responses = [
        make_chat_completion(
            content=None,
            tool_calls=[make_tool_call()],
            finish_reason="tool_calls",
        ),
        make_chat_completion(content="done"),
    ]
    assert (await agent_env.agent.run("4+4?")).answer == "done"
    assert agent_env.histories[1][-1]["content"] == "8"


# ---------------------------------------------------------------------------
# Agent.run — continue branches
# ---------------------------------------------------------------------------


async def test_agent_run_dispatches_tool_call(agent_env):
    """A tool_calls response dispatches to the MCP calculator."""
    agent_env.responses = [
        make_chat_completion(
            content=None,
            tool_calls=[make_tool_call()],
            finish_reason="tool_calls",
        ),
        make_chat_completion(content="4 + 4 = 8"),
    ]
    assert (await agent_env.agent.run("4+4?")).answer == "4 + 4 = 8"
    agent_env.call_tool.assert_awaited_once_with("add", {"a": 4, "b": 4})


async def test_agent_run_history_starts_with_user_prompt(agent_env):
    """The history holds only conversation items, not the system message."""
    agent_env.responses = [make_chat_completion(content="8")]
    await agent_env.agent.run("4+4?")
    assert agent_env.histories[0] == [{"role": "user", "content": "4+4?"}]


async def test_agent_run_returns_tool_error_to_llm(agent_env):
    """A tool error is sent to the LLM as the tool message content."""
    agent_env.call_tool.side_effect = ToolError(
        "Error calling tool 'divide': Cannot divide by zero"
    )
    agent_env.responses = [
        make_chat_completion(
            content=None,
            tool_calls=[make_tool_call(name="divide")],
            finish_reason="tool_calls",
        ),
        make_chat_completion(content="undefined"),
    ]
    assert (await agent_env.agent.run("10/0?")).answer == "undefined"
    assert agent_env.histories[1][-1] == {
        "role": "tool",
        "tool_call_id": "call-1",
        "content": "Error calling tool 'divide': Cannot divide by zero",
    }


async def test_agent_run_returns_invalid_json_arguments_to_llm(agent_env):
    """Invalid JSON arguments are sent to the LLM without a tool call."""
    agent_env.responses = [
        make_chat_completion(
            content=None,
            tool_calls=[make_tool_call(arguments="{bad")],
            finish_reason="tool_calls",
        ),
        make_chat_completion(content="done"),
    ]
    assert (await agent_env.agent.run("4+4?")).answer == "done"
    agent_env.call_tool.assert_not_awaited()
    assert "invalid JSON arguments" in agent_env.histories[1][-1]["content"]


async def test_agent_run_dispatches_multiple_tool_calls(agent_env):
    """Every tool call in one response is dispatched in order."""
    agent_env.responses = [
        make_chat_completion(
            content=None,
            tool_calls=[
                make_tool_call(call_id="c1", name="add"),
                make_tool_call(
                    call_id="c2", name="multiply", arguments='{"a": 2, "b": 3}'
                ),
            ],
            finish_reason="tool_calls",
        ),
        make_chat_completion(content="done"),
    ]
    assert (await agent_env.agent.run("compute")).answer == "done"
    assert agent_env.call_tool.await_count == 2
    assert [c.args[0] for c in agent_env.call_tool.await_args_list] == [
        "add",
        "multiply",
    ]
