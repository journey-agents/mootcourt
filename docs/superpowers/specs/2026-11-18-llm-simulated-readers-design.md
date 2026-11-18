# Simulated readers: design

Written 18 November 2026, before any model call on archive headlines. Revised the same day after two reviewers read earlier drafts, after the user asked for alignment with earlier results and for a place in the paper's body, and after a survey of published methods. Status: for the user's approval. Nothing here is built.

## Why

The user wants the paper to answer one more question: if a large language model plays a human reader of the publisher's stories, how often does a panel of such readers point the same way as the real test? The user wants a number per model for three models, an honest statement of the limits, and a module in the package that others can run.

The user also wants the readers aligned with the results of earlier tests before they predict later ones, wants several ways of aligning compared, and wants this part to be one of the paper's main contributions, something later work can cite.

The paper already says that language-model outcomes match human effects only after calibration against human data, and that the package's optional language-model forecast enters at weight zero (related work). The reader panel is a different object from that forecast: it scores direction only, it is never blended into a card, and the weight stays at zero.

## What had been seen when this was written

Every number in the paper at commit `952e1b6`, the confirmatory run included. In particular the designer knows that always choosing the earliest arm is right more often than not, and the prompts and profiles are written with that knowledge; the paper will say so. No simulated reader has been run on any archive headline. No prompt, profile or feed has been tried on archive headlines. Two reviewers read earlier versions of this design and their criticisms are folded in.

## Goals

1. An opt-in module that plays a panel of simulated readers over story cards and returns, for each arm of each test, a panel score.
2. Seven ways of aligning that panel with earlier tests, each allowed to learn only from tests that the paper's visibility rule lets a forecast see at that origin.
3. One run on the exploratory split of the headline archive for each of three models, scored against the observed results on the paper's rows.
4. A section in the paper's body, with an appendix for detail, presented as a contribution: a time-ordered test of simulated readers, plain and aligned, with a fixed rule for what each alignment may see. The contribution is the test and its rule. It is stated the same way whether the numbers are high or low.

## Non-goals

- Images. The archive holds an image identifier and no image file. A simulated reader sees text only.
- A forecast under the paper's visibility rule. A model trained after 2015 has seen the period it is asked about. The result is never called a forecast made before launch, never enters the ladder or the challenger tables, and never changes a registered verdict.
- Any claim about the size of an effect, about calibration, or about tests outside this archive.
- The confirmatory split, the hold-out split and the undeployed file. They are not opened.

## Anti-goals

- A headline of the kind "simulated users predict experiments". The sentences the paper may use are fixed below, for every outcome, before any call.
- A result that depends on choices made after seeing scores.
- A model call in the default path, in the test suite or in CI.
- An abstract written after the number is known. The abstract gains one finding and the contribution list gains one item, and the wording of both is fixed below for every outcome.

## What the user decided

- The models are Claude Opus, Claude Sonnet and Claude Haiku, called through `claude -p`. All three are reported. The single vendor is named as a limitation.
- The command is wrapped by the module. A simulated reader is handed story cards and nothing else: no repository, no file, no tool, no result.
- The limits are stated whatever the numbers are.
- The simulation should be as close to a real reader as the archive allows.
- The readers are aligned with earlier results, and all seven alignment methods below are run, including the two that need further model calls.
- This part is a main contribution in the paper's body. Both reviewers advised an appendix, because the model's training may hold these headlines and no fresh split can confirm the result; the user decided otherwise, and the paper states those two limits next to the result.

Everything else in this document is the designer's call, and the user can change any of it before approval.

## Design

### A reader sees one arm, in a feed

In the real test a visitor saw one package and clicked or did not. So a simulated reader never sees two arms of one test. One model call plays one reader scrolling one feed of up to 30 story cards. Each card comes from a different test and shows one arm. For each card the reader returns a probability from 0 to 100 that they would click it.

A probability and not a yes or no, because a vote of ten or twenty readers per arm is too coarse and would produce many ties.

### What a card shows

The headline and nothing else. The paper models the headline and the image only, and its text classifier reads headlines only, so a headline-only card keeps the comparison like for like. The excerpt is left out: the ledger keeps it for the variant and not for the reference arm, and it can differ between arms within the headline-only cell, which would mark the arm. The card carries no test identifier, no arm label, no date and no count.

