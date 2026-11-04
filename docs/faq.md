# FAQ

## What it is for

**What does it do, in one sentence?** It reads the record of your concluded experiments, forecasts what that record implies about a proposed one, checks each forecast against what the live test later showed, and declines to rule when the record has nothing to say.

**Does it replace running the experiment?** No. The card helps you choose which tests to run and how large to make them, and the result of the live test is what counts. It never touches a ship, allocation or stopping rule, and a card never contains such a recommendation.

**Who is it for?** A team that has an archive of concluded A/B tests and plans the next ones: a data scientist who maintains the experiment program, or a product team that wants a second look at the plan before launching.

**What does a card say that my own judgment does not?** It says what happened in experiments that looked like this one, weighs them by how noisy each was, and gives a probability with an interval. It also says how well forecasts like it did in the past and how fragile this one is. It does not say why an effect occurred: precedent is not mechanism.

**What is a "cell"?** A group of alike experiments that share a base rate, by default one per metric. See the [glossary](concepts.md#glossary) for this and the other terms.

## What you need

**How many tests do I need?** A few dozen concluded experiments per metric make a first card and a first backtest possible. The gates in the backtest report give the number of scored experiments at which a Brier skill difference of 0.20 or 0.10 can be told from zero, at two power targets; with the default simulation they are of the order of 175 and 400 at the release gate. Below the gate, comparisons are reported as undecidable at this n, and cards still work.

**Do I need user-level data?** No. The ledger holds aggregates: for each experiment, variant and metric, the effect, its standard error, the units per arm and the dates. See [Ledger format](ledger-format.md).

**Do I need headline or other text?** No. Without it the models use the cell as the only feature, and the report says so. With it, the forecaster also weighs precedents by similarity.

**My platform is not in the list of importers.** Write a mapping file that points your columns at the exchange columns, or write the exchange format yourself; see [tutorial 2](tutorials/02-your-own-archive.md). The importers read files only. They call no vendor API and hold no credentials.

**What if my effects are in different units on different metrics?** Fine, as long as the rows of one cell share a unit. The importer refuses to mix units in a cell.

**Can I use it for non-experiment data?** No. The model assumes each row is a randomized comparison with a standard error.

## Reading the results

**Why does the card often abstain?** Because declining is the right answer when the ledger holds little support for the proposal, when the proposal is unlike every precedent, when the cell has no recent record or has drifted, or when the forecast is unstable under a small change in the precedents. The abstention rate is reported next to every score, so declining cannot hide in the numbers. See [troubleshooting](troubleshooting.md#a-card-abstains).

**Why is P2 sometimes no better than P1?** Weighing precedents helps only if similar tests had similar effects. When they did not, the admission guard sets the weight on precedents to zero for that cell and P2 equals P1. The guard only limits how much noise the selection fits on validation rows. It does not promise that P2 beats P1 on later tests, and P2 can score below P1 out of time: on the Upworthy archive it does, by a few thousandths of a nat of log score. The guard is weak at the size of the Upworthy cells: on a synthetic ledger of 3,700 tests it admits a weight in most cells with no planted text signal (those admissions are not false positives, because the ledger still has structure the precedents capture; method call 198), and the weights it admitted on Upworthy lost out of time (see the guard pairs on the results page). Treat an admitted weight as a hypothesis, not as evidence. The reports say how often the guard held the weight at zero, and the results page shows guarded and unguarded selection side by side.

**What is the difference between the two intervals on a card?** The interval for the true effect is what the team reads. The interval for the observed estimate adds the noise the test will have at its planned standard error, so it is wider, and it is the one a result is compared with and the one coverage is measured against. See the [card reference](reference/card.md).

**Why does my card need a row id?** The weekly join finds a card by the ledger row that holds its result. Give the card `--row-id source:test_id:variant_id` (or `--test-id` with `--variant-id`), `row_id` in `POST /card`, or `row_id` in the MCP tool, when you issue it. A card without a row id is valid, but no outcome can be attached to it. See [tutorial 4](tutorials/04-weekly-loop.md).

**The skill is near zero and the interval contains zero. Is it broken?** No. It means that the data cannot tell the forecaster from always predicting the base rate. On the Upworthy archive that is the result. On a synthetic sample it is expected. See [Results](results.md) and [Limitations](limitations.md).

**What does "undecidable at this n" mean?** The number of scored experiments is below the gate: whatever the point estimate of a skill difference is, that many experiments cannot establish it. It is not a negative result. The gate depends on how often your tests end significant and positive, so a backtest reads each cell's gate at the simulated base rate nearest the cell's own; `moot simulate gate-power` writes those gates.

**What is Brier skill?** One minus the forecaster's Brier score over the Brier score of a constant base rate. Zero is no better than the base rate, positive is better. Brier score is the mean squared error of the probability against the event (a significant positive result).

**Are the scores against the true effect?** No. A predictor is scored against the estimate a test produced, noise included, because the true effect is never observed. No predictor can reach a perfect score, and a small gain is hard to see.

**Does the published result mean it will work for my experiments?** No. The reference runs use two public archives, one of which is headline tests from a single publisher. Their numbers say nothing about another organization's tests, which is why `moot benchmark --ledger` runs the same protocol on yours.

**Why is the card issued "as of" a date?** Every card is made at an origin, and sees only rows that were usable by then. A static ledger such as the sample needs `--now` at the end of its history. A live ledger does not.

## Operating it

**How often do I run what?** Join weekly, refit nightly or after a join, back-test after a refit, promote after the back-test, issue cards whenever a test is proposed. See [Operations](operations.md) and [tutorial 4](tutorials/04-weekly-loop.md).

**Why does a new model not become the champion?** `moot promote` requires a Brier skill gain over the champion by a margin (0.02), and a backtest that rests on at least as many distinct experiments as the gate asks. With a small ledger the second condition usually fails, and the champion stays. That is the rule working.

**Can I edit a card after the result is known?** No. Cards are frozen under a digest of their content, and an outcome is a separate file written once. That is what makes the record usable.

**Does it run in a container or in CI?** There is a Dockerfile and a CI workflow in the repository; see [Release](release.md). The tutorials and the README quickstart run in a temporary folder in the test suite.

**How big a ledger can it take?** [Scale](scale.md) has the measured fit, backtest and card times up to a million contrasts.

## Safety and privacy

**Does anything leave my machine?** No. No default code path calls the network or a model. A response simulator is an outside program that you configure, and it receives aggregate inputs only. The download script is the one place that uses the network, and only when you run it.

**Is the service safe to expose?** Not as it is. It has no authentication and binds to the loopback address. Put your own access control in front of it before binding anything wider.

**Can I share my results without sharing my ledger?** Yes. `moot benchmark --ledger` writes a one-page report card of aggregates: counts, rates and scores with intervals, no row ids, no experiment names, no headlines. Check that your experiment count and base rate are not themselves confidential, and that the file name is one you are willing to show.

**Can I use my own agent for a second opinion?** Yes. See [Attach a simulation agent](simulators.md) and [tutorial 6](tutorials/06-simulation-agent.md). It starts with a weight of zero and earns a weight only by beating the model on later origins.

**An agent built on a language model may have seen the public archives.** Yes, and the package accounts for it: every record carries the agent's knowledge cutoff, origins before it are flagged as possibly contaminated, and the weight is earned on clean origins only. On the public archives, which end before any current model's cutoff, such an agent cannot earn a weight. Run it on tests of your own that are newer than its training data.

## About the project

**Where do the numbers in the README come from?** From the reports in the data root, written by the commands in [tutorial 3](tutorials/03-reproduce-upworthy.md) and rendered into the [Results](results.md) page by a script that also checks they are current.

**Which archives does it use?** The Upworthy Research Archive (Matias et al., Scientific Data 8, 195, 2021; CC BY 4.0) and the ASOS Digital Experiments Dataset (Liu, Cardoso, Couturier and McCoy, NeurIPS 2021 Datasets and Benchmarks; CC BY 4.0).

**How do I report a problem?** Send the output of `moot doctor` and the command you ran, with its output.
