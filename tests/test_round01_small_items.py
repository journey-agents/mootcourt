"""T-075 items 2 to 5 (round 01): the precedent rung's docstring, the sample ledger's base rate, the defaulted-reference line on the card,
and the per-platform score report of the continuous-integration job.
"""
from __future__ import annotations

import importlib
import importlib.util
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from test_review_l import fresh_report, upworthy_like

ROOT = Path(__file__).resolve().parents[1]


def _script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------ item 2: the module docstring of the precedent rung (R3 nit 2)
def test_the_p2_docstring_says_what_the_rung_is_and_measures_the_guard_on_validation_rows():
    doc = importlib.import_module("mootcourt.predictors.p2").__doc__
    head = doc[:2500]
    phrases = ("P1's predictive family", "location", "scale", "admission guard", "lambda-zero identity", "validation rows", '"loto"', '"forward"')
    for phrase in phrases:
        assert phrase in head, phrase
    assert "beats the rung below out of sample by more than noise" not in doc
    assert "transfers out of time" in doc or "realized out-of-time" in doc


# ------------------------------------------------------------------ item 3: the sample ledger's base rate (R6 minor 6, question 5)
def _rate(frame: pd.DataFrame) -> float:
    return float((frame["effect"] > 1.96 * frame["se"]).mean())


def test_the_sample_generator_has_a_base_rate_parameter_whose_default_is_near_the_headline_archive():
    from mootcourt.importers import sample

    assert sample.SAMPLE_BASE_RATE == pytest.approx(0.09)
    default = sample.sample_exchange()
    assert len(default) == 360 and default["experiment_id"].nunique() == 120               # the fixture stays small
    assert 0.05 <= _rate(default) <= 0.13                                                  # one draw of 360 rows around 0.09
    assert default.equals(sample.sample_exchange(base_rate=sample.SAMPLE_BASE_RATE))
    legacy = sample.sample_exchange(base_rate=None)                                        # the earlier fixed means
    assert _rate(legacy) > 0.15 and _rate(sample.sample_exchange(base_rate=0.30)) > _rate(default)
    assert (ROOT / "examples" / "ledgers" / "sample.csv").read_text(encoding="utf-8") == default.to_csv(index=False)


def test_moot_init_writes_quick_gates_at_the_sample_base_rate(tmp_path):
    from mootcourt import onboarding

    assert onboarding.QUICK_GATE_BASE == pytest.approx(0.09)
    got = onboarding.init_project(tmp_path / "proj")
    gates = json.loads(Path(got["gates"]).read_text())
    assert list(gates["by_base_rate"]) == ["0.09"] and gates["by_base_rate"]["0.09"]["n_200"] >= 100
    assert pd.read_csv(got["sample_ledger"]).shape[0] == 360


# ------------------------------------------------------------------ item 4: the card says when the reference headline was defaulted (R2 question 2)
def _bundle(ledger, as_of):
    from mootcourt.bundle import fit_bundle

    return fit_bundle(ledger, "upworthy", "20261104-tttttttttttt", as_of=as_of)


def test_the_card_prints_a_line_when_the_reference_headline_was_defaulted_and_not_when_it_was_given():
    from mootcourt import card as card_mod

    ledger = upworthy_like()
    origin = pd.Timestamp("2014-07-01", tz="UTC")
    bundle = _bundle(ledger, origin)
    assert bundle.space.pairwise
    common = dict(source="upworthy", headline="a headline with no reference given", image_changed=False, impressions=20000,
                  origin=origin.to_pydatetime(), cell="headline_only")
    without = card_mod.build_card(bundle, card_mod.CardRequest(**common), reliability=fresh_report(origin), now=origin.to_pydatetime())
    with_ref = card_mod.build_card(bundle, card_mod.CardRequest(**common, reference_headline="the reference headline"),
                                   reliability=fresh_report(origin), now=origin.to_pydatetime())
    assert without.request.reference_defaulted is True and with_ref.request.reference_defaulted is False
    md = card_mod.to_markdown(without)
    assert "Reference headline: not supplied" in md and "fit-set mean" in md
    assert "Reference headline: not supplied" not in card_mod.to_markdown(with_ref)
    assert card_mod.to_json(without)["request"]["reference_defaulted"] is True
    assert "reference_defaulted" in card_mod.__doc__


def test_a_ledger_without_reference_headlines_never_marks_the_reference_as_defaulted(tmp_path):
    from mootcourt import card as card_mod
    from mootcourt.bundle import fit_bundle
    from mootcourt.sources.synthetic import SyntheticConfig, generate

    ledger, _ = generate(SyntheticConfig(seed=1, n_tests=200))
    origin = pd.Timestamp("2014-07-01", tz="UTC")
    bundle = fit_bundle(ledger, "synthetic", "20261104-ssssssssssss", as_of=origin)
    assert not bundle.space.pairwise
    req = card_mod.CardRequest(source="synthetic", headline="a plain headline", image_changed=False, impressions=20000,
                               origin=origin.to_pydatetime(), cell="headline_only")
    c = card_mod.build_card(bundle, req, reliability=fresh_report(origin), now=origin.to_pydatetime())
    assert c.request.reference_defaulted is False and "Reference headline: not supplied" not in card_mod.to_markdown(c)


# ------------------------------------------------------------------ item 5: the per-platform score report (R5 minor 8)
def test_the_score_report_is_deterministic_names_the_platform_and_carries_the_three_rungs_to_six_decimals(tmp_path):
    mod = _script("ci_score_report")
    first = mod.build_report()
    second = mod.build_report()
    assert first["rungs"] == second["rungs"] and set(first["rungs"]) == {"P0", "P1", "P2"}
    for rung, rec in first["rungs"].items():
        for key in ("logscore", "brier_skill"):
            assert isinstance(rec[key], float) and rec[key] == round(rec[key], 6), (rung, key)
        assert rec["rows"] > 100 and rec["tests"] > 30
    assert first["rungs"]["P0"]["brier_skill"] == 0.0 and first["rungs"]["P1"]["logscore"] > first["rungs"]["P0"]["logscore"]
    assert first["python"] == ".".join(str(v) for v in sys.version_info[:3]) and first["platform"]
    assert first["ledger"]["generator"].startswith("mootcourt.importers.sample")
    out = tmp_path / "score-report-x.json"
    assert mod.main(["--out", str(out)]) == 0
    doc = json.loads(out.read_text())
    assert doc["rungs"] == first["rungs"] and doc["seed"] == 0


def test_the_ci_workflow_runs_the_score_report_on_every_python_and_uploads_it():
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "scripts/ci_score_report.py" in text
    assert re.search(r"score-report-\$\{\{ matrix\.python-version \}\}\.json", text)
    assert "actions/upload-artifact@" in text.split("scripts/ci_score_report.py", 1)[1]
    assert np.all([v in text for v in ('"3.11"', '"3.12"', '"3.13"')])
