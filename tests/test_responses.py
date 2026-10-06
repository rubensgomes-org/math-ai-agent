"""Unit tests for the Responses API path in :mod:`math_ai_agent.llm`."""

import copy
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import mcp_types
import pytest
from fastmcp.exceptions import ToolError
from openai import omit
from openai.types.responses import (
    ResponseFunctionToolCall,
    ResponseOutputMessage,
    ResponseOutputText,
    ResponseReasoningItem,
)
from openai.types.responses.response_reasoning_item import Content, Summary

from math_ai_agent.agent.agent import Agent
from math_ai_agent.config.config import LLMConfig
from math_ai_agent.llm.llm_errors import (
    ContentFilterError,
    LLMRequestFailedError,
    TokenLimitError,
)
from math_ai_agent.llm.responses_client import ResponsesClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_API_KEY_ENV = "TEST_LLM_KEY"
_BASE_URL = "http://localhost:11434/v1"
_MODEL = "test-model"
_INSTRUCTIONS = "Test instructions."
_USAGE = SimpleNamespace(
    input_tokens=10,
    output_tokens=5,
    total_tokens=15,
)
_TOOL_RESULT = SimpleNamespace(data=8, structured_content={"result": 8})
_ADD_TOOL = mcp_types.Tool(
    name="add",
    description="Add two numbers",
    input_schema={
        "type": "object",
        "properties": {
            "a": {"type": "number"},
            "b": {"type": "number"},
        },
        "required": ["a", "b"],
    },
)
# The Responses tool definitions the client sends for _ADD_TOOL.
_TOOLS = [
    {
        "type": "function",
        "name": "add",
        "description": "Add two numbers",
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
            "required": ["a", "b"],
        },
    }
]


def _make_message(text="42"):
    """Build a Responses output message item carrying ``text``."""
    return ResponseOutputMessage(
        id="msg-1",
        content=[
            ResponseOutputText(annotations=[], text=text, type="output_text")
        ],
        role="assistant",
        status="completed",
        type="message",
    )


def _make_reasoning(summaries=(), texts=None):
    """Build a Responses ``reasoning`` output item."""
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


def _answer(final="(none)", reasoning="(none)"):
    """Build the expected formatted answer returned by ``Agent.run``."""
    return f"reasoning:\n{reasoning}\n\nfinal response:\n{final}"


def _make_function_call(
    call_id="call-1", name="add", arguments='{"a": 4, "b": 4}'
):
    """Build a Responses ``function_call`` output item."""
    return ResponseFunctionToolCall(
        call_id=call_id,
        name=name,
        arguments=arguments,
        type="function_call",
    )


def _make_response(
    status="completed",
    response_id="resp-1",
    output=None,
    usage=_USAGE,
    incomplete_details=None,
    error=None,
):
    """Build a fake Response-like object for the Responses API."""
    if output is None:
        output = [_make_message()]
    output_text = "".join(
        part.text
        for item in output
        if isinstance(item, ResponseOutputMessage)
        for part in item.content
        if isinstance(part, ResponseOutputText)
    )
    response = SimpleNamespace(
        id=response_id,
        status=status,
        output=output,
        output_text=output_text,
        usage=usage,
        incomplete_details=incomplete_details,
        error=error,
    )
    response.model_dump = lambda **_: {
        "status": status,
        "output": [item.model_dump() for item in output],
    }
    return response


def _llm_config(**updates) -> LLMConfig:
    """Build an ``LLMConfig`` with test values and ``updates`` applied."""
    return LLMConfig(
        model_base_url=_BASE_URL,
        model=_MODEL,
        api_key_env=_API_KEY_ENV,
        system_instructions=_INSTRUCTIONS,
        **updates,
    )


def _make_client(is_stateful=False):
    """Create a ResponsesClient instance with test parameters."""
    return ResponsesClient(_llm_config(is_stateful=is_stateful), [_ADD_TOOL])


# ---------------------------------------------------------------------------
# __init__ — validation
# ---------------------------------------------------------------------------


def test_init_sets_instance_attributes():
    """Instantiation sets instance attributes."""
    client = ResponsesClient(_llm_config(), [_ADD_TOOL])
    assert client.openai_client is not None
    assert client.tools == _TOOLS
    assert client.model == _MODEL
    assert isinstance(client, ResponsesClient)


def test_init_empty_tools_raises():
    """Empty tools list raises ValueError."""
    with pytest.raises(ValueError, match="tools must not be empty"):
        ResponsesClient(_llm_config(), [])


# ---------------------------------------------------------------------------
# _format_tools
# ---------------------------------------------------------------------------


_MCP_TOOLS = [
    mcp_types.Tool(
        name="add",
        description="Add two numbers",
        input_schema={"type": "object", "properties": {}},
    ),
    mcp_types.Tool(
        name="noop", input_schema={"type": "object", "properties": {}}
    ),
]

