"""T-034 contracts: the ledger exchange format, the vendor importers, the conformance checker and the ingest command."""
import math
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "importers"
UTC_NOW = pd.Timestamp("2026-01-01", tz="UTC").to_pydatetime()


def _imp(imp):
    return imp("mootcourt.importers")


def _read(imp, fmt, name, **kw):
    return _imp(imp).read_format(fmt, FIX / name, **kw)


def _good(**over):
    row = {"experiment_id": "e1", "variant_id": "v", "metric_id": "m", "effect": "0.1", "se": "0.05", "n_baseline": "1000", "n_variant": "1000",
           "started_at": "2024-01-01T00:00:00Z", "ended_at": "2024-01-15T00:00:00Z", "source_system": "test", "variance_method": "normal"}
    row.update(over)
    return row


def _frame(*rows):
    return pd.DataFrame(list(rows), dtype=str)


# ---------------------------------------------------------------- the exchange format
def test_clean_file_has_no_violations(imp):
    assert _imp(imp).check_exchange(_frame(_good()), UTC_NOW) == []


def test_missing_required_column_is_named(imp):
    df = _frame(_good()).drop(columns=["se", "ended_at"])
    got = _imp(imp).check_exchange(df, UTC_NOW)
    assert {v.column for v in got} == {"se", "ended_at"} and all(v.severity == "error" and v.row == 0 for v in got)


def test_violations_name_the_row_and_the_column(imp):
    rows = [_good(), _good(variant_id="v2", effect="abc"), _good(variant_id="v3", se="-1"), _good(variant_id="v4", n_baseline="-5"),
            _good(variant_id="v5", ended_at="2023-12-01T00:00:00Z"), _good(variant_id="v6", started_at="not a date"),
            _good(variant_id="v7", ended_at="2030-01-01T00:00:00Z"), _good(variant_id="v8", usable_after="2024-01-02T00:00:00Z"),
            _good(variant_id="v2", effect="0.2")]
    got = {(v.row, v.column): v for v in _imp(imp).check_exchange(_frame(*rows), UTC_NOW)}
    assert (2, "effect") in got and "not a number" in got[(2, "effect")].message
    assert (3, "se") in got and "greater than zero" in got[(3, "se")].message
    assert (4, "n_baseline") in got and "negative" in got[(4, "n_baseline")].message
    assert (5, "ended_at") in got and "before started_at" in got[(5, "ended_at")].message
    assert (6, "started_at") in got
    assert (7, "ended_at") in got and "future" in got[(7, "ended_at")].message
    assert (8, "usable_after") in got and "horizon" in got[(8, "usable_after")].message
    assert (9, "variant_id") in got and "duplicate of row 2" in got[(9, "variant_id")].message
    assert str(got[(3, "se")]).startswith("error: row 3, column se")


def test_missing_provenance_and_missing_se_are_warnings_not_errors(imp):
    df = _frame(_good(se="")).drop(columns=["variance_method"])
    got = _imp(imp).check_exchange(df, UTC_NOW)
    assert got and all(v.severity == "warning" for v in got)
    assert {v.column for v in got} == {"se", "variance_method"}
    assert _imp(imp).errors_of(got) == []


