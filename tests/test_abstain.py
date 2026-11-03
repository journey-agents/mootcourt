"""T-009 contracts: the four abstention triggers."""
import datetime as dt
import time

import numpy as np
import pytest

UTC = dt.timezone.utc
NOW = dt.datetime(2014, 7, 15, 12, 0, tzinfo=UTC)


def _state(imp, y, s=1.0, test_ids=None, mu=10.0, tau=1.0, lam=1.0, tau_res2=0.0, kernel=1.0):
    p2 = imp("mootcourt.predictors.p2")
    n = len(y)
    return p2.NeighborState(
        row_ids=tuple(f"r{i}" for i in range(n)), kernel=np.full(n, kernel), y=np.asarray(y, float),
        s=np.full(n, s), test_ids=tuple(test_ids or [f"t{i}" for i in range(n)]),
        mu=mu, tau=tau, lam=lam, tau_res2=tau_res2)


def _stable_state(imp):
    # 40 tests, two rows each, all far above the significance bar: p_sig ~ 1 in every resample
    ids = [f"t{i // 2}" for i in range(80)]
    return _state(imp, [10.0] * 80, test_ids=ids, mu=10.0)


def _unstable_state(imp):
    # four tests whose y alternates far above and far below: resampling flips p_sig across 0.35
    return _state(imp, [10.0, -10.0, 10.0, -10.0], mu=0.0)


def _control(imp, reliability_factory, **over):
    kw = dict(n_support=100, density=0.5, density_threshold=0.1,
              reliability_report=reliability_factory(), cell="headline_only", now=NOW,
              neighbor_state=_stable_state(imp), s_star=1.0)
    kw.update(over)
    return kw


def test_config_defaults(imp):
    cfg = imp("mootcourt.abstain").AbstainConfig()
    assert cfg.support_min == 30 and cfg.novelty_percentile == 5
    assert cfg.reliability_max_age_days == 14 and cfg.drift_consecutive == 2
    assert cfg.bootstrap_resamples == 200 and cfg.action_threshold == 0.35 and cfg.same_side_fraction == 0.80


@pytest.mark.parametrize("n,fires", [(0, True), (29, True), (30, False), (500, False)])
def test_check_support_boundary(imp, n, fires):
    assert imp("mootcourt.abstain").check_support(n) is fires


def test_check_support_rejects_negative(imp):
    with pytest.raises(ValueError):
        imp("mootcourt.abstain").check_support(-1)


@pytest.mark.parametrize("density,fires", [(0.05, True), (0.0999, True), (0.1, False), (0.5, False)])
def test_check_novelty_against_stored_threshold(imp, density, fires):
    assert imp("mootcourt.abstain").check_novelty(density, 0.1) is fires


def test_check_reliability_each_way_to_fire(imp, reliability_factory):
    ab = imp("mootcourt.abstain")
    fresh = reliability_factory()
    assert ab.check_reliability(fresh, "headline_only", NOW) is False
    assert ab.check_reliability(None, "headline_only", NOW) is True                         # missing report
    assert ab.check_reliability(fresh, "other_cell", NOW) is True                           # cell missing
    stale = reliability_factory(as_of=NOW - dt.timedelta(days=15))
    assert ab.check_reliability(stale, "headline_only", NOW) is True                        # older than 14 days
    edge = reliability_factory(as_of=NOW - dt.timedelta(days=14))
    assert ab.check_reliability(edge, "headline_only", NOW) is False                        # exactly 14 days is fine
    assert ab.check_reliability(reliability_factory(drifted=True), "headline_only", NOW) is True
    assert ab.check_reliability(reliability_factory(consecutive_below=2), "headline_only", NOW) is True
    assert ab.check_reliability(reliability_factory(consecutive_below=1), "headline_only", NOW) is False


def test_instability_fires_on_split_precedents_and_not_on_a_stable_set(imp):
    ab = imp("mootcourt.abstain")
    unstable = ab.check_instability(_unstable_state(imp), s_star=1.0, seed=0)
    stable = ab.check_instability(_stable_state(imp), s_star=1.0, seed=0)
    assert unstable.fires is True and unstable.same_side_fraction <= 0.80
    assert stable.fires is False and stable.same_side_fraction > 0.95


def test_instability_is_seeded_and_resamples_by_test(imp):
    ab = imp("mootcourt.abstain")
    st = _unstable_state(imp)
    a = ab.check_instability(st, s_star=1.0, seed=7)
    b = ab.check_instability(st, s_star=1.0, seed=7)
    assert a.same_side_fraction == b.same_side_fraction
    # one test holding every row can never be split by a by-test bootstrap
    one_test = _state(imp, [10.0, -10.0, 10.0, -10.0], test_ids=["only"] * 4, mu=0.0)
    assert ab.check_instability(one_test, s_star=1.0, seed=7).same_side_fraction == pytest.approx(1.0)


def test_each_trigger_fires_alone_and_control_fires_none(imp, reliability_factory):
    ab = imp("mootcourt.abstain")
    control = ab.decide(**_control(imp, reliability_factory))
    assert control.status == "issue" and tuple(control.reasons) == ()
    cases = {
        "support": dict(n_support=5),
        "novelty": dict(density=0.01),
        "reliability": dict(reliability_report=None),
        "instability": dict(neighbor_state=_unstable_state(imp)),
    }
    for trigger, over in cases.items():
        d = ab.decide(**_control(imp, reliability_factory, **over))
        assert d.status == "abstain", trigger
        assert tuple(d.reasons) == (trigger,), f"{trigger} fixture must fire only {trigger}, got {d.reasons}"


def test_all_four_fire_at_once_and_all_reasons_listed(imp, reliability_factory):
    ab = imp("mootcourt.abstain")
    d = ab.decide(**_control(imp, reliability_factory, n_support=1, density=0.0, reliability_report=None,
                             neighbor_state=_unstable_state(imp)))
    assert d.status == "abstain"
    assert set(d.reasons) == {"support", "novelty", "reliability", "instability"}
    assert set(d.details) >= set(d.reasons)


def test_drifted_cell_reason_mentions_drift(imp, reliability_factory):
    d = imp("mootcourt.abstain").decide(**_control(imp, reliability_factory,
                                                  reliability_report=reliability_factory(drifted=True)))
    assert d.reasons == ("reliability",) and "drift" in d.details["reliability"].lower()


def test_bootstrap_check_runs_under_100ms_on_1000_neighbours(imp):
    ab = imp("mootcourt.abstain")
    rng = np.random.default_rng(0)
    n = 1000
    st = imp("mootcourt.predictors.p2").NeighborState(
        row_ids=tuple(f"r{i}" for i in range(n)), kernel=rng.uniform(0.1, 1, n), y=rng.normal(2, 3, n),
        s=rng.uniform(0.5, 2, n), test_ids=tuple(f"t{i // 2}" for i in range(n)),
        mu=2.0, tau=3.0, lam=0.7, tau_res2=0.5)
    ab.check_instability(st, s_star=1.0, seed=0)
    best = min(_t(lambda: ab.check_instability(st, s_star=1.0, seed=0)) for _ in range(5))
    assert best < 0.100


def _t(fn):
    t0 = time.perf_counter()
    fn()
    return time.perf_counter() - t0
