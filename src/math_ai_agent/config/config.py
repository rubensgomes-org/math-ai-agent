# General Disclaimer
#
# **AI Generated Content**
#
# This project's source code and documentation were generated predominantly
# by an Artificial Intelligence Large Language Model (AI LLM). The project
# lead, [Rubens Gomes](https://rubensgomes.com), provided initial prompts,
# reviewed, and made refinements to the generated output. While human review
# and refinement have occurred, users should be aware that the output may
# contain inaccuracies, errors, or security vulnerabilities
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
# OTHERWISE, ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE
# USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# **No-Warranty Disclaimer**
#
# THIS SOFTWARE IS PROVIDED 'AS IS,' WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT.

"""Configuration helpers — loads config.yaml and configures logging."""

import functools
import logging
import logging.config
import os
from importlib.resources import files
from pathlib import Path
from typing import Any, Literal, Self

import yaml
from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)

DEFAULT_LLM_TIMEOUT_SECONDS = 120.0
CALCULATOR_MCP_URL_ENV = "CALCULATOR_MCP_URL"


class LLMConfig(BaseModel):
    """The ``llm`` section of config.yaml.

    ``api_key`` is read from the ``api_key_env`` environment variable at
    construction and is excluded from ``repr()`` and ``model_dump()``.
    """

    api_style: Literal["chat", "responses"] = "chat"
    model_base_url: str = Field(min_length=1)
    model: str = Field(min_length=1)
    api_key_env: str
    system_instructions: str
    timeout_seconds: float = Field(default=DEFAULT_LLM_TIMEOUT_SECONDS, gt=0)
    max_concurrent_prompts: int = Field(default=10, gt=0)
    is_stateful: bool = False
    temperature: float | None = Field(default=None, ge=0, le=2)
    api_key: str = Field(default="", exclude=True, repr=False)

    @model_validator(mode="after")
    def _load_api_key(self) -> Self:
        """Set ``api_key`` from the ``api_key_env`` environment variable.

        Raises:
            ValueError: If the environment variable is not set or empty.
        """
        logger.debug("LLM API key environment variable: %s", self.api_key_env)
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            error = f"{self.api_key_env} environment variable is not set."
            logger.error(error)
            raise ValueError(error)
        self.api_key = api_key
        return self


class CalculatorMCPConfig(BaseModel):
    """The ``server.calculator_mcp`` section of config.yaml."""

    url: str
    is_oauth: bool = False
    token_dir: str
    callback_port: int


class ServerConfig(BaseModel):
    """The ``server`` section of config.yaml."""

    calculator_mcp: CalculatorMCPConfig


class WebConfig(BaseModel):
    """The ``web`` section of config.yaml: where the app listens."""

    host: str = "127.0.0.1"
    port: int = 9090


class AppConfig(BaseModel):
    """The full config.yaml; ``logging`` is a ``dictConfig`` mapping."""

    llm: LLMConfig
    server: ServerConfig
    web: WebConfig = WebConfig()
    logging: dict[str, Any]


def _resolve_config_path() -> Path:
    """Return the config.yaml path.

    Resolution order:

    1. The ``MATHAIAGENT_CONFIG`` environment variable, when set.
    2. The ``config.yaml`` bundled inside the
       ``math_ai_agent.config`` package.

    Returns:
        The resolved path to config.yaml.
    """
    env_path = os.environ.get("MATHAIAGENT_CONFIG")
    if env_path:
        return Path(env_path)
    return Path(str(files("math_ai_agent.config").joinpath("config.yaml")))


def load_config(path: Path) -> AppConfig:
    """Parse and validate the config file at ``path``.

    Raises:
        pydantic.ValidationError: If the file does not match the models.
    """
    with open(path, encoding="utf-8") as f:
        return AppConfig.model_validate(yaml.safe_load(f))


def _apply_env_overrides(app_config: AppConfig) -> AppConfig:
    """Return ``app_config`` with environment variable overrides applied.

    A non-empty ``CALCULATOR_MCP_URL`` replaces
    ``server.calculator_mcp.url``.
    """
    mcp_url = os.environ.get(CALCULATOR_MCP_URL_ENV)
    if not mcp_url:
        return app_config
    calculator_mcp = app_config.server.calculator_mcp.model_copy(
        update={"url": mcp_url}
    )
    server = app_config.server.model_copy(
        update={"calculator_mcp": calculator_mcp}
    )
    return app_config.model_copy(update={"server": server})


@functools.cache
def get_config() -> AppConfig:
    """Return the application config, loaded once on first call."""
    return _apply_env_overrides(load_config(_resolve_config_path()))


def configure_logging() -> None:
    """Apply the logging configuration from config.yaml."""
    logging.config.dictConfig(get_config().logging)
    logger.debug("Loaded config from %s", _resolve_config_path())
