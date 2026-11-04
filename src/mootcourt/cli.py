"""Command line entry point for Moot Court (``moot``)."""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import threading
import time
from pathlib import Path

import typer
import typer.core

from mootcourt import __version__
from mootcourt.config import BOOTSTRAP_RESAMPLES, EARN_WEIGHT_MARGIN, PROMOTION_MARGIN
from mootcourt.storage import storage_paths, visible_glob

DEFAULT_SERVE_HOST = "127.0.0.1"
DEFAULT_SERVE_PORT = 8000

def _user_error_types() -> tuple[type, ...]:
    """Errors that mean "the input or the files are wrong", not "the program is broken": the package's own error types, bad values
    (ValueError) and unreadable or missing files (OSError). Imported lazily so ``moot --help`` stays fast."""
    from mootcourt.bundle import BundleIntegrityError
    from mootcourt.harness import LeakageError
    from mootcourt.service import UnknownSourceError
    from mootcourt.simulate import PowerBudgetExceeded
    from mootcourt.storage import SidecarEnvironmentError

    return (ValueError, OSError, BundleIntegrityError, LeakageError, PowerBudgetExceeded, UnknownSourceError, SidecarEnvironmentError)


class Heartbeat:
    """Prints "<what>: still running, N s elapsed" to standard error after ``delay`` seconds and every ``every`` seconds until the block
    ends, so a command that takes long on a slow volume is never silent (round 01, R6; call 207). ``echo`` replaces the printer."""

    def __init__(self, what: str, delay: float = 10.0, every: float = 10.0, echo=None):
        self.what, self.delay, self.every = what, float(delay), float(every)
        self.echo = echo or (lambda line: typer.echo(line, err=True))
        self._stop = threading.Event()
        self._t0 = time.perf_counter()
        self._thread: threading.Thread | None = None

    def elapsed(self) -> float:
        return time.perf_counter() - self._t0

    def past_delay(self) -> bool:
        return self.elapsed() >= self.delay

    def _run(self) -> None:
        if self._stop.wait(self.delay):
            return
        while True:
            self.echo(f"{self.what}: still running, {self.elapsed():.0f} s elapsed")
            if self._stop.wait(self.every):
                return

    def __enter__(self):
        self._t0 = time.perf_counter()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        return False


def _describe_error(exc: BaseException) -> str:
    if isinstance(exc, KeyError) and exc.args:
        return str(exc.args[0])
    if isinstance(exc, OSError) and getattr(exc, "filename", None):
        return f"{exc.filename}: {exc.strerror or exc}"
    return str(exc) or type(exc).__name__


class _FriendlyGroup(typer.core.TyperGroup):
    """The root command group: an input error ends in one line on standard error and exit code 2, not a traceback.

    Set ``MOOTCOURT_DEBUG=1`` to get the traceback instead. Usage errors (``typer.BadParameter``) and ``typer.Exit`` pass through unchanged.
    """

    def invoke(self, ctx):
        try:
            return super().invoke(ctx)
        except Exception as exc:
            if os.environ.get("MOOTCOURT_DEBUG") or not isinstance(exc, _user_error_types()):
                raise
            typer.echo(f"error: {_describe_error(exc)}", err=True)
            raise typer.Exit(code=2) from None


app = typer.Typer(
    cls=_FriendlyGroup,
    name="moot",
    help="Moot Court: argue the next experiment from precedent before the trial.",
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True, help="Print the version and exit."
    ),
) -> None:
    """Moot Court command line."""


_TRUE = {"true", "yes", "1", "y"}
_FALSE = {"false", "no", "0", "n"}


def _parse_bool(value: str, name: str) -> bool:
    low = value.strip().lower()
    if low in _TRUE:
        return True
    if low in _FALSE:
        return False
    raise typer.BadParameter(f"{name} must be true or false, got {value!r}")


def _parse_time(value: str | None, name: str) -> dt.datetime | None:
    if value is None:
        return None
    try:
        t = dt.datetime.fromisoformat(value)
    except ValueError:
        raise typer.BadParameter(f"{name} {value!r} is not an ISO-8601 time, for example 2014-07-15T12:00:00+00:00") from None
    if t.tzinfo is None:
        raise typer.BadParameter(f"{name} needs a UTC offset, for example 2014-07-15T12:00:00+00:00")
    return t


def resolve_model_id(models_dir: Path, source: str, model_id: str | None = None) -> str:
    """The model to serve for a source: an explicit id, else the registry champion, else the newest fitted bundle."""
    if model_id:
        return model_id
    try:
        from mootcourt.registry import Registry  # the registry arrives with the operations tasks
    except ImportError:
        Registry = None  # noqa: N806
    if Registry is not None:
        try:
            return Registry(models_dir).get_champion(source)
        except KeyError:
            pass
    best = None
    for manifest in visible_glob(models_dir, "*/manifest.json"):
        m = json.loads(manifest.read_text(encoding="utf-8"))
        if m.get("source") == source and (best is None or m["fit_time"] > best["fit_time"]):
            best = m
    if best is None:
        raise typer.BadParameter(f"no fitted model for source {source} in {models_dir}; run `moot fit` first")
    return best["model_id"]


