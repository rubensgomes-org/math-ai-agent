"""Unit tests for :mod:`math_ai_agent.llm.responses_client`."""

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from openai import omit

from math_ai_agent.llm.responses_client import ResponsesClient

from tests.fakes.common import (
    ADD_TOOL,
    INSTRUCTIONS,
    MCP_TOOLS,
    MODEL,
    TOOLS_DEFINITIONS,
    llm_config,
)
from tests.fakes.responses import (
    TOOLS,
    make_client,
    make_function_call,
    make_message,
    make_response,
)

# ---------------------------------------------------------------------------
# __init__ — validation
# ---------------------------------------------------------------------------


def test_init_sets_instance_attributes():
    """Instantiation sets instance attributes."""
    client = ResponsesClient(llm_config(), [ADD_TOOL])
    assert client.openai_client is not None
    assert client.tools == TOOLS
    assert client.model_name == MODEL
    assert isinstance(client, ResponsesClient)


# ---------------------------------------------------------------------------
# _format_tools
# ---------------------------------------------------------------------------


def test_format_tools_flattens_each_definition():
    """Each definition becomes a flat Responses function tool."""
    # pylint: disable-next=protected-access
    assert ResponsesClient._format_tools(MCP_TOOLS) == [
        {"type": "function", "strict": False, **definition}
        for definition in TOOLS_DEFINITIONS
    ]


def test_format_tools_empty_list():
    # pylint: disable-next=protected-access
    assert ResponsesClient._format_tools([]) == []


# ---------------------------------------------------------------------------
# prompt
# ---------------------------------------------------------------------------


async def test_prompt_returns_response():
    """prompt returns the Response from the API."""
    fake_response = make_response(output=[make_message("The answer is 8")])
    client = make_client()

    mock_create = AsyncMock(return_value=fake_response)
    client.openai_client.responses = SimpleNamespace(create=mock_create)

    history = [{"role": "user", "content": "4+4?"}]
    result = await client.prompt(history)

    assert result is fake_response
    assert result.output_text == "The answer is 8"


async def test_prompt_sends_expected_arguments():
    """prompt sends input, tools, instructions, store=False and include."""
    fake_response = make_response()
    client = make_client()

    mock_create = AsyncMock(return_value=fake_response)
    client.openai_client.responses = SimpleNamespace(create=mock_create)

    history = [{"role": "user", "content": "4+4?"}]
    await client.prompt(history)

    mock_create.assert_awaited_once_with(
        model=MODEL,
        input=history,
        tools=TOOLS,
        instructions=INSTRUCTIONS,
        store=False,
        previous_response_id=omit,
        include=["reasoning.encrypted_content"],
        temperature=omit,
    )


async def test_prompt_stateful_sends_previous_response_id():
    """A stateful client stores and continues the previous response."""
    client = make_client(is_stateful=True)

    mock_create = AsyncMock(return_value=make_response())
    client.openai_client.responses = SimpleNamespace(create=mock_create)

    tool_output = {
        "type": "function_call_output",
        "call_id": "c",
        "output": "8",
    }
    await client.prompt([tool_output], "resp-1")

    mock_create.assert_awaited_once_with(
        model=MODEL,
        input=[tool_output],
        tools=TOOLS,
        instructions=INSTRUCTIONS,
        store=True,
        previous_response_id="resp-1",
        include=omit,
        temperature=omit,
    )


@pytest.mark.parametrize("temperature", [0.0, 0.2])
async def test_prompt_sends_temperature(temperature):
    """A set temperature is sent, including 0."""
    client = ResponsesClient(llm_config(temperature=temperature), [ADD_TOOL])
    mock_create = AsyncMock(return_value=make_response())
    client.openai_client.responses = SimpleNamespace(create=mock_create)

    await client.prompt([{"role": "user", "content": "4+4?"}])

    assert mock_create.await_args.kwargs["temperature"] == temperature


async def test_prompt_with_function_call():
    """prompt handles a response with a function_call item."""
    fake_response = make_response(output=[make_function_call()])
    client = make_client()

    mock_create = AsyncMock(return_value=fake_response)
    client.openai_client.responses = SimpleNamespace(create=mock_create)

    result = await client.prompt([{"role": "user", "content": "4+4?"}])

    assert result.output_text == ""
    assert result.output[0].name == "add"


async def test_prompt_stateless_rejects_previous_response_id():
    """A stateless client cannot continue a stored response."""
    client = make_client()
    mock_create = AsyncMock()
    client.openai_client.responses = SimpleNamespace(create=mock_create)

    with pytest.raises(ValueError, match="requires a stateful client"):
        await client.prompt([], "resp-1")
    mock_create.assert_not_awaited()


async def test_debug_logs_tools_and_response(caplog):
    """At DEBUG, the tools are logged once and each response as JSON."""
    caplog.set_level(logging.DEBUG, logger="math_ai_agent.llm")
    client = make_client()
    client.openai_client.responses = SimpleNamespace(
        create=AsyncMock(return_value=make_response())
    )
    await client.prompt([{"role": "user", "content": "4+4?"}])
    assert "LLM tools:" in caplog.text
    assert "LLM response:" in caplog.text


def test_log_token_usage_logs_counts(caplog):
    caplog.set_level(logging.INFO)
    make_client().log_token_usage(make_response())
    assert "input=10 cached=2 output=5 reasoning=3 total=15" in caplog.text


def test_log_token_usage_warns_without_usage(caplog):
    make_client().log_token_usage(make_response(usage=None))
    assert "No token usage reported" in caplog.text
