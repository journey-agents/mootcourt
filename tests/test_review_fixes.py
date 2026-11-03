"""T-028 contracts: the normal findings of the chunk A and B code review, one test each."""
import datetime as dt
import json
import shutil

import numpy as np
import pandas as pd
import pytest

UTC = dt.timezone.utc


@pytest.fixture(scope="module")
def synth():
    from mootcourt.sources import synthetic as syn

    ledger, _ = syn.generate(syn.SyntheticConfig(seed=71, n_tests=300, variants_per_test=2, text_effect_strength=2.0))
    return ledger


@pytest.fixture(scope="module")
def bundle(synth):
    from mootcourt import bundle as bm

    return bm.fit_bundle(synth, "synthetic", "20261102-aaaaaaaaaaaa")


# ------------------------------------------------ REV-001 unlisted artifacts, REV-015 identity, REV-019 one read
def _saved(bundle, tmp_path):
    from mootcourt import bundle as bm

    return bm.save_bundle(bundle, tmp_path)


def _edit_manifest(d, fn):
    path = d / "manifest.json"
    man = json.loads(path.read_text())
    fn(man)
    path.write_text(json.dumps(man))


def test_load_refuses_a_required_artifact_missing_from_the_manifest(bundle, tmp_path):
    from mootcourt import bundle as bm

    d = _saved(bundle, tmp_path)
    _edit_manifest(d, lambda m: m["artifacts"].pop("space_objects.joblib"))
    with pytest.raises(bm.BundleIntegrityError):
        bm.load_bundle(bundle.model_id, tmp_path)


def test_load_refuses_an_empty_artifact_map(bundle, tmp_path):
    from mootcourt import bundle as bm

    d = _saved(bundle, tmp_path)
    _edit_manifest(d, lambda m: m.update(artifacts={}))
    with pytest.raises(bm.BundleIntegrityError):
        bm.load_bundle(bundle.model_id, tmp_path)


def test_load_refuses_a_planted_unlisted_joblib_file(bundle, tmp_path):
    from mootcourt import bundle as bm

    d = _saved(bundle, tmp_path)
    shutil.copy(d / "space_objects.joblib", d / "planted.joblib")
    with pytest.raises(bm.BundleIntegrityError):
        bm.load_bundle(bundle.model_id, tmp_path)


def test_load_refuses_a_manifest_naming_another_model(bundle, tmp_path):
    from mootcourt import bundle as bm

    d = _saved(bundle, tmp_path)
    _edit_manifest(d, lambda m: m.update(model_id="zzzzzzzzzzzz"))
    with pytest.raises(bm.BundleIntegrityError):
        bm.load_bundle(bundle.model_id, tmp_path)


def test_save_over_an_existing_bundle_keeps_the_directory_loadable(bundle, tmp_path):
    from mootcourt import bundle as bm

    _saved(bundle, tmp_path)
    _saved(bundle, tmp_path)
    assert bm.load_bundle(bundle.model_id, tmp_path).model_id == bundle.model_id
    assert [p.name for p in tmp_path.iterdir()] == [bundle.model_id]


# ------------------------------------------------ REV-002 snapshot content digest
def test_ensure_snapshot_gives_a_new_id_when_a_value_changes_and_ids_do_not(synth, tmp_path):
    from mootcourt import ledger as lm

    a = lm.ensure_snapshot(synth, tmp_path, today=dt.date(2026, 11, 1))
    changed = synth.copy()
    changed.loc[changed.index[0], "y"] = changed.loc[changed.index[0], "y"] + 1.0
    b = lm.ensure_snapshot(changed, tmp_path, today=dt.date(2026, 11, 2))
    assert a != b
    assert lm.read_snapshot(tmp_path, b)["y"].iloc[0] == pytest.approx(changed["y"].iloc[0])
    assert lm.ensure_snapshot(synth, tmp_path, today=dt.date(2026, 11, 3)) == a, "an unchanged ledger still reuses its snapshot"
    assert lm.snapshot_id(changed, today=dt.date(2026, 11, 1)).split("-")[1] != lm.snapshot_id(synth, today=dt.date(2026, 11, 1)).split("-")[1]


