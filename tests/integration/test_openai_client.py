"""Integration test client for the OpenAI Responses API.

Sends a simple prompt to verify end-to-end connectivity with the
OpenAI API.  Run standalone with::

    poetry run python tests/integration/test_openai_client.py**

** Ensure the LLM defined below is running locally (e.g., ollama run phi)

"""

import logging
import time

from ai_utils_lib.config.config import load_config
from ai_utils_lib.config.file_load_config import configure_logging
from openai import OpenAI, OpenAIError

_PACKAGE = "math_ai_agent"

logger = logging.getLogger(__name__)

_SYSTEM_INSTRUCTIONS = "You are a Python expert programmer.\n"

# The active endpoint, model, and API key env var now come from the
# `model:` block in config.yaml at the project root (GitHub Marketplace
# Model by default).  Edit config.yaml to switch providers; the
# alternatives below are kept for reference.
#
# OpenAI API key stored in my secrets. (NOT FREE)
#   base_url: "https://api.openai.com/v1"
#   name: "gpt-5.2"
#   api_key_env: "OPENAI_API_KEY"
#
# Ollama locally running server. Any string works for local Ollama. (FREE)
#   base_url: "http://localhost:11434/v1"
#   name: "llama2"  # Meta Open-Source 7B size
#   name: "qwen3.5"  # https://ollama.com/library/qwen3.5
#   name: "phi"  # https://ollama.com/library/phi


def run_client() -> None:
    """Connect to LLM and send a prompt."""
    config = load_config(_PACKAGE).model
    base_url = str(config.base_url)
    model = config.name
    logger.info("Connecting to %s using model %s", base_url, model)
    prompt = "How do I check if a Python object is an instance of a class?"
    with OpenAI(
        api_key=config.api_key,
        base_url=base_url,
    ) as client:
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
        except OpenAIError:
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
    configure_logging(load_config(_PACKAGE))
    main()
