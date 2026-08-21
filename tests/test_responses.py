# General Disclaimer
#
# **AI Generated Content**
#
# This project's source code and documentation were generated predominantly
# by an Artificial Intelligence Large Language Model (AI LLM). The project
# lead, [Rubens Gomes](https://rubensgomes.com), provided initial prompts,
# reviewed, and made refinements to the generated output. While human review and
# refinement have occurred, users should be aware that the output may contain
# inaccuracies, errors, or security vulnerabilities
#
# **Third-Party Content Notice**
#
# This software may include components or snippets derived from third-party
# sources. The software's users and distributors are responsible for ensuring
# compliance with any underlying licenses applicable to such components.
#
# **Copyright Status Statement**
#
# Copyright protection, if any, is limited to the original
# human contributions and modifications made to this project.
# The AI-generated portions of the code and
# documentation are not subject to copyright and are considered to be in the
# public domain.
#
# **Limitation of liability**
#
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES, OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR
# OTHERWISE, ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.
#
# **No-Warranty Disclaimer**
#
# THIS SOFTWARE IS PROVIDED 'AS IS,' WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT.

"""Unit tests for the Responses API path in :mod:`math_ai_agent.llm`."""

import copy
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from openai.types.responses import (
    ResponseFunctionToolCall,
    ResponseOutputMessage,
    ResponseOutputText,
)

from math_ai_agent.llm import agent as llm_module
from math_ai_agent.llm.agent import _SYSTEM_INSTRUCTIONS, agent_loop
from math_ai_agent.llm.client import ResponsesClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_API_KEY = "test-api-key"
_BASE_URL = "http://localhost:11434/v1"
_MODEL = "test-model"
_USAGE = SimpleNamespace(
    input_tokens=10,
    output_tokens=5,
    total_tokens=15,
)
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
        status=status,
        output=output,
        output_text=output_text,
        usage=usage,
        incomplete_details=incomplete_details,
        error=error,
    )
    response.model_dump = lambda: {
        "status": status,
        "output": [item.model_dump() for item in output],
    }
    return response


def _make_client():
    """Create a ResponsesClient instance with test parameters."""
    return ResponsesClient(_API_KEY, _BASE_URL, _MODEL, _TOOLS)


# ---------------------------------------------------------------------------
# __init__ — validation
# ---------------------------------------------------------------------------


def test_init_sets_instance_attributes():
    """Instantiation sets instance attributes."""
    client = ResponsesClient(_API_KEY, _BASE_URL, _MODEL, _TOOLS)
    assert client.openai_client is not None
    assert client.tools is _TOOLS
    assert client.model == _MODEL
    assert isinstance(client, ResponsesClient)


def test_init_empty_api_key_raises():
    """Empty api_key raises ValueError."""
    with pytest.raises(ValueError, match="api_key must not be empty"):
        ResponsesClient("", _BASE_URL, _MODEL, _TOOLS)


def test_init_empty_base_url_raises():
    """Empty base_url raises ValueError."""
    with pytest.raises(ValueError, match="base_url must not be empty"):
        ResponsesClient(_API_KEY, "", _MODEL, _TOOLS)


def test_init_empty_model_raises():
    """Empty model raises ValueError."""
    with pytest.raises(ValueError, match="model must not be empty"):
        ResponsesClient(_API_KEY, _BASE_URL, "", _TOOLS)


def test_init_empty_tools_raises():
    """Empty tools list raises ValueError."""
    with pytest.raises(ValueError, match="tools must not be empty"):
        ResponsesClient(_API_KEY, _BASE_URL, _MODEL, [])


def test_init_none_api_key_raises():
    """None api_key raises ValueError."""
    with pytest.raises(ValueError, match="api_key must not be empty"):
        ResponsesClient(None, _BASE_URL, _MODEL, _TOOLS)


# ---------------------------------------------------------------------------
# create_response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_response_returns_response():
    """create_response returns the Response from the API."""
    fake_response = _make_response(output=[_make_message("The answer is 8")])
    client = _make_client()

    mock_create = AsyncMock(return_value=fake_response)
    client.openai_client.responses = SimpleNamespace(create=mock_create)

    history = [{"role": "user", "content": "4+4?"}]
    result = await client.create_response(history, _SYSTEM_INSTRUCTIONS)

    assert result is fake_response
    assert result.output_text == "The answer is 8"


