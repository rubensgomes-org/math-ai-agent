"""Start and run the FastAPI web server app."""

import asyncio
import logging
from collections.abc import Iterator
from contextlib import AsyncExitStack, contextmanager
from pathlib import Path

import uvicorn
from ai_utils_lib.config.models import AppConfig
from fastapi import APIRouter, FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from openai import APIConnectionError, APIStatusError, APITimeoutError

from math_ai_agent.agent import Agent, AgentError, LLMRateLimitedError
from math_ai_agent.body_size_limit import BodySizeLimitMiddleware
from math_ai_agent.mcp.calc_client import CalcMCPClient
from math_ai_agent.rate_limit import SlidingWindowRateLimiter
from math_ai_agent.schemas import PromptRequest, PromptResponse

logger = logging.getLogger(__name__)

_INDEX_HTML = Path(__file__).parent / "static" / "index.html"

_PROMPT_TIMEOUT_SECONDS = 300
# Far above a MAX_PROMPT_CHARS prompt, even with 4-byte characters.
_MAX_BODY_BYTES = 64 * 1024
_PROMPTS_PER_CLIENT = 10
_RATE_LIMIT_WINDOW_SECONDS = 60

_LLM_RATE_LIMITED = LLMRateLimitedError.client_message
_LLM_TIMED_OUT = "The LLM took too long to answer. Please try again."
_LLM_UNREACHABLE = "Cannot reach the LLM. Please try again later."
_LLM_FAILED = "The LLM failed to answer the prompt."
_PROMPT_TIMED_OUT = "The agent took too long to answer. Please try again."
_CLIENT_RATE_LIMITED = "Too many prompts. Please try again shortly."
_UNEXPECTED_ERROR = (
    "An unexpected error occurred processing the prompt. Please try again."
)

# Errors mapped by the app's exception handlers.
_HANDLED_ERRORS = (AgentError, APIStatusError, APIConnectionError, TimeoutError)

_router = APIRouter()


def create_app(
    agent: Agent, rate_limiter: SlidingWindowRateLimiter | None = None
) -> FastAPI:
    """Create the web app serving prompts with ``agent``."""
    app = FastAPI()
    app.state.agent = agent
    app.state.rate_limiter = rate_limiter or SlidingWindowRateLimiter(
        _PROMPTS_PER_CLIENT, _RATE_LIMIT_WINDOW_SECONDS
    )
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=_MAX_BODY_BYTES)
    app.include_router(_router)
    app.add_exception_handler(AgentError, _agent_error_handler)
    app.add_exception_handler(APIStatusError, _llm_api_error_handler)
    app.add_exception_handler(APIConnectionError, _llm_api_error_handler)
    app.add_exception_handler(TimeoutError, _prompt_timeout_handler)
    return app


# -------------------------------------------------
# Routes
# -------------------------------------------------
@_router.get("/")
async def root() -> FileResponse:
    """Serve the main HTML page."""
    logger.debug("Serving root HTML page: %s", _INDEX_HTML)
    return FileResponse(_INDEX_HTML, media_type="text/html")


@_router.get("/health", response_class=PlainTextResponse)
async def health() -> str:
    """Report liveness only; the LLM and MCP server are not checked."""
    logger.debug("health check")
    return "OK"


@_router.post("/prompt")
@_router.post("/prompt/", include_in_schema=False)
async def prompt(payload: PromptRequest, request: Request) -> PromptResponse:
    """Accept a prompt from the user and return the LLM agent's answer."""
    _check_rate_limit(request)
    agent: Agent = request.app.state.agent
    logger.debug("Calling LLM with user prompt: %s", payload.text)
    try:
        async with asyncio.timeout(_PROMPT_TIMEOUT_SECONDS):
            result = await agent.run(payload.text)
    except _HANDLED_ERRORS:
        raise
    except Exception as error:
        logger.exception("Unexpected error answering prompt")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, _UNEXPECTED_ERROR
        ) from error
    logger.debug("Answer:\n%s", result.answer)
    return PromptResponse(
        answer=result.answer,
        reasoning=result.reasoning if payload.display_reasoning else None,
    )


def _check_rate_limit(request: Request) -> None:
    """Raise 429 when the client exceeded its prompt rate.

    Behind proxies, uvicorn sets the client from X-Forwarded-For only for
    peers listed in the ``FORWARDED_ALLOW_IPS`` environment variable.
    """
    client = request.client.host if request.client else "unknown"
    retry_after = request.app.state.rate_limiter.try_acquire(client)
    if retry_after is None:
        return
    logger.warning("Rate limiting prompts from client %s", client)
    raise HTTPException(
        status.HTTP_429_TOO_MANY_REQUESTS,
        _CLIENT_RATE_LIMITED,
        headers={"Retry-After": str(retry_after)},
    )


