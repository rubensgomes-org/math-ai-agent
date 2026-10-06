"""Helpers for the agent loop."""

import logging
from typing import Any

from openai.types.responses import (
    Response,
    ResponseOutputItem,
    ResponseReasoningItem,
)

logger = logging.getLogger(__name__)

_EMPTY_SECTION = "(none)"


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


def next_turn_input(
    stateful: bool,
    history: list[Any],
    response_outputs: list[ResponseOutputItem],
    tool_outputs: list[Any],
) -> list[Any]:
    """Return the input items for the next turn.

    Stateful turns send only the tool outputs and continue the stored
    response.  Stateless turns replay the whole conversation,
    including reasoning items, so the model keeps its context.
    """
    if stateful:
        logger.debug("LLM model is operating in stateful mode")
        return tool_outputs
    logger.debug("LLM model is operating in stateless mode.")
    output_items = [
        item.model_dump(exclude_none=True) for item in response_outputs
    ]
    return [*history, *output_items, *tool_outputs]


def format_answer(reasoning: list[str], final_response: str) -> str:
    """Format the answer as reasoning and final response sections.

    Surrounding whitespace is stripped from each text, so sections are
    separated by exactly one blank line and turns by a line break.  Each
    section shows ``(none)`` when the LLM returned no text for it.
    """
    sections = {
        "reasoning": "\n".join(
            text.strip() for text in reasoning if text.strip()
        ),
        "final response": final_response.strip(),
    }
    return "\n\n".join(
        f"{heading}:\n{text or _EMPTY_SECTION}"
        for heading, text in sections.items()
    )


def tool_error(tool_name: str, message: str) -> str:
    """Log a failed tool call and return the error text for the LLM."""
    logger.warning("Calculator MCP tool %s failed: %s", tool_name, message)
    return message
