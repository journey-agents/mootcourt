"""Built-in providers: ``null`` (the default, always declines) and ``heuristic`` (deterministic, for tests and as the
example of the protocol)."""
from __future__ import annotations

import math
import re

from mootcourt.simulators.base import SimulationRequest, SimulationResult, SimulatorInfo


class NullSimulator:
    """The default provider: it has no opinion, so the stacking weight can never become positive."""

    def describe(self) -> SimulatorInfo:
        return SimulatorInfo("null", "1", None, "free", "Declines every request; the default provider.")

    def simulate(self, request: SimulationRequest) -> SimulationResult | None:
        return None


class HeuristicSimulator:
    """Deterministic opinion from structured headline features only.

    Not a model of respondents: a logistic of a few visible headline traits around a base probability. It exists to
    show the protocol and to drive tests without any model call. Probabilities stay in [0.02, 0.60].
    """

    def describe(self) -> SimulatorInfo:
        return SimulatorInfo("heuristic", "1", None, "free",
                             "Deterministic logistic of headline length, a question mark, a number and an image change.")

    def simulate(self, request: SimulationRequest) -> SimulationResult | None:
        h = request.variant_headline
        words = len(h.split())
        z = -1.8 + (0.35 if "?" in h else 0.0) + (0.25 if re.search(r"\d", h) else 0.0) + 0.05 * (min(words, 14) - 8)
        z += 0.2 if request.image_changed else 0.0
        p = 1.0 / (1.0 + math.exp(-z))
        p = min(0.60, max(0.02, p))
        return SimulationResult(p_win_ai=p, n_simulated=0, provider_id="heuristic", version="1", notes="heuristic")
