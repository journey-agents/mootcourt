# Simulated readers

This page describes an opt-in module that asks a language model to play a panel of ten readers, shows them story
headlines, and scores how often the panel picks the headline that won the real test. It is a side study of the paper.
It is not part of the forecast, the card or the default path, and nothing here runs unless you pass a flag that allows
model calls.

## What it does

A test in the archive compared a reference headline with one or more variant headlines for the same story. The module
takes the tests in which only the headline changed and builds feeds: numbered lists of headlines, one headline per
story. Each of ten fixed reader profiles reads each feed and gives, for every headline, the probability from 0 to 100
that this reader would click on it. The two headlines of a test are never in the same feed. They are read in matched
feeds that hold the same stories in the same positions, so the surroundings are equal.

The panel score of a headline is the mean, over the readers, of the reader's probability minus the mean of that
reader's whole reply. The panel's direction for a contrast is the sign of the variant's score minus the reference's.
An exact tie counts as half. A reader sees a headline and nothing else: no click rate, no identifier, no image and no
name of the site.

## Aligning the panel with earlier tests

Seven methods use the results of earlier tests. Each one is refitted at every scoring date and may use only tests whose
results were in hand by that date, the same rule the paper's forecasts follow. At the first scoring date no earlier
result exists, so every aligned panel equals the plain panel there.

1. Direction map: a logistic regression of the observed direction on the panel difference.
2. Reader weights: weights over the ten readers, fitted to the click counts of earlier headlines.
3. Audience matching: weights chosen only so that the panel's mean click level matches the earlier mean click rate.
4. Error correction: a curve from panel score to click rate, then a correction on four traits of a headline.
5. Panel plus history: the panel difference as one more feature of the text classifier.
6. Past results in the prompt: ten earlier tests with their click rates are shown before the feed.
7. Audience brief: the model first writes a note of at most 150 words from 200 earlier tests, and every reader gets it.

Methods 1 to 5 reuse the stored answers of the plain panel. Methods 6 and 7 need new calls.

## The three stages

```bash
# 1. Fix the units, feeds and probe set, and count the calls. No model is called.
uv run python scripts/simulated_readers.py plan --ledger LEDGER.parquet --scores SCORES.parquet --out PLAN_DIR

# 2. Make the calls of one model. Stored replies are never asked for again, so this can be started again at any time.
uv run python scripts/simulated_readers.py run --model claude-opus-5-5 --plan PLAN_DIR --transcripts T_DIR --allow-model-calls

# 3. Write the reports from the stored replies. No model is called.
uv run python scripts/simulated_readers.py score --plan PLAN_DIR --transcripts T_DIR --ledger LEDGER.parquet --out OUT_DIR --commit HASH
```

`run` exits with code 2 unless `--allow-model-calls` is given. It exits with code 3 after five calls in a row end
without a usable reply, for example when a usage limit is reached; start it again later and it continues. Nothing from
such a streak is stored, so a limit message is never recorded as a refusal. `score` exits with code 5 while
any planned call of any of the three models is not stored, so no partial result can be read. The stage `canary` makes
one call on five invented headlines and stores the tool's own start record; it exits with code 4 if that record lists
any tool or any server, if the reply cannot be read, or if the tool does not report its model and version.

The model is reached through the `claude` command line tool, started in an empty directory with no tools, no servers,
no settings and no stored session, and with an environment that holds a short list of allowed names. The tool adds some context of its own that cannot be switched off under a subscription login: an environment
block with the working directory, the platform, the model's name and today's date, and a reminder about the account.
None of it concerns the archive. Each reply is checked whole against a schema: the right count of numbers, each from
0 to 100. A reply that fails is asked for twice more and then recorded as missing. Nothing is clipped or filled in.

## What the result may be called

The tests are public and older than the models, so a model may have seen them during training. Three probes describe
that risk on 300 tests: completing a headline from its first four words, rating how familiar a headline is, and the
direct question of which headline won. The probes describe the risk and cannot rule it out. A result from this module
is therefore a statement about these models on this archive with contamination not excluded. It is not evidence that
simulated readers forecast tests that the model has not seen.

The reports give three readings that were fixed before any call: the plain panel against always choosing the earliest
headline, the weighted panel against the plain panel, and the text classifier with the panel against the text
classifier alone. Only the primary model's readings carry a verdict word.

The design, with every decision and its reason, is in `docs/superpowers/specs/2026-11-18-llm-simulated-readers-design.md`
in the repository, and the exact values are in `docs/superpowers/plans/2026-11-18-simulated-readers.md`.
