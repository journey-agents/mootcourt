"""The split-half fit with degrees of freedom and a standard deviation (scripts/split_half_spread.py)."""
import importlib.util
import json
import math
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def sps():
    path = Path(__file__).resolve().parents[1] / "scripts" / "split_half_spread.py"
    spec = importlib.util.spec_from_file_location("split_half_spread", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_sd_is_none_when_the_tail_has_no_variance(sps):
    assert sps.sd_or_none(tau=1.0, nu=2.0) is None
    assert sps.sd_or_none(tau=1.0, nu=float("inf")) == pytest.approx(1.0)
    assert sps.sd_or_none(tau=1.0, nu=3.0) == pytest.approx(3 ** 0.5)


def test_the_document_matches_the_report_and_writes_infinity_as_a_word(sps, tmp_path):
    from mootcourt import harness_stats as hs
    from mootcourt.ledger import write_ledger
    from mootcourt.sources import synthetic as synth

    ledger = synth.generate(synth.SyntheticConfig(seed=3, n_tests=400, variants_per_test=2))[0]
    origin = ledger["started_at"].max().floor("D")
    old = hs.split_half(ledger, origin)
    report = {"header": {"last_origin": origin.isoformat()},
              "tables": {"split_half": [{"cell": c, **{k: v[k] for k in ("mu_odd", "mu_even", "tau_odd", "tau_even")}} for c, v in old.items()]}}
    doc = sps.build(ledger, report)
    assert doc["matches_report"] is True and set(doc["split_half"]) == set(old)
    for cell, row in doc["split_half"].items():
        for half in ("odd", "even"):
            nu = row[f"nu_{half}"]
            assert nu == "inf" or nu > 2
            want = row[f"tau_{half}"] if nu == "inf" else row[f"tau_{half}"] * math.sqrt(nu / (nu - 2))
            assert row[f"sd_{half}"] == pytest.approx(want)
    json.dumps(doc, allow_nan=False)          # nothing in it needs a non-standard number
    report["tables"]["split_half"][0]["mu_odd"] += 1.0
    assert sps.build(ledger, report)["matches_report"] is False
    ledger_path = tmp_path / "ledger.parquet"
    write_ledger(ledger, ledger_path)
    (tmp_path / "r.json").write_text(json.dumps(report))
    assert sps.main(["--ledger", str(ledger_path), "--report", str(tmp_path / "r.json"), "--out", str(tmp_path / "o.json")]) == 1
