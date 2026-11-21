"""One call of a reader through an endpoint that speaks the common chat-completions format, such as a local model server.

The address is read from the environment variable ``MOOTCOURT_READERS_ENDPOINT`` (for example
``http://127.0.0.1:8000/v1``) and an optional key from ``MOOTCOURT_READERS_ENDPOINT_KEY``; this module never prints or
stores the key. A request holds the model, the system text, one user message and a token limit. No sampling setting is
sent, so the server applies the model's own defaults. ``MOOTCOURT_READERS_REASONING_EFFORT``, when set, is sent as
``reasoning_effort`` with every request of the process and is named in the version string of each stored reply.

The reply's text is the message content with any thinking block taken out. An error of the server, an unreadable
response and a response that holds a tool call raise ``TransportError`` and are never stored. The standard library does
the sending, and it is imported only when a call is made.
"""
from __future__ import annotations

import json
import os
import time

from mootcourt.simulators.readers.command import ToolReply, TransportError

MAX_TOKENS = 16000          # thinking counts toward it; a reply cut at the limit fails the caller's check
ENDPOINT_ENV, KEY_ENV, EFFORT_ENV = "MOOTCOURT_READERS_ENDPOINT", "MOOTCOURT_READERS_ENDPOINT_KEY", "MOOTCOURT_READERS_REASONING_EFFORT"
EMBED_BATCH = 64
_THINK_END = "</think>"


def effort() -> str | None:
    return os.environ.get(EFFORT_ENV) or None


def request_body(model: str, system: str, prompt: str) -> dict:
    """Everything one request holds."""
    body = {"model": model, "max_tokens": MAX_TOKENS,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}
    if effort():
        body["reasoning_effort"] = effort()
    return body


def version() -> str:
    return "chat-completions endpoint" + (f"; reasoning_effort={effort()}" if effort() else "; no setting sent")


def _post(path: str, body: dict, time_cap_s: float) -> dict:
    """Send one JSON body to the endpoint and return the JSON it answers with."""
    import urllib.error
    import urllib.request

    base = os.environ.get(ENDPOINT_ENV)
    if not base:
        raise TransportError(f"the local transport needs the endpoint's address in {ENDPOINT_ENV}")
    headers = {"Content-Type": "application/json"}
    if os.environ.get(KEY_ENV):
        headers["Authorization"] = "Bearer " + os.environ[KEY_ENV]
    request = urllib.request.Request(base.rstrip("/") + path, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=time_cap_s) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise TransportError(f"the endpoint answered with status {exc.code}: {exc.read().decode('utf-8', 'replace')[:300]}") from exc
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
        raise TransportError(f"the endpoint could not be reached: {type(exc).__name__}: {str(exc)[:300]}") from exc
    except ValueError as exc:
        raise TransportError(f"the endpoint's response is not JSON: {str(exc)[:200]}") from exc


def answer_text(content: str | None) -> str:
    """The reply without a thinking block: what follows the last end mark of thinking, or the whole text when there is none."""
    text = content or ""
    return text.rsplit(_THINK_END, 1)[1].strip() if _THINK_END in text else text


def call(model: str, system: str, prompt: str, schema: dict | None = None, *, time_cap_s: float = 180.0, post=None) -> ToolReply:
    """Send one request and return the reply's text with the model the server reports and the tokens it counts.

    ``schema`` is not sent: the prompt states the form of the reply and the caller checks it, as with the other transports.
    """
    started = time.monotonic()
    response = (post or _post)("/chat/completions", request_body(model, system, prompt), time_cap_s)
    try:
        message = response["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise TransportError(f"the endpoint's response holds no message: {str(response)[:200]}") from exc
    if message.get("tool_calls"):
        raise TransportError("the response holds a tool call that was not asked for")
    usage = response.get("usage") or {}
    reported = response.get("model") if isinstance(response.get("model"), str) else None
    return ToolReply(text=answer_text(message.get("content")), reported_model=reported, tool_version=version(),
                     seconds=time.monotonic() - started,
                     usage={"input_tokens": int(usage.get("prompt_tokens") or 0), "output_tokens": int(usage.get("completion_tokens") or 0)})


def embed(model: str, texts: list[str], *, time_cap_s: float = 600.0, post=None) -> list[list[float]]:
    """The embedding of each text, in order, from the endpoint's embeddings route."""
    out: list[list[float]] = []
    for start in range(0, len(texts), EMBED_BATCH):
        part = texts[start:start + EMBED_BATCH]
        response = (post or _post)("/embeddings", {"model": model, "input": part}, time_cap_s)
        try:
            rows = sorted(response["data"], key=lambda row: row["index"])
            vectors = [row["embedding"] for row in rows]
        except (KeyError, TypeError) as exc:
            raise TransportError(f"the endpoint's response holds no embeddings: {str(response)[:200]}") from exc
        if len(vectors) != len(part):
            raise TransportError(f"asked for {len(part)} embeddings and got {len(vectors)}")
        out.extend(vectors)
    return out