### Rows and arms

The rows are the paper's scored rows in the headline-only cell of the main run: 1,770 tests and 5,966 contrasts (`paper/data/run9-visible-exposure`). Every test of the cell is run; there is no sample. For each test the arms shown are the reference arm (the earliest created, as the loader defines it) and every arm that takes part in a scored headline-only contrast. Arms of the same test whose contrast is in another cell are not shown. The cell where headline and image both change, and the image-only cell, are left out.

The plan must locate the row-level inputs before anything is fixed further: the headlines of each arm and the row-level values of each baseline named below, for exactly the rows scored in run 9. If a baseline's row-level values are not saved, the plan says how they are regenerated from run 9's code state without touching `src/`, or drops that comparison and says so.

### Blocks and matched feeds

The comparison between two arms of a test must not be mixed with the feed around them.

- Blocks are formed within a scored origin, so that every test of a block may be aligned on the same earlier tests. Within an origin, tests are sorted by their number of shown arms, in random order within a count, and cut into blocks of 30. The last block of an origin may hold fewer than 30.
- A block has as many feeds as its largest test has arms. Every feed of a block holds the same stories in the same positions. Only the arm shown for each story changes from feed to feed.
- A test's arms are placed in the block's feeds in a random order. A test with fewer arms than the block has feeds repeats its arms in a further random order until every feed is filled. An arm's score averages its repeats.
- The order of positions is random per block and fixed across that block's feeds.

Matching removes position and story as sources of bias. It does not make the 29 neighbours identical, since they are other arms of the same stories. That remainder is noise shared by the whole panel, and two steps address it. First, each call's probabilities are centred on that call's own mean before any averaging, which removes a call's overall level. Second, the interval that governs the wording resamples whole blocks.

Each model call is a fresh process with no memory of any other call. The same reader profile therefore reads every feed of a block without knowing that another arm exists.

### The panel

Ten reader profiles read every feed. A profile is a short paragraph: an age band, a few interests, a mood, phone or desktop, and where they met the story. The period is given once, in the system prompt, as "between 2013 and 2015", and the publisher is not named; no profile names a year, because a feed mixes tests of different quarters. The archive holds no audience data, so the profiles are assumed. They are written once, before any call, and the paper says that their spread is variation between prompts and not sampling from the real audience.

Whether ten readers are enough is measured and not assumed: the panel is split into two halves of five by profile number, and the share of contrasts on which the halves agree in direction is reported per model. That measure reads no outcome.

### Panel score, direction, ties and missing replies

For an arm, the panel score is the mean over readers of the centred probability, averaged over the arm's repeats. For a contrast, the predicted direction is the sign of the variant's score minus the reference's.

- A difference of exactly zero is a tie. A tie counts as half right, and ties are counted.
- A reply that fails the schema is retried twice with the same input, then recorded as missing. A refusal is recorded as missing.
- A reader with any missing feed in a block is dropped from that whole block, so every arm of a test is averaged over the same readers.
- A contrast left with no reader counts as a tie and is counted separately.

No size is reported. The panel difference is used as a direction and as a ranking score only.

### Aligning the readers with earlier results

Published work finds that raw simulated effects are attenuated or biased and need calibration against human outcomes (see "Prior work"). Seven alignment methods are run. Each is refitted at every scored origin, on the headline-only tests that the paper's visibility rule lets a forecast see at that origin and for which panel answers exist, which are the scored tests of earlier origins past their assigned end. At the first scored origin no such test exists, so every aligned panel equals the plain panel there, and the paper says so. The plan counts the tests available at each origin before anything else is fixed.

No prompt, profile or setting is tuned by hand on any outcome. Every tuning constant below is given an exact value in the plan.

Five methods use the stored answers of the plain panel and need no further call:

1. Direction map. A logistic regression of the observed direction on the panel difference, fitted on earlier contrasts. It turns the panel into a probability that the variant beats the reference, which is scored with the Brier score against the earlier share of contrasts won by the variant.
2. Reader weights. The click count of an arm is binomial in its impressions, with a click probability that is a logistic function of a weighted mean of the ten readers' answers. The weights lie on the simplex and are shrunk toward equal weights; an intercept and a positive slope are fitted with them.
3. Audience matching. The weights are chosen only so that the weighted panel's mean click level matches the mean click rate of earlier arms, with no use of which arm won. This is the reweighting that survey practice uses, and published audits find it weak; it is run as the comparison for method 2.
4. Error correction. A monotone map from panel score to click rate, fitted on earlier arms, followed by a linear correction of the remaining error on four fixed traits of a headline: its length in words, a question mark, a digit, and the word "you".
5. Panel plus history. The panel difference enters the paper's text classifier as one more feature, refitted at each origin as that classifier is. The comparison is with the same classifier without the feature.

Two methods put earlier results in front of the reader and need new calls, on feeds built exactly as the plain panel's:

6. Past results in the prompt. Before the feed, the reader is shown ten earlier tests drawn with a seed from the tests visible at that origin, each as its headlines with their observed click rates.
7. Audience brief. At each origin the same model is given a seeded draw of 200 visible earlier tests with their click rates and writes a note of at most 150 words on what this audience clicked. Every reader at that origin receives the note. The notes are stored with the transcripts.

Published results on this archive found that examples in the prompt changed little, so methods 6 and 7 are expected to be the weakest. They are run because the user asked for the full comparison, and they are reported whatever they show.

### Reference outcome and baselines

The outcome is the paper's: the sign of the observed effect on all rows, and separately on decisive rows, where the absolute effect exceeds 1.96 standard errors. The paper's printed baseline accuracy, ceiling and ranking figures are pooled over cells, so none of them is reused. Each is recomputed on these rows:

- the rule that always picks the earliest arm (`always_reference`)
- the text classifier (`text_lr`)
- the direction ceiling
- for ranking, the arm-count rule and the random order matched on arm count, with the top quarter taken within each origin as the paper does

### Measures

Primary, for Claude Opus, three readings fixed now, each a paired difference in direction accuracy on all 5,966 contrasts:

1. The plain panel minus the earliest-arm rule.
2. The panel with reader weights (method 2) minus the plain panel. This asks whether alignment helps.
3. The text classifier with the panel feature (method 5) minus the text classifier without it. This asks whether simulated readers add anything to what past tests already give.

Each carries a 90 percent bootstrap interval from 500 resamples of whole blocks, with Bonferroni-adjusted bounds for a family of three, computed as the paper computes them. The adjusted interval governs the wording. An interval that resamples tests is printed beside it.

Described, with no verdict word:

- The same three readings for Sonnet and Haiku.
- Every alignment method against the plain panel and against the earliest-arm rule, in one table, for each model.
- The plain panel's direction accuracy minus one half.
- Direction accuracy on decisive rows.
- For method 1, the Brier skill of the direction probability.
- The text classifier's paired difference from the earliest-arm rule on the same rows, which the paper does not print today.
- Ranking: captured positive lift at a quarter budget, a test's score being the largest panel difference among its contrasts, minus the arm-count rule's and minus the matched random order's.
- Agreement between the three models on direction, the split-half agreement, and the counts of ties and missing replies.

What this can detect, from rough arithmetic and not from data: a paired difference in accuracy of about 0.03 or more. A smaller one will read as not shown. The ranking comparison rests on fewer tests than the paper's and is descriptive. Published accuracy on this archive is modest, so a null on all three readings is a likely outcome and is reported as prominently as a positive one.

### Wording the result may take

Fixed now for Opus, read from the three adjusted intervals. Each reading has three sentences, for an interval above zero, containing zero, and below zero:

- Reading 1: the plain panel "matched the observed direction more often than always choosing the earliest arm", "is not shown to match it more often than", or "matched it less often than".
- Reading 2: aligning the readers with earlier results "raised", "is not shown to raise", or "lowered" that share.
- Reading 3: adding the simulated readers to a classifier fitted on earlier tests "raised", "is not shown to raise", or "lowered" its share of directions matched.

