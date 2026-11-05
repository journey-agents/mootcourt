# Response simulators

A response simulator is an agent built outside this repository that gives a second opinion on a proposed test. It might
be a pool of simulated readers backed by a language model, a trained click model, or a rule of thumb. Moot Court
attaches it without a code change, scores it on the out-of-time backtest, and gives it zero weight until it earns some.
The opinion never touches a ship, allocation or stopping rule: the card prioritizes and sizes the test, and the live test
decides.

## What goes in and what comes out

The request holds aggregate, non-personal inputs only: the source, the cell, the origin, the reference and variant
headlines, whether the image or the headline changed, the planned units per arm, the standard error known before
launch, the action threshold and a budget (simulated respondents and seconds). There is no user-level field, and an
unknown key is refused.

The result holds `p_win_ai` in [0, 1], the probability that the live test ends with a significant positive estimate, the
same event that `p_sig` forecasts. It may also hold `point_ai` and `interval_ai` in the effect's units, `n_simulated`,
aggregate `raw_votes`, `cost_usd` and `latency_s`. An agent that cannot answer prints `null` and the request is a decline.

## Attach an existing agent over stdio

The agent reads one JSON line on stdin and prints one JSON line. This is a whole agent.

```python
import json, sys

req = json.loads(sys.stdin.readline())
words = len(req["variant_headline"].split())
p = 0.10 + 0.01 * min(words, 12) + 0.05 * ("?" in req["variant_headline"])
print(json.dumps({"p_win_ai": p, "n_simulated": 1}))
```

Register it in `mootcourt.toml`.

```toml
[simulators.my_agent]
adapter = "stdio"
command = ["python3", "my_agent.py"]
version = "1.0"
knowledge_cutoff = "2025-06-01"   # required: the date its training data ends
cost_model = "per_call"           # free, per_call or per_token
time_cap_s = 20
env = ["MY_AGENT_API_KEY"]        # names it needs; every other KEY, TOKEN or SECRET variable is removed
```

The process runs without a shell, in its own process group, with the config file's folder as its working directory. A time cap
kills the whole group, and so does an interrupt or any other exit, so a wrapper such as `sh -c` or `uv run` cannot leave the agent
running. Output beyond one megabyte is refused. Every variable whose name looks like a credential (KEY, TOKEN, SECRET, PASSWORD,
CREDENTIAL, DSN, COOKIE, SESSION, BEARER, PRIVATE, or the whole words PASS, AUTH, PAT and CERT), every proxy variable and every `*_URL` or
`*_URI` variable that carries a login is removed unless you declare it by name in the provider's `env` list. `PIP_CERT`, `NO_PROXY` and the public certificate paths (`SSL_CERT_FILE`, `SSL_CERT_DIR`, `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE`) are kept. An agent that must reach the network through a proxy needs each proxy variable it uses (`HTTPS_PROXY`, `HTTP_PROXY`, `ALL_PROXY`) declared, because a proxy address often carries a login. A command that would run anything inside the data root is
refused: the working directory, the program, any argument that names a path (also after an `=` or in a `:` separated list, as in `--config=path`), the words of the string after `sh -c` (or `bash`, `zsh`, `dash`, `ksh`), and the file a
`-m module` or `-mmodule` argument would load, whatever the letter case on a case-insensitive volume. A wrapper through `env` is checked as the program it starts: its long options are read by unique prefix, as GNU env reads them (`--spl` is `--split-string`), and the string of `env -S` is split into words that are checked like any other. A shell string is split into words and each word is checked as a path; what a shell would build while it runs (variables, command substitution, a path joined from pieces) is not evaluated, so a shell wrapper is a convenience to review and not a sandbox. Nothing downloaded or generated there is ever run.

`knowledge_cutoff` is required for every stdio and http provider. Without it every origin would count as possibly
contaminated and the agent could never earn a weight. An agent with no training data of its own can declare a date before the
earliest origin.

## Attach an agent behind HTTP

