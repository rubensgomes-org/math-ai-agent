"""Pydantic models for the prompt request and response."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, StrictBool, StringConstraints

# static/index.html sets the same limit as the textarea maxlength.
MAX_PROMPT_CHARS = 4000


class PromptRequest(BaseModel):
    """The prompt text and display choice sent by the web page."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, min_length=1, max_length=MAX_PROMPT_CHARS
        ),
    ]
    display_reasoning: StrictBool = True


class PromptResponse(BaseModel):
    """The agent's final answer and, when requested, its reasoning."""

    model_config = ConfigDict(frozen=True)

    answer: str
    reasoning: str | None = None
