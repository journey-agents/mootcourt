"""T-037 contracts: `moot benchmark --scale N` at N = 2000 (the 1e5 and 1e6 runs are done by hand and documented in docs/scale.md)."""
import json

import pytest
from typer.testing import CliRunner


def _cli(imp, args, root):
    return CliRunner().invoke(imp("mootcourt.cli").app, args, env={"MOOTCOURT_DATA_ROOT": str(root)})


def test_scale_run_writes_the_report_and_the_ledger_under_the_root(imp, tmp_path):
    res = _cli(imp, ["benchmark", "--scale", "2000", "--cards", "40", "--scored-per-origin", "150"], tmp_path)
    assert res.exit_code == 0, res.output
    doc = json.loads((tmp_path / "reports" / "scale-2000.json").read_text())
    assert doc["kind"] == "scale" and doc["n_contrasts"] == 2000 and doc["synthetic"] is True and doc["schema_version"] == 1
    assert set(doc["stages"]) == {"generate", "write_ledger", "fit", "backtest", "cards"}
    assert doc["wall_seconds"] > 0 and doc["peak_rss_bytes"] > 10**6 and doc["peak_rss_gb"] > 0
    lat = doc["card_latency_ms"]
    assert lat["n"] == 40 and 0 < lat["p50_ms"] <= lat["p95_ms"] <= lat["max_ms"]
    assert doc["stages"]["fit"]["n_rows"] == 2000 and doc["stages"]["fit"]["top_m"] == 1000
    assert doc["stages"]["backtest"]["n_scored_rows"] > 0 and {"P0", "P1", "P2"} <= set(doc["stages"]["backtest"]["rungs"])
    assert sum(doc["stages"]["cards"]["statuses"].values()) == 40
    assert (tmp_path / "experiments" / "scale" / "ledger-2000.parquet").is_file()
    assert set(doc["disk_before"]) == set(doc["disk_after"]) and all("free_gb" in v for v in doc["disk_after"].values())
    assert isinstance(doc["under_one_second_per_card"], bool) and isinstance(doc["fit_under_one_hour"], bool)


def test_exactly_one_mode_is_required(imp, tmp_path):
    assert _cli(imp, ["benchmark"], tmp_path).exit_code != 0
    assert _cli(imp, ["benchmark", "--scale", "2000", "--ledger", str(tmp_path / "x.parquet")], tmp_path).exit_code != 0
    assert _cli(imp, ["benchmark", "--scale", "3"], tmp_path).exit_code != 0                     # too small to mean anything


def test_the_scored_sample_thins_only_the_scored_quarters(imp):
    bench = imp("mootcourt.benchmark")
    ledger = bench.make_scale_ledger(4000, seed=3)
    origins = imp("mootcourt.harness").quarterly_origins(ledger)[-2:]
    thin = bench.sample_scored_rows(ledger, origins, 100, seed=9)
    import pandas as pd

    for t in origins:
        window = (thin["started_at"] >= t) & (thin["started_at"] < t + pd.DateOffset(months=3))
        assert int(window.sum()) <= 100
    before = ledger[ledger["started_at"] < origins[0]]
    assert len(thin[thin["started_at"] < origins[0]]) == len(before)
    assert bench.sample_scored_rows(ledger, origins, 100, seed=9)["row_id"].tolist() == thin["row_id"].tolist()


def test_peak_memory_is_read_in_bytes(imp):
    assert imp("mootcourt.benchmark").peak_rss_bytes() > 10 * 1024 * 1024


@pytest.mark.parametrize("n_cards", [0])
def test_zero_cards_is_refused(imp, tmp_path, n_cards):
    assert _cli(imp, ["benchmark", "--scale", "2000", "--cards", str(n_cards)], tmp_path).exit_code != 0
