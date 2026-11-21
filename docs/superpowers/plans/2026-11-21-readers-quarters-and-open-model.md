# Simulated readers: quarters as units, a familiarity interval, and a run with an open model

Written on 21 November 2026, before any result named below exists. It follows the review by four fresh readers of that
day. It adds to the designs of 18 and 19 November and changes nothing in runs 11 and 12: their reports stay as they are.

## What was already seen

This plan comes after the results of runs 11 and 12, so everything here is an analysis added after results, and the
paper must say so. Two reviewers also did arithmetic of their own on the printed accuracies by quarter of run 11, and we
read it: for the primary model, reader weights minus the plain panel had a mean near 0.012 over the seven quarters with
a Student-t interval near 0.001 to 0.023, and the plain panel minus the earliest-arm rule a mean near 0.007 with an
interval that contains zero. One reviewer put the standard error of the familiarity share near 0.016. None of these
numbers is in the paper. Part A therefore fixes a method, not an expectation. No reply of the open model exists and no
embedding of a headline exists as this is written.

## Part A: two computations from the stored replies (no model call)

**A1. The three readings with the seven quarters as the units.** For each model of runs 11 and 12 and each of the three
readings, take the per-contrast difference the reading already uses, average it within each of the seven origins, and
treat the seven means as the units: their mean, and a Student-t interval at 90 percent with six degrees of freedom. This
is the estimator of `scripts/by_origin_difference.py` (`origin_level`). Because the three readings are one family, the
report also holds the interval at the Bonferroni level for three. The report holds the seven values and the count of
leave-one-out intervals that stay above zero.

How it is read. A reading is clear of zero with the quarters as the units only if its interval at the level for three
excludes zero by more than the margin of 0.0010. The fixed words of the three readings do not change, because the design
fixed their rule before the first call. The paper prints the quarter reading beside each fixed word and says which of
the two it rests on. A null here means the reading is not shown to hold for a further quarter; with seven units the
interval is wide, and the paper says that as well.

**A2. An interval for the familiarity probe.** The share of probed contrasts on which the higher familiarity rating
points to the winner, minus one half, with a tie counted as one half: a 90 percent interval from 500 resamples of whole
blocks, the stream and rule of the other intervals. Six shares exist (three models, two runs) and no adjustment is
made; the paper says so. A share is read as above one half only if its lower end is above one half by more than 0.0010.
If any is, the paper says the probe points to the winner more often than chance for that model and that the probe
cannot separate recall from appeal. If none is, the paper says the share is not shown to differ from one half.

## Part B: a run with an open model (run 13, a side run)

**Model.** `Qwen/Qwen3.8-27B` at the revision the hub serves on the day of the run, recorded in the run folder. It is
the newest open instruction model of that family that fits one graphics card of 80 GB at full precision. It is served
by vLLM on one rented pod. The pod is started for the run and terminated when the run ends; the run log records both
times. The archive was public before this model was trained, as for the hosted models, so contamination is not excluded
here either.

**Requests.** The plan folder of run 11 is used unchanged: the same units, feeds, profiles, prompts and probes, 9,007
calls. A request holds the model, the system text, the prompt and a token limit of 16,000. No sampling setting is sent,
so the server applies the defaults of the model's own generation file. The rule for thinking is the rule of runs 11 and
12, nothing sent and the default in force, with one exception fixed here: a canary of twenty reader calls on invented
headlines measures the tokens per call, and if the projected cost of the whole run at the default is above 40 US
dollars, every request of the run carries `reasoning_effort` medium. The canary reads no archive headline and no
outcome, so the choice cannot depend on a result. The README states which setting was used. Three attempts per request
and the stop after five calls in a row without a usable reply are unchanged.

**Role.** The open model is not the primary model. Its report is written by the same code and carries no verdict word.
It is described as a fourth model from another maker, with weights that anyone can download.

**B1. A direct judgment without readers.** A new kind of call, `direct`, on all 5,966 contrasts: the two headlines of
a contrast, in a drawn order, and the question which of the two more people would click. No profile, no feed, no
publisher and no dates are named. Ten contrasts per call, formed within a block so that the block intervals apply; the
order within a block and the order of the two headlines come from a seeded stream. The model's answer for a contrast is
right when it picks the headline with the higher click rate. A contrast without a usable answer counts as one half, as
a contrast without a reader does.

Three comparisons are fixed now, each with a block interval at 90 percent, unadjusted, and the quarter reading of A1:

1. the direct judgment minus the open model's plain panel;
2. the direct judgment minus the earliest-arm rule;
3. the open model's plain panel minus the earliest-arm rule (already in its report).

How they are read. No verdict word. The paper applies its margin. If the interval of comparison 1 contains zero, the
paper says profiles and feeds are not shown to add to or take from what this model says when asked directly. If it lies
on one side, the paper says which, for this model only, and says the question stays open for the hosted models, which
were not asked. Comparison 2 above zero would be the first judgment by a model in this paper that is above the rule that
reads nothing; the paper would report it as a description from an analysis added after results, on tests the model may
have seen.

**B2. A stronger classifier for the third reading.** The third reading adds the panel to a classifier that is below
the earliest-arm rule. A second classifier is fitted the same way on embeddings. Each headline is embedded once by
`Qwen/Qwen3-Embedding-8B`, with no instruction text, at the full dimension, and normalized to unit length. At each
origin a logistic regression (C of 1.0, the library's default, not tuned) is fitted on the admitted rows of the source
that are visible at the origin. Its design is the difference of the two headlines' embeddings, the variant's embedding
and one column per cell, with an intercept. This mirrors the text classifier of the main run, with embeddings in place
of word counts. The version with the panel adds one column, the panel difference divided by ten, as method 5 does.

Comparisons fixed now, each with a block interval at 90 percent, unadjusted, and the quarter reading:

1. the embedding classifier minus the earliest-arm rule;
2. the embedding classifier minus the text classifier of the main run;
3. the embedding classifier with the panel minus without it, for three panels: the primary model in run 11, the primary
   model in run 12, and the open model in run 13.

How they are read. No verdict word. If comparison 1 contains zero or is below it, the paper says a stronger text model
is still not shown to beat the rule that reads nothing on these rows. If comparison 3 contains zero for a panel, the
paper says the gain of the third reading is not shown against a stronger classifier, and that the fixed word of the
third reading describes a weak classifier. If it is above zero, the paper says so with its size.

## Code and order of work

1. This plan is committed first.
2. Code with tests: a transport for a local endpoint that speaks the common chat format (`local`), the `direct` kind,
   the embedding classifier, the quarter reading and the familiarity interval, and a script that writes the new reports.
   New report files only; no existing report is rewritten.
3. The code state is committed and the commit is recorded in each run folder before any call. Nothing under `src/` or
   `scripts/` changes during the run.
4. Part A is run. Then the pod is started, the canary decides the thinking setting, the embeddings and the calls are
   made, and the pod is terminated.
5. Tables come from the report keys. The paper's text, the claims register and the limits follow. Whatever the numbers
   are, they are reported as they come out.

## Limits known now

Seven quarters give wide intervals. The open model is one model, served once; its replies are one draw. Its training
data may hold the archive. The embedding classifier is one untuned model, and a null from it does not show that no text
model can beat the earliest-arm rule. The direct judgment was run for the open model only.
