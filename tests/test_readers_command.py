"""The wrapper around the command line tool and the transcript store. Every test runs a stand-in; none starts a model."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from mootcourt.simulators.readers.command import TransportError, build_command, call
from mootcourt.simulators.readers.prompts import clicks_schema, parse_clicks
from mootcourt.simulators.readers.transcripts import ModelCallsNotAllowed, Transcripts, ask, request_hash

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("fake_reader_tool", ROOT / "tests" / "fixtures" / "fake_reader_tool.py")
fake_reader_tool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fake_reader_tool)


@pytest.fixture
def fake(tmp_path):
    return lambda **options: fake_reader_tool.make_fake(tmp_path / "fakes", **options)


def two(text):
    return parse_clicks(text, 2)


def test_command_turns_tools_servers_settings_and_sessions_off():
    c = build_command("claude-opus-5-5", "S", {"type": "object"})
    assert c[:2] == ["claude", "-p"] and c[c.index("--model") + 1] == "claude-opus-5-5"
    assert c[c.index("--tools") + 1] == "" and "--strict-mcp-config" in c and "--no-session-persistence" in c
    assert c[c.index("--setting-sources") + 1] == "" and c[c.index("--system-prompt") + 1] == "S"
    assert "--bare" not in c and "--append-system-prompt" not in c
    assert json.loads(c[c.index("--mcp-config") + 1]) == {"mcpServers": {}} and "--disable-slash-commands" in c
    assert c[c.index("--output-format") + 1] == "json" and json.loads(c[c.index("--json-schema") + 1]) == {"type": "object"}


def test_child_runs_in_an_empty_directory_outside_the_repository(fake):
    r = call("m", "S", "P", clicks_schema(2), program=fake(echo_cwd=True))
    seen = json.loads(r.text)
    cwd = Path(seen["cwd"])
    assert seen["listing"] == [] and ROOT not in cwd.parents and cwd != ROOT
    assert not cwd.exists()                                    # removed after the call


def test_credentials_in_the_environment_do_not_reach_the_child(fake, monkeypatch):
    monkeypatch.setenv("SOME_API_KEY", "secret")
    r = call("m", "S", "P", clicks_schema(2), program=fake(echo_env=True))
    assert "SOME_API_KEY" not in json.loads(r.text)["env"]


def test_the_reply_carries_what_the_tool_reports(fake):
    r = call("some-model", "S", "P", clicks_schema(2), program=fake(clicks=[10, 20]))
    assert (r.reported_model, r.tool_version) == ("some-model", "fake-1") and r.seconds >= 0
    assert two(r.text) == [10.0, 20.0]


def test_a_stored_reply_is_read_back_without_a_call(fake, tmp_path):
    t = Transcripts(tmp_path / "t")
    a = ask(t, "m", "plain", "S", "P", clicks_schema(2), two, program=fake(clicks=[10, 20]), allow_model_calls=True)
    b = ask(t, "m", "plain", "S", "P", clicks_schema(2), two, program="/nonexistent")
    assert a["status"] == "ok" and b["parsed"] == [10.0, 20.0]
    assert t.count("m", "plain") == {"ok": 1}


def test_without_the_flag_no_call_is_made(tmp_path, fake):
    program = fake(clicks=[1, 2])
    with pytest.raises(ModelCallsNotAllowed):
        ask(Transcripts(tmp_path / "t"), "m", "plain", "S", "P", clicks_schema(2), two, program=program)
    assert program.calls() == 0


def test_a_bad_reply_is_retried_twice_then_recorded_invalid(fake, tmp_path):
    args = ("m", "plain", "S", "P", clicks_schema(2), two)
    ok = ask(Transcripts(tmp_path / "a"), *args, program=fake(bad_first=2, clicks=[1, 2]), allow_model_calls=True)
    bad = ask(Transcripts(tmp_path / "b"), *args, program=fake(bad_first=3, clicks=[1, 2]), allow_model_calls=True)
    assert (ok["status"], ok["attempts"]) == ("ok", 3) and (bad["status"], bad["attempts"]) == ("invalid", 3)


def test_an_out_of_range_number_is_invalid_and_not_clipped(fake, tmp_path):
    r = ask(Transcripts(tmp_path / "t"), "m", "plain", "S", "P", clicks_schema(2), two, program=fake(clicks=[10, 140]), allow_model_calls=True)
    assert r["status"] == "invalid" and r["parsed"] is None


def test_a_refusal_is_recorded_as_a_refusal(fake, tmp_path):
    r = ask(Transcripts(tmp_path / "t"), "m", "plain", "S", "P", clicks_schema(2), two, program=fake(refuse=True), allow_model_calls=True)
    assert r["status"] == "refusal" and r["parsed"] is None


@pytest.mark.parametrize("mode", ["exit_nonzero", "usage_limit_text_exit_zero", "sleep_past_cap"])
def test_transport_failures_store_nothing(fake, tmp_path, mode):
    t = Transcripts(tmp_path / "t")
    with pytest.raises(TransportError):
        ask(t, "m", "plain", "S", "P", clicks_schema(2), two, program=fake(**{mode: True}), allow_model_calls=True, time_cap_s=1)
    assert t.count("m", "plain") == {}


def test_the_record_holds_the_request_the_reply_and_the_caller_s_labels(fake, tmp_path):
    t = Transcripts(tmp_path / "t")
    r = ask(t, "m", "plain", "S", "P", clicks_schema(2), two, program=fake(clicks=[10, 20]), allow_model_calls=True,
            meta={"block_id": "0-00", "feed_index": 1, "reader": 3})
    assert r["request"] == {"model": "m", "kind": "plain", "system": "S", "prompt": "P", "schema": clicks_schema(2)}
    assert r["meta"] == {"block_id": "0-00", "feed_index": 1, "reader": 3} and json.loads(r["reply_text"]) == {"clicks": [10, 20]}
    assert {"reported_model", "tool_version", "seconds", "stored_at", "attempts"} <= set(r)
    assert t.get("m", "plain", request_hash("m", "plain", "S", "P", clicks_schema(2))) == r


def test_the_hash_changes_with_every_part_of_the_request():
    base = ("m", "plain", "S", "P", clicks_schema(2))
    others = [("n", *base[1:]), ("m", "brief", *base[2:]), ("m", "plain", "T", "P", base[4]), ("m", "plain", "S", "Q", base[4]),
              ("m", "plain", "S", "P", clicks_schema(3))]
    assert len({request_hash(*base), *(request_hash(*o) for o in others)}) == 6


def test_a_damaged_transcript_is_a_miss(tmp_path):
    t = Transcripts(tmp_path / "t")
    p = t.put("m", "plain", "abc", {"status": "ok"})
    p.write_text("{not json", encoding="utf-8")
    assert t.get("m", "plain", "abc") is None and t.count("m", "plain") == {}


def test_a_dot_file_the_drive_leaves_beside_a_transcript_is_not_counted(tmp_path):
    t = Transcripts(tmp_path / "t")
    p = t.put("m", "plain", "abc", {"status": "ok"})
    (p.parent / "._abc.json").write_text('{"status": "ok"}', encoding="utf-8")
    assert t.count("m", "plain") == {"ok": 1}
