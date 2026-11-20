# Simulated readers through the vendor's API: a second run (run 12)

Written on 19 November 2026, before any call is made with an API key and before any reply of run 11 is scored or read.

**Parent plan:** `docs/superpowers/plans/2026-11-18-simulated-readers.md`. Everything there stands unless this file says otherwise.

**Spec:** `docs/superpowers/specs/2026-11-18-llm-simulated-readers-design.md`.

## Why a second run

Run 11 reaches the models through the command line tool under a subscription login. Amendment 10 of the parent plan records what that tool adds to every call and the wrapper cannot remove: a sentence naming the agent kit, an environment block with the present date, a reminder about the account, and a token budget tag. A reader in run 11 is therefore told the present date beside the instruction to play a person of 2013 to 2015.

Run 12 sends the same requests through the vendor's Messages API with a key. The model then receives the system prompt and the reader's prompt and nothing else. The run answers one question: do the results of run 11 depend on the context the tool adds?

## What is known when this is written

- Run 11's calls for `claude-opus-5-5` and `claude-sonnet-5-5` are stored, and the calls for `claude-haiku-5-5` are being made. No reply has been read and nothing has been scored. Only counts of stored files and the lengths of requests and replies have been looked at, to estimate the cost of this run.
- The one outcome figure known to the author is still the earliest-arm rule's accuracy of 0.570.

## What stays the same

- The plan folder of run 11, file for file, with the checksums in the parent plan's record. The requests of run 12 are the requests of run 11: same model names, same system prompts, same prompts, same request hashes.
- The three models, the seven methods, the three readings, the family of three, the bootstrap, the probes, and every report key.
- The rules of the wrapper: up to three attempts per request, a reply is checked against the form the prompt states, a reply that reports another model is a transport failure, and five calls in a row without a usable reply stop the run with exit code 3.
- Run 11 remains the run that the parent plan declared. Its verdict words for `claude-opus-5-5` are the ones the paper's fixed wording is chosen from.

## What changes

1. **Transport.** The call goes through the vendor's Python package (`anthropic`), `client.messages.create`, with `model`, `system`, one user message holding the prompt, and `max_tokens` of 16,000. No tool is declared. No other field is sent.
2. **No sampling setting.** These three models reject a temperature other than the default, so none is sent. Thinking and effort are left at each model's default: the vendor documents the default effort as medium for `claude-opus-5-5` and `claude-haiku-5-5` and high for `claude-sonnet-5-5`. The run folder records this.
3. **No fallback model.** The vendor offers a setting that reruns a declined request on another model. It is not used, because a reply from another model is not a reply of the model under test.
4. **A declined request.** A response whose stop reason is a refusal has its text, possibly empty, treated as a reply. It fails the check, is tried again, and after three attempts is stored as a refusal, as in run 11.
5. **A reply cut at the token limit** fails the check like any other bad reply.
6. **Transport failures.** A rate limit, a server error, a timeout, a connection error, a rejected key and a rejected request are transport failures after the package's own retries (five). Nothing is stored for them.
7. **What a record adds.** Each stored record also holds the token counts the API reports (`usage`). The field `tool_version` holds the package's name and version. Both are additive.
8. **The key.** The script never takes the key as an argument and never prints or stores it. The package reads it from the environment variable `ANTHROPIC_API_KEY`, which the operator's shell fills from a file outside the repository. No tracked file names that file.
9. **Canary.** For each model, one call on the invented headlines of run 11's canary. It passes when the reply satisfies the form, the response reports the model asked for, and the response holds no tool call. The canary file stores the request body without the key.
10. **Dependency.** A new optional extra, `readers-api`, holds `anthropic`. The default install does not gain it, and no default path calls a model.

## Files

