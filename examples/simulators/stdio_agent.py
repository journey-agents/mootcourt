"""A working stdio agent in about twenty lines: one JSON request on stdin, one JSON result on stdout.

It is not a model of respondents. It scores a headline with three visible traits so that the protocol can be tried
end to end with no model call. Replace the body of `opinion` with your own agent.
"""
import json
import math
import sys


def opinion(req: dict) -> dict:
    """Return the agent's probability that the test ends significant and positive, and a point estimate."""
    h = req["variant_headline"]
    score = -1.6 + 0.4 * ("?" in h) + 0.3 * any(c.isdigit() for c in h) + 0.04 * (min(len(h.split()), 14) - 8)
    p = 1.0 / (1.0 + math.exp(-score))
    return {"p_win_ai": round(p, 4), "point_ai": round(2.0 * req["s_star"] * (p - 0.15), 4), "n_simulated": 1, "notes": "example agent"}


if __name__ == "__main__":
    print(json.dumps(opinion(json.loads(sys.stdin.readline()))))
