"""Live integration test for the FastAPI web server.

It launches a FastAPI web server with the following endpoints:
    - ``GET /`` returns the index.html page.
    - ``POST /prompt/`` submits user prompt and returns same prompt back.

From the project root folder run:
    poetry run uvicorn tests.integration.test_app:app --reload
"""

import logging
from pathlib import Path

from ai_utils_lib.config.config import load_config
from ai_utils_lib.config.file_load_config import configure_logging
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from math_ai_agent.schemas import PromptRequest

configure_logging(load_config("math_ai_agent"))
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent.parent.parent / "src/math_ai_agent/static"

# -------------------------------------------------
# Create the FastAPI app instance
# -------------------------------------------------
app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ----- Routes -----
@app.get("/", response_class=HTMLResponse)
async def root() -> str:
    """Serve the main HTML page.

    Returns:
        The HTML content of the index page.
    """
    logger.debug("Serving root HTML page: %s%s", STATIC_DIR, "/index.html")
    return (STATIC_DIR / "index.html").read_text()


@app.post("/prompt/")
async def prompt(payload: PromptRequest) -> dict[str, str]:
    """Accept a prompt text from the user and return an answer.

    Args:
        payload: The validated question from the request body.

    Returns:
        A dict containing the ``answer`` key with the response.
    """
    logger.debug("Received prompt: %s", payload.text)
    prompt_text = payload.text.strip()
    logger.debug("Response: %s", prompt_text)
    return {"answer": prompt_text}
