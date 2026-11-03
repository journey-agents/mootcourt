"""HTTP adapter: POST the request JSON to a URL and read the result JSON.

Loopback only by default. A host that is not loopback needs ``allow_remote=True`` (``--allow-remote`` on the command
line). The exchange uses ``http.client`` directly: no proxy variable (``HTTP_PROXY`` and its relatives) is ever read, so
nothing can route the request to another host, and a redirect is never followed, so a loopback URL cannot send the request
elsewhere. An https URL is verified by default (the standard library's default context: certificate chain and host name). The
time cap is a wall clock for the whole exchange (connection, headers and body): the exchange runs in a worker thread, and
when the cap is reached the caller gets a timeout at once and the connection is closed, so a server that sends one byte at
a time cannot stretch it. A reply larger than one megabyte is refused.

One limit: the worker is a thread and cannot be interrupted, so what it does before a socket exists is not cut short at the
cap. That is name resolution for a host that is not a literal address (``allow_remote`` only; a loopback URL names a
literal address or ``localhost``). The TCP connect and the TLS handshake each carry the cap as their own timeout (the
handshake as one deadline, whatever the server drips), so a stalled handshake ends the worker by itself within one more
cap after the caller has already received its timeout; the caller is never held. The worker is a daemon thread and holds
no state the next call reads.

A decline is the agent replying ``null``. Any other None result is a failure: ``last_failure`` holds its kind
(transport, timeout, invalid) and ``last_note`` the reason; the runner records it and does not cache it.
"""
from __future__ import annotations

import http.client
import ipaddress
import json
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from mootcourt.simulators.base import MAX_OUTPUT_BYTES, SimulationRequest, SimulationResult, SimulatorError, SimulatorInfo


def is_loopback_host(host: str | None) -> bool:
    """True for ``localhost`` and literal loopback addresses; a name is never resolved."""
    if not host:
        return False
    if host.lower() in ("localhost", "localhost.localdomain"):
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return False


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class HttpSimulator:
    """Adapter for an agent behind an HTTP endpoint that accepts a JSON POST."""

    def __init__(self, url: str, info: SimulatorInfo, time_cap_s: float = 30.0, allow_remote: bool = False):
        parts = urllib.parse.urlsplit(url)
        if parts.scheme not in ("http", "https"):
            raise SimulatorError("the url must start with http:// or https://")
        try:
            _ = parts.port                               # the port is parsed on first access; a bad one raises ValueError
        except ValueError:
            raise SimulatorError("the url has an invalid port") from None
        if not allow_remote and not is_loopback_host(parts.hostname):
            raise SimulatorError(f"{parts.hostname} is not a loopback host; pass --allow-remote to send requests to it")
        if time_cap_s <= 0:
            raise SimulatorError("time_cap_s must be positive")
        self.url, self.info, self.time_cap_s = url, info, float(time_cap_s)
        self.last_note = ""
        self.last_failure: str | None = None

    def describe(self) -> SimulatorInfo:
        return self.info

    def _fail(self, kind: str, note: str):
        self.last_failure, self.last_note = kind, note
        return None

    def _exchange(self, body: bytes, cap: float, deadline: float, box: dict) -> None:
        """Worker: open the connection, send the request and read the reply under the deadline; the outcome goes into ``box``.

        The connection object is stored before anything is sent, so the caller can shut its socket down when the cap is reached,
        whatever the server is doing (sending the status line or a header one byte at a time included).
        """
        conn = None
        try:
            parts = urllib.parse.urlsplit(self.url)
            cls = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
            conn = cls(parts.hostname, parts.port, timeout=cap)       # inside the guard: any construction error reaches box["exc"]
            box["conn"] = conn
            target = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
            conn.request("POST", target, body=body, headers={"Content-Type": "application/json"})
            if box.get("aborted"):
                return
            resp = conn.getresponse()
            if resp.status >= 300:                       # a redirect is not followed, and an error status is a failed request
                raise urllib.error.HTTPError(self.url, resp.status, resp.reason, resp.headers, None)
            box["raw"] = self._read(resp, deadline)
        except BaseException as exc:  # noqa: BLE001  (handed to the caller, which classifies it)
            box["exc"] = exc
        finally:
            if conn is not None:
                conn.close()

    def _read(self, resp, deadline: float) -> bytes | None:
        """Read the reply in chunks; None when it is too large. The caller's join enforces the wall clock."""
        data = bytearray()
        while True:
            if time.monotonic() > deadline:
                raise TimeoutError("time cap reached while reading the reply")
            chunk = resp.read(65536)
            if not chunk:
                return bytes(data)
            data += chunk
            if len(data) > MAX_OUTPUT_BYTES:
                return None

    @staticmethod
    def _abort(box: dict) -> None:
        """Shut down the connection of a worker that overran the cap, best effort; the worker then ends on its own."""
        box["aborted"] = True
        conn = box.get("conn")
        try:
            sock = getattr(conn, "sock", None)
            if sock is not None:
                sock.shutdown(socket.SHUT_RDWR)
        except (AttributeError, OSError):
            pass
        try:
            if conn is not None:
                conn.close()
        except OSError:
            pass

    def simulate(self, request: SimulationRequest) -> SimulationResult | None:
        self.last_note, self.last_failure = "", None
        cap = min(self.time_cap_s, float(request.budget.max_seconds))
        body = json.dumps(request.to_wire(), sort_keys=True).encode("utf-8")
        t0 = time.perf_counter()
        box: dict = {}
        worker = threading.Thread(target=self._exchange, args=(body, cap, time.monotonic() + cap, box), daemon=True)
        worker.start()
        worker.join(cap)
        if worker.is_alive():
            self._abort(box)
            return self._fail("timeout", f"time cap of {cap:g} s reached")
        exc = box.get("exc")
        if exc is not None:
            if isinstance(exc, (TimeoutError, socket.timeout)):
                return self._fail("timeout", f"time cap of {cap:g} s reached")
            if isinstance(exc, (urllib.error.URLError, OSError, http.client.HTTPException)):
                reason = getattr(exc, "reason", exc)
                if isinstance(reason, (TimeoutError, socket.timeout)):
                    return self._fail("timeout", f"time cap of {cap:g} s reached")
                return self._fail("transport", f"request failed: {exc}")
            raise exc
        raw = box.get("raw")
        latency = time.perf_counter() - t0
        if raw is None:
            return self._fail("invalid", f"invalid output: the reply is too large (more than {MAX_OUTPUT_BYTES} bytes)")
        try:
            data = json.loads(raw.decode("utf-8"))
            if data is None:
                self.last_note = "the agent declined"
                return None
            return SimulationResult.from_dict(data, provider_id=self.info.provider_id, version=self.info.version, latency_s=latency)
        except (ValueError, SimulatorError, TypeError, AttributeError, KeyError, OverflowError) as exc:
            return self._fail("invalid", f"invalid output: {exc}")
