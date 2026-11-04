"""``moot init`` and ``moot doctor``: set a project up in one command and check that it stays healthy.

``init_project`` writes ``mootcourt.toml``, creates the data root layout, writes the sample ledger (synthetic, exchange format, base
rate ``SAMPLE_BASE_RATE``) and a quick gate file simulated at that base rate (``QUICK_GATE_BASE``), and returns the three commands that
follow. ``run_doctor`` runs the checks below, writes a report to the reports directory
and returns it; ``exit_code`` maps the worst status to 0 (healthy), 1 (warnings) or 2 (failures).

Doctor checks: Python and dependency versions against the minimums in pyproject.toml, sidecar files in the environment (an install on
an exFAT volume; a failure, since `moot backtest` dies on them), the data root and the free space of its volume
(warning under 10 GB), the ledger against the schema, model freshness (the champion of each source was fit on the newest snapshot),
the age of each reliability report (warning past the staleness limit), the configured cells, the card records (post-hoc cards, which the
join recorded and never scored, are a warning; reissues are counted), and the service when ``[service] url`` is set.
"""
from __future__ import annotations

import datetime as dt
import importlib.metadata as md
import json
import shlex
import shutil
import sys
import sysconfig
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from mootcourt.config import RELIABILITY_MAX_AGE_DAYS
from mootcourt.importers.sample import SAMPLE_BASE_RATE
from mootcourt.settings import CONFIG_FILE, load_settings
from mootcourt.storage import LOW_SPACE_BYTES, human_bytes, sidecar_files, storage_paths, visible_glob

MIN_PYTHON = (3, 11)
MIN_VERSIONS = {"numpy": "1.26", "scipy": "1.11", "pandas": "2.1", "pyarrow": "14", "scikit-learn": "1.4", "joblib": "1.3", "typer": "0.12",
                "fastapi": "0.110", "uvicorn": "0.29", "mcp": "1.2", "matplotlib": "3.8"}
OK, WARN, FAIL = "ok", "warn", "fail"
SAMPLE_NAME = "sample-ledger.csv"
QUICK_GATE = {"reps": 400, "B": 300}
QUICK_GATE_BASE = SAMPLE_BASE_RATE  # the quick gates are simulated at the sample ledger's base rate, the headline archive's (round 01, R6 question 5)


def _ver(v: str) -> tuple:
    out = []
    for part in v.split(".")[:3]:
        digits = "".join(ch for ch in part if ch.isdigit())
        out.append(int(digits) if digits else 0)
    return tuple(out)


def _toml_str(value) -> str:
    """A TOML basic string: ``json.dumps`` escapes quotes, backslashes and control characters the way TOML reads them."""
    return json.dumps(str(value), ensure_ascii=False)


def config_text(data_root: Path, cells: list[str], name: str) -> str:
    for label, value in (("name", name), ("data root", str(data_root)), *(("cell", c) for c in cells)):
        if any(ord(ch) < 32 or ord(ch) == 127 for ch in str(value)):
            raise ValueError(f"the project {label} {value!r} holds a control character")
    cell_list = ", ".join(_toml_str(c) for c in cells)
    return f"""# Moot Court project configuration, written by `moot init`.

[project]
name = {_toml_str(name)}

[storage]
data_root = {_toml_str(data_root)}

# The cells the program forecasts: usually one per metric, or per kind of change. `moot doctor` checks that each has history.
[cells]
names = [{cell_list}]

[decision]
# p_sig at or above which the team would act; the card's robustness check asks whether the opinion stays on one side of it.
action_threshold = 0.35

[gate]
# Power at which gate sizes are read from reports/gates.json (0.90 is the release gate). `moot simulate power` uses it.
target_power = 0.90

# Response simulators attach an outside agent as a second opinion, at weight zero until it earns weight on your backtest.
# `moot simulators list` shows the built-ins (null, heuristic). To add a command-line agent, uncomment and edit:
# [simulators.my_agent]
# adapter = "stdio"
# command = ["python3", "path/to/agent.py"]
# version = "0.1"
# knowledge_cutoff = "2025-06-01"    # required: the date the agent's knowledge ends; origins before it are marked contaminated
# cost_model = "free"
# time_cap_s = 20

# Set to check a running service with `moot doctor`:
# [service]
# url = "http://127.0.0.1:8000"
"""


