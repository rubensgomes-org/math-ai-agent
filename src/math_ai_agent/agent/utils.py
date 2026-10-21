"""Helpers for the agent loop."""

from typing import Any

from openai.types.responses import (
    Response,
    ResponseOutputItem,
    ResponseReasoningItem,
)


def reasoning_texts(response: Response) -> list[str]:
    """Return the reasoning text in a response's reasoning items.

    An item's ``summary`` is used only when it has no ``content``: some
    providers repeat the content in the summary, and others, such as
    OpenAI, return only the summary.
    """
    return [
        part.text
        for item in response.output
        if isinstance(item, ResponseReasoningItem)
        for part in item.content or item.summary
    ]


def replay_input(
    history: list[Any],
    response_outputs: list[ResponseOutputItem],
    tool_outputs: list[Any],
) -> list[Any]:
    """Return the whole conversation as the next stateless turn's input.

    Reasoning items are replayed too, so the model keeps its context.
    """
    output_items = [
        item.model_dump(exclude_none=True) for item in response_outputs
    ]
    return [*history, *output_items, *tool_outputs]


def join_reasoning(reasoning: list[str]) -> str | None:
    """Join the stripped, non-blank reasoning texts by line breaks.

    Returns None when the LLM returned no reasoning text.
    """
    stripped = (text.strip() for text in reasoning)
    return "\n".join(text for text in stripped if text) or None