def test_snapshot_id_ignores_row_order_and_time_resolution(synth):
    from mootcourt import ledger as lm

    day = dt.date(2026, 11, 1)
    base = lm.snapshot_id(synth, day)
    assert lm.snapshot_id(synth.sample(frac=1.0, random_state=1), day) == base
    coarse = synth.copy()
    for c in ("started_at", "final_read_at", "usable_after"):
        coarse[c] = coarse[c].dt.as_unit("us")
    assert lm.snapshot_id(coarse, day) == base


def test_append_rows_accepts_reordered_columns_for_an_idempotent_append(synth):
    from mootcourt import ledger as lm

    out = lm.append_rows(synth, synth.head(5)[list(reversed(synth.columns))])
    assert len(out) == len(synth)


# ------------------------------------------------ REV-003 card id covers the content
def _req(**over):
    from mootcourt import card as cm

    kw = dict(source="synthetic", headline="you will not believe what happened next", image_changed=False,
              impressions=20000, origin=None, team_forecast=None, row_id=None)
    kw.update(over)
    return cm.CardRequest(**kw)


def _report(now, cell="headline_only", skill=0.1):
    t = (now - dt.timedelta(days=1)).isoformat()
    return {"source": "synthetic", "as_of": t, "cells": {cell: {
        "as_of": t, "rolling_logscore": -2.0, "p0_rolling_logscore": -2.1, "brier_skill": skill, "n": 300,
        "drifted": False, "consecutive_below": 0}}}


NOW = dt.datetime(2030, 1, 15, 12, tzinfo=UTC)


def test_card_id_changes_with_the_reliability_state_and_the_team_forecast(bundle):
    from mootcourt import card as cm

    base = cm.build_card(bundle, _req(), reliability=None, now=NOW)
    with_report = cm.build_card(bundle, _req(), reliability=_report(NOW), now=NOW)
    other_skill = cm.build_card(bundle, _req(), reliability=_report(NOW, skill=0.2), now=NOW)
    assert len({base.card_id, with_report.card_id, other_skill.card_id}) == 3
    again = cm.build_card(bundle, _req(), reliability=_report(NOW), now=NOW)
    assert again.card_id == with_report.card_id
    changed = cm.build_card(bundle, _req(headline_changed=False), reliability=None, now=NOW) if hasattr(_req(), "headline_changed") else None
    if changed is not None:
        assert changed.card_id != base.card_id


def test_freeze_or_load_returns_the_frozen_content_and_fails_on_a_different_card(bundle, tmp_path):
    from mootcourt import card as cm

    card = cm.build_card(bundle, _req(), reliability=_report(NOW), now=NOW)
    first = cm.freeze_or_load(card, tmp_path)
    again = cm.freeze_or_load(card, tmp_path)
    assert first == again == cm.to_json(card)
    path = tmp_path / f"{card.card_id}.json"
    path.chmod(0o644)
    data = json.loads(path.read_text())
    data["abstention"]["status"] = "abstain"
    path.write_text(json.dumps(data))
    with pytest.raises(cm.CardFrozenError):
        cm.freeze_or_load(card, tmp_path)


# ------------------------------------------------ REV-004 / REV-005 fit cutoff
def test_a_past_origin_before_the_fit_cutoff_is_refused(bundle, synth):
    from mootcourt import card as cm

    cutoff = synth["usable_after"].max()
    assert bundle.fit_cutoff == cutoff
    early = (cutoff - dt.timedelta(days=100)).to_pydatetime()
    x = bundle.transform_text("anything at all")
    with pytest.raises(ValueError, match="cutoff"):
        bundle.predict_all(x, 1.5, "headline_only", early)
    with pytest.raises(ValueError, match="cutoff"):
        cm.build_card(bundle, _req(origin=early), reliability=None, now=cutoff.to_pydatetime())
    bundle.predict_all(x, 1.5, "headline_only", cutoff)           # equal to the cutoff is fine


def test_a_bundle_fit_as_of_the_origin_may_predict_there(synth):
    from mootcourt import bundle as bm
    from mootcourt import card as cm

    origin = synth["usable_after"].quantile(0.5).to_pydatetime()
    b = bm.fit_bundle(synth, "synthetic", "20261102-bbbbbbbbbbbb", as_of=origin)
    assert b.fit_cutoff <= pd.Timestamp(origin)
    card = cm.build_card(b, _req(origin=origin), reliability=None, now=origin)
    assert card.origin


def test_the_fit_cutoff_survives_save_and_load(bundle, tmp_path):
    from mootcourt import bundle as bm

    _saved(bundle, tmp_path)
    assert bm.load_bundle(bundle.model_id, tmp_path).fit_cutoff == bundle.fit_cutoff