_TOOLS_DEFINITIONS = [
    {
        "name": "add",
        "description": "Add two numbers",
        "parameters": {"type": "object", "properties": {}},
    },
    {"name": "noop", "parameters": {"type": "object", "properties": {}}},
]


def test_format_tools_flattens_each_definition():
    """Each definition becomes a flat Responses function tool."""
    # pylint: disable-next=protected-access
    assert ResponsesClient._format_tools(_MCP_TOOLS) == [
        {"type": "function", **definition} for definition in _TOOLS_DEFINITIONS
    ]


def test_format_tools_empty_list():
    # pylint: disable-next=protected-access
    assert ResponsesClient._format_tools([]) == []


# ---------------------------------------------------------------------------
# prompt
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prompt_returns_response():
    """prompt returns the Response from the API."""
    fake_response = _make_response(output=[_make_message("The answer is 8")])
    client = _make_client()

    mock_create = AsyncMock(return_value=fake_response)
    client.openai_client.responses = SimpleNamespace(create=mock_create)

    history = [{"role": "user", "content": "4+4?"}]
    result = await client.prompt(history)

    assert result is fake_response
    assert result.output_text == "The answer is 8"


@pytest.mark.asyncio
async def test_prompt_sends_expected_arguments():
    """prompt sends input, tools, instructions and store=False."""
    fake_response = _make_response()
    client = _make_client()

    mock_create = AsyncMock(return_value=fake_response)
    client.openai_client.responses = SimpleNamespace(create=mock_create)

    history = [{"role": "user", "content": "4+4?"}]
    await client.prompt(history)

    mock_create.assert_awaited_once_with(
        model=_MODEL,
        input=history,
        tools=_TOOLS,
        instructions=_INSTRUCTIONS,
        store=False,
        previous_response_id=omit,
        temperature=omit,
    )


