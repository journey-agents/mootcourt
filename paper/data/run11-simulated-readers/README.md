Run 11 (19 to 20 November 2026): the simulated readers. It is a side run on the exploratory split of the Upworthy Research Archive and not a successor of run 9. Run 9 (`paper/data/run9-visible-exposure/`) remains the current main run, and every table that is not about simulated readers still comes from it.

What it is. A panel of ten readers, each played by a language model, scores headline cards in matched feeds. The panel's score gives a direction for each contrast between a variant headline and the reference headline of its test, and that direction is checked against the recorded result. Seven methods then use earlier recorded results to adjust the panel. The design is `docs/superpowers/specs/2026-11-18-llm-simulated-readers-design.md`. The plan, its amendments and the record made before the first call are `docs/superpowers/plans/2026-11-18-simulated-readers.md`. The manual page is `docs/simulated-readers.md`.

The code. Every reply was requested and every report was written with `src/` and `scripts/` as they are at commit 942b8e85f565f5ac2387b9e32ff88d217bcdcc7f (`run-commit.txt`). The branch head when the run started was f512726, which adds only the written record to that commit. No file under `src/` or `scripts/` changed between the first call and the last report.

The inputs. The ledger and the saved scores of run 9, snapshot `20261106-2dc461f52ea4`, cell `headline_only`. `plan.json` holds the counts, the seed 20261118 and the SHA-256 of each file of the plan: 1,771 units, 1,770 tests, 5,966 contrasts, 63 blocks and 308 feeds. No file named holdout, confirmatory or undeployed was read.

The models. `claude-opus-5-5`, `claude-sonnet-5-5` and `claude-haiku-5-5`, one after another in that order. The vendor's page gave the training data cutoff "Jun 2026" for each on 19 November 2026. The archive's tests ran from 2013 to 2015 and were published years before that cutoff, so nothing is hidden from any of the three. Verdict words are written only for `claude-opus-5-5`, the model declared primary before the run.

The transport. Each call ran the command line tool `claude` at version 2.1.327 under a subscription login, from an empty temporary directory, with an environment that held only `HOME`, `LANG`, `LOGNAME`, `PATH`, `SHELL`, `TERM`, `TMPDIR` and `USER`. The flags were:

```
claude -p --model <id> --system-prompt <text> --tools "" --strict-mcp-config --mcp-config {"mcpServers":{}}
       --setting-sources "" --no-session-persistence --disable-slash-commands --output-format stream-json --verbose
```

The three canary files (`canary-<model>.json`) hold, for each model, the tool's start record on invented headlines: no tool and no server listed, the model asked for, and the version.

What the tool adds and the wrapper could not remove. Under a subscription login the tool puts its own context around the system prompt: one sentence that names the agent kit, an environment block with the working directory, the platform, the model's name and knowledge cutoff and the present date, a reminder about the account, and a token budget tag. None of it holds anything about the archive. A reader was therefore told that the present year is 2026 beside the instruction to play a person of 2013 to 2015. This is a limit of the run. Run 12 repeats the same requests through the vendor's API without that context (`docs/superpowers/plans/2026-11-19-simulated-readers-api-run.md`).

The calls (`run-log.txt`, UTC). The run began at 21:33:33 on 19 November 2026 and ended at 04:25:47 on 20 November. Each model ended with exit code 0 at its first start; no usage limit stopped the run and no transport failure was logged.

| model | calls planned | usable replies | invalid | refusals | recorded by the operator | requests that took a second or third attempt | SHA-256 of the transcript archive |
|---|---|---|---|---|---|---|---|
| `claude-opus-5-5` | 9,007 | 9,007 | 0 | 0 | 0 | 15 | `0f775cc7409c0d864adc50c94aa1f585bee7fae12a25e03ad7472545cd096afd` |
| `claude-sonnet-5-5` | 9,007 | 9,007 | 0 | 0 | 0 | 20 | `fd53a30656455c30c7ad200b720a74ef045b13fd65d3feeaf18212ad56b63f06` |
| `claude-haiku-5-5` | 9,007 | 9,007 | 0 | 0 | 0 | 59 | `9ce97e79cf488162d002154fc5c42adf3b561de9d15254b8af04bcc5a6208a0c` |

