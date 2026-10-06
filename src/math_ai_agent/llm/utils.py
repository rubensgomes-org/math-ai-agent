"""Helpers for building and logging LLM requests."""

import json
from typing import Any

import mcp_types
from openai import omit


def function_definition(tool: mcp_types.Tool) -> dict[str, Any]:
    """Return the MCP tool's ``name``, optional ``description``, and
    ``parameters`` (its input schema)."""
    definition: dict[str, Any] = {"name": tool.name}
    if tool.description:
        definition["description"] = tool.description
    definition["parameters"] = tool.input_schema
    return definition


def omit_if_none(value: Any) -> Any:
    """Return ``omit``, which leaves the field out of the request, for
    ``None``; otherwise return ``value``."""
    return omit if value is None else value


def to_json(value: Any) -> str:
    """Format a request payload as indented JSON for logging.

    SDK objects, such as ``ChatCompletionMessage``, are converted with
    ``model_dump``; anything else that JSON cannot encode uses ``str``.
    """

    def _encode(item: Any) -> Any:
        if hasattr(item, "model_dump"):
            return item.model_dump(exclude_none=True)
        return str(item)

    return json.dumps(value, indent=2, ensure_ascii=False, default=_encode)
