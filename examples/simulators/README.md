# Simulator examples

- `stdio_agent.py`: a working stdio agent. Register it with the `example_stdio` table in `mootcourt.toml` and run
  `moot simulators run --provider example_stdio --source synthetic --origins quarterly --out agent.jsonl`.
- `persona_pool_template.py`: a persona-pool template. The call that would reach a language model is a stub, marked
  STUB, and nothing in this folder contacts a model or the network.

Both read one JSON request line on standard input and print one JSON result line. The request and result fields are in
`docs/simulators.md`.
