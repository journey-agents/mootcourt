"""The readings added after the first two runs: the local transport, the direct judgment, the quarters as the units,
the familiarity interval and the embedding classifier. No test here reaches the network or a model."""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from readers_world import make_world
from scipy import stats

from mootcourt import harness
from mootcourt.simulators.readers import direct, embedfeature, extras, local, pipeline
from mootcourt.simulators.readers.command import TransportError
from mootcourt.simulators.readers.feeds import build_feeds
from mootcourt.simulators.readers.prompts import clicks_schema, parse_clicks
from mootcourt.simulators.readers.transcripts import Transcripts, ask, request_hash
from mootcourt.sources import synthetic

MODEL = "open-model-1"
GOOD = '{"clicks": [0.1, 0.2]}'


def answer(content=GOOD, model=MODEL, **message):
    return {"model": model, "choices": [{"message": {"role": "assistant", "content": content, **message}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 30}}


# ------------------------------------------------------------------------------------------------------------ transport
def test_a_request_holds_the_model_two_messages_and_a_token_limit_and_no_sampling_setting(monkeypatch):
    monkeypatch.delenv(local.EFFORT_ENV, raising=False)
    body = local.request_body(MODEL, "system text", "the prompt")
    assert body == {"model": MODEL, "max_tokens": local.MAX_TOKENS,
                    "messages": [{"role": "system", "content": "system text"}, {"role": "user", "content": "the prompt"}]}


def test_the_effort_setting_is_sent_and_named_only_when_the_environment_holds_it(monkeypatch):
    monkeypatch.setenv(local.EFFORT_ENV, "medium")
    assert local.request_body(MODEL, "s", "p")["reasoning_effort"] == "medium"
    assert "reasoning_effort=medium" in local.version()
    monkeypatch.delenv(local.EFFORT_ENV)
    assert "no setting sent" in local.version()


def test_the_reply_is_the_content_without_a_thinking_block_with_the_tokens_the_server_counts():
    sent = []
    reply = local.call(MODEL, "s", "p", post=lambda path, body, cap: sent.append((path, body)) or answer("<think>{\"x\": 1}</think>\n\n" + GOOD))
    assert reply.text == GOOD and reply.reported_model == MODEL
    assert reply.usage == {"input_tokens": 12, "output_tokens": 30}
    assert sent[0][0] == "/chat/completions"


def test_a_tool_call_or_a_response_without_a_message_is_a_transport_failure():
    with pytest.raises(TransportError):
        local.call(MODEL, "s", "p", post=lambda *a: answer(tool_calls=[{"id": "1"}]))
    with pytest.raises(TransportError):
        local.call(MODEL, "s", "p", post=lambda *a: {"error": "busy"})


def test_no_address_in_the_environment_is_a_transport_failure(monkeypatch):
    monkeypatch.delenv(local.ENDPOINT_ENV, raising=False)
    with pytest.raises(TransportError, match=local.ENDPOINT_ENV):
        local.call(MODEL, "s", "p")


def test_ask_through_the_local_endpoint_stores_the_reply_under_the_same_request_hash(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(local, "_post", lambda path, body, cap: calls.append(body) or answer())
    record = ask(Transcripts(tmp_path), MODEL, "plain", "s", "p", clicks_schema(2), lambda text: parse_clicks(text, 2),
                 allow_model_calls=True, transport="local")
    assert record["status"] == "ok" and record["usage"]["output_tokens"] == 30
    assert record["request_hash"] == request_hash(MODEL, "plain", "s", "p", clicks_schema(2))
    ask(Transcripts(tmp_path), MODEL, "plain", "s", "p", clicks_schema(2), lambda text: parse_clicks(text, 2), transport="local")
    assert len(calls) == 1          # a stored reply is never asked for again


def test_embeddings_come_back_in_the_order_asked_and_in_batches():
    def post(path, body, cap):
        assert path == "/embeddings"
        return {"data": [{"index": i, "embedding": [float(len(t)), 1.0]} for i, t in reversed(list(enumerate(body["input"])))]}
    texts = [f"t{'x' * i}" for i in range(local.EMBED_BATCH + 3)]
    vectors = local.embed("embedder", texts, post=post)
    assert [v[0] for v in vectors] == [float(len(t)) for t in texts]


# -------------------------------------------------------------------------------------------------------- direct judgment
@pytest.fixture(scope="module")
def world():
    w = make_world(seed=5, units=(40, 40, 40))
    feeds = build_feeds(w.arms)
    return SimpleNamespace(arms=w.arms, contrasts=w.contrasts.reset_index(drop=True), feeds=feeds)


def test_every_contrast_is_asked_once_and_no_call_crosses_a_block(world):
    calls = direct.direct_calls(world, pipeline.Call)
    asked = [row for call in calls for row in call.meta["row_ids"]]
    assert sorted(asked) == sorted(world.contrasts["row_id"]) and len(set(asked)) == len(asked)
    assert all(len(call.meta["row_ids"]) <= direct.DIRECT_BATCH for call in calls)
    block_of_unit = world.feeds.drop_duplicates("unit_id").set_index("unit_id")["block_id"]
    block_of_row = world.contrasts.set_index("row_id")["unit_id"].map(block_of_unit)
    assert all(set(block_of_row[call.meta["row_ids"]]) == {call.meta["block_id"]} for call in calls)
    assert all(call.kind == "direct" for call in calls)


def test_the_prompt_names_no_reader_no_publisher_and_no_date(world):
    prompt = direct.direct_calls(world, pipeline.Call)[0].prompt
    assert "A:" in prompt and "B:" in prompt
    for word in ("Upworthy", "2013", "2015", "person", "profile"):
        assert word not in prompt


def test_the_items_are_the_same_on_every_build_and_both_orders_occur(world):
    one, two = (direct.direct_items(world.contrasts, world.arms, world.feeds) for _ in range(2))
    pd.testing.assert_frame_equal(one, two)
    assert 0.3 < one["variant_first"].mean() < 0.7


def test_a_judge_that_always_picks_the_winner_is_right_everywhere_and_an_unanswered_contrast_counts_one_half(world):
    items = direct.direct_items(world.contrasts, world.arms, world.feeds)
    won = world.contrasts.set_index("row_id")["y"] > 0
    winners = {r.row_id: "A" if bool(won[r.row_id]) == bool(r.variant_first) else "B" for r in items.itertuples()}
    frame = direct.direct_frame(world.contrasts, items, winners)
    assert frame["correct"].eq(1.0).all()
    first = world.contrasts["row_id"].iloc[0]
    frame = direct.direct_frame(world.contrasts, items, {k: v for k, v in winners.items() if k != first})
    assert frame["correct"].iloc[0] == 0.5 and bool(frame["no_reader"].iloc[0])


# ------------------------------------------------------------------------------------------------- quarters as the units
def test_the_quarter_reading_is_a_student_t_interval_on_the_means_of_the_origins(world):
    r = np.random.default_rng(3)
    a, b = r.random(len(world.contrasts)), r.random(len(world.contrasts))
    out = extras.origin_level(world.contrasts, a, b, family=3)
    index = world.contrasts["origin_index"].to_numpy()
    means = np.array([(a - b)[index == i].mean() for i in sorted(set(index))])
    half = stats.t.ppf(0.95, len(means) - 1) * means.std(ddof=1) / np.sqrt(len(means))
    assert out["estimate"] == pytest.approx(means.mean()) and out["origins"] == len(means)
    assert (out["lo"], out["hi"]) == pytest.approx((means.mean() - half, means.mean() + half))
    wide = stats.t.ppf(1 - 0.05 / 3, len(means) - 1) * means.std(ddof=1) / np.sqrt(len(means))
    assert (out["adjusted_lo"], out["adjusted_hi"]) == pytest.approx((means.mean() - wide, means.mean() + wide))
    assert out["adjusted_lo"] < out["lo"] and list(out["by_origin"].values()) == pytest.approx(list(means))


def test_a_gain_in_every_origin_is_above_zero_and_a_gain_in_one_origin_is_not(world):
    index = world.contrasts["origin_index"].to_numpy()
    zeros = np.zeros(len(index))
    everywhere = extras.origin_level(world.contrasts, 0.05 + 0.001 * index, zeros)
    assert everywhere["lo"] > 0 and everywhere["origins_above_zero"] == everywhere["origins"]
    once = extras.origin_level(world.contrasts, np.where(index == 0, 0.3, 0.0), zeros)
    assert once["lo"] < 0 < once["hi"] and once["origins_above_zero"] == 1 and once["leave_one_out_above_zero"] == 0


def test_the_familiarity_share_counts_a_tie_as_one_half_and_has_a_block_interval(world):
    units = sorted(world.contrasts["unit_id"].unique())[:60]
    scored = world.contrasts[world.contrasts["unit_id"].isin(units)]
    seen = {}
    for row in scored.itertuples():          # the variant is rated higher exactly when it won, so every direction is right
        seen[row.ref_arm_id] = 50.0
        seen[row.arm_id] = 80.0 if row.y > 0 else 20.0
    out = extras.familiarity_interval(world.contrasts, world.feeds, units, seen)
    assert out["share"] == 1.0 and out["n"] == len(scored) and out["minus_half"]["estimate"] == pytest.approx(0.5)
    flat = extras.familiarity_interval(world.contrasts, world.feeds, units, {arm: 50.0 for arm in seen})
    assert flat["share"] == 0.5 and flat["ties"] == len(scored)
    assert flat["minus_half"]["lo"] == pytest.approx(0.0) and "verdict" not in flat["minus_half"]


# ------------------------------------------------------------------------------------------------- embedding classifier
@pytest.fixture(scope="module")
def synth():
    ledger = synthetic.generate(synthetic.SyntheticConfig(seed=62, n_tests=400, variants_per_test=1, text_effect_strength=2.0,
                                                          cell_params={"headline_only": (0.0, 0.5)}, s_scale=1.0))[0]
    rungs = harness.default_rungs("synthetic", ledger, "text_lr")
    scores = harness.rolling_origin(ledger, rungs, harness.quarterly_origins(ledger), source="synthetic")
    text = scores[scores["rung"] == "text_lr"].reset_index(drop=True)
    origins = sorted(text["origin"].unique())
    contrasts = text[["row_id", "origin", "y"]].assign(origin_index=text["origin"].map({o: i for i, o in enumerate(origins)}))
    return SimpleNamespace(ledger=ledger, contrasts=contrasts)


def _table(texts, informative_for=None):
    r = np.random.default_rng(9)
    return embedfeature.unit_vectors(texts, r.normal(size=(len(texts), 16)))


def test_every_headline_of_the_source_is_listed_once(synth):
    texts = embedfeature.headlines_of(synth.ledger, synth.contrasts)
    assert texts == sorted(set(texts)) and all(t.strip() for t in texts) and len(texts) > 100


def test_vectors_are_scaled_to_unit_length():
    table = embedfeature.unit_vectors(["a", "b"], [[3.0, 4.0], [0.0, 0.0]])
    assert np.linalg.norm(table["a"]) == pytest.approx(1.0) and not table["b"].any()


def test_a_headline_without_an_embedding_stops_the_fit(synth):
    texts = embedfeature.headlines_of(synth.ledger, synth.contrasts)
    with pytest.raises(ValueError, match="no embedding"):
        embedfeature.embedding_directions(synth.ledger, synth.contrasts, _table(texts[:-50]))


def test_a_panel_that_knows_the_outcome_lifts_the_classifier_and_a_flat_panel_changes_nothing(synth):
    table = _table(embedfeature.headlines_of(synth.ledger, synth.contrasts))
    alone = embedfeature.embedding_directions(synth.ledger, synth.contrasts, table)
    assert alone["p"].between(0, 1).all() and len(alone) == len(synth.contrasts)
    flat = embedfeature.embedding_directions(synth.ledger, synth.contrasts, table, pd.Series(0.0, index=synth.contrasts["row_id"]))
    assert np.allclose(flat["p"], alone["p"], atol=1e-6)
    knows = pd.Series(10.0 * np.sign(synth.contrasts["y"].to_numpy()), index=synth.contrasts["row_id"])
    lifted = embedfeature.embedding_directions(synth.ledger, synth.contrasts, table, knows)
    later = (synth.contrasts["origin_index"] > 0).to_numpy()          # the panel column is learned from earlier origins
    assert lifted["correct"][later].mean() > alone["correct"][later].mean() + 0.2