def init_project(directory: Path | str, data_root: Path | str | None = None, cells: list[str] | None = None, name: str | None = None,
                 force: bool = False, progress=None) -> dict:
    """Create the project files in ``directory``. Raises FileExistsError when mootcourt.toml exists and ``force`` is false.

    ``progress`` (a callable taking one line) receives the quick gate simulation's progress lines (call 207)."""
    from mootcourt import simulate
    from mootcourt.importers.sample import METRICS, sample_exchange

    d = Path(directory).resolve()
    cfg = d / CONFIG_FILE
    if cfg.exists() and not force:
        raise FileExistsError(f"{cfg} already exists; pass --force to overwrite it")
    root = Path(data_root).expanduser().resolve() if data_root else d / "mootcourt-data"
    cells = cells or list(METRICS)
    text = config_text(root, cells, name or d.name)         # validates the strings before any folder is created
    d.mkdir(parents=True, exist_ok=True)
    layout = storage_paths(root=root)
    for folder in layout.named().values():
        folder.mkdir(parents=True, exist_ok=True)
    cfg.write_text(text, encoding="utf-8")
    sample = layout.data / SAMPLE_NAME
    sample_exchange().to_csv(sample, index=False)
    gates = layout.gates_path
    if not gates.exists():
        rows_per_test, icc = simulate.SOURCE_DEPENDENCE[QUICK_GATE_BASE]
        simulate.write_gates(gates, base=QUICK_GATE_BASE, base_rates=[QUICK_GATE_BASE], target=load_settings(d)["gate"]["target_power"],
                             reps=QUICK_GATE["reps"], B=QUICK_GATE["B"], with_table=False, rows_per_test=rows_per_test, icc=icc,
                             level=simulate.DEFAULT_LEVEL, progress=progress,
                             dependence_source=f"the public archive at base rate {QUICK_GATE_BASE:.2f} (SOURCE_DEPENDENCE)")
    commands = [f"moot ingest --format generic --input {shlex.quote(str(sample))} --source-name sample",
                "moot fit --source sample && moot backtest --source sample",
                "moot card --source sample --cell checkout_conversion --impressions 20000 --now 2025-12-30T00:00:00+00:00"]
    return {"config": str(cfg), "data_root": str(root), "sample_ledger": str(sample), "gates": str(gates), "gate_replicates": QUICK_GATE["reps"],
            "commands": commands}


# ------------------------------------------------------------------------------------------------ doctor
def _check(name: str, status: str, detail: str) -> dict:
    return {"name": name, "status": status, "detail": detail}


def check_versions() -> list[dict]:
    out = []
    py = sys.version_info[:2]
    out.append(_check("python", OK if py >= MIN_PYTHON else FAIL, f"{sys.version.split()[0]} (needs {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer)"))
    for pkg, minimum in MIN_VERSIONS.items():
        try:
            have = md.version(pkg)
        except md.PackageNotFoundError:
            out.append(_check(f"package {pkg}", FAIL, f"not installed (needs {minimum} or newer)"))
            continue
        out.append(_check(f"package {pkg}", OK if _ver(have) >= _ver(minimum) else FAIL, f"{have} (needs {minimum} or newer)"))
    return out


