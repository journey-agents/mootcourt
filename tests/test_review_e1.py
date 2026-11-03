"""T-041 contracts: fixes for the code review of chunks C and D1 (review-results-cd1.json)."""
import datetime as dt
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "upworthy_late_variants.csv"
UTC = dt.timezone.utc


def _load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- REV-001 Upworthy visibility
def test_fixture_is_34_real_tests_with_late_packages():
    raw = pd.read_csv(FIXTURE, dtype=str)
    created = pd.to_datetime(raw["created_at"], utc=True, format="ISO8601")
    span = created.groupby(raw["clickability_test_id"]).agg(lambda s: s.max() - s.min())
    assert raw["clickability_test_id"].nunique() == 34 and (span >= pd.Timedelta(days=1)).all()


def test_no_upworthy_row_is_visible_before_its_variant_existed(imp):
    up, ledger_mod = imp("mootcourt.sources.upworthy"), imp("mootcourt.ledger")
    led = up.load_upworthy(FIXTURE)
    raw = pd.read_csv(FIXTURE, dtype=str)
    raw["created"] = pd.to_datetime(raw["created_at"], utc=True, format="ISO8601")
    created = dict(zip(raw.iloc[:, 0].astype(str), raw["created"]))
    ref_created = raw.groupby("clickability_test_id")["created"].min()
    last_created = raw.groupby("clickability_test_id")["created"].max()
    horizon = pd.Timedelta(days=7)
    contrasts = led[led["status"] != "single_arm"]
    assert len(contrasts) > 100
    late = 0
    for r in contrasts.itertuples():
        var_c, ref_c = created[r.variant_id], ref_created[r.test_id]
        assert r.started_at == max(var_c, ref_c)
        assert r.final_read_at == last_created[r.test_id] + horizon and r.usable_after == r.final_read_at      # test level since REV-026
        assert r.usable_after >= var_c + horizon           # never visible before its variant existed
        if var_c > ref_c + horizon:
            late += 1
            probe = var_c                                  # a variant created after the reference's old usable_after
            vis = ledger_mod.visible_rows(led.assign(status="admitted"), probe)
            assert r.row_id not in set(vis["row_id"])
    assert late > 0, "the fixture must contain variants created more than 7 days after the reference"


def test_period_is_the_quarter_of_the_final_read(imp):
    up, ledger_mod = imp("mootcourt.sources.upworthy"), imp("mootcourt.ledger")
    led = up.load_upworthy(FIXTURE)
    assert (led["period"] == led["final_read_at"].map(ledger_mod.quarter_of)).all()


# ---------------------------------------------------------------- REV-002 reliability staleness
def _outcome(cell, at, ls=-1.0):
    return {"cell": cell, "at": at.isoformat(), "logscore": ls, "p0_logscore": ls, "brier": 0.2, "p0_brier": 0.2}


def test_empty_window_keeps_the_old_entry_as_of_so_staleness_fires(imp):
    rel, ab = imp("mootcourt.reliability"), imp("mootcourt.abstain")
    t0 = dt.datetime(2014, 7, 1, tzinfo=UTC)
    first = rel.build_reliability(None, [_outcome("a", t0 - dt.timedelta(days=1)) for _ in range(12)], t0, advance=True, source="x")
    assert first["cells"]["a"]["as_of"] == t0.isoformat()
    t1 = t0 + dt.timedelta(days=30)
    second = rel.build_reliability(first, [], t1, advance=True, source="x")
    assert second["as_of"] == t1.isoformat()                       # the report moves
    assert second["cells"]["a"]["as_of"] == t0.isoformat()          # the cell does not
    assert ab.reliability_reason(second, "a", t1) is not None and "older than" in ab.reliability_reason(second, "a", t1)