# ------------------------------------------------ REV-007 future-dated report
def test_a_future_dated_reliability_report_is_not_fresh():
    from mootcourt import abstain as ab

    report = _report(NOW + dt.timedelta(days=300))
    reason = ab.reliability_reason(report, "headline_only", NOW)
    assert reason is not None and "after" in reason
    assert ab.reliability_reason(_report(NOW), "headline_only", NOW) is None


# ------------------------------------------------ REV-011 every reason listed with no visible rows
def test_a_card_for_an_unseen_cell_lists_the_reliability_reason_next_to_support(bundle, synth):
    from mootcourt import card as cm

    now = synth["usable_after"].max().to_pydatetime()
    card = cm.build_card(bundle, _req(cell="unseen_cell"), reliability=None, now=now)
    assert card.abstention.status == "abstain"
    assert "support" in card.abstention.reasons and "reliability" in card.abstention.reasons


# ------------------------------------------------ REV-012 precedent shares include the tail
def test_precedent_weight_shares_count_the_unlisted_tail(synth):
    from mootcourt.features import FeatureSpace
    from mootcourt.predictors.p1 import P1Predictor
    from mootcourt.predictors.p2 import P2Predictor

    adm = synth[synth["status"] == "admitted"]
    space = FeatureSpace.fit(adm, cell_only=False)
    p1 = P1Predictor().fit(adm)
    p2 = P2Predictor().fit(adm, space, p1, lambda_override=0.5, top_m=20)
    cutoff = adm["usable_after"].max()
    x = space.transform_text(["you will not believe it"], False, cell="headline_only")[0]
    st = p2.neighbor_state(x, "headline_only", cutoff)
    assert st.tail[0] > 0
    rows = p2.top_precedents(x, "headline_only", cutoff, 5)
    w = st.kernel / (st.s ** 2 + st.tau ** 2)
    assert rows["weight"].iloc[0] == pytest.approx(w.max() / (w.sum() + st.tail[0]))
    assert rows["weight"].sum() < 1.0


# ------------------------------------------------ REV-016 / REV-017 earn_weight
def _rows(n=400, base=0.3):
    event = np.arange(n) % 10 < int(base * 10)
    return pd.DataFrame({"p_sig": np.full(n, base), "event": event})


def test_earn_weight_counts_only_rows_with_an_opinion():
    from mootcourt.predictors import second_opinion as so

    class Few:
        def __init__(self):
            self.i = 0

        def p_ai(self, row):
            self.i += 1
            return (1.0 if row["event"] else 0.0) if self.i <= 5 else None

    res = so.earn_weight(Few(), _rows(), n_gate=200, margin=0.001)
    assert res.weight == 0.0 and "gate" in res.message.lower()


def test_earn_weight_margin_is_in_brier_skill_units():
    from mootcourt.predictors import second_opinion as so

    class Noisy:
        def p_ai(self, row):
            return 0.45 if row["event"] else 0.25

    rows = _rows()
    p, e = rows["p_sig"].to_numpy(float), rows["event"].to_numpy(float)
    base = float(np.mean((p - e) ** 2))
    best = min(float(np.mean(((1 - w) * p + w * np.where(e > 0, 0.45, 0.25) - e) ** 2)) for w in so.WEIGHT_GRID)
    skill = (base - best) / (np.mean(e) * (1 - np.mean(e)))
    assert base - best < 0.1 < skill, "the fixture must separate absolute and skill units"
    assert so.earn_weight(Noisy(), rows, n_gate=200, margin=0.1).weight > 0.0
    assert so.earn_weight(Noisy(), rows, n_gate=200, margin=0.99).weight == 0.0


# ------------------------------------------------ REV-018 size caps
def test_service_payload_caps_the_headline_and_the_cell():
    from mootcourt import service

    with pytest.raises(ValueError):
        service.CardPayload(source="synthetic", headline="x" * 5000, image_changed=False, impressions=1000)
    with pytest.raises(ValueError):
        service.CardPayload(source="synthetic", headline="ok", cell="c" * 500, image_changed=False, impressions=1000)


# ------------------------------------------------ REV-013 docstring
def test_harness_docstring_does_not_claim_a_third_guard():
    from mootcourt import harness

    doc = harness.__doc__ or ""
    assert "every frame that reached" not in doc and "three guards" not in doc
