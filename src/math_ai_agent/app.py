# General Disclaimer
#
# **AI Generated Content**
#
# This project's source code and documentation were generated predominantly
# by an Artificial Intelligence Large Language Model (AI LLM). The project
# lead, [Rubens Gomes](https://rubensgomes.com), provided initial prompts,
# reviewed, and made refinements to the generated output. While human review and
# refinement have occurred, users should be aware that the output may contain
# inaccuracies, errors, or security vulnerabilities
#
# **Third-Party Content Notice**
#
# This software may include components or snippets derived from third-party
# sources. The software's users and distributors are responsible for ensuring
# compliance with any underlying licenses applicable to such components.
#
# **Copyright Status Statement**
#
# Copyright protection, if any, is limited to the original
# human contributions and modifications made to this project.
# The AI-generated portions of the code and
# documentation are not subject to copyright and are considered to be in the
# public domain.
#
# **Limitation of liability**
#
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES, OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR
# OTHERWISE, ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.
#
# **No-Warranty Disclaimer**
#
# THIS SOFTWARE IS PROVIDED 'AS IS,' WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT.

"""The FastAPI web server app.

Launches a FastAPI web server with the following endpoints:
    - `GET /` returns the index.html page.
    - `GET /health` returns 200 with plain text `OK`.
    - `POST /prompt/` submits user prompt and returns AI response.

From the project root folder run::

    poetry run math-ai-agent

Pass ``--version`` to print the installed version and exit.
"""

import argparse
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import version
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, PlainTextResponse

from math_ai_agent.config.config import configure_logging, get_config
from math_ai_agent.llm import (
    Agent,
    AgentBusyError,
    ContentFilterError,
    LLMRequestFailedError,
    TokenLimitError,
)
from math_ai_agent.mcp.calc_connection import CalcFastMCPConnection
from math_ai_agent.payload import Payload

configure_logging()
logger = logging.getLogger(__name__)

_INDEX_HTML = Path(__file__).parent / "static" / "index.html"
_DISTRIBUTION_NAME = "math-ai-agent"


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> AsyncIterator[None]:
    """Initialize and connect to MCP server and build the agent for the app's lifetime."""
    logger.info("Starting application...")
    async with CalcFastMCPConnection() as calc:
        logger.info("Established the Calculator MCP connection")
        fastapi_app.state.agent = await Agent.create(calc)
        yield
        logger.info("Shutting down the application...")


# -------------------------------------------------
# Create the FastAPI app instance
# -------------------------------------------------
app = FastAPI(lifespan=lifespan)


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
    return "OK"


@app.post("/prompt/")
async def prompt(payload: Payload, request: Request) -> dict[str, str]:
    """Accept a prompt text from the user and return an answer.

    Args:
        payload: The validated question and display choice from the
            request body.
        request: The request, used to reach the app's ``Agent``.

    Returns:
        A dict containing the `answer` key with the response.

    Raises:
        HTTPException: 503 if too many prompts are already running,
            422 if the content is blocked by a safety filter, 502 if
            the LLM reaches its token limit or the request fails, or
            500 for any other error.
    """
    logger.debug("Received prompt: %s", payload.text)
    prompt_text = payload.text.strip()
    logger.debug("Calling LLM with user prompt: %s", prompt_text)
    agent: Agent = request.app.state.agent
    try:
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
    except Exception as error:
        logger.exception("Unexpected error answering prompt: %s", prompt_text)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        ) from error
    logger.debug("Output:\n%s", json.dumps(output, indent=2))
    return {"answer": output}


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse the command-line arguments; ``--version`` prints and exits."""
    parser = argparse.ArgumentParser(prog=_DISTRIBUTION_NAME)
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {version(_DISTRIBUTION_NAME)}",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Run the web app with uvicorn on the configured host and port.

    ``log_config=None`` stops uvicorn from replacing the logging
    configuration from ``config.yaml`` with its own.

    Args:
        argv: Command-line arguments; defaults to ``sys.argv[1:]``.
    """
    _parse_args(argv)
    web = get_config().web
    uvicorn.run(app, host=web.host, port=web.port, log_config=None)