def test_to_ledger_maps_rows_statuses_and_keys(imp):
    ex = imp("mootcourt.importers.exchange")
    rows = [_good(), _good(variant_id="small", n_variant="10"), _good(variant_id="nose", se=""), _good(variant_id="srm", srm_flag="true"),
            _good(variant_id="same", baseline_id="same"), _good(variant_id="m2", metric_id="m2", cell="area_x")]
    led = ex.to_ledger(_frame(*rows), "acme", now=UTC_NOW)
    by = led.set_index("variant_id")
    assert by.loc["v::m", "status"] == "admitted" and by.loc["small::m", "status"] == "low_exposure"
    assert by.loc["nose::m", "status"] == "low_exposure" and '"missing_variance"' in by.loc["nose::m", "features_json"]
    assert by.loc["srm::m", "status"] == "imbalance_flag" and by.loc["same::m", "status"] == "duplicate_arm"
    assert by.loc["m2::m2", "cell"] == "area_x" and by.loc["v::m", "cell"] == "m"
    r = by.loc["v::m"]
    assert r["row_id"] == "acme:e1:v::m" and r["test_id"] == "e1" and r["source"] == "acme" and r["period"] == "2024Q1"
    assert r["usable_after"] == r["final_read_at"] == pd.Timestamp("2024-01-15", tz="UTC")
    assert '"source_system": "test"' in r["features_json"]
    delayed = ex.to_ledger(_frame(_good()), "acme", usable_delay_days=3, now=UTC_NOW)
    assert delayed["usable_after"].iloc[0] == pd.Timestamp("2024-01-18", tz="UTC")


def test_to_ledger_refuses_a_file_with_errors(imp):
    with pytest.raises(_imp(imp).ExchangeError) as exc:
        imp("mootcourt.importers.exchange").to_ledger(_frame(_good(se="0")), "acme", now=UTC_NOW)
    assert "row 1, column se" in str(exc.value)


def test_delta_method_ratio_variance(imp):
    # equal arms, independent numerator and denominator: Var(R) = (vn / md^2 + mn^2 vd / md^4) / n per arm
    eff, se = _imp(imp).delta_method_ratio_se(100, 2.0, 4.0, 1.0, 0.5, 0.0, 100, 2.4, 4.0, 1.0, 0.5, 0.0)
    v = (1.0 / 16.0 + 4.0 * 0.5 / 256.0) / 100
    v2 = (1.0 / 16.0 + 2.4 ** 2 * 0.5 / 256.0) / 100
    assert eff == pytest.approx(0.6 - 0.5) and se == pytest.approx(math.sqrt(v + v2))
    with pytest.raises(ValueError):
        _imp(imp).delta_method_ratio_se(0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0)


# ---------------------------------------------------------------- one test file per format
def test_statsig_view_takes_the_latest_day_and_a_halfwidth(imp):
    d = _read(imp, "statsig", "statsig_view.csv").set_index(["experiment_id", "metric_id"])
    a = d.loc[("exp_a", "m1")]
    assert a["effect"] == pytest.approx(1.0) and a["se"] == pytest.approx(0.392 / 1.959964, rel=1e-5)
    assert a["n_baseline"] == 5000 and a["n_variant"] == 5200 and a["baseline_id"] == "Control" and a["variant_id"] == "Test"
    assert a["started_at"].endswith("Z") and "half-width" in a["variance_method"] and bool(a["cuped"]) is True
    assert len(d) == 3                                              # the earlier daily row of exp_a / m1 is dropped
    rel = _read(imp, "statsig", "statsig_view.csv", effect_scale="relative").set_index(["experiment_id", "metric_id"]).loc[("exp_a", "m1")]
    assert rel["effect"] == pytest.approx(0.10) and rel["effect_unit"] == "relative"
    wide = _read(imp, "statsig", "statsig_view.csv", ci_level=0.90).set_index(["experiment_id", "metric_id"]).loc[("exp_a", "m1")]
    assert wide["se"] == pytest.approx(0.392 / 1.644854, rel=1e-5)


def test_statsig_view_missing_column_is_a_clear_error(imp, tmp_path):
    p = tmp_path / "v.csv"
    pd.read_csv(FIX / "statsig_view.csv").drop(columns=["controlUnits"]).to_csv(p, index=False)
    with pytest.raises(_imp(imp).MappingError, match="controlUnits"):
        _imp(imp).read_format("statsig", p)


