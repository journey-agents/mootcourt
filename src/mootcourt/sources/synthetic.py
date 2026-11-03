"""Synthetic source with known truth, for calibration tests and the gate power simulation.

Every row has ``source == "synthetic"`` and every rendered output that uses it carries
``SYNTHETIC_LABEL``. Truth (``theta_true``) is returned separately and never stored in the ledger.

Model. Test i has a cell, a start time and a test-level effect ``u_i ~ Normal(0, test_effect_sd^2)``
shared by its variants. Variant j has a latent effect

    theta_ij = mu_cell + shift + u_i + text_effect_strength * (signal_ij - 0.5) + e_ij,
    e_ij ~ Normal(0, tau_cell^2),

where ``signal_ij`` is 1 when the headline contains a word of ``SIGNAL_WORDS`` (half of all headlines
do). With ``text_effect_strength = 0`` and ``test_effect_sd = 0`` (the defaults) theta has exactly mean
``mu_cell`` and sd ``tau_cell``; a nonzero strength adds ``strength^2 / 4`` to the variance. The
observed effect is ``y = theta + Normal(0, s^2)`` with ``s`` log-normal around ``s_scale``.

Units: ``theta``, ``y``, ``s``, ``mu`` and ``tau`` are all in the same units (percent lift).
Origin semantics: ``final_read_at = started_at + 7 days`` and ``usable_after = final_read_at + 7 days``,
so a row is visible at an origin when it is admitted and ``usable_after <= origin``.
"""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from mootcourt.ledger import LEDGER_COLUMNS, SCHEMA_VERSION, make_row_id, quarter_of, validate_ledger

SYNTHETIC_LABEL = "synthetic"
SOURCE = "synthetic"

SIGNAL_WORDS = ("amazing", "secret", "shocking", "unbelievable", "heartbreaking", "genius", "incredible", "powerful")
_TOPICS = (
    "dog", "cat", "teacher", "doctor", "student", "mother", "father", "farmer", "soldier", "artist",
    "scientist", "pilot", "baker", "child", "senator", "athlete", "nurse", "driver", "writer", "mayor",
    "river", "city", "school", "factory", "garden", "bridge", "island", "market", "library", "village",
    "engine", "planet", "forest", "ocean", "mountain", "kitchen", "airport", "museum", "hospital", "stadium",
)
_FILLERS = (
    "found", "says", "shows", "wants", "makes", "changes", "asks", "tells", "builds", "saves",
    "the", "a", "this", "that", "every", "nobody", "everyone", "world", "year", "story",
    "how", "why", "when", "what", "will", "can", "could", "should", "just", "about",
    "money", "love", "home", "future", "truth", "reason", "answer", "problem", "idea", "moment",
    "people", "history", "dream", "lesson", "chance", "small", "big", "new", "old",
)
_DEFAULT_CELLS = {"headline_only": (2.0, 3.0), "image_only": (-1.0, 1.5), "both": (0.5, 2.0)}
_IMAGE_CHANGED = {"image_only": True, "both": True}
_HORIZON_DAYS = 7
_SPAN_DAYS = 820
_START = dt.datetime(2013, 1, 1, tzinfo=dt.timezone.utc)


@dataclass(frozen=True)
class SyntheticConfig:
    """Configuration of the synthetic generator.

    ``cell_params`` maps a cell name to ``(mu, tau)`` in percent lift. ``s_scale`` is the median
    standard error of ``y`` in the same units. ``shift_at`` and ``shift_delta`` move mu for tests that
    start at or after ``shift_at``. ``team_forecaster_sd`` (units of theta) adds a labeled synthetic
    team forecast to every row's features_json. ``low_exposure_frac`` is the share of rows given
    status ``low_exposure``.
    """

    seed: int = 0
    n_tests: int = 1000
    variants_per_test: int = 2
    cell_params: dict[str, tuple[float, float]] = field(default_factory=lambda: dict(_DEFAULT_CELLS))
    s_scale: float = 1.5
    s_log_sd: float = 0.25
    test_effect_sd: float = 0.0
    text_effect_strength: float = 0.0
    low_exposure_frac: float = 0.0
    shift_at: dt.datetime | None = None
    shift_delta: float = 0.0
    team_forecaster_sd: float | None = None
    start: dt.datetime = _START
    span_days: float = _SPAN_DAYS


def _validate(cfg: SyntheticConfig) -> None:
    if cfg.n_tests < 1:
        raise ValueError("n_tests must be at least 1")
    if not 1 <= cfg.variants_per_test <= 4:
        raise ValueError("variants_per_test must be between 1 and 4")
    if not cfg.cell_params:
        raise ValueError("cell_params must name at least one cell")
    if any(tau < 0 for _, tau in cfg.cell_params.values()) or cfg.s_scale <= 0:
        raise ValueError("tau must be nonnegative and s_scale positive")
    if not 0.0 <= cfg.low_exposure_frac < 1.0:
        raise ValueError("low_exposure_frac must be in [0, 1)")
    if cfg.team_forecaster_sd is not None and cfg.team_forecaster_sd <= 0:
        raise ValueError("team_forecaster_sd must be positive")


