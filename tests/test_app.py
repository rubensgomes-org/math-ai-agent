"""Unit tests for :mod:`math_ai_agent.app`.

``ASGITransport`` does not run the app lifespan, so these tests never
connect to the MCP server or start OAuth.
"""

import asyncio
import signal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import uvicorn
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Request, Response
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    RateLimitError,
)

from math_ai_agent import app as app_module
from math_ai_agent.app import create_app
from math_ai_agent.agent import (
    AgentBusyError,
    AgentError,
    ContentFilterError,
    LLMRateLimitedError,
    LLMRequestFailedError,
    MaxTurnsExceededError,
    TokenLimitError,
    UnexpectedResponseError,
)
from math_ai_agent.agent import AgentAnswer
from math_ai_agent.schemas import MAX_PROMPT_CHARS
from math_ai_agent.rate_limit import SlidingWindowRateLimiter


@pytest.fixture()
def mock_agent():
    """A mock ``Agent`` whose ``run`` is awaitable."""
    agent = MagicMock()
    agent.run = AsyncMock()
    return agent


@pytest.fixture()
def app(mock_agent):
    """The web app serving prompts with ``mock_agent``."""
    return create_app(mock_agent)


def test_create_app_stores_agent(mock_agent):
    assert create_app(mock_agent).state.agent is mock_agent


