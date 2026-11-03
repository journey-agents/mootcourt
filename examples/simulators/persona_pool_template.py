"""Template for a persona-pool agent. The language model call is a STUB: nothing here contacts any model.

A persona pool asks a set of described readers which of two headlines they would click, then turns the share that
prefer the variant into the probability the live test ends significant and positive. To use it, replace the body of
`ask_persona` (marked STUB) with your own model call, keep the aggregate output, and register the script as a stdio
provider. Personas are aggregate descriptions of reader groups, never real people, and the request carries no
user-level data.

The mapping from the share to a probability is a rough normal approximation. Calibrate it on your own recorded runs
before trusting it, and let the backtest decide the weight: it starts at zero.
"""
import hashlib
import json
import math
import sys

PERSONAS = [
    {"group": "skims on a phone, short attention", "weight": 0.4},
    {"group": "reads long form, curious about causes", "weight": 0.3},
    {"group": "shares things that feel fair or kind", "weight": 0.3},
]


def ask_persona(persona: dict, reference: str, variant: str) -> float:
    """STUB: return the chance, in [0, 1], that this persona clicks the variant over the reference.

    Replace this body with your model call. The stub below is a deterministic placeholder derived from a hash, so the
    template runs offline and returns something between 0.4 and 0.6.
    """
    digest = hashlib.sha256(f"{persona['group']}|{reference}|{variant}".encode()).digest()
    return 0.4 + 0.2 * digest[0] / 255.0


def share_to_p_sig(share: float, s_star: float) -> float:
    """Normal approximation: a share above one half maps to a small positive effect, compared with 1.96 standard errors."""
    effect = 0.5 * (share - 0.5)                       # percentage points per unit of share, a placeholder scale
    z = (effect - 1.96 * s_star) / s_star
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def main() -> None:
    req = json.loads(sys.stdin.readline())
    n = min(len(PERSONAS), req["budget"]["max_respondents"])
    votes = [ask_persona(p, req["reference_headline"], req["variant_headline"]) * p["weight"] for p in PERSONAS[:n]]
    share = sum(votes) / sum(p["weight"] for p in PERSONAS[:n])
    out = {"p_win_ai": round(share_to_p_sig(share, req["s_star"]), 4), "n_simulated": n, "raw_votes": {"variant_share": round(share, 4)}}
    print(json.dumps(out))


if __name__ == "__main__":
    main()