def test_optimizely_pairs_each_variation_with_its_baseline(imp):
    d = _read(imp, "optimizely", "optimizely.csv", experiment_id="opt1").set_index("metric_id")
    s = d.loc["signup_id"]
    assert s["variant_id"] == "v1" and s["baseline_id"] == "v0" and s["effect"] == pytest.approx(0.15)
    assert s["se"] == pytest.approx(0.30 / (2 * 1.644854), rel=1e-5) and s["n_baseline"] == 4000 and s["n_variant"] == 4000
    assert d.loc["purchase_id", "effect"] == pytest.approx(-0.05) and "assumed" in s["variance_method"]
    assert len(d) == 2
    with pytest.raises(_imp(imp).MappingError, match="--experiment-id"):
        _read(imp, "optimizely", "optimizely.csv")


def test_harness_csv_and_json(imp):
    c = _read(imp, "harness", "harness.csv", experiment_id="checkout_flow").set_index("metric_id")
    assert c.loc["checkout", "effect"] == pytest.approx(0.08) and c.loc["checkout", "se"] == pytest.approx(0.16 / (2 * 1.959964), rel=1e-5)
    assert c.loc["checkout", "variant_id"] == "on" and c.loc["checkout", "baseline_id"] == "off" and c.loc["checkout", "n_variant"] == 3050
    j = _read(imp, "harness", "harness.json").iloc[0]
    assert j["experiment_id"] == "checkout_flow" and j["effect"] == pytest.approx(0.08) and j["se"] == pytest.approx(c.loc["checkout", "se"])
    assert bool(j["srm_flag"]) is False
    with pytest.raises(_imp(imp).MappingError, match="--experiment-id"):
        _read(imp, "harness", "harness.csv")


def test_growthbook_result_and_bulk_snapshots(imp):
    r = _read(imp, "growthbook", "growthbook_result.json").iloc[0]
    assert r["experiment_id"] == "exp_gb" and r["variant_id"] == "1" and r["baseline_id"] == "0" and r["metric_id"] == "met_a"
    assert r["effect"] == pytest.approx(0.04) and r["se"] == pytest.approx(0.02) and r["n_baseline"] == 4500
    assert r["effect_unit"] == "relative" and "frequentist" in r["variance_method"]
    b = _read(imp, "growthbook", "growthbook_result.json", engine="bayesian").iloc[0]
    assert b["effect"] == pytest.approx(0.05) and b["se"] == pytest.approx(0.03)
    snap = _read(imp, "growthbook", "growthbook_bulk.json")
    assert len(snap) == 1 and snap.iloc[0]["effect"] == pytest.approx(0.04)          # the latest snapshot is the final read
    assert snap.iloc[0]["ended_at"] == "2024-06-15T00:00:00Z"


def test_jetstream_keeps_the_last_window_and_needs_the_missing_context(imp):
    kw = dict(experiment_id="nimbus1", started_at="2024-04-01T00:00:00Z", ended_at="2024-04-30T00:00:00Z", n_baseline=20000, n_variant=20100)
    d = _read(imp, "jetstream", "jetstream.csv", **kw)
    assert len(d) == 1
    r = d.iloc[0]
    assert r["effect"] == pytest.approx(0.05) and r["se"] == pytest.approx(0.08 / (2 * 1.959964), rel=1e-5)
    assert r["variant_id"] == "treatment" and r["baseline_id"] == "control" and r["effect_unit"] == "relative"
    diff = _read(imp, "jetstream", "jetstream.csv", comparison="difference", **kw).iloc[0]
    assert diff["effect"] == pytest.approx(0.5) and diff["effect_unit"] == "absolute"
    with pytest.raises(_imp(imp).MappingError, match="--n-baseline"):
        _read(imp, "jetstream", "jetstream.csv", experiment_id="x", started_at="a", ended_at="b", n_variant=1)


