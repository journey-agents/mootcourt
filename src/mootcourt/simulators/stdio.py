"""Stdio adapter: run a command, send the request as one JSON line on stdin, read one JSON line from stdout.

The process runs without a shell, in its own process group, with the repository's environment minus every variable
whose name looks like a credential (KEY, TOKEN, SECRET, PASSWORD, CREDENTIAL, DSN, COOKIE, SESSION, BEARER, PRIVATE, or the
whole words PASS, AUTH, PAT and CERT in the name), every proxy variable, and every ``*_URL`` or ``*_URI`` variable whose value
carries a user name and password, unless the provider declares that variable by name. A time cap kills the whole process group, so a
wrapper such as ``sh -c`` or ``uv run`` cannot leave the real agent running. Output beyond one megabyte is refused.
The group is killed on every exit path, including an interrupt (Ctrl-C does not reach the child, which has its own
session) and any exception. The adapter also refuses a command that would run anything inside the data root: the
resolved working directory, the program, any argument that names a path, the value after ``=`` in an ``--opt=path``
argument (and each piece of it when it is a ``:`` list), the words of a string after ``sh -c`` (or bash, zsh, dash, ksh), and
the string of ``env -S`` (``--split-string``), which env splits into a command, and the file a ``-m module`` or ``-mmodule``
argument would load; letter case is ignored where the volume ignores it. A shell string
is split into words and each word is checked as a path; what a shell would build at run time (variables, command substitution,
a path assembled by concatenation) is not evaluated, so a shell wrapper is a convenience to be reviewed, not a sandbox.

A decline is the agent printing ``null``; it leaves ``last_failure`` empty. Everything else that returns None is a
failure with a kind in ``last_failure`` (timeout, start, exit, invalid) and a reason in ``last_note``: the runner
records it and does not cache it.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Iterable, Mapping
from pathlib import Path

from mootcourt.simulators.base import MAX_OUTPUT_BYTES, SimulationRequest, SimulationResult, SimulatorError, SimulatorInfo

# found anywhere in the name
SECRET_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "PASSWD", "CREDENTIAL", "DSN", "COOKIE", "SESSION", "BEARER", "PRIVATE")
SECRET_WORDS = ("PASS", "AUTH", "PAT", "CERT")                                      # found as a whole word between underscores
# public certificates and a host list, not credentials
NOT_SECRET = {"SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE", "PIP_CERT", "NO_PROXY"}
_URL_WITH_LOGIN = re.compile(r"://[^/@\s]+:[^/@\s]+@")


def _looks_secret(name: str, value: str = "") -> bool:
    upper = name.upper()
    if upper in NOT_SECRET:
        return False
    if upper.endswith("_PROXY") or upper == "PROXY":                      # a proxy URL often carries a login
        return True
    if upper.endswith(("_URL", "_URI")) and _URL_WITH_LOGIN.search(value or ""):
        return True
    return any(m in upper for m in SECRET_MARKERS) or any(w in SECRET_WORDS for w in re.split(r"[^A-Z0-9]+", upper))


def scrub_env(environ: Mapping[str, str], declared: Iterable[str] = ()) -> dict[str, str]:
    """A copy of ``environ`` without credential-looking names or values, except the declared names."""
    keep = set(declared)
    return {k: v for k, v in environ.items() if k in keep or not _looks_secret(k, v)}


def _module_candidates(name: str, base: Path) -> list[Path]:
    """Files or folders a ``python -m name`` could load: the working directory, the search path and PYTHONPATH (not imported)."""
    rel = Path(*name.split("."))
    dirs = [base, *(Path(p) for p in sys.path if p), *(Path(p) for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p)]
    return [d / sub for d in dirs for sub in (rel.with_suffix(".py"), rel, rel / "__main__.py")]


SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "ash"}


def _shell_tokens(string: str) -> list[str]:
    """The words of a shell command string; a string shlex cannot read is split on white space instead."""
    try:
        return shlex.split(string)
    except ValueError:
        return string.split()


_ENV_VALUE_LETTERS = "uCPa"                 # short options of env that take a value: -u NAME, -C DIR, -P PATH, -a ARG
_ENV_VALUE_LONG = {"--unset", "--chdir", "--default-path", "--argv0", "--split-string"}      # long forms; "=VALUE" attaches the value


_ENV_LONG_ALL = ("--ignore-environment", "--null", "--unset", "--chdir", "--split-string", "--block-signal", "--default-signal", "--ignore-signal",
                 "--list-signal-handling", "--debug", "--argv0", "--version", "--help", "--default-path")


def _env_long(word: str) -> str | None:
    """The long option of env a word names, by unique prefix as GNU env reads it (``--spl`` is ``--split-string``); None if unknown or ambiguous."""
    name = word.split("=", 1)[0]
    if name in _ENV_LONG_ALL:
        return name
    hits = [o for o in _ENV_LONG_ALL if o.startswith(name)] if len(name) > 2 else []
    return hits[0] if len(hits) == 1 else None


def _env_short_cluster(word: str) -> tuple[str | None, bool]:
    """Read a short option cluster of env (``-i``, ``-uNAME``, ``-iS``, ``-Sstring``) from its first letter.

    Letters that take no value (``-i``, ``-0``, ``-v``) are skipped. The first letter that takes a value ends the cluster: the rest of
    the word is its value (``-uSHELL`` unsets SHELL, it does not mean ``-S HELL``), and when nothing follows, the next word is.
    Returns ``(letter, attached)``: the value-taking letter that ended the cluster, or None, and whether its value is in the word.
    """
    for k, letter in enumerate(word[1:], 1):
        if letter in _ENV_VALUE_LETTERS or letter == "S":
            return letter, k + 1 < len(word)
    return None, False


def _env_option_width(command: list[str], i: int) -> int:
    """Number of words the env option at ``command[i]`` occupies (the option and its value)."""
    word = command[i]
    if word.startswith("--"):
        return 1 if "=" in word or _env_long(word) not in _ENV_VALUE_LONG else 2
    if word.startswith("-") and len(word) > 1:
        letter, attached = _env_short_cluster(word)
        return 2 if letter is not None and not attached else 1
    return 1


def _split_env_strings(command: list[str], depth: int = 0) -> list[str]:
    """``command`` with the string of ``env -S`` (``--split-string``, in any spelling) split into words and put in its place.

    ``env -S 'sh -c "python3 /x/agent.py"' `` runs what the string says, so its words are checked like any others; a string
    that is itself an ``env -S`` command is split again (to a small depth). Only a bare ``-S`` (or ``-S`` among argument-free
    letters, ``-iS``) starts a split: in ``-uSHELL`` the S belongs to the name that ``-u`` unsets.
    """
    if not command or os.path.basename(command[0]) != "env" or depth > 4:
        return command
    i = 1
    while i < len(command):
        word = command[i]
        value = None
        if word.startswith("--") and _env_long(word) == "--split-string":          # in any unique-prefix spelling, as GNU env reads it
            if "=" in word:
                value, width = word.split("=", 1)[1], 1
            else:
                value, width = (command[i + 1] if i + 1 < len(command) else ""), 2
        elif word.startswith("-") and not word.startswith("--") and len(word) > 1:
            letter, attached = _env_short_cluster(word)
            if letter == "S":                                                   # -S, -iS, or the value attached as in -Sstring
                value, width = (word[word.index("S") + 1:], 1) if attached else ((command[i + 1] if i + 1 < len(command) else ""), 2)
        if value is not None:
            rest = _split_env_strings(command[:1] + _shell_tokens(value), depth + 1)
            return _split_env_strings(command[:i] + rest[1:] + command[i + width:], depth + 1)
        if not word.startswith("-") and "=" not in word:
            if os.path.basename(word) == "env":                                 # env env -S '...'
                return command[:i] + _split_env_strings(command[i:], depth + 1)
            break
        i += _env_option_width(command, i) if word.startswith("-") else 1
    return command


def _program_index(command: list[str]) -> int:
    """Index of the program a command runs: past a leading ``env`` and its options and NAME=VALUE arguments."""
    i = 0
    while i < len(command) and os.path.basename(command[i]) == "env":                # env may wrap env
        i += 1
        while i < len(command) and (command[i].startswith("-") or "=" in command[i]):
            i += _env_option_width(command, i) if command[i].startswith("-") else 1     # an option's value is part of the option
    return min(i, len(command) - 1)


def _expand_shell_strings(command: list[str]) -> list[str]:
    """``command`` plus the words of the string that follows ``-c`` after a shell program (``sh -c 'python3 /x/agent.py'``, also
    behind ``env NAME=VALUE``), nested ones too, and the words of an ``env -S`` string."""
    command = _split_env_strings(command)
    out = list(command)
    start = _program_index(command)
    if os.path.basename(command[start]) in SHELLS:
        for i, element in enumerate(command[start:-1], start):
            if re.fullmatch(r"-[a-z]*c[a-z]*", element):
                out += _expand_shell_strings(_shell_tokens(command[i + 1]) or [""])
                break
    return out


def _resolve_command_paths(command: list[str], cwd: str | None) -> list[Path]:
    """Every path a command would touch: the working directory, the program on the search path, each element that
    names an existing file or folder, the value after ``=`` in an option, each piece of a ``:`` separated list, the words of a
    shell string after ``sh -c``, and the files a ``-m`` module (``-m NAME`` or ``-mNAME``) could load."""
    base = Path(cwd) if cwd else Path.cwd()
    found = [base.resolve()]
    first = shutil.which(command[0], path=os.environ.get("PATH"))
    if first:
        found.append(Path(first).resolve())
    elements = _expand_shell_strings(command)
    candidates: list[str] = []
    for i, element in enumerate(elements):
        candidates.append(element)
        if "=" in element:
            candidates.append(element.split("=", 1)[1])                       # the whole value after "="
        candidates += re.split(r"[=:]", element)                                # and each piece around "=" or ":" (a path list, the first included)
        module = None
        if element == "-m" and i + 1 < len(elements):
            module = elements[i + 1]
        elif re.fullmatch(r"-m[A-Za-z_][\w.]*", element):                     # python accepts the name attached: -mNAME
            module = element[2:]
        if module:
            found.extend(c.resolve() for c in _module_candidates(module, base) if _exists(c))
    for element in candidates:
        try:
            p = Path(element)
            if not p.is_absolute():
                p = base / p
            if p.exists():
                found.append(p.resolve())
        except (OSError, ValueError):
            continue
    return found


def _exists(p: Path) -> bool:
    try:
        return p.exists()
    except (OSError, ValueError):
        return False


def _inside(p: Path, root: Path) -> bool:
    """True when ``p`` is ``root`` or beneath it. Compares by file identity, so letter case on a case-insensitive volume
    and links do not matter; falls back to a case-folded comparison of the names for paths that do not exist."""
    for anc in (p, *p.parents):
        try:
            if anc.exists() and root.exists() and os.path.samefile(anc, root):
                return True
        except OSError:
            continue
    a, r = os.path.normcase(str(p)).casefold(), os.path.normcase(str(root)).casefold().rstrip(os.sep)
    return a == r or a.startswith(r + os.sep)


def refuse_data_root_command(command: list[str], cwd: str | None) -> None:
    """Raise SimulatorError when the command, its working directory, or a file named in it lies inside the configured data root."""
    from mootcourt.storage import storage_paths

    root = storage_paths().root
    if root is None:
        return
    root = root.resolve()
    for p in _resolve_command_paths(command, cwd):
        if _inside(p, root):
            raise SimulatorError(f"{p} is inside the data root {root}; nothing under the data root is run as a simulator command")


def kill_group(proc: subprocess.Popen) -> None:
    """Kill the process group the child leads (the child and everything it started)."""
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        proc.kill()
    except OSError:
        pass


class StdioSimulator:
    """Adapter for an agent that speaks one JSON line in and one JSON line out."""

    def __init__(self, command: list[str], info: SimulatorInfo, time_cap_s: float = 30.0, env: Iterable[str] = (), cwd: str | None = None):
        if not command or not all(isinstance(c, str) for c in command):
            raise SimulatorError("command must be a non-empty list of strings")
        if time_cap_s <= 0:
            raise SimulatorError("time_cap_s must be positive")
        refuse_data_root_command(list(command), cwd)
        self.command, self.info, self.time_cap_s, self.cwd = list(command), info, float(time_cap_s), cwd
        self.declared_env = tuple(env)
        self.last_note = ""
        self.last_failure: str | None = None

    def describe(self) -> SimulatorInfo:
        return self.info

    def _fail(self, kind: str, note: str):
        self.last_failure, self.last_note = kind, note
        return None

    def _run(self, payload: str, env: dict, cap: float):
        """Start the command in its own group, feed it, read at most the output limit, and kill the group on time or overflow."""
        proc = subprocess.Popen(self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, cwd=self.cwd,
                                shell=False, start_new_session=True)
        try:
            return self._supervise(proc, payload, cap)
        finally:
            # Every exit path, an interrupt and any exception included, ends the whole group: nothing the command started outlives the call.
            kill_group(proc)
            proc.wait()

    def _supervise(self, proc: subprocess.Popen, payload: str, cap: float):
        bufs = {"out": bytearray(), "err": bytearray()}
        overflow = threading.Event()

        def pump(stream, key):
            try:
                while True:
                    chunk = stream.read(65536)
                    if not chunk:
                        return
                    if len(bufs[key]) + len(chunk) > MAX_OUTPUT_BYTES:
                        overflow.set()
                        kill_group(proc)
                        return
                    bufs[key] += chunk
            except (OSError, ValueError):
                return

        def feed():
            try:
                proc.stdin.write(payload.encode("utf-8"))
                proc.stdin.close()
            except (OSError, ValueError):
                pass

        threads = [threading.Thread(target=pump, args=(proc.stdout, "out"), daemon=True),
                   threading.Thread(target=pump, args=(proc.stderr, "err"), daemon=True),
                   threading.Thread(target=feed, daemon=True)]
        for t in threads:
            t.start()
        timed_out = False
        try:
            proc.wait(timeout=cap)
        except subprocess.TimeoutExpired:
            timed_out = True
        # The leader has exited or the cap is over: nothing it started may outlive this call.
        kill_group(proc)
        proc.wait()
        for t in threads:
            t.join(timeout=5)
        return proc.returncode, bytes(bufs["out"]), bytes(bufs["err"]), timed_out, overflow.is_set()

    def simulate(self, request: SimulationRequest) -> SimulationResult | None:
        self.last_note, self.last_failure = "", None
        cap = min(self.time_cap_s, float(request.budget.max_seconds))
        payload = json.dumps(request.to_wire(), sort_keys=True) + "\n"
        env = scrub_env(os.environ, self.declared_env)
        t0 = time.perf_counter()
        try:
            code, out, err, timed_out, overflow = self._run(payload, env, cap)
        except OSError as exc:
            return self._fail("start", f"could not start the command: {exc}")
        latency = time.perf_counter() - t0
        if timed_out:
            return self._fail("timeout", f"time cap of {cap:g} s reached; process group killed")
        if overflow:
            return self._fail("invalid", f"invalid output: the output is too large (more than {MAX_OUTPUT_BYTES} bytes)")
        if code != 0:
            return self._fail("exit", f"exit code {code}: {err.decode('utf-8', 'replace').strip()[:200]}")
        line = next((ln for ln in out.decode("utf-8", "replace").splitlines() if ln.strip()), "")
        try:
            data = json.loads(line)
            if data is None:
                self.last_note = "the agent declined"
                return None
            return SimulationResult.from_dict(data, provider_id=self.info.provider_id, version=self.info.version, latency_s=latency)
        except (ValueError, SimulatorError, TypeError, AttributeError, KeyError, OverflowError) as exc:
            return self._fail("invalid", f"invalid output: {exc}")