Every such statement opens with "On the headline-only tests of the exploratory split, with nothing hidden from the model's training and contamination not excluded,". The abstract's new finding is those three statements in one or two sentences, and the new contribution item reads: "A time-ordered test of simulated readers, plain and aligned with earlier tests by seven methods, under a fixed rule for what an alignment may see." The paper never says that one model confirms another: the three share a vendor and, most likely, training data.

### Recall probes

A model may have met these headlines on the web. If the publisher ran the winning package afterwards, the winner is also the arm most likely to be found there, so a reader that prefers familiar headlines could score direction through memory. Three probes describe that channel. Each runs on a fixed random set of 300 headline-only tests drawn with a seed before any call, in calls separate from the panel.

1. Completion. For each test, two arms are probed: the arm with the highest observed click rate and one other arm chosen at random. The model is given the first four words of the headline and asked for the rest, as an earlier study of this archive did. The measure is the mean token F1 of the completion, for winning arms and for the others, and their paired difference.
2. Familiarity. The model rates each shown arm of the 300 tests from 0 to 100 for how sure it is that it has seen this exact headline. The measures are the direction accuracy of the rule "pick the arm with the higher rating" on those tests' contrasts, and the share of contrasts on which that rule and the panel agree.
3. Named source, both arms shown. The model is told the publisher and the period, shown the reference and the variant of one contrast in random order, and asked which had the higher click rate. It is scored as direction accuracy on those contrasts.

The probes describe contamination. They do not bound it or exclude it, and the paper says so. Probe 3 appears in the probe table and nowhere else, and is never called a simulated reader.

### How the model is called

One wrapper function builds the command. Requirements:

- The working directory is a new empty temporary directory outside the repository and outside the data root.
- Built-in tools are off, no MCP server is loaded, no settings source is read, no session is saved, and the system prompt is replaced by the module's own.
- The model is named by its full identifier: `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`. The plan records each model's published knowledge cutoff, as the existing simulator package requires of a provider.
- The prompt goes in on standard input and the reply is one JSON object checked against a schema: one probability per card position.
- Every request and reply is written to a transcript on the data root, keyed by a hash of the request, with the model identifier and tool version the tool reports. A rerun reads the stored reply, and scoring never calls a model.
- Tests inspect the built command. They cannot show what the tool sends, so before the run one canary call on a synthetic feed stores the tool's own start record (tools, servers, version), and the README of the run folder quotes it.
- The tool version is recorded at the start. If it changes during the run, the run continues, and the report gives the count of replies per version.

The tool gives no control of temperature and may add context of its own, such as the current date. The paper says so. The exact flags, and which login variables must pass the existing environment scrub, are for the builder to settle on synthetic headlines only.

### Where the code goes

- A new subpackage `mootcourt.simulators.readers`: profiles, cards, blocks and feeds, the command wrapper, transcripts, and the panel score. The existing simulator interface takes two headlines and returns one probability of a win, so it does not fit; the subpackage reuses only that package's environment scrub, its refusal of commands inside the data root, its process-group kill and its cache.
- A script `scripts/simulated_readers.py` with three stages. `plan` writes the blocks, feeds and probe sets from the row inputs and a seed, prints the exact number of calls, and calls no model. `run --model NAME` makes the calls. `score` reads transcripts and writes one report per model.
- `run` refuses to start without an explicit flag that allows model calls, and the test suite never passes it.
- Tests use a fake command that returns fixed probabilities. A synthetic ledger with a planted text effect checks that the scoring recovers a known direction.

### The run

The run-experiments order applies. The plan that follows this design is committed first. The module is built with tests, the suite is green, the code is committed, and that commit is recorded in the run folder. Then `plan`, the canary, the three `run` stages, the probes, then `score`. `src/` and `scripts/` do not change during the run. Any trial of prompts uses synthetic headlines only. Nothing is scored until every planned call is stored or recorded as missing.

The run folder is `paper/data/run11-simulated-readers`. Its README says that it is a side run and that run 9 remains the current main run, since the repository's convention is that the highest number is current. Transcripts stay on the data root with their checksums in the README.

### Cost and risk to the account

