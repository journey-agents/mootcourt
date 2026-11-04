# Tutorial 6: attach a response-simulation agent as a second opinion

**You will:** write a tiny outside agent, register it in `mootcourt.toml`, run it once over the backtest, see how it scores against the model, ask whether it earns a weight, and put its opinion next to a card.

**Prerequisites:** [tutorial 1](01-first-card.md) done (the steps below repeat its setup so that this page runs by itself). The agent here is a rule of thumb, so no model call, account or key is needed. A real agent backed by a language model is attached in exactly the same way.

**Time:** about 20 minutes. Running the agent over the backtest takes 10 to 15 seconds; the rest is reading.

## What a second opinion is

A **response simulator** is any program you or your team already have that gives a second opinion on a proposed test: a pool of simulated readers backed by a language model, a trained click model, a rule of thumb. Moot Court does not care how it works. It gives the program a proposed test, reads back a probability that the live test will end significant and positive, scores that probability on the same backtest as the model, and gives it a **weight of zero** until it earns a weight by beating the model on origins it was not tuned on. The opinion shows next to the model's on the card. It never replaces the model's, and it never touches a ship, allocation or stopping rule.

What goes to the agent is aggregate and non-personal: the source and cell, the origin, the reference and variant headlines if you have them, whether the image or headline changed, the planned exposures per arm, the standard error known before launch, the action threshold and a budget (the number of simulated respondents and a time cap). There is no user-level field, and an unknown field is refused. [Simulators](../simulators.md) lists the whole request and result.

## 0. Set up a project

```bash run quiet
mkdir moot-agent && cd moot-agent
moot init > /dev/null
moot ingest --format generic --input mootcourt-data/data/sample-ledger.csv --source-name sample > /dev/null
moot fit --source sample > /dev/null
moot backtest --source sample > /dev/null
```

## 1. Write the agent

An agent over stdio reads one JSON line on standard input and prints one JSON line. This one guesses that a longer headline and a question mark do better. It is a rule of thumb, chosen to be plainly naive.

```bash run
cat > my_agent.py <<'PY'
import json
import sys

req = json.loads(sys.stdin.readline())
words = len(req["variant_headline"].split())
p = 0.10 + 0.01 * min(words, 12) + 0.05 * ("?" in req["variant_headline"])
print(json.dumps({"p_win_ai": round(p, 2), "n_simulated": 1}))
PY
echo '{"variant_headline": "Is this the best day of the week?"}' | python my_agent.py
```

```text output
{"p_win_ai": 0.23, "n_simulated": 1}
```

(Run directly, the agent sees only the field it reads. Moot Court sends the full request.)

The result must contain `p_win_ai`, a probability in [0, 1] for "the live test ends significant and positive", which is the event the model's `p_sig` forecasts. It may also contain `point_ai` and `interval_ai` for the effect, `n_simulated`, aggregate votes, `cost_usd` and `latency_s`. An agent that cannot answer prints `null`, and that counts as a decline.

## 2. Register it

Add a table to `mootcourt.toml`.

```bash run
cat >> mootcourt.toml <<'EOF'

[simulators.my_agent]
adapter = "stdio"
command = ["python3", "my_agent.py"]
version = "1.0"
knowledge_cutoff = "1970-01-01"   # a rule of thumb has no training data, so any date before the first origin is true
cost_model = "free"
time_cap_s = 20
EOF
moot simulators list
```

```text output
name              adapter      version  knowledge cutoff  cost      weight earned
heuristic         builtin      1        none              free      0 (not earned)
my_agent          stdio        1.0      1970-01-01        free      0 (not earned)
null              builtin      1        none              free      0 (not earned)
```

The columns: the provider's name, its adapter (stdio, http or built-in), its version, its **knowledge cutoff** and the weight it has earned. `heuristic` and `null` are built-ins. Three settings need care:

- **`knowledge_cutoff` is required.** An agent built on a language model may have seen your archive or its public relatives in pretraining. Every record the agent produces carries the cutoff, and a scored origin earlier than it is flagged as possibly contaminated. Without a cutoff every origin counts as possibly contaminated and the agent could never earn a weight. Declare the date its training data ends, honestly.
- **`version`.** A weight belongs to one version. Change the version when you change the agent: a new version starts with weight zero and its own cache.
- **`env`.** The agent runs without a shell with a cleaned environment: every variable that looks like a credential is removed unless you list it by name in `env = ["MY_API_KEY"]`. The command may not run anything inside the data root. [Simulators](../simulators.md) has the full list of rules.

An HTTP agent is registered with `adapter = "http"` and a `url`; it must be on this machine unless you pass `--allow-remote` on the command line.

## 3. Run it once over the backtest

```bash run
moot simulators run --provider my_agent --source sample --out agent.jsonl
```

```text output
my_agent 1.0: 330 requests, 330 called, 0 from the cache, 0 declined, 0 failed (recorded, not cached); cost 0.0000 dollars, agent latency 8.9 s, wall 9.3 s
wrote agent.jsonl
```

The runner asks the agent once for every scored row of the rolling-origin backtest, which here is 330 rows, and writes one record per request: the request digest, the provider and version, the cutoff, the result, the latency and the cost. This took 10 to 15 seconds (the time is the sum over 330 requests; the exact figure moves with the machine) because the agent starts as a new process for each request. Costs matter when the agent calls a language model: use `--limit 20` for a trial run first, and `--max-respondents` and `--max-seconds` to bound each call.

Results are cached under the data root by provider, version and request digest, so running the same command again calls the agent zero times. A **decline** (the agent printed `null`) is cached. A **failure** (a timeout, a crash, an invalid output) is recorded with its reason but not cached, so the next run asks again. The run finishes either way, so one bad call does not lose the others.

