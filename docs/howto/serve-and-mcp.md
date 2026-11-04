# Serve the card and use the MCP tool

This is the short form. [Tutorial 5](../tutorials/05-serve-http-and-mcp.md) runs the service and an MCP client and shows their output.

Both interfaces read fitted models and reports from the data root. Fit and back-test first.

## HTTP service

```
moot serve
```

The service binds to `127.0.0.1:8000`. It offers `POST /card`, `GET /reliability/{source}` and `GET /health`. `POST /card`
issues a card and freezes it; that is the only write. Request body:

```json
{"source": "sample", "cell": "checkout_conversion", "impressions": 20000, "row_id": "sample:exp-101:treatment::checkout_conversion"}
```

This is the request for the sample ledger of the [quickstart](../quickstart.md), whose cells are metrics, so it names a `cell`. A ledger with headline text takes `headline` and `image_changed` instead and needs no cell. Without a cell on a ledger of metrics the service answers 422 and lists the cells. With the server running, send it from another terminal:

```
curl -s -X POST http://127.0.0.1:8000/card -H 'content-type: application/json' \
  -d '{"source": "sample", "cell": "checkout_conversion", "impressions": 20000}'
```

The answer is the card as JSON (HTTP 200). On the sample ledger it abstains for `reliability`, because the sample's reliability report is old (see below); [tutorial 5](../tutorials/05-serve-http-and-mcp.md) reads such a card line by line. Stop the server with Ctrl-C.

`row_id` is optional: it names the ledger row (`source:test_id:variant_id`) that the weekly join will attach the outcome to. A card without it is valid, but no join can find it. The MCP tool takes the same argument and only echoes it, because it never freezes a card. The service uses its own clock as the issue time and has no `now` field, so a source whose reliability report is more than 14 days old gets abstained cards; join fresh results first.

The service has no authentication. Keep it on the loopback address, or put your own access control in front of it.

## MCP server

```
moot mcp
```

The server speaks the Model Context Protocol over stdio and offers three tools that read and propose only:

| Tool | Returns |
|---|---|
| `get_card` | A card for a proposed change, as JSON. Nothing is frozen or written. |
| `list_precedents` | The highest-weight precedents for the proposal, with their weights, effects and test ids. It takes an optional `exposure`; without it the average exposure of the fit is used. |
| `reliability_report` | The rolling reliability report of a source. |

An origin earlier than the model's fit cutoff is refused by `get_card` and `list_precedents`, because the parameters were
fitted on later rows.

To register it with an MCP client, give the client the command `moot mcp` and the data root as an environment variable.
