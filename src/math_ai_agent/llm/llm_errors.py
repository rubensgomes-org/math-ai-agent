"""Exceptions raised by the LLM agent."""

from http import HTTPStatus


class AgentError(RuntimeError):
    """Base class for agent errors mapped to an HTTP response.

    The exception message is for logs; ``client_message`` is safe to return
    to the client.
    """

    status_code: HTTPStatus = HTTPStatus.INTERNAL_SERVER_ERROR
    client_message: str = "The agent failed to answer the prompt."


class AgentBusyError(AgentError):
    """Raised when the maximum number of prompts is already running."""

    status_code = HTTPStatus.SERVICE_UNAVAILABLE
    client_message = "The server is busy. Please try again shortly."


class TokenLimitError(AgentError):
    """Raised when the LLM stops because it reached its token limit."""

    # TODO: needs to fix status_code. this may not be an error.
    status_code = HTTPStatus.BAD_GATEWAY
    client_message = "The LLM reached its token limit before answering."


class ContentFilterError(AgentError):
    """Raised when the LLM provider blocks content for safety reasons."""

    # TODO: needs to fix status_code. this may not be an error.
    status_code = HTTPStatus.UNPROCESSABLE_CONTENT
    client_message = "The prompt was blocked by the LLM safety filter."


class LLMRequestFailedError(AgentError):
    """Raised when the LLM provider reports the response as failed."""

    # TODO: needs to fix status_code. this may not be an error.
    status_code = HTTPStatus.BAD_GATEWAY
    client_message = "The LLM request failed. Please try again."

    def __init__(self, message: str, code: str | None = None) -> None:
        """Create the error with the provider's error code, if any."""
        super().__init__(message)
        self.code = code