async def test_root_returns_html(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Math AI Agent" in response.text


async def test_root_contains_form_elements(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.get("/")
        assert "textarea-question-id" in response.text
        assert "button-submit-id" in response.text
        assert "textarea-response-id" in response.text
        assert "div-error-id" in response.text


async def test_health_returns_ok(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.text == "OK"


async def test_prompt_returns_answer_and_reasoning(app, mock_agent):
    mock_agent.run.return_value = AgentAnswer(
        answer="The answer is 4.", reasoning="Add 2 and 2."
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post("/prompt/", json={"text": "What is 2+2?"})
    assert response.status_code == 200
    assert response.json() == {
        "answer": "The answer is 4.",
        "reasoning": "Add 2 and 2.",
    }
    mock_agent.run.assert_awaited_once_with("What is 2+2?")


async def test_prompt_omits_reasoning_when_not_requested(app, mock_agent):
    mock_agent.run.return_value = AgentAnswer(answer="8", reasoning="Add.")
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post(
            "/prompt/", json={"text": "4+4?", "display_reasoning": False}
        )
    assert response.status_code == 200
    assert response.json() == {"answer": "8", "reasoning": None}


async def test_prompt_strips_whitespace(app, mock_agent):
    mock_agent.run.return_value = AgentAnswer(answer="hello response")
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post("/prompt/", json={"text": "  hello  "})
    assert response.status_code == 200
    mock_agent.run.assert_awaited_once_with("hello")


async def test_prompt_rejects_oversized_body(app, mock_agent):
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post(
            "/prompt", content=b"x" * (app_module._MAX_BODY_BYTES + 1)
        )
    assert response.status_code == 413
    mock_agent.run.assert_not_awaited()


# Expected HTTP status and Retry-After header for each AgentError.
_AGENT_ERROR_RESPONSES = [
    (AgentBusyError, 503, "5"),
    (TokenLimitError, 500, None),
    (ContentFilterError, 422, None),
    (LLMRequestFailedError, 502, None),
    (LLMRateLimitedError, 429, "10"),
    (MaxTurnsExceededError, 502, None),
    (UnexpectedResponseError, 502, None),
]


def _subclasses(cls):
    return {
        sub
        for direct in cls.__subclasses__()
        for sub in (direct, *_subclasses(direct))
    }


def test_every_agent_error_has_an_expected_response():
    assert {row[0] for row in _AGENT_ERROR_RESPONSES} == _subclasses(AgentError)


@pytest.mark.parametrize(
    ("error_class", "status_code", "retry_after"), _AGENT_ERROR_RESPONSES
)
async def test_prompt_maps_agent_error_to_http_response(
    app, mock_agent, error_class, status_code, retry_after
):
    """An AgentError returns its status, client message and Retry-After."""
    mock_agent.run.side_effect = error_class("internal detail")
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post("/prompt/", json={"text": "1+1?"})
    assert response.status_code == status_code
    assert response.json()["detail"] == error_class.client_message
    assert response.headers.get("retry-after") == retry_after
    assert "internal detail" not in response.text


_LLM_REQUEST = Request("POST", "https://llm.test/v1/responses")


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    [
        (
            InternalServerError(
                "Internal server error",
                response=Response(500, request=_LLM_REQUEST),
                body={"error": {"message": "provider secret details"}},
            ),
            502,
            app_module._LLM_FAILED,  # pylint: disable=protected-access
        ),
        (
            AuthenticationError(
                "Incorrect API key provided: sk-...abcd",
                response=Response(401, request=_LLM_REQUEST),
                body=None,
            ),
            502,
            app_module._LLM_FAILED,  # pylint: disable=protected-access
        ),
        (
            RateLimitError(
                "Error code: 429",
                response=Response(429, request=_LLM_REQUEST),
                body={"error": {"message": "You have no credits remaining."}},
            ),
            429,
            app_module._LLM_RATE_LIMITED,  # pylint: disable=protected-access
        ),
        (
            APIConnectionError(request=_LLM_REQUEST),
            502,
            app_module._LLM_UNREACHABLE,  # pylint: disable=protected-access
        ),
        (
            APITimeoutError(request=_LLM_REQUEST),
            504,
            app_module._LLM_TIMED_OUT,  # pylint: disable=protected-access
        ),
    ],
    ids=["server-error", "auth-error", "rate-limit", "connection", "timeout"],
)
async def test_prompt_maps_llm_api_error_to_safe_response(
    app, mock_agent, caplog, error, status_code, detail
):
    mock_agent.run.side_effect = error
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post("/prompt/", json={"text": "1+1?"})
    assert response.status_code == status_code
    assert response.json()["detail"] == detail
    assert f"LLM API {type(error).__name__}" in caplog.text
    assert "Traceback" not in caplog.text


async def test_prompt_logs_provider_message(app, mock_agent, caplog):
    mock_agent.run.side_effect = InternalServerError(
        "Internal server error",
        response=Response(500, request=_LLM_REQUEST),
        body={"error": {"message": "model overloaded"}},
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post("/prompt/", json={"text": "1+1?"})
    assert "model overloaded" not in response.text
    assert "model overloaded" in caplog.text


async def test_prompt_returns_500_on_unexpected_error(app, mock_agent, caplog):
    mock_agent.run.side_effect = ValueError("Non-supported finish_reason")
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post(
            "/prompt/", json={"text": "my private question"}
        )
        assert response.status_code == 500
        assert "unexpected error" in response.json()["detail"]
    assert "Non-supported finish_reason" in caplog.text
    assert "my private question" not in caplog.text


async def test_prompt_missing_question_field(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post("/prompt/", json={})
        assert response.status_code == 422


async def test_prompt_invalid_content_type(app):
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


async def test_prompt_empty_body(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post("/prompt/")
        assert response.status_code == 422


async def test_prompt_wrong_type_for_text(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post("/prompt/", json={"text": 123})
        assert response.status_code == 422


async def test_prompt_rejects_unknown_field(app, mock_agent):
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post(
            "/prompt", json={"text": "1+1?", "display_reasonng": False}
        )
    assert response.status_code == 422
    mock_agent.run.assert_not_awaited()


@pytest.mark.parametrize(
    "text",
    ["", "   ", "x" * (MAX_PROMPT_CHARS + 1)],
    ids=["empty", "blank", "too-long"],
)
async def test_prompt_rejects_invalid_text(app, mock_agent, text):
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post("/prompt/", json={"text": text})
    assert response.status_code == 422
    mock_agent.run.assert_not_awaited()


async def test_prompt_get_method_not_allowed(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.get("/prompt/")
        assert response.status_code == 405


def _async_context(target: MagicMock) -> MagicMock:
    """Make ``target`` an async context manager that yields itself."""
    target.__aenter__ = AsyncMock(return_value=target)
    target.__aexit__ = AsyncMock(return_value=None)
    return target


@pytest.fixture()
def startup_mocks():
    """Patch the MCP client, agent, and uvicorn used by ``run``."""
    calc = _async_context(MagicMock())
    agent = _async_context(MagicMock())
    with (
        patch.object(
            app_module, "CalcMCPClient", return_value=calc
        ) as calc_class,
        patch.object(app_module, "Agent", return_value=agent) as agent_class,
        patch.object(app_module.uvicorn, "Config") as config_class,
        patch.object(app_module, "_GracefulServer") as server_class,
    ):
        server_class.return_value.serve = AsyncMock()
        yield {
            "calc": calc,
            "calc_class": calc_class,
            "agent": agent,
            "agent_class": agent_class,
            "config_class": config_class,
            "server": server_class.return_value,
        }


def test_run_connects_mcp_then_serves(startup_mocks, app_config):
    calc, agent = startup_mocks["calc"], startup_mocks["agent"]

    async def serve():
        calc.__aexit__.assert_not_awaited()
        agent.__aexit__.assert_not_awaited()

    startup_mocks["server"].serve.side_effect = serve
    assert app_module.run(app_config) == 0
    startup_mocks["calc_class"].assert_called_once_with(
        app_config.mcp["calculator"]
    )
    startup_mocks["agent_class"].assert_called_once_with(calc, app_config.model)
    served_app = startup_mocks["config_class"].call_args.args[0]
    assert served_app.state.agent is agent
    assert startup_mocks["config_class"].call_args.kwargs == {
        "host": app_config.web.host,
        "port": app_config.web.port,
        "log_config": None,
    }
    startup_mocks["server"].serve.assert_awaited_once()
    agent.__aexit__.assert_awaited_once()
    calc.__aexit__.assert_awaited_once()


def test_run_returns_1_when_mcp_connection_fails(startup_mocks, app_config):
    startup_mocks["calc"].__aenter__.side_effect = ConnectionError("refused")
    with patch.object(app_module, "logger") as mock_logger:
        assert app_module.run(app_config) == 1
    startup_mocks["server"].serve.assert_not_awaited()
    mock_logger.error.assert_called_once()
    assert "exc_info" not in mock_logger.error.call_args.kwargs
    assert "ConnectionError" in mock_logger.error.call_args.args


def test_run_logs_type_of_error_without_message(startup_mocks, app_config):
    startup_mocks["calc"].__aenter__.side_effect = TimeoutError()
    with patch.object(app_module, "logger") as mock_logger:
        assert app_module.run(app_config) == 1
    assert "TimeoutError" in mock_logger.error.call_args.args


@pytest.mark.parametrize("captured", [signal.SIGINT, signal.SIGTERM])
def test_graceful_server_does_not_reraise_captured_signal(captured):
    # pylint: disable-next=protected-access
    server = app_module._GracefulServer(app_module.uvicorn.Config(FastAPI()))
    original_handler = signal.getsignal(captured)
    with server.capture_signals():
        server.handle_exit(captured, None)
    assert server.should_exit
    assert signal.getsignal(captured) is original_handler


@pytest.mark.parametrize("path", ["/prompt", "/prompt/"])
async def test_prompt_accepts_path_with_and_without_slash(
    app, mock_agent, path
):
    mock_agent.run.return_value = AgentAnswer(answer="2")
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post(path, json={"text": "1+1?"})
    assert response.status_code == 200
    assert response.json()["answer"] == "2"


async def test_prompt_rate_limits_each_client(mock_agent):
    app = create_app(mock_agent, SlidingWindowRateLimiter(1, 60))
    mock_agent.run.return_value = AgentAnswer(answer="2")
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        first = await client.post("/prompt", json={"text": "1+1?"})
        second = await client.post("/prompt", json={"text": "1+1?"})
    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers["retry-after"] == "60"
    mock_agent.run.assert_awaited_once()


async def test_prompt_times_out_with_504(app, mock_agent, monkeypatch):
    monkeypatch.setattr(app_module, "_PROMPT_TIMEOUT_SECONDS", 0.01)

    async def _slow_run(*_):
        await asyncio.sleep(1)

    mock_agent.run.side_effect = _slow_run
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post("/prompt", json={"text": "1+1?"})
    assert response.status_code == 504
    # pylint: disable-next=protected-access
    assert response.json()["detail"] == app_module._PROMPT_TIMED_OUT


async def test_prompt_forwards_provider_retry_after(app, mock_agent):
    mock_agent.run.side_effect = RateLimitError(
        "Error code: 429",
        response=Response(
            429, request=_LLM_REQUEST, headers={"retry-after": "7"}
        ),
        body=None,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.post("/prompt", json={"text": "1+1?"})
    assert response.status_code == 429
    assert response.headers["retry-after"] == "7"


def test_uvicorn_server_has_captured_signals():
    """_GracefulServer relies on this private uvicorn attribute."""
    server = uvicorn.Server(uvicorn.Config(FastAPI()))
    # pylint: disable-next=protected-access
    assert isinstance(server._captured_signals, list)
