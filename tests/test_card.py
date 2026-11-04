"""T-011 contracts: card data class, robustness, renderers, freeze."""
import dataclasses
import datetime as dt
import functools
import importlib
import json
import os
import re
import stat
import time
from pathlib import Path

import numpy as np
import pytest
from scipy import stats

EM, EN = chr(0x2014), chr(0x2013)
GOLDEN = Path(__file__).parent / "fixtures" / "card_golden.md"
FIXED_NOW_ISO = "2014-07-15T12:00:00+00:00"
SECTION_ORDER = ["evidence", "prediction", "team_forecast", "robustness", "skill", "abstention", "footer"]


@functools.lru_cache(maxsize=1)
def _bl():
    """Fit one small synthetic bundle per session; import errors surface inside the calling test."""
    syn = importlib.import_module("mootcourt.sources.synthetic")
    ledger, _ = syn.generate(syn.SyntheticConfig(seed=81, n_tests=300, variants_per_test=2, text_effect_strength=2.0))
    bundle = importlib.import_module("mootcourt.bundle").fit_bundle(
        ledger, "synthetic", "20261102-cccccccccccc", as_of=dt.datetime(2014, 7, 15, 12, tzinfo=dt.timezone.utc))
    return bundle, ledger


def _request(imp, **over):
    card = imp("mootcourt.card")
    kw = dict(source="synthetic", headline="you will not believe what happened next", image_changed=False,
              impressions=20000, origin=None, team_forecast=None, row_id=None)
    kw.update(over)
    return card.CardRequest(**kw)


def _issue(imp, bundle, ledger, frozen_clock, reliability=None, **over):
    card = imp("mootcourt.card")
    origin = frozen_clock()
    req = _request(imp, origin=origin, **over)
    return card.build_card(bundle, req, reliability=reliability, now=frozen_clock())


def _fresh_report(reliability_factory, frozen_clock, cell="headline_only"):
    return reliability_factory(cell=cell, as_of=frozen_clock() - dt.timedelta(days=1), n=500)


def test_cell_derivation(imp):
    d = imp("mootcourt.card").derive_cell
    assert d("upworthy", image_changed=False, headline_changed=True) == "headline_only"
    assert d("upworthy", image_changed=True, headline_changed=True) == "both"
    assert d("upworthy", image_changed=True, headline_changed=False) == "image_only"
    assert d("upworthy", image_changed=False, headline_changed=False) == "headline_only"


def test_s_star_from_exposure_absolute_difference(imp):
    f = imp("mootcourt.card").s_star_from_exposure
    assert f(10000, 0.02) == pytest.approx(100 * np.sqrt(2 * 0.02 * 0.98 / 10000), rel=1e-9)
    with pytest.raises(ValueError):
        f(0, 0.02)
    with pytest.raises(ValueError):
        f(1000, 0.0)


def test_card_is_frozen_with_sections_in_spec_order(imp, frozen_clock, reliability_factory):
    bundle, ledger = _bl()
    c = _issue(imp, bundle, ledger, frozen_clock, _fresh_report(reliability_factory, frozen_clock))
    assert dataclasses.is_dataclass(c)
    names = [f.name for f in dataclasses.fields(c)]
    for header in ("source", "cell", "origin", "snapshot_id", "model_id", "feature_hash", "issued_at"):
        assert header in names
    positions = [names.index(n) for n in SECTION_ORDER]
    assert positions == sorted(positions)
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.cell = "x"


def test_build_card_requires_version_ids(imp, frozen_clock):
    bundle, ledger = _bl()
    card = imp("mootcourt.card")
    broken = dataclasses.replace(bundle, snapshot_id="") if dataclasses.is_dataclass(bundle) else None
    assert broken is not None, "ModelBundle must be a dataclass so a missing id can be simulated"
    with pytest.raises(ValueError):
        card.build_card(broken, _request(imp, origin=frozen_clock()), now=frozen_clock())


def test_json_schema_pins_keys(imp, frozen_clock, reliability_factory):
    bundle, ledger = _bl()
    card = imp("mootcourt.card")
    c = _issue(imp, bundle, ledger, frozen_clock, _fresh_report(reliability_factory, frozen_clock))
    j = card.to_json(c)
    assert set(j) >= {"card_id", "source", "cell", "origin", "snapshot_id", "model_id", "feature_hash",
                      "issued_at", "evidence", "prediction", "team_forecast", "robustness", "skill",
                      "abstention", "footer"}
    assert j["snapshot_id"] == bundle.snapshot_id and j["model_id"] == bundle.model_id
    assert j["feature_hash"] == bundle.feature_hash and j["issued_at"]
    assert set(j["evidence"]) >= {"n_cell", "n_eff", "base_rate_sig_pos"}
    assert set(j["robustness"]) >= {"k", "dismissals_needed", "bootstrap_same_side"}
    json.dumps(j)
    if j["abstention"]["status"] == "issue":
        assert set(j["prediction"]) >= {"p_sig", "point", "interval_80", "interval_90", "p_win"}


