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

"""Unit tests for the Chat Completions path in
:mod:`math_ai_agent.llm`.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from math_ai_agent.llm import agent as llm_module
from math_ai_agent.llm.agent import agent_loop
from math_ai_agent.llm.client import ChatCompletionClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_API_KEY = "test-api-key"
_BASE_URL = "http://localhost:11434/v1"
_MODEL = "test-model"
_USAGE = SimpleNamespace(
    prompt_tokens=10,
    completion_tokens=5,
    total_tokens=15,
)
_TOOLS = [
    {
        "type": "function",
        "function": {
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
        },
    }
]


def _make_chat_completion(
    content="42", tool_calls=None, finish_reason="stop", usage=_USAGE
):
    """Build a fake ChatCompletion-like response object."""
    message = SimpleNamespace(
        role="assistant",
        content=content,
        tool_calls=tool_calls,
        function_call=None,
        refusal=None,
    )
    choice = SimpleNamespace(
        message=message,
        finish_reason=finish_reason,
    )
    response = SimpleNamespace(choices=[choice], usage=usage)

    def _dump_tool_calls(tc_list):
        if tc_list is None:
            return None
        return [
            {
                "id": tc.id,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in tc_list
        ]

    response.model_dump = lambda: {
        "choices": [
            {
                "finish_reason": finish_reason,
                "message": {
                    "role": "assistant",
                    "content": content,
                    "tool_calls": _dump_tool_calls(tool_calls),
                    "function_call": None,
                    "refusal": None,
                },
            }
        ]
    }
    return response


def _make_client():
    """Create an ChatCompletionClient instance with test parameters."""
    return ChatCompletionClient(_API_KEY, _BASE_URL, _MODEL, _TOOLS)


# ---------------------------------------------------------------------------
# __init__ — validation
# ---------------------------------------------------------------------------


def test_init_sets_instance_attributes():
    """Instantiation sets instance attributes."""
    client = ChatCompletionClient(_API_KEY, _BASE_URL, _MODEL, _TOOLS)
    assert client.openai_client is not None
    assert client.tools is _TOOLS
    assert client.model == _MODEL
    assert isinstance(client, ChatCompletionClient)


def test_init_empty_api_key_raises():
    """Empty api_key raises ValueError."""
    with pytest.raises(ValueError, match="api_key must not be empty"):
        ChatCompletionClient("", _BASE_URL, _MODEL, _TOOLS)


def test_init_empty_base_url_raises():
    """Empty base_url raises ValueError."""
    with pytest.raises(ValueError, match="base_url must not be empty"):
        ChatCompletionClient(_API_KEY, "", _MODEL, _TOOLS)


def test_init_empty_model_raises():
    """Empty model raises ValueError."""
    with pytest.raises(ValueError, match="model must not be empty"):
        ChatCompletionClient(_API_KEY, _BASE_URL, "", _TOOLS)


def test_init_empty_tools_raises():
    """Empty tools list raises ValueError."""
    with pytest.raises(ValueError, match="tools must not be empty"):
        ChatCompletionClient(_API_KEY, _BASE_URL, _MODEL, [])


def test_init_none_api_key_raises():
    """None api_key raises ValueError."""
    with pytest.raises(ValueError, match="api_key must not be empty"):
        ChatCompletionClient(None, _BASE_URL, _MODEL, _TOOLS)


# ---------------------------------------------------------------------------
# create_response — text response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_response_returns_completion():
    """create_response returns the ChatCompletion from the API."""
    fake_response = _make_chat_completion(content="The answer is 8")
    client = _make_client()

    mock_create = AsyncMock(return_value=fake_response)
    client.openai_client.chat = SimpleNamespace(
        completions=SimpleNamespace(create=mock_create)
    )

    history = [{"role": "user", "content": "4+4?"}]
    result = await client.create_response(history)

    assert result is fake_response
    assert result.choices[0].message.content == "The answer is 8"
    mock_create.assert_awaited_once_with(
        model=_MODEL,
        messages=history,
        tools=_TOOLS,
        store=False,
    )


@pytest.mark.asyncio
async def test_create_response_with_tool_calls():
    """create_response handles a response with tool_calls."""
    tool_call = SimpleNamespace(
        id="call_123",
        function=SimpleNamespace(
            name="add",
            arguments='{"a": 2, "b": 3}',
        ),
    )
    fake_response = _make_chat_completion(
        content=None,
        tool_calls=[tool_call],
        finish_reason="tool_calls",
    )
    client = _make_client()

    mock_create = AsyncMock(return_value=fake_response)
    client.openai_client.chat = SimpleNamespace(
        completions=SimpleNamespace(create=mock_create)
    )

    history = [{"role": "user", "content": "2+3?"}]
    result = await client.create_response(history)

    assert result is fake_response
    assert result.choices[0].message.content is None
    assert len(result.choices[0].message.tool_calls) == 1
    assert result.choices[0].message.tool_calls[0].function.name == "add"


@pytest.mark.asyncio
async def test_create_response_with_none_content_no_tool_calls():
    """create_response handles None content without tool_calls."""
    fake_response = _make_chat_completion(
        content=None,
        tool_calls=None,
        finish_reason="stop",
    )
    client = _make_client()

    mock_create = AsyncMock(return_value=fake_response)
    client.openai_client.chat = SimpleNamespace(
        completions=SimpleNamespace(create=mock_create)
    )

    history = [{"role": "user", "content": "hello"}]
    result = await client.create_response(history)

    assert result.choices[0].message.content is None
    assert result.choices[0].message.tool_calls is None


@pytest.mark.asyncio
async def test_create_response_passes_all_messages():
    """create_response forwards the full message history."""
    fake_response = _make_chat_completion(content="done")
    client = _make_client()

    mock_create = AsyncMock(return_value=fake_response)
    client.openai_client.chat = SimpleNamespace(
        completions=SimpleNamespace(create=mock_create)
    )

    history = [
        {"role": "system", "content": "You are a math tutor."},
        {"role": "user", "content": "What is 2+2?"},
        {"role": "assistant", "content": "4"},
        {"role": "user", "content": "And 3+3?"},
    ]
    await client.create_response(history)

    mock_create.assert_awaited_once_with(
        model=_MODEL,
        messages=history,
        tools=_TOOLS,
        store=False,
    )


@pytest.mark.asyncio
async def test_create_response_multiple_tool_calls():
    """create_response handles multiple tool calls in one response."""
    tool_calls = [
        SimpleNamespace(
            id="call_1",
            function=SimpleNamespace(name="add", arguments='{"a": 1, "b": 2}'),
        ),
        SimpleNamespace(
            id="call_2",
            function=SimpleNamespace(name="add", arguments='{"a": 3, "b": 4}'),
        ),
    ]
    fake_response = _make_chat_completion(
        content=None,
        tool_calls=tool_calls,
        finish_reason="tool_calls",
    )
    client = _make_client()

    mock_create = AsyncMock(return_value=fake_response)
    client.openai_client.chat = SimpleNamespace(
        completions=SimpleNamespace(create=mock_create)
    )

    history = [{"role": "user", "content": "(1+2) + (3+4)?"}]
    result = await client.create_response(history)

    assert len(result.choices[0].message.tool_calls) == 2


# ---------------------------------------------------------------------------
# agent_loop — helpers
# ---------------------------------------------------------------------------


def _make_tool_call(call_id="call-1", name="add", arguments='{"a": 4, "b": 4}'):
    """Build a fake tool_call object as returned by the OpenAI SDK."""
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=arguments),
    )


@pytest.fixture()
def agent_env():
    """Patch config getters, MCP tool discovery, and tool dispatch.

    Yields a ``SimpleNamespace`` whose ``responses`` list is consumed
    one entry per ``create_response`` call, and whose ``call_tool``
    mock records every dispatched calculator tool call.
    """
    env = SimpleNamespace(responses=[], call_tool=AsyncMock(return_value="8"))

    async def _next_response(history):  # pylint: disable=unused-argument
        return env.responses.pop(0)

    with (
        patch.object(
            llm_module, "get_calc_mcp_tools", AsyncMock(return_value=_TOOLS)
        ),
        patch.object(llm_module, "get_api_style", return_value="chat"),
        patch.object(llm_module, "get_api_key", return_value=_API_KEY),
        patch.object(llm_module, "get_model_base_url", return_value=_BASE_URL),
        patch.object(llm_module, "get_model", return_value=_MODEL),
        patch.object(llm_module, "call_tool", env.call_tool),
        patch.object(
            ChatCompletionClient, "create_response", side_effect=_next_response
        ),
    ):
        yield env


# ---------------------------------------------------------------------------
# agent_loop — terminal responses
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_loop_returns_content_on_stop(agent_env):
    """A "stop" finish_reason returns the assistant message content."""
    agent_env.responses = [_make_chat_completion(content="The answer is 8")]
    assert await agent_loop("4+4?") == "The answer is 8"


@pytest.mark.asyncio
async def test_agent_loop_returns_empty_string_for_none_content(agent_env):
    """A "stop" with no content returns an empty string, not None."""
    agent_env.responses = [_make_chat_completion(content=None)]
    assert await agent_loop("4+4?") == ""


@pytest.mark.asyncio
async def test_agent_loop_handles_missing_usage(agent_env):
    """A response without usage data is logged and does not raise."""
    agent_env.responses = [_make_chat_completion(content="8", usage=None)]
    assert await agent_loop("4+4?") == "8"


# ---------------------------------------------------------------------------
# agent_loop — error finish reasons
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_loop_length_raises_runtime_error(agent_env):
    """A "length" finish_reason raises RuntimeError."""
    agent_env.responses = [_make_chat_completion(finish_reason="length")]
    with pytest.raises(RuntimeError, match="Token limit reached"):
        await agent_loop("4+4?")


@pytest.mark.asyncio
async def test_agent_loop_content_filter_raises_runtime_error(agent_env):
    """A "content_filter" finish_reason raises RuntimeError."""
    agent_env.responses = [
        _make_chat_completion(finish_reason="content_filter")
    ]
    with pytest.raises(RuntimeError, match="blocked"):
        await agent_loop("4+4?")


@pytest.mark.asyncio
async def test_agent_loop_unknown_reason_raises_value_error(agent_env):
    """An unrecognised finish_reason raises ValueError."""
    agent_env.responses = [_make_chat_completion(finish_reason="wat")]
    with pytest.raises(ValueError, match="Unknown finish_reason: wat"):
        await agent_loop("4+4?")


# ---------------------------------------------------------------------------
# agent_loop — continue branches
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_loop_none_reason_continues(agent_env):
    """A None finish_reason loops again instead of terminating."""
    agent_env.responses = [
        _make_chat_completion(finish_reason=None),
        _make_chat_completion(content="done"),
    ]
    assert await agent_loop("4+4?") == "done"
    assert agent_env.responses == []


@pytest.mark.asyncio
async def test_agent_loop_dispatches_tool_call(agent_env):
    """A tool_calls response dispatches to the MCP calculator."""
    agent_env.responses = [
        _make_chat_completion(
            content=None,
            tool_calls=[_make_tool_call()],
            finish_reason="tool_calls",
        ),
        _make_chat_completion(content="4 + 4 = 8"),
    ]
    assert await agent_loop("4+4?") == "4 + 4 = 8"
    agent_env.call_tool.assert_awaited_once_with("add", {"a": 4, "b": 4})


@pytest.mark.asyncio
async def test_agent_loop_dispatches_multiple_tool_calls(agent_env):
    """Every tool call in one response is dispatched in order."""
    agent_env.responses = [
        _make_chat_completion(
            content=None,
            tool_calls=[
                _make_tool_call(call_id="c1", name="add"),
                _make_tool_call(
                    call_id="c2", name="multiply", arguments='{"a": 2, "b": 3}'
                ),
            ],
            finish_reason="tool_calls",
        ),
        _make_chat_completion(content="done"),
    ]
    assert await agent_loop("compute") == "done"
    assert agent_env.call_tool.await_count == 2
    assert [c.args[0] for c in agent_env.call_tool.await_args_list] == [
        "add",
        "multiply",
    ]


# ---------------------------------------------------------------------------
# agent_loop — api_style dispatch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_loop_dispatches_to_chat_loop():
    """An api_style of "chat" routes to the Chat Completions loop."""
    chat = AsyncMock(return_value="chat answer")
    responses = AsyncMock(return_value="responses answer")
    with (
        patch.object(llm_module, "get_api_style", return_value="chat"),
        patch.object(llm_module, "_chat_agent_loop", chat),
        patch.object(llm_module, "_responses_agent_loop", responses),
    ):
        assert await agent_loop("4+4?") == "chat answer"
    chat.assert_awaited_once_with("4+4?")
    responses.assert_not_awaited()


@pytest.mark.asyncio
async def test_agent_loop_dispatches_to_responses_loop():
    """An api_style of "responses" routes to the Responses loop."""
    chat = AsyncMock(return_value="chat answer")
    responses = AsyncMock(return_value="responses answer")
    with (
        patch.object(llm_module, "get_api_style", return_value="responses"),
        patch.object(llm_module, "_chat_agent_loop", chat),
        patch.object(llm_module, "_responses_agent_loop", responses),
    ):
        assert await agent_loop("4+4?") == "responses answer"
    responses.assert_awaited_once_with("4+4?")
    chat.assert_not_awaited()
