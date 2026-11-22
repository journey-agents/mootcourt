Run 13 (21 November 2026): the simulated readers of run 11 again with an open model, a direct judgment without readers, and a classifier on embeddings. It is a side run on the exploratory split of the Upworthy Research Archive and not a successor of run 9. Run 9 (`paper/data/run9-visible-exposure/`) remains the current main run.

Why it exists. Readers of a draft asked three things that runs 11 and 12 could not answer: whether a model from another maker, with weights that anyone can download, behaves like the hosted models; whether reader profiles and feeds add anything to asking a model directly which of two headlines more people would click; and whether the third reading of run 11 holds against a classifier stronger than the weighted word counts of the main run. The plan is `docs/superpowers/plans/2026-11-21-readers-quarters-and-open-model.md`. It was written on 21 November 2026, after the results of runs 11 and 12 were known and before any reply of the open model or any embedding existed. Everything here is therefore an analysis added after results. No entry of these reports carries a verdict word, and the open model is not the primary model.

The code. Every reply was requested and every report was written with `src/` and `scripts/` as they are at commit f234784612b8ea8e832b5ff88a4b24ebdc275e08 (`run-commit.txt`). The calls ran on the rented machine itself, from a clone of the public branch at that commit, because a forwarded connection from the operator's machine dropped under parallel load. The plan folder was copied to the machine and its file checksums were compared with `plan.json`. The reports were written afterwards on the operator's machine from the copied replies. One script outside the run, the builder of the anonymous version of the paper, was edited in the working tree while the calls ran; no file that makes a call or writes a report changed.

