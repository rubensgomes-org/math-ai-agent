"""Unit tests for :mod:`math_ai_agent.body_size_limit`."""

import pytest

from math_ai_agent.body_size_limit import BodySizeLimitMiddleware

_LIMIT = 10


class _EchoApp:
    """ASGI app recording the body it reads and replying 200."""

    def __init__(self) -> None:
        self.body: bytes | None = None
        self.called = False

    async def __call__(self, scope, receive, send):
        self.called = True
        if scope["type"] != "http":
            return
        message = await receive()
        self.body = message.get("body", b"")
        await send({"type": "http.response.start", "status": 200})
        await send({"type": "http.response.body", "body": b"ok"})


async def _call(chunks, headers=(), scope_type="http"):
    """Run the middleware; return the app and the response status."""
    app = _EchoApp()
    messages = [
        {
            "type": "http.request",
            "body": chunk,
            "more_body": i < len(chunks) - 1,
        }
        for i, chunk in enumerate(chunks)
    ]
    sent = []

    async def receive():
        return messages.pop(0) if messages else {"type": "http.disconnect"}

    async def send(message):
        sent.append(message)

    scope = {"type": scope_type, "headers": list(headers)}
    await BodySizeLimitMiddleware(app, _LIMIT)(scope, receive, send)
    status = next(
        (m["status"] for m in sent if m["type"] == "http.response.start"),
        None,
    )
    return app, status


async def test_replays_body_within_the_limit_as_one_message():
    app, status = await _call([b"12345", b"67890"])
    assert status == 200
    assert app.body == b"1234567890"


async def test_rejects_declared_length_over_the_limit_without_reading():
    app, status = await _call([b"x"], headers=[(b"content-length", b"11")])
    assert status == 413
    assert not app.called


async def test_rejects_streamed_body_over_the_limit():
    app, status = await _call([b"123456", b"78901"])
    assert status == 413
    assert not app.called


@pytest.mark.parametrize("length", [b"abc", b"5"])
async def test_reads_body_when_declared_length_is_invalid_or_small(length):
    app, status = await _call([b"12345"], headers=[(b"content-length", length)])
    assert status == 200
    assert app.body == b"12345"


async def test_passes_non_http_scopes_through():
    app, status = await _call([], scope_type="websocket")
    assert app.called
    assert status is None


async def test_passes_a_disconnect_before_the_body_to_the_app():
    app, _ = await _call([])
    assert app.called
    assert app.body == b""
