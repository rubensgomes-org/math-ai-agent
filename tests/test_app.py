"""Unit tests for :mod:`math_ai_agent.app`.

``ASGITransport`` does not run the app lifespan, so these tests never
connect to the MCP server or start OAuth.
"""

import signal
from importlib.metadata import version
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient, Request, Response
from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)

from math_ai_agent import app as app_module
from math_ai_agent.app import Payload, app
from math_ai_agent.cli import main
from math_ai_agent.llm import (
    AgentBusyError,
    ContentFilterError,
    LLMRequestFailedError,
    TokenLimitError,
)


@pytest.fixture()
def mock_agent():
    """Install a mock ``Agent`` on the app state."""
    agent = MagicMock()
    agent.run = AsyncMock()
    app.state.agent = agent
    yield agent
    del app.state.agent


@pytest.mark.asyncio
async def test_app_is_fastapi_instance():
    assert app.title == "FastAPI"


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
        assert "div-error-id" in response.text


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
async def test_prompt_returns_answer(mock_agent):
    mock_agent.run.return_value = "The answer is 4."
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post("/prompt/", json={"text": "What is 2+2?"})
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert data["answer"] == "The answer is 4."
    mock_agent.run.assert_awaited_once_with("What is 2+2?", True)


@pytest.mark.asyncio
async def test_prompt_passes_display_reasoning(mock_agent):
    mock_agent.run.return_value = "8"
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post(
            "/prompt/", json={"text": "4+4?", "display_reasoning": False}
        )
        assert response.status_code == 200
    mock_agent.run.assert_awaited_once_with("4+4?", False)


@pytest.mark.asyncio
async def test_prompt_strips_whitespace(mock_agent):
    mock_agent.run.return_value = "hello response"
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post("/prompt/", json={"text": "  hello  "})
        assert response.status_code == 200
        assert response.json()["answer"] == "hello response"
    mock_agent.run.assert_awaited_once_with("hello", True)


@pytest.mark.asyncio
async def test_prompt_returns_503_when_agent_busy(mock_agent):
    mock_agent.run.side_effect = AgentBusyError("Too many prompts")
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post("/prompt/", json={"text": "1+1?"})
        assert response.status_code == 503
        assert "busy" in response.json()["detail"]


@pytest.mark.asyncio
async def test_prompt_returns_422_when_content_filtered(mock_agent):
    mock_agent.run.side_effect = ContentFilterError("blocked")
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post("/prompt/", json={"text": "1+1?"})
        assert response.status_code == 422
        assert "safety filter" in response.json()["detail"]


@pytest.mark.asyncio
async def test_prompt_returns_502_when_token_limit_reached(mock_agent):
    mock_agent.run.side_effect = TokenLimitError("Token limit reached.")
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post("/prompt/", json={"text": "1+1?"})
        assert response.status_code == 502
        assert "token limit" in response.json()["detail"]


@pytest.mark.asyncio
async def test_prompt_returns_502_when_llm_request_fails(mock_agent):
    mock_agent.run.side_effect = LLMRequestFailedError("failed", "server_error")
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post("/prompt/", json={"text": "1+1?"})
        assert response.status_code == 502
        assert "request failed" in response.json()["detail"]


_LLM_REQUEST = Request("POST", "https://llm.test/v1/responses")


@pytest.mark.asyncio
async def test_prompt_returns_llm_status_when_llm_server_fails(
    mock_agent, caplog
):
    error = InternalServerError(
        "Internal server error",
        response=Response(500, request=_LLM_REQUEST),
        body=None,
    )
    mock_agent.run.side_effect = error
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post("/prompt/", json={"text": "1+1?"})
        assert response.status_code == 500
        assert response.json()["detail"] == (
            f"LLM API server error: {error.message}"
        )
    assert "LLM API server error" in caplog.text
    assert "Traceback" not in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        APIConnectionError(request=_LLM_REQUEST),
        APITimeoutError(request=_LLM_REQUEST),
    ],
)
async def test_prompt_returns_502_when_llm_connection_fails(
    mock_agent, caplog, error
):
    mock_agent.run.side_effect = error
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post("/prompt/", json={"text": "1+1?"})
        assert response.status_code == 502
        assert response.json()["detail"] == (
            f"LLM API server network connection error: {error.message}"
        )
    assert "LLM API server network connection error" in caplog.text
    assert "Traceback" not in caplog.text


