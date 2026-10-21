"""Test values shared by the Chat Completions and Responses tests."""

from types import SimpleNamespace

import mcp_types
from ai_utils_lib.config.models import Model

API_KEY_ENV = "TEST_LLM_KEY"
BASE_URL = "http://localhost:11434/v1"
MODEL = "test-model"
INSTRUCTIONS = "Test instructions."
TOOL_RESULT = SimpleNamespace(data=8, structured_content={"result": 8})
ADD_TOOL = mcp_types.Tool(
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
MCP_TOOLS = [
    mcp_types.Tool(
        name="add",
        description="Add two numbers",
        input_schema={"type": "object", "properties": {}},
    ),
    mcp_types.Tool(
        name="noop", input_schema={"type": "object", "properties": {}}
    ),
]
# The function definitions built from MCP_TOOLS.
TOOLS_DEFINITIONS = [
    {
        "name": "add",
        "description": "Add two numbers",
        "parameters": {"type": "object", "properties": {}},
    },
    {"name": "noop", "parameters": {"type": "object", "properties": {}}},
]


def llm_config(**updates) -> Model:
    """Build a ``Model`` with test values and ``updates`` applied."""
    return Model(
        base_url=BASE_URL,
        name=MODEL,
        api_key_env=API_KEY_ENV,
        instructions=INSTRUCTIONS,
        **updates,
    )
