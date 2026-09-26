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

"""Unit tests for :mod:`math_ai_agent.app`."""

# TODO: refactor this unit test so that it does NOT start OAuth authentication.

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from math_ai_agent.app import Prompt, app, main


@pytest.mark.asyncio
async def test_app_is_fastapi_instance():
    assert app.title == "FastAPI"


@pytest.mark.asyncio
async def test_static_files_mount():
    routes = [route.path for route in app.routes]
    assert "/static" in routes or any("/static" in r for r in routes)


@pytest.mark.asyncio
async def test_static_files_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.get("/static/nonexistent.html")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_root_returns_html():
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Math AI Agent" in response.text


@pytest.mark.asyncio
async def test_root_contains_form_elements():
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.get("/")
        assert "textarea-question-id" in response.text
        assert "button-submit-id" in response.text
        assert "textarea-response-id" in response.text


@pytest.mark.asyncio
async def test_health_returns_ok():
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.text == "OK"


@pytest.mark.asyncio
@patch(
    "math_ai_agent.app.agent_loop",
    new_callable=AsyncMock,
    return_value="The answer is 4.",
)
async def test_prompt_returns_answer(mock_agent_loop):
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post("/prompt/", json={"text": "What is 2+2?"})
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert data["answer"] == "The answer is 4."
    mock_agent_loop.assert_awaited_once_with("What is 2+2?")


@pytest.mark.asyncio
@patch(
    "math_ai_agent.app.agent_loop",
    new_callable=AsyncMock,
    return_value="hello response",
)
async def test_prompt_strips_whitespace(mock_agent_loop):
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post("/prompt/", json={"text": "  hello  "})
        assert response.status_code == 200
        assert response.json()["answer"] == "hello response"
    mock_agent_loop.assert_awaited_once_with("hello")


@pytest.mark.asyncio
async def test_prompt_missing_question_field():
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post("/prompt/", json={})
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_prompt_invalid_content_type():
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post(
            "/prompt/",
            content="not json",
            headers={"content-type": "text/plain"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_prompt_empty_body():
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post("/prompt/")
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_prompt_wrong_type_for_question():
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post("/prompt/", json={"question": 123})
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_prompt_get_method_not_allowed():
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.get("/prompt/")
        assert response.status_code == 405


def test_math_question_model():
    q = Prompt(text="What is 5*3?")
    assert q.text == "What is 5*3?"


def test_math_question_model_requires_question():
    with pytest.raises(Exception):
        Prompt()


@patch("math_ai_agent.app.uvicorn.run")
@patch("math_ai_agent.app.get_config")
def test_main_runs_uvicorn_with_configured_host_and_port(
    mock_get_config, mock_run
):
    mock_get_config.return_value.web.host = "0.0.0.0"
    mock_get_config.return_value.web.port = 1234
    main()
    mock_run.assert_called_once_with(app, host="0.0.0.0", port=1234)
