# Tutorial 5: serve the card over HTTP and through the MCP tool

**You will:** start the HTTP service, ask it for a card with `curl`, read the reliability report through it, and then ask the same questions through the Model Context Protocol (MCP) server that an AI assistant can call as a tool.

**Prerequisites:** [tutorial 1](01-first-card.md) done (the steps below repeat its setup in a fresh folder so that this page runs by itself). `curl` for the HTTP part.

**Time:** about 10 minutes; the commands take under a minute.

**Who this is for:** a team that wants experiment planning tools, notebooks or an assistant to ask for cards without a shell. Both interfaces only read fitted models and reports. The one write is that `POST /card` freezes the card it issues.

## 0. Set up a project

If you still have the folder of tutorial 1, use it and skip this step.

```bash run quiet
mkdir moot-serve && cd moot-serve
moot init > /dev/null
moot ingest --format generic --input mootcourt-data/data/sample-ledger.csv --source-name sample > /dev/null
moot fit --source sample > /dev/null
moot backtest --source sample > /dev/null
```

## 1. Start the HTTP service

Run this section and the rest of the HTTP part in one terminal: the later steps use the variable `SERVER` that this section sets.

The service binds to the loopback address `127.0.0.1` on port 8000 by default. This tutorial uses port 8731 so that it does not clash with anything. It starts in a second or two, and in a real deployment it runs under your process manager. Here it runs in the background of this shell, with its log in a file.

```bash run
moot serve --port 8731 > serve.log 2>&1 &
SERVER=$!
until curl -sf http://127.0.0.1:8731/health > /dev/null; do sleep 0.5; done
curl -s http://127.0.0.1:8731/health | python -m json.tool
```

```text output
{
    "status": "ok",
    "sources": [
        "sample"
    ],
    "boundary": "The card prioritizes and sizes the test. The live test decides. Moot Court never touches a ship, allocation or stopping rule."
}
```

`/health` lists the sources that have a fitted model. If your source is missing, run `moot fit --source NAME` and restart the service (it reads models when it starts).

## 2. Ask for a card