def test_markdown_and_json_agree_and_footer_is_the_boundary(imp, frozen_clock, reliability_factory,
                                                           spec_boundary_sentence):
    bundle, ledger = _bl()
    card = imp("mootcourt.card")
    c = _issue(imp, bundle, ledger, frozen_clock, _fresh_report(reliability_factory, frozen_clock))
    md = card.to_markdown(c)
    assert md.rstrip().endswith(spec_boundary_sentence)
    assert card.to_json(c)["footer"] == spec_boundary_sentence
    for key in ("snapshot_id", "model_id", "feature_hash"):
        assert getattr(c, key) in md
    headings = [m.start() for m in (re.search(h, md, re.I) for h in
                ("evidence", "prediction", "robustness", "skill", "abstention")) if m]
    assert headings == sorted(headings), "sections must appear in spec order"


_ID_LINE = re.compile(r"^(- (?:Card id|Model|Feature hash): )[0-9a-f]{12,16}$", re.MULTILINE)


def _mask_ids(md: str) -> str:
    return _ID_LINE.sub(r"\1<id>", md)


def test_golden_markdown(imp, frozen_clock, reliability_factory):
    bundle, ledger = _bl()
    card = imp("mootcourt.card")
    c = _issue(imp, bundle, ledger, frozen_clock, _fresh_report(reliability_factory, frozen_clock),
               headline="a fixed headline for the golden file")
    md = card.to_markdown(c)
    if os.environ.get("MOOT_UPDATE_GOLDEN") == "1":
        GOLDEN.write_text(md, encoding="utf-8")
    assert GOLDEN.exists(), "golden file missing: review the output, then run once with MOOT_UPDATE_GOLDEN=1"
    # The card id, model id and feature hash are content hashes of fitted floating point parameters. The same fit on
    # another operating system or linear algebra build differs in the last bits, so those three lines are compared
    # against the card itself and masked in the layout comparison; the frozen-id tests cover their stability on one
    # platform.
    for value in (c.card_id, c.model_id, c.feature_hash):
        assert value in md
    assert _mask_ids(md) == _mask_ids(GOLDEN.read_text(encoding="utf-8"))


def _forced_abstain(imp, c, reasons):
    ab = imp("mootcourt.abstain")
    decision = ab.AbstainDecision(status="abstain", reasons=tuple(reasons),
                                  details={r: f"{r} trigger fired" for r in reasons})
    return dataclasses.replace(c, abstention=decision)


@pytest.mark.parametrize("reasons", [["support"], ["novelty"], ["reliability"], ["instability"],
                                     ["support", "novelty", "reliability", "instability"]])
def test_abstained_card_lists_reasons_and_hides_estimates(imp, frozen_clock, reliability_factory,
                                                          reasons):
    bundle, ledger = _bl()
    card = imp("mootcourt.card")
    c = _forced_abstain(imp, _issue(imp, bundle, ledger, frozen_clock, _fresh_report(reliability_factory, frozen_clock)),
                        reasons)
    md = card.to_markdown(c)
    for r in reasons:
        assert r in md.lower()
    assert "p0" in md.lower(), "an abstained card still shows P0"
    # round 00 (T-054): the skill section reports the MEASURED skill with its 90 percent interval, which is not a forecast of this test, so
    # the hidden-estimate check reads the sections above it
    assert not re.search(r"point estimate|interval|80 percent|90 percent", md.split("## Skill at this n")[0], re.I)
    j = card.to_json(c)
    assert j["abstention"]["status"] == "abstain" and list(j["abstention"]["reasons"]) == list(reasons)
    assert not ({"point", "interval_80", "interval_90", "p_win", "p_sig"} & set(j["prediction"] or {}))


def test_real_abstention_without_reliability_report(imp, frozen_clock):
    bundle, ledger = _bl()
    c = _issue(imp, bundle, ledger, frozen_clock, reliability=None)
    assert c.abstention.status == "abstain" and "reliability" in c.abstention.reasons


def test_every_status_is_free_of_dashes_and_role_noun(imp, frozen_clock, reliability_factory):
    bundle, ledger = _bl()
    card = imp("mootcourt.card")
    issued = _issue(imp, bundle, ledger, frozen_clock, _fresh_report(reliability_factory, frozen_clock))
    variants = [issued] + [_forced_abstain(imp, issued, [r]) for r in ("support", "novelty", "reliability", "instability")]
    for c in variants:
        text = card.to_markdown(c) + json.dumps(card.to_json(c), ensure_ascii=False)
        assert EM not in text and EN not in text
        assert not re.search(r"\bown" + r"er\b", text, re.I)