The plain panel needs close to 3,000 calls per model. Methods 6 and 7 each repeat the panel at every origin but the first, close to 2,700 calls each, and the probes add roughly 1,500. That is about 10,000 calls per model and on the order of 30,000 in all on the user's subscription. The `plan` stage prints the exact count before any call. Rate limits may stretch the run over a week or more; it resumes from the transcripts. That many automated calls on a personal subscription may run against its terms or limits. That is the user's decision to take, and the paper states how the calls were made.

### In the paper

- A new section in the body, "Simulated readers and their alignment with earlier tests", holding the design in brief, one table of the three primary readings for the three models, one table of the seven methods, and the limits. An appendix holds the prompts, the profiles, the probes and the remaining measures.
- A fifth item in the list of contributions and one finding in the abstract, both in the wording fixed above.
- Related work gains the published methods named under "Prior work", and keeps the sentence that the package's optional forecast stays at weight zero, with: "The simulated readers of Section N are scored on direction only and are not that forecast."
- One paragraph in limitations: assumed profiles written with the paper's results known, one vendor, no temperature control, contamination described and not excluded, no fresh split to confirm the result, and a hosted model that will be retired, so the result can be rescored from the transcripts and cannot be regenerated.
- One item in the appendix on which readings were fixed before their results: this analysis was added after every other result was known, with its design fixed before its own result.
- The conclusion gains the same three statements. No other finding of the paper changes.
- Tables come from report keys through `paper/build_tables.py`; each number in prose has a source line; each claim has a row in the claims register.

## Prior work, and what may be claimed as new

A survey of 26 web queries on 18 November 2026 found these as the nearest work. It is not a systematic review.

- A study already cited in the paper predicts click rates of this archive's headlines with one prompt and no reader profiles, calibrates the predictions against human click rates, finds raw effects attenuated, and uses a split by date only as a diagnostic on one kind of contrast.
- A second study of this archive compares prompting, examples in the prompt, embeddings with a regression, and fine-tuning, on a random split by test.
- Published families of alignment: calibration and rectification against a human sample; weights over profiles fitted to aggregate outcomes; examples or histories in the prompt; fine-tuning on behavioural data; optimisation of prompts; and the simulator as a feature or prior in a statistical model.

The paper may say "to our knowledge" and no more, and only for these three points: a panel of reader profiles aligned on earlier headline tests and scored on strictly later ones as the main design; the alignment families compared in one time-ordered replay; and the comparison with the rule that always picks the earliest arm. One journal article on weights over prompts and profiles fitted to aggregate benchmarks could not be opened during the survey. It must be read before any of the three points is written.

Every work cited in the paper for this section is opened and checked against its source before its entry is added to the bibliography. Works the survey listed as recalled or not opened are not cited until that is done.

## Fixed before the first call

The plan that follows this design writes each of these as an exact value, and the commit that holds it is the record:

- The seed, and the blocks, feeds and probe sets that `plan` writes from it, with their checksums.
- The cell, the rows, the arms shown and the headline-only card.
- The system prompt, the reader prompt, the ten profiles and the output schema, word for word.
- Block size 30, the repeat rule, centring per call, ten readers, the split into halves, the retry rule, the tie rule and the two rules for missing replies.
- The three model identifiers with their cutoffs, Opus as the primary model, and the tool version at the start.
- The three primary readings, the family of three, the block bootstrap with 500 resamples and its seed, the described measures, the baselines recomputed on the cell, and the wording for each outcome.
- The seven alignment methods: the tests each may learn from at each origin, every tuning constant, the four headline traits, the ten examples and the 200-test draw with their seeds, and the prompt that asks for the audience brief.
- The three probes, their prompts and their measures.
- The sentences for the abstract, the contribution list and the conclusion, for every outcome.

## Left to the builder

- The exact command flags and the login variables, verified on synthetic headlines.
- How many calls run at once.
- The layout of transcript files and the names of report keys, following the existing simulator runner's records.

## Open risks

- The subscription's limits and terms, as above.
- The tool may change its hidden behaviour between calls; the stored identifier and version per reply are the only guard.
- A null result is as hard to read as a positive one, because assumed profiles and the feed format could each explain it. The paper says that as well.
- The result is one measurement that cannot be regenerated, with contamination undetermined, placed in the paper's body by the user's decision against two reviewers' advice.
