"""One call of the command line tool that plays a reader.

The tool is started without a shell, in a new empty directory outside the repository and the data root, with no
tools, no servers, no settings and no stored session, and with an environment that holds a short allow list of names
and nothing else. The prompt goes in on standard input. The child leads its own process group, and a time cap ends the
whole group. A failure of the transport (a nonzero exit, a timeout, an event stream that cannot be read, a listed
tool or server, a usage-limit message in place of a reply) raises ``TransportError``: it is not a reply and is never stored as one.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from mootcourt.simulators.readers.prompts import first_json_object
from mootcourt.simulators.stdio import kill_group, refuse_data_root_command

# Names the tool's login needs beyond the allow list. With a subscription login it needs none (settled on 19 November 2026).
LOGIN_ENV: tuple[str, ...] = ()

# Where the tool's event stream carries each part of a reply. The start record is the first event; the result record the last.
START_RECORD = {"type": "system", "subtype": "init", "tools": "tools", "servers": "mcp_servers", "model": "model",
                "version": "claude_code_version"}
RESULT_RECORD = {"type": "result", "text": "result", "error": "is_error", "models": "modelUsage"}

# The fields of a start record that are kept on file. The rest holds paths and session identifiers of the machine.
START_FIELDS = ("type", "subtype", "tools", "mcp_servers", "model", "claude_code_version", "agents", "plugins", "skills",
                "slash_commands", "apiKeySource", "permissionMode", "output_style")

# Applied only to a reply that holds no JSON object.
USAGE_LIMIT_PATTERN = re.compile(
    r"usage limit|rate limit|limit reached|try again (later|at)|hit your( \w+)? limit|\bresets\b|api error|overloaded|"
    r"connection error|credit balance|invalid api key|/login|prompt is too long|not logged in|authentication", re.I)

# The child's environment holds these names and no others, so a run started from a terminal and one started from an agent
# session send the same thing. ``LOGIN_ENV`` adds what the tool's login needs.
ENV_ALLOWED = ("PATH", "HOME", "USER", "LOGNAME", "LANG", "TMPDIR", "TERM", "SHELL")

MAX_OUTPUT_BYTES = 4_000_000


class TransportError(RuntimeError):
    """The tool did not deliver a reply: a nonzero exit, a timeout, an unreadable envelope or a usage-limit message."""


@dataclass(frozen=True)
class ToolReply:
    text: str
    reported_model: str | None
    tool_version: str | None
    seconds: float


def build_command(model: str, system: str, schema: dict | None = None, program: str = "claude") -> list[str]:
    """The exact command of one call. The prompt is not part of it; it is sent on standard input.

    The reply's schema is not passed to the tool: the tool would answer it through a tool of its own, and the start record
    must list no tool. The prompt states the form of the reply and the reply is checked here. The event stream is on for
    every call, because only the start record carries the tool's version.
    """
    return [program, "-p", "--model", model, "--system-prompt", system, "--tools", "", "--strict-mcp-config",
            "--mcp-config", json.dumps({"mcpServers": {}}), "--setting-sources", "", "--no-session-persistence",
            "--disable-slash-commands", "--output-format", "stream-json", "--verbose"]


def _repository_roots() -> list[Path]:
    """Every folder with a ``.git`` entry above the working directory or above this file."""
    roots = []
    for start in (Path.cwd().resolve(), Path(__file__).resolve().parent):
        for folder in (start, *start.parents):
            if (folder / ".git").exists():
                roots.append(folder)
    return roots


def _inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _empty_directory() -> Path:
    """A new empty directory that lies outside the repository and outside the data root."""
    from mootcourt.storage import storage_paths

    path = Path(tempfile.mkdtemp(prefix="reader-call-")).resolve()
    data_root = storage_paths().root
    forbidden = _repository_roots() + ([Path(data_root).resolve()] if data_root is not None else [])
    for root in forbidden:
        if _inside(path, root):
            shutil.rmtree(path, ignore_errors=True)
            raise TransportError(f"the temporary directory {path} lies inside {root}; set TMPDIR to a place outside it")
    return path


def child_env() -> dict[str, str]:
    """The environment of the child: the allowed names, the locale names and the names the login needs."""
    keep = set(ENV_ALLOWED) | set(LOGIN_ENV)
    return {k: v for k, v in os.environ.items() if k in keep or k.startswith("LC_")}


def same_model(requested: str, reported: str | None) -> bool:
    """Whether the model the tool reports is the one asked for. A dated or bracketed form of the same identifier counts."""
    if not reported:
        return True
    return reported == requested or reported.startswith((requested + "-", requested + "["))


def read_events(stdout: str) -> tuple[dict, dict]:
    """The start record and the result record of the tool's event stream."""
    events = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            events.append(event)
    start = next((e for e in events if e.get("type") == START_RECORD["type"] and e.get("subtype") == START_RECORD["subtype"]), None)
    result = next((e for e in reversed(events) if e.get("type") == RESULT_RECORD["type"] and RESULT_RECORD["text"] in e), None)
    if start is None or result is None:
        raise TransportError("the tool's output holds no start record or no result record")
    return start, result