def test_no_new_outcomes_join_refreshes_only_cells_still_backed_by_the_window(imp):
    rel, ab = imp("mootcourt.reliability"), imp("mootcourt.abstain")
    t0 = dt.datetime(2014, 7, 1, tzinfo=UTC)
    outs = [_outcome("a", t0 - dt.timedelta(days=1)) for _ in range(12)] + [_outcome("b", t0 - dt.timedelta(days=1)) for _ in range(12)]
    first = rel.build_reliability(None, outs, t0, advance=True, source="x")
    t1 = t0 + dt.timedelta(days=60)              # "a" is still inside the 8-week window, "b" has aged out
    outs_a = [_outcome("a", t1 - dt.timedelta(days=3))] * 12
    again = rel.build_reliability(first, outs_a, t1, advance=False, source="x")
    assert again["cells"]["a"]["as_of"] == t1.isoformat()
    assert again["cells"]["b"]["as_of"] == t0.isoformat()
    assert again["cells"]["a"]["consecutive_below"] == first["cells"]["a"]["consecutive_below"]
    assert ab.reliability_reason(again, "b", t1) is not None


def test_backtest_replay_uses_the_same_reliability_function(imp):
    assert imp("mootcourt.harness").build_reliability is imp("mootcourt.reliability").build_reliability


def test_backtest_cell_without_recent_outcomes_abstains_on_reliability(imp, make_synth):
    """Replay: a cell that stops receiving outcomes is not carried forward as fresh (call 30)."""
    rel = imp("mootcourt.reliability")
    t0 = dt.datetime(2014, 1, 1, tzinfo=UTC)
    rep = rel.build_reliability(None, [_outcome("only_early", t0 - dt.timedelta(days=2))] * 12, t0, advance=True)
    q2 = dt.datetime(2014, 4, 1, tzinfo=UTC)
    rep2 = rel.build_reliability(rep, [], q2, advance=True)
    assert imp("mootcourt.abstain").reliability_reason(rep2, "only_early", q2) is not None


# ---------------------------------------------------------------- REV-003 decidability by tests
def test_report_markdown_puts_the_by_test_column_before_the_by_row_column(imp):
    report = imp("mootcourt.report")
    cols = report._AGG_GROUPS[0][1]
    assert cols.index("decidable_by_tests") < cols.index("decidable")


def test_readme_table_headline_column_counts_tests_and_labels_both():
    mod = _load_script("render_readme_results")
    doc = {"header": {"gate_decision_target": 0.9, "gate_by_target": {"0.80": {}}},
           "tables": {"aggregate": [{"cell": "ALL", "rung": "P1", "n": 337, "logscore": -1.0, "brier_skill": 0.0, "brier_skill_lo": -0.1,
                                     "brier_skill_hi": 0.1, "coverage_80": 0.8, "coverage_90": 0.9, "abstention_rate": 0.1,
                                     "decidable": "decidable at skill 0.20 only", "decidable_research": "decidable at skill 0.20 only",
                                     "decidable_by_tests": "undecidable at this n", "decidable_research_by_tests": "undecidable at this n"}]}}
    lines = mod.results_table(doc)
    head = lines[0].lower()
    assert head.index("by tests") < head.index("by rows")
    assert "by tests" in head and "by rows" in head
    row = lines[2]
    assert row.index("undecidable") < row.index("skill 0.20 only")


def test_by_test_research_label_is_in_the_aggregate(imp, make_synth):
    harness, hs = imp("mootcourt.harness"), imp("mootcourt.harness_stats")
    ledger = make_synth(seed=141, n_tests=120, variants_per_test=2)[0]
    rungs = {k: v for k, v in harness.default_rungs("synthetic").items() if k in ("P0", "P1")}
    sc = harness.rolling_origin(ledger, rungs, harness.quarterly_origins(ledger))
    agg = hs.aggregate_scores(sc, {"n_200": 200, "n_400": 400}, B=30, seed=0)
    assert "decidable_research_by_tests" in agg.columns and "decidable_by_tests" in agg.columns


# ---------------------------------------------------------------- REV-004 docs and REV-005 run log
def test_method_md_does_not_claim_impressions_were_fixed_in_advance():
    text = (ROOT / "docs" / "method.md").read_text(encoding="utf-8")
    flat = re.sub(r"\s+", " ", text).lower()
    assert "fixed the impressions in advance" not in flat and "fixed the impressions" not in flat
    assert "planned-exposure proxy" in flat or "proxy for the planned exposure" in flat
    assert "+0.10" in text and "limitation" in flat


