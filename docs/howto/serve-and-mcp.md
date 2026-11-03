# Serve the card and use the MCP tool

Both interfaces read fitted models and reports from the data root. Fit and back-test first.

## HTTP service

```
moot serve
```

The service binds to `127.0.0.1:8000`. It offers `POST /card`, `GET /reliability/{source}` and `GET /health`. `POST /card`
issues a card and freezes it; that is the only write. Request body:

```json
{"source": "mine", "headline": "A plain headline", "image_changed": false, "impressions": 20000}
```

The service has no authentication. Keep it on the loopback address, or put your own access control in front of it.

## MCP server

```
moot mcp
```

The server speaks the Model Context Protocol over stdio and offers three tools that read and propose only:

| Tool | Returns |
|---|---|
| `get_card` | A card for a proposed change, as JSON. Nothing is frozen or written. |
| `list_precedents` | The highest-weight precedents for the proposal, with their weights, effects and test ids. |
| `reliability_report` | The rolling reliability report of a source. |

An origin earlier than the model's fit cutoff is refused by `get_card` and `list_precedents`, because the parameters were
fitted on later rows.

To register it with an MCP client, give the client the command `moot mcp` and the data root as an environment variable.
