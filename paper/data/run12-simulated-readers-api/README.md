Run 12 (20 November 2026): the simulated readers of run 11 again, through the vendor's API. It is a side run on the exploratory split of the Upworthy Research Archive and not a successor of run 9. Run 9 (`paper/data/run9-visible-exposure/`) remains the current main run.

Why it exists. Run 11 (`paper/data/run11-simulated-readers/`) reached the models through a command line tool that puts its own context around every call, the present date included. Run 12 sends the same requests through the vendor's Messages API, where a model receives the system prompt and the reader's prompt and nothing else. It answers one question: do the results of run 11 depend on the context the tool adds? The plan is `docs/superpowers/plans/2026-11-19-simulated-readers-api-run.md`. It was written on 19 November 2026, before any reply of run 11 had been scored or read and before any call of run 12, and it fixes how the comparison is read.

The code. Every reply was requested and every report was written with `src/` and `scripts/` as they are at commit 87163a63ec24ae5e7699ddb4697aea8eb1a0e52a (`run-commit.txt`). That commit adds the second transport, the `--label` option and the `compare` stage to the code state of run 11, which had been scored before any of it was written. No file under `src/` or `scripts/` changed between the first call and the last report.

The inputs. The plan folder of run 11, file for file (`plan.json` here is a copy of run 11's). The planned calls are therefore those of run 11, 9,007 per model, with the same model names, system prompts and prompts. One kind differs in text: a reader call of the audience brief (method 7) carries the note the model wrote in the same run, so those 2,860 prompts and their request hashes are this run's own. Every other request is identical to run 11's. No file named holdout, confirmatory or undeployed was read.

The models. `claude-opus-5-5`, `claude-sonnet-5-5` and `claude-haiku-5-5`, one after another in that order. Verdict words in the paper come from run 11 and only for `claude-opus-5-5`. The reports of this run hold verdict keys for that model too, because the same code wrote them; the paper prints this run's intervals beside run 11's and takes no verdict word from them.

The transport. The vendor's Python package, `anthropic` at version 2.11.0, `messages.create`. One request holds four fields and no other:

```
model       the model's full identifier
system      the system prompt of the reader or of the probe
messages    one user message that holds the prompt
max_tokens  16000
```

No tool is declared. No sampling setting is sent, because these models reject a temperature other than the default. Thinking and effort are left at each model's default; the vendor documents the default effort as medium for `claude-opus-5-5` and `claude-haiku-5-5` and as high for `claude-sonnet-5-5`. No fallback model is named. The package retried a rate limit, a server error, a timeout or a dropped connection up to five times, and a call was given 180 seconds. Four calls ran at once. The key was read by the package from an environment variable and is in no file of the repository or of the transcripts.

The three canary files (`canary-<model>.json`) hold, for each model, the request body as sent on invented headlines and what came back: the model asked for, no tool call, the stop reason and the token counts.

The calls (`run-log.txt`, UTC). The canaries and the three probe kinds began at 04:55 on 20 November 2026. The remaining calls began at about 05:05 and the last model ended at 08:17:56. Each stage ended with exit code 0 at its first start, and no transport failure was logged.

| model | calls planned | usable replies | invalid | refusals | recorded by the operator | requests that took a second or third attempt | SHA-256 of the transcript archive |
|---|---|---|---|---|---|---|---|
| `claude-opus-5-5` | 9,007 | 9,007 | 0 | 0 | 0 | 23 | `16388af7895ad7d18b7187b5b72267bfd798cb8e4f5cb1ee1e460d6eaa8ddf8d` |
| `claude-sonnet-5-5` | 9,007 | 9,007 | 0 | 0 | 0 | 18 | `4d334df9b5e19b876f0d3920e751d256d8a9a5030d9c13938387039ece60bb8a` |
| `claude-haiku-5-5` | 9,007 | 9,003 | 4 | 0 | 0 | 100 | `0d0c0241804917c0667cce11e57156c4edccf8a7b351d5b5e7068b006c735b85` |

Every reply reported the model asked for. The four invalid replies of `claude-haiku-5-5` are feeds of the audience brief (method 7) whose reply gave the wrong number of probabilities at each of three attempts. By the rule fixed before run 11, a reader with a missing feed in a block is dropped from that block. No contrast was left without a reader. The archive checksum is computed as in run 11. The transcripts are on the data root under `experiments/run12-simulated-readers-api/transcripts/` and are not in the repository.

Tokens and cost. Each stored record holds the token counts the API reported, summed over that request's attempts. At the vendor's list prices on 19 November 2026 (dollars per million tokens, input and output: 4 and 20, 2 and 10, 0.10 and 0.50):

| model | input tokens | output tokens | cost at list prices, dollars |
|---|---|---|---|
| `claude-opus-5-5` | 17,558,623 | 870,723 | 87.65 |
| `claude-sonnet-5-5` | 17,544,292 | 672,012 | 41.81 |
| `claude-haiku-5-5` | 17,507,775 | 1,846,640 | 2.67 |

The total is 132.13 dollars. `cost-projection.txt` is the projection of 120 to 170 dollars made after the probe calls and before the rest, under the plan's ceiling of 300 dollars. These figures are computed from the recorded counts; the vendor's invoice was not read. The three canary calls are not in them.

The reports. `simulated-readers-<model>-run12-api-20261106-2dc461f52ea4.json` for each model and `simulated-readers-agreement-run12-api-20261106-2dc461f52ea4.json`, written by `scripts/simulated_readers.py score --label run12-api`. `simulated-readers-transport-<model>-20261106-2dc461f52ea4.json` for each model, written by the `compare` stage from the stored replies of both runs. Neither stage calls a model.

What the reports show, in words (the numbers are in the paper's generated tables, each with its key):

1. For `claude-opus-5-5` the plain panel's accuracy is the same in the two runs to four decimals, and the interval of the difference contains zero. By the rule fixed in the plan, the context the tool adds did not move the plain panel's accuracy by an amount this design can detect. The same interval contains zero for the two smaller models.
2. The two plain panels of one model do not give the same direction on every contrast: they agree on about 85 percent of contrasts for `claude-opus-5-5` and on fewer for the smaller models. Replies vary from call to call, and no sampling setting can be fixed, so this run cannot separate that variation from the effect of the added context.
3. Reading 1 (the plain panel against the earliest-arm rule) and reading 3 (the text classifier with and without the panel) fall on the same side of zero in both runs for `claude-opus-5-5`.
4. Reading 2 (reader weights against the plain panel) does not: its adjusted interval lies above zero in run 11 by a small margin and contains zero here. The verdict word of run 11 stands, as the plan fixed, and the paper says beside it that the second run does not repeat it.
5. The audience brief is the most accurate of the seven methods for `claude-opus-5-5` and `claude-sonnet-5-5` in both runs. For `claude-haiku-5-5` it is not in this run. The notes of the brief are written by the model afresh in each run, so this method differs between runs by more than the transport.

Deviations from the plan: none. Nothing changed after a result was seen.

Other things a reader should know:

- The tests of the new transport were written before its code, and the code was written before those tests were first run, so they were never seen to fail.
- The full test suite was not rerun on the operator's machine after the transport was added; the tests of the readers, of the script and of the writing rules were. The suite on the branch's continuous integration is the full check.
- A hosted model is retired in time. The reports can be rebuilt from the transcripts, and the replies cannot be requested again once the models are gone.
