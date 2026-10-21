"""Exceptions raised by the LLM agent."""

from http import HTTPStatus
from typing import ClassVar


class AgentError(RuntimeError):
    """Base class for agent errors mapped to an HTTP response.

    The class attributes give the response: ``status_code``, a
    ``client_message`` safe to return, and an optional Retry-After delay.
    The exception message is for logs.
    """

    status_code: ClassVar[HTTPStatus] = HTTPStatus.INTERNAL_SERVER_ERROR
    client_message: ClassVar[str] = "The agent failed to answer the prompt."
    retry_after_seconds: ClassVar[int | None] = None


class AgentBusyError(AgentError):
    """Raised when the maximum number of prompts is already running."""

    status_code = HTTPStatus.SERVICE_UNAVAILABLE
    client_message = "The server is busy. Please try again shortly."
    retry_after_seconds = 5


class TokenLimitError(AgentError):
    """Raised when the LLM stops because it reached its token limit."""

    client_message = "The LLM reached its token limit before answering."


class ContentFilterError(AgentError):
    """Raised when the LLM provider blocks content for safety reasons."""

    status_code = HTTPStatus.UNPROCESSABLE_CONTENT
    client_message = "The answer was blocked by the LLM safety filter."


class LLMRequestFailedError(AgentError):
    """Raised when the LLM provider reports the response as failed."""

    status_code = HTTPStatus.BAD_GATEWAY
    client_message = "The LLM request failed. Please try again."


class LLMRateLimitedError(LLMRequestFailedError):
    """Raised when the LLM provider fails the response for rate limiting."""

    status_code = HTTPStatus.TOO_MANY_REQUESTS
    client_message = "The LLM is busy. Please try again shortly."
    retry_after_seconds = 10


class MaxTurnsExceededError(AgentError):
    """Raised when the LLM gives no answer within the agent's turn limit."""

    status_code = HTTPStatus.BAD_GATEWAY
    client_message = "The LLM did not answer within the allowed turns."


class UnexpectedResponseError(AgentError):
    """Raised when the LLM response has an unsupported shape or status."""

    status_code = HTTPStatus.BAD_GATEWAY
    client_message = "The LLM returned an unexpected response."
