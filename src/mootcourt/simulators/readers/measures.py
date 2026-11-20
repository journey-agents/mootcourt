"""The measures of the simulated readers and the report of one model.

A comparison is a paired difference of two per-contrast scores over the same contrasts. Its interval resamples whole
blocks, because the cards of a block were read in the same calls and their errors move together. The three readings
fixed before the run form one family, and their adjusted bounds use the Bonferroni normal quantile for three. Only
the primary model's readings carry a verdict word.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.special import ndtri

from mootcourt.decision_value import _matched_value, _top_k_value, budget_k
from mootcourt.simulators.readers import align
from mootcourt.simulators.readers.panel import direction_frame, directions, panel_scores, reader_scores, split_half_agreement
from mootcourt.simulators.readers.protocol import PRIMARY_MODEL, SEED, rng
from mootcourt.simulators.readers.textfeature import text_with_panel

FAMILY = 3                      # the three readings fixed before the run
ALPHA = 0.05
B_DEFAULT = 500
METHODS = ("direction_map", "reader_weights", "audience_matching", "error_correction", "text_with_panel", "examples_in_prompt",
           "audience_brief")


def _resampled_means(d: np.ndarray, groups: np.ndarray, key: int, B: int) -> np.ndarray:
    """Means of ``d`` over ``B`` resamples of whole groups, drawn with the bootstrap stream and ``key``."""
    codes, _ = pd.factorize(groups, sort=True)          # sorted, so the draws do not depend on the order of the rows
    sums, counts = np.bincount(codes, weights=d), np.bincount(codes)
    draw = rng("bootstrap", key).integers(0, len(sums), size=(B, len(sums)))
    return sums[draw].sum(axis=1) / counts[draw].sum(axis=1)


def paired_difference(contrasts: pd.DataFrame, a: np.ndarray, b: np.ndarray, block_of_row: pd.Series, *, family: int | None,
                      B: int = B_DEFAULT, verdict: bool = True) -> dict:
    """Mean of ``a`` minus mean of ``b`` over the same contrasts, with intervals from resampling whole blocks.

    ``block_of_row`` is indexed by ``row_id``. ``lo`` and ``hi`` are the 5th and 95th percentiles over resampled blocks;
    ``test_lo`` and ``test_hi`` are the same over resampled tests, for comparison. With a ``family`` the adjusted bounds are
    the estimate minus and plus the block standard error times the Bonferroni normal quantile, and the verdict reads them.
    """
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    estimate = float(d.mean())
    blocks = contrasts["row_id"].map(block_of_row)
    if blocks.isna().any():
        raise ValueError("a contrast has no block")
    by_block = _resampled_means(d, blocks.to_numpy(), 0, B)
    by_test = _resampled_means(d, contrasts["test_id"].to_numpy(), 1, B)
    se = float(by_block.std(ddof=1))
    out = {"estimate": estimate, "n": int(len(d)), "lo": float(np.percentile(by_block, 5)), "hi": float(np.percentile(by_block, 95)),
           "se": se, "test_lo": float(np.percentile(by_test, 5)), "test_hi": float(np.percentile(by_test, 95)), "resamples": int(B)}
    if family is not None:
        z = float(ndtri(1 - ALPHA / family))
        out.update(adjusted_lo=estimate - z * se, adjusted_hi=estimate + z * se, family_size=int(family))
        if verdict:
            out["verdict"] = "above" if out["adjusted_lo"] > 0 else "below" if out["adjusted_hi"] < 0 else "contains_zero"
    return out


def accuracy(contrasts: pd.DataFrame, correct, mask=None) -> dict:
    """Share of directions matched, with the counts of ties and of contrasts that no reader scored.

    ``correct`` is a frame from ``directions`` (its ``tie`` and ``no_reader`` columns are counted) or an array of per-contrast
    scores, in the order of ``contrasts``.
    """
    frame = correct if isinstance(correct, pd.DataFrame) else None
    values = (frame["correct"] if frame is not None else pd.Series(correct)).to_numpy(dtype=float)
    keep = np.ones(len(values), dtype=bool) if mask is None else np.asarray(mask, dtype=bool)
    n = int(keep.sum())
    return {"accuracy": float(values[keep].mean()) if n else None, "n": n,
            "ties": int(frame["tie"].to_numpy()[keep].sum()) if frame is not None else 0,
            "no_reader": int(frame["no_reader"].to_numpy()[keep].sum()) if frame is not None else 0}


def _captured(tables: list[dict], draws: list[np.ndarray] | None, frac: float) -> tuple[float, float, float]:
    """Captured share of value, pooled over origins, for the panel, the arm-count rule and the matched random order."""
    total, got = 0.0, np.zeros(3)
    for i, t in enumerate(tables):
        pick = slice(None) if draws is None else draws[i]
        score, value, arms = t["score"][pick], t["value"][pick], t["arms"][pick]
        k = budget_k(len(value), frac)
        total += float(value.sum())
        got += (_top_k_value(score, value, k), _top_k_value(arms, value, k), _matched_value(score, value, arms, k))
    if total <= 0:
        return (float("nan"),) * 3
    return tuple(float(v) for v in got / total)


def ranking(contrasts: pd.DataFrame, diff: pd.Series, frac: float = 0.25, B: int = B_DEFAULT) -> dict:
    """Which tests to run first: the value captured by the top quarter of units within each origin.

    ``diff`` is indexed by ``row_id``. A unit's score is the largest panel difference among its contrasts (a missing one
    ranks last), its value the largest positive effect among them, and its arm count the number of its scored contrasts.
    Intervals resample units within each origin.
    """
    frame = pd.DataFrame({"unit_id": contrasts["unit_id"].to_numpy(), "origin_index": contrasts["origin_index"].to_numpy(),
                          "y": contrasts["y"].to_numpy(dtype=float),
                          "diff": contrasts["row_id"].map(diff).fillna(-np.inf).to_numpy(dtype=float)})
    units = frame.groupby("unit_id").agg(origin_index=("origin_index", "first"), score=("diff", "max"), best=("y", "max"),
                                         arms=("y", "size"))
    tables = [{"score": g["score"].to_numpy(dtype=float), "value": np.maximum(g["best"].to_numpy(dtype=float), 0.0),
               "arms": g["arms"].to_numpy(dtype=float)} for _, g in units.groupby("origin_index", sort=True)]
    panel, arm_count, matched = _captured(tables, None, frac)
    draw = rng("bootstrap", 2)
    samples = np.array([_captured(tables, [draw.integers(0, len(t["value"]), size=len(t["value"])) for t in tables], frac)
                        for _ in range(B)])

    def difference(column: int, estimate: float) -> dict:
        d = samples[:, 0] - samples[:, column]
        return {"estimate": estimate, "lo": float(np.nanpercentile(d, 5)), "hi": float(np.nanpercentile(d, 95)),
                "se": float(np.nanstd(d, ddof=1))}

    return {"frac": frac, "n_units": int(len(units)), "resamples": int(B), "panel": {"estimate": panel},
            "arm_count": {"estimate": arm_count}, "matched_random": {"estimate": matched},
            "panel_minus_arm_count": difference(1, panel - arm_count), "panel_minus_matched_random": difference(2, panel - matched)}


@dataclass
class ModelRun:
    """Everything the report of one model is computed from. No part of it is a model call."""

    arms: pd.DataFrame
    contrasts: pd.DataFrame
    feeds: pd.DataFrame
    answers: dict[str, pd.DataFrame]                      # "plain", and "examples" and "brief" for the origins after the first
    notes: dict[int, str] = field(default_factory=dict)   # the audience note of each origin index
    notes_missing: list[int] = field(default_factory=list)   # origin indexes whose note was not a usable reply
    counts: dict = field(default_factory=dict)            # calls_planned, calls_ok, calls_invalid, calls_refusal
    tool_versions: dict = field(default_factory=dict)
    reported_models: dict = field(default_factory=dict)
    commit: str = ""
    ledger: pd.DataFrame | None = None                    # needed by method 5 only
    probes: dict = field(default_factory=dict)


def _origin_names(contrasts: pd.DataFrame) -> dict[int, str]:
    first = contrasts.groupby("origin_index")["origin"].first()
    return {int(i): pd.Timestamp(o).strftime("%Y-%m-%d") for i, o in first.items()}


def _with_plain_at_first_origin(contrasts: pd.DataFrame, own: pd.DataFrame, plain: pd.DataFrame) -> pd.DataFrame:
    """A method that has no call at the first origin equals the plain panel there."""
    first = (contrasts["origin_index"] == 0).to_numpy()
    return direction_frame(contrasts, np.where(first, plain["diff"].to_numpy(), own["diff"].to_numpy()))


def model_report(run: ModelRun, model: str) -> dict:
    """The report of one model: baselines, the plain panel, the three readings, the seven methods, ranking and probes."""
    contrasts = run.contrasts.reset_index(drop=True)
    arms = run.arms
    primary = model == PRIMARY_MODEL
    names = _origin_names(contrasts)
    block_of_row = pd.Series(contrasts["unit_id"].map(run.feeds.drop_duplicates("unit_id").set_index("unit_id")["block_id"]).to_numpy(),
                             index=contrasts["row_id"])
    decisive = contrasts["decisive"].to_numpy(dtype=bool)
    reference = contrasts["ref_correct"].to_numpy(dtype=float)
    text_saved = contrasts["text_lr_correct"].to_numpy(dtype=float)

    def compare(a, b, family=None):
        return paired_difference(contrasts, a, b, block_of_row, family=family, verdict=primary)

    scores = reader_scores(run.feeds, run.answers["plain"])
    plain = directions(contrasts, panel_scores(scores))
    plain_correct = plain["correct"].to_numpy()

    def method_entry(frame: pd.DataFrame) -> dict:
        correct = frame["correct"].to_numpy(dtype=float)
        return {**accuracy(contrasts, frame), "decisive_accuracy": accuracy(contrasts, frame, decisive)["accuracy"],
                "minus_plain": compare(correct, plain_correct), "minus_always_reference": compare(correct, reference)}

    mapped = align.direction_map(arms, contrasts, scores)
    weighted, weight_fits = align.reader_weights(arms, contrasts, scores)
    matched, match_fits = align.audience_matching(arms, contrasts, scores)
    corrected, correction_fits = align.error_correction(arms, contrasts, scores)
    methods: dict = {
        "direction_map": {**method_entry(mapped), "brier_skill": align.brier_skill(contrasts, mapped)},
        "reader_weights": {**method_entry(weighted), "fits": {names[i]: fit for i, fit in weight_fits.items()}},
        "audience_matching": {**method_entry(matched), "fits": {names[i]: fit for i, fit in match_fits.items()}},
        "error_correction": {**method_entry(corrected), "fits": {names[i]: fit for i, fit in correction_fits.items()}},
        "text_with_panel": None,
    }
    text_reading = None
    if run.ledger is not None:
        text = text_with_panel(run.ledger, contrasts, pd.Series(plain["diff"].to_numpy(), index=contrasts["row_id"]))
        with_panel, without = text["correct_with"].to_numpy(), text["correct_without"].to_numpy()
        text_reading = compare(with_panel, without, family=FAMILY)
        methods["text_with_panel"] = {
            "accuracy": float(with_panel.mean()), "n": int(len(with_panel)), "decisive_accuracy": float(with_panel[decisive].mean()),
            "without_accuracy": float(without.mean()), "without_equals_saved_share": float((without == text_saved).mean()),
            "minus_plain": compare(with_panel, plain_correct), "minus_always_reference": compare(with_panel, reference),
        }
    for name, kind in (("examples_in_prompt", "examples"), ("audience_brief", "brief")):
        own = directions(contrasts, panel_scores(reader_scores(run.feeds, run.answers[kind])))
        methods[name] = method_entry(_with_plain_at_first_origin(contrasts, own, plain))
    methods["audience_brief"]["notes"] = {
        names[i]: {"words": len(note.split()), "sha256": hashlib.sha256(note.encode("utf-8")).hexdigest()}
        for i, note in sorted(run.notes.items())}
    methods["audience_brief"]["notes_missing"] = [names[i] for i in sorted(run.notes_missing)]

    by_origin = {}
    for index, name in names.items():
        at = (contrasts["origin_index"] == index).to_numpy()
        by_origin[name] = {"plain": accuracy(contrasts, plain, at), "always_reference": accuracy(contrasts, reference, at),
                           "reader_weights": accuracy(contrasts, weighted, at)}

    report = {
        "model": model, "primary": primary, "seed": SEED, "commit": run.commit,
        "counts": {"units": int(arms["unit_id"].nunique()), "tests": int(arms["test_id"].nunique()), "contrasts": int(len(contrasts)),
                   "blocks": int(run.feeds["block_id"].nunique()),
                   "feeds": int(run.feeds.groupby("block_id")["feed_index"].nunique().sum()), **run.counts},
        "tool_versions": dict(run.tool_versions), "reported_models": dict(run.reported_models),
        "baselines": {"always_reference": accuracy(contrasts, reference), "text_lr": accuracy(contrasts, text_saved),
                      "ceiling": {"accuracy": float(contrasts["dir_ceiling_row"].mean()), "n": int(len(contrasts))},
                      "text_lr_minus_always_reference": paired_difference(contrasts, text_saved, reference, block_of_row, family=None)},
        "plain": {**accuracy(contrasts, plain),
                  "accuracy_minus_half": paired_difference(contrasts, plain_correct, np.full(len(contrasts), 0.5), block_of_row, family=None),
                  "decisive": accuracy(contrasts, plain, decisive), "split_half": split_half_agreement(contrasts, scores)},
        "readings": {"plain_minus_always_reference": compare(plain_correct, reference, family=FAMILY),
                     "weights_minus_plain": compare(weighted["correct"].to_numpy(), plain_correct, family=FAMILY),
                     "text_with_panel_minus_text": text_reading},
        "methods": methods, "by_origin": by_origin,
        "ranking": ranking(contrasts, pd.Series(plain["diff"].to_numpy(), index=contrasts["row_id"])),
        "probes": dict(run.probes),
    }
    return _plain_json(report)


def _plain_json(value):
    """Python numbers, lists and dicts only, with None where a number is not finite."""
    if isinstance(value, dict):
        return {str(k): _plain_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain_json(v) for v in value]
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    return value


def agreement_report(per_model: dict[str, pd.DataFrame]) -> dict:
    """For each pair of models, the share of contrasts on which the plain panels agree in direction. Ties and gaps are left out."""
    models = list(per_model)
    pairs = {}
    for i, one in enumerate(models):
        for two in models[i + 1:]:
            a = per_model[one].set_index("row_id")["diff"]
            b = per_model[two].set_index("row_id")["diff"].reindex(a.index)
            both = (a.notna() & b.notna() & (a != 0) & (b != 0)).to_numpy()
            agree = np.sign(a.to_numpy()[both]) == np.sign(b.to_numpy()[both])
            pairs[f"{one}__{two}"] = {"agree_share": float(agree.mean()) if both.any() else None, "n": int(both.sum()),
                                      "left_out": int((~both).sum())}
    return {"models": models, "pairs": pairs}


def transport_report(contrasts: pd.DataFrame, feeds: pd.DataFrame, tool_plain: pd.DataFrame, api_plain: pd.DataFrame) -> dict:
    """The plain panels of one model in two runs that differ only in transport: agreement in direction and the paired difference in accuracy.

    Both frames come from ``directions`` on the same contrasts. Agreement leaves out a contrast where either panel is
    tied or has no reader. The difference is the second run minus the first and belongs to no family, so it has no
    adjusted bounds and no verdict.
    """
    contrasts = contrasts.reset_index(drop=True)
    block_of_row = pd.Series(contrasts["unit_id"].map(feeds.drop_duplicates("unit_id").set_index("unit_id")["block_id"]).to_numpy(),
                             index=contrasts["row_id"])
    a, b = tool_plain["diff"].to_numpy(dtype=float), api_plain["diff"].to_numpy(dtype=float)
    both = ~np.isnan(a) & ~np.isnan(b) & (a != 0) & (b != 0)
    agree = np.sign(a[both]) == np.sign(b[both])
    tool_correct, api_correct = tool_plain["correct"].to_numpy(dtype=float), api_plain["correct"].to_numpy(dtype=float)
    return {"plain": {"agree_share": float(agree.mean()) if both.any() else None, "n": int(both.sum()), "left_out": int((~both).sum()),
                      "accuracy_tool": float(tool_correct.mean()), "accuracy_api": float(api_correct.mean()),
                      "accuracy_api_minus_tool": paired_difference(contrasts, api_correct, tool_correct, block_of_row, family=None)}}
