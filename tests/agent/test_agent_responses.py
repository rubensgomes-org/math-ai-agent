"""Unit tests for the ``Agent`` loop over the Responses API."""

import copy
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastmcp.exceptions import ToolError

from math_ai_agent.agent.agent import Agent
from math_ai_agent.agent.errors import (
    ContentFilterError,
    LLMRateLimitedError,
    LLMRequestFailedError,
    MaxTurnsExceededError,
    TokenLimitError,
    UnexpectedResponseError,
)
from math_ai_agent.llm.responses_client import ResponsesClient

from tests.fakes.common import TOOL_RESULT
from tests.fakes.responses import (
    agent_answer,
    make_client,
    make_function_call,
    make_message,
    make_reasoning,
    make_response,
)


@pytest.fixture(params=[False], ids=["stateless"])
def agent_env(app_config, request):
    """Build an ``Agent`` with a fake MCP client and a patched LLM.

    Yields a ``SimpleNamespace`` whose ``responses`` list is consumed
    one entry per ``prompt`` call, whose ``histories`` list
    records a snapshot of the input items sent on each call, whose
    whose ``previous_response_ids`` list records the response ID
    continued on each call, and whose ``call_tool`` mock records every
    dispatched calculator tool call.  The fixture param sets whether
    the client is stateful.
    """
    env = SimpleNamespace(
        responses=[],
        histories=[],
        previous_response_ids=[],
        call_tool=AsyncMock(return_value=TOOL_RESULT),
    )

    async def _next_response(input_items, previous_id):
        env.histories.append(copy.deepcopy(input_items))
        env.previous_response_ids.append(previous_id)
        return env.responses.pop(0)

    env.agent = Agent(
        SimpleNamespace(call_tool=env.call_tool),
        app_config.model,
        make_client(is_stateful=request.param),
    )
    with patch.object(ResponsesClient, "prompt", side_effect=_next_response):
        yield env


# ---------------------------------------------------------------------------
# Agent.run — terminal responses
# ---------------------------------------------------------------------------


async def test_agent_run_returns_output_text_on_completed(agent_env):
    """A "completed" status with no tool calls returns the output text."""
    agent_env.responses = [
        make_response(output=[make_message("The answer is 8")])
    ]
    assert await agent_env.agent.run("4+4?") == agent_answer("The answer is 8")


async def test_agent_run_returns_empty_answer_for_no_output(agent_env):
    """A "completed" status with no output items has empty parts."""
    agent_env.responses = [make_response(output=[])]
    assert await agent_env.agent.run("4+4?") == agent_answer()


async def test_agent_run_handles_missing_usage(agent_env):
    """A response without usage data is logged and does not raise."""
    agent_env.responses = [
        make_response(output=[make_message("8")], usage=None)
    ]
    assert await agent_env.agent.run("4+4?") == agent_answer("8")


async def test_agent_run_sends_user_prompt_without_system_item(agent_env):
    """The first input carries only the user prompt, no system item."""
    agent_env.responses = [make_response(output=[make_message("8")])]
    await agent_env.agent.run("4+4?")
    assert agent_env.histories[0] == [{"role": "user", "content": "4+4?"}]


# ---------------------------------------------------------------------------
# Agent.run — error statuses
# ---------------------------------------------------------------------------


async def test_agent_run_max_output_tokens_raises_token_limit_error(
    agent_env,
):
    """An "incomplete" max_output_tokens response raises TokenLimitError."""
    agent_env.responses = [
        make_response(
            status="incomplete",
            incomplete_details=SimpleNamespace(reason="max_output_tokens"),
        )
    ]
    with pytest.raises(TokenLimitError, match="Token limit reached"):
        await agent_env.agent.run("4+4?")


async def test_agent_run_content_filter_raises_content_filter_error(
    agent_env,
):
    """An "incomplete" content_filter response raises ContentFilterError."""
    agent_env.responses = [
        make_response(
            status="incomplete",
            incomplete_details=SimpleNamespace(reason="content_filter"),
        )
    ]
    with pytest.raises(ContentFilterError, match="blocked for safety"):
        await agent_env.agent.run("4+4?")


async def test_agent_run_unknown_incomplete_reason_raises_unexpected_error(
    agent_env,
):
    """An unrecognised incomplete reason raises UnexpectedResponseError."""
    agent_env.responses = [
        make_response(
            status="incomplete",
            incomplete_details=SimpleNamespace(reason="wat"),
        )
    ]
    with pytest.raises(
        UnexpectedResponseError, match="Unknown incomplete reason: wat"
    ):
        await agent_env.agent.run("4+4?")


