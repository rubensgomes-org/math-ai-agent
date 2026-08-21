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

"""Configuration helpers — loads config.yaml and configures logging."""

import logging
import logging.config
import os
from importlib.resources import files
from pathlib import Path

import yaml


def _resolve_config_path() -> Path:
    """Return the config.yaml path.

    Resolution order:

    1. The ``CALCULATOR_MCP_CONFIG`` environment variable, when set.
    2. A ``config.yaml`` in the current working directory — this is
       the copy at the project root, and is what you edit when
       running from a clone.
    3. The ``config.yaml`` bundled inside the
       ``math_ai_agent.config`` package, which ships in the wheel and
       serves as the default for installed copies.

    Returns:
        The resolved path to config.yaml.
    """
    env_path = os.environ.get("CALCULATOR_MCP_CONFIG")
    if env_path:
        return Path(env_path)
    cwd_path = Path.cwd() / "config.yaml"
    if cwd_path.is_file():
        return cwd_path
    return Path(str(files("math_ai_agent.config").joinpath("config.yaml")))


_CONFIG_PATH = _resolve_config_path()


def _load_config() -> dict:
    """Load and return the full config.yaml as a dict.

    Returns:
        The parsed YAML configuration.
    """
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def configure_logging() -> None:
    """Apply the logging configuration from config.yaml."""
    config = _load_config()
    logging.config.dictConfig(config["logging"])


configure_logging()

logger = logging.getLogger(__name__)
logger.debug("Config path resolved to %s", _CONFIG_PATH)


def get_timeout() -> int:
    """Return the HTTP client timeout (seconds) from config.yaml.

    Returns:
        The timeout in seconds.
    """
    config = _load_config()
    timeout: int = config["server"]["calculator_mcp"]["timeout"]
    logger.info("HTTP client timeout: %s seconds", timeout)
    return timeout


def is_oauth() -> bool:
    """Return whether OAuth is enabled from config.yaml.

    Returns:
        True if the calculator_mcp is_oauth setting is true, False otherwise.
    """
    config = _load_config()
    oauth: bool = config["server"]["calculator_mcp"].get("is_oauth", False)
    logger.info("OAuth enabled: %s", oauth)
    return oauth


def get_url() -> str:
    """Return the calculator MCP server URL from config.yaml.

    Returns:
        The MCP server URL string.
    """
    config = _load_config()
    url: str = config["server"]["calculator_mcp"]["url"]
    logger.info("MCP server URL: %s", url)
    return url


def get_token_dir() -> str:
    """Return the OAuth token directory from config.yaml.

    Returns:
        The token directory path string.
    """
    config = _load_config()
    token_dir: str = config["server"]["calculator_mcp"]["token_dir"]
    logger.info("OAuth token directory: %s", token_dir)
    return token_dir


def get_callback_port() -> int:
    """Return the OAuth callback server port from config.yaml.

    Returns:
        The callback port number.
    """
    config = _load_config()
    port: int = config["server"]["calculator_mcp"]["callback_port"]
    logger.info("OAuth callback port: %s", port)
    return port


def get_model_base_url() -> str:
    """Return the LLM model base URL from config.yaml.

    Returns:
        The model base URL string.
    """
    config = _load_config()
    url: str = config["llm"]["model_base_url"]
    logger.info("LLM model base URL: %s", url)
    return url


def get_model() -> str:
    """Return the LLM model identifier from config.yaml.

    Returns:
        The model identifier string.
    """
    config = _load_config()
    model: str = config["llm"]["model"]
    logger.info("LLM model: %s", model)
    return model


def get_api_style() -> str:
    """Return the OpenAI API style from config.yaml.

    The ``llm.api_style`` setting selects which OpenAI API the LLM
    client uses: ``"responses"`` for the Responses API
    (``POST /v1/responses``) or ``"chat"`` for the legacy Chat
    Completions API (``POST /v1/chat/completions``).  Defaults to
    ``"chat"`` when the setting is absent.

    Returns:
        Either ``"responses"`` or ``"chat"``.

    Raises:
        ValueError: If the configured style is not recognised.
    """
    config = _load_config()
    style: str = config["llm"].get("api_style", "chat")
    if style not in ("chat", "responses"):
        error = f"Unknown llm.api_style: {style}"
        logger.error(error)
        raise ValueError(error)
    logger.info("LLM API style: %s", style)
    return style


def get_api_key() -> str:
    """Return the LLM API key from the environment.

    The config.yaml ``llm.api_key_env`` setting names the environment
    variable holding the key; the key value itself is never stored in
    config.yaml.  Only the variable name is logged, never the key.

    Returns:
        The API key read from the configured environment variable.

    Raises:
        RuntimeError: If the environment variable is not set or empty.
    """
    config = _load_config()
    env_name: str = config["llm"]["api_key_env"]
    logger.info("LLM API key environment variable: %s", env_name)
    api_key = os.environ.get(env_name)
    if not api_key:
        error = f"{env_name} environment variable is not set."
        logger.error(error)
        raise RuntimeError(error)
    return api_key
