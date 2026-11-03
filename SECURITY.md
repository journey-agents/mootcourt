# Security

## Reporting a problem

Write to liyingjie@journey-ai.net with the version (`moot --version`), what you did and what happened. Please do not
open a public issue for a vulnerability. You will get an answer within seven days.

## Supported versions

Only the latest 0.x release receives fixes.

## What the software does with your data

- Ledgers, models, reports and cards stay on the machine under the data root. Nothing is uploaded.
- No default code path calls a language model or the network. The service binds to the loopback address unless you
  say otherwise, and only its card endpoint writes (it freezes the card).
- The MCP server is read-only.
- A response simulator is an outside program that you configure. The stdio adapter runs it without a shell, in its own
  process group, with credential-like environment variables removed unless you declare them, and refuses a command that
  lies inside the data root. The HTTP adapter sends requests to loopback by default, ignores proxy settings, does not
  follow redirects and bounds the reply. A request carries aggregate inputs only, never user-level fields.
- Downloads come from a fixed allow-list, are checked against pinned checksums and are never executed.

## Out of scope

The accuracy of a forecast is a method question, not a vulnerability; see `docs/method.md` for what the tool claims.