@pytest.mark.asyncio
async def test_prompt_stateful_sends_previous_response_id():
    """A stateful client stores and continues the previous response."""
    client = _make_client(is_stateful=True)

    mock_create = AsyncMock(return_value=_make_response())
    client.openai_client.responses = SimpleNamespace(create=mock_create)

    tool_output = {
        "type": "function_call_output",
        "call_id": "c",
        "output": "8",
    }
    await client.prompt([tool_output], "resp-1")

    mock_create.assert_awaited_once_with(
        model=_MODEL,
        input=[tool_output],
        tools=_TOOLS,
        instructions=_INSTRUCTIONS,
        store=True,
        previous_response_id="resp-1",
        temperature=omit,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("temperature", [0.0, 0.2])
async def test_prompt_sends_temperature(temperature):
    """A set temperature is sent, including 0."""
    client = ResponsesClient(_llm_config(temperature=temperature), [_ADD_TOOL])
    mock_create = AsyncMock(return_value=_make_response())
    client.openai_client.responses = SimpleNamespace(create=mock_create)

    await client.prompt([{"role": "user", "content": "4+4?"}])

    assert mock_create.await_args.kwargs["temperature"] == temperature


@pytest.mark.asyncio
async def test_prompt_with_function_call():
    """prompt handles a response with a function_call item."""
    fake_response = _make_response(output=[_make_function_call()])
    client = _make_client()

    mock_create = AsyncMock(return_value=fake_response)
    client.openai_client.responses = SimpleNamespace(create=mock_create)

    result = await client.prompt([{"role": "user", "content": "4+4?"}])

    assert result.output_text == ""
    assert result.output[0].name == "add"


# ---------------------------------------------------------------------------
# Agent.run — helpers
# ---------------------------------------------------------------------------


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
    app_config.llm.api_style = "responses"
    env = SimpleNamespace(
        responses=[],
        histories=[],
        previous_response_ids=[],
        call_tool=AsyncMock(return_value=_TOOL_RESULT),
    )

    async def _next_response(input_items, previous_id):
        env.histories.append(copy.deepcopy(input_items))
        env.previous_response_ids.append(previous_id)
        return env.responses.pop(0)

    env.agent = Agent(
        SimpleNamespace(call_tool=env.call_tool),
        _make_client(is_stateful=request.param),
    )
    with patch.object(ResponsesClient, "prompt", side_effect=_next_response):
        yield env


# ---------------------------------------------------------------------------
# Agent.run — terminal responses
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_run_returns_output_text_on_completed(agent_env):
    """A "completed" status with no tool calls returns the output text."""
    agent_env.responses = [
        _make_response(output=[_make_message("The answer is 8")])
    ]
    assert await agent_env.agent.run("4+4?") == _answer("The answer is 8")


@pytest.mark.asyncio
async def test_agent_run_shows_none_for_no_output(agent_env):
    """A "completed" status with no output items shows (none) everywhere."""
    agent_env.responses = [_make_response(output=[])]
    assert await agent_env.agent.run("4+4?") == _answer()


@pytest.mark.asyncio
async def test_agent_run_handles_missing_usage(agent_env):
    """A response without usage data is logged and does not raise."""
    agent_env.responses = [
        _make_response(output=[_make_message("8")], usage=None)
    ]
    assert await agent_env.agent.run("4+4?") == _answer("8")


@pytest.mark.asyncio
async def test_agent_run_sends_user_prompt_without_system_item(agent_env):
    """The first input carries only the user prompt, no system item."""
    agent_env.responses = [_make_response(output=[_make_message("8")])]
    await agent_env.agent.run("4+4?")
    assert agent_env.histories[0] == [{"role": "user", "content": "4+4?"}]


# ---------------------------------------------------------------------------
# Agent.run — error statuses
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_run_max_output_tokens_raises_token_limit_error(
    agent_env,
):
    """An "incomplete" max_output_tokens response raises TokenLimitError."""
    agent_env.responses = [
        _make_response(
            status="incomplete",
            incomplete_details=SimpleNamespace(reason="max_output_tokens"),
        )
    ]
    with pytest.raises(TokenLimitError, match="Token limit reached"):
        await agent_env.agent.run("4+4?")


@pytest.mark.asyncio
async def test_agent_run_content_filter_raises_content_filter_error(
    agent_env,
):
    """An "incomplete" content_filter response raises ContentFilterError."""
    agent_env.responses = [
        _make_response(
            status="incomplete",
            incomplete_details=SimpleNamespace(reason="content_filter"),
        )
    ]
    with pytest.raises(ContentFilterError, match="blocked for safety"):
        await agent_env.agent.run("4+4?")


@pytest.mark.asyncio
async def test_agent_run_unknown_incomplete_reason_raises_value_error(
    agent_env,
):
    """An unrecognised incomplete reason raises ValueError."""
    agent_env.responses = [
        _make_response(
            status="incomplete",
            incomplete_details=SimpleNamespace(reason="wat"),
        )
    ]
    with pytest.raises(ValueError, match="Unknown incomplete reason: wat"):
        await agent_env.agent.run("4+4?")


@pytest.mark.asyncio
async def test_agent_run_missing_incomplete_details_raises_value_error(
    agent_env,
):
    """An "incomplete" status without details raises ValueError."""
    agent_env.responses = [_make_response(status="incomplete")]
    with pytest.raises(ValueError, match="Unknown incomplete reason: None"):
        await agent_env.agent.run("4+4?")


@pytest.mark.asyncio
async def test_agent_run_failed_raises_llm_request_failed_error(agent_env):
    """A "failed" status raises LLMRequestFailedError with its code."""
    agent_env.responses = [
        _make_response(
            status="failed",
            error=SimpleNamespace(code="server_error", message="upstream 502"),
        )
    ]
    with pytest.raises(LLMRequestFailedError, match="upstream 502") as info:
        await agent_env.agent.run("4+4?")
    assert info.value.code == "server_error"


@pytest.mark.asyncio
async def test_agent_run_failed_without_error_raises_llm_error(agent_env):
    """A "failed" status with no error object has no error code."""
    agent_env.responses = [_make_response(status="failed")]
    with pytest.raises(LLMRequestFailedError, match="unknown error") as info:
        await agent_env.agent.run("4+4?")
    assert info.value.code is None


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["wat", "queued", "in_progress"])
async def test_agent_run_unknown_status_raises_value_error(agent_env, status):
    """A non-final or unrecognised response status raises ValueError."""
    agent_env.responses = [_make_response(status=status)]
    expected = f"Non-supported response status: {status}"
    with pytest.raises(ValueError, match=expected):
        await agent_env.agent.run("4+4?")


# ---------------------------------------------------------------------------
# Agent.run — continue branches
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_run_dispatches_tool_call(agent_env):
    """A function_call item dispatches to the MCP calculator."""
    agent_env.responses = [
        _make_response(output=[_make_function_call()]),
        _make_response(output=[_make_message("4 + 4 = 8")]),
    ]
    assert await agent_env.agent.run("4+4?") == _answer("4 + 4 = 8")
    agent_env.call_tool.assert_awaited_once_with("add", {"a": 4, "b": 4})


@pytest.mark.asyncio
async def test_agent_run_returns_tool_error_to_llm(agent_env):
    """A tool error is sent to the LLM as the tool output."""
    agent_env.call_tool.side_effect = ToolError(
        "Error calling tool 'divide': Cannot divide by zero"
    )
    agent_env.responses = [
        _make_response(output=[_make_function_call(name="divide")]),
        _make_response(output=[_make_message("undefined")]),
    ]
    assert await agent_env.agent.run("10/0?") == _answer("undefined")
    assert agent_env.histories[1][-1]["output"] == (
        "Error calling tool 'divide': Cannot divide by zero"
    )