def check_environment(site_packages: Path | None = None, prefix: Path | None = None) -> list[dict]:
    """Sidecar files (``._name``, which macOS writes beside every file on an exFAT volume) in the active environment (round 01, R6; call 226).

    Looks at the top level of the interpreter's site-packages and under the plotting library's style directory, the two places where they
    first break ``moot backtest``; an environment whose prefix lies on an external volume is a warning before any sidecar appears.
    """
    site = Path(site_packages) if site_packages is not None else Path(sysconfig.get_paths()["purelib"])
    prefix = Path(prefix) if prefix is not None else Path(sys.prefix)
    found = sidecar_files(site) + sidecar_files(site / "matplotlib" / "mpl-data" / "stylelib")
    if found:
        n = len(found)
        return [_check("environment", FAIL, f"{n} sidecar file{'s' if n != 1 else ''} (`._name`) under {site}, for example {found[0].name}: "
                                            "an install on an exFAT volume leaves one beside every file, and `moot backtest` fails on them "
                                            "(the plotting library cannot read its style directory); make the environment on the internal "
                                            f"disk and install there, or delete them: find {site} -name '._*' -type f -delete")]
    if str(prefix).startswith("/Volumes/"):
        return [_check("environment", WARN, f"the environment {prefix} lives on an external volume; if the volume is exFAT, macOS writes `._` "
                                            "sidecar files beside its files and `moot backtest` fails on them; keep the environment on the "
                                            "internal disk")]
    return [_check("environment", OK, f"no sidecar files under {site}")]


def check_storage(paths) -> list[dict]:
    root = paths.root
    if root is not None and not root.exists():
        return [_check("data root", FAIL, f"{root} does not exist; run `moot init` or create it")]
    probe = root if root is not None else Path.cwd()
    free = shutil.disk_usage(probe).free
    detail = f"{root if root is not None else 'repo-local folders'}; free space {human_bytes(free)}"
    if free < LOW_SPACE_BYTES:
        return [_check("data root", WARN, detail + " (under 10 GB; point the root at a larger volume)")]
    return [_check("data root", OK, detail)]


def check_ledger(paths) -> tuple[list[dict], dict[str, str]]:
    """Ledger conformance; also returns the content digest (12 characters) of each source's rows."""
    from mootcourt.importers.ingest import check_ledger_frame
    from mootcourt.ledger import content_digest, read_ledger

    if not paths.ledger_path.exists():
        return [_check("ledger", WARN, f"no ledger at {paths.ledger_path}; import results with `moot ingest`")], {}
    out = []
    viol = check_ledger_frame(paths.ledger_path)
    errs = [v for v in viol if v.severity == "error"]
    if errs:
        out.append(_check("ledger", FAIL, f"{len(errs)} error(s); first: {errs[0]}; run `moot ledger check {paths.ledger_path}`"))
    elif viol:
        out.append(_check("ledger", WARN, f"{len(viol)} warning(s); first: {viol[0]}"))
    else:
        out.append(_check("ledger", OK, f"{paths.ledger_path} conforms"))
    snaps: dict[str, str] = {}
    try:
        df = read_ledger(paths.ledger_path)
        for src in sorted(df["source"].unique()):
            snaps[src] = content_digest(df[df["source"] == src].reset_index(drop=True))[:12]
    except Exception:  # noqa: BLE001  (the schema check above already reported the problem)
        pass
    return out, snaps


def check_models(paths, snaps: dict[str, str]) -> list[dict]:
    from mootcourt.registry import Registry

    out = []
    if not paths.models.exists() or not (paths.models / "registry.json").exists():
        return [_check("models", WARN, "no registry; run `moot fit --source NAME`")]
    reg = Registry(paths.models)
    for src in reg.sources():
        mid = reg.get_champion(src)
        manifest = paths.models / mid / "manifest.json"
        fitted = json.loads(manifest.read_text(encoding="utf-8")).get("snapshot_id") if manifest.exists() else None
        newest = snaps.get(src)
        if fitted is None:
            out.append(_check(f"model {src}", FAIL, f"champion {mid} has no manifest"))
        elif newest and fitted.split("-")[-1] != newest:
            out.append(_check(f"model {src}", WARN, f"champion {mid} was fit on snapshot {fitted}, which no longer matches the ledger; "
                                                   "run `moot fit`"))
        else:
            out.append(_check(f"model {src}", OK, f"champion {mid} on snapshot {fitted}"))
    return out or [_check("models", WARN, "the registry is empty; run `moot fit --source NAME`")]


