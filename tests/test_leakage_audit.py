"""Builder additions (T-022): the post-hoc leakage audit passes on a clean backtest and fails on a leaked one."""
import subprocess
import sys
from pathlib import Path

import pandas as pd

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "leakage_audit.py"


def _setup(imp, make_synth, tmp_path):
    harness = imp("mootcourt.harness")
    ledger = make_synth(seed=95, n_tests=120, variants_per_test=2, cell_params={"headline_only": (1.0, 2.0)}, s_scale=2.0)[0]
    p0 = imp("mootcourt.predictors.p0").P0Predictor
    scores = harness.rolling_origin(ledger, {"P0": lambda r, o: p0().fit(r)}, harness.quarterly_origins(ledger))
    imp("mootcourt.ledger").write_ledger(ledger, tmp_path / "ledger.parquet")
    scores.to_parquet(tmp_path / "scores.parquet")
    return ledger, scores


def _run(tmp_path):
    return subprocess.run([sys.executable, str(SCRIPT), "--ledger", str(tmp_path / "ledger.parquet"), "--scores", str(tmp_path / "scores.parquet"),
                           "--out", str(tmp_path / "audit.txt")], capture_output=True, text=True)


def test_clean_backtest_passes_with_a_written_log(imp, make_synth, tmp_path):
    _setup(imp, make_synth, tmp_path)
    r = _run(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    log = (tmp_path / "audit.txt").read_text()
    assert "total violations: 0" in log and "rows both fit and scored 0" in log and "PASS" in log


def test_scoring_a_row_at_an_origin_after_it_became_usable_is_flagged(imp, make_synth, tmp_path):
    ledger, scores = _setup(imp, make_synth, tmp_path)
    early = scores["origin"].min()
    # a row scored at the last origin although it belongs to the first window: it was usable by then, so it is flagged
    leaked = scores[scores["origin"] == early].iloc[:1].copy()
    leaked["origin"] = scores["origin"].max()
    pd.concat([scores, leaked], ignore_index=True).to_parquet(tmp_path / "scores.parquet")
    r = _run(tmp_path)
    assert r.returncode == 1 and "FAIL" in r.stdout
