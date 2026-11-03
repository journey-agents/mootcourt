"""Find and build providers: built-ins, Python entry points and ``mootcourt.toml``.

Registration, in the order they are looked up:

1. built-ins ``null`` and ``heuristic``;
2. Python entry points in the group ``mootcourt.simulators``: each names a class or a zero-argument factory that
   returns an object with ``describe`` and ``simulate``;
3. the ``[simulators.<name>]`` tables of ``mootcourt.toml`` in the working directory (or the file named by the
   caller). A table sets ``adapter`` to ``stdio``, ``http``, ``recorded`` or ``builtin`` plus that adapter's
   settings, ``version``, ``knowledge_cutoff``, ``cost_model`` and ``description``. ``enabled = false`` hides a
   provider. A name from the file may not shadow a built-in.

Relative paths in the file resolve against the working directory. A stdio command runs with the config file's
directory as its working directory. ``knowledge_cutoff`` (an ISO date) is required for every stdio and http provider
and for every entry-point provider: a missing cutoff would otherwise make every origin look clean. An agent with no
training data of its own can declare a date before the earliest origin.
"""
from __future__ import annotations

import tomllib
from importlib import metadata
from pathlib import Path

from mootcourt.simulators.base import ResponseSimulator, SimulatorError, SimulatorInfo
from mootcourt.simulators.builtin import HeuristicSimulator, NullSimulator
from mootcourt.simulators.http import HttpSimulator
from mootcourt.simulators.recorded import RecordedSimulator
from mootcourt.simulators.stdio import StdioSimulator

CONFIG_FILE = "mootcourt.toml"
ENTRY_POINT_GROUP = "mootcourt.simulators"
BUILTINS = {"null": NullSimulator, "heuristic": HeuristicSimulator}
ADAPTERS = ("stdio", "http", "recorded", "builtin")


def load_config(path=None) -> dict:
    """The ``simulators`` tables of the config file (an empty dict when the file or the table is missing)."""
    p = Path(path) if path is not None else Path.cwd() / CONFIG_FILE
    if not p.is_file():
        return {}
    return dict(tomllib.loads(p.read_text(encoding="utf-8")).get("simulators", {}))


def entry_point_names() -> dict[str, metadata.EntryPoint]:
    return {ep.name: ep for ep in metadata.entry_points(group=ENTRY_POINT_GROUP)}


def provider_names(config_path=None) -> list[str]:
    """Every provider that can be built, sorted; disabled config tables are left out."""
    names = set(BUILTINS) | set(entry_point_names())
    names |= {n for n, t in load_config(config_path).items() if t.get("enabled", True)}
    return sorted(names)


def _info(name: str, table: dict) -> SimulatorInfo:
    return SimulatorInfo(provider_id=str(table.get("provider_id", name)), version=str(table.get("version", "0")),
                         knowledge_cutoff=table.get("knowledge_cutoff"), cost_model=str(table.get("cost_model", "free")),
                         description=str(table.get("description", f"{table.get('adapter', 'provider')} provider {name}")))


def _require_cutoff(name: str, cutoff) -> None:
    if cutoff is None:
        raise SimulatorError(f"provider {name}: knowledge_cutoff is required (an ISO date such as 2025-06-01); without it every origin "
                             "would count as possibly contaminated and the agent could not earn a weight")


def from_table(name: str, table: dict, allow_remote: bool = False, base_dir=None) -> ResponseSimulator:
    """Build a provider from one config table; a stdio command runs in ``base_dir`` (the config file's folder)."""
    adapter = table.get("adapter")
    if adapter not in ADAPTERS:
        raise SimulatorError(f"provider {name}: adapter must be one of {ADAPTERS}, got {adapter!r}")
    if adapter == "builtin":
        key = table.get("name", name)
        if key not in BUILTINS:
            raise SimulatorError(f"provider {name}: no built-in called {key}")
        return BUILTINS[key]()
    if adapter == "recorded":
        if "path" not in table:
            raise SimulatorError(f"provider {name}: the recorded adapter needs path")
        return RecordedSimulator(table["path"])
    info = _info(name, table)
    _require_cutoff(name, info.knowledge_cutoff)
    cap = float(table.get("time_cap_s", 30.0))
    if adapter == "stdio":
        if "command" not in table:
            raise SimulatorError(f"provider {name}: the stdio adapter needs command")
        cwd = str(Path(base_dir).resolve()) if base_dir is not None else None
        return StdioSimulator(table["command"], info, time_cap_s=cap, env=table.get("env", ()), cwd=cwd)
    if "url" not in table:
        raise SimulatorError(f"provider {name}: the http adapter needs url")
    return HttpSimulator(table["url"], info, time_cap_s=cap, allow_remote=allow_remote)       # only the command-line flag grants it, never the file


def get_simulator(name: str, config_path=None, allow_remote: bool = False) -> ResponseSimulator:
    """Build the named provider; SimulatorError lists the known names when it is unknown."""
    cfg = load_config(config_path)
    clash = [n for n in cfg if n in BUILTINS and cfg[n].get("adapter") != "builtin"]
    if clash:
        raise SimulatorError(f"config tables may not shadow built-in providers: {clash}")
    if name in BUILTINS:
        return BUILTINS[name]()
    if name in cfg and cfg[name].get("enabled", True):
        base = Path(config_path).resolve().parent if config_path is not None else Path.cwd()
        return from_table(name, cfg[name], allow_remote, base_dir=base)
    eps = entry_point_names()
    if name in eps:
        made = eps[name].load()()
        if not (hasattr(made, "describe") and hasattr(made, "simulate")):
            raise SimulatorError(f"entry point {name} did not produce a simulator")
        _require_cutoff(name, made.describe().knowledge_cutoff)
        return made
    raise SimulatorError(f"unknown provider {name!r}; known: {', '.join(provider_names(config_path))}")


def describe_all(config_path=None) -> list[dict]:
    """One dict per provider: name, adapter, id, version, knowledge cutoff, cost model; unbuildable ones carry an error."""
    cfg = load_config(config_path)
    eps = entry_point_names()
    rows = []
    for name in provider_names(config_path):
        adapter = "builtin" if name in BUILTINS else ("entry point" if name in eps and name not in cfg else cfg[name].get("adapter"))
        row = {"name": name, "adapter": adapter}
        try:
            info = get_simulator(name, config_path, allow_remote=True).describe()
            row.update(provider_id=info.provider_id, version=info.version, knowledge_cutoff=info.knowledge_cutoff,
                       cost_model=info.cost_model, description=info.description)
        except Exception as exc:  # a broken table must not hide the others
            row.update(provider_id=name, version="?", knowledge_cutoff=None, cost_model="?", description=f"unavailable: {exc}")
        rows.append(row)
    return rows