async def test_agent_run_missing_incomplete_details_raises_unexpected_error(
    agent_env,
):
    """An "incomplete" status without details raises UnexpectedResponseError."""
    agent_env.responses = [make_response(status="incomplete")]
    with pytest.raises(
        UnexpectedResponseError, match="Unknown incomplete reason: None"
    ):
        await agent_env.agent.run("4+4?")


async def test_agent_run_failed_raises_llm_request_failed_error(agent_env):
    """A "failed" status raises LLMRequestFailedError naming its code."""
    agent_env.responses = [
        make_response(
            status="failed",
            error=SimpleNamespace(code="server_error", message="upstream 502"),
        )
    ]
    with pytest.raises(LLMRequestFailedError, match="upstream 502") as info:
        await agent_env.agent.run("4+4?")
    assert type(info.value) is LLMRequestFailedError
    assert "code=server_error" in str(info.value)


async def test_agent_run_rate_limited_raises_rate_limited_error(agent_env):
    """A "failed" status with a rate limit code raises LLMRateLimitedError."""
    agent_env.responses = [
        make_response(
            status="failed",
            error=SimpleNamespace(
                code="rate_limit_exceeded", message="slow down"
            ),
        )
    ]
    with pytest.raises(LLMRateLimitedError, match="slow down"):
        await agent_env.agent.run("4+4?")


async def test_agent_run_failed_without_error_raises_llm_error(agent_env):
    """A "failed" status with no error object has no error code."""
    agent_env.responses = [make_response(status="failed")]
    with pytest.raises(LLMRequestFailedError, match="unknown error") as info:
        await agent_env.agent.run("4+4?")
    assert "code=None" in str(info.value)


@pytest.mark.parametrize("status", ["wat", "queued", "in_progress"])
async def test_agent_run_unknown_status_raises_unexpected_error(
    agent_env, status
):
    """A non-final or unknown status raises UnexpectedResponseError."""
    agent_env.responses = [make_response(status=status)]
    expected = f"Non-supported response status: {status}"
    with pytest.raises(UnexpectedResponseError, match=expected):
        await agent_env.agent.run("4+4?")


async def test_agent_run_stops_at_turn_limit(app_config, agent_env):
    """An LLM that keeps calling tools fails after max_turns turns."""
    agent_env.agent = Agent(
        SimpleNamespace(call_tool=agent_env.call_tool),
        app_config.model,
        make_client(),
        max_turns=2,
    )
    agent_env.responses = [
        make_response(output=[make_function_call()]) for _ in range(3)
    ]
    with pytest.raises(MaxTurnsExceededError, match="after 2 turns"):
        await agent_env.agent.run("4+4?")
    assert len(agent_env.histories) == 2


# ---------------------------------------------------------------------------
# Agent.run — continue branches
# ---------------------------------------------------------------------------


async def test_agent_run_dispatches_tool_call(agent_env):
    """A function_call item dispatches to the MCP calculator."""
    agent_env.responses = [
        make_response(output=[make_function_call()]),
        make_response(output=[make_message("4 + 4 = 8")]),
    ]
    assert await agent_env.agent.run("4+4?") == agent_answer("4 + 4 = 8")
    agent_env.call_tool.assert_awaited_once_with("add", {"a": 4, "b": 4})


async def test_agent_run_returns_tool_error_to_llm(agent_env):
    """A tool error is sent to the LLM as the tool output."""
    agent_env.call_tool.side_effect = ToolError(
        "Error calling tool 'divide': Cannot divide by zero"
    )
    agent_env.responses = [
        make_response(output=[make_function_call(name="divide")]),
        make_response(output=[make_message("undefined")]),
    ]
    assert await agent_env.agent.run("10/0?") == agent_answer("undefined")
    assert agent_env.histories[1][-1]["output"] == (
        "Error calling tool 'divide': Cannot divide by zero"
    )


@pytest.mark.parametrize(
    "arguments, message",
    [
        ("{bad", "invalid JSON arguments"),
        ("[4, 4]", "arguments must be a JSON object"),
    ],
)
async def test_agent_run_returns_invalid_arguments_to_llm(
    agent_env, arguments, message
):
    """Invalid tool arguments are sent to the LLM without a tool call."""
    agent_env.responses = [
        make_response(output=[make_function_call(arguments=arguments)]),
        make_response(output=[make_message("done")]),
    ]
    assert await agent_env.agent.run("4+4?") == agent_answer("done")
    agent_env.call_tool.assert_not_awaited()
    assert message in agent_env.histories[1][-1]["output"]