# -------------------------------------------------
# Exception handlers
# -------------------------------------------------
async def _agent_error_handler(
    request: Request, error: Exception
) -> JSONResponse:
    """Return an ``AgentError``'s status, client message and Retry-After."""
    assert isinstance(error, AgentError)
    logger.error("Agent error answering prompt: %s", error)
    headers = (
        None
        if error.retry_after_seconds is None
        else {"Retry-After": str(error.retry_after_seconds)}
    )
    return _error_response(error.status_code, error.client_message, headers)


async def _llm_api_error_handler(
    request: Request, error: Exception
) -> JSONResponse:
    """Map an LLM API error to a response safe for the client."""
    assert isinstance(error, (APIStatusError, APIConnectionError))
    logger.error(
        "LLM API %s answering prompt: %s",
        type(error).__name__,
        _error_message(error),
    )
    if isinstance(error, APITimeoutError):
        return _error_response(status.HTTP_504_GATEWAY_TIMEOUT, _LLM_TIMED_OUT)
    if isinstance(error, APIConnectionError):
        return _error_response(status.HTTP_502_BAD_GATEWAY, _LLM_UNREACHABLE)
    if error.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        retry_after = error.response.headers.get("retry-after")
        return _error_response(
            status.HTTP_429_TOO_MANY_REQUESTS,
            _LLM_RATE_LIMITED,
            {"Retry-After": retry_after} if retry_after else None,
        )
    return _error_response(status.HTTP_502_BAD_GATEWAY, _LLM_FAILED)


async def _prompt_timeout_handler(
    request: Request, error: Exception
) -> JSONResponse:
    """Return 504 when a prompt exceeds its total time limit."""
    logger.error(
        "Prompt exceeded %s seconds: %s",
        _PROMPT_TIMEOUT_SECONDS,
        type(error).__name__,
    )
    return _error_response(status.HTTP_504_GATEWAY_TIMEOUT, _PROMPT_TIMED_OUT)


def _error_response(
    status_code: int, detail: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse({"detail": detail}, status_code, headers)


def _error_message(error: APIStatusError | APIConnectionError) -> str:
    """Return the LLM provider's error message, or the SDK's when absent."""
    body = getattr(error, "body", None)
    if isinstance(body, dict):
        details = body.get("error", body)
        if isinstance(details, dict) and isinstance(
            details.get("message"), str
        ):
            return details["message"]
    return error.message


class _GracefulServer(uvicorn.Server):
    """Uvicorn server that does not re-raise SIGINT/SIGTERM on shutdown.

    ``uvicorn.Server`` re-raises the captured signal after ``serve()``
    returns, which cancels the caller's cleanup and prints a traceback.
    Relies on uvicorn's private ``_captured_signals``; uvicorn is pinned to
    a minor version and a test checks the attribute.
    """

    @contextmanager
    def capture_signals(self) -> Iterator[None]:
        """Install uvicorn's signal handlers, then drop captured signals."""
        with super().capture_signals():
            try:
                yield
            finally:
                self._captured_signals.clear()


# -------------------------------------------------
# run() - connects to the MCP server, then starts uvicorn web server
# -------------------------------------------------
def run(app_config: AppConfig) -> int:
    """Run the web app with uvicorn; return the process exit code."""
    return asyncio.run(_serve(app_config))


async def _serve(app_config: AppConfig) -> int:
    """Connect to the MCP server, then serve until shutdown.

    Connecting before uvicorn starts keeps MCP errors out of uvicorn's
    lifespan, so they are logged here without a traceback.
    """
    async with AsyncExitStack() as stack:
        try:
            calc = await stack.enter_async_context(
                CalcMCPClient(app_config.mcp["calculator"])
            )
            logger.info(
                "Initializing Agent to use LLM model: %s at url: %s",
                app_config.model.name,
                app_config.model.base_url,
            )
            agent = await stack.enter_async_context(
                Agent(calc, app_config.model)
            )
        except Exception as error:  # pylint: disable=broad-exception-caught
            logger.error(
                "Cannot start the application: %s: %s",
                type(error).__name__,
                error,
            )
            return 1
        uv_config = uvicorn.Config(
            create_app(agent),
            host=app_config.web.host,
            port=app_config.web.port,
            log_config=None,
        )
        logger.info(
            "Starting web server on %s:%s",
            app_config.web.host,
            app_config.web.port,
        )
        await _GracefulServer(uv_config).serve()
        logger.info("Shutting down the application...")
    return 0
