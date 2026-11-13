# Reviewer Runs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Answer with numbers the six reviewer requests that the paper now states as limits.

**Architecture:** Each request becomes one small, additive piece: a standalone script under `scripts/` that reads existing reports or score tables, or one new option of `moot backtest` whose default changes nothing. All code is committed first, then every run is made from that one commit, and the new reports go into `paper/data/run8-randomization-window/` beside the reports they extend. Tables come from the new report keys through `paper/summary_tables/`; the paper's text changes last.

**Tech Stack:** Python 3, numpy, pandas, typer (`src/mootcourt/cli.py`), pytest, `uv`, bash run scripts, LaTeX through `make paper` and `scripts/tmlr_build.py`.

**Spec:** The panel review of 12 November 2026 (local notes in `.claude/fleet/red-team-2026-11-12/`, files `r2-venue.md`, `r3-check.md`, `applied-R2.md`) and the limits the paper states in `paper/sections/limitations.tex` under "What remains undone". This plan is the written record of design and decisions that `CLAUDE.md` requires before a result exists. The earlier plan of the same kind is `docs/superpowers/plans/2026-11-12-base-rate-recency-and-origins.md`.

Written 13 November 2026, before any result it describes exists.

## Global Constraints

- No em dash, no en dash, no other Unicode dash in any file. Write "to" for ranges and "minus" in prose.
- Do not use the common word for a person who possesses or is responsible for something.
- A run's results come from one committed code state: commit first, then run, and record the commit in the run folder. Do not edit `src/` or `scripts/` during a run.
- Decisions about an analysis are written down before its result exists. Sections "Decisions fixed before results" below are those decisions. If a run changes after results are seen, the paper says so.
- New report keys are additive. No existing key of an existing report may change value. Check with `git diff --stat paper/data` and by eye.
- Generated tables under `paper/tables/` are never edited by hand. Change `paper/summary_tables/*.py` or `paper/build_tables.py`.
- Each line of prose with a number has a `% src:` line directly above naming report and key. Every claim has a row in `paper/reviews/claims.md`. At most two numbers per sentence.
- No LLM calls. No download. Never open an Upworthy file named holdout, confirmatory or undeployed.
- Every number stays exploratory. None of these runs touches the confirmatory split.
- `MOOTCOURT_DATA_ROOT="/Volumes/Crucial X10/mootcourt-data"`; heavy outputs go there, not on the internal disk.
- Each new commit identifier that the paper would print goes into `FORBIDDEN` of `scripts/tmlr_build.py`, and the paper names it only inside `\iftmlr ... \else ... \fi`.
- The anonymous build holds 26 lettered appendix sections, the most LaTeX allows. A new table goes inside an existing block or section; no new `%% tmlr:title` line.
- The anonymous body stays at about 31 pages. Check the page of "References" after the text changes.

## What was seen before this was written