def _run(command: list[str], prompt: str, time_cap_s: float) -> tuple[str, float]:
    """Run the command in a new empty directory and return its standard output and the seconds it took."""
    cwd = _empty_directory()
    started = time.monotonic()
    try:
        refuse_data_root_command(command, str(cwd))
        try:
            proc = subprocess.Popen(command, cwd=cwd, env=child_env(), stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                                    errors="replace", start_new_session=True)
        except OSError as exc:
            raise TransportError(f"the tool could not be started: {exc}") from exc
        try:
            stdout, stderr = proc.communicate(prompt, timeout=time_cap_s)
        except subprocess.TimeoutExpired as exc:
            raise TransportError(f"the tool gave no reply within {time_cap_s:g} seconds") from exc
        finally:
            kill_group(proc)
            proc.wait()
    finally:
        shutil.rmtree(cwd, ignore_errors=True)
    if proc.returncode != 0:
        raise TransportError(f"the tool exited with code {proc.returncode}: {(stderr or stdout).strip()[:300]}")
    if len(stdout) > MAX_OUTPUT_BYTES:
        raise TransportError("the tool's output is larger than the cap")
    return stdout, time.monotonic() - started


def _reply(start: dict, result: dict, seconds: float) -> ToolReply:
    loaded = list(start.get(START_RECORD["tools"]) or []) + list(start.get(START_RECORD["servers"]) or [])
    if loaded:
        raise TransportError(f"the tool's start record lists tools or servers, and none may be loaded: {loaded}")
    text = result[RESULT_RECORD["text"]]
    text = text if isinstance(text, str) else json.dumps(text)
    if result.get(RESULT_RECORD["error"]):
        raise TransportError(f"the tool reported an error: {text.strip()[:300]}")
    if first_json_object(text) is None and USAGE_LIMIT_PATTERN.search(text):
        raise TransportError(f"the tool answered with a usage-limit message: {text.strip()[:300]}")
    used = sorted(result.get(RESULT_RECORD["models"]) or {})
    model_id = used[0] if len(used) == 1 else (",".join(used) or start.get(START_RECORD["model"]))
    version = start.get(START_RECORD["version"])
    return ToolReply(text=text, reported_model=model_id if isinstance(model_id, str) else None,
                     tool_version=version if isinstance(version, str) else None, seconds=seconds)


def call(model: str, system: str, prompt: str, schema: dict | None = None, *, program: str = "claude",
         time_cap_s: float = 180.0) -> ToolReply:
    """Run the tool once and return its reply text with what the tool reports about itself."""
    stdout, seconds = _run(build_command(model, system, schema, program), prompt, time_cap_s)
    return _reply(*read_events(stdout), seconds)


def start_record(model: str, system: str, prompt: str, schema: dict | None = None, *, program: str = "claude",
                 time_cap_s: float = 180.0) -> dict:
    """One call that returns the tool's own start record, the tools and servers it lists, and the reply.

    This is the canary. Tests can inspect the command, and only the tool can say what it loaded. A listed tool or server
    does not raise here: the caller reports it.
    """
    stdout, seconds = _run(build_command(model, system, schema, program), prompt, time_cap_s)
    start, result = read_events(stdout)
    tools, servers = list(start.get(START_RECORD["tools"]) or []), list(start.get(START_RECORD["servers"]) or [])
    reply = _reply({**start, START_RECORD["tools"]: [], START_RECORD["servers"]: []}, result, seconds)
    return {"start_record": {k: start[k] for k in START_FIELDS if k in start}, "tools": tools, "servers": servers,
            "reply_text": reply.text, "reported_model": reply.reported_model, "tool_version": reply.tool_version,
            "command": build_command(model, "<system prompt>", None, program), "env_names": sorted(child_env())}