The inputs. The plan folder of run 11, file for file (`plan.json` here is a copy of run 11's): the same units, feeds, profiles, prompts and probes, 9,007 calls. As in run 12, the reader calls of the audience brief carry the note the model wrote in this run. No file named holdout, confirmatory or undeployed was read.

The model. `Qwen/Qwen3.8-27B` at revision 37561816e66b5b9153b1b64c10968c18c1e6f4a0 of the model hub, served under the name `qwen3.8-27b` at full precision (bfloat16) by vLLM 0.34.0 with torch 2.14.0 and transformers 5.22.2, on one H100 card of 80 GB. The server ran with a context of 32,768 tokens, at most 128 requests at once, and the reasoning parser for this family, which separates the model's thinking from its answer. The archive was public before this model was trained, so contamination is not excluded here either.

The transport. `src/mootcourt/simulators/readers/local.py` posts to the chat endpoint of the server. One request holds the model's name, the system text, one user message with the prompt, and a token limit of 16,000. No sampling setting is sent, so the server applies the defaults of the model's own generation file. A call was given 180 seconds and three attempts. Forty-eight calls ran at once.

The thinking setting, and one departure in how it was applied. The plan's rule: nothing sent and the default in force, unless a canary on invented headlines projects the whole run above 40 US dollars at the default, in which case every request runs at `reasoning_effort` medium. `cost-projection.txt` holds the measurement: at the default the run was projected at 65 to 118 dollars, so medium was used. The plan says every request carries the setting. This server does not read that field from a request, so the setting was given to the server once, as an argument of the chat template that applies to every request, and the requests themselves carry no setting. Each stored record says so (`chat-completions endpoint; no setting sent`). `effort-canary-default.json` and `effort-canary-medium.json` are the two canaries of twenty calls on five invented headlines; the second sent the setting as a request field, which the server ignored, so its token counts are not those of medium. The figures in `cost-projection.txt` come from a second measurement on a longer invented feed. The choice was made before any archive headline was sent to the model.

The calls (`run-log.txt`, UTC). The machine was started at 17:56:04 on 21 November 2026. The calls began at 18:45:00 and ended at 22:58:27, and the machine was terminated at 22:59:37. The canary (`canary-qwen3.8-27b.json`) holds the request as sent on invented headlines and what came back.

| kind | calls planned | usable replies | invalid | refusals | requests that took a second attempt |
|---|---|---|---|---|---|
| the plan of run 11 (seven kinds) | 9,007 | 9,007 | 0 | 0 | 3 |
| the direct judgment | 616 | 616 | 0 | 0 | 0 |

The first start of the reader stage ended with four calls of the audience brief without a stored reply. The stage was started again by the same script, as the code allows for a transport failure, and made those four calls. Every reply reported the model asked for. No contrast was left without a reader, and every contrast has a usable direct answer.

The SHA-256 of the transcript archive, computed as in run 11 over the 9,623 stored files, is `9d47a37187ffc1098c908446518065c925416b4d14b9d2a9f76ac4a03c19a27f`. The stored replies are released with the paper as `run13-stored-replies.tar.xz` (9,624 files with the canary, SHA-256 `752b8e4f9d574e518f8bc1292202570e59e6b0cecce985ed148ef58458902073`); the file is not in the repository, which accepts text files only.

Tokens and cost. The stored records hold 11,704,059 input tokens and 23,975,325 output tokens, the thinking included. That is about 2,490 output tokens a call, above the 1,596 of the measurement on invented headlines. The machine cost 4.39 dollars an hour and ran for about five hours, so the run cost about 22 dollars, the downloads and the embeddings included. The vendor's invoice was not read.

The embeddings. Each of the 8,769 distinct headlines of the source's admitted rows was embedded once by `Qwen/Qwen3-Embedding-8B` at revision 1d8ad4ca9b3dd8059ad90a75d4983776a23d44af, with no instruction text, at the full dimension of 4,096, and normalized to unit length, on the same machine before the calls began. The file of vectors is not in the repository. It is released beside the stored replies, in the data release tagged `paper-data-2026-11-21`, as `run13-headline-embeddings.npz`; its SHA-256 is `f79b7879e7293e1c97edca67c9e016f58e4d3cc019cb87c107f91e48d21d9c96`, and the report holds the same value.

The reports.

- `simulated-readers-qwen3.8-27b-run13-open-20261106-2dc461f52ea4.json` and `simulated-readers-agreement-run13-open-20261106-2dc461f52ea4.json`, written by `scripts/simulated_readers.py score --label run13-open --models qwen3.8-27b`. The first has the form of the reports of runs 11 and 12. Its entry `primary` is false and its readings hold no verdict.
- `simulated-readers-quarters-qwen3.8-27b-run13-open-20261106-2dc461f52ea4.json`, written by `scripts/readers_extras.py quarters`: the three readings with the seven quarters as the units, and the block interval of the familiarity probe.
- `simulated-readers-open-model-qwen3.8-27b-run13-open-20261106-2dc461f52ea4.json`, written by `scripts/readers_extras.py open-model`: the direct judgment and the embedding classifier, each comparison with a block interval at 90 percent, unadjusted, and with the quarters as the units. The entries under `embedding.with_panel` use the stored replies of runs 11 and 12 for the primary hosted model and of this run for the open model.

No stage that writes a report calls a model.

What the reports show, in words (the numbers are in the paper's generated tables, each with its key):

1. The open model's plain panel is below the earliest-arm rule, with blocks resampled and with the quarters as the units. In this it behaves like the two smaller hosted models and not like the primary one.
2. Asked directly, without profiles or feeds, the open model is right more often than its own plain panel with blocks resampled. With the quarters as the units the interval of that difference contains zero. The direct judgment is not shown to differ from the earliest-arm rule either way.
3. The classifier on embeddings is more accurate than the text classifier of the main run, with blocks resampled and with the quarters as the units. It is above the earliest-arm rule with blocks resampled, and with the quarters as the units that interval contains zero.
4. Adding the primary hosted model's panel to the embedding classifier raises its accuracy in both runs with blocks resampled. With the quarters as the units the interval is clear of zero in run 12, and in run 11 its lower end is inside the margin the paper applies. Adding the open model's panel is not shown to raise it.

Deviations from the plan. Three, none after a result was seen. One: the thinking setting was applied on the server and not in each request, as described above. Two: the plan names a canary of twenty reader calls on invented headlines as the measurement for the cost rule, and the projection that decided came from a second measurement, sixteen calls on a longer invented feed that is closer to the length of a real feed (`cost-projection.txt`). The projection from the named canary alone would have been lower. Both measurements read invented headlines only. Three: the plan runs the quarter reading of runs 11 and 12 before the machine is started, and those reports were written after it was started; they read stored replies of the earlier runs only.

Other things a reader should know:

- The open model was served once, and its replies are one draw. No second run of the same requests was made for it.
- The embedding classifier is one untuned model. Its regularization is the library's default.
- The direct judgment was run for the open model only, so it says nothing about the hosted models.
- The full test suite was not rerun on the operator's machine after the code of this run was added; the tests of the readers, of the scripts and of the writing rules were. The suite on the branch's continuous integration is the full check.
