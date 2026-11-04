"""T-042 contracts: the P2 admission guard (lambda above zero only when its selection gain clears the noise)."""
import functools
import math

import numpy as np
import pytest
import typer

NULL_SEEDS = range(24)
STRONG = 4.0


def _fit(imp, seed, strength, n_tests=300, **kw):
    syn, feats = imp("mootcourt.sources.synthetic"), imp("mootcourt.features")
    p1m, p2m = imp("mootcourt.predictors.p1"), imp("mootcourt.predictors.p2")
    ledger, _ = syn.generate(syn.SyntheticConfig(seed=seed, n_tests=n_tests, variants_per_test=2, text_effect_strength=strength))
    return p2m.P2Predictor().fit(ledger, feats.FeatureSpace.fit(ledger), p1m.P1Predictor().fit(ledger), **kw)


@functools.lru_cache(maxsize=None)
def _null_summaries(guard_key):
    import importlib

    guard = None if guard_key == "off" else guard_key
    out = []
    for seed in NULL_SEEDS:
        out += _fit(importlib.import_module, seed, 0.0, guard=guard).selection_summary()
    return tuple(out)


def test_cluster_standard_error_matches_the_hand_computation(imp):
    p2 = imp("mootcourt.predictors.p2")
    g, se = p2.gain_and_se(np.array([1.0, 1.0, -1.0, -1.0]), np.array([0, 0, 1, 1]))
    assert g == 0.0 and se == pytest.approx(1.0)                      # two tests, perfectly clustered
    g, se = p2.gain_and_se(np.array([1.0, -1.0, 1.0, -1.0]), np.array([0, 1, 2, 3]))
    assert se == pytest.approx(math.sqrt(16.0 / 3.0) / 4.0)           # four singletons: T / (T - 1) = 4 / 3
    assert p2.gain_and_se(np.array([1.0, 2.0]), np.array([7, 7]))[1] == math.inf   # one test: no standard error
    assert p2.gain_and_se(np.array([]), np.array([]))[1] == math.inf


def test_clustering_widens_the_standard_error(imp):
    p2 = imp("mootcourt.predictors.p2")
    rng = np.random.default_rng(0)
    base = rng.normal(0.0, 1.0, 100)
    gain = np.repeat(base, 2) + rng.normal(0.0, 0.1, 200)             # two rows per test share a common component
    _, se_clustered = p2.gain_and_se(gain, np.repeat(np.arange(100), 2))
    _, se_naive = p2.gain_and_se(gain, np.arange(200))
    assert se_clustered > 1.2 * se_naive


def test_guard_default_is_a_config_constant_and_validated(imp):
    cfg, p2 = imp("mootcourt.config"), imp("mootcourt.predictors.p2")
    assert cfg.P2_GUARD_MULT > 0 and p2.P2Predictor().guard == cfg.P2_GUARD_MULT
    with pytest.raises(ValueError):
        _fit(imp, 1, 0.0, n_tests=60, guard=-0.5)


def test_no_precedent_signal_keeps_lambda_at_zero_in_at_least_90_percent_of_cells():
    cells = _null_summaries(2.0)
    zero = sum(1 for r in cells if r["lambda"] == 0.0)
    assert len(cells) >= 60
    assert zero / len(cells) >= 0.90, f"{zero} of {len(cells)} cells at lambda 0"


def test_the_guard_is_what_removes_the_false_admissions():
    default = [r for r in _null_summaries(2.0) if r["lambda"] > 0]
    off = [r for r in _null_summaries("off") if r["lambda"] > 0]
    assert len(off) > 2 * len(default) and len(off) / len(_null_summaries("off")) > 0.3     # the earlier rule fits noise


def test_a_planted_strong_text_signal_selects_lambda_above_zero(imp):
    for seed in range(3):
        for r in _fit(imp, seed, STRONG, n_tests=500, selection="loto").selection_summary():
            assert r["lambda"] > 0.0 and r["guard_held"] is False
            assert r["gain"] - r["guard"] * r["gain_se"] > 0


def test_every_admitted_lambda_clears_the_guard_and_the_record_is_complete():
    for r in _null_summaries(2.0):
        assert set(("lambda", "lambda_unguarded", "gain", "gain_se", "guard_held", "guard")) <= set(r)
        if r["lambda"] > 0:
            assert r["gain"] - r["guard"] * r["gain_se"] > 0 and r["guard_held"] is False
        assert r["guard_held"] == (r["lambda"] == 0.0 and r["lambda_unguarded"] > 0.0)


def test_guard_off_reproduces_the_earlier_rule_and_records_no_hold():
    rows = _null_summaries("off")
    assert all(r["guard"] is None and r["guard_held"] is False and r["lambda"] == r["lambda_unguarded"] for r in rows)


def test_lambda_override_bypasses_the_guard(imp):
    p2 = _fit(imp, 2, 0.0, n_tests=120, lambda_override=0.5)
    assert all(r["lambda"] == 0.5 and r["guard_held"] is False for r in p2.selection_summary())