@pytest.mark.asyncio
async def test_prompt_returns_provider_message_when_llm_rejects(mock_agent):
    provider_message = "You have no credits remaining."
    mock_agent.run.side_effect = RateLimitError(
        "Error code: 429",
        response=Response(429, request=_LLM_REQUEST),
        body={"error": {"message": provider_message}},
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post("/prompt/", json={"text": "1+1?"})
        assert response.status_code == 429
        assert response.json()["detail"] == (
            f"LLM API server error: {provider_message}"
        )


@pytest.mark.asyncio
async def test_prompt_returns_500_on_unexpected_error(mock_agent, caplog):
    mock_agent.run.side_effect = ValueError("Non-supported finish_reason")
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post("/prompt/", json={"text": "1+1?"})
        assert response.status_code == 500
        assert "unexpected error" in response.json()["detail"]
    assert "Non-supported finish_reason" in caplog.text


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
    q = Payload(text="What is 5*3?")
    assert q.text == "What is 5*3?"
    assert q.display_reasoning is True


def test_math_question_model_requires_question():
    with pytest.raises(Exception):
        Payload()


def _async_context(target: MagicMock) -> MagicMock:
    """Make ``target`` an async context manager that yields itself."""
    target.__aenter__ = AsyncMock(return_value=target)
    target.__aexit__ = AsyncMock(return_value=None)
    return target


@pytest.fixture()
def startup_mocks():
    """Patch the MCP client, agent, config, and uvicorn used by ``run``."""
    calc = _async_context(MagicMock())
    agent = _async_context(MagicMock())
    with (
        patch.object(app_module, "CalcMCPClient", return_value=calc),
        patch.object(app_module, "Agent", return_value=agent) as agent_class,
        patch.object(app_module, "get_config") as get_config,
        patch.object(app_module.uvicorn, "Config") as config_class,
        patch.object(app_module, "_GracefulServer") as server_class,
    ):
        get_config.return_value.web.host = "0.0.0.0"
        get_config.return_value.web.port = 1234
        server_class.return_value.serve = AsyncMock()
        yield {
            "calc": calc,
            "agent": agent,
            "agent_class": agent_class,
            "config_class": config_class,
            "server": server_class.return_value,
        }


def test_main_connects_mcp_then_serves(startup_mocks):
    calc, agent = startup_mocks["calc"], startup_mocks["agent"]

    async def serve():
        assert app.state.agent is agent
        calc.__aexit__.assert_not_awaited()
        agent.__aexit__.assert_not_awaited()

    startup_mocks["server"].serve.side_effect = serve
    assert main([]) == 0
    startup_mocks["agent_class"].assert_called_once_with(calc)
    startup_mocks["config_class"].assert_called_once_with(
        app, host="0.0.0.0", port=1234, log_config=None
    )
    startup_mocks["server"].serve.assert_awaited_once()
    agent.__aexit__.assert_awaited_once()
    calc.__aexit__.assert_awaited_once()


def test_main_returns_1_when_mcp_connection_fails(startup_mocks):
    startup_mocks["calc"].__aenter__.side_effect = ConnectionError("refused")
    with patch.object(app_module, "logger") as mock_logger:
        assert main([]) == 1
    startup_mocks["server"].serve.assert_not_awaited()
    mock_logger.error.assert_called_once()
    assert "exc_info" not in mock_logger.error.call_args.kwargs


@pytest.mark.parametrize("captured", [signal.SIGINT, signal.SIGTERM])
def test_graceful_server_does_not_reraise_captured_signal(captured):
    # pylint: disable-next=protected-access
    server = app_module._GracefulServer(app_module.uvicorn.Config(app))
    original_handler = signal.getsignal(captured)
    with server.capture_signals():
        server.handle_exit(captured, None)
    assert server.should_exit
    assert signal.getsignal(captured) is original_handler


@patch("math_ai_agent.app.run")
def test_main_version_prints_version_and_exits(mock_run, capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    package_version = version("math-ai-agent")
    assert capsys.readouterr().out.strip() == (
        f"math-ai-agent {package_version}"
    )
    mock_run.assert_not_called()
