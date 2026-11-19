"""A synthetic world for the tests of the simulated readers: units over three origins with a planted effect per arm.

Reader 7's centred score is the planted effect and the other nine readers are noise, unless the world is built with
``informative=False``. Nothing here is archive data.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

ORIGINS = [pd.Timestamp(d, tz="UTC") for d in ("2014-01-01", "2014-04-01", "2014-07-01")]
STARTS = ("Seven", "Why", "This", "How", "What", "Nine", "The", "One")
WORDS = ("people", "found", "a", "simple", "way", "to", "change", "their", "morning", "and", "nobody", "expected", "it", "at", "all")


@dataclass
class World:
    arms: pd.DataFrame
    contrasts: pd.DataFrame
    rs: pd.DataFrame

    def origin(self, index: int) -> pd.Timestamp:
        return ORIGINS[index]

    def with_unit_usable_only_after(self, origin_index: int) -> "World":
        """A copy with one more unit at the first origin whose signal is decisive and whose result arrives too late."""
        late = ORIGINS[origin_index] + pd.Timedelta(days=10)
        unit = "t_late@2014-01-01"
        common = {"unit_id": unit, "test_id": "t_late", "origin": ORIGINS[0], "origin_index": 0, "usable_after": late}
        arms = pd.DataFrame([
            {**common, "arm_id": f"{unit}#0", "headline": "A late reference headline with eight words here", "is_reference": True,
             "clicks": 100, "impressions": 2_000_000},
            {**common, "arm_id": f"{unit}#1", "headline": "A late variant headline with eight words here", "is_reference": False,
             "clicks": 1_500_000, "impressions": 2_000_000},
        ])
        contrast = pd.DataFrame([{**{k: common[k] for k in ("unit_id", "test_id", "origin", "origin_index", "usable_after")},
                                  "row_id": "zz_late", "arm_id": f"{unit}#1", "ref_arm_id": f"{unit}#0", "y": 0.75, "s": 0.001,
                                  "decisive": True, "ref_correct": 0.0, "text_lr_correct": 1.0, "dir_ceiling_row": 1.0,
                                  "s_star": 0.001}])
        rs = pd.DataFrame([{"arm_id": f"{unit}#{k}", "reader": r, "centred": (400.0 if k else -400.0) * (-1 if r != 7 else 1),
                            "raw": 50.0 + (40.0 if k else -40.0)} for k in (0, 1) for r in range(1, 11)])
        return replace(self, arms=pd.concat([self.arms, arms], ignore_index=True),
                       contrasts=pd.concat([self.contrasts, contrast], ignore_index=True),
                       rs=pd.concat([self.rs, rs], ignore_index=True))

    @property
    def units_with_a_short_headline(self) -> list[str]:
        return sorted(self.arms[self.arms.headline.str.split().str.len() < 8].unit_id.unique())


def _headline(r: np.random.Generator, question: bool, short: bool) -> str:
    n = int(r.integers(3, 6)) if short else int(r.integers(9, 14))
    words = [str(r.choice(STARTS)), *(str(w) for w in r.choice(WORDS, n - 1)), format(int(r.integers(1 << 30)), "x")]
    return " ".join(words) + ("?" if question else "")


def make_world(seed: int = 11, units=(120, 120, 120), question_effect: float = 0.0, informative: bool = True,
               effect_sd: float = 0.25, impressions: int = 3000) -> World:
    r = np.random.default_rng(seed)
    arm_rows, contrast_rows, score_rows = [], [], []
    for origin_index, n_units in enumerate(units):
        origin = ORIGINS[origin_index]
        for u in range(n_units):
            test_id = f"t{origin_index}_{u:03d}"
            unit = f"{test_id}@{origin.strftime('%Y-%m-%d')}"
            common = {"unit_id": unit, "test_id": test_id, "origin": origin, "origin_index": origin_index,
                      "usable_after": origin + pd.Timedelta(days=20)}
            rates = []
            for k in range(int(r.integers(2, 5))):
                question = bool(r.random() < 0.4)
                effect = float(r.normal(0, effect_sd))
                logit = np.log(0.03 / 0.97) + effect + question_effect * question
                clicks = int(r.binomial(impressions, 1 / (1 + np.exp(-logit))))
                rates.append(clicks / impressions)
                short = bool(u % 15 == 0 and k == 1)
                arm_rows.append({**common, "arm_id": f"{unit}#{k}", "headline": _headline(r, question, short), "is_reference": k == 0,
                                 "clicks": clicks, "impressions": impressions})
                for reader in range(1, 11):
                    signal = 20 * effect if (reader == 7 and informative) else float(r.normal(0, 8))
                    score_rows.append({"arm_id": f"{unit}#{k}", "reader": reader, "centred": signal, "raw": 30.0 + reader + signal})
                if k:
                    y = rates[k] - rates[0]
                    s = float(np.sqrt(rates[k] * (1 - rates[k]) / impressions + rates[0] * (1 - rates[0]) / impressions)) or 1e-4
                    contrast_rows.append({**common, "row_id": f"{test_id}_r{k}", "arm_id": f"{unit}#{k}", "ref_arm_id": f"{unit}#0",
                                          "y": y if y != 0 else 1e-6, "s": s, "decisive": abs(y) > 1.96 * s,
                                          "ref_correct": float(y < 0), "text_lr_correct": float(r.random() < 0.55),
                                          "dir_ceiling_row": 0.8, "s_star": s})
    contrasts = pd.DataFrame(contrast_rows).sort_values(["origin_index", "row_id"]).reset_index(drop=True)
    return World(arms=pd.DataFrame(arm_rows), contrasts=contrasts, rs=pd.DataFrame(score_rows))


def make_answers(world: World, feeds: pd.DataFrame, seed: int = 21, informative: bool = True, gain: float = 900.0) -> pd.DataFrame:
    """Answers of ten readers over the feeds. Every reader leans on the arm's click rate when ``informative``; noise is added."""
    r = np.random.default_rng(seed)
    rate = (world.arms.set_index("arm_id")["clicks"] / world.arms.set_index("arm_id")["impressions"])
    lean = feeds["arm_id"].map(rate).to_numpy() - 0.03
    frames = []
    for reader in range(1, 11):
        prob = 30 + reader + (gain * lean if informative else 0.0) + r.normal(0, 4, len(feeds))
        frames.append(feeds[["block_id", "feed_index", "position"]].assign(reader=reader, prob=np.clip(prob, 0, 100)))
    return pd.concat(frames, ignore_index=True)[["block_id", "feed_index", "reader", "position", "prob"]]