`POST /card` takes the fields of `moot card`: `source` and `impressions` are required, and `origin` is the time whose rows the forecaster may see (the `--origin` option of the command line, see [tutorial 1](01-first-card.md#5-ask-for-a-card)). The service has no `--now`: it uses the clock of the machine it runs on as the issue time. That clock matters here, because the sample ledger's reliability report is old, so this card will abstain, and the output shows why. A ledger without headline text is served by naming the `cell`. The card is returned as JSON and frozen under `cards/`, exactly like a card from the command line.

```bash run
curl -s -X POST http://127.0.0.1:8731/card -H 'content-type: application/json' \
  -d '{"source": "sample", "cell": "checkout_conversion", "impressions": 20000, "origin": "2025-12-30T00:00:00+00:00"}' \
  | python -c "
import json, sys
card = json.load(sys.stdin)
print('cell      ', card['cell'])
print('origin    ', card['origin'])
print('status    ', card['abstention']['status'], card['abstention']['reasons'])
print('detail    ', card['abstention']['details']['reliability'])
print('rung      ', card['prediction']['rung'], 'p_sig', round(card['prediction']['p0']['p_sig'], 3))
"
```

```text output
cell       checkout_conversion
origin     2025-12-30T00:00:00+00:00
status     abstain ['reliability']
detail     reliability report is older than 14 days
rung       P0 p_sig 0.234
```

This card **abstains**, and the reason is on the card: `reliability report is older than 14 days`. The `origin` you send says which rows the forecaster may see. The check on the age of the reliability report uses the real clock of the machine the service runs on, and the sample ledger's reliability report is dated 2025. A real ledger that you join weekly ([tutorial 4](04-weekly-loop.md)) has a fresh report, and its cards carry the full prediction. The abstained card still carries the base-rate forecast (`rung P0`) so that a tool has something to show, with the reasons beside it.

What to look at in a card from the service:

- `abstention.status` is `issue` or `abstain`. Always read it first. When it is `abstain`, the reasons say which trigger fired, and the prediction is not an opinion.
- `prediction` holds the forecast. On a card that gives an opinion it has `p_sig`, the chance that the live test ends significant and positive, and `interval_80` and `interval_90` for the true effect. On an abstained card it holds only the base-rate forecast, under `p0`.
- `robustness` tells how far the answer is from changing a decision at the action threshold, and `skill` how well forecasts like it did in the backtest, with the number of rows that rests on.

The reliability report of a source:

```bash run
curl -s http://127.0.0.1:8731/reliability/sample | python -c "
import json, sys
r = json.load(sys.stdin)
print('as of', r['as_of'])
for cell, e in r['cells'].items():
    print(cell, 'as of', e['as_of'][:10], 'n', e['n'], 'drifted', e['drifted'])
"
```

```text output
as of 2025-12-29T00:00:00+00:00
checkout_conversion as of 2025-12-29 n 7 drifted False
pages_per_session as of 2025-12-29 n 7 drifted False
revenue_per_user as of 2025-12-29 n 7 drifted False
```

Requests that cannot be answered return a JSON error with a status code:

```bash run
curl -s -w '  [HTTP %{http_code}]\n' -X POST http://127.0.0.1:8731/card -H 'content-type: application/json' -d '{"source": "nope", "impressions": 20000}'
curl -s -w '\n[HTTP %{http_code}]\n' -X POST http://127.0.0.1:8731/card -H 'content-type: application/json' -d '{"source": "sample"}' | cut -c 1-160
```

```text output
{"error":"\"no model is registered for source nope; known sources: ['sample']\""}  [HTTP 404]
{"detail":[{"type":"missing","loc":["body","impressions"],"msg":"Field required","input":{"source":"sample"}}]}
[HTTP 422]
```

A source with no model is a 404 and names the sources that have one (the message is a JSON string inside the JSON object, which is why you see escaped quotes). A request that lacks a required field is a 422.

Stop the service (this works in the shell that started it; from another terminal, find the process with `lsof -i :8731` and `kill` its id):

```bash run
kill $SERVER
wait $SERVER 2> /dev/null || true
```

### Safety of the service

There is **no authentication**. It binds to the loopback address, and while it does it accepts only loopback names in the `Host` header, so a web page cannot reach it through a DNS name that resolves to 127.0.0.1. Keep it on loopback, or put your own access control in front of it before binding another address with `--host`. Models are loaded only from the local files that `moot fit` wrote, checked by a digest, and never downloaded.

The service reads `[decision] action_threshold` from `mootcourt.toml` once, at startup. Restart it to change that.

## 3. The MCP server

MCP is the protocol an AI assistant uses to call a tool. `moot mcp` speaks it over standard input and output, which means that an MCP client starts it as a child process. It offers three tools. All three read and propose only: nothing is frozen or written.

| Tool | Returns |
|---|---|
| `get_card` | a card for a proposed change, as JSON |
| `list_precedents` | the highest-weight precedents for the proposal with their weights, effects and experiment ids |
| `reliability_report` | the rolling reliability report of a source |

To register it with an assistant that supports MCP, give the client the command `moot mcp` and make it run in the project folder, which holds `mootcourt.toml` and so tells it where the data root is. If the client cannot set a working folder, set the environment variable `MOOTCOURT_DATA_ROOT` instead. Either one is enough. The script below does the first: it runs from the project folder.

Here is a minimal client written with the MCP Python package, which `moot` already depends on. It starts the server, lists the tools and calls two of them. Your assistant does the same thing without a script.

```bash run
cat > mcp_demo.py <<'PY'
import asyncio
import json

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    params = StdioServerParameters(command="moot", args=["mcp"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("tools:", [t.name for t in tools.tools])
            args = {"source": "sample", "cell": "checkout_conversion", "impressions": 20000, "origin": "2025-12-30T00:00:00+00:00"}
            card = json.loads((await session.call_tool("get_card", args)).content[0].text)
            print("card:", card["abstention"]["status"], card["abstention"]["reasons"], "rung", card["prediction"]["rung"])
            precedents = json.loads((await session.call_tool("list_precedents", {**args, "k": 3})).content[0].text)
            for p in precedents:
                print("precedent:", p["test_id"], "weight", round(p["weight"], 4), "effect", p["y"], "se", p["s"])


asyncio.run(main())
PY
python mcp_demo.py
```

```text output
tools: ['get_card', 'list_precedents', 'reliability_report']
card: abstain ['reliability'] rung P0
precedent: exp-003 weight 0.009 effect 0.015169 se 0.008696
precedent: exp-105 weight 0.009 effect -0.013988 se 0.008751
precedent: exp-115 weight 0.009 effect -0.040743 se 0.008771
```

The `origin` is optional (default now). An origin earlier than the end of the history the model was fitted on is refused, because its parameters were fitted on rows that the origin should not see. A refused request shows up in the client as a generic tool error. The reason is in the server's standard error: in your terminal if you run `moot mcp` yourself, and in the client's MCP log if the client started it.

`list_precedents` is the tool that makes a card explainable to an assistant's user: it names the past experiments that carry the forecast and says how much weight each has. On a ledger without features that tell experiments apart, the weights are nearly equal, as here. On a ledger with headline text, the heaviest precedents are the most similar headlines.

## What you have

A service that gives any tool a card with `curl` or a library call, and an MCP server that gives an assistant the same cards and their precedents, both read-only apart from the one frozen card. For deployment, run `moot serve` under your process manager behind your own access control, and rerun `moot fit` after each join so that it serves the latest model.
