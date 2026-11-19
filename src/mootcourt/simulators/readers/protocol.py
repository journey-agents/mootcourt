"""The fixed protocol of the simulated readers: seed, random streams, models and sizes. Fixed before any model call."""
from __future__ import annotations

import numpy as np

SEED = 20261118
STREAMS = {"blocks": 1, "arms": 2, "positions": 3, "probe_set": 4, "examples": 5, "brief_draw": 6, "bootstrap": 7,
           "probe_items": 8}

MODELS = ("claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5")
PRIMARY_MODEL = MODELS[0]

BLOCK_SIZE = 30
N_READERS = 10
HALVES = ((1, 2, 3, 4, 5), (6, 7, 8, 9, 10))
CELL = "headline_only"
Z = 1.96


def rng(stream: str, *keys: int) -> np.random.Generator:
    """The generator of one named stream and its integer keys. Each draw of the protocol has its own."""
    return np.random.default_rng([SEED, STREAMS[stream], *(int(k) for k in keys)])