def test_eppo_needs_a_mapping_and_says_where_the_template_is(imp):
    with pytest.raises(_imp(imp).MappingError, match=r"examples/mappings/eppo\.toml"):
        _read(imp, "eppo", "eppo_export.csv")
    m = _imp(imp).load_mapping(FIX / "eppo_mapping.toml")
    d = _read(imp, "eppo", "eppo_export.csv", mapping=m).iloc[0]
    assert d["experiment_id"] == "e1" and float(d["effect"]) == pytest.approx(0.02)
    assert float(d["se"]) == pytest.approx(0.08 / (2 * 1.959964), rel=1e-5)
    assert int(d["n_baseline"]) == 7000 and d["source_system"] == "eppo"


def test_shipped_templates_parse_and_are_marked_as_templates(imp):
    for name in ("eppo", "statsig-csv", "generic"):
        m = _imp(imp).load_mapping(ROOT / "examples" / "mappings" / f"{name}.toml")
        assert set(m) == {"columns", "constants", "options"}
    assert "TEMPLATE ONLY" in (ROOT / "examples" / "mappings" / "eppo.toml").read_text(encoding="utf-8")


def test_mapping_names_a_missing_input_column(imp, tmp_path):
    m = {"columns": {"experiment_id": "nope"}}
    with pytest.raises(_imp(imp).MappingError, match="'nope'"):
        _imp(imp).read_format("generic", FIX / "eppo_export.csv", mapping=m)


def test_generic_reads_the_exchange_columns_from_csv_and_parquet(imp, tmp_path):
    csv = ROOT / "examples" / "ledgers" / "sample.csv"
    a = _imp(imp).read_format("generic", csv)
    assert len(a) == 360 and set(a.columns) >= set(imp("mootcourt.importers.exchange").REQUIRED)
    pq = tmp_path / "s.parquet"
    pd.read_csv(csv).to_parquet(pq, index=False)
    b = _imp(imp).read_format("generic", pq)
    assert _imp(imp).check_exchange(b, UTC_NOW) == [] and len(b) == 360


def test_unknown_format_lists_the_formats(imp):
    with pytest.raises(ValueError, match="statsig"):
        _imp(imp).read_format("nope", FIX / "harness.csv")


def test_sample_file_matches_the_generator_and_conforms(imp):
    sample = imp("mootcourt.importers.sample").sample_exchange()
    assert (ROOT / "examples" / "ledgers" / "sample.csv").read_text(encoding="utf-8") == sample.to_csv(index=False)
    assert _imp(imp).check_exchange(sample.astype(str), UTC_NOW) == []


# ---------------------------------------------------------------- the commands
def _cli(imp):
    return imp("mootcourt.cli").app


def test_ingest_dry_run_prints_the_admission_summary_and_writes_nothing(imp, tmp_path):
    ledger = tmp_path / "l" / "ledger.parquet"
    res = CliRunner().invoke(_cli(imp), ["ingest", "--format", "generic", "--input", str(ROOT / "examples/ledgers/sample.csv"),
                                         "--source-name", "sample", "--ledger", str(ledger), "--dry-run"])
    assert res.exit_code == 0, res.output
    assert "360 rows from 120 experiments" in res.output and "admitted: 360" in res.output and "checkout_conversion 120" in res.output
    assert "dry run" in res.output and not ledger.exists()


def test_ingest_writes_the_ledger_and_is_idempotent(imp, tmp_path):
    ledger = tmp_path / "l" / "ledger.parquet"
    args = ["ingest", "--format", "growthbook", "--input", str(FIX / "growthbook_result.json"), "--source-name", "gb", "--ledger", str(ledger)]
    assert CliRunner().invoke(_cli(imp), args).exit_code == 0
    again = CliRunner().invoke(_cli(imp), args)
    assert again.exit_code == 0, again.output
    df = imp("mootcourt.ledger").read_ledger(ledger)
    assert len(df) == 1 and df["source"].iloc[0] == "gb" and df["status"].iloc[0] == "admitted"