def test_held_cell_predicts_exactly_like_p1(imp, origin):
    syn, feats = imp("mootcourt.sources.synthetic"), imp("mootcourt.features")
    p1m, p2m = imp("mootcourt.predictors.p1"), imp("mootcourt.predictors.p2")
    ledger, _ = syn.generate(syn.SyntheticConfig(seed=11, n_tests=250, variants_per_test=2))
    space, p1 = feats.FeatureSpace.fit(ledger), p1m.P1Predictor().fit(ledger)
    p2 = p2m.P2Predictor().fit(ledger, space, p1, guard=1e9)                  # nothing can clear an enormous multiplier
    x = space.transform(ledger.iloc[[0]])[0]
    a, b = p1.predict(x, 1.5, "headline_only", origin), p2.predict(x, 1.5, "headline_only", origin)
    assert all(r["lambda"] == 0.0 for r in p2.selection_summary())
    assert np.allclose(a.pdf, b.pdf) if hasattr(a, "pdf") else a.p_sig(1.5) == pytest.approx(b.p_sig(1.5))


def test_guard_record_survives_save_and_load(imp):
    p2m, p1m, feats = imp("mootcourt.predictors.p2"), imp("mootcourt.predictors.p1"), imp("mootcourt.features")
    p2 = _fit(imp, 3, 0.0, n_tests=150)
    space = feats.FeatureSpace.fit(imp("mootcourt.sources.synthetic").generate(imp("mootcourt.sources.synthetic").SyntheticConfig(
        seed=3, n_tests=150, variants_per_test=2))[0])
    back = p2m.P2Predictor.from_state(p2.to_state(), space, p1m.P1Predictor())
    assert back.guard == p2.guard
    got = {r["cell"]: (r["guard_held"], r["gain"]) for r in back.selection_summary()}
    assert got == {r["cell"]: (r["guard_held"], r["gain"]) for r in p2.selection_summary()}


def test_cli_parses_the_guard_and_names_the_variant(imp):
    cli = imp("mootcourt.cli")
    assert cli._parse_guard(None) == "default" and cli._parse_guard("off") is None and cli._parse_guard("1.5") == 1.5
    with pytest.raises(typer.BadParameter):
        cli._parse_guard("-1")
    with pytest.raises(typer.BadParameter):
        cli._parse_guard("much")
    v = cli._variant_settings("both", None, None, None, "t", None, None, "absolute", "prelaunch", None)
    assert v == {"p2_guard": "off"} and cli._variant_name(v) == "p2-guard-off"
    assert cli._variant_settings("both", None, None, None, "t", None, None, "absolute", "prelaunch", "default") == {}
    assert cli._variant_settings("both", None, None, None, "t", None, None, "absolute", "prelaunch", imp("mootcourt.config").P2_GUARD_MULT) == {}


def test_default_rungs_pass_the_guard_through(imp, make_synth):
    harness = imp("mootcourt.harness")
    ledger = make_synth(seed=141, n_tests=120, variants_per_test=2)[0]
    off = harness.default_rungs("synthetic", p2_guard=None)["P2"](ledger, imp("mootcourt.harness").quarterly_origins(ledger)[-1])
    assert off.guard is None
    on = harness.default_rungs("synthetic")["P2"](ledger, imp("mootcourt.harness").quarterly_origins(ledger)[-1])
    assert on.guard == imp("mootcourt.config").P2_GUARD_MULT


def test_report_summarises_the_guard_per_cell(imp):
    report = imp("mootcourt.report")
    sel = [{"origin": f"2014-0{i}-01", "rung": "P2", "cell": "a", "selection": "loto", "lambda": lam, "bandwidth_mult": 0.5, "half_life_days": None,
            "guard": 2.0, "lambda_unguarded": 0.3, "gain": 0.01, "gain_se": 0.01, "guard_held": lam == 0.0}
           for i, lam in enumerate([0.0, 0.0, 0.5], 1)]
    row = report.selection_by_cell(sel)[0]
    assert row["share_lambda_zero"] == pytest.approx(2 / 3) and row["share_guard_held"] == pytest.approx(2 / 3)
    assert row["guard"] == 2.0 and row["lambda_unguarded_mean"] == pytest.approx(0.3)
    old = report.selection_by_cell([{k: v for k, v in sel[0].items() if k not in ("guard", "lambda_unguarded", "gain", "gain_se", "guard_held")}])[0]
    assert old["share_guard_held"] is None


def test_docs_explain_the_rule_as_the_admission_rule_made_operational():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    method = " ".join((root / "docs" / "method.md").read_text(encoding="utf-8").split()).lower()
    assert "admission guard" in method and "beats the rung below" in method and "more than noise" in method
    readme = " ".join((root / "README.md").read_text(encoding="utf-8").split()).lower()
    assert "admission guard" in readme and "guarded" in readme and "unguarded" in readme
