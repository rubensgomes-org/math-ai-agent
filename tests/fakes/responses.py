"""Fake Responses API objects and client builders for tests."""

from types import SimpleNamespace

from openai.types.responses import (
    ResponseFunctionToolCall,
    ResponseOutputMessage,
    ResponseOutputText,
    ResponseReasoningItem,
    ResponseUsage,
)
from openai.types.responses.response_reasoning_item import Content, Summary
from openai.types.responses.response_usage import (
    InputTokensDetails,
    OutputTokensDetails,
)

from math_ai_agent.agent import AgentAnswer
from math_ai_agent.llm.responses_client import ResponsesClient
from tests.fakes.common import ADD_TOOL, llm_config

USAGE = ResponseUsage(
    input_tokens=10,
    input_tokens_details=InputTokensDetails(
        cached_tokens=2, cache_write_tokens=0
    ),
    output_tokens=5,
    output_tokens_details=OutputTokensDetails(reasoning_tokens=3),
    total_tokens=15,
)
# The Responses tool definitions the client sends for ADD_TOOL.
TOOLS = [
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
        "strict": False,
    }
]


def make_message(text="42"):
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


def make_reasoning(summaries=(), texts=None):
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


def agent_answer(final="", reasoning=None):
    """Build the expected ``AgentAnswer`` returned by ``Agent.run``."""
    return AgentAnswer(answer=final, reasoning=reasoning)


def make_function_call(
    call_id="call-1", name="add", arguments='{"a": 4, "b": 4}'
):
    """Build a Responses ``function_call`` output item."""
    return ResponseFunctionToolCall(
        call_id=call_id,
        name=name,
        arguments=arguments,
        type="function_call",
    )


def make_response(
    status="completed",
    response_id="resp-1",
    output=None,
    usage=USAGE,
    incomplete_details=None,
    error=None,
):
    """Build a fake Response-like object for the Responses API."""
    if output is None:
        output = [make_message()]
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


def make_client(is_stateful=False):
    """Create a ``ResponsesClient`` with test parameters."""
    return ResponsesClient(llm_config(is_stateful=is_stateful), [ADD_TOOL])
