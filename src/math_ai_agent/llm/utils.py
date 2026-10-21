"""Helpers for LLM requests and logging."""

import json
from typing import Any

from openai import Omit, omit

_MAX_LOG_JSON_CHARS = 20_000


def omit_if_none[T](value: T | None) -> T | Omit:
    """Return ``omit`` for ``None``, else ``value``."""
    return omit if value is None else value


def json_for_log(value: Any) -> str:
    """Format ``value`` as indented JSON for logs only, never requests.

    Any object with ``model_dump``, such as an SDK model, is dumped;
    anything else JSON cannot encode uses ``str``.  Output longer than
    ``_MAX_LOG_JSON_CHARS`` is truncated.
    """

    def _encode(item: Any) -> Any:
        if hasattr(item, "model_dump"):
            return item.model_dump(exclude_none=True)
        return str(item)

    text = json.dumps(value, indent=2, ensure_ascii=False, default=_encode)
    if len(text) <= _MAX_LOG_JSON_CHARS:
        return text
    dropped = len(text) - _MAX_LOG_JSON_CHARS
    return f"{text[:_MAX_LOG_JSON_CHARS]}... ({dropped} characters truncated)"
