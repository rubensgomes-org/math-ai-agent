"""agent — LLM agent sub-package for math_ai_agent.

Re-exports the agent and its exceptions so callers can use
``from math_ai_agent.agent import AgentError``.
"""

from math_ai_agent.agent.agent import Agent, AgentAnswer
from math_ai_agent.agent.errors import (
    AgentBusyError,
    AgentError,
    ContentFilterError,
    LLMRateLimitedError,
    LLMRequestFailedError,
    MaxTurnsExceededError,
    TokenLimitError,
    UnexpectedResponseError,
)

__all__ = [
    "Agent",
    "AgentAnswer",
    "AgentBusyError",
    "AgentError",
    "ContentFilterError",
    "LLMRateLimitedError",
    "LLMRequestFailedError",
    "MaxTurnsExceededError",
    "TokenLimitError",
    "UnexpectedResponseError",
]
