"""The transport through the vendor's API: what one request holds, what counts as a reply, and what is never stored.

No test here reaches the network. A stand-in client records the request and returns a response of the documented shape.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

anthropic = pytest.importorskip("anthropic")

from mootcourt.simulators.readers import api, measures  # noqa: E402
from mootcourt.simulators.readers.command import TransportError  # noqa: E402
from mootcourt.simulators.readers.panel import direction_frame  # noqa: E402
from mootcourt.simulators.readers.prompts import clicks_schema, parse_clicks  # noqa: E402
from mootcourt.simulators.readers.transcripts import Transcripts, ask, request_hash  # noqa: E402

MODEL = "claude-opus-5-5"
GOOD = '{"clicks": [0.1, 0.2]}'


def block(kind, **fields):
    return SimpleNamespace(type=kind, **fields)


class StandIn:
    """A client that answers from a list and keeps every request it was sent."""

    def __init__(self, *responses):
        self.responses, self.requests, self.options = list(responses), [], []
        self.messages = SimpleNamespace(create=self._create)

    def with_options(self, **options):
        self.options.append(options)
        return self

    def _create(self, **request):
        self.requests.append(request)
        answer = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        if isinstance(answer, BaseException):
            raise answer
        return answer


def response(text=GOOD, model=MODEL, stop="end_turn", content=None):
    content = content if content is not None else [block("thinking", thinking=""), block("text", text=text)]
    return SimpleNamespace(content=content, model=model, stop_reason=stop,
                           usage=SimpleNamespace(input_tokens=120, output_tokens=45, cache_read_input_tokens=0,
                                                 cache_creation_input_tokens=0))


def test_a_request_holds_the_model_the_system_prompt_one_user_message_and_a_token_limit_and_nothing_else():
    client = StandIn(response())
    reply = api.call(MODEL, "You are a reader.", "Rate these.", clicks_schema(2), client=client, time_cap_s=30.0)
    assert client.requests == [{"model": MODEL, "system": "You are a reader.", "max_tokens": 16000,
                                "messages": [{"role": "user", "content": "Rate these."}]}]
    assert client.options == [{"timeout": 30.0, "max_retries": api.RETRIES}]
    assert reply.text == GOOD and reply.reported_model == MODEL
    assert reply.usage == {"input_tokens": 120, "output_tokens": 45, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
    assert reply.tool_version == f"anthropic-python {anthropic.__version__}"


def test_text_blocks_are_joined_and_thinking_is_left_out():
    client = StandIn(response(content=[block("thinking", thinking="private"), block("text", text='{"clicks": '),
                                       block("text", text="[0.1, 0.2]}")]))
    assert api.call(MODEL, "s", "p", client=client).text == GOOD


def test_a_declined_request_is_a_reply_with_whatever_text_it_has():
    client = StandIn(response(content=[], stop="refusal"))
    assert api.call(MODEL, "s", "p", client=client).text == ""


def test_a_tool_call_in_the_response_is_a_transport_failure():
    client = StandIn(response(content=[block("tool_use", name="x", input={})]))
    with pytest.raises(TransportError, match="tool"):
        api.call(MODEL, "s", "p", client=client)


@pytest.mark.parametrize("error", [
    anthropic.APIConnectionError(request=None),
    anthropic.APITimeoutError(request=None),
])
def test_an_error_of_the_api_is_a_transport_failure(error):
    with pytest.raises(TransportError, match="API"):
        api.call(MODEL, "s", "p", client=StandIn(error))


def test_ask_through_the_api_stores_usage_under_the_same_request_hash_as_the_tool(tmp_path, monkeypatch):
    client = StandIn(response())
    monkeypatch.setattr(api, "make_client", lambda: client)
    record = ask(Transcripts(tmp_path), MODEL, "plain", "s", "p", clicks_schema(2), lambda text: parse_clicks(text, 2),
                 allow_model_calls=True, transport="api")
    assert record["status"] == "ok" and record["usage"]["output_tokens"] == 45
    assert record["request_hash"] == request_hash(MODEL, "plain", "s", "p", clicks_schema(2))
    assert record["tool_version"].startswith("anthropic-python ")
    assert len(client.requests) == 1
    again = ask(Transcripts(tmp_path), MODEL, "plain", "s", "p", clicks_schema(2), lambda text: parse_clicks(text, 2),
                allow_model_calls=False, transport="api")
    assert again["reply_text"] == GOOD and len(client.requests) == 1          # a stored reply is never asked for again


def test_a_reply_from_another_model_is_not_stored(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "make_client", lambda: StandIn(response(model="claude-sonnet-5-5")))
    with pytest.raises(TransportError, match="another model"):
        ask(Transcripts(tmp_path), MODEL, "plain", "s", "p", clicks_schema(2), lambda text: parse_clicks(text, 2),
            allow_model_calls=True, transport="api")
    assert Transcripts(tmp_path).records(MODEL, "plain") == []


def test_three_declined_requests_are_stored_as_a_refusal(tmp_path, monkeypatch):
    client = StandIn(response(content=[], stop="refusal"))
    monkeypatch.setattr(api, "make_client", lambda: client)
    record = ask(Transcripts(tmp_path), MODEL, "plain", "s", "p", clicks_schema(2), lambda text: parse_clicks(text, 2),
                 allow_model_calls=True, transport="api")
    assert record["status"] == "refusal" and record["attempts"] == 3 and len(client.requests) == 3


def test_the_canary_keeps_the_request_and_no_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-not-a-real-key")
    record = api.canary(MODEL, "s", "p", client=StandIn(response()))
    assert record["request"] == {"model": MODEL, "system": "s", "max_tokens": 16000, "messages": [{"role": "user", "content": "p"}]}
    assert record["tools"] == [] and record["reported_model"] == MODEL and record["stop_reason"] == "end_turn"
    assert "sk-ant-not-a-real-key" not in json.dumps(record)


def test_the_transport_report_compares_the_plain_panels_of_two_runs():
    n = 120
    r = np.random.default_rng(3)
    contrasts = pd.DataFrame({"row_id": [f"r{i}" for i in range(n)], "test_id": [f"t{i // 2}" for i in range(n)],
                              "unit_id": [f"u{i // 2}" for i in range(n)], "y": r.choice([-0.01, 0.01], n)})
    feeds = pd.DataFrame({"unit_id": [f"u{i}" for i in range(n // 2)], "block_id": [f"b{i // 6}" for i in range(n // 2)]})
    tool = np.sign(contrasts.y.to_numpy()) * 0.1                      # right everywhere
    other = tool.copy()
    other[:30] *= -1                                                  # the second run is wrong on thirty contrasts
    other[30] = 0.0                                                   # and tied on one
    report = measures.transport_report(contrasts, feeds, direction_frame(contrasts, tool), direction_frame(contrasts, other))
    plain = report["plain"]
    assert (plain["n"], plain["left_out"]) == (n - 1, 1)
    assert plain["agree_share"] == pytest.approx(89 / 119)
    difference = plain["accuracy_api_minus_tool"]
    assert difference["estimate"] == pytest.approx((-30 - 0.5) / n)
    assert difference["hi"] < 0 and "verdict" not in difference and "adjusted_lo" not in difference
    assert plain["accuracy_tool"] == pytest.approx(1.0) and plain["accuracy_api"] == pytest.approx((89 + 0.5) / n)
