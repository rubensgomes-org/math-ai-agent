"""Start and run the FastAPI web server app."""

import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, PlainTextResponse
from openai import APIConnectionError, APIStatusError

from math_ai_agent.agent import Agent
from math_ai_agent.config.config import configure_logging, get_config
from math_ai_agent.llm import (
    AgentBusyError,
    ContentFilterError,
    LLMRequestFailedError,
    TokenLimitError,
)
from math_ai_agent.mcp.calc_client import CalcMCPClient
from math_ai_agent.payload import Payload

configure_logging()
logger = logging.getLogger(__name__)

_INDEX_HTML = Path(__file__).parent / "static" / "index.html"


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> AsyncIterator[None]:
    """Connect to the MCP server and build the agent for the app's lifetime."""
    async with CalcMCPClient() as calc:
        async with Agent(calc) as agent:
            fastapi_app.state.agent = agent
            yield
            logger.warning("Shutting down the application...")


# -------------------------------------------------
# Create the FastAPI app instance
# -------------------------------------------------
app = FastAPI(lifespan=lifespan)


def _llm_error_message(error: APIStatusError | APIConnectionError) -> str:
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
    """Accept a prompt text from the user and return an answer."""
    prompt_text = payload.text.strip()
    agent: Agent = request.app.state.agent
    try:
        logger.debug("Calling LLM with user prompt: %s", prompt_text)
        output = await agent.run(prompt_text, payload.display_reasoning)
    except AgentBusyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The server is busy. Please try again shortly.",
        ) from error
    except ContentFilterError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The prompt was blocked by the LLM safety filter.",
        ) from error
    except TokenLimitError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The LLM reached its token limit before answering.",
        ) from error
    except LLMRequestFailedError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The LLM request failed. Please try again.",
        ) from error
    except (APIStatusError, APIConnectionError) as error:
        logger.error("LLM service error answering prompt: %s", error)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM service error: {_llm_error_message(error)}",
        ) from error
    except Exception as error:
        logger.exception("Unexpected error answering prompt: %s", prompt_text)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        ) from error
    logger.debug(
        "Output:\n%s", json.dumps(output, indent=2, ensure_ascii=False)
    )
    return {"answer": output}


# -------------------------------------------------
# run() - starts uvicorn web server
# -------------------------------------------------
def run() -> None:
    """Run the web app with uvicorn on the configured host and port."""
    web = get_config().web
    uvicorn.run(app, host=web.host, port=web.port, log_config=None)