The adapter POSTs the request JSON and reads the result JSON. Loopback only by default; pass `--allow-remote` on the command line for any other host (a config table cannot grant it). The time cap is a wall clock for the whole exchange: a server that sends one byte at a time is cut off at the cap. Proxy settings in the environment are ignored, redirects are not followed and a reply larger than one megabyte is refused. Two limits to know about. The cap cannot interrupt name resolution, so with `--allow-remote` a host name that is slow to resolve is not cut short at the cap, although your call still gets its timeout on time. And a request may still be sent after your call has timed out: the cap applies to the whole exchange, but a request that has already left may be received by the agent even though the caller recorded a timeout, so an agent should treat a repeated or abandoned request as harmless. A host with several addresses can also use one cap per address while connecting, in the background.

```python
from http.server import BaseHTTPRequestHandler, HTTPServer
import json

class Agent(BaseHTTPRequestHandler):
    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        body = json.dumps({"p_win_ai": 0.12, "n_simulated": 1}).encode()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body)

HTTPServer(("127.0.0.1", 8765), Agent).serve_forever()
```

```toml
[simulators.my_service]
adapter = "http"
url = "http://127.0.0.1:8765/simulate"
```

Python packages can register providers instead, through the entry point group `mootcourt.simulators`: the entry names a
class or a zero-argument function that returns an object with `describe()` and `simulate(request)`.

## Backtest it once, replay it for free

```bash
moot simulators list
moot simulators run --provider my_agent --source upworthy --origins quarterly --out agent.jsonl
moot backtest --source upworthy --second-opinion agent.jsonl
moot earn-weight --source upworthy --second-opinion agent.jsonl
```

`run` calls the agent once per scored row of the rolling-origin backtest and writes one record per request: the request
hash, provider id and version, knowledge cutoff, result, latency and cost. Results are cached under the cache folder of
the storage root, keyed by provider, version and request hash, so a second run never calls the agent again. A new version
starts a new cache. A cache hit takes the provider's version and knowledge cutoff from the provider as it is described now, so a corrected
cutoff reaches the records and the contamination split follows it; an entry that no longer passes the result check counts as a miss.
Replaying a records file never writes to that cache. `backtest --second-opinion` replays the file and adds two rungs to a separate report: `agent` (its
probability alone) and `P2+agent` (the stacked probability at the weight in force). Rows with no result are scored as
declined and counted.

A decline is the agent printing `null`, and it is cached. A timeout, a command that would not start, a non-zero exit, a
connection error or an output that is not a valid result is a failure: the record says so, with the reason, the run still
finishes and writes every record, and nothing is cached, so the next run asks the agent again. Probabilities and intervals
are checked again when a records file is read back, and a bad value stops the command with the record named.

## How the weight is earned

The stacked probability is `(1 - w) p_sig + w p_AI`. The weight starts at zero. `moot earn-weight` puts the recorded rows
with an opinion in time order and cuts them between two origins. It chooses `w` on a grid by Brier score on the origins
before an inner cut and judges it on the later origins, never on the same rows. A positive weight is written to the registry only when,
on the judged rows, the stacked Brier score beats `p_sig` by the earn-weight margin (0.02) and those judged rows come from at least as many distinct tests as the gate's n (the gate counts tests, not rows, because rows of one test are not independent).
Otherwise it stays zero, and a weight that no longer passes is reset to zero. The scores come from the backtest of the current
ledger snapshot, found by its id.

A weight belongs to one provider version and to the champion it was earned on. A new version starts at zero. After a promotion
the weight lapses until it is earned again. The card shows the agent's probability, the provider id and version and the weight
in force next to `p_sig`, and says in words when the weight is zero.

## Contamination

An agent built on a language model may have seen this public archive in pretraining. Every record carries the provider's
knowledge cutoff. A scored origin earlier than the cutoff is flagged as possibly contaminated, and so is every origin of a
provider that declares no cutoff. The report shows contaminated and clean scores separately, and `earn-weight` uses clean
origins only unless you pass `--include-contaminated`. A weight earned that way is stored with a contaminated flag, and the
card and the report say so next to the weight. On archives that end before any current model's cutoff, that means a language-model agent
cannot earn weight from this data. That is the honest answer, not a bug: run it on a ledger of your own tests that are
newer than its cutoff.

## The audit record of displaced weights

An earned weight belongs to one version of a provider on one champion. When a newer version of the same provider earns a weight on the same source, the older version's record is moved aside, not deleted. `moot simulators list` prints these under "displaced weights", and the registry file (`registry.json` under the models folder, key `second_opinion_history`) is the audit record of every weight that was ever in force. A displaced weight is never applied to a card.