async def test_agent_run_dispatches_multiple_tool_calls(agent_env):
    """Every function_call item in one response is dispatched in order."""
    agent_env.responses = [
        make_response(
            output=[
                make_function_call(call_id="c1", name="add"),
                make_function_call(
                    call_id="c2", name="multiply", arguments='{"a": 2, "b": 3}'
                ),
            ]
        ),
        make_response(output=[make_message("done")]),
    ]
    assert await agent_env.agent.run("compute") == agent_answer("done")
    assert agent_env.call_tool.await_count == 2
    assert [c.args[0] for c in agent_env.call_tool.await_args_list] == [
        "add",
        "multiply",
    ]


async def test_agent_run_replays_output_items_and_tool_output(agent_env):
    """Output items are echoed back followed by function_call_output."""
    agent_env.responses = [
        make_response(output=[make_message("plan"), make_function_call()]),
        make_response(output=[make_message("done")]),
    ]
    await agent_env.agent.run("4+4?")

    second_history = agent_env.histories[1]
    assert second_history[0] == {"role": "user", "content": "4+4?"}
    assert second_history[1]["type"] == "message"
    assert second_history[2]["type"] == "function_call"
    assert second_history[2]["call_id"] == "call-1"
    assert second_history[3] == {
        "type": "function_call_output",
        "call_id": "call-1",
        "output": "8",
    }
    assert agent_env.previous_response_ids == [None, None]


@pytest.mark.parametrize("agent_env", [True], ids=["stateful"], indirect=True)
async def test_agent_run_stateful_sends_only_tool_output(agent_env):
    """A stateful turn sends only new items and continues the response."""
    agent_env.responses = [
        make_response(
            response_id="resp-1",
            output=[make_message("plan"), make_function_call()],
        ),
        make_response(response_id="resp-2", output=[make_message("done")]),
    ]
    answer = await agent_env.agent.run("4+4?")

    assert answer == agent_answer(final="done")
    assert agent_env.histories == [
        [{"role": "user", "content": "4+4?"}],
        [{"type": "function_call_output", "call_id": "call-1", "output": "8"}],
    ]
    assert agent_env.previous_response_ids == [None, "resp-1"]


# ---------------------------------------------------------------------------
# Agent.run — reasoning sections
# ---------------------------------------------------------------------------


async def test_agent_run_includes_reasoning_from_every_turn(agent_env):
    """Reasoning text from all turns is joined in order."""
    agent_env.responses = [
        make_response(
            output=[
                make_reasoning(["Plan: add."], ["Need 4 + 4."]),
                make_function_call(),
            ]
        ),
        make_response(
            output=[
                make_reasoning(["Report."], ["Tool said 8."]),
                make_message("4 + 4 = 8"),
            ]
        ),
    ]
    assert await agent_env.agent.run("4+4?") == agent_answer(
        final="4 + 4 = 8", reasoning="Need 4 + 4.\nTool said 8."
    )


async def test_agent_run_strips_final_response(agent_env):
    """The final response and reasoning are returned without whitespace."""
    agent_env.responses = [
        make_response(
            output=[
                make_reasoning(texts=["Need 4 + 4."]),
                make_message("  4 + 4 = 8\n"),
            ]
        ),
    ]
    assert await agent_env.agent.run("4+4?") == agent_answer(
        final="4 + 4 = 8", reasoning="Need 4 + 4."
    )


async def test_agent_run_strips_blank_lines_from_answer(agent_env):
    """Whitespace around each text adds no blank lines to the reasoning."""
    agent_env.responses = [
        make_response(
            output=[
                make_reasoning(texts=["\nUse divide tool.\n\n", "  \n"]),
                make_function_call(),
            ]
        ),
        make_response(
            output=[
                make_reasoning(texts=["\n\nProvide answer.\n"]),
                make_message("\nThe result is 97.39.\n\n"),
            ]
        ),
    ]
    assert await agent_env.agent.run("4+4?") == agent_answer(
        final="The result is 97.39.",
        reasoning="Use divide tool.\nProvide answer.",
    )


async def test_agent_run_uses_summary_without_content(agent_env):
    """A reasoning item with only a summary shows the summary."""
    agent_env.responses = [
        make_response(
            output=[make_reasoning(["Short plan."]), make_message("8")]
        )
    ]
    assert await agent_env.agent.run("4+4?") == agent_answer(
        final="8", reasoning="Short plan."
    )