- Create `src/mootcourt/simulators/readers/api.py`: `call(model, system, prompt, schema=None, *, time_cap_s=180.0) -> ToolReply` and `canary(model, system, prompt) -> dict`. `ToolReply` gains an optional `usage: dict | None = None`.
- Modify `src/mootcourt/simulators/readers/transcripts.py`: `ask(..., transport="tool")` chooses the call; a record stores `usage` when the reply has one.
- Modify `src/mootcourt/simulators/readers/pipeline.py` and `scripts/simulated_readers.py`: the option `--transport {tool,api}` on `run` and `canary`, default `tool`; `score --label LABEL` writes `run_label` into each report and puts the label into the report's file name; without it nothing changes. A new stage `compare --plan DIR --tool DIR --api DIR --reports DIR --label LABEL --out DIR --commit HASH` writes the comparison and calls no model.
- Modify `src/mootcourt/simulators/readers/measures.py`: `transport_report(contrasts, feeds, tool_plain, api_plain) -> dict`, described below.
- Tests: `tests/test_readers_api.py` with a stand-in client (no network), and additions to the pipeline and script tests.
- Docs: a section in `docs/simulated-readers.md`; one numbered decision in `docs/method.md`.

## The comparison between the two runs, fixed now

For each model, `score` with both transcript folders writes `simulated-readers-transport-<model>-<snapshot>.json` with these keys:

- `plain.agree_share`, `plain.n`, `plain.left_out`: the share of contrasts on which the plain panels of the two runs give the same direction, among contrasts where neither panel is tied or missing.
- `plain.accuracy_api_minus_tool` with `estimate`, `lo`, `hi`, `se`: the difference in plain accuracy, run 12 minus run 11, on the same contrasts, with the block bootstrap of the parent plan (63 blocks, B = 500). `lo` and `hi` are the 5th and 95th percentiles over resampled blocks, as for every difference outside a family in the parent plan. This is one comparison per model and belongs to no family. (Corrected on 19 November 2026 before any code or call of this run: the first wording named a 95 percent interval, which is not what the existing function gives.)
- `readings.<name>.api` and `readings.<name>.tool`: the three readings of each run side by side, copied from the two model reports.

How the paper reads it, decided now:

- If the interval of `plain.accuracy_api_minus_tool` for `claude-opus-5-5` contains zero, the paper says the added context did not move the plain panel's accuracy by an amount this design can detect, and gives the interval.
- If it does not contain zero, the paper says the transport changed the result, gives both accuracies, and reports the readings of both runs with equal weight. The verdict words still come from run 11, and the paper says a reader may prefer run 12 because its context is clean.
- In either case the three readings of run 12 are printed beside those of run 11 for all three models. No method, prompt, seed or rule changes because of what either run shows.

## Cost and its ceiling

From the lengths of run 11's requests, one model's calls hold roughly 11 to 15 million input tokens. Output is dominated by thinking, which run 11 did not record. At the vendor's list prices on 19 November 2026 (per million tokens, input and output: 4 and 20 dollars for `claude-opus-5-5`, 2 and 10 for `claude-sonnet-5-5`, 0.10 and 0.50 for `claude-haiku-5-5`) the estimate for all three models is 140 to 235 dollars.

The three probe kinds (201 calls per model) are made first. Their recorded usage gives the output tokens per call, and the cost of the rest is projected from it and from the request lengths. If the projection for all three models exceeds 300 dollars, the run stops there and the user decides. The projection and the final spend go into the run folder.

## Order of work

1. Wait until run 11 has ended. No file under `src/` or `scripts/` changes before that.
2. Score run 11 at its recorded code state, as the parent plan's Task 14 says, before the code below is written. Run 11's reports therefore come from commit `942b8e8`.
3. Build the transport, the option and the comparison with tests first. Full reader tests, lint, writing rules. Commit. Record the commit.
4. Canaries with the key. Then the probe kinds, then the cost projection.
5. The remaining kinds for the three models, logs on the data root under `experiments/run12-simulated-readers-api/`.
6. Score run 12 and the comparison. Assemble `paper/data/run12-simulated-readers-api/` with a README that states it is a side run, the commit, the package version, the request fields, the defaults left in place, the spend, and every deviation.
7. The paper's section reports both runs as fixed above.

## What a null means

Agreement between the runs does not show that the readers are right about the archive. It shows only that the tool's added context is not what drives the result. Disagreement does not say which run is closer to real readers; the outcome labels say that, through each run's own accuracy.
