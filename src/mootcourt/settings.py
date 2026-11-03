"""Project settings from ``mootcourt.toml`` in the working directory, with defaults.

Keys (all optional; ``moot init`` writes them with their defaults):

    [project]    name = "my-program"
    [storage]    data_root = "/path/to/large/volume"      (read by ``mootcourt.storage``)
    [cells]      names = ["checkout_conversion", ...]      the cells the program forecasts (informational, checked by ``moot doctor``)
    [decision]   action_threshold = 0.35                   p_sig above which the team would act; used by the card's robustness check
    [gate]       target_power = 0.90                       the power at which gate sizes are read; ``moot simulate power`` uses it
    [service]    url = "http://127.0.0.1:8000"             checked by ``moot doctor`` when set
    [simulators.NAME] ...                                  response simulators (see ``moot simulators list``)
"""
from __future__ import annotations

import tomllib
from pathlib import Path

from mootcourt.config import ACTION_THRESHOLD

CONFIG_FILE = "mootcourt.toml"


def abstain_config(cwd: Path | str | None = None):
    """The abstention configuration from the project file: the one place every card path (CLI, service, MCP) reads it.

    Only ``[decision] action_threshold`` is configurable; the other abstention limits are fixed by ``mootcourt.config``.
    """
    from mootcourt.abstain import AbstainConfig

    return AbstainConfig(action_threshold=load_settings(cwd)["decision"]["action_threshold"])


def load_settings(cwd: Path | str | None = None) -> dict:
    """Settings with defaults filled in. A malformed file raises ValueError naming the file."""
    from mootcourt.simulate import DEFAULT_TARGET

    path = Path(cwd or Path.cwd()) / CONFIG_FILE
    raw: dict = {}
    if path.is_file():
        try:
            raw = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            raise ValueError(f"{path}: {exc}") from None
    dec = {"action_threshold": float((raw.get("decision") or {}).get("action_threshold", ACTION_THRESHOLD))}
    gate = {"target_power": float((raw.get("gate") or {}).get("target_power", DEFAULT_TARGET))}
    if not 0.0 < dec["action_threshold"] < 1.0:
        raise ValueError(f"{path}: decision.action_threshold must be between 0 and 1")
    if not 0.5 <= gate["target_power"] < 1.0:
        raise ValueError(f"{path}: gate.target_power must be in [0.5, 1)")
    return {"project": {"name": str((raw.get("project") or {}).get("name", ""))}, "cells": list((raw.get("cells") or {}).get("names", [])),
            "decision": dec, "gate": gate, "service": dict(raw.get("service") or {}), "storage": dict(raw.get("storage") or {}),
            "simulators": dict(raw.get("simulators") or {}), "path": str(path), "exists": path.is_file()}