@pytest.mark.asyncio
async def test_create_response_sends_expected_arguments():
    """create_response sends input, tools, instructions and store=False."""
    fake_response = _make_response()
    client = _make_client()

    mock_create = AsyncMock(return_value=fake_response)
    client.openai_client.responses = SimpleNamespace(create=mock_create)

    history = [{"role": "user", "content": "4+4?"}]
    await client.create_response(history, _SYSTEM_INSTRUCTIONS)

    mock_create.assert_awaited_once_with(
        model=_MODEL,
        input=history,
        tools=_TOOLS,
        instructions=_SYSTEM_INSTRUCTIONS,
        store=False,
    )


@pytest.mark.asyncio
async def test_create_response_with_function_call():
    """create_response handles a response with a function_call item."""
    fake_response = _make_response(output=[_make_function_call()])
    client = _make_client()

    mock_create = AsyncMock(return_value=fake_response)
    client.openai_client.responses = SimpleNamespace(create=mock_create)

    result = await client.create_response(
        [{"role": "user", "content": "4+4?"}], _SYSTEM_INSTRUCTIONS
    )

    assert result.output_text == ""
    assert result.output[0].name == "add"


# ---------------------------------------------------------------------------
# agent_loop — helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def agent_env():
    """Patch config getters, MCP tool discovery, and tool dispatch.

    Yields a ``SimpleNamespace`` whose ``responses`` list is consumed
    one entry per ``create_response`` call, whose ``histories`` list
    records a snapshot of the input items sent on each call, whose
    ``instructions`` list records the system prompt sent on each call,
    and whose ``call_tool`` mock records every dispatched calculator
    tool call.
    """
    env = SimpleNamespace(
        responses=[],
        histories=[],
        instructions=[],
        call_tool=AsyncMock(return_value="8"),
    )

    async def _next_response(history, instructions):
        env.histories.append(copy.deepcopy(history))
        env.instructions.append(instructions)
        return env.responses.pop(0)

    with (
        patch.object(
            llm_module, "get_calc_mcp_tools", AsyncMock(return_value=_TOOLS)
        ),
        patch.object(llm_module, "get_api_style", return_value="responses"),
        patch.object(llm_module, "get_api_key", return_value=_API_KEY),
        patch.object(llm_module, "get_model_base_url", return_value=_BASE_URL),
        patch.object(llm_module, "get_model", return_value=_MODEL),
        patch.object(llm_module, "call_tool", env.call_tool),
        patch.object(
            ResponsesClient, "create_response", side_effect=_next_response
        ),
    ):
        yield env


# ---------------------------------------------------------------------------
# agent_loop — terminal responses
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_loop_returns_output_text_on_completed(agent_env):
    """A "completed" status with no tool calls returns the output text."""
    agent_env.responses = [
        _make_response(output=[_make_message("The answer is 8")])
    ]
    assert await agent_loop("4+4?") == "The answer is 8"


@pytest.mark.asyncio
async def test_agent_loop_returns_empty_string_for_no_output(agent_env):
    """A "completed" status with no output items returns an empty string."""
    agent_env.responses = [_make_response(output=[])]
    assert await agent_loop("4+4?") == ""


@pytest.mark.asyncio
async def test_agent_loop_handles_missing_usage(agent_env):
    """A response without usage data is logged and does not raise."""
    agent_env.responses = [
        _make_response(output=[_make_message("8")], usage=None)
    ]
    assert await agent_loop("4+4?") == "8"


@pytest.mark.asyncio
async def test_agent_loop_passes_system_instructions(agent_env):
    """The loop supplies the system prompt to the client each turn."""
    agent_env.responses = [
        _make_response(output=[_make_function_call()]),
        _make_response(output=[_make_message("done")]),
    ]
    await agent_loop("4+4?")
    assert agent_env.instructions == [
        _SYSTEM_INSTRUCTIONS,
        _SYSTEM_INSTRUCTIONS,
    ]


@pytest.mark.asyncio
async def test_agent_loop_sends_user_prompt_without_system_item(agent_env):
    """The first input carries only the user prompt, no system item."""
    agent_env.responses = [_make_response(output=[_make_message("8")])]
    await agent_loop("4+4?")
    assert agent_env.histories[0] == [{"role": "user", "content": "4+4?"}]