def _reliability_check(f: Path, now: dt.datetime) -> dict:
    from mootcourt.abstain import staleness_reason

    doc = json.loads(f.read_text(encoding="utf-8"))
    src = doc.get("source", f.stem.split("-", 1)[1])
    # The card judges each cell by the cell's own as_of (call 82), with an exact time comparison, so the doctor does too.
    cells = doc.get("cells") or {}
    stamps = {c: (e.get("as_of") or doc["as_of"]) for c, e in cells.items()} or {"(report)": doc["as_of"]}
    stale = {c: staleness_reason(a, now, RELIABILITY_MAX_AGE_DAYS) for c, a in stamps.items()}
    stale = {c: why for c, why in stale.items() if why}
    oldest = max(((now - dt.datetime.fromisoformat(a)).days for a in stamps.values()), default=0)
    if stale:
        names = ", ".join(sorted(stale))
        return _check(f"reliability {src}", WARN, f"{len(stale)} of {len(stamps)} entries are stale (limit {RELIABILITY_MAX_AGE_DAYS} days, "
                                                 f"oldest {oldest} days old): {names}; those cells abstain until new outcomes "
                                                 "for the cell are joined")
    return _check(f"reliability {src}", OK, f"every entry is within {RELIABILITY_MAX_AGE_DAYS} days (oldest {max(oldest, 0)} days old)")


def check_reliability(paths, now: dt.datetime) -> list[dict]:
    out = []
    files = visible_glob(paths.reports, "reliability-*.json")
    for f in files:
        try:
            out.append(_reliability_check(f, now))
        except (ValueError, KeyError, TypeError, AttributeError, OSError) as exc:       # one bad file is a finding, and the other checks still run
            out.append(_check(f"reliability file {f.name}", FAIL, f"{f.name} is malformed ({type(exc).__name__}: {exc}); "
                                                                  "repair or delete it; `moot backtest` writes a new one"))
    return out or [_check("reliability", WARN, "no reliability report; `moot backtest` seeds one and `moot join` keeps it current")]


def _card_problems(paths, now: dt.datetime) -> dict[str, dict[str, int]]:
    """Per source, the frozen cards no join will score: no row id, a row id absent from the ledger, a row id of an unadmitted test, and a
    horizon that has passed at ``now`` with no outcome file yet (call 252). A card whose row has not concluded is not a finding."""
    import pandas as pd

    from mootcourt.ledger import ADMITTED, read_ledger

    ledger = None
    if paths.ledger_path.exists():
        try:
            ledger = read_ledger(paths.ledger_path).set_index("row_id")
        except Exception:  # noqa: BLE001  (check_ledger reports the cause)
            ledger = None
    out: dict[str, dict[str, int]] = {}
    for f in visible_glob(paths.cards, "*.json"):
        try:
            card = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        c = out.setdefault(str(card.get("source", "unknown")), {"no_row_id": 0, "unknown_row": 0, "past_horizon": 0, "unadmitted": 0})
        row_id = (card.get("request") or {}).get("row_id")
        if not row_id:
            c["no_row_id"] += 1
        elif ledger is None:
            continue
        elif row_id not in ledger.index:
            c["unknown_row"] += 1
        elif ledger.loc[row_id, "status"] != ADMITTED:
            c["unadmitted"] += 1
        elif pd.Timestamp(ledger.loc[row_id, "usable_after"]) <= pd.Timestamp(now) and not (paths.cards / "outcomes" / f"{f.stem}.json").exists():
            c["past_horizon"] += 1
    return out