def test_robustness_greedy_dismissals_match_independent_computation(imp):
    card = imp("mootcourt.card")
    p2 = imp("mootcourt.predictors.p2")
    n = 6
    y = np.array([6.0, 5.0, 4.0, 0.0, 0.0, 0.0])
    st = p2.NeighborState(row_ids=tuple(f"r{i}" for i in range(n)), kernel=np.array([1.0, 0.9, 0.8, 0.3, 0.2, 0.1]),
                          y=y, s=np.full(n, 1.0), test_ids=tuple(f"t{i}" for i in range(n)),
                          mu=0.0, tau=1.0, lam=1.0, tau_res2=0.0)
    s_star, a = 1.0, 0.35

    def p_sig(keep):
        k, yy = st.kernel[keep], y[keep]
        w = k / (1.0 + 1.0)
        m = (w * yy).sum() / w.sum()
        vm = (w ** 2 * 2.0).sum() / w.sum() ** 2
        return stats.norm.sf(1.96 * s_star, m, np.sqrt(vm + s_star ** 2))

    keep, needed = list(range(n)), 0
    start_above = p_sig(keep) >= a
    while needed < n and (p_sig(keep) >= a) == start_above:
        keep.pop(0)
        needed += 1
        if not keep:
            break
    got = card.robustness_dismissals(st, s_star=s_star, threshold=a, k=6)
    assert got == needed


def test_robustness_reports_more_than_k_when_nothing_crosses(imp):
    card, p2 = imp("mootcourt.card"), imp("mootcourt.predictors.p2")
    n = 3
    st = p2.NeighborState(row_ids=tuple(f"r{i}" for i in range(n)), kernel=np.ones(n), y=np.full(n, 10.0),
                          s=np.ones(n), test_ids=tuple(f"t{i}" for i in range(n)), mu=10.0, tau=1.0, lam=1.0, tau_res2=0.0)
    assert card.robustness_dismissals(st, s_star=1.0, threshold=0.35, k=3) is None


def test_freeze_card_atomic_read_only_no_overwrite(imp, frozen_clock, reliability_factory, tmp_path):
    bundle, ledger = _bl()
    card = imp("mootcourt.card")
    c = _issue(imp, bundle, ledger, frozen_clock, _fresh_report(reliability_factory, frozen_clock))
    path = card.freeze_card(c, tmp_path)
    assert path == tmp_path / f"{c.card_id}.json"
    assert not (path.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    assert json.loads(path.read_text())["card_id"] == c.card_id
    assert not list(tmp_path.glob("*.tmp")) and not list(tmp_path.glob(".*"))
    before = path.read_bytes()
    with pytest.raises(card.CardFrozenError):
        card.freeze_card(c, tmp_path)
    assert path.read_bytes() == before


def test_team_forecast_is_stored_frozen_at_issue(imp, frozen_clock, reliability_factory):
    bundle, ledger = _bl()
    p3 = imp("mootcourt.predictors.p3")
    tf = p3.TeamForecast.create(0.55, 1.2, clock=frozen_clock)
    c = _issue(imp, bundle, ledger, frozen_clock, _fresh_report(reliability_factory, frozen_clock), team_forecast=tf)
    j = imp("mootcourt.card").to_json(c)
    assert j["team_forecast"]["p_win_team"] == 0.55 and j["team_forecast"]["point_team"] == 1.2
    assert j["team_forecast"]["frozen_at"] == tf.frozen_at.isoformat()
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.team_forecast.p_win_team = 0.9


@pytest.mark.slow
def test_issue_latency_p95_under_one_second_on_20000_rows(imp, make_synth, frozen_clock, reliability_factory):
    ledger, _ = make_synth(seed=82, n_tests=10000, variants_per_test=2)
    frozen_clock.now = ledger["usable_after"].max() + dt.timedelta(days=1)
    bundle = imp("mootcourt.bundle").fit_bundle(ledger, "synthetic", "20261102-dddddddddddd")
    card = imp("mootcourt.card")
    report = _fresh_report(reliability_factory, frozen_clock)
    origin = frozen_clock()
    times = []
    for i in range(30):
        req = _request(imp, headline=f"headline {i} about cats and money", origin=origin)
        t = time.perf_counter()
        card.build_card(bundle, req, reliability=report, now=frozen_clock())
        times.append(time.perf_counter() - t)
    assert np.percentile(times, 95) < 1.0


# T6-plan row 4 (R2 minor 10, call 251): the window of one test says why it has no interval
def _skill_text(imp, **kw):
    card = imp("mootcourt.card")
    base = dict(available=True, brier_skill=0.12, n=40, as_of="2025-12-30T00:00:00+00:00", window_weeks=8)
    return "\n".join(card._skill_lines(card.Skill(**{**base, **kw})))


def test_a_window_of_one_test_says_fewer_than_two_tests_and_not_that_no_interval_is_recorded(imp):
    text = _skill_text(imp, n_tests=1)
    assert "fewer than two tests in the window" in text and "no interval is recorded" not in text


def test_a_report_without_test_ids_still_says_no_interval_is_recorded(imp):
    assert "no interval is recorded" in _skill_text(imp, n_tests=None)


def test_a_window_with_an_interval_prints_it(imp):
    text = _skill_text(imp, n_tests=9, brier_skill_lo=0.01, brier_skill_hi=0.2)
    assert "90 percent interval" in text and "fewer than two" not in text
