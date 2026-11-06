# X10: does the predicted distribution improve test size choice? Design note

Written 6 November 2026 by the run 8 builder, before any sizing number exists. For the lead's review. Nothing in this note runs until the lead replies.

## Question and why a replay cannot answer it

A launching team chooses how many impressions to give a test. A concluded archive test ran once, at one size, so its size cannot be changed after the fact. Two things can still be measured honestly on the exploratory split: whether the forecast probability of a significant result at the size a test actually had matches the rate that followed (part A), and whether sizes computed from the out-of-time prior would have cost less than sizes from two simpler rules, in a simulation whose world is not the prior (part B). If part B cannot be made fair (the two feasibility failures below), the paper says sizing is not evaluated.

Units: effects in percentage points of click-through rate, divided by 100 where a probability is needed; sizes are impressions per arm; value is extra clicks over always showing the reference.

## Part A: out-of-time assurance by exposure

For rungs P0, P1, P2 and the text classifier, over the scored rows of the main run (every forecast is out of time by construction), five equal-mass bins of the row's planned exposure, pooled and within each cell. Per bin: rows, tests, mean exposure, mean forecast probability of the significant-positive event, realized rate, the difference with a 90 percent by-test interval. One pooled number per rung: the slope of (realized minus forecast) on standardized log exposure, with a by-test interval. The planned exposure of an archive row is its realized impressions, a stand-in; the note in the key says so, and X3 reports what fixing it does. Part A uses only stored score tables. It is cheap and can run on the data now.

## Part B: test-and-roll sizes against a world that is not the prior

**Decision problem (Feige and McDowell).** A page has N impressions in all. A test gives n impressions to each of the variant and the reference, the arm with the higher observed rate is shown to the remaining N minus 2n. With theta the true difference in rate (variant minus reference), the expected gain over always showing the reference is `n theta + (N - 2n) theta P(theta_hat > 0)`, where `theta_hat` has standard error `s_n = sqrt(2 c (1 - c) / n)` and c is the reference rate. The oracle gain is `N max(theta, 0)`. Regret is oracle gain minus expected gain. For a normal prior with mean zero this reduces to the closed form of the paper, and a test checks the numerical optimizer against it.

**Audience.** The archive does not record how many impressions a page went on to receive. N is therefore a multiple of the test's own scale: `N = m * 2 * (median planned exposure per arm of the cell's visible rows)`. Primary `m = 20`; `m = 5` and `m = 100` are reported beside it. These three values are fixed now.

**Three sizing rules, each computed per origin and cell from data visible at that origin only.**

1. *Prior rule.* Fit P1 on the visible rows, take the cell's pooled parameters for the origin's quarter (location, scale and degrees of freedom of the Student-t prior on theta), and choose n on a grid (1 to N/2) that maximizes expected gain under that prior, by quadrature over the t density.
2. *Base-rate rule.* A normal prior with mean zero whose standard deviation reproduces the visible significant-positive base rate of the cell at the cell's median planned standard error: `tau = s_star * sqrt((1.96 / z)^2 - 1)` with `z` the standard normal quantile of one minus the base rate (defined when the base rate exceeds 0.025; otherwise tau is zero and the rule tests nothing beyond one impression, which is reported). This uses the same information as P0 and nothing more. Then the same maximization.
3. *Fixed power rule.* The size at which a two-sided test at the 5 percent level has 80 percent power to detect a 10 percent relative lift on the cell's visible median reference rate. It reads no forecast. These parameters are fixed now.

Every size is capped at N/2. Three anchors are reported: never test (always the reference), test the whole audience (n = N/2, no roll), and the oracle.

**The world used to measure regret.** It must not be the prior being tested, and it must not be fitted on the data the rules saw. At each origin and cell, the distribution of true effects is the nonparametric maximum likelihood mixing distribution (Kiefer and Wolfowitz, fitted by EM on a grid of 200 effect values) of the rows scored at that origin, using each row's y and realized s. That is the next quarter's world, in a family that is not Student-t, estimated from rows the rules never saw. Expected regret under that distribution is computed exactly by summing over the grid (no Monte Carlo error), and a simulation of 20,000 tests per case cross-checks the formula in a unit test. Two misspecification worlds are reported beside it: the same distribution with its effects scaled by 0.67 and by 1.5, which show how each rule's regret moves when the world is narrower or wider than the history.

**Statistics.** The primary figure is relative regret, the sum over origins and cells of regret divided by the sum of oracle gain, per rule, and the paired difference of each rule from the fixed power rule and of the prior rule from the base-rate rule. Intervals resample whole tests within each origin and cell, refit the nonparametric distribution on each resample (200 resamples), and recompute the rules' regret under it; the sizes themselves come from earlier data and do not change across resamples. Adjusted bounds use the Bonferroni quantile for the two primary paired differences. Origin-and-cell units with fewer than 100 scored rows are listed and left out of every pooled figure; no unit is dropped by hand otherwise.

**What is reported, and when sizing is "not evaluated".** Approved by the lead on 6 November 2026 with three changes, fixed before any result.

- *A null is a result.* If the adjusted intervals of the prior rule's regret difference from both other rules contain zero, the paper reports "evaluated; no measurable sizing advantage". It does not report "not evaluated".
- *"Not evaluated" is reserved for two feasibility failures,* recorded in the key: fewer than half of the origin-and-cell units that remain after the date rule (decision D1) have 100 or more scored rows (the count of both is reported); or the three rules choose sizes within 10 percent of each other in more than 80 percent of the units.
- *What N and the world mean.* N is a synthetic horizon in impressions, a multiple of the cell's test scale; there is no money. The nonparametric world is fitted to the rows scored at that origin and cell, so regret measures each rule against what happened later. The 0.67 and 1.5 worlds are printed beside the main one.

Confirmed unchanged: audience multiple 20 primary with 5 and 100 beside it; power rule at 80 percent power, 5 percent level, 10 percent relative lift on the cell's visible median click-through rate, an absolute effect scale; the sizes-within-10-percent criterion.

## Not evaluated, and why

- P2 and the other headline-aware rungs: their predictive is per test, and the truth proxy is per cell. A per-test world does not exist for a test that ran once.
- Sequential stopping and tests with more than two arms: the decision problem is one variant against the reference at a fixed size.
- Profit in money: the unit is clicks.

## Implementation (ready for the go)

`src/mootcourt/sizing.py` (pure functions with tests: the gain, the optimizer checked against the closed form, the grid mixing distribution, the three rules, exact regret checked by simulation), the report key `sizing_evaluation` in `scripts/paper_extras.py` (parts A and B, upworthy only), and a stage `sizing-upworthy` of the driver after the main backtest. Part A needs only the score table. Part B refits P1 at each of nine origins (about 20 s each) and the mixing distribution 27 times at 200 resamples each; the estimate is 15 to 25 minutes on one core.