# ---------------------------------------------------------------------------
# agent_loop — error statuses
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_loop_max_output_tokens_raises_runtime_error(agent_env):
    """An "incomplete" max_output_tokens response raises RuntimeError."""
    agent_env.responses = [
        _make_response(
            status="incomplete",
            incomplete_details=SimpleNamespace(reason="max_output_tokens"),
        )
    ]
    with pytest.raises(RuntimeError, match="Token limit reached"):
        await agent_loop("4+4?")


@pytest.mark.asyncio
async def test_agent_loop_content_filter_raises_runtime_error(agent_env):
    """An "incomplete" content_filter response raises RuntimeError."""
    agent_env.responses = [
        _make_response(
            status="incomplete",
            incomplete_details=SimpleNamespace(reason="content_filter"),
        )
    ]
    with pytest.raises(RuntimeError, match="blocked"):
        await agent_loop("4+4?")


@pytest.mark.asyncio
async def test_agent_loop_unknown_incomplete_reason_raises_value_error(
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
        await agent_loop("4+4?")


@pytest.mark.asyncio
async def test_agent_loop_missing_incomplete_details_raises_value_error(
    agent_env,
):
    """An "incomplete" status without details raises ValueError."""
    agent_env.responses = [_make_response(status="incomplete")]
    with pytest.raises(ValueError, match="Unknown incomplete reason: None"):
        await agent_loop("4+4?")


@pytest.mark.asyncio
async def test_agent_loop_failed_raises_runtime_error(agent_env):
    """A "failed" status raises RuntimeError with the provider message."""
    agent_env.responses = [
        _make_response(
            status="failed",
            error=SimpleNamespace(code="server_error", message="upstream 502"),
        )
    ]
    with pytest.raises(RuntimeError, match="upstream 502"):
        await agent_loop("4+4?")


@pytest.mark.asyncio
async def test_agent_loop_failed_without_error_raises_runtime_error(agent_env):
    """A "failed" status with no error object still raises RuntimeError."""
    agent_env.responses = [_make_response(status="failed")]
    with pytest.raises(RuntimeError, match="unknown error"):
        await agent_loop("4+4?")


@pytest.mark.asyncio
async def test_agent_loop_unknown_status_raises_value_error(agent_env):
    """An unrecognised response status raises ValueError."""
    agent_env.responses = [_make_response(status="wat")]
    with pytest.raises(ValueError, match="Unknown response status: wat"):
        await agent_loop("4+4?")


# ---------------------------------------------------------------------------
# agent_loop — continue branches
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_loop_in_progress_continues(agent_env):
    """An "in_progress" status loops again instead of terminating."""
    agent_env.responses = [
        _make_response(status="in_progress"),
        _make_response(output=[_make_message("done")]),
    ]
    assert await agent_loop("4+4?") == "done"
    assert agent_env.responses == []


@pytest.mark.asyncio
async def test_agent_loop_queued_continues(agent_env):
    """A "queued" status loops again instead of terminating."""
    agent_env.responses = [
        _make_response(status="queued"),
        _make_response(output=[_make_message("done")]),
    ]
    assert await agent_loop("4+4?") == "done"
    assert agent_env.responses == []


@pytest.mark.asyncio
async def test_agent_loop_dispatches_tool_call(agent_env):
    """A function_call item dispatches to the MCP calculator."""
    agent_env.responses = [
        _make_response(output=[_make_function_call()]),
        _make_response(output=[_make_message("4 + 4 = 8")]),
    ]
    assert await agent_loop("4+4?") == "4 + 4 = 8"
    agent_env.call_tool.assert_awaited_once_with("add", {"a": 4, "b": 4})


@pytest.mark.asyncio
async def test_agent_loop_dispatches_multiple_tool_calls(agent_env):
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
    assert await agent_loop("compute") == "done"
    assert agent_env.call_tool.await_count == 2
    assert [c.args[0] for c in agent_env.call_tool.await_args_list] == [
        "add",
        "multiply",
    ]


@pytest.mark.asyncio
async def test_agent_loop_replays_output_items_and_tool_output(agent_env):
    """Output items are echoed back followed by function_call_output."""
    agent_env.responses = [
        _make_response(output=[_make_message("plan"), _make_function_call()]),
        _make_response(output=[_make_message("done")]),
    ]
    await agent_loop("4+4?")

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
