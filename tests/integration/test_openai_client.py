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

"""Integration test client for the OpenAI Responses API.

Sends a simple prompt to verify end-to-end connectivity with the
OpenAI API.  Run standalone with::

    poetry run python tests/integration/test_openai_client.py**

** Ensure the LLM defined below is running locally (e.g., ollama run phi)

"""

import logging
import time

from openai import OpenAI

from math_ai_agent.config.config import (
    configure_logging,
    get_api_key,
    get_model,
    get_model_base_url,
)

configure_logging()
logger = logging.getLogger(__name__)

_SYSTEM_INSTRUCTIONS = "You are a Python expert programmer.\n"

# The active endpoint, model, and API key env var now come from the
# `llm:` block in config.yaml at the project root (GitHub Marketplace
# Model by default).  Edit config.yaml to switch providers; the
# alternatives below are kept for reference.
#
# OpenAI API key stored in my secrets. (NOT FREE)
#   model_base_url: "https://api.openai.com/v1"
#   model: "gpt-5.2"
#   api_key_env: "OPENAI_API_KEY"
#
# Ollama locally running server. Any string works for local Ollama. (FREE)
#   model_base_url: "http://localhost:11434/v1"
#   model: "llama2"  # Meta Open-Source 7B size
#   model: "qwen3.5"  # https://ollama.com/library/qwen3.5
#   model: "phi"  # https://ollama.com/library/phi


def run_client() -> None:
    """Connect to LLM and send a prompt."""
    base_url = get_model_base_url()
    model = get_model()
    logger.info("Connecting to %s using model %s", base_url, model)
    client = OpenAI(
        api_key=get_api_key(),
        base_url=base_url,
    )

    prompt = "How do I check if a Python object is an instance of a class?"

    logger.debug("========== %s API CALL (BEGIN) ==========", "NEW")
    logger.debug("Sending prompt: %s", prompt)

    try:
        start = time.perf_counter()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_INSTRUCTIONS},
                {"role": "user", "content": prompt},
            ],
        )
        elapsed = time.perf_counter() - start

        logger.info("Response received successfully")
        result = response.choices[0].message.content
        logger.debug("Response text: %s", result)
        print(result)
        print(f"\n[Model: {model} | API: NEW | " f"Time: {elapsed:.2f}s]\n")
    except Exception:
        logger.exception(
            "Failed to get response from model %s via NEW API",
            model,
        )
    finally:
        logger.debug("========== %s API CALL (END) ==========", "NEW")


def main() -> None:
    """Entry point for the OpenAI client."""
    run_client()


if __name__ == "__main__":
    main()
