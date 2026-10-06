"""Exceptions raised by the LLM agent."""


class AgentBusyError(RuntimeError):
    """Raised when the maximum number of prompts is already running."""


class TokenLimitError(RuntimeError):
    """Raised when the LLM stops because it reached its token limit."""


class ContentFilterError(RuntimeError):
    """Raised when the LLM provider blocks content for safety reasons."""


class LLMRequestFailedError(RuntimeError):
    """Raised when the LLM provider reports the response as failed."""

    def __init__(self, message: str, code: str | None = None) -> None:
        """Create the error.

        Args:
            message: Error description.
            code: Provider error code, such as ``server_error``.
        """
        super().__init__(message)
        self.code = code
