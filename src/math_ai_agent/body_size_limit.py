"""ASGI middleware rejecting oversized request bodies."""

import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send

_TOO_LARGE_STATUS = 413
_TOO_LARGE_BODY = json.dumps(
    {"detail": "The request body is too large."}
).encode()


class BodySizeLimitMiddleware:
    """Return 413 for HTTP bodies larger than ``max_bytes``.

    The body is read, up to the limit, before the app runs and then
    replayed to it, so streamed bodies without ``Content-Length`` are
    limited too.
    """

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self._app = app
        self._max_bytes = max_bytes

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        if _declared_length(scope) > self._max_bytes:
            await _send_too_large(send)
            return
        first_message = await self._read_body(receive)
        if first_message is None:
            await _send_too_large(send)
            return
        await self._app(scope, _replay(first_message, receive), send)

    async def _read_body(self, receive: Receive) -> Message | None:
        """Return the whole body as one message, or None if too large."""
        body = b""
        while True:
            message = await receive()
            if message["type"] != "http.request":
                return message
            body += message.get("body", b"")
            if len(body) > self._max_bytes:
                return None
            if not message.get("more_body", False):
                return {"type": "http.request", "body": body}


def _declared_length(scope: Scope) -> int:
    for name, value in scope["headers"]:
        if name == b"content-length":
            return int(value) if value.isdigit() else 0
    return 0


def _replay(first_message: Message, receive: Receive) -> Receive:
    """Return ``first_message`` once, then defer to ``receive``."""
    replayed = False

    async def _receive() -> Message:
        nonlocal replayed
        if replayed:
            return await receive()
        replayed = True
        return first_message

    return _receive


async def _send_too_large(send: Send) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": _TOO_LARGE_STATUS,
            "headers": [(b"content-type", b"application/json")],
        }
    )
    await send({"type": "http.response.body", "body": _TOO_LARGE_BODY})