def generate(cfg: SyntheticConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate ``(ledger, truth)``; the same config always gives the same frames.

    The ledger passes ``validate_ledger`` and is sorted by test start time. ``truth`` has columns
    ``row_id`` and ``theta_true`` (same units as ``y``).
    """
    _validate(cfg)
    rng = np.random.default_rng(cfg.seed)
    n_t, k = cfg.n_tests, cfg.variants_per_test
    cells = list(cfg.cell_params)
    n = n_t * k

    # Test-level draws.
    start_offsets = np.sort(rng.uniform(0.0, cfg.span_days, n_t))
    cell_idx = rng.integers(0, len(cells), n_t)
    topic_idx = rng.integers(0, len(_TOPICS), n_t)
    u_test = rng.normal(0.0, cfg.test_effect_sd, n_t) if cfg.test_effect_sd > 0 else np.zeros(n_t)

    # Variant-level draws.
    test_of = np.repeat(np.arange(n_t), k)
    variant_of = np.tile(np.arange(k), n_t)
    signal = rng.random(n) < 0.5
    mu = np.array([cfg.cell_params[c][0] for c in cells])[cell_idx][test_of]
    tau = np.array([cfg.cell_params[c][1] for c in cells])[cell_idx][test_of]
    started = [cfg.start + dt.timedelta(days=float(d)) for d in start_offsets]
    started_row = pd.to_datetime([started[i] for i in test_of], utc=True)
    shift = np.zeros(n)
    if cfg.shift_at is not None:
        shift = np.where(started_row >= pd.Timestamp(cfg.shift_at), cfg.shift_delta, 0.0)
    theta = mu + shift + u_test[test_of] + cfg.text_effect_strength * (signal - 0.5) + rng.normal(0.0, 1.0, n) * tau

    s = cfg.s_scale * np.exp(rng.normal(0.0, cfg.s_log_sd, n))
    low = rng.random(n) < cfg.low_exposure_frac
    s = np.where(low, s * 3.0, s)
    y = theta + rng.normal(0.0, 1.0, n) * s
    n_arm = np.where(low, rng.integers(100, 1000, n), rng.integers(2000, 40000, n))

    # Headlines: one shared topic word per test, filler words, a signal word iff signal.
    headlines, feats = [], []
    n_fill = rng.integers(2, 5, n)
    fill_idx = rng.integers(0, len(_FILLERS), (n, 4))
    sig_idx = rng.integers(0, len(SIGNAL_WORDS), n)
    pos = rng.random(n)
    if cfg.team_forecaster_sd is not None:
        point_team = theta + rng.normal(0.0, cfg.team_forecaster_sd, n)
        p_win_team = stats.norm.cdf(point_team / cfg.team_forecaster_sd)
    for r in range(n):
        words = [_TOPICS[topic_idx[test_of[r]]]] + [_FILLERS[j] for j in fill_idx[r, : n_fill[r]]]
        if signal[r]:
            words.insert(1 + int(pos[r] * len(words)) % len(words), SIGNAL_WORDS[sig_idx[r]])
        headline = " ".join(words)
        headlines.append(headline)
        f = {"headline": headline, "image_changed": bool(_IMAGE_CHANGED.get(cells[cell_idx[test_of[r]]], False))}
        if cfg.team_forecaster_sd is not None:
            f["p_win_team"] = float(p_win_team[r])
            f["point_team"] = float(point_team[r])
            f["team_label"] = SYNTHETIC_LABEL
        feats.append(json.dumps(f, sort_keys=True))

    final = started_row + pd.Timedelta(days=_HORIZON_DAYS)
    usable = final + pd.Timedelta(days=_HORIZON_DAYS)
    test_ids = [f"t{i:06d}" for i in test_of]
    variant_ids = [f"v{j}" for j in variant_of]
    status = np.where(low, "low_exposure", "admitted")
    ledger = pd.DataFrame(
        {
            "row_id": [make_row_id(SOURCE, t, v) for t, v in zip(test_ids, variant_ids)],
            "source": SOURCE,
            "test_id": test_ids,
            "variant_id": variant_ids,
            "cell": [cells[c] for c in cell_idx[test_of]],
            "period": [quarter_of(t) for t in final],
            "started_at": started_row,
            "final_read_at": final,
            "usable_after": usable,
            "y": y.astype("float64"),
            "s": s.astype("float64"),
            "n_ref": n_arm.astype("int64"),
            "n_var": n_arm.astype("int64"),
            "status": status,
            "features_json": feats,
            "schema_version": np.full(n, SCHEMA_VERSION, dtype="int64"),
        }
    )[LEDGER_COLUMNS]
    validate_ledger(ledger)
    truth = pd.DataFrame({"row_id": ledger["row_id"], "theta_true": theta})
    return ledger, truth
