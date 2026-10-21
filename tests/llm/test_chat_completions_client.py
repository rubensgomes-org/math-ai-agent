"""Unit tests for :mod:`math_ai_agent.llm.chat_completions_client`."""

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import mcp_types
import pytest
from ai_utils_lib.config.models import DEFAULT_MODEL_TIMEOUT_SECONDS
from openai import omit

from math_ai_agent.llm.chat_completions_client import ChatCompletionsClient

from tests.fakes.chat import (
    TOOLS,
    USAGE,
    make_chat_completion,
    make_client,
    make_tool_call,
)
from tests.fakes.common import (
    ADD_TOOL,
    INSTRUCTIONS,
    MCP_TOOLS,
    MODEL,
    TOOLS_DEFINITIONS,
    llm_config,
)

# ---------------------------------------------------------------------------
# __init__ — validation
# ---------------------------------------------------------------------------


def test_init_sets_instance_attributes():
    """Instantiation sets instance attributes."""
    client = ChatCompletionsClient(llm_config(), [ADD_TOOL])
    assert client.openai_client is not None
    assert client.tools == TOOLS
    assert client.model_name == MODEL
    assert isinstance(client, ChatCompletionsClient)


async def test_prompt_debug_logs_response(caplog):
    """At DEBUG, each response is logged as JSON."""
    caplog.set_level(logging.DEBUG, logger="math_ai_agent.llm")
    client = make_client()
    client.openai_client.chat = SimpleNamespace(
        completions=SimpleNamespace(
            create=AsyncMock(return_value=make_chat_completion())
        )
    )
    await client.prompt([{"role": "user", "content": "4+4?"}])
    assert "LLM response:" in caplog.text


async def test_async_with_closes_openai_client():
    """Leaving an ``async with`` block closes the client."""
    client = make_client()
    with patch.object(
        client.openai_client, "close", new_callable=AsyncMock
    ) as mock_close:
        async with client as entered:
            assert entered is client
    mock_close.assert_awaited_once()


def test_init_uses_default_timeout():
    client = ChatCompletionsClient(llm_config(), [ADD_TOOL])
    assert client.openai_client.timeout == DEFAULT_MODEL_TIMEOUT_SECONDS


def test_init_uses_given_timeout():
    client = ChatCompletionsClient(llm_config(timeout_seconds=30), [ADD_TOOL])
    assert client.openai_client.timeout == 30


@pytest.mark.parametrize("temperature", [0.0, 0.2])
async def test_prompt_sends_temperature(temperature):
    """A set temperature is sent, including 0."""
    client = ChatCompletionsClient(
        llm_config(temperature=temperature), [ADD_TOOL]
    )
    mock_create = AsyncMock(return_value=make_chat_completion())
    client.openai_client.chat = SimpleNamespace(
        completions=SimpleNamespace(create=mock_create)
    )

    await client.prompt([{"role": "user", "content": "4+4?"}])

    assert mock_create.await_args.kwargs["temperature"] == temperature


# ---------------------------------------------------------------------------
# _format_tools
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("description", [None, ""])
def test_format_tools_omits_missing_description(description):
    tool = mcp_types.Tool(
        name="noop",
        description=description,
        input_schema={"type": "object", "properties": {}},
    )
    # pylint: disable-next=protected-access
    [definition] = ChatCompletionsClient._format_tools([tool])
    assert "description" not in definition["function"]


def test_format_tools_nests_each_definition_under_function():
    """Each definition becomes a nested Chat Completions function tool."""
    # pylint: disable-next=protected-access
    assert ChatCompletionsClient._format_tools(MCP_TOOLS) == [
        {"type": "function", "function": definition}
        for definition in TOOLS_DEFINITIONS
    ]


def test_format_tools_empty_list():
    # pylint: disable-next=protected-access
    assert ChatCompletionsClient._format_tools([]) == []


# ---------------------------------------------------------------------------
# prompt — text response
# ---------------------------------------------------------------------------


_SYSTEM_MESSAGE = {"role": "system", "content": INSTRUCTIONS}


def test_init_rejects_stateful_model():
    """A stateful model config fails, since the API is stateless."""
    with pytest.raises(ValueError, match="stateless"):
        make_client(is_stateful=True)


