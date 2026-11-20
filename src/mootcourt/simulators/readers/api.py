"""One call of a reader through the vendor's Messages API.

The request holds the model, the system prompt, one user message with the prompt, and a token limit. Nothing else is
sent: no tool, no sampling setting, no thinking or effort setting, no fallback model. The model therefore receives
the two texts and nothing around them. The key is read by the vendor's package from the environment variable
``ANTHROPIC_API_KEY``; this module never takes, prints or stores it.

A response is a reply whatever its stop reason: a declined request has little or no text, fails the caller's check and
is tried again like any other bad reply. An error of the API after the package's own retries, and a response that holds
a tool call, raise ``TransportError`` and are never stored.

The package is an optional extra (``readers-api``) and is imported only when a call is made.
"""
from __future__ import annotations

import functools
import time

from mootcourt.simulators.readers.command import ToolReply, TransportError

MAX_TOKENS = 16000          # thinking counts toward it; a reply cut at the limit fails the caller's check
RETRIES = 5                 # the package's own retries of a rate limit, a server error, a timeout or a dropped connection
USAGE_FIELDS = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")


def _package():
    try:
        import anthropic
    except ImportError as exc:          # pragma: no cover - depends on the install
        raise TransportError("the API transport needs the optional extra: uv sync --extra readers-api") from exc
    return anthropic


@functools.lru_cache(maxsize=1)
def make_client():
    """The one client of the process. It reads the key from the environment."""
    return _package().Anthropic()


def request_body(model: str, system: str, prompt: str) -> dict:
    """Everything one request holds."""
    return {"model": model, "system": system, "max_tokens": MAX_TOKENS, "messages": [{"role": "user", "content": prompt}]}


def _send(model: str, system: str, prompt: str, client, time_cap_s: float):
    anthropic = _package()
    client = client if client is not None else make_client()
    started = time.monotonic()
    try:
        response = client.with_options(timeout=time_cap_s, max_retries=RETRIES).messages.create(**request_body(model, system, prompt))
    except anthropic.APIStatusError as exc:
        raise TransportError(f"the API answered with status {exc.status_code}: {str(exc)[:300]}") from exc
    except anthropic.APIConnectionError as exc:          # a timeout is one of these
        raise TransportError(f"the API could not be reached: {type(exc).__name__}: {str(exc)[:300]}") from exc
    except anthropic.APIError as exc:
        raise TransportError(f"the API call failed: {type(exc).__name__}: {str(exc)[:300]}") from exc
    return response, time.monotonic() - started


def _tools(response) -> list[str]:
    return [block.type for block in response.content if block.type not in ("text", "thinking", "redacted_thinking")]


def _text(response) -> str:
    return "".join(block.text for block in response.content if block.type == "text")


def _usage(response) -> dict:
    usage = getattr(response, "usage", None)
    return {name: int(getattr(usage, name, 0) or 0) for name in USAGE_FIELDS}


def version() -> str:
    return f"anthropic-python {_package().__version__}"


def call(model: str, system: str, prompt: str, schema: dict | None = None, *, time_cap_s: float = 180.0, client=None) -> ToolReply:
    """Send one request and return the reply's text with the model the API reports and the tokens it counts.

    ``schema`` is not sent: the prompt states the form of the reply and the caller checks it, as with the other transport.
    """
    response, seconds = _send(model, system, prompt, client, time_cap_s)
    extra = _tools(response)
    if extra:
        raise TransportError(f"the response holds a tool call or another block that was not asked for: {extra}")
    reported = response.model if isinstance(response.model, str) else None
    return ToolReply(text=_text(response), reported_model=reported, tool_version=version(), seconds=seconds, usage=_usage(response))


def canary(model: str, system: str, prompt: str, *, time_cap_s: float = 180.0, client=None) -> dict:
    """One call that returns the request as sent, without the key, and what the response holds.

    A tool call in the response does not raise here: the caller reports it.
    """
    response, _ = _send(model, system, prompt, client, time_cap_s)
    reported = response.model if isinstance(response.model, str) else None
    return {"request": request_body(model, system, prompt), "tools": _tools(response), "servers": [],
            "reply_text": _text(response), "reported_model": reported, "tool_version": version(),
            "stop_reason": response.stop_reason, "usage": _usage(response), "transport": "api"}
