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
    - `POST /prompt/` submits user prompt and returns AI response.

From the project root folder run::

    poetry run uvicorn math_ai_agent.app:app --reload
"""

import json
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from math_ai_agent.config.config import configure_logging
from math_ai_agent.llm.llm import agent_loop
from math_ai_agent.models import Prompt

configure_logging()
logger = logging.getLogger(__name__)

# folder to HTML file
_STATIC_DIR = Path(__file__).parent / "static"

# -------------------------------------------------
# Create the FastAPI app instance
# -------------------------------------------------
app = FastAPI()
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


# -------------------------------------------------
# Routes
# -------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def root() -> str:
    """Serve the main HTML page.

    Returns:
        The HTML content of the index page.
    """
    logger.debug("Serving root HTML page: %s%s", _STATIC_DIR, "/index.html")
    return (_STATIC_DIR / "index.html").read_text()


@app.post("/prompt/")
async def prompt(payload: Prompt) -> dict[str, str]:
    """Accept a prompt text from the user and return an answer.

    Args:
        payload: The validated question from the request body.

    Returns:
        A dict containing the `answer` key with the response.

    Raises:
        RuntimeError: If the agent loop encounters a token limit
            or content filter error.
        ValueError: If the LLM returns an unknown finish reason.
    """
    logger.debug("Received prompt: %s", payload.text)
    prompt_text = payload.text.strip()
    logger.debug("Calling LLM with user prompt: %s", prompt_text)
    output = await agent_loop(prompt_text)
    logger.debug("Output:\n%s", json.dumps(output, indent=2))
    return {"answer": output}
