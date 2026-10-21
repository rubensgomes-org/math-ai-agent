"""Fake Chat Completions objects and client builders for tests."""

from types import SimpleNamespace

from openai.types.chat import (
    ChatCompletionMessage,
    ChatCompletionMessageFunctionToolCall,
)
from openai.types.chat.chat_completion_message_function_tool_call import (
    Function,
)
from openai.types.completion_usage import (
    CompletionTokensDetails,
    CompletionUsage,
    PromptTokensDetails,
)

from math_ai_agent.llm.chat_completions_client import ChatCompletionsClient
from tests.fakes.common import ADD_TOOL, llm_config

USAGE = CompletionUsage(
    prompt_tokens=10,
    prompt_tokens_details=PromptTokensDetails(cached_tokens=2),
    completion_tokens=5,
    completion_tokens_details=CompletionTokensDetails(reasoning_tokens=3),
    total_tokens=15,
)
# The Chat Completions tool definitions the client sends for ADD_TOOL.
TOOLS = [
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


def make_chat_completion(
    content="42", tool_calls=None, finish_reason="stop", usage=USAGE
):
    """Build a fake ChatCompletion-like response object."""
    message = ChatCompletionMessage(
        role="assistant", content=content, tool_calls=tool_calls
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

    response.model_dump = lambda **_: {
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


def make_tool_call(call_id="call-1", name="add", arguments='{"a": 4, "b": 4}'):
    """Build a function tool call as returned by the OpenAI SDK."""
    return ChatCompletionMessageFunctionToolCall(
        id=call_id,
        type="function",
        function=Function(name=name, arguments=arguments),
    )


def make_client(**updates):
    """Create a ``ChatCompletionsClient`` with test parameters."""
    return ChatCompletionsClient(llm_config(**updates), [ADD_TOOL])
