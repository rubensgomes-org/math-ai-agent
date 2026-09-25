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

"""Shared pytest fixtures."""

import pytest

from math_ai_agent.config.config import AppConfig


@pytest.fixture()
def app_config() -> AppConfig:
    """Return a minimal ``AppConfig`` with test values."""
    return AppConfig.model_validate(
        {
            "llm": {
                "api_style": "chat",
                "model_base_url": "http://localhost:11434/v1",
                "model": "test-model",
                "api_key_env": "TEST_LLM_KEY",
                "system_instructions": "Test instructions.",
            },
            "server": {
                "calculator_mcp": {
                    "url": "http://localhost:9000/mcp",
                    "is_oauth": False,
                    "token_dir": "/tmp/test-tokens",
                    "callback_port": 10000,
                }
            },
            "logging": {
                "version": 1,
                "disable_existing_loggers": False,
                "root": {"level": "WARNING"},
            },
        }
    )
