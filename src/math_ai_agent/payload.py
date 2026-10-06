"""Pydantic model for the user prompt request."""

from pydantic import BaseModel


class Payload(BaseModel):
    """The prompt text and display choice sent by the web page."""

    text: str
    display_reasoning: bool = True