def test_data_md_and_method_md_name_the_later_created_at():
    data = re.sub(r"\s+", " ", (ROOT / "DATA.md").read_text(encoding="utf-8")).lower()
    method = re.sub(r"\s+", " ", (ROOT / "docs" / "method.md").read_text(encoding="utf-8")).lower()
    spec = re.sub(r"\s+", " ", (ROOT / "docs" / "superpowers" / "specs" / "2026-11-02-mootcourt-design.md").read_text(encoding="utf-8")).lower()
    for text in (data, method, spec):
        assert "later" in text and "created_at" in text.replace("`", "")
    assert "later `created_at` of the two arms" in data or "later created_at of the two arms" in data
    assert "later created_at of the two arms" in spec or "later `created_at` of the two arms" in spec


def test_run_log_labels_checksum_verification_and_records_a_clean_download():
    log = ROOT / "scripts" / "run_log.py"
    text = log.read_text(encoding="utf-8")
    assert "checksum verification" in text.lower()
    readme = (ROOT / "docs" / "results.md").read_text(encoding="utf-8")        # the generated results block moved here from the README (T-053)
    low = readme.lower()
    assert "Download 5.1 s" not in readme
    # The run time block states what the data stage was: a clean-clone download, or a checksum verification with no download (BUG-007).
    assert "clean-clone download" in low or "no download in this run" in low


# ---------------------------------------------------------------- REV-006 download fallback
def test_download_stops_when_no_approved_file_matches(tmp_path):
    from test_download import _run, _Stub

    s = _Stub({"jd64p": {"notes.txt": b"n\n", "renamed-data.csv": b"x\n"}, "64jsb": {}})
    try:
        r = _run(tmp_path, s)
    finally:
        s.close()
    assert r.returncode == 4, r.stdout + r.stderr
    assert "exploratory" in r.stderr and "no approved file" in r.stderr.lower()
    raw = tmp_path / "data" / "raw"
    assert not raw.exists() or not any(p.is_file() for p in raw.rglob("*"))


def test_bare_pytest_collects_download_extra():
    r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "tests/test_download_extra.py", "-p", "no:cacheprovider"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    text = (ROOT / "tests" / "test_download_extra.py").read_text(encoding="utf-8")
    assert "from tests" not in text and "import tests" not in text


# ---------------------------------------------------------------- found while re-running: AppleDouble files on exFAT
def test_ingest_ignores_dot_files_beside_the_exploratory_file(imp, tmp_path):
    from typer.testing import CliRunner

    up = tmp_path / "raw" / "upworthy"
    up.mkdir(parents=True)
    src = pd.read_csv(FIXTURE, dtype=str)
    name = "upworthy-archive-exploratory-packages-03.12.2020.csv"
    src.to_csv(up / name, index=False)
    (up / ("._" + name)).write_bytes(b"\x00\x05\x16\x07\xb0\x00")        # the resource-fork stub macOS writes on exFAT
    res = CliRunner().invoke(imp("mootcourt.cli").app, ["ingest", "--source", "upworthy", "--raw-dir", str(tmp_path / "raw"),
                                                        "--ledger", str(tmp_path / "ledger" / "ledger.parquet")])
    assert res.exit_code == 0, res.output


def test_a_bundle_saved_beside_apple_double_files_still_loads(imp, make_synth, tmp_path, monkeypatch):
    """On exFAT, macOS writes ._name companions while a bundle is saved; the manifest must not list them."""
    bundle_mod = imp("mootcourt.bundle")
    led = make_synth(seed=3, n_tests=60, variants_per_test=2)[0]
    bundle = bundle_mod.fit_bundle(led, "synthetic", "20261103-aaaaaaaaaaaa")
    real = bundle_mod.joblib.dump if hasattr(bundle_mod, "joblib") else None

    def dump_with_companion(obj, path, *a, **k):
        out = real(obj, path, *a, **k)
        (Path(str(path)).parent / ("._" + Path(str(path)).name)).write_bytes(b"\x00\x05")
        return out

    if real is not None:
        monkeypatch.setattr(bundle_mod.joblib, "dump", dump_with_companion)
    bundle_mod.save_bundle(bundle, tmp_path)
    again = bundle_mod.load_bundle(bundle.model_id, tmp_path)
    assert again.model_id == bundle.model_id
