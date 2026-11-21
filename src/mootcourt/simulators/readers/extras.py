"""Readings added after the results of the first two runs: the quarters as the units, an interval for the familiarity
probe, the direct judgment and the embedding classifier. Nothing here calls a model, and no report of an earlier run
is rewritten: each function returns a new report.

The plan is ``docs/superpowers/plans/2026-11-21-readers-quarters-and-open-model.md``.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from mootcourt.simulators.readers import align
from mootcourt.simulators.readers.measures import ALPHA, FAMILY, ModelRun, _origin_names, _plain_json, accuracy, paired_difference
from mootcourt.simulators.readers.panel import directions, panel_scores, reader_scores
from mootcourt.simulators.readers.textfeature import text_with_panel

LEVEL = 0.9


def origin_level(contrasts: pd.DataFrame, a, b, family: int | None = None) -> dict:
    """Mean of ``a`` minus ``b`` within each origin, then the origins as the units: their mean and a Student-t interval.

    ``lo`` and ``hi`` are at 90 percent. With a ``family`` the adjusted bounds use the Student-t quantile at the
    Bonferroni level. ``leave_one_out_above_zero`` counts the intervals that stay above zero when one origin is removed.
    """
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    names = _origin_names(contrasts)
    index = contrasts["origin_index"].to_numpy()
    means = np.array([d[index == i].mean() for i in sorted(names)], dtype=float)

    def interval(values: np.ndarray, quantile: float) -> tuple[float, float]:
        if len(values) < 2:
            return float("nan"), float("nan")
        half = float(stats.t.ppf(quantile, len(values) - 1) * values.std(ddof=1) / np.sqrt(len(values)))
        return float(values.mean() - half), float(values.mean() + half)

    lo, hi = interval(means, 0.5 + LEVEL / 2.0)
    out = {"estimate": float(means.mean()), "lo": lo, "hi": hi, "origins": int(len(means)),
           "by_origin": {names[i]: float(m) for i, m in zip(sorted(names), means)},
           "origins_above_zero": int((means > 0).sum()),
           "leave_one_out_above_zero": int(sum(1 for k in range(len(means)) if interval(np.delete(means, k), 0.5 + LEVEL / 2.0)[0] > 0))}
    if family is not None:
        out["adjusted_lo"], out["adjusted_hi"] = interval(means, 1 - ALPHA / family)
        out["family_size"] = int(family)
    return out


def _block_of_row(contrasts: pd.DataFrame, feeds: pd.DataFrame) -> pd.Series:
    return pd.Series(contrasts["unit_id"].map(feeds.drop_duplicates("unit_id").set_index("unit_id")["block_id"]).to_numpy(),
                     index=contrasts["row_id"])


def both(contrasts: pd.DataFrame, feeds: pd.DataFrame, a, b, family: int | None = None) -> dict:
    """One comparison read twice: with blocks resampled and the quarters fixed, and with the quarters as the units."""
    return {"blocks": paired_difference(contrasts, a, b, _block_of_row(contrasts, feeds), family=family, verdict=False),
            "quarters": origin_level(contrasts, a, b, family=family)}


def familiarity_interval(contrasts: pd.DataFrame, feeds: pd.DataFrame, unit_ids: list[str], seen: dict) -> dict:
    """The share of probed contrasts on which the higher familiarity rating points to the winner, minus one half, with a block interval."""
    scored = contrasts[contrasts["unit_id"].isin(unit_ids)]
    rating = pd.Series(seen, dtype=float)
    gap = (scored["arm_id"].map(rating) - scored["ref_arm_id"].map(rating)).to_numpy(dtype=float)
    kept = scored[~np.isnan(gap)].reset_index(drop=True)
    gap = gap[~np.isnan(gap)]
    correct = np.where(gap == 0, 0.5, (np.sign(gap) == np.sign(kept["y"].to_numpy(dtype=float))).astype(float))
    return {"share": float(correct.mean()), "n": int(len(kept)), "ties": int((gap == 0).sum()),
            "minus_half": paired_difference(kept, correct, np.full(len(kept), 0.5), _block_of_row(kept, feeds), family=None, verdict=False)}


def reading_arrays(run: ModelRun) -> dict:
    """The per-contrast scores the three readings compare, computed as the model's report computes them."""
    contrasts = run.contrasts.reset_index(drop=True)
    scores = reader_scores(run.feeds, run.answers["plain"])
    plain = directions(contrasts, panel_scores(scores))
    weighted, _ = align.reader_weights(run.arms, contrasts, scores)
    out = {"plain": plain["correct"].to_numpy(dtype=float), "plain_diff": plain["diff"].to_numpy(dtype=float),
           "reference": contrasts["ref_correct"].to_numpy(dtype=float), "weights": weighted["correct"].to_numpy(dtype=float),
           "text_saved": contrasts["text_lr_correct"].to_numpy(dtype=float)}
    if run.ledger is not None:
        text = text_with_panel(run.ledger, contrasts, pd.Series(out["plain_diff"], index=contrasts["row_id"]))
        out["text_with"], out["text_without"] = text["correct_with"].to_numpy(), text["correct_without"].to_numpy()
    return out