Every reply came from tool version 2.1.327 and reported the model asked for. An attempt after the first means the earlier reply did not have the form the prompt asks for; the stored reply is the first one that did. The archive checksum is the SHA-256 of the sorted list of each stored file's own SHA-256 and relative path (`shasum -a 256` over the files in byte order of their paths, then over that listing). The transcripts themselves are on the data root under `experiments/run11-simulated-readers/transcripts/` and are not in the repository.

The reports. `simulated-readers-<model>-20261106-2dc461f52ea4.json` for each model and `simulated-readers-agreement-20261106-2dc461f52ea4.json`, written by `scripts/simulated_readers.py score`. The stage reads stored replies and calls no model.

What the reports show, in words (the numbers are in the paper's generated tables, each with its key):

1. The plain panel of `claude-opus-5-5` is not shown to differ from the rule that always picks the earliest arm: the adjusted interval of the difference contains zero. The plain panels of the two smaller models are below that rule.
2. Fitted reader weights improve on the plain panel for each model. For `claude-opus-5-5` the adjusted interval lies above zero by a small margin.
3. Adding the panel's score to the text classifier of run 9 improves that classifier for `claude-opus-5-5` and not for the other two.
4. Among the seven methods the audience brief is the most accurate for each model. For `claude-opus-5-5` its interval against the earliest-arm rule lies above zero; for the other two that interval contains zero. These intervals belong to no declared family.
5. Two of the three probes for earlier exposure to the archive show no sign of it: a model completes a winning headline no better than another arm of the same test, and its familiarity ratings point to the winner about as often as a coin would. The third probe names the publisher and asks directly which headline of a pair won. Each model answers it right more often than a coin would, which a model can do by judging the headlines and which is therefore no evidence of exposure either way. The probes describe the risk and cannot rule it out.

Deviations from the plan, each recorded in the plan before the first call on the archive:

- The objective of the reader weights was changed to the mean binomial log likelihood per arm, because the planned objective left the weights equal whatever the readers answered.
- The flag that passes the reply's schema to the tool was dropped, because with it the tool loads a tool of its own. The prompt states the form of the reply and the wrapper checks it.
- Three expected counts of earlier visible units were corrected by one each; the plan's table had counted tests where it said units.
- The stop rule, the handling of a reply from another model, the rule for an origin without a usable audience note, and the shuffling of the completion probe were fixed after a review of the branch and before any call.

Nothing changed after a result was seen. No request was recorded as missing by the operator.

Other things a reader should know:

- The full test suite ran once before the review fixes (1,652 passed, 1 failed, and that failure was fixed). After the fixes only the tests of the readers, the writing rules and the documentation were rerun locally; the suite on the branch's continuous integration is the full check.
- One outcome figure of this cell was known when the design was written: the earliest-arm rule's accuracy of 0.570.
- The tool does not report token counts in a form the wrapper stored, so this run has no record of tokens used.

Added on 21 November 2026, after the results of this run were known. The three files named `simulated-readers-quarters-<model>-...json` hold, for each model, the three readings with the seven quarters as the units (a Student-t interval on the seven quarterly means, at 90 percent and at the level for a family of three) beside the reading with blocks resampled, and a block interval for the familiarity probe. They were computed from the stored replies of this run by `scripts/readers_extras.py quarters` at commit `f234784612b8ea8e832b5ff88a4b24ebdc275e08`, and no model was called. Their `blocks` entries repeat the estimates of the run's own reports, which are unchanged. The plan, written before these files existed, is `docs/superpowers/plans/2026-11-21-readers-quarters-and-open-model.md`. It records that two reviewers had already done rough arithmetic on the printed accuracies by quarter, so these readings fix a method after results and are reported as such.