def test_ingest_error_names_row_and_column_and_exits_1(imp, tmp_path):
    bad = tmp_path / "bad.csv"
    pd.read_csv(ROOT / "examples/ledgers/sample.csv").assign(se=lambda d: d["se"].where(d.index != 4, -1.0)).to_csv(bad, index=False)
    res = CliRunner().invoke(_cli(imp), ["ingest", "--format", "generic", "--input", str(bad), "--ledger", str(tmp_path / "l.parquet"), "--dry-run"])
    assert res.exit_code == 1 and "row 5, column se" in res.output


def test_ingest_template_format_without_mapping_fails_clearly(imp, tmp_path):
    args = ["ingest", "--format", "eppo", "--input", str(FIX / "eppo_export.csv"), "--ledger", str(tmp_path / "l.parquet")]
    res = CliRunner().invoke(_cli(imp), args)
    assert res.exit_code == 1 and "examples/mappings/eppo.toml" in res.output


def test_ledger_check_exit_codes(imp, tmp_path):
    ok = CliRunner().invoke(_cli(imp), ["ledger", "check", str(ROOT / "examples/ledgers/sample.csv")])
    assert ok.exit_code == 0 and "conforms" in ok.output
    bad = tmp_path / "bad.csv"
    df = pd.read_csv(ROOT / "examples/ledgers/sample.csv")
    df.loc[2, "ended_at"] = "2099-01-01T00:00:00Z"
    df = pd.concat([df, df.iloc[[0]]]).drop(columns=["variance_method"])
    df.to_csv(bad, index=False)
    res = CliRunner().invoke(_cli(imp), ["ledger", "check", str(bad)])
    assert res.exit_code == 1
    assert "row 3, column ended_at" in res.output and "duplicate of row 1" in res.output and "variance_method" in res.output and "FAIL" in res.output
    missing = CliRunner().invoke(_cli(imp), ["ledger", "check", str(tmp_path / "nope.csv")])
    assert missing.exit_code == 1


def test_ledger_check_on_a_ledger_file(imp, tmp_path):
    ledger = tmp_path / "l.parquet"
    CliRunner().invoke(_cli(imp), ["ingest", "--format", "generic", "--input", str(ROOT / "examples/ledgers/sample.csv"), "--source-name", "sample",
                                   "--ledger", str(ledger)])
    res = CliRunner().invoke(_cli(imp), ["ledger", "check", str(ledger)])
    assert res.exit_code == 0, res.output
    led = imp("mootcourt.ledger").read_ledger(ledger)
    led.loc[led.index[0], "usable_after"] = led["final_read_at"].iloc[0] - pd.Timedelta(days=1)
    imp("mootcourt.ledger").write_ledger(led, tmp_path / "bad.parquet")
    res = CliRunner().invoke(_cli(imp), ["ledger", "check", str(tmp_path / "bad.parquet")])
    assert res.exit_code == 1 and "horizon" in res.output


def test_formats_command_separates_documented_from_template(imp):
    res = CliRunner().invoke(_cli(imp), ["ledger", "formats"])
    assert res.exit_code == 0
    lines = {ln.split(":")[0]: ln for ln in res.output.splitlines()}
    assert "documented mapping" in lines["growthbook"] and "template" in lines["eppo"]
    assert set(lines) >= {"generic", "statsig", "harness", "jetstream"}


def test_the_format_document_covers_every_format_and_says_which_are_templates():
    text = " ".join((ROOT / "docs" / "ledger-format.md").read_text(encoding="utf-8").split())
    for name in ("generic", "statsig", "optimizely", "harness", "growthbook", "jetstream", "eppo"):
        assert f"`{name}`" in text
    for col in ("experiment_id", "variant_id", "metric_id", "effect", "se", "n_baseline", "usable_after", "variance_method", "source_system"):
        assert f"`{col}`" in text
    assert "not documented publicly" in text and "template" in text and "delta method" in text and "examples/ledgers/sample.csv" in text
    assert "https://docs.growthbook.io/api/experiments/operation/getExperimentResults" in text
