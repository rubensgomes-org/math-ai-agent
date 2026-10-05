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

"""Helpers for building and logging LLM requests."""

import json
from typing import Any

import mcp_types
from openai import omit


def function_definition(tool: mcp_types.Tool) -> dict[str, Any]:
    """Return the MCP tool's ``name``, optional ``description``, and
    ``parameters`` (its input schema)."""
    definition: dict[str, Any] = {"name": tool.name}
    if tool.description:
        definition["description"] = tool.description
    definition["parameters"] = tool.input_schema
    return definition


def omit_if_none(value: Any) -> Any:
    """Return ``omit``, which leaves the field out of the request, for
    ``None``; otherwise return ``value``."""
    return omit if value is None else value


def to_json(value: Any) -> str:
    """Format a request payload as indented JSON for logging.

    SDK objects, such as ``ChatCompletionMessage``, are converted with
    ``model_dump``; anything else that JSON cannot encode uses ``str``.
    """

    def _encode(item: Any) -> Any:
        if hasattr(item, "model_dump"):
            return item.model_dump(exclude_none=True)
        return str(item)

    return json.dumps(value, indent=2, ensure_ascii=False, default=_encode)