@app.command()
def card(
    source: str = typer.Option(..., "--source", help="Data source: upworthy, asos or synthetic."),
    headline: str = typer.Option("", "--headline", help="Proposed headline (text sources; leave out for ledgers without headline text)."),
    image_changed: str = typer.Option("false", "--image-changed", help="true or false."),
    impressions: int = typer.Option(
        ..., "--impressions", help="Planned units per arm; the reference arm's when --impressions-variant is given."
    ),
    impressions_variant: int | None = typer.Option(
        None, "--impressions-variant", help="Planned exposures of the variant arm; default: the same as --impressions."
    ),
    origin: str | None = typer.Option(None, "--origin", help="ISO-8601 time with offset; default now."),
    models_dir: Path | None = typer.Option(None, "--models-dir", help="Default: the storage root."),
    cards_dir: Path | None = typer.Option(None, "--cards-dir", help="Default: the storage root."),
    reports_dir: Path | None = typer.Option(None, "--reports-dir", help="Default: the storage root."),
    now: str | None = typer.Option(None, "--now", help="Issue time (ISO-8601 with offset); default now."),
    row_id: str | None = typer.Option(None, "--row-id", help="Ledger row the weekly join will attach the outcome to (source:test_id:variant_id)."),
    test_id: str | None = typer.Option(None, "--test-id", help="With --variant-id: the ledger row key, instead of --row-id."),
    variant_id: str | None = typer.Option(None, "--variant-id", help="With --test-id: the ledger row key, instead of --row-id."),
    model_id: str | None = typer.Option(None, "--model-id", help="Model to use; default the registry champion."),
    cell: str | None = typer.Option(None, "--cell", help="Primary metric's cell (needed for metric-keyed sources)."),
    guardrail: list[str] | None = typer.Option(None, "--guardrail", help="Guardrail as CELL:DELTA (harm margin above zero); repeat."),
    headline_changed: str = typer.Option("true", "--headline-changed", help="true or false."),
    as_json: bool = typer.Option(False, "--json", help="Print the card as JSON instead of Markdown."),
    verbose: bool = typer.Option(False, "--verbose", help="Print timings to standard error."),
    simulator: str | None = typer.Option(None, "--simulator", help="Attach a response simulator (see `moot simulators list`) as a second opinion."),
    reference_headline: str = typer.Option(
        "", "--reference-headline", help="Reference arm's headline: read by a pairwise feature space and passed to a simulator."
    ),
    sim_config: Path | None = typer.Option(None, "--sim-config", help="Config file with [simulators.*] tables; default mootcourt.toml."),
    allow_remote: bool = typer.Option(False, "--allow-remote", help="Allow an http simulator on a non-loopback host."),
) -> None:
    """Issue a card for a proposed experiment and freeze it under the cards directory."""
    paths = storage_paths()
    models_dir = models_dir if models_dir is not None else paths.models
    cards_dir = cards_dir if cards_dir is not None else paths.cards
    reports_dir = reports_dir if reports_dir is not None else paths.reports
    from mootcourt import card as card_mod
    from mootcourt.bundle import load_bundle

    t0 = time.perf_counter()
    mid = resolve_model_id(models_dir, source, model_id)
    bundle = load_bundle(mid, models_dir)
    t_load = time.perf_counter() - t0
    now_t = _parse_time(now, "--now") or dt.datetime.now(dt.timezone.utc)
    from mootcourt.ledger import resolve_row_id

    try:
        resolved_row = resolve_row_id(source, row_id, test_id, variant_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from None
    request = card_mod.CardRequest(
        source=source, headline=headline, image_changed=_parse_bool(image_changed, "--image-changed"),
        impressions=impressions, origin=_parse_time(origin, "--origin") or now_t, row_id=resolved_row,
        headline_changed=_parse_bool(headline_changed, "--headline-changed"), cell=cell,
        guardrails=tuple(_parse_guardrail(g) for g in (guardrail or [])), reference_headline=reference_headline,
        impressions_variant=impressions_variant,
    )
    report = card_mod.load_reliability_report(reports_dir, source)
    from mootcourt.settings import abstain_config

    cfg = abstain_config()
    gates = _load_gates_or_none(reports_dir)
    issued, t_issue = card_mod.time_issue(bundle, request, report, now_t, config=cfg, gates=gates)
    if simulator is not None:
        issued = _attach_simulator(issued, simulator, source, models_dir, reference_headline, sim_config, allow_remote, paths.cache)
    try:
        frozen = card_mod.freeze_or_load(issued, cards_dir)   # the card id covers the content; a clash fails loudly
    except card_mod.CardFrozenError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    if verbose:
        print(f"bundle load {t_load:.3f} s (once per process), issue {t_issue:.3f} s with the bundle in memory", file=sys.stderr)
    if as_json:
        # the sealed forecast of an abstained card stays in the file
        typer.echo(json.dumps(card_mod.public_json(frozen), indent=1, sort_keys=True))
    else:
        typer.echo(card_mod.to_markdown(issued))


def _load_gates_or_none(reports_dir: Path):
    """The gates of the reports folder for the card's skill line, or None when there is no gates.json (the line then says so)."""
    from mootcourt import simulate

    try:
        return simulate.load_gates(Path(reports_dir) / "gates.json")
    except FileNotFoundError:
        return None


def _parse_guardrail(text: str):
    from mootcourt.card import Guardrail

    cell, sep, delta = text.rpartition(":")
    try:
        d = float(delta)
    except ValueError:
        d = float("nan")
    if not sep or not cell or not d > 0 or d == float("inf"):
        raise typer.BadParameter(f"--guardrail must be CELL:DELTA with DELTA above zero and finite, got {text!r}")
    return Guardrail(cell, d)


def _attach_simulator(issued, name, source, models_dir, reference_headline, sim_config, allow_remote, cache_root):
    """Ask the named simulator about the card's request (through the cache) and attach its opinion with the weight in force."""
    from mootcourt import card as card_mod
    from mootcourt.registry import Registry
    from mootcourt.simulators import SimulationRequest, SimulatorError
    from mootcourt.simulators.cache import SimulationCache
    from mootcourt.simulators.loader import get_simulator
    from mootcourt.simulators.runner import RequestItem, run

    try:
        sim = get_simulator(name, sim_config, allow_remote=allow_remote)
        r = issued.request
        req = SimulationRequest(source=source, cell=issued.cell, origin=issued.origin, reference_headline=reference_headline,
                                variant_headline=r.headline, image_changed=r.image_changed, headline_changed=r.headline_changed,
                                planned_n_ref=r.impressions, planned_n_var=r.impressions_variant or r.impressions, s_star=r.s_star,
                                action_threshold=issued.robustness.action_threshold)
    except SimulatorError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    info = sim.describe()
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "one.jsonl"
        run(sim, [RequestItem(r.row_id or "card", issued.origin, req)], out, SimulationCache(Path(cache_root) / "simulators"))
        rec = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    p_ai = None if rec["declined"] else float(rec["result"]["p_win_ai"])
    try:
        stored = Registry(models_dir).get_second_opinion(source, info.provider_id, info.version)
    except (OSError, ValueError):
        stored = None
    weight, contaminated = (float(stored["weight"]), bool(stored.get("contaminated"))) if stored else (0.0, False)
    return card_mod.with_second_opinion(issued, info.provider_id, info.version, info.knowledge_cutoff, p_ai, weight, contaminated)


def _load_source_ledger(ledger_path: Path, source: str):
    """Rows of one source from the ledger file; a clear error when the file or the source is missing."""
    from mootcourt.ledger import read_ledger

    if not ledger_path.exists():
        raise typer.BadParameter(
            f"{ledger_path} does not exist; build the ledger first (for the synthetic source: `moot simulate ledger --out {ledger_path}`)")
    df = read_ledger(ledger_path)
    df = df[df["source"] == source].reset_index(drop=True)
    if df.empty:
        raise typer.BadParameter(f"the ledger {ledger_path} has no rows for source {source}")
    return df


def _model_identity(df, source: str, snapshot_id: str, models_dir: Path) -> tuple[str, str]:
    """Model id and feature hash of the bundle for this snapshot: an existing one, else a fit that is not saved."""
    for manifest in visible_glob(models_dir, "*/manifest.json"):
        m = json.loads(manifest.read_text(encoding="utf-8"))
        if m.get("source") == source and m.get("snapshot_id") == snapshot_id:
            return m["model_id"], m["feature_hash"]
    from mootcourt.bundle import fit_bundle

    b = fit_bundle(df, source, snapshot_id)
    return b.model_id, b.feature_hash


def _require_fittable(df) -> None:
    """End in one line, naming the minimum, when no quarter has enough admitted rows usable before it starts (a ledger too small to backtest)."""
    from mootcourt.harness import MIN_FIT_ROWS, quarterly_origins
    from mootcourt.ledger import ADMITTED, visible_rows

    adm = df[df["status"] == ADMITTED]
    ok = len(adm) and any(len(visible_rows(adm, t)) >= MIN_FIT_ROWS for t in quarterly_origins(df))
    if not ok:
        raise typer.BadParameter(f"the ledger is too small to backtest: {len(adm)} admitted rows, and a quarter is scored only when at least "
                                 f"{MIN_FIT_ROWS} admitted rows are usable before it starts")


def _parse_guard(value: str | None):
    """``--p2-guard`` as the value P2 takes: None (the config default) is returned as the string ``"default"``, ``off`` as None."""
    if value is None:
        return "default"
    if value.strip().lower() in ("off", "none"):
        return None
    try:
        g = float(value)
    except ValueError:
        raise typer.BadParameter("--p2-guard must be 'off' or a nonnegative multiplier of the standard error") from None
    if g < 0:
        raise typer.BadParameter("--p2-guard must be 'off' or a nonnegative multiplier of the standard error")
    return g


def _variant_settings(features, bandwidth_mult, lam, kappa, prior, p2_selection, recency, effect_scale="absolute", s_star="prelaunch",
                      p2_guard="default", drop_triggers=(), admission="realized", pairwise="on", contrasts="all") -> dict:
    """The ablation settings that differ from the defaults, as a dict; empty for the main run."""
    from mootcourt.config import KAPPA, P2_GUARD_MULT, P2_SELECTION_DEFAULT

    v: dict = {}
    if features != "both":
        v["features"] = features
    if bandwidth_mult is not None:
        v["bandwidth_mult"] = bandwidth_mult
    if lam is not None:
        v["lambda"] = lam
    if kappa is not None and kappa != KAPPA:
        v["kappa"] = kappa
    if prior != "t":
        v["prior"] = prior
    if p2_selection is not None and p2_selection != P2_SELECTION_DEFAULT:
        v["p2_selection"] = p2_selection
    if recency is not None:
        v["recency"] = recency
    if p2_guard != "default" and p2_guard != P2_GUARD_MULT:
        v["p2_guard"] = "off" if p2_guard is None else p2_guard
    if effect_scale != "absolute":
        v["effect_scale"] = effect_scale
    if s_star != "prelaunch":
        v["s_star"] = s_star
    if drop_triggers:
        v["drop_trigger"] = sorted(set(drop_triggers))
    if admission != "realized":
        v["admission"] = admission
    if pairwise != "on":
        v["pairwise"] = pairwise
    if contrasts != "all":
        v["contrasts"] = contrasts
    if "p2_guard" in v:                      # last, so a run with the guard off is always named `<ablation>+p2-guard-off` (call 176)
        v["p2_guard"] = v.pop("p2_guard")
    return v


def _variant_name(v: dict) -> str:
    """File-name suffix of a variant, for example ``features-text`` or ``p2-selection-forward+recency-select``."""
    return "+".join(f"{k.replace('_', '-')}-{'-'.join(val) if isinstance(val, list) else val}" for k, val in v.items())


def _variant_flags(v: dict) -> str:
    """The command-line flags that reproduce a variant; a list (``--drop-trigger``) is one flag per name."""
    return "".join(f" --{k.replace('_', '-')} {x}" for k, val in v.items() for x in (val if isinstance(val, list) else [val]))


@app.command()
def backtest(
    source: str = typer.Option(..., "--source", help="Data source: upworthy, asos or synthetic."),
    origins: str = typer.Option("quarterly", "--origins", help="Only quarterly is supported."),
    challenger: list[str] | None = typer.Option(None, "--challenger", help="Challenger rungs: gbm, local_eb, text_lr."),
    seed: int = typer.Option(0, "--seed"),
    second_opinion: Path | None = typer.Option(
        None, "--second-opinion", help="Records file from `moot simulators run`: adds the agent and stacked rungs."
    ),
    bootstrap: int = typer.Option(500, "--bootstrap", help="Bootstrap resamples (by test) for every interval."),
    features: str = typer.Option("both", "--features", help="Ablation: text, structured or both."),
    bandwidth_mult: float | None = typer.Option(None, "--bandwidth-mult", help="Ablation: fix the P2 bandwidth multiplier."),
    lam: float | None = typer.Option(None, "--lambda", help="Ablation: fix the P2 weight on precedents."),
    kappa: float | None = typer.Option(None, "--kappa", help="Ablation: P1 pooling strength."),
    prior: str = typer.Option("t", "--prior", help="Ablation: P1 prior family, t or normal."),
    p2_selection: str | None = typer.Option(
        None, "--p2-selection", help="How P2 chooses lambda and bandwidth: forward (default) or loto (leave one test out)."
    ),
    recency: str | None = typer.Option(None, "--recency", help="Time kernel for P2: select, or a half-life in days."),
    p2_guard: str | None = typer.Option(None, "--p2-guard", help="Ablation: P2 admission guard multiplier, or off."),
    effect_scale: str = typer.Option("absolute", "--effect-scale", help="absolute (default) or relative: the cautionary first run (Upworthy only)."),
    drop_trigger: list[str] | None = typer.Option(
        None, "--drop-trigger", help="Ablation: switch an abstention trigger off (support, novelty, reliability or instability); repeatable."
    ),
    s_star: str = typer.Option("prelaunch", "--s-star", help="prelaunch (default) or realized: feed the realized standard error (cautionary run)."),
    admission: str = typer.Option(
        "realized",
        "--admission",
        help="realized (default: the ledger's statuses, including the minimum-clicks rule on realized clicks) "
        "or prelaunch: admit on exposure only, every contrast with a finite standard error (ablation).",
    ),
    contrasts: str = typer.Option(
        "all",
        "--contrasts",
        help="all (default) or one: keep one admitted contrast per test (the lowest row id), so a test has one headline against its reference "
        "(ablation of the arm-count structure, round 01 R3 minor 6).",
    ),
    pairwise: str = typer.Option(
        "on",
        "--pairwise",
        help="on (default): the feature space and the challengers read the reference headline where the ledger has one; "
        "off: the variant headline only.",
    ),
    recalibrate: bool = typer.Option(
        True, "--recalibrate/--no-recalibrate", help="Add a recalibrated rung (+cal) for every challenger, fit on visible rows only."
    ),
    recalibration: str = typer.Option("platt", "--recalibration", help="Map of the recalibrated rungs: platt or isotonic."),
    local_k: int = typer.Option(50, "--local-k", help="Neighbors used by the local_eb challenger."),
    primary_metric: str | None = typer.Option(None, "--primary-metric", help="Multi-metric ledgers: the metric the decision value uses."),
    baselines: bool = typer.Option(True, "--baselines/--no-baselines", help="Score the always_reference and always_variant baselines."),
    learning_curve: str | None = typer.Option(None, "--learning-curve", help="Comma-separated history fractions, for example 0.1,0.25,0.5,1."),
    seeds: int = typer.Option(3, "--seeds", help="Random history subsamples per fraction in the learning curve."),
    ledger_path: Path | None = typer.Option(None, "--ledger", help="Default: the storage root."),
    reports_dir: Path | None = typer.Option(None, "--reports-dir", help="Default: the storage root."),
    models_dir: Path | None = typer.Option(None, "--models-dir", help="Default: the storage root."),
    verbose: bool = typer.Option(False, "--verbose", help="Print one line per origin to standard error."),
    progress_after: float = typer.Option(10.0, "--progress-after", help="Seconds after which progress lines go to standard error."),
) -> None:
    """Rolling-origin backtest at calendar quarter starts; writes the report, figures and score table."""
    paths = storage_paths()
    ledger_path = ledger_path if ledger_path is not None else paths.ledger_path
    reports_dir = reports_dir if reports_dir is not None else paths.reports
    models_dir = models_dir if models_dir is not None else paths.models
    from mootcourt import simulate
    from mootcourt.config import P2_SELECTIONS
    from mootcourt.features import FEATURE_SETS
    from mootcourt.harness import PRIOR_KINDS, default_rungs, parse_challengers, quarterly_origins, rolling_origin
    from mootcourt.ledger import ensure_snapshot
    from mootcourt.registry import attach_backtest, date_seed_at_champion_fit
    from mootcourt.report import write_report

    if origins != "quarterly":
        raise typer.BadParameter("only --origins quarterly is supported")
    for name, value, allowed in (("--features", features, FEATURE_SETS), ("--prior", prior, PRIOR_KINDS),
                                 ("--p2-selection", p2_selection, P2_SELECTIONS)):
        if value is not None and value not in allowed:
            raise typer.BadParameter(f"{name} must be one of {', '.join(allowed)}")
    if recency not in (None, "select"):
        try:
            if float(recency) <= 0:
                raise ValueError
            recency_arg: str | float | None = float(recency)
        except ValueError:
            raise typer.BadParameter("--recency must be 'select' or a half-life in days") from None
    else:
        recency_arg = recency
    try:
        names = parse_challengers(challenger)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from None
    for name, value, allowed in (("--effect-scale", effect_scale, ("absolute", "relative")), ("--s-star", s_star, ("prelaunch", "realized")),
                                 ("--admission", admission, ("realized", "prelaunch")), ("--recalibration", recalibration, ("platt", "isotonic")),
                                 ("--pairwise", pairwise, ("on", "off")), ("--contrasts", contrasts, ("all", "one"))):
        if value not in allowed:
            raise typer.BadParameter(f"{name} must be one of {', '.join(allowed)}")
    if effect_scale == "relative" and source != "upworthy":
        raise typer.BadParameter("--effect-scale relative needs the Upworthy source (it reads the relative lift stored with each row)")
    guard_arg = _parse_guard(p2_guard)
    from mootcourt.abstain import TRIGGERS

    for name in drop_trigger or []:
        if name not in TRIGGERS:
            raise typer.BadParameter(f"--drop-trigger must be one of {', '.join(TRIGGERS)}; got {name!r}")
    variant = _variant_settings(features, bandwidth_mult, lam, kappa, prior, p2_selection, recency, effect_scale, s_star, guard_arg,
                                tuple(drop_trigger or ()), admission, pairwise, contrasts)
    t0 = time.perf_counter()
    df = _load_source_ledger(ledger_path, source)
    sid = ensure_snapshot(df, ledger_path.parent)
    gates_path = reports_dir / "gates.json"
    if not gates_path.exists():
        typer.echo(f"{gates_path} is missing; running the gate power simulation first (synthetic data, same as `moot simulate power`)")
        from mootcourt.settings import load_settings

        simulate.write_gates(gates_path, target=load_settings()["gate"]["target_power"])      # the configured power (REV-045)
    gates = simulate.load_gates(gates_path)
    typer.echo(f"gates read from {gates_path.resolve()}: {json.dumps({k: v for k, v in gates.items() if k != 'by_base_rate'}, sort_keys=True)}")
    if gates.get("by_base_rate"):
        typer.echo(
            "gate sizes by base rate (tests): "
            + "; ".join(f"{b:.2f}: n_200 {v['n_200']}, n_400 {v['n_400']}" for b, v in sorted(gates["by_base_rate"].items()))
        )
    else:
        typer.echo(
            f"note: these gates were simulated at one base rate ({gates.get('base_rate', 'unrecorded')}); "
            "run `moot simulate gate-power` to size them "
            "by test at the base rate of your archive"
        )
    settings = dict(
        features=features,
        bandwidth_mult=bandwidth_mult,
        lam=lam,
        prior=prior,
        p2_selection=p2_selection,
        recency=recency_arg,
        local_k=local_k,
        recalibrate=recalibrate,
        recalibration=recalibration,
        **({"pairwise": False} if pairwise == "off" else {}),
        **({"kappa": kappa} if kappa is not None else {}),
        **({} if guard_arg == "default" else {"p2_guard": guard_arg}),
    )

    def make_rungs(frame):
        try:
            return default_rungs(source, frame, names, baselines=baselines, **settings)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from None

    command = f"moot backtest --source {source} --origins {origins}" + "".join(f" --challenger {n}" for n in names)
    command += _variant_flags(variant) + f" --seed {seed}"
    if admission == "prelaunch":          # before the learning curve too: the curve must be on the admission its recorded command says
        from mootcourt.scale import prelaunch_admission_ledger

        before = int((df["status"] == "admitted").sum())
        df = prelaunch_admission_ledger(df)         # a view, like the cautionary run: the snapshot id above is the stored ledger's
        typer.echo(f"admission on exposure only: {int((df['status'] == 'admitted').sum()) - before} contrasts admitted "
                   "that the realized-clicks rule excluded")
    if contrasts == "one":
        from mootcourt.scale import one_contrast_per_test_ledger

        n_before = int((df["status"] == "admitted").sum())
        df = one_contrast_per_test_ledger(df)         # a view: the snapshot id above is the stored ledger's
        typer.echo(f"one contrast per test: {int((df['status'] == 'admitted').sum())} of {n_before} admitted contrasts kept")
    if learning_curve is not None:
        from mootcourt.learning_curve import parse_fractions, run_learning_curve, write_learning_curve

        try:
            fractions = parse_fractions(learning_curve)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from None
        doc = run_learning_curve(df, source, make_rungs, fractions, seeds, gates, B=bootstrap, seed=seed, verbose=verbose)
        doc["command"] = command + f" --learning-curve {learning_curve} --seeds {seeds}"
        wrote = write_learning_curve(doc, reports_dir, sid)
        typer.echo(f"learning curve over {len(fractions)} fractions, {seeds} seeds, final origin {doc['final_origin']}, "
                   f"{doc['heldout_rows']} held-out rows, in {time.perf_counter() - t0:.1f} s")
        typer.echo("\n".join(f"wrote {p}" for p in wrote.values()))
        return
    _require_fittable(df)
    model_id, feature_hash = _model_identity(df, source, sid, models_dir)
    if effect_scale == "relative":
        from mootcourt.scale import relative_lift_ledger

        df = relative_lift_ledger(df)          # after the snapshot id: this is a view for the cautionary run, not a new ledger
        typer.echo("cautionary run: y is the relative lift in percent and s its standard error")
    if s_star == "realized":
        typer.echo("cautionary run: the forecaster is given each row's realized standard error")
    with Heartbeat(f"backtest of {source}", delay=progress_after) as beat:
        scores = rolling_origin(df, make_rungs(df), quarterly_origins(df), source=source, verbose=verbose, s_star_mode=s_star,
                                drop_triggers=tuple(drop_trigger or ()),
                                progress=lambda line: typer.echo(f"progress: {line}", err=True) if beat.past_delay() and not verbose else None)
    t_scored = time.perf_counter() - t0
    if scores.empty:
        from mootcourt.harness import MIN_FIT_ROWS as _MIN

        n_adm = int((df["status"] == "admitted").sum())
        raise typer.BadParameter(f"the ledger is too small to backtest: {n_adm} admitted rows, and a quarter is scored only when at least {_MIN} "
                                 "admitted rows are usable before it starts")
    so_meta, out_dir, suffix, main_run = None, reports_dir, "", True
    if variant:
        out_dir, suffix, main_run = reports_dir / "ablations", _variant_name(variant), False
    if second_opinion is not None:
        from mootcourt.registry import Registry
        from mootcourt.simulators import SimulatorError
        from mootcourt.simulators.scoring import add_agent_rungs, load_second_opinion

        try:
            data = load_second_opinion(second_opinion)
            stored = Registry(models_dir).get_second_opinion(source, data.provider_id, data.version)
            weight, w_contaminated = (float(stored["weight"]), bool(stored.get("contaminated"))) if stored else (0.0, False)
            scores, so_meta = add_agent_rungs(scores, df, data, weight, weight_contaminated=w_contaminated)
        except SimulatorError as exc:
            raise typer.BadParameter(str(exc)) from None
        command += f" --second-opinion {second_opinion.name}"
        out_dir, suffix, main_run = reports_dir / f"second-opinion-{data.provider_id}", "second-opinion", False
        typer.echo(f"second opinion {data.provider_id} {data.version}: weight in force {weight}, "
                   f"{so_meta['n_with_opinion']} of {so_meta['n_rows']} rows with an opinion, {so_meta['n_declined']} declined, "
                   f"{so_meta['n_failed']} failed calls, {so_meta['n_missing']} absent from the file")
    reference, reference_files = None, None
    released_note = None
    if drop_trigger and (set(variant) != {"drop_trigger"} or second_opinion is not None):
        # The released rows compare with the main run's scores, which equal this run's only when the dropped trigger is the one change (REV-J-001).
        released_note = ("Released rows are not computed: this run changes another setting besides the dropped trigger, so its scores "
                         "differ from the main run's and the rows the trigger released cannot be isolated.")
        typer.echo(released_note)
    elif drop_trigger and not main_run:
        main_scores = reports_dir / f"scores-{source}-{sid}.parquet"
        if main_scores.exists():
            import pandas as pd

            reference = pd.read_parquet(main_scores)
            reference_files = {"main_scores": main_scores.name, "main_report": f"backtest-{source}-{sid}.json"}
        else:
            typer.echo(f"no main run's scores at {main_scores}: the report prints no released rows (run `moot backtest --source {source}` first)")
    paths = write_report(scores, ledger=df, source=source, snapshot_id=sid, model_id=model_id, feature_hash=feature_hash,
                         command=command, seed=seed, gates=gates, out_dir=out_dir, B=bootstrap, second_opinion=so_meta,
                         extra_notes={"released_rows_skipped": released_note} if released_note else None, suffix=suffix, main=main_run,
                         variant=variant or None, primary_metric=primary_metric,
                         reference_scores=reference, reference_files=reference_files)
    if main_run:
        attached = attach_backtest(models_dir, source, sid, json.loads(paths.json.read_text(encoding="utf-8")), paths.json.name)
        if attached:
            typer.echo(f"filled the backtest summary of model {', '.join(attached)}")
        date_seed_at_champion_fit(models_dir, out_dir, source)
    typer.echo(f"scored {scores['row_id'].nunique()} rows over {scores['origin'].nunique()} origins in {t_scored:.1f} s "
               f"(report writing {time.perf_counter() - t0 - t_scored:.1f} s; the whole run {time.perf_counter() - t0:.1f} s)")
    typer.echo(f"wrote {paths.md}\nwrote {paths.json}\nwrote {paths.scores}")


@app.command()
def fit(
    source: str = typer.Option(..., "--source", help="Data source: upworthy, asos or synthetic."),
    ledger_path: Path | None = typer.Option(None, "--ledger", help="Default: the storage root."),
    models_dir: Path | None = typer.Option(None, "--models-dir", help="Default: the storage root."),
    reports_dir: Path | None = typer.Option(None, "--reports-dir", help="Default: the storage root."),
    now: str | None = typer.Option(None, "--now", help="Fit clock (ISO-8601 with offset): only rows usable at this instant enter the fit; "
                                                       "default now."),
) -> None:
    """Fit P0, P1 and P2 on the rows usable at the fit clock, at the current ledger snapshot; save the bundle and register it."""
    paths = storage_paths()
    ledger_path = ledger_path if ledger_path is not None else paths.ledger_path
    models_dir = models_dir if models_dir is not None else paths.models
    reports_dir = reports_dir if reports_dir is not None else paths.reports
    from mootcourt.ledger import visible_rows
    from mootcourt.registry import fit_command

    t0 = time.perf_counter()
    df = _load_source_ledger(ledger_path, source)
    clock = _parse_time(now, "--now") or dt.datetime.now(dt.timezone.utc)
    n_usable = len(visible_rows(df, clock)) if "status" in getattr(df, "columns", ()) else None
    model_id, sid, role, summary = fit_command(source, df, ledger_path.parent, models_dir, reports_dir, now=clock)
    usable = f" on {n_usable} rows usable at {clock.isoformat()}" if n_usable is not None else ""
    typer.echo(f"fitted model {model_id} at snapshot {sid}{usable} in {time.perf_counter() - t0:.1f} s; it is the {role} for {source}")
    from mootcourt.registry import Registry

    if summary is None and Registry(models_dir).pending_refresh(source) == model_id:
        typer.echo("a refresh of the champion is pending: same method, newer data; `moot backtest` decides it (no further `moot fit`)")
    elif summary is None:
        typer.echo("no backtest exists for this snapshot, so the backtest summary slot is empty; run `moot backtest` then `moot fit`")
    else:
        typer.echo(f"backtest summary filled from {summary['report']}: Brier skill {summary['brier_skill']:.4f} at n = {summary['n']}")


@app.command()
def ingest(
    source: str = typer.Option("all", "--source", help="upworthy, asos, synthetic or all."),
    raw_dir: Path | None = typer.Option(None, "--raw-dir", help="Where scripts/download_data.py put the files; default: the storage root."),
    ledger_path: Path | None = typer.Option(None, "--ledger", help="Default: the storage root."),
    synthetic: bool = typer.Option(True, "--synthetic/--no-synthetic", help="With --source all, also add the synthetic ledger."),
    n_tests: int = typer.Option(1000, "--n-tests", help="Synthetic tests."),
    seed: int = typer.Option(0, "--seed", help="Synthetic seed."),
    fmt: str | None = typer.Option(None, "--format", help="Import a results export instead: see `moot ledger formats`. Needs --input."),
    input_file: Path | None = typer.Option(None, "--input", help="The export file (CSV, Parquet or JSON) for --format."),
    source_name: str = typer.Option("ledger", "--source-name", help="Source name given to imported rows."),
    mapping: Path | None = typer.Option(None, "--mapping", help="TOML mapping file (columns, constants, options) for generic and template formats."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the admission summary of an import and write nothing."),
    experiment_id: str | None = typer.Option(None, "--experiment-id", help="Experiment id for exports that carry none."),
    ci_level: float | None = typer.Option(None, "--ci-level", help="Confidence level of the exported intervals when the format does not state it."),
    effect_scale: str | None = typer.Option(None, "--effect-scale-import", help="absolute or relative, for formats that export both."),
    started_at: str | None = typer.Option(None, "--started-at", help="Start time for exports without dates (ISO-8601)."),
    ended_at: str | None = typer.Option(None, "--ended-at", help="End time for exports without dates (ISO-8601)."),
    n_baseline: int | None = typer.Option(None, "--n-baseline", help="Baseline units for exports without counts."),
    n_variant: int | None = typer.Option(None, "--n-variant", help="Variant units for exports without counts."),
    engine: str | None = typer.Option(None, "--engine", help="Analysis engine to read when an export holds several: frequentist or bayesian."),
    analysis_basis: str | None = typer.Option(None, "--analysis-basis", help="Jetstream tables: enrollments (default) or exposures."),
    min_exposure: int = typer.Option(100, "--min-exposure", help="Imports: fewer units than this in an arm makes the row low_exposure."),
    usable_delay_days: float = typer.Option(0.0, "--usable-delay-days", help="Imports: days after the end before a row may be used."),
) -> None:
    """Build the shared ledger from the downloaded files, or import a results export. Idempotent: rows already present are unchanged."""
    paths = storage_paths()
    raw_dir = raw_dir if raw_dir is not None else paths.raw
    ledger_path = ledger_path if ledger_path is not None else paths.ledger_path
    if fmt is not None or input_file is not None:
        _ingest_export(fmt, input_file, source_name, mapping, dry_run, ledger_path, min_exposure, usable_delay_days,
                       dict(experiment_id=experiment_id, ci_level=ci_level, effect_scale=effect_scale, started_at=started_at,
                            ended_at=ended_at, n_baseline=n_baseline, n_variant=n_variant, engine=engine, analysis_basis=analysis_basis))
        return
    from mootcourt.ledger import ADMITTED, append_rows, ensure_snapshot, read_ledger, write_ledger
    from mootcourt.sources import asos, upworthy
    from mootcourt.sources import synthetic as synth

    if source not in ("all", "upworthy", "asos", "synthetic"):
        raise typer.BadParameter("source must be upworthy, asos, synthetic or all")
    wanted = ["upworthy", "asos"] + (["synthetic"] if synthetic else []) if source == "all" else [source]
    ledger = read_ledger(ledger_path) if ledger_path.exists() else None
    t0 = time.perf_counter()
    for name in wanted:
        t1 = time.perf_counter()
        if name == "synthetic":
            new, _ = synth.generate(synth.SyntheticConfig(seed=seed, n_tests=n_tests))
        else:
            folder = Path(raw_dir) / name
            # dot files are skipped: macOS writes AppleDouble companions (._name) beside files on exFAT volumes
            files = visible_glob(folder, "*exploratory*packages*.csv") if name == "upworthy" else [folder]
            if not files or not files[0].exists():
                raise typer.BadParameter(f"no downloaded {name} file under {folder}; run `make data` first")
            new = upworthy.load_upworthy(files[0]) if name == "upworthy" else asos.load_asos(files[0])
        ledger = new if ledger is None else append_rows(ledger, new)
        adm = int((new["status"] == ADMITTED).sum())
        typer.echo(f"{name}: {len(new)} contrasts, {adm} admitted, {new['test_id'].nunique()} tests ({time.perf_counter() - t1:.1f} s)")
    write_ledger(ledger, ledger_path)
    for name in wanted:
        sid = ensure_snapshot(ledger[ledger["source"] == name].reset_index(drop=True), ledger_path.parent)
        typer.echo(f"snapshot {sid} for {name}")
    typer.echo(f"ledger {ledger_path}: {len(ledger)} rows in {time.perf_counter() - t0:.1f} s")


def _ingest_export(fmt, input_file, source_name, mapping, dry_run, ledger_path, min_exposure, usable_delay_days, options) -> None:
    """The ``--format`` branch of ``moot ingest``: read, check, convert, summarise and (without --dry-run) append."""
    from mootcourt.importers import FORMATS, ExchangeError, MappingError, admission_summary
    from mootcourt.importers.exchange import unit_conflicts
    from mootcourt.importers.ingest import format_summary, import_file
    from mootcourt.ledger import LedgerConflictError, append_rows, ensure_snapshot, read_ledger, write_ledger

    if fmt is None or input_file is None:
        raise typer.BadParameter("--format and --input go together")
    if fmt not in FORMATS:
        raise typer.BadParameter(f"unknown format {fmt!r}; the formats are {', '.join(FORMATS)}")
    try:
        new, warnings = import_file(fmt, input_file, source_name, mapping, min_exposure, usable_delay_days, **options)
    except ExchangeError as exc:
        typer.echo(f"error: {exc}", err=True)
        if fmt == "growthbook" and any(v.column == "started_at" for v in exc.violations):
            typer.echo("hint: a GrowthBook bulk snapshot has no start date; pass --started-at", err=True)
        raise typer.Exit(code=1) from None
    except (MappingError, FileNotFoundError, ValueError, OverflowError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    for w in warnings[:20]:
        typer.echo(str(w), err=True)
    typer.echo(format_summary(admission_summary(new)))
    if dry_run:
        typer.echo("dry run: nothing written")
        return
    ledger = read_ledger(ledger_path) if ledger_path.exists() else None
    if ledger is not None:
        clash = unit_conflicts(ledger, new)
        if clash:
            typer.echo("error: " + clash[0], err=True)
            raise typer.Exit(code=1)
    try:
        merged = new if ledger is None else append_rows(ledger, new)
    except LedgerConflictError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    write_ledger(merged, ledger_path)
    sid = ensure_snapshot(merged[merged["source"] == source_name].reset_index(drop=True), ledger_path.parent)
    typer.echo(f"snapshot {sid} for {source_name}")
    typer.echo(f"ledger {ledger_path}: {len(merged)} rows")


ledger_app = typer.Typer(help="The vendor-neutral ledger exchange format: formats and conformance check.", no_args_is_help=True)
app.add_typer(ledger_app, name="ledger")


@ledger_app.command("check")
def ledger_check(file: Path = typer.Argument(..., help="An exchange file (CSV or Parquet) or a ledger Parquet file.")) -> None:
    """Report schema violations, duplicate ids, impossible values, horizon violations and missing provenance. Exit code 1 on any."""
    from mootcourt.importers.ingest import check_file

    try:
        violations = check_file(file)
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    for v in violations:
        typer.echo(str(v))
    if violations:
        n_err = sum(1 for v in violations if v.severity == "error")
        typer.echo(f"FAIL: {n_err} error(s), {len(violations) - n_err} warning(s)")
        raise typer.Exit(code=1)
    typer.echo("ok: the file conforms to the ledger exchange format")


@ledger_app.command("formats")
def ledger_formats() -> None:
    """List the import formats and whether the export is documented publicly or needs an editable mapping template."""
    from mootcourt.importers import DOCUMENTED, FORMATS, TEMPLATE_ONLY

    for name in FORMATS:
        kind = "documented mapping" if name in DOCUMENTED else ("mapping template to edit (export not documented publicly)" if name in TEMPLATE_ONLY
                                                                   else "exchange columns, or any file through --mapping")
        typer.echo(f"{name}: {kind}")


@app.command()
def promote(
    source: str = typer.Option(..., "--source"),
    models_dir: Path | None = typer.Option(None, "--models-dir", help="Default: the storage root."),
    reports_dir: Path | None = typer.Option(None, "--reports-dir", help="Default: the storage root."),
    margin: float = typer.Option(PROMOTION_MARGIN, "--margin", help="The lower bound of the paired Brier skill difference's 90 percent "
                                                                    "interval must clear this; default 0 (the interval decides)."),
    challenger_scores: Path | None = typer.Option(None, "--challenger-scores", help="Per-row score table of a backtest of the challenger's "
                                                  "method (scores-<source>-<snapshot>[--variant].parquet); default: the table of the "
                                                  "challenger's own summary."),
    challenger_rung: str | None = typer.Option(None, "--challenger-rung", help="Rung of that table to pair; default the summary's rung (P2)."),
    bootstrap: int = typer.Option(500, "--bootstrap", help="Resamples (whole tests) of the paired difference, as in the backtest."),
) -> None:
    """Promote the challenger only if the paired comparison on common rows clears the margin at the gate's n (tests)."""
    paths = storage_paths()
    models_dir = models_dir if models_dir is not None else paths.models
    reports_dir = reports_dir if reports_dir is not None else paths.reports
    from mootcourt.registry import promote_command

    try:
        res = promote_command(models_dir, reports_dir, source, margin=margin, challenger_scores=challenger_scores,
                              challenger_rung=challenger_rung, B=bootstrap)
    except FileNotFoundError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(res.reason if res.promoted else f"not promoted: {res.reason}")


@app.command("earn-weight")
def earn_weight_cmd(
    source: str | None = typer.Option(None, "--source", help="Source whose backtest scores at the current ledger snapshot are used."),
    second_opinion: Path | None = typer.Option(None, "--second-opinion", help="Records file from `moot simulators run`."),
    include_contaminated: bool = typer.Option(False, "--include-contaminated",
                                              help="Also use contaminated origins; the stored weight is then marked contaminated."),
    ledger_path: Path | None = typer.Option(None, "--ledger", help="Default: the storage root."),
    models_dir: Path | None = typer.Option(None, "--models-dir", help="Default: the storage root."),
    reports_dir: Path | None = typer.Option(None, "--reports-dir", help="Default: the storage root."),
) -> None:
    """Fit the second-opinion weight; it stays 0 until a provider earns it (the default provider has no opinion)."""
    paths = storage_paths()
    ledger_path = ledger_path if ledger_path is not None else paths.ledger_path
    models_dir = models_dir if models_dir is not None else paths.models
    reports_dir = reports_dir if reports_dir is not None else paths.reports
    import pandas as pd

    from mootcourt import simulate
    from mootcourt.ledger import ensure_snapshot
    from mootcourt.predictors.second_opinion import NullProvider, earn_weight
    from mootcourt.registry import find_scores

    try:
        n_gate = simulate.load_gates(reports_dir / "gates.json")["n_400"]
    except FileNotFoundError:
        n_gate = sys.maxsize
    if second_opinion is None:
        scored = pd.DataFrame({"p_sig": [], "event": []})
        if source is not None:
            df = _load_source_ledger(ledger_path, source)
            found = find_scores(reports_dir, source, ensure_snapshot(df, ledger_path.parent))
            if found is not None:
                scored = pd.read_parquet(found)
                scored = scored[scored["rung"] == "P2"] if (scored["rung"] == "P2").any() else scored
        res = earn_weight(NullProvider(), scored, n_gate=n_gate, margin=EARN_WEIGHT_MARGIN)
        typer.echo(f"{res.message}. The weight stays 0 until a provider earns it at the gate's n with the margin {EARN_WEIGHT_MARGIN}.")
        return
    if source is None:
        raise typer.BadParameter("--source is required with --second-opinion")
    from mootcourt.registry import Registry
    from mootcourt.simulators import SimulatorError
    from mootcourt.simulators.scoring import RecordedProvider, earn_frame, load_second_opinion, uses_contaminated

    df = _load_source_ledger(ledger_path, source)
    sid = ensure_snapshot(df, ledger_path.parent)
    found = find_scores(reports_dir, source, sid)
    if found is None:
        raise typer.BadParameter(f"no backtest scores for {source} at snapshot {sid} in {reports_dir}; run `moot backtest`")
    try:
        data = load_second_opinion(second_opinion)
        frame = earn_frame(pd.read_parquet(found), df, data, include_contaminated=include_contaminated)
    except SimulatorError as exc:
        raise typer.BadParameter(str(exc)) from None
    res = earn_weight(RecordedProvider(data), frame, n_gate=n_gate, margin=EARN_WEIGHT_MARGIN)
    contaminated = include_contaminated and uses_contaminated(frame, data)
    evidence = {"message": res.message, "n_rows": res.n, "n_tests": res.n_tests, "n_chosen": res.n_chosen, "cut": res.cut,
                "brier_p_sig": res.brier_base,
                "brier_stacked": res.brier_stacked, "n_gate": None if n_gate == sys.maxsize else n_gate, "margin": EARN_WEIGHT_MARGIN,
                "scores_file": found.name, "snapshot_id": sid, "knowledge_cutoff": data.knowledge_cutoff, "cutoff_unknown": data.cutoff_unknown,
                "included_contaminated": include_contaminated, "contaminated": contaminated, "records_file": second_opinion.name}
    reg = Registry(models_dir)
    try:
        if res.weight > 0 or reg.get_second_opinion_weight(source, data.provider_id, data.version) > 0:
            reg.set_second_opinion_weight(source, data.provider_id, data.version, res.weight, evidence, contaminated=contaminated)
    except KeyError as exc:
        raise typer.BadParameter(f"{exc.args[0]}; run `moot fit` first") from None
    if include_contaminated:
        scope = "all origins, contaminated ones included"
    elif data.cutoff_unknown:
        scope = "no origins (no knowledge cutoff is declared, so every origin is possibly contaminated; see --include-contaminated)"
    else:
        scope = f"origins from {data.knowledge_cutoff} on" if data.knowledge_cutoff else "all origins"
    typer.echo(f"{data.provider_id} {data.version} on {scope}, scores {found.name}, {res.n} judged rows "
               f"({res.n_tests} tests) with an opinion: {res.message}")
    if res.weight > 0:
        typer.echo(f"wrote weight {res.weight} for {data.provider_id} {data.version} on {source} to the registry"
                   + (" (marked contaminated: it was earned with origins the agent may have seen)" if contaminated else ""))


@app.command()
def join(
    source: str = typer.Option(..., "--source"),
    ledger_path: Path | None = typer.Option(None, "--ledger", help="Default: the storage root."),
    cards_dir: Path | None = typer.Option(None, "--cards-dir", help="Default: the storage root."),
    reports_dir: Path | None = typer.Option(None, "--reports-dir", help="Default: the storage root."),
    new_rows: Path | None = typer.Option(None, "--new-rows", help="Ledger parquet of newly concluded rows to append."),
    now: str | None = typer.Option(None, "--now", help="Join time (ISO-8601 with offset); default now."),
) -> None:
    """Weekly loop: append new rows, join outcomes to issued cards, type misses, rewrite reliability."""
    paths = storage_paths()
    ledger_path = ledger_path if ledger_path is not None else paths.ledger_path
    cards_dir = cards_dir if cards_dir is not None else paths.cards
    reports_dir = reports_dir if reports_dir is not None else paths.reports
    from mootcourt.loop import join_command

    res = join_command(source, ledger_path.parent, cards_dir, reports_dir, new_rows_path=new_rows,
                       now=_parse_time(now, "--now") or dt.datetime.now(dt.timezone.utc))
    extra = ""
    if res.n_post_hoc:
        extra += f"; {res.n_post_hoc} post-hoc card{'s' if res.n_post_hoc != 1 else ''} recorded, not scored (issued after the test started)"
    if res.n_reissues:
        extra += f"; {res.n_reissues} reissue{'s' if res.n_reissues != 1 else ''} recorded, not scored (a row is scored once)"
    typer.echo(f"appended {res.n_new_rows} rows" + (f", snapshot {res.snapshot_id}" if res.snapshot_id else "")
               + f"; attached {res.n_outcomes} outcomes {json.dumps(res.miss_counts, sort_keys=True)}{extra}; reliability in {res.reliability_path}")
    if res.n_outside_window:
        from mootcourt.config import TRAILING_WEEKS

        typer.echo(f"{res.n_outside_window} of the {res.n_outcomes} attached outcomes are older than the trailing {TRAILING_WEEKS} weeks "
                   "at this join, so they do not date a reliability entry; a cell with no outcome inside the window keeps its old date and ages")


@app.command()
def serve(
    host: str = typer.Option(DEFAULT_SERVE_HOST, "--host", help="Bind address; loopback by default, no authentication is provided."),
    port: int = typer.Option(DEFAULT_SERVE_PORT, "--port"),
    models_dir: Path | None = typer.Option(None, "--models-dir", help="Default: the storage root."),
    cards_dir: Path | None = typer.Option(None, "--cards-dir", help="Default: the storage root."),
    reports_dir: Path | None = typer.Option(None, "--reports-dir", help="Default: the storage root."),
) -> None:
    """Start the read-only HTTP service (POST /card, GET /reliability/{source}, GET /health)."""
    paths = storage_paths()
    models_dir = models_dir if models_dir is not None else paths.models
    cards_dir = cards_dir if cards_dir is not None else paths.cards
    reports_dir = reports_dir if reports_dir is not None else paths.reports
    import uvicorn

    from mootcourt.service import create_app
    from mootcourt.simulators.http import is_loopback_host

    # On a loopback bind only loopback names are accepted as the Host header (DNS rebinding); a wider bind is the operator's gateway to guard.
    trusted = ["127.0.0.1", "localhost", "::1", "[::1]"] if is_loopback_host(host) else None
    if trusted is not None:                      # the address this process binds to is also a name its clients use (127.0.0.2, 0:0:0:0:0:0:0:1)
        bare = host.strip("[]")
        trusted += [x for x in (host, bare, f"[{bare}]" if ":" in bare else None) if x and x not in trusted]
    uvicorn.run(create_app(models_dir, cards_dir, reports_dir=reports_dir, trusted_hosts=trusted), host=host, port=port)


@app.command()
def mcp(
    models_dir: Path | None = typer.Option(None, "--models-dir", help="Default: the storage root."),
    reports_dir: Path | None = typer.Option(None, "--reports-dir", help="Default: the storage root."),
) -> None:
    """Start the read-only MCP server on stdio (get_card, list_precedents, reliability_report)."""
    paths = storage_paths()
    models_dir = models_dir if models_dir is not None else paths.models
    reports_dir = reports_dir if reports_dir is not None else paths.reports
    from mootcourt.mcp_server import build_server

    build_server(models_dir, reports_dir).run(transport="stdio")


simulators_app = typer.Typer(help="Response simulators: attach an outside agent as a second opinion.", no_args_is_help=True)
app.add_typer(simulators_app, name="simulators")


@simulators_app.command("list")
def simulators_list(
    config: Path | None = typer.Option(None, "--config", help="Config file; default mootcourt.toml in the working directory."),
    models_dir: Path | None = typer.Option(None, "--models-dir", help="Default: the storage root."),
) -> None:
    """List providers with version, knowledge cutoff and the earned weight per source."""
    from mootcourt.registry import Registry
    from mootcourt.simulators.loader import describe_all

    if config is not None and not Path(config).is_file():
        typer.echo(f"error: the config file {config} does not exist", err=True)
        raise typer.Exit(code=2)
    models_dir = models_dir if models_dir is not None else storage_paths().models
    reg = Registry(models_dir)
    typer.echo(f"{'name':<18}{'adapter':<13}{'version':<9}{'knowledge cutoff':<18}{'cost':<10}weight earned")
    for row in describe_all(config):
        in_force = []
        for src in reg.sources():
            rec = reg.get_second_opinion(src, row["provider_id"], row["version"])        # this version, on the current champion
            if rec and float(rec["weight"]) > 0:
                in_force.append(f"{src}={float(rec['weight']):g}" + (" (contaminated)" if rec.get("contaminated") else ""))
        w = ", ".join(in_force) or "0 (not earned)"
        cut = str(row["knowledge_cutoff"] or "none")
        typer.echo(f"{row['name']:<18}{str(row['adapter']):<13}{row['version']:<9}{cut:<18}{row['cost_model']:<10}{w}")
    shown = False
    for src in reg.sources():
        for h in reg.second_opinion_history(src):             # the audit record of weights a newer version of the provider displaced
            if not shown:
                typer.echo("displaced weights (earlier versions, kept as the audit record; not in force):")
                shown = True
            typer.echo(f"  {src}: {h['provider_id']} version {h['version']} weight {float(h['weight']):g}")


@simulators_app.command("run")
def simulators_run(
    provider: str = typer.Option(..., "--provider", help="Provider name (see `moot simulators list`)."),
    source: str = typer.Option(..., "--source", help="Data source: upworthy, asos or synthetic."),
    origins: str = typer.Option("quarterly", "--origins", help="Only quarterly is supported."),
    out: Path = typer.Option(..., "--out", help="Records file to write (JSONL)."),
    config: Path | None = typer.Option(None, "--config", help="Config file; default mootcourt.toml in the working directory."),
    allow_remote: bool = typer.Option(False, "--allow-remote", help="Allow an http provider on a non-loopback host."),
    limit: int | None = typer.Option(None, "--limit", help="Only the first N requests (a trial run)."),
    max_respondents: int = typer.Option(100, "--max-respondents", help="Budget passed to the agent."),
    max_seconds: float = typer.Option(30.0, "--max-seconds", help="Time cap passed to the agent and enforced by the adapters."),
    use_cache: bool = typer.Option(True, "--cache/--no-cache", help="Reuse results under the cache folder."),
    ledger_path: Path | None = typer.Option(None, "--ledger", help="Default: the storage root."),
) -> None:
    """Run a provider once over the rolling-origin request set and write one record per request."""
    from mootcourt.simulators import Budget, SimulatorError
    from mootcourt.simulators.cache import SimulationCache
    from mootcourt.simulators.loader import get_simulator
    from mootcourt.simulators.runner import build_requests, run

    paths = storage_paths()
    ledger_path = ledger_path if ledger_path is not None else paths.ledger_path
    if origins != "quarterly":
        raise typer.BadParameter("only --origins quarterly is supported")
    try:
        sim = get_simulator(provider, config, allow_remote=allow_remote)
        items = build_requests(_load_source_ledger(ledger_path, source), budget=Budget(max_respondents, max_seconds), limit=limit)
    except SimulatorError as exc:
        raise typer.BadParameter(str(exc)) from None
    t0 = time.perf_counter()
    summary = run(sim, items, out, SimulationCache(paths.cache / "simulators") if use_cache else None)
    info = sim.describe()
    typer.echo(f"{info.provider_id} {info.version}: {summary.n_requests} requests, {summary.n_called} called, {summary.n_cached} from the cache, "
               f"{summary.n_declined} declined, {summary.n_failed} failed (recorded, not cached); cost {summary.cost_usd:.4f} dollars, "
               f"agent latency {summary.latency_s:.1f} s, "
               f"wall {time.perf_counter() - t0:.1f} s")
    typer.echo(f"wrote {out}")


@app.command()
def init(
    directory: Path = typer.Option(Path("."), "--dir", help="Project folder; mootcourt.toml is written here."),
    data_root: Path | None = typer.Option(None, "--data-root", help="Where data, models, reports and cards live; default <dir>/mootcourt-data."),
    cells: str | None = typer.Option(None, "--cells", help="Comma-separated cell names the program forecasts; default the sample ledger's metrics."),
    name: str | None = typer.Option(None, "--name", help="Project name; default the folder name."),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing mootcourt.toml."),
    progress_after: float = typer.Option(10.0, "--progress-after", help="Seconds after which the quick gate simulation reports progress."),
) -> None:
    """Create mootcourt.toml, the data root layout, a sample ledger and quick gates; print the three commands that follow."""
    from mootcourt.onboarding import init_project

    try:
        with Heartbeat("the quick gates simulation (synthetic data)", delay=progress_after) as beat:
            res = init_project(directory, data_root, [c.strip() for c in cells.split(",") if c.strip()] if cells else None, name, force,
                               progress=lambda line: typer.echo(line, err=True) if beat.past_delay() else None)
    except FileExistsError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    typer.echo(f"wrote {res['config']}")
    typer.echo(f"data root {res['data_root']} (layout created)")
    typer.echo(f"sample ledger {res['sample_ledger']} (synthetic)")
    typer.echo(f"quick gates {res['gates']} ({res['gate_replicates']} replicates; run `moot simulate gate-power` for the full simulation)")
    typer.echo("Next, from the project folder:")
    for i, c in enumerate(res["commands"], 1):
        typer.echo(f"  {i}. {c}")


@app.command()
def doctor() -> None:
    """Check versions, data root and space, ledger, model freshness, reliability age and the service; write reports/doctor.json.

    Exit code 0 healthy, 1 warnings, 2 failures.
    """
    from mootcourt.onboarding import exit_code, run_doctor

    report = run_doctor()
    for c in report["checks"]:
        typer.echo(f"{c['status'].upper():<5} {c['name']}: {c['detail']}")
    typer.echo(f"status: {report['status']}")
    raise typer.Exit(code=exit_code(report))


@app.command()
def benchmark(
    scale: int | None = typer.Option(None, "--scale", help="Generate a synthetic ledger of this many contrasts; time the fit, a backtest and cards."),
    ledger: Path | None = typer.Option(None, "--ledger", help="Run the standard protocol on this ledger and write the one-page report card."),
    source: str | None = typer.Option(None, "--source", help="With --ledger: the source to score when the ledger holds several."),
    bootstrap: int = typer.Option(BOOTSTRAP_RESAMPLES, "--bootstrap", help="With --ledger: bootstrap resamples for the intervals."),
    cards: int = typer.Option(1000, "--cards", help="With --scale: how many cards to issue and time."),
    origins: int = typer.Option(2, "--origins", help="With --scale: how many of the last quarterly origins the small backtest scores."),
    scored_per_origin: int = typer.Option(2000, "--scored-per-origin", help="With --scale: rows scored at each origin (a seeded random sample)."),
    seed: int = typer.Option(20261103, "--seed", help="Random seed."),
    reports_dir: Path | None = typer.Option(None, "--reports-dir", help="Default: the storage root."),
    experiments_dir: Path | None = typer.Option(None, "--experiments-dir", help="With --scale: default the storage root."),
) -> None:
    """Scale benchmark (--scale N) or the organization report card (--ledger FILE); exactly one of the two."""
    from mootcourt import benchmark as bench

    if (scale is None) == (ledger is None):
        raise typer.BadParameter("give exactly one of --scale N and --ledger FILE")
    paths = storage_paths()
    reports_dir = reports_dir if reports_dir is not None else paths.reports
    if scale is not None:
        experiments_dir = experiments_dir if experiments_dir is not None else paths.experiments
        try:
            doc = bench.run_scale(scale, experiments_dir=experiments_dir, reports_dir=reports_dir, seed=seed, n_cards=cards, n_origins=origins,
                                  scored_per_origin=scored_per_origin, log=typer.echo)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from None
        c = doc["card_latency_ms"]
        typer.echo(f"scale {scale}: wall {doc['wall_seconds']} s, fit {doc['stages']['fit']['seconds']} s, peak memory {doc['peak_rss_gb']} GB, "
                   f"card p50 {c['p50_ms']} ms p95 {c['p95_ms']} ms")
        typer.echo(f"wrote {doc['report_path']}")
        return
    try:
        card = bench.run_report_card(ledger, reports_dir, source=source, seed=seed, bootstrap=bootstrap, log=typer.echo)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from None
    typer.echo(f"wrote {card['paths']['md']}\nwrote {card['paths']['json']}")


@app.command()
def storage() -> None:
    """Show where the heavy directories live, their sizes and the free space of their volumes."""
    from mootcourt.storage import ENV_VAR, human_bytes, storage_report

    paths = storage_paths()
    shown = paths.root if paths.root is not None else "not set (repo-local default paths)"
    typer.echo(f"data root: {shown}  [set {ENV_VAR} or storage.data_root in mootcourt.toml]")
    low = False
    for row in storage_report(paths):
        flag = "" if row["exists"] else " (not created yet)"
        typer.echo(f"{row['name']:<12}{row['path']}{flag}  size {human_bytes(row['bytes'])}  free {human_bytes(row['free_bytes'])}")
        low = low or row["low_space"]
    if low:
        typer.echo("warning: less than 10 GB free on a volume that holds one of these directories; point the root at a larger volume", err=True)


simulate_app = typer.Typer(help="Synthetic data and gate power. Everything here is synthetic.", no_args_is_help=True)
app.add_typer(simulate_app, name="simulate")


@simulate_app.command("ledger")
def simulate_ledger(
    out: Path = typer.Option(..., "--out", help="Where to write the synthetic ledger (parquet)."),
    seed: int = typer.Option(0, "--seed"),
    n_tests: int = typer.Option(1000, "--n-tests"),
    text_effect: float = typer.Option(
        0.0,
        "--text-effect",
        help="Planted headline text signal (percent lift between headlines with and without a signal word); "
        "0 is the no-signal archive, above 0 is the positive control.",
    ),
    variants_per_test: int = typer.Option(2, "--variants-per-test", min=1, max=4),
) -> None:
    """Write a synthetic ledger with known truth (source synthetic)."""
    from mootcourt.ledger import write_ledger
    from mootcourt.sources import synthetic

    ledger, _ = synthetic.generate(synthetic.SyntheticConfig(seed=seed, n_tests=n_tests, text_effect_strength=text_effect,
                                                             variants_per_test=variants_per_test))
    write_ledger(ledger, out)
    typer.echo(f"wrote {len(ledger)} synthetic rows to {out} (label: synthetic"
               + (f", planted text effect {text_effect:g}" if text_effect else "") + ")")


@simulate_app.command("power")
def simulate_power(
    out: Path | None = typer.Option(None, "--out", help="Default: gates.json under the reports directory."),
    reps: int = typer.Option(1000, "--reps", help="Simulated gates per point; lower is faster and noisier."),
    bootstrap: int = typer.Option(500, "--bootstrap", help="Bootstrap resamples per simulated gate."),
    seed: int = typer.Option(20261102, "--seed"),
    base_rate: list[float] | None = typer.Option(
        None, "--base-rate", help="Base rate of the significant-positive event; repeat for several. Default 0.30."
    ),
    target: float | None = typer.Option(None, "--target", help="Power of the release gate; default gate.target_power in mootcourt.toml, else 0.90."),
    rows_per_test: float = typer.Option(
        1.0, "--rows-per-test", help="Mean rows per test; above 1 simulates tests and bootstraps by test (the sizes are then tests)."
    ),
    level: float = typer.Option(0.95, "--level", help="Interval whose lower end must clear zero."),
) -> None:
    """Simulate the release gates and write reports/gates.json (synthetic data only)."""
    paths = storage_paths()
    out = out if out is not None else paths.gates_path
    from mootcourt import simulate
    from mootcourt.settings import load_settings

    power = target if target is not None else load_settings()["gate"]["target_power"]
    rates = list(base_rate) if base_rate else [0.30]
    doc = simulate.write_gates(out, base=rates[0], base_rates=rates if base_rate else None, target=power, reps=reps, B=bootstrap, seed=seed,
                               rows_per_test=rows_per_test, level=level)
    _print_gates(doc, simulate, reps, bootstrap, out)


def _print_gates(doc: dict, simulate, reps: int, bootstrap: int, out) -> None:
    for key, entry in sorted((doc.get("by_base_rate") or {"": doc}).items()):
        typer.echo(
            (f"base rate {key}: " if key else "")
            + f"interval {doc.get('interval', {}).get('level', 0.95)} by {doc.get('interval', {}).get('by', 'row')}"
        )
        if entry.get("table"):
            iv = doc.get("interval", {})
            typer.echo(simulate.format_table(entry["table"], iv.get("level", 0.95), iv.get("by", "row")))
        for t, v in sorted(entry["by_target"].items()):
            typer.echo(f"power {t}: n_200 = {v['n_200']} (skill 0.20), n_400 = {v['n_400']} (skill 0.10)")
    typer.echo(f"release gate = power {doc['decision_target']:.2f}; reps {reps}, bootstrap {bootstrap}, {doc['seconds']} s. "
               f"Synthetic data. Wrote {out}")


@simulate_app.command("gate-power")
def simulate_gate_power(
    out: Path | None = typer.Option(None, "--out", help="Default: gates.json under the reports directory."),
    reps: int = typer.Option(1000, "--reps", help="Simulated gates per point; lower is faster and noisier."),
    bootstrap: int = typer.Option(500, "--bootstrap", help="Bootstrap resamples (by test) per simulated gate."),
    seed: int = typer.Option(20261102, "--seed"),
    base_rate: list[float] | None = typer.Option(None, "--base-rate", help="Base rate of the significant-positive event; repeat for several. "
                                                 "Default: 0.09 (the Upworthy archive), 0.14 (ASOS) and 0.30 (the earlier gates)."),
    target: float | None = typer.Option(None, "--target", help="Power of the release gate; default gate.target_power in mootcourt.toml, else 0.90."),
    rows_per_test: float | None = typer.Option(None, "--rows-per-test", help="Mean rows per test; default: the measured value of each base rate "
                                               "(Upworthy 3.5, ASOS 5); sizes are numbers of tests."),
    icc: float | None = typer.Option(None, "--icc", help="Binary within-test correlation of the event; default: the measured value of each base rate "
                                     "(Upworthy 0.13, ASOS 0.67)."),
    level: float = typer.Option(0.90, "--level", help="Interval whose lower end must clear zero (the harness reports 90 percent by test)."),
    source: str | None = typer.Option(None, "--source", help="Measure rows per test, the base rate and the within-test correlation on this "
                                                             "source's ledger instead of a public archive's values."),
    ledger_path: Path | None = typer.Option(None, "--ledger", help="Default: the storage root."),
    table: bool = typer.Option(True, "--table/--no-table", help="Also simulate the power table (the slow part; the sizes do not need it)."),
    progress_after: float = typer.Option(10.0, "--progress-after", help="Seconds after which progress lines go to standard error."),
) -> None:
    """Simulate the gates by test at the base rates of the archives, or at your ledger's, and write reports/gates.json (synthetic data only)."""
    paths = storage_paths()
    out = out if out is not None else paths.gates_path
    from mootcourt import simulate
    from mootcourt.settings import load_settings

    power = target if target is not None else load_settings()["gate"]["target_power"]
    rates = list(base_rate) if base_rate else list(simulate.RELEASE_BASE_RATES)
    rpt = {b: v[0] for b, v in simulate.SOURCE_DEPENDENCE.items()} if rows_per_test is None else rows_per_test
    corr = {b: v[1] for b, v in simulate.SOURCE_DEPENDENCE.items()} if icc is None else icc
    where = "given on the command line" if (rows_per_test is not None and icc is not None) else "the public archive nearest this base rate"
    if source is not None:
        dep = simulate.ledger_dependence(_load_source_ledger(ledger_path if ledger_path is not None else paths.ledger_path, source))
        rpt = dep["rows_per_test"] if rows_per_test is None else rows_per_test
        corr = dep["icc"] if icc is None else icc
        if not base_rate:
            rates = [dep["base_rate"]]
        where = (f"measured on the {source} ledger ({dep['n_rows']} admitted rows in {dep['n_tests']} tests; event rate {dep['base_rate']:.3f})"
                 + ("" if rows_per_test is None and icc is None else "; the value given on the command line wins"))
    for b in rates:
        typer.echo(f"assumptions at base rate {b:.2f}: rows per test {simulate._at(rpt, b):.1f}, within-test correlation {simulate._at(corr, b):.2f} "
                   f"({where}" + ("" if source is not None or (rows_per_test is not None and icc is not None)
                                  else "; pass --source NAME to measure them on your own ledger") + ")")
    with Heartbeat("gate power simulation (synthetic data)", delay=progress_after) as beat:
        doc = simulate.write_gates(out, base=rates[0], base_rates=rates, target=power, reps=reps, B=bootstrap, seed=seed, rows_per_test=rpt,
                                   icc=corr, level=level, max_seconds=900.0, with_table=table, dependence_source=where,
                                   progress=lambda line: typer.echo(line, err=True) if beat.past_delay() else None)
    _print_gates(doc, simulate, reps, bootstrap, out)


@app.command()
def reliability(
    source: str = typer.Option(..., "--source"),
    reports_dir: Path | None = typer.Option(None, "--reports-dir", help="Default: the storage root."),
    as_json: bool = typer.Option(False, "--json", help="Print the report as JSON instead of the table."),
) -> None:
    """Print the weekly reliability report of a source: one line per cell, or the JSON (call 208)."""
    paths = storage_paths()
    reports_dir = reports_dir if reports_dir is not None else paths.reports
    from mootcourt.card import load_reliability_report

    report = load_reliability_report(reports_dir, source)
    if report is None:
        raise typer.BadParameter(f"no reliability report for source {source} under {reports_dir}; `moot backtest` seeds one and `moot join` "
                                 "keeps it current")
    if as_json:
        typer.echo(json.dumps(report, indent=1, sort_keys=True))
        return

    def num(v, nd=3):
        return "n/a" if v is None else f"{v:.{nd}f}"

    typer.echo(f"report as of {report['as_of']}")
    typer.echo(f"{'cell':22} {'as of':12} {'rows':>5} {'tests':>5} {'brier skill':>12} {'interval':>18} {'log score':>10} {'P0 log score':>13} "
               f"{'below':>6} drifted")
    for cell, e in sorted((report.get("cells") or {}).items()):
        interval = f"{num(e.get('brier_skill_lo'))} to {num(e.get('brier_skill_hi'))}" if e.get("brier_skill_lo") is not None else "n/a"
        tests = e.get("n_tests") if e.get("n_tests") is not None else "n/a"
        typer.echo(f"{cell:22} {str(e.get('as_of', ''))[:10]:12} {e.get('n', 'n/a'):>5} {tests:>5} "
                   f"{num(e.get('brier_skill')):>12} {interval:>18} {num(e.get('rolling_logscore')):>10} {num(e.get('p0_rolling_logscore')):>13} "
                   f"{e.get('consecutive_below', 0):>6} {e.get('drifted', False)}")


if __name__ == "__main__":  # pragma: no cover
    app()