## 4. Score it on the backtest

```bash run
moot backtest --source sample --second-opinion agent.jsonl | tail -n 3
```

```text output
wrote ~/moot-agent/mootcourt-data/reports/second-opinion-my_agent/backtest-sample-20261104-80131c793938--second-opinion.md
wrote ~/moot-agent/mootcourt-data/reports/second-opinion-my_agent/backtest-sample-20261104-80131c793938--second-opinion.json
wrote ~/moot-agent/mootcourt-data/reports/second-opinion-my_agent/scores-sample-20261104-80131c793938--second-opinion.parquet
```

This replays the records and writes a separate report next to the main one. It adds two rungs: `agent`, the agent's probability alone, and `P2+agent`, the model's probability stacked with the agent's at the weight in force. Open the report and look at the section "Second opinion":

```bash run
sed -n '/^## Second opinion/,/^Limitation/p' mootcourt-data/reports/second-opinion-my_agent/backtest-sample-*--second-opinion.md | head -n 6
grep -E '^\| all \| (P2|agent) ' mootcourt-data/reports/second-opinion-my_agent/backtest-sample-*--second-opinion.md | cut -d '|' -f 3,4,5,9,10,11
```

```text output
## Second opinion

- Provider: my_agent version 1.0, knowledge cutoff 1970-01-01
- Weight in force: 0.0000 (zero until earned on the backtest)
- Rows scored by the base rung P2: 330; with an opinion: 330; declined: 0; failed calls: 0; absent from the records file: 0
- Cost of the recorded run: 0.0000 dollars, latency 8.9498 seconds in total
 P2 | 330 | 0.1595 | 0.0195 | -0.0071 | 0.0462
 P2 on agent rows | 330 | 0.1595 | 0.0195 | -0.0071 | 0.0462
 agent | 330 | 0.1724 | -0.0598 | -0.1104 | 0.0000
```

The last two lines are the rows `P2` and `agent` of the score table, cut to the columns rung, rows, Brier score, Brier skill and the two ends of its 90 percent interval.

What to look at:

- **Rows with an opinion, declined, failed.** Rows that failed or were declined are counted and scored as declined, never dropped silently.
- **Brier skill of the agent against the base rate, with its interval.** The agent's skill is below zero and its whole interval is below or at zero: it forecast worse than always saying the base rate. A rule of thumb that is not informative here is the expected result.
- **P2 and P2+agent.** With the weight at zero these are identical.
- **Clean and contaminated origins.** The report gives the scores twice: on all origins and on the origins after the agent's cutoff. For a language-model agent trained on public data the "clean" rows may be few or none, and the weight is earned on the clean rows only.

## 5. Ask whether it earns a weight

```bash run
moot earn-weight --source sample --second-opinion agent.jsonl
```

```text output
my_agent 1.0 on origins from 1970-01-01 on, scores scores-sample-20261104-80131c793938.parquet, 147 judged rows (49 tests) with an opinion: 147 judged rows with an opinion from 49 tests is below the gate of 150 tests; weight stays 0
```

The stacked probability is `(1 - w) p_sig + w p_AI`. The weight starts at zero. `earn-weight` puts the recorded rows in time order and cuts them between two origins. It chooses `w` on a grid from the earlier rows and **judges** it on the later rows, never on the same rows. A positive weight is stored only if, on the judged rows, the stacked Brier score beats the model's by the promotion margin (0.02) and those rows come from at least as many distinct experiments as the gate asks (counted in experiments, because rows of one experiment are not independent). Otherwise the weight stays zero, and a weight that no longer passes is reset to zero. Here it says why: 49 judged experiments is far below the gate of 400.

For a real agent on a real ledger, the usual outcome in the first months is also zero. That is the honest answer, not a defect. Run it again as the ledger grows, and run it on a ledger of your own experiments that are newer than the agent's training data.

## 6. See the opinion on a card

```bash run
moot card --source sample --cell checkout_conversion --impressions 20000 --now 2025-12-30T00:00:00+00:00 --simulator my_agent --reference-headline "A plain headline" | sed -n '/^## Prediction/,/^## Robustness/p'
```

```text output
## Prediction

- P(significant and positive): 0.220
- Point estimate: 0.00 units of the ledger's effect
- 80 percent interval for the true effect: -0.03 to 0.04 units of the ledger's effect
- 80 percent interval for the result of the test at the planned standard error: -0.04 to 0.05 units of the ledger's effect
- P(true effect above 0): 0.551
- Rung: P2, weight on precedents 0.0

## Team forecast

- None provided.

## Second opinion

- Provider: my_agent version 1.0, knowledge cutoff 1970-01-01
- P(significant and positive) according to the agent: 0.100
- Model, side by side: P(significant and positive) 0.220
- Weight in force: 0.00
- The weight is zero: the agent has not earned a place in the number yet, so the model's p_sig is the one that counts.

## Robustness
```

The agent was called live for this card, and its probability, its provider and version and the weight in force appear next to the model's. When the weight is zero the card says so in words, and the agent's number is information, not a forecast anyone should act on. A card that abstains shows no second opinion.

`moot simulators list` also prints **displaced weights**: when a newer version of an agent earns a weight, the older version's record is moved aside, not deleted, and the registry keeps every weight that was ever in force.

## What you have

An outside agent attached without a code change, scored on the same out-of-time backtest as the model, held at weight zero until it earns more, with its cutoff recorded so that contamination is visible. To use a language-model agent, replace the body of `my_agent.py` (the template `examples/simulators/persona_pool_template.py` in the repository marks the call to fill in) and keep everything else.