def quarters_report(run: ModelRun, model: str, seen: dict | None = None, probe_units: list[str] | None = None) -> dict:
    """The three readings of one model with the quarters as the units, and the interval of its familiarity probe."""
    contrasts = run.contrasts.reset_index(drop=True)
    arrays = reading_arrays(run)
    readings = {"plain_minus_always_reference": both(contrasts, run.feeds, arrays["plain"], arrays["reference"], FAMILY),
                "weights_minus_plain": both(contrasts, run.feeds, arrays["weights"], arrays["plain"], FAMILY)}
    if "text_with" in arrays:
        readings["text_with_panel_minus_text"] = both(contrasts, run.feeds, arrays["text_with"], arrays["text_without"], FAMILY)
    report = {"model": model, "commit": run.commit, "level": LEVEL, "readings": readings,
              "always_reference_by_origin": origin_level(contrasts, arrays["reference"], np.zeros(len(contrasts)))["by_origin"],
              "note": "added after the results of runs 11 and 12; the origins are the units of the quarters entries"}
    if seen is not None and probe_units is not None:
        report["familiarity"] = familiarity_interval(contrasts, run.feeds, probe_units, seen)
    return _plain_json(report)


def open_model_report(run: ModelRun, model: str, direct: pd.DataFrame | None, embedding: dict | None) -> dict:
    """The comparisons fixed for the open model: the direct judgment and the embedding classifier.

    ``direct`` is the frame of ``direct.direct_frame``. ``embedding`` holds ``without`` (per-contrast scores of the
    classifier alone), ``model`` (the embedding model's name) and ``with_panel``, a table from a panel's name to the
    scores of the classifier with that panel.
    """
    contrasts = run.contrasts.reset_index(drop=True)
    arrays = reading_arrays(run)
    report: dict = {"model": model, "commit": run.commit, "level": LEVEL,
                    "note": "added after the results of runs 11 and 12; no entry carries a verdict word"}
    if direct is not None:
        correct = direct["correct"].to_numpy(dtype=float)
        decisive = contrasts["decisive"].to_numpy(dtype=bool)
        report["direct"] = {**accuracy(contrasts, direct), "decisive_accuracy": accuracy(contrasts, direct, decisive)["accuracy"],
                            "minus_plain": both(contrasts, run.feeds, correct, arrays["plain"]),
                            "minus_always_reference": both(contrasts, run.feeds, correct, arrays["reference"]),
                            "plain_minus_always_reference": both(contrasts, run.feeds, arrays["plain"], arrays["reference"]),
                            "agreement_with_plain": _agreement(direct["diff"].to_numpy(dtype=float), arrays["plain_diff"])}
    if embedding is not None:
        without = np.asarray(embedding["without"], dtype=float)
        report["embedding"] = {"model": embedding["model"], "accuracy": float(without.mean()), "n": int(len(without)),
                               "minus_always_reference": both(contrasts, run.feeds, without, arrays["reference"]),
                               "minus_text": both(contrasts, run.feeds, without, arrays["text_saved"]),
                               "with_panel": {name: {"accuracy": float(np.mean(scores)),
                                                     "minus_without": both(contrasts, run.feeds, scores, without),
                                                     "minus_always_reference": both(contrasts, run.feeds, scores, arrays["reference"])}
                                              for name, scores in embedding["with_panel"].items()}}
    return _plain_json(report)


def _agreement(a: np.ndarray, b: np.ndarray) -> dict:
    kept = ~np.isnan(a) & ~np.isnan(b) & (a != 0) & (b != 0)
    return {"agree_share": float((np.sign(a[kept]) == np.sign(b[kept])).mean()) if kept.any() else None, "n": int(kept.sum())}
