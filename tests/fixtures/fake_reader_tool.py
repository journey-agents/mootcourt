"""A stand-in for the command line tool that plays a reader. No model is involved.

Run as a program it reads the prompt on standard input, works out what is asked from the prompt's last line, and prints
the event stream of the real tool: a start record, the reply, and a result record. Its behaviour is set by
``FAKE_READER_*`` environment variables, which ``make_fake`` writes into a small launcher script, because the wrapper
under test passes on only a short list of the caller's environment.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import stat
import sys
import time
import zlib
from pathlib import Path

PLANTED_WORD = "amazing"          # the planted mode clicks most on a headline that holds this word
MIDDLE_WORD = "plain"             # and more on one that holds this word than on one that holds neither


def planted_score(line: str) -> float:
    lowered = line.lower()
    return 60.0 if PLANTED_WORD in lowered else 40.0 if MIDDLE_WORD in lowered else 20.0


def _option(argv: list[str], name: str, default: str = "") -> str:
    return argv[argv.index(name) + 1] if name in argv else default


def _count(path: str) -> int:
    """Add one line to the count file and return the number of lines, under an exclusive lock."""
    import fcntl

    with open(path, "a+", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.write("x\n")
        fh.flush()
        fh.seek(0)
        return sum(1 for _ in fh)


def _numbered(prompt: str) -> list[str]:
    return [m.group(1) for m in re.finditer(r"^\s*\d+\. (.*)$", prompt, re.M)]


def _number(text: str) -> float:
    return float(zlib.crc32(text.encode("utf-8")) % 101)


def _schema_from(prompt: str) -> dict:
    """What the prompt asks for, read from its last line: the tool is given no schema, so the stand-in reads the request."""
    found = re.search(r'Reply as \{"(\w+)": .*?\}(?: with exactly (\d+))?', prompt)
    if not found:
        return {}
    return {"properties": {found.group(1): {"minItems": int(found.group(2) or 0)}}}


def _reply(prompt: str, schema: dict, env: dict) -> str:
    key = next(iter(schema.get("properties", {"clicks": {}})))
    n = schema.get("properties", {}).get(key, {}).get("minItems", 0)
    mode = env.get("FAKE_READER_MODE", "")
    lines = _numbered(prompt)
    if key == "note":
        return json.dumps({"note": "This audience clicks on surprising stories about ordinary people."})
    if key == "completions":
        return json.dumps({"completions": ["and nobody saw it coming"] * n})
    if key == "seen":
        return json.dumps({"seen": [_number(line) for line in lines[:n]] + [0.0] * max(0, n - len(lines))})
    if key == "winners":
        pairs = re.findall(r"^\s*\d+\. A: (.*)\n\s+B: (.*)$", prompt, re.M)
        picks = [("A" if planted_score(a) >= planted_score(b) else "B") for a, b in pairs]
        return json.dumps({"winners": (picks + ["A"] * n)[:n]})
    if "FAKE_READER_CLICKS" in env:
        return json.dumps({"clicks": json.loads(env["FAKE_READER_CLICKS"])})
    feed = prompt.split("The feed:", 1)[-1]
    lines = _numbered(feed)
    if mode == "planted":
        return json.dumps({"clicks": [planted_score(line) for line in lines]})
    if mode == "random":
        return json.dumps({"clicks": [_number(prompt[:80] + line) for line in lines]})
    return json.dumps({"clicks": [50.0] * n})


def main(argv: list[str]) -> int:
    env = os.environ
    prompt = sys.stdin.read()
    calls = _count(env["FAKE_READER_COUNT_FILE"]) if env.get("FAKE_READER_COUNT_FILE") else 0
    if env.get("FAKE_READER_EXIT_NONZERO"):
        print("the tool failed", file=sys.stderr)
        return 1
    if env.get("FAKE_READER_SLEEP_PAST_CAP"):
        time.sleep(30)
    schema = _schema_from(prompt)
    if env.get("FAKE_READER_USAGE_LIMIT_TEXT_EXIT_ZERO"):
        text = "You have reached your usage limit. Try again later."
    elif env.get("FAKE_READER_SAY"):
        text = env["FAKE_READER_SAY"]
    elif env.get("FAKE_READER_REFUSE_SOME_NOTES") and "note" in schema.get("properties", {}) and zlib.crc32(prompt.encode()) % 2 == 0:
        text = "I would rather not write that note."
    elif env.get("FAKE_READER_REFUSE"):
        text = "I cannot play this role."
    elif env.get("FAKE_READER_ECHO_CWD") or env.get("FAKE_READER_ECHO_ENV"):
        text = json.dumps({"cwd": os.getcwd(), "listing": sorted(os.listdir(".")), "env": sorted(env), "argv": argv})
    elif calls and calls <= int(env.get("FAKE_READER_BAD_FIRST", "0")):
        text = json.dumps({"clicks": [1]})                          # the wrong count of numbers
    else:
        text = _reply(prompt, schema, env)
    model = env.get("FAKE_READER_REPORT_MODEL") or _option(argv, "--model")
    start = {"type": "system", "subtype": "init", "model": model, "mcp_servers": [], "claude_code_version": "fake-1",
             "tools": json.loads(env.get("FAKE_READER_START_TOOLS", "[]")), "session_id": "not-kept", "cwd": os.getcwd()}
    if env.get("FAKE_READER_NO_VERSION"):
        del start["claude_code_version"]
    print(json.dumps(start))
    print(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}))
    print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": text, "modelUsage": {model: {"outputTokens": 1}}}))
    return 0


class Fake(str):
    """The path of a launcher, with the count of calls made through it."""

    count_file: Path

    def calls(self) -> int:
        return len(self.count_file.read_text(encoding="utf-8").splitlines()) if self.count_file.exists() else 0


def make_fake(folder: Path, **options) -> Fake:
    """Write a launcher into ``folder`` that runs this file with the given behaviour, and return its path."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    name = "fake-" + format(zlib.crc32(json.dumps(options, sort_keys=True, default=str).encode()), "08x")
    count_file = folder / f"{name}.count"
    lines = ["#!/bin/sh", f"export FAKE_READER_COUNT_FILE={shlex.quote(str(count_file))}"]
    for key, value in options.items():
        text = value if isinstance(value, str) else json.dumps(value)
        lines.append(f"export FAKE_READER_{key.upper()}={shlex.quote(text)}")
    lines.append(f'exec {shlex.quote(sys.executable)} {shlex.quote(str(Path(__file__).resolve()))} "$@"')
    launcher = folder / name
    launcher.write_text("\n".join(lines) + "\n", encoding="utf-8")
    launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR)
    fake = Fake(str(launcher))
    fake.count_file = count_file
    return fake


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