def test_log_token_usage_logs_counts(caplog):
    caplog.set_level(logging.INFO)
    make_client().log_token_usage(make_chat_completion())
    expected = "prompt=10 cached=2 completion=5 reasoning=3 total=15"
    assert expected in caplog.text


def test_log_token_usage_omits_unreported_details(caplog):
    caplog.set_level(logging.INFO)
    usage = USAGE.model_copy(
        update={
            "prompt_tokens_details": None,
            "completion_tokens_details": None,
        }
    )
    make_client().log_token_usage(make_chat_completion(usage=usage))
    assert "prompt=10 completion=5 total=15" in caplog.text


async def test_prompt_returns_completion():
    """prompt returns the ChatCompletion from the API."""
    fake_response = make_chat_completion(content="The answer is 8")
    client = make_client()

    mock_create = AsyncMock(return_value=fake_response)
    client.openai_client.chat = SimpleNamespace(
        completions=SimpleNamespace(create=mock_create)
    )

    history = [{"role": "user", "content": "4+4?"}]
    result = await client.prompt(history)

    assert result is fake_response
    assert result.choices[0].message.content == "The answer is 8"
    mock_create.assert_awaited_once_with(
        model=MODEL,
        messages=[_SYSTEM_MESSAGE, *history],
        tools=TOOLS,
        temperature=omit,
    )


async def test_prompt_with_tool_calls():
    """prompt handles a response with tool_calls."""
    tool_call = make_tool_call(call_id="call_123", arguments='{"a": 2, "b": 3}')
    fake_response = make_chat_completion(
        content=None,
        tool_calls=[tool_call],
        finish_reason="tool_calls",
    )
    client = make_client()

    mock_create = AsyncMock(return_value=fake_response)
    client.openai_client.chat = SimpleNamespace(
        completions=SimpleNamespace(create=mock_create)
    )

    history = [{"role": "user", "content": "2+3?"}]
    result = await client.prompt(history)

    assert result is fake_response
    assert result.choices[0].message.content is None
    assert len(result.choices[0].message.tool_calls) == 1
    assert result.choices[0].message.tool_calls[0].function.name == "add"


async def test_prompt_with_none_content_no_tool_calls():
    """prompt handles None content without tool_calls."""
    fake_response = make_chat_completion(
        content=None,
        tool_calls=None,
        finish_reason="stop",
    )
    client = make_client()

    mock_create = AsyncMock(return_value=fake_response)
    client.openai_client.chat = SimpleNamespace(
        completions=SimpleNamespace(create=mock_create)
    )

    history = [{"role": "user", "content": "hello"}]
    result = await client.prompt(history)

    assert result.choices[0].message.content is None
    assert result.choices[0].message.tool_calls is None


async def test_prompt_passes_all_messages():
    """prompt forwards the history after the configured system message."""
    fake_response = make_chat_completion(content="done")
    client = make_client()

    mock_create = AsyncMock(return_value=fake_response)
    client.openai_client.chat = SimpleNamespace(
        completions=SimpleNamespace(create=mock_create)
    )

    history = [
        {"role": "user", "content": "What is 2+2?"},
        {"role": "assistant", "content": "4"},
        {"role": "user", "content": "And 3+3?"},
    ]
    await client.prompt(history)

    mock_create.assert_awaited_once_with(
        model=MODEL,
        messages=[_SYSTEM_MESSAGE, *history],
        tools=TOOLS,
        temperature=omit,
    )


async def test_prompt_multiple_tool_calls():
    """prompt handles multiple tool calls in one response."""
    tool_calls = [
        make_tool_call(call_id="call_1", arguments='{"a": 1, "b": 2}'),
        make_tool_call(call_id="call_2", arguments='{"a": 3, "b": 4}'),
    ]
    fake_response = make_chat_completion(
        content=None,
        tool_calls=tool_calls,
        finish_reason="tool_calls",
    )
    client = make_client()

    mock_create = AsyncMock(return_value=fake_response)
    client.openai_client.chat = SimpleNamespace(
        completions=SimpleNamespace(create=mock_create)
    )

    history = [{"role": "user", "content": "(1+2) + (3+4)?"}]
    result = await client.prompt(history)

    assert len(result.choices[0].message.tool_calls) == 2
