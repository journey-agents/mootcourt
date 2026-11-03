"""T-015 contracts: report writer, figures, reliability seed, backtest CLI."""
import json
import re

import numpy as np
import pandas as pd
import pytest

EM, EN = chr(0x2014), chr(0x2013)


@pytest.fixture
def scores(imp, make_synth):
    harness = imp("mootcourt.harness")
    ledger = make_synth(seed=95, n_tests=240, variants_per_test=2,
                        cell_params={"headline_only": (1.0, 2.0)}, s_scale=2.0)[0]

    def p0(rows, origin):
        return imp("mootcourt.predictors.p0").P0Predictor().fit(rows)

    def p1(rows, origin):
        return imp("mootcourt.predictors.p1").P1Predictor().fit(rows)

    return ledger, harness.rolling_origin(ledger, {"P0": p0, "P1": p1}, harness.quarterly_origins(ledger))


def _write(imp, scores_pair, tmp_path, source="synthetic", gates=None, **kw):
    ledger, sc = scores_pair
    report = imp("mootcourt.report")
    command = kw.pop("command", f"moot backtest --source {source} --origins quarterly")
    return report.write_report(
        sc, ledger=ledger, source=source, snapshot_id="20261102-eeeeeeeeeeee", model_id="m123456789ab",
        feature_hash="f123456789ab", command=command, seed=0,
        gates=gates or {"n_200": 200, "n_400": 400}, out_dir=tmp_path, **kw)


def test_files_named_by_source_and_snapshot(imp, scores, tmp_path):
    paths = _write(imp, scores, tmp_path)
    assert paths.md == tmp_path / "backtest-synthetic-20261102-eeeeeeeeeeee.md"
    assert paths.json == tmp_path / "backtest-synthetic-20261102-eeeeeeeeeeee.json"
    assert paths.md.exists() and paths.json.exists()
    for name in ("reliability", "score_by_origin", "coverage", "decision_value"):
        png = paths.figures[name]
        assert png.suffix == ".png" and png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_json_and_markdown_carry_the_same_numbers(imp, scores, tmp_path):
    paths = _write(imp, scores, tmp_path)
    md = paths.md.read_text(encoding="utf-8")
    data = json.loads(paths.json.read_text(encoding="utf-8"))
    agg = data["tables"]["aggregate"]
    assert agg
    for row in agg:
        for key, v in row.items():
            if isinstance(v, float) and np.isfinite(v):
                assert f"{v:.4f}" in md, f"{key}={v} from JSON missing in Markdown"
    for row in data["tables"]["decision_value"]:
        for key, v in row.items():
            if isinstance(v, float) and np.isfinite(v):
                assert f"{v:.4f}" in md


def test_header_carries_provenance_and_synthetic_label(imp, scores, tmp_path):
    paths = _write(imp, scores, tmp_path)
    md = paths.md.read_text(encoding="utf-8")
    head = json.loads(paths.json.read_text(encoding="utf-8"))["header"]
    for key in ("source", "snapshot_id", "model_id", "feature_hash", "command", "seed"):
        assert key in head
    assert head["snapshot_id"] in md and head["model_id"] in md and head["feature_hash"] in md
    assert head["command"] in md and "synthetic" in md.lower()
    assert "observed estimate with known standard error" in md


def test_non_synthetic_source_has_no_synthetic_label(imp, scores, tmp_path):
    ledger, sc = scores
    paths = _write(imp, (ledger.assign(source="upworthy"), sc), tmp_path, source="upworthy")
    assert "synthetic" not in paths.md.read_text(encoding="utf-8").lower()


def test_small_n_renders_undecidable_rows_not_blanks(imp, scores, tmp_path):
    paths = _write(imp, scores, tmp_path, gates={"n_200": 10 ** 6, "n_400": 10 ** 7})
    md = paths.md.read_text(encoding="utf-8")
    assert md.count("undecidable at this n") >= 2
    assert not re.search(r"\bnan\b", md.lower())


def test_report_text_has_no_dashes_or_role_noun(imp, scores, tmp_path):
    paths = _write(imp, scores, tmp_path)
    text = paths.md.read_text(encoding="utf-8") + paths.json.read_text(encoding="utf-8")
    assert EM not in text and EN not in text and not re.search(r"\bown" + r"er\b", text, re.I)


def test_reliability_report_is_seeded_from_scores(imp, scores, tmp_path):
    ledger, sc = scores
    path = imp("mootcourt.report").write_reliability(sc, source="synthetic", out_dir=tmp_path,
                                                     as_of=pd.Timestamp("2014-07-15T12:00:00Z").to_pydatetime())
    assert path == tmp_path / "reliability-synthetic.json"
    rep = json.loads(path.read_text())
    cell = rep["cells"]["headline_only"]
    assert set(cell) >= {"as_of", "rolling_logscore", "p0_rolling_logscore", "brier_skill", "n", "drifted", "consecutive_below"}
    assert cell["drifted"] is False and cell["n"] > 0
    ab = imp("mootcourt.abstain")
    assert ab.check_reliability(rep, "headline_only", pd.Timestamp("2014-07-16T00:00:00Z").to_pydatetime()) is False


@pytest.mark.slow
def test_backtest_cli_end_to_end(imp, tmp_path, monkeypatch):
    from typer.testing import CliRunner

    app = imp("mootcourt.cli").app
    monkeypatch.chdir(tmp_path)
    for d in ("data/ledger", "reports", "models"):
        (tmp_path / d).mkdir(parents=True)
    runner = CliRunner()
    assert runner.invoke(app, ["simulate", "ledger", "--out", "data/ledger/ledger.parquet"]).exit_code == 0
    res = runner.invoke(app, ["backtest", "--source", "synthetic", "--origins", "quarterly"])
    assert res.exit_code == 0, res.output
    assert list((tmp_path / "reports").glob("backtest-synthetic-*.md"))
    assert list((tmp_path / "reports").glob("backtest-synthetic-*.json"))
    assert (tmp_path / "reports" / "reliability-synthetic.json").exists()