- Every report of run 8 as the paper prints it, including the calibration percentiles (P1 at the 100th percentile of the clustered null on the headline archive), the planted control at seed 7 (P2 recovers 0.09 of the oracle's gain pooled and 0.03 in the headline-only cell), the challengers raw and recalibrated, the learning curve at the final origin, the two exposure fixings where both were run, and `tables.split_half` of the synthetic backtest.
- Not seen and not computed: the rejection rate of the calibration procedure on outcomes drawn from the forecasts; any planted ledger with a seed other than 7 at 11,100 tests under the rolling backtest; a recalibrated P0, P1 or P2; a learning curve at any origin but the last; the base rate with a period term under exposure fixed on visible rows; the ranking within strata under exposure fixed on visible rows; degrees of freedom of the split-half fits.

## File Structure

| File | Change | Responsibility |
|---|---|---|
| `scripts/calibration_null_size.py` | create | Part A: rejection rate of the calibration procedure on calibrated outcomes |
| `scripts/positive_control_seeds.py` | create | Part B: recovered share by seed, from per-seed backtest folders |
| `src/mootcourt/harness.py` | modify `default_rungs` | Part C: `recalibrate_ladder` adds `P0+cal`, `P1+cal`, `P2+cal` |
| `src/mootcourt/cli.py` | modify `backtest`, `_variant_settings`, `_variant_flags` | Parts C and D: `--recalibrate-ladder`, `--learning-curve-origin` |
| `src/mootcourt/learning_curve.py` | modify `run_learning_curve`, `write_learning_curve` | Part D: an explicit origin |
| `scripts/learning_curve_origins.py` | create | Part D: one summary over the per-origin curves |
| `src/mootcourt/extras_v2.py` | modify `exposure_fixed` | Part E: a `variant` argument, new key `exposure_fixed_visible` |
| `scripts/paper_extras.py` | modify the `step("exposure_fixed", ...)` call site | Part E: write the second key |
| `src/mootcourt/harness_stats.py` | modify `split_half` | Part F: add `nu_*` and `sd_*` per half |
| `scripts/split_half_spread.py` | create | Part F: write the split-half fit of the synthetic ledger with the new keys |
| `scripts/run_ablations.sh` | modify the variant list | Parts C and E: two new variants |
| `scripts/run_reviewer_runs.sh` | create | The driver of every run in this plan, with stage timings |
| `paper/summary_tables/experiments.py`, `appendix.py`, `limits.py` | modify | Tables for Parts A to F |
| `paper/sections/*.tex`, `paper/reviews/claims.md`, run folder `README.md` | modify | Text, register, sixth exception paragraph |
| `tests/test_calibration_null_size.py`, `tests/test_positive_control_seeds.py`, `tests/test_learning_curve_origins.py`, `tests/test_split_half_spread.py` | create | One test file per new script |
| `tests/test_review_n.py` (recalibration), `tests/test_challengers_ablations.py` (learning curve), `tests/test_x2_x3_views.py`, `tests/test_harness_stats.py` (split-half) | modify | Tests for the changed functions |

## Review Focus

1. A stratum whose forecast is one number for every row (P0 inside a cell at one origin, P1 with exposure fixed). The calibration size script must return a rate and not divide by zero; expected: the row is reported with `constant_forecast: true` and a rate.
2. A planted ledger at one seed where the guard admits no weight in any cell. The seeds summary must report a recovered share of 0.0 for that seed and count it, not drop the seed.
3. A recalibration map at an origin with too few visible events. `Recalibrated` already falls back to the visible base rate below `MIN_EVENTS`; the ladder rungs must take the same fallback and the report must count the origins where it happened.
4. A learning-curve origin whose smallest fractions leave too few rows to fit. Expected: the point is written with `fitted: false` and the summary counts it; the run does not stop.
5. A report that lacks the new key (a run folder from before this plan). Every table builder must print "not run" in the cell and the build must pass.

Each line has its test in the task that holds the code.

---

## Part A: does the calibration test reject a calibrated forecaster at its stated rate?

### Why

The paper says the prior fails calibration because its error sits at the 100th percentile of a null clustered by test. The procedure estimates the within-test correlation from the same outcomes it then tests. No run shows how often the whole procedure rejects when the forecasts are in fact calibrated.

### What is added

`scripts/calibration_null_size.py`. For one score table, one rung and one stratum it takes the real forecasts `p` and test identifiers, and repeats `reps` times: draw outcomes from `p` with a known latent within-test correlation `rho_true` (one shared normal per test plus one per row, the copula of `ece_null`), then run the report's procedure unchanged on those outcomes (`design_effect`, `latent_rho_for_design_effect`, `ece_percentile` with `NULL_DRAWS`, as in `harness_stats.py` lines 858 to 868), and record the percentile.

### Decisions fixed before results

- Inputs: `scores-upworthy-20261106-2dc461f52ea4.parquet` of the main run. Rungs P0, P1, P2. Strata ALL, headline_only, image_only, both. Both binnings (equal width, equal mass).
- `rho_true` takes three values per stratum: 0, the latent correlation the report's procedure gives on the real outcomes (`rho_obs`), and twice that, capped at 0.99.
- `reps = 400`, seed 20261113 for the outcome draws; the procedure's own seed stays 0, as in the report.
- Reported per row: the share of repetitions with percentile above 95 and above 99, each with a Wilson 95 percent interval, and the 95th percentile of the recorded percentiles (the empirical critical value).
- Reading. At `rho_true = rho_obs`, the procedure is "sized" when the Wilson interval of the rejection share at 95 contains 0.05 or lies below it. If it is sized in a stratum, the paper keeps its calibration verdicts there and cites the rate. If it is not, the paper prints the measured rate, and a verdict of "rejected" stands in that stratum only where the observed percentile is above the empirical critical value; any other "rejected" becomes "not decided by this test".
- A null here (the procedure over-rejects everywhere) weakens the calibration claim and the paper says so in the abstract's calibration sentence. The headline on the log score does not depend on it.

### Task A1: the size script

**Files:**
- Create: `scripts/calibration_null_size.py`
- Test: `tests/test_calibration_null_size.py`

**Interfaces:**
- Consumes: `mootcourt.harness_stats.design_effect(p, event, test_ids) -> dict` (key `design_effect`), `latent_rho_for_design_effect(p, test_ids, target_deff, seed=0) -> float`, `ece_percentile(p, event, draws, seed, n_bins, test_ids, icc, equal_mass) -> float`, `NULL_DRAWS`.
- Produces: `draw_events(p, test_ids, rho, rng) -> np.ndarray` of 0.0 and 1.0; `procedure_percentile(p, event, test_ids, equal_mass=False, seed=0) -> float`; `size_row(p, test_ids, rho_true, reps, seed, equal_mass=False) -> dict` with keys `reps`, `rho_true`, `reject_95`, `reject_95_lo`, `reject_95_hi`, `reject_99`, `reject_99_lo`, `reject_99_hi`, `critical_95`, `constant_forecast`; `summarize(scores: pd.DataFrame, rungs, strata, reps, seed) -> dict` with `rows` (one per rung, stratum, binning, `rho_true` label in `("zero", "observed", "double")`) and `inputs`. Command line: `--scores PATH --out PATH [--reps 400] [--seed 20261113] [--jobs 4]`.

- [ ] **Step 1: Write the failing tests**

```python
def test_draws_keep_the_marginals():
    rng = np.random.default_rng(0)
    p = np.full(20000, 0.2); t = np.repeat(np.arange(5000), 4)
    e = cns.draw_events(p, t, 0.5, rng)
    assert abs(e.mean() - 0.2) < 0.01
    by_test = pd.Series(e).groupby(t).mean()
    assert by_test.var() > 0.2 * 0.8 / 4 * 1.2          # outcomes of a test move together

def test_independent_calibrated_forecasts_reject_near_five_percent():
    rng = np.random.default_rng(1)
    p = rng.uniform(0.02, 0.4, 3000); t = np.arange(3000)          # one row per test
    row = cns.size_row(p, t, 0.0, reps=200, seed=3)
    assert row["reject_95_lo"] <= 0.05 <= row["reject_95_hi"]
    assert 90.0 <= row["critical_95"] <= 99.9

def test_constant_forecast_is_flagged_and_still_scored():
    p = np.full(800, 0.1); t = np.repeat(np.arange(200), 4)
    row = cns.size_row(p, t, 0.3, reps=20, seed=0)
    assert row["constant_forecast"] is True and 0.0 <= row["reject_95"] <= 1.0

def test_summary_has_one_row_per_rung_stratum_binning_and_truth(tmp_scores):
    doc = cns.summarize(tmp_scores, rungs=("P0", "P1"), strata=("ALL",), reps=5, seed=0)
    assert len(doc["rows"]) == 2 * 1 * 2 * 3
    assert {r["truth"] for r in doc["rows"]} == {"zero", "observed", "double"}
```

`tmp_scores` is a fixture: 600 rows, columns `rung`, `cell`, `test_id`, `p_sig`, `event`, two rungs, 150 tests of 2 rows.

- [ ] **Step 2: Run them and see them fail**

Run: `uv run pytest -p no:cacheprovider tests/test_calibration_null_size.py`
Expected: FAIL, module `calibration_null_size` not found.

- [ ] **Step 3: Implement the script**

Import the script in tests the way `tests/test_by_origin_difference.py` imports its script. The Wilson interval is at 95 percent. `draw_events` uses its own generator and must not call or change `ece_null`, whose random stream fixes published percentiles. The event column and the stratum filter follow `scripts/by_origin_difference.py`.

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run pytest -p no:cacheprovider tests/test_calibration_null_size.py`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/calibration_null_size.py tests/test_calibration_null_size.py
git commit -m "Add the rejection rate of the calibration procedure on calibrated outcomes"
```

---

## Part B: the positive control over several seeds

### Why

The figure the paper sets against the real archive (P2 recovers 0.09 of the oracle's gain) rests on one simulated ledger, seed 7.

### Decisions fixed before results

- Seeds 7, 8, 9, 10 and 11. Seed 7 is the existing run and is reused, not rerun. Each new seed repeats lines 118 to 120 of `scripts/run_experiments.sh` with only `--seed` of `simulate ledger` changed: 11,100 tests, planted lift 1.0 percent, the three challengers, backtest seed 0.
- Per seed, from `positive_control_rungs` of `scripts/paper_extras.py` unchanged: the oracle's gain over P1, P2's gain over P1, the recovered share pooled and in the headline-only cell, and P2 minus P1 in the headline-only cell.
- Reported: each seed's values, and over seeds the median, the smallest and the largest. No interval over five seeds is claimed.
- One more count: the seeds at which P2 minus P1 in the headline-only cell falls inside the real archive's interval for that cell (minus 0.0007 to 0.0010, read from the main report, not typed).
- Reading. The paper replaces the single figure with the median and the range. If the count above is 5 of 5, the sentence "the real interval contains what a planted signal of that size returns" stays. If it is 3 or 4, the sentence says "at most seeds". If it is 2 or fewer, the sentence is withdrawn and the paper says the real result is weak evidence against a signal of that size.
- A seed where the guard admits nothing counts as a recovered share of zero.

### Task B1: the seeds summary

**Files:**
- Create: `scripts/positive_control_seeds.py`
- Test: `tests/test_positive_control_seeds.py`

**Interfaces:**
- Consumes: `paper_extras.positive_control_rungs(run_dirs, strength=1.0) -> dict` with `runs`, each holding `n_tests`, `by_cell` and rung rows with `diff_logscore_vs_p1`; read its return shape in `scripts/paper_extras.py` line 425 before writing the reader.
- Produces: `seed_record(run_doc: dict, seed: int) -> dict` with keys `seed`, `oracle_gain`, `p2_gain`, `recovered_pooled`, `recovered_headline_only`, `p2_minus_p1_headline_only`, `guard_admitted_cells`; `summarize(records: list[dict], real_lo: float, real_hi: float) -> dict` with `by_seed`, `median`, `min`, `max` (each a dict over the four numeric keys) and `inside_real_interval` (an int) and `seeds` (an int). Command line: `--runs SEED=DIR ... --main-report PATH --out PATH`.

- [ ] **Step 1: Write the failing tests**

```python
def rec(seed, share, d):
    return {"seed": seed, "oracle_gain": 0.02, "p2_gain": 0.02 * share, "recovered_pooled": share,
            "recovered_headline_only": share / 3, "p2_minus_p1_headline_only": d, "guard_admitted_cells": 1}

def test_median_and_range_over_seeds():
    doc = pcs.summarize([rec(7, 0.09, 0.0004), rec(8, 0.0, 0.0), rec(9, 0.20, 0.0020)], real_lo=-0.0007, real_hi=0.0010)
    assert doc["seeds"] == 3
    assert doc["median"]["recovered_pooled"] == pytest.approx(0.09)
    assert doc["min"]["recovered_pooled"] == 0.0 and doc["max"]["recovered_pooled"] == pytest.approx(0.20)
    assert doc["inside_real_interval"] == 2

def test_a_seed_with_no_admission_is_zero_and_kept():
    run_doc = make_run_doc(p2_gain=0.0, oracle_gain=0.02, admitted=0)          # helper in the test file, shaped like positive_control_rungs
    r = pcs.seed_record(run_doc, seed=8)
    assert r["recovered_pooled"] == 0.0 and r["guard_admitted_cells"] == 0
```

- [ ] **Step 2: Run and see them fail.** `uv run pytest -p no:cacheprovider tests/test_positive_control_seeds.py`; expected: module not found.
- [ ] **Step 3: Implement.** The recovered share is `p2_gain / oracle_gain`; an oracle gain at or below zero gives `None` for the share and the seed is listed with a note.
- [ ] **Step 4: Run and see 2 passed.**
- [ ] **Step 5: Commit** with message "Add the positive control summarized over ledger seeds".

---

## Part C: the ladder's rungs through the same recalibration map

### Why

The challengers are printed raw and recalibrated with one Platt map per origin, fit on visible rows. P0, P1 and P2 get no map, so the table does not say whether the same map would lift them.

### Decisions fixed before results

- One option, `--recalibrate-ladder` (default off, which changes nothing), adds rungs `P0+cal`, `P1+cal`, `P2+cal` through the existing `Recalibrated` wrapper and the same method (`platt`), fit on the visible rows of each origin. Like the challengers' maps they report only `p_sig`.
- One run: the main settings plus `--recalibrate-ladder`, written as an ablation report (`--recalibrate-ladder` variant). The main report is not rerun and its family of 52 intervals does not change.
- Reported in Table `fmt-challengers`: three new rows with Brier skill against the raw base rate, the unadjusted interval, and the calibration percentile. The intervals of the new rows are unadjusted and the caption says so.
- Reading. If the interval of `P1+cal` lies above zero, the paper says a map fit on visible rows removes the prior's shortfall on skill, and that this is the like for like comparison with the recalibrated challengers. If it spans zero, the paper says the map does not rescue it. Either way the headline, which is on the log score, is untouched, because the map gives no density.
- `P0+cal` is the check on the method: P0 is one number per cell and origin, so its map can only move levels. Its row is printed whatever it shows.
- The origins at which the map fell back to the visible base rate are counted and printed in the caption.

### Task C1: the option

**Files:**
- Modify: `src/mootcourt/harness.py` (`default_rungs`, near lines 610 to 690)
- Modify: `src/mootcourt/cli.py` (`backtest` options near line 482, `_variant_settings`, `_variant_flags`)
- Modify: `scripts/run_ablations.sh` (add `"--recalibrate-ladder"` to the variant list at lines 39 to 42)
- Test: `tests/test_review_n.py`, which already covers `Recalibrated`

**Interfaces:**
- Produces: `default_rungs(..., recalibrate_ladder: bool = False)`; with it, the returned dict holds `"P0+cal"`, `"P1+cal"`, `"P2+cal"` after the raw rungs, each `lambda rows, origin: Recalibrated(raw_factory(rows, origin), recalibration)`. CLI flag `--recalibrate-ladder/--no-recalibrate-ladder`, variant suffix `recalibrate-ladder`.

- [ ] **Step 1: Write the failing tests**

```python
def test_ladder_rungs_get_a_map_only_when_asked(small_ledger):
    plain = default_rungs("synthetic", small_ledger)
    assert not any(k.endswith("+cal") for k in plain)
    with_map = default_rungs("synthetic", small_ledger, recalibrate_ladder=True)
    assert {"P0+cal", "P1+cal", "P2+cal"} <= set(with_map)
    assert list(with_map)[:3] == list(plain)[:3]          # the raw rungs keep their order

def test_recalibrated_prior_scores_and_reports_only_p_sig(small_ledger):
    scores = rolling_origin(small_ledger, default_rungs("synthetic", small_ledger, recalibrate_ladder=True), source="synthetic")
    cal = scores[scores["rung"] == "P1+cal"]; raw = scores[scores["rung"] == "P1"]
    assert len(cal) == len(raw) and cal["p_sig"].between(0, 1).all()
    assert cal["logscore"].isna().all()
    assert raw.reset_index(drop=True)["p_sig"].equals(                      # the raw rung is untouched by the option
        rolling_origin(small_ledger, default_rungs("synthetic", small_ledger), source="synthetic").query("rung == 'P1'").reset_index(drop=True)["p_sig"])

def test_map_falls_back_below_min_events(tiny_ledger):          # an origin with fewer visible events than recalibration.MIN_EVENTS
    scores = rolling_origin(tiny_ledger, default_rungs("synthetic", tiny_ledger, recalibrate_ladder=True), source="synthetic")
    cal = scores[scores["rung"] == "P1+cal"]
    assert cal.groupby(["origin", "cell"])["p_sig"].nunique().max() == 1
```

Use the ledger fixtures of the existing recalibration tests; if the names differ, reuse theirs.

- [ ] **Step 2: Run and see them fail** on the unknown keyword.
- [ ] **Step 3: Implement.** `Recalibrated` fits its map on the inner model's out-of-fold predictions for visible rows; confirm that the P0, P1 and P2 predictor classes satisfy what `Recalibrated.__init__` and its fit call on the inner model (read `harness.py` lines 552 to 592). If one lacks a method the wrapper calls, add that method to the predictor with a test; do not weaken the wrapper.
- [ ] **Step 4: Run the three tests and the whole of the touched test file; all pass.** A new command line option changes the generated command reference: regenerate it with `scripts/gen_cli_docs.py` and run the docs tests (`grep -ln gen_cli_docs tests/*.py` names them).
- [ ] **Step 5: Commit** with message "Add a recalibration map for the ladder's rungs, off by default".

---

## Part D: the learning curve at every origin

### Why

"More history improves the forecast of the distribution" is measured at one origin, the last one with enough held-out rows.

### Decisions fixed before results

- The same curve as the existing one (fractions 0.01, 0.02, 0.05, 0.1, 0.25, 0.5, 1; 20 seeds; the challengers and flags of line 121 of `scripts/run_experiments.sh`) at each of the seven scored origins of the main run. The existing curve at the final origin is reused if its origin is one of the seven and is not rerun.
- Per origin the summary reads two paired differences against the full history, at one quarter and at one half of it, on the log score and on the Brier score, each with its interval as `_paired_vs_full` already computes it.
- Reported: a table with one row per origin, and two counts: the origins at which half the history scores worse than all of it on the log score with an interval that excludes zero, and the same at one quarter.
- Reading. If the count at one quarter is at least 5 of 7, the paper says more history helped at most origins. If it is 3 or 4, it says the gain is not consistent across origins. If it is 2 or fewer, the sentence that more history improved the forecast is limited to the origin where it was measured, and the abstract's clause on history is cut.
- A fraction that leaves too few rows to fit at an early origin is recorded as not fitted and is not counted on either side.

### Task D1: an explicit origin for the curve

**Files:**
- Modify: `src/mootcourt/learning_curve.py` (`run_learning_curve` line 178, `write_learning_curve` line 377)
- Modify: `src/mootcourt/cli.py` (near lines 488 and 619 to 629)
- Test: `tests/test_challengers_ablations.py`, which holds the learning curve tests (confirm with `grep -ln learning_curve tests/*.py`)

**Interfaces:**
- Produces: `run_learning_curve(..., origin: pd.Timestamp | None = None)`; `None` keeps `final_origin(ledger, heldout_min)`. Each point of the returned document gains `fitted: bool`. `write_learning_curve(doc, out_dir, snapshot_id, suffix: str | None = None)` writes `learning-curve-<source>-<sid>--origin-YYYY-MM-DD.json` when a suffix is given. CLI option `--learning-curve-origin YYYY-MM-DD`; a date that is not a quarterly origin of the ledger is a `typer.BadParameter`.

- [ ] **Step 1: Write the failing tests**

```python
def test_default_origin_is_unchanged(curve_ledger, factory, gates):
    a = run_learning_curve(curve_ledger, "synthetic", factory, [0.5, 1.0], 2, gates, B=20)
    b = run_learning_curve(curve_ledger, "synthetic", factory, [0.5, 1.0], 2, gates, B=20, origin=final_origin(curve_ledger))
    assert a["final_origin"] == b["final_origin"] and a["points"] == b["points"]

def test_an_earlier_origin_scores_its_own_quarter(curve_ledger, factory, gates):
    early = quarterly_origins(curve_ledger)[-3]
    doc = run_learning_curve(curve_ledger, "synthetic", factory, [0.5, 1.0], 2, gates, B=20, origin=early)
    assert doc["final_origin"] == early.isoformat()
    assert doc["heldout_rows"] > 0

def test_a_fraction_too_small_to_fit_is_recorded_not_raised(curve_ledger, factory, gates):
    doc = run_learning_curve(curve_ledger, "synthetic", factory, [0.001, 1.0], 2, gates, B=20)
    small = [p for p in doc["points"] if p["fraction"] == 0.001]
    assert small and all(p["fitted"] is False for p in small)
```

Take `curve_ledger`, `factory` and `gates` from the existing tests of this file. If the document's list of points has another key name, use the existing one in all three tests and in Task D2.

- [ ] **Step 2: Run and see them fail.**
- [ ] **Step 3: Implement.** The key `final_origin` keeps its name in the document so that existing readers work; add `origin_rule: "final" | "given"`.
- [ ] **Step 4: Run the touched test file; all pass, old tests included.**
- [ ] **Step 5: Commit** with message "Let the learning curve run at a named origin".

### Task D2: the summary over origins

**Files:**
- Create: `scripts/learning_curve_origins.py`
- Test: `tests/test_learning_curve_origins.py`

**Interfaces:**
- Consumes: the documents written by Task D1.
- Produces: `origin_row(doc: dict, rung: str = "P1") -> dict` with `origin`, `heldout_rows`, and for each of `quarter` and `half`: `log_diff`, `log_lo`, `log_hi`, `brier_diff`, `brier_lo`, `brier_hi`, `fitted`; `summarize(docs: list[dict]) -> dict` with `rows`, `origins`, `worse_at_half` and `worse_at_quarter` (ints: interval of the log-score difference excludes zero on the side of the smaller history scoring worse), `not_fitted` (an int). Command line: `--curves PATH ... --out PATH`.

- [ ] **Step 1: Write the failing test**

```python
def test_counts_only_intervals_that_exclude_zero():
    docs = [fake_curve("2014-01-01", quarter=(-0.010, -0.015, -0.005), half=(-0.002, -0.006, 0.002)),
            fake_curve("2014-04-01", quarter=(-0.001, -0.004, 0.002), half=(0.001, -0.002, 0.004)),
            fake_curve("2014-07-01", quarter=None, half=(-0.004, -0.007, -0.001))]          # quarter not fitted
    doc = lco.summarize(docs)
    assert doc["origins"] == 3 and doc["worse_at_quarter"] == 1 and doc["worse_at_half"] == 1 and doc["not_fitted"] == 1
```

`fake_curve` builds the smallest document `origin_row` can read; the sign convention (smaller history minus full history, in the score's own orientation) is the one `_paired_vs_full` uses, so read lines 134 to 160 of `learning_curve.py` and state the convention in the script's docstring.

- [ ] **Step 2 to 4: fail, implement, pass.**
- [ ] **Step 5: Commit** with message "Add the learning curve summarized over origins".

---

## Part E: tables that still read the whole-ledger exposure run

### Why

Exposure fixed at the cell median over the whole ledger reads rows after the origin. The paper labels it a diagnostic, yet three tables and one list of readings still rest on it, while the version that obeys the visibility rule exists for two reports only.

### Decisions fixed before results

- One new backtest variant: `--base-recency quarter --exposure cell-median-visible`. The two visible-rows reports that exist are reused.
- `exposure_fixed` of `extras_v2.py` is computed a second time against the visible-rows report and stored under a new key, `exposure_fixed_visible`. The existing key keeps its values.
- Tables `fmt-exposure-fixed` and `fmt-base-recency` and the last column of `fmt-base-density` switch to the visible-rows reports. The whole-ledger figures stay in the reports and in one sentence that says the two fixings were compared.
- The five readings in the list under Table `fmt-exposure-fixed` (P1 constant in all strata and its AUC of one half; P2's strata with more than one forecast; P2's AUC in the headline-only cell; the rise in pooled Brier skill; the pattern by cell) are read again from the new key. Each is reported as the visible-rows run gives it. Where a reading changes side, the paper says the earlier reading came from the diagnostic and does not hold under the visibility rule.
- The reading of P2's AUC within the headline-only cell (it rose with exposure fixed) was already marked as unplanned. It stays marked so.

### Task E1: the second key

**Files:**
- Modify: `src/mootcourt/extras_v2.py` (`exposure_fixed`, line 293)
- Modify: `scripts/paper_extras.py` (line 1624)
- Modify: `scripts/run_ablations.sh` (add `"--base-recency quarter --exposure cell-median-visible"`)
- Test: `tests/test_x2_x3_views.py`

**Interfaces:**
- Produces: `exposure_fixed(reports_dir, source, snapshot_id, variant: str = "exposure-cell-median") -> dict | None`; with `variant="exposure-cell-median-visible"` the `definition` string says the median is taken over the cell's admitted rows usable by the start of the row's calendar quarter. `paper_extras` writes `doc["exposure_fixed_visible"]` beside `doc["exposure_fixed"]`.

- [ ] **Step 1: Write the failing tests**

```python
def test_the_default_variant_is_unchanged(reports_with_both_fixings):
    d, sid = reports_with_both_fixings
    assert extras_v2.exposure_fixed(d, "upworthy", sid) == extras_v2.exposure_fixed(d, "upworthy", sid, variant="exposure-cell-median")

def test_the_visible_variant_reads_its_own_report(reports_with_both_fixings):
    d, sid = reports_with_both_fixings
    doc = extras_v2.exposure_fixed(d, "upworthy", sid, variant="exposure-cell-median-visible")
    assert doc["report"].endswith("--exposure-cell-median-visible.json")
    assert "start of the row's calendar quarter" in doc["definition"]

def test_a_missing_visible_report_gives_none(reports_with_whole_ledger_only):
    d, sid = reports_with_whole_ledger_only
    assert extras_v2.exposure_fixed(d, "upworthy", sid, variant="exposure-cell-median-visible") is None
```

Build the fixtures from the existing fixture of this file that writes a main and a fixed report.

- [ ] **Step 2 to 4: fail, implement, pass; then run all of `tests/test_x2_x3_views.py`.**
- [ ] **Step 5: Commit** with message "Read exposure fixed on visible rows into its own report key".

---

## Part F: degrees of freedom of the split-half fits

### Why

The table of synthetic truth prints a Student-t scale beside the generator's normal standard deviation. The two are not comparable, and the report holds no degrees of freedom for the two halves, so the paper withdrew its sentence on spreads.

### Decisions fixed before results

- `split_half` records, per cell and half, the fitted degrees of freedom and the standard deviation equivalent `tau * sqrt(nu / (nu - 2))`, through `sd_equivalent` of `predictors/p1.py`. Existing keys keep their values.
- The main synthetic report is not rerun. A small script writes `split-half-synthetic-20261103-bf4fd286e2b2.json` from the same ledger.
- Table `fmt-app-syn-truth` prints the standard deviation equivalent beside the generator's standard deviation. A half whose fit has degrees of freedom at or below 2 has no finite standard deviation; the cell prints "none" and the caption says why.
- Reading. The paper states, per cell, whether both halves' standard deviations fall within three tenths of the truth, the bound its withdrawn sentence used. It restores the sentence only for cells where both do.

### Task F1: the keys and the script

**Files:**
- Modify: `src/mootcourt/harness_stats.py` (`split_half`, line 408)
- Create: `scripts/split_half_spread.py`
- Test: `tests/test_harness_stats.py`, which covers `split_half`, and `tests/test_split_half_spread.py`

**Interfaces:**
- Produces: each cell's dict from `split_half` gains `nu_odd`, `nu_even`, `sd_odd`, `sd_even` (floats; `sd_*` is `None` when `nu <= 2`; `nu` infinite is written as the string `"inf"` in JSON, as the rest of the report does, so check how `report.py` serializes infinity and follow it). Script: `--ledger PATH --out PATH`, writes `{"split_half": {...}, "inputs": {...}}`.

- [ ] **Step 1: Write the failing tests**

```python
def test_split_half_keeps_old_keys_and_adds_spread(synthetic_ledger):
    out = split_half(synthetic_ledger)
    cell = next(iter(out.values()))
    assert {"mu_odd", "mu_even", "tau_odd", "tau_even"} <= set(cell)          # unchanged keys
    assert {"nu_odd", "nu_even", "sd_odd", "sd_even"} <= set(cell)
    assert cell["sd_odd"] is None or cell["sd_odd"] >= cell["tau_odd"]

def test_sd_is_none_when_the_tail_has_no_variance():
    assert sps.sd_or_none(tau=1.0, nu=2.0) is None
    assert sps.sd_or_none(tau=1.0, nu=float("inf")) == pytest.approx(1.0)
    assert sps.sd_or_none(tau=1.0, nu=3.0) == pytest.approx(3 ** 0.5)
```

- [ ] **Step 2 to 4: fail, implement, pass.** Confirm with one more assertion in the existing test that `mu_*` and `tau_*` equal their values before the change on the fixture (take the values by running the test once before editing `split_half`).
- [ ] **Step 5: Commit** with message "Record degrees of freedom and standard deviation of the split-half fits".

---

## Task G: the run

**Files:**
- Create: `scripts/run_reviewer_runs.sh`
- Modify: `scripts/tmlr_build.py` (`FORBIDDEN`), after the run commit is known

**Interfaces:**
- Consumes: every command line produced in Parts A to F.
- Produces: stage lines appended to a `stages-reviewer-runs.txt` under the data root in the format of `stages.txt` (`NAME EXIT SECONDS`), and these reports under `$MOOTCOURT_DATA_ROOT/reports`:
  - `calibration-null-size-upworthy-20261106-2dc461f52ea4.json`
  - `positive-control/seeds/seed-8` to `seed-11` (backtest folders), and `positive-control-seeds.json`
  - `ablations/backtest-upworthy-20261106-2dc461f52ea4--recalibrate-ladder.json`
  - `ablations/backtest-upworthy-20261106-2dc461f52ea4--exposure-cell-median-visible+base-recency-quarter.json` (confirm the order of the suffix parts from an existing file name before writing table readers)
  - `learning-curve-upworthy-20261106-2dc461f52ea4--origin-YYYY-MM-DD.json` for each scored origin, and `learning-curve-origins-upworthy-20261106-2dc461f52ea4.json`
  - `paper-extras-upworthy-20261106-2dc461f52ea4.json` with the added key `exposure_fixed_visible`
  - `split-half-synthetic-20261103-bf4fd286e2b2.json`

- [ ] **Step 1: Write the driver.** Model it on `scripts/run8.sh` and the `step` and `pool` helpers of `scripts/run_experiments.sh`. It refuses to start when `git status --porcelain src scripts` is not empty and writes `git rev-parse HEAD` to `reviewer-runs-commit.txt` first. It has `--dry-run` and `--only NAME`. Stages and rough times from `stages.txt` of run 8: four planted backtests at about 11 minutes each; two ablations at about 4 minutes each; six learning curves at up to 33 minutes each; the size script about 1 to 2 hours with `--jobs 4`; extras and split-half under 5 minutes. With the pool the whole run is about 3 hours.
- [ ] **Step 2: Run `scripts/run_reviewer_runs.sh --dry-run`** and read every printed command against this plan.
- [ ] **Step 3: Full suite.** `uv run pytest -p no:cacheprovider` (about 50 minutes). Expected: all pass. Run `uv run ruff check src scripts tests`.
- [ ] **Step 4: Commit the driver.** This commit is the code state of the run. Record its identifier.
- [ ] **Step 5: Run.** `scripts/run_reviewer_runs.sh 2>&1 | tee "$MOOTCOURT_DATA_ROOT/reviewer-runs.log"`, in the background. Do not touch `src/` or `scripts/` until it ends. Check `df -h /` before and after.
- [ ] **Step 6: Check the results are additive.** `scripts/assemble_run_folder.py --update`, then `git diff --stat paper/data/run8-randomization-window`. Expected: new files, and `paper-extras-upworthy-*.json` changed only by one added key. Confirm with `python3 -c` that every key present before has the same value. A rerun of the extras stage can drop keys written by a separate option such as `--sizing-only`; if any key is gone, restore the stage that writes it before going on.
- [ ] **Step 7: Record.** Add a sixth exception paragraph to the run folder's `README.md`: what was added, on which commit, and that it came after the panel review. Add the commit identifier to `FORBIDDEN` in `scripts/tmlr_build.py`. Append a "Post-run notes" section to this plan with each decision rule and the branch the result took, written before any paper text changes.
- [ ] **Step 8: Commit** the reports, the README and the notes with message "Add the reviewer runs to run 8".

## Task H: tables

**Files:**
- Modify: `paper/summary_tables/experiments.py`, `paper/summary_tables/appendix.py`, `paper/summary_tables/limits.py`, and `paper/build_tables.py` for `fmt-app-syn-truth`
- Test: `tests/test_summary_tables.py`

**Interfaces:**
- Produces these generated tables (names fixed here so the text can cite them):
  - `fmt-calibration-size`: rows P0, P1, P2 by stratum at the observed correlation, columns rejection share at 95 with interval, empirical critical value, observed percentile from the main report.
  - `fmt-control-seeds`: one row per seed, then median, smallest, largest.
  - `fmt-challengers`: three added rows `P0+cal`, `P1+cal`, `P2+cal`.
  - `fmt-learning-origins`: one row per origin.
  - `fmt-exposure-fixed`, `fmt-base-recency`, `fmt-base-density`: now from the visible-rows reports; `fmt-base-density` drops its whole-ledger column.
  - `fmt-app-syn-truth`: standard deviation equivalents.

- [ ] **Step 1: For each table, add a test** in the style of the file: the table builds from the run folder, has the stated row count, and builds to a "not run" cell from a folder that lacks the new report (Review Focus 5). Row counts: `fmt-calibration-size` 12; `fmt-control-seeds` 5 seeds plus 3; `fmt-learning-origins` 7.
- [ ] **Step 2: Run and see them fail.**
- [ ] **Step 3: Implement the builders,** then `make tables` and `git status --short paper/tables`. A changed table not named above is a finding to explain before going on.
- [ ] **Step 4: Tests pass;** `uv run pytest -p no:cacheprovider tests/test_summary_tables.py tests/test_build_tables_deterministic.py`.
- [ ] **Step 5: Commit** with message "Build the tables of the reviewer runs".

## Task I: the paper

**Files:**
- Modify: `paper/sections/results.tex`, `results-b.tex`, `ablations.tex`, `appendix.tex`, `limitations.tex`, `discussion.tex`, `abstract-tmlr.tex`, `paper/main.tex` (abstract and the glance table's source rows if a headline reading changes), `paper/dist/metadata.md`, `paper/reviews/claims.md`

- [ ] **Step 1: Apply each decision rule** from the post-run notes, one part at a time. For each part: place the table inside an existing section or moved block (no new appendix letter), write the sentences the rule calls for, put a `% src:` line above each line with a number, and read each key to confirm it is the quantity the sentence claims.
- [ ] **Step 2: Remove from "What remains undone"** each limit that now has a run, and state what the run still does not show (five seeds are not a distribution; one map method; one archive).
- [ ] **Step 3: Say when it was added.** Each new result carries one sentence that it was run after the panel review, with decisions written down first, and that it is exploratory.
- [ ] **Step 4: Claims register.** A row for each new claim, and a changed row for each claim whose wording or verdict changed. While there, refresh the quoted sentences of rows whose paper wording changed in the rewrite of 13 November.
- [ ] **Step 5: Paper check.** Run the `paper-check` skill in order: `make tables`; `make paper`; `uv run python scripts/paper_audit.py` (0 unmatched, 0 unresolved); `uv run python scripts/claims_audit.py paper/reviews/claims.md paper/data/run8-randomization-window` (exit 0); the paper tests with `tests/test_tmlr_build.py`; `uv run python scripts/tmlr_build.py --paper paper --compile` (0 undefined references, "References" on or before page 32). Keep `paper/dist/metadata.md` under 1,920 plain-text characters, in agreement with the abstract, with the right page and table counts.
- [ ] **Step 6: An independent read.** One fresh reader, briefed as the `paper-review` skill says, reads only the changed passages and their tables against the reports. Apply or reject each finding with a reason.
- [ ] **Step 7: Commit** with message "Report the reviewer runs in the paper". Push `paper-v2` only on the user's word.

## Self-review notes

- Coverage: the six requests map to Parts A (calibration null), B (control over seeds), C (recalibrated ladder), D (learning curve by origin), E (whole-ledger tables), F (split-half degrees of freedom). Tasks G to I carry them to reports, tables and text.
- Each part states what a null means and which sentence of the paper it changes.
- Names used across tasks: `exposure_fixed_visible`, `recalibrate_ladder`, `--recalibrate-ladder`, `--learning-curve-origin`, `fitted`, `fmt-calibration-size`, `fmt-control-seeds`, `fmt-learning-origins`.
- Open to the implementer by design: the body of each function, the fixtures' construction, and the layout of each table's columns beyond the ones named.