@pytest.mark.asyncio
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
        _make_response(output=[_make_function_call(arguments=arguments)]),
        _make_response(output=[_make_message("done")]),
    ]
    assert await agent_env.agent.run("4+4?") == _answer("done")
    agent_env.call_tool.assert_not_awaited()
    assert message in agent_env.histories[1][-1]["output"]


@pytest.mark.asyncio
async def test_agent_run_dispatches_multiple_tool_calls(agent_env):
    """Every function_call item in one response is dispatched in order."""
    agent_env.responses = [
        _make_response(
            output=[
                _make_function_call(call_id="c1", name="add"),
                _make_function_call(
                    call_id="c2", name="multiply", arguments='{"a": 2, "b": 3}'
                ),
            ]
        ),
        _make_response(output=[_make_message("done")]),
    ]
    assert await agent_env.agent.run("compute") == _answer("done")
    assert agent_env.call_tool.await_count == 2
    assert [c.args[0] for c in agent_env.call_tool.await_args_list] == [
        "add",
        "multiply",
    ]


@pytest.mark.asyncio
async def test_agent_run_replays_output_items_and_tool_output(agent_env):
    """Output items are echoed back followed by function_call_output."""
    agent_env.responses = [
        _make_response(output=[_make_message("plan"), _make_function_call()]),
        _make_response(output=[_make_message("done")]),
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


@pytest.mark.asyncio
@pytest.mark.parametrize("agent_env", [True], ids=["stateful"], indirect=True)
async def test_agent_run_stateful_sends_only_tool_output(agent_env):
    """A stateful turn sends only new items and continues the response."""
    agent_env.responses = [
        _make_response(
            response_id="resp-1",
            output=[_make_message("plan"), _make_function_call()],
        ),
        _make_response(response_id="resp-2", output=[_make_message("done")]),
    ]
    answer = await agent_env.agent.run("4+4?")

    assert answer == _answer(final="done")
    assert agent_env.histories == [
        [{"role": "user", "content": "4+4?"}],
        [{"type": "function_call_output", "call_id": "call-1", "output": "8"}],
    ]
    assert agent_env.previous_response_ids == [None, "resp-1"]


# ---------------------------------------------------------------------------
# Agent.run — reasoning sections
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_run_includes_reasoning_from_every_turn(agent_env):
    """Reasoning text from all turns is joined in order."""
    agent_env.responses = [
        _make_response(
            output=[
                _make_reasoning(["Plan: add."], ["Need 4 + 4."]),
                _make_function_call(),
            ]
        ),
        _make_response(
            output=[
                _make_reasoning(["Report."], ["Tool said 8."]),
                _make_message("4 + 4 = 8"),
            ]
        ),
    ]
    assert await agent_env.agent.run("4+4?") == _answer(
        final="4 + 4 = 8", reasoning="Need 4 + 4.\nTool said 8."
    )


@pytest.mark.asyncio
async def test_agent_run_without_reasoning_returns_final_response(agent_env):
    """With display_reasoning False, only the final text is returned."""
    agent_env.responses = [
        _make_response(
            output=[
                _make_reasoning(texts=["Need 4 + 4."]),
                _make_message("  4 + 4 = 8\n"),
            ]
        ),
    ]
    answer = await agent_env.agent.run("4+4?", display_reasoning=False)
    assert answer == "4 + 4 = 8"


@pytest.mark.asyncio
async def test_agent_run_strips_blank_lines_from_answer(agent_env):
    """Whitespace around each text adds no extra blank lines."""
    agent_env.responses = [
        _make_response(
            output=[
                _make_reasoning(texts=["\nUse divide tool.\n\n", "  \n"]),
                _make_function_call(),
            ]
        ),
        _make_response(
            output=[
                _make_reasoning(texts=["\n\nProvide answer.\n"]),
                _make_message("\nThe result is 97.39.\n\n"),
            ]
        ),
    ]
    assert await agent_env.agent.run("4+4?") == (
        "reasoning:\nUse divide tool.\nProvide answer.\n\n"
        "final response:\nThe result is 97.39."
    )


@pytest.mark.asyncio
async def test_agent_run_uses_summary_without_content(agent_env):
    """A reasoning item with only a summary shows the summary."""
    agent_env.responses = [
        _make_response(
            output=[_make_reasoning(["Short plan."]), _make_message("8")]
        )
    ]
    assert await agent_env.agent.run("4+4?") == _answer(
        final="8", reasoning="Short plan."
    )
