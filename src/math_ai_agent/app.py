"""Start and run the FastAPI web server app."""

import asyncio
import json
import logging
from collections.abc import Iterator
from contextlib import AsyncExitStack, contextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, PlainTextResponse
from openai import APIConnectionError, APIStatusError

from math_ai_agent.agent import Agent
from math_ai_agent.config.config import configure_logging, get_config
from math_ai_agent.llm import AgentError
from math_ai_agent.mcp.calc_client import CalcMCPClient
from math_ai_agent.payload import Payload

configure_logging()
logger = logging.getLogger(__name__)

_INDEX_HTML = Path(__file__).parent / "static" / "index.html"


# -------------------------------------------------
# Create the FastAPI app instance
# -------------------------------------------------
app = FastAPI()


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


# -------------------------------------------------
# Routes
# -------------------------------------------------
@app.get("/")
async def root() -> FileResponse:
    """Serve the main HTML page."""
    logger.debug("Serving root HTML page: %s", _INDEX_HTML)
    return FileResponse(_INDEX_HTML, media_type="text/html")


@app.get("/health", response_class=PlainTextResponse)
async def health() -> str:
    """Report that the server is up."""
    logger.debug("health check")
    return "OK"


@app.post("/prompt/")
async def prompt(payload: Payload, request: Request) -> dict[str, str]:
    """Accept a prompt from the user and return the LLM agent's answer."""
    prompt_text = payload.text.strip()
    agent: Agent = request.app.state.agent
    try:
        logger.debug("Calling LLM with user prompt: %s", prompt_text)
        output = await agent.run(prompt_text, payload.display_reasoning)
    except AgentError as error:
        logger.error("Agent error answering prompt: %s", error)
        raise HTTPException(
            status_code=error.status_code, detail=error.client_message
        ) from error
    except APIStatusError as error:
        logger.error("LLM API server error answering prompt: %s", error)
        raise HTTPException(
            status_code=error.status_code,
            detail=f"LLM API server error: {_error_message(error)}",
        ) from error
    except APIConnectionError as error:
        logger.error(
            "LLM API server network connection error answering prompt: %s",
            error,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "LLM API server network connection error: "
                f"{_error_message(error)}"
            ),
        ) from error
    except Exception as error:
        logger.exception("Unexpected error answering prompt: %s", prompt_text)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "An unexpected error occurred processing the prompt. "
                "Please try again."
            ),
        ) from error
    logger.debug(
        "Output:\n%s", json.dumps(output, indent=2, ensure_ascii=False)
    )
    return {"answer": output}


class _GracefulServer(uvicorn.Server):
    """Uvicorn server that does not re-raise SIGINT/SIGTERM on shutdown.

    ``uvicorn.Server`` re-raises the captured signal after ``serve()``
    returns, which cancels the caller's cleanup and prints a traceback.
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
def run() -> int:
    """Run the web app with uvicorn; return the process exit code."""
    return asyncio.run(_serve())


async def _serve() -> int:
    """Connect to the MCP server, then serve until shutdown.

    Connecting before uvicorn starts keeps MCP errors out of uvicorn's
    lifespan, so they are logged here without a traceback.
    """
    async with AsyncExitStack() as stack:
        try:
            logger.info(
                "Connecting to calculator MCP server %s",
                get_config().server.calculator_mcp.url,
            )
            calc = await stack.enter_async_context(CalcMCPClient())
            logger.info(
                "Initializing Agent to use LLM model %s",
                get_config().llm.model,
            )
            agent = await stack.enter_async_context(Agent(calc))
        except Exception as error:  # pylint: disable=broad-exception-caught
            logger.error("Cannot start the application: %s", error)
            return 1
        app.state.agent = agent
        web = get_config().web
        config = uvicorn.Config(
            app, host=web.host, port=web.port, log_config=None
        )
        logger.info("Starting web server on %s:%s", web.host, web.port)
        await _GracefulServer(config).serve()
        logger.warning("Shutting down the application...")
    return 0