def check_cards(paths, now: dt.datetime | None = None) -> list[dict]:
    """Per source: scored outcomes, post-hoc cards (issued after their test started, recorded and never scored; a warning, since the record
    was filled after the fact), reissues (a later card for a row another card scores), and the cards no join will score (no row id, a row id
    absent from the ledger, a passed horizon with no outcome, an unadmitted test; each a warning). A source with none of these is not listed."""
    now = now or dt.datetime.now(dt.timezone.utc)
    out_dir = paths.cards / "outcomes"
    counts: dict[str, dict[str, int]] = {}
    for f in visible_glob(out_dir, "*.json"):
        try:
            o = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        c = counts.setdefault(str(o.get("source", "unknown")), {"scored": 0, "post_hoc": 0, "reissue": 0})
        if o.get("post_hoc"):
            c["post_hoc"] += 1
        elif o.get("reissue"):
            c["reissue"] += 1
        elif o.get("scored", True):
            c["scored"] += 1
    problems = {src: p for src, p in _card_problems(paths, now).items() if any(p.values())}
    out = []
    for src in sorted(set(counts) | set(problems)):
        c = counts.get(src, {"scored": 0, "post_hoc": 0, "reissue": 0})
        p = problems.get(src, {})
        detail = (f"{c['scored']} scored outcomes, {c['post_hoc']} post-hoc cards (issued after their test started: recorded, never scored), "
                  f"{c['reissue']} reissues (a later card for a row another card scores)")
        labels = (("no_row_id", "cards with no row id"), ("unknown_row", "cards with a row id absent from the ledger"),
                  ("past_horizon", "cards past their horizon with no outcome"), ("unadmitted", "cards on an unadmitted test"))
        found = [f"{label}: {p[key]}" for key, label in labels if p.get(key)]
        if found:
            detail += "; no join scores these as they stand, " + ", ".join(found)
        out.append(_check(f"cards {src}", WARN if (c["post_hoc"] or found) else OK, detail))
    return out


def check_service(url: str | None, timeout: float = 2.0) -> list[dict]:
    if not url:
        return []
    from mootcourt.simulators.http import _NoRedirect, is_loopback_host

    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https") or not is_loopback_host(parts.hostname):
        return [_check("service", WARN, f"{url} is not a loopback http(s) URL, so it was not contacted; "
                                       "the doctor checks a service on this machine only")]
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect)  # no proxy, no redirect
        with opener.open(url.rstrip("/") + "/health", timeout=timeout) as r:
            return [_check("service", OK if r.status == 200 else FAIL, f"{url} answered {r.status}")]
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return [_check("service", FAIL, f"{url} is not reachable: {exc}")]


def check_cells(configured: list[str], paths) -> list[dict]:
    if not configured or not paths.ledger_path.exists():
        return []
    from mootcourt.ledger import ADMITTED, read_ledger

    try:
        df = read_ledger(paths.ledger_path)
    except Exception:  # noqa: BLE001  (check_ledger reports the cause)
        return []
    have = df[df["status"] == ADMITTED].groupby("cell").size().to_dict()
    thin = [c for c in configured if have.get(c, 0) < 20]
    if thin:
        return [_check("cells", WARN, "cells with fewer than 20 admitted rows: " + ", ".join(f"{c} ({have.get(c, 0)})" for c in thin))]
    return [_check("cells", OK, f"{len(configured)} configured cells, each with 20 or more admitted rows")]


def run_doctor(now: dt.datetime | None = None, write: bool = True) -> dict:
    """Run every check and write ``doctor.json`` under the reports directory. Returns the report."""
    now = now or dt.datetime.now(dt.timezone.utc)
    settings = load_settings()
    paths = storage_paths()
    checks = check_versions() + check_environment() + check_storage(paths)
    ledger_checks, snaps = check_ledger(paths) if (paths.root is None or paths.root.exists()) else ([], {})
    checks += ledger_checks
    if paths.root is None or paths.root.exists():
        checks += check_models(paths, snaps) + check_reliability(paths, now) + check_cells(settings["cells"], paths) + check_cards(paths, now)
    checks += check_service(settings["service"].get("url"))
    def status_of(items):
        return FAIL if any(c["status"] == FAIL for c in items) else (WARN if any(c["status"] == WARN for c in items) else OK)

    report = {"at": now.isoformat(), "status": status_of(checks), "config": settings["path"] if settings["exists"] else None, "checks": checks}
    if write and (paths.reports.exists() or (paths.root is not None and paths.root.exists())):
        try:
            paths.reports.mkdir(parents=True, exist_ok=True)
            (paths.reports / "doctor.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
        except OSError as exc:        # a read-only data root (a volume mounted for another user) is a finding, not a crash
            checks.append(_check("report", WARN, f"could not write {paths.reports / 'doctor.json'}: {exc}"))
            report["status"] = status_of(checks)
    return report


def exit_code(report: dict) -> int:
    """0 healthy, 1 warnings, 2 failures."""
    return {OK: 0, WARN: 1, FAIL: 2}[report["status"]]
